#!/usr/bin/env python3
"""
Retrieval and Generation System for Personal Diary Chatbot

This module implements the RAG (Retrieval-Augmented Generation) pipeline for the diary chatbot.
It handles document retrieval from the vector database and generates contextual responses
using Google's Generative AI.

Components:
- Document Retrieval: Query vector database for relevant diary entries
- Context Processing: Format retrieved documents for LLM consumption
- Response Generation: Generate contextual responses using retrieved diary content
- Conversation Management: Handle chat history and context preservation
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from functools import lru_cache
import hashlib

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# LangChain imports
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain.prompts import ChatPromptTemplate, PromptTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiaryRAGSystem:
    """
    Retrieval-Augmented Generation system for personal diary chatbot.
    
    This class handles the complete RAG pipeline:
    1. Retrieve relevant diary entries from vector database
    2. Format context for LLM consumption
    3. Generate contextual responses using Google's Generative AI
    """
    
    def __init__(
        self,
        user_id: int = 1,
        base_vector_path: str = "./src/VectorDB",
        google_api_key: Optional[str] = None,
        embedding_model: str = "models/embedding-001",
        chat_model: str = "gemini-2.5-flash-exp",
        max_retrieval_docs: int = 5
    ):
        """
        Initialize the RAG system with user-specific vector database.
        
        Args:
            user_id: User ID for user-specific vector database
            base_vector_path: Base path for vector databases
            google_api_key: Google API key for embeddings and chat
            embedding_model: Model for text embeddings
            chat_model: Model for chat completion
            max_retrieval_docs: Maximum number of documents to retrieve
        """
        self.user_id = user_id
        self.base_vector_path = base_vector_path
        
        # Create user-specific paths
        self.vector_db_path = os.path.join(base_vector_path, f"user_{user_id}_vector_db")
        self.collection_name = f"user_{user_id}_diary_entries"
        self.max_retrieval_docs = max_retrieval_docs
        
        # Ensure user vector database directory exists
        os.makedirs(self.vector_db_path, exist_ok=True)
        
        # Set up Google API key
        if google_api_key:
            os.environ["GOOGLE_API_KEY"] = google_api_key
        elif not os.getenv("GOOGLE_API_KEY"):
            raise ValueError("Google API key must be provided either as parameter or environment variable")
        
        # Initialize embedding and chat models
        try:
            # Fix for Streamlit event loop issue
            import asyncio
            import nest_asyncio
            
            # Allow nested event loops for Streamlit compatibility
            try:
                nest_asyncio.apply()
            except:
                pass
                
            # Set event loop for thread if not exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            self.embeddings = GoogleGenerativeAIEmbeddings(model=embedding_model)
            self.chat_model = ChatGoogleGenerativeAI(
                model=chat_model,
                temperature=0.3,  # Lower temperature for faster, more focused responses
                max_tokens=800,   # Shorter responses for speed
                top_k=20,        # Limit token choices for speed
                top_p=0.8        # Nucleus sampling for faster generation
            )
            logger.info(f"Initialized embeddings with model: {embedding_model}")
            logger.info(f"Initialized chat model: {chat_model}")
        except Exception as e:
            logger.error(f"Failed to initialize models: {str(e)}")
            raise
        
        # Initialize vector store
        self.vector_store = None
        self._setup_vector_store()
        
        # Set up prompt templates
        self._setup_prompts()
        
        # Initialize conversation chain
        self._setup_conversation_chain()
    
    def _setup_vector_store(self):
        """Set up connection to the vector database."""
        try:
            if os.path.exists(self.vector_db_path):
                self.vector_store = Chroma(
                    persist_directory=self.vector_db_path,
                    embedding_function=self.embeddings,
                    collection_name=self.collection_name
                )
                collection_info = self.vector_store._collection.count()
                logger.info(f"Connected to vector database (primary) with {collection_info} documents")
                # Fallback: legacy nested path if empty
                if collection_info == 0:
                    nested_path = os.path.join(self.vector_db_path, os.path.basename(self.vector_db_path))
                    if os.path.isdir(nested_path):
                        try:
                            nested_vs = Chroma(
                                persist_directory=nested_path,
                                embedding_function=self.embeddings,
                                collection_name=self.collection_name
                            )
                            nested_count = nested_vs._collection.count()
                            if nested_count > 0:
                                logger.warning(
                                    f"Primary path empty. Switching to legacy nested path {nested_path} with {nested_count} docs"
                                )
                                self.vector_store = nested_vs
                                self.vector_db_path = nested_path
                        except Exception as ne:
                            logger.debug(f"Failed to read nested path: {ne}")
            else:
                logger.warning(f"Vector database not found at {self.vector_db_path}")
                logger.info("Run indexing pipeline first.")
        except Exception as e:
            logger.error(f"Failed to setup vector store: {str(e)}")
            self.vector_store = None

    def reload_vector_store(self) -> int:
        """Reload vector store from disk. Returns new document count or 0."""
        try:
            self._setup_vector_store()
            if self.vector_store:
                return self.vector_store._collection.count()
        except Exception as e:
            logger.warning(f"reload_vector_store failed: {e}")
        return 0

    def get_document_count(self) -> int:
        try:
            if self.vector_store:
                return self.vector_store._collection.count()
        except Exception:
            pass
        return 0
    
    def _setup_prompts(self):
        """Set up prompt templates for different scenarios."""
        
        # Main RAG prompt template
        self.rag_prompt = ChatPromptTemplate.from_template("""
Bạn là một trợ lý AI thông minh và thấu hiểu, chuyên về việc phân tích và thảo luận nội dung về nhật ký cá nhân.

Dựa trên các mục nhật ký sau đây được tìm kiếm từ cơ sở dữ liệu:

{context}

Người dùng hỏi: {question}

Hãy trả lời một cách:
- Thấu hiểu và empathetic (đồng cảm)
- Dựa trên nội dung nhật ký được cung cấp
- Cung cấp insights và connections giữa các entries
- Đưa ra suggestions hoặc reflections nếu phù hợp
- Sử dụng tiếng Việt tự nhiên và ấm áp

Nếu không tìm thấy thông tin liên quan trong nhật ký, hãy thành thật nói và đề xuất các cách khác để giúp đỡ.

Trả lời:
""")
        
        # Fallback prompt when no relevant documents found
        self.fallback_prompt = ChatPromptTemplate.from_template("""
Bạn là một trợ lý AI thân thiện và hữu ích cho việc quản lý nhật ký cá nhân.

Người dùng hỏi: {question}

Vì không tìm thấy thông tin liên quan trong nhật ký hiện tại, hãy:
- Trả lời một cách thân thiện ngắn gọn và hữu ích
- Đề xuất cách người dùng có thể ghi nhật ký về chủ đề này
- Khuyến khích reflection và self-discovery
- Cung cấp general guidance nếu phù hợp

Sử dụng tiếng Việt tự nhiên và ấm áp.

Trả lời:
""")
        
        # Summary prompt for multiple diary entries
        self.summary_prompt = ChatPromptTemplate.from_template("""
Dựa trên các mục nhật ký sau đây:

{context}

Hãy tạo một summary ngắn gọn về:
- Chủ đề chính được đề cập
- Cảm xúc và mood tổng thể
- Patterns hoặc themes đáng chú ý
- Insights về personal growth

Sử dụng tiếng Việt và giữ tính cách empathetic.

Summary:
""")
    
    def _setup_conversation_chain(self):
        """Set up the conversation chain for RAG processing."""
        try:
            # Create retriever from vector store
            if self.vector_store:
                self.retriever = self.vector_store.as_retriever(
                    search_kwargs={"k": self.max_retrieval_docs}
                )
                
                # Set up the main RAG chain
                self.rag_chain = (
                    {
                        "context": self.retriever | self._format_docs,
                        "question": RunnablePassthrough()
                    }
                    | self.rag_prompt
                    | self.chat_model
                    | StrOutputParser()
                )
                
                # Set up fallback chain
                self.fallback_chain = (
                    {"question": RunnablePassthrough()}
                    | self.fallback_prompt
                    | self.chat_model
                    | StrOutputParser()
                )
                
                logger.info("Conversation chain setup complete")
            else:
                logger.warning("Cannot setup conversation chain without vector store")
                
        except Exception as e:
            logger.error(f"Failed to setup conversation chain: {str(e)}")
            raise
    
    def _format_docs(self, docs: List[Document]) -> str:
        """
        Format retrieved documents for LLM consumption.
        
        Args:
            docs: List of retrieved documents
            
        Returns:
            Formatted string with document content and metadata
        """
        if not docs:
            return "Không tìm thấy mục nhật ký liên quan."
        
        formatted_docs = []
        for i, doc in enumerate(docs, 1):
            # Extract metadata
            metadata = doc.metadata
            date = metadata.get('date', 'Unknown date')
            title = metadata.get('title', 'Untitled')
            tags = metadata.get('tags_list', metadata.get('tags', ''))
            
            # Format document
            doc_text = f"""
Mục {i}:
Ngày: {date}
Tiêu đề: {title}
Tags: {tags if tags else 'Không có tags'}
Nội dung: {doc.page_content.strip()}
---
"""
            formatted_docs.append(doc_text)
        
        return "\n".join(formatted_docs)
    
    def retrieve_relevant_entries(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        k: Optional[int] = None
    ) -> List[Document]:
        """
        Retrieve relevant diary entries based on query with optimized performance.
        
        Args:
            query: Search query
            filters: Optional metadata filters
            k: Number of documents to retrieve (overrides default)
            
        Returns:
            List of relevant documents
        """
        if not self.vector_store:
            logger.warning("Vector store not available for retrieval")
            return []
        
        try:
            # Use smaller k for faster response
            k = k or min(self.max_retrieval_docs, 3)  # Limit to 3 docs for speed
            
            if filters:
                docs = self.vector_store.similarity_search(
                    query=query,
                    k=k,
                    filter=filters
                )
            else:
                docs = self.vector_store.similarity_search(
                    query=query,
                    k=k
                )
            
            logger.info(f"Retrieved {len(docs)} documents for query: '{query[:50]}...'")
            return docs
            
        except Exception as e:
            logger.error(f"Error during retrieval: {str(e)}")
            return []
    
    def format_documents_for_context(self, docs: List[Document]) -> str:
        """
        Format retrieved documents into context string for the prompt.
        
        Args:
            docs: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        if not docs:
            return "Không có thông tin nhật ký liên quan."
        
        formatted_docs = []
        for i, doc in enumerate(docs, 1):
            # Extract metadata
            metadata = doc.metadata
            date = metadata.get('date', 'Không có ngày')
            source = metadata.get('source', 'Không rõ nguồn')
            
            # Format document
            doc_text = f"Nhật ký {i} (Ngày: {date}):\n{doc.page_content}"
            formatted_docs.append(doc_text)
        
        return "\n\n".join(formatted_docs)
    
    def generate_fast_response(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate fast response with optimized settings for speed.
        
        Args:
            query: User question
            filters: Optional metadata filters
            
        Returns:
            AI response string (optimized for speed)
        """
        try:
            # Fast retrieval with only 2 most relevant docs
            relevant_docs = self.retrieve_relevant_entries(
                query=query, 
                filters=filters,
                k=2  # Only 2 docs for maximum speed
            )
            
            if not relevant_docs:
                return self.fallback_chain.invoke(query)
            
            # Create concise context
            context = self.format_documents_for_context(relevant_docs[:2])  # Only use top 2
            
            # Fast prompt template
            fast_prompt = ChatPromptTemplate.from_template(
                """Dựa vào thông tin nhật ký sau, trả lời ngắn gọn và súc tích:

{context}

Câu hỏi: {question}

Trả lời ngắn (1-2 câu):"""
            )
            
            # Create optimized chain
            chain = (
                {"context": lambda x: context, "question": RunnablePassthrough()}
                | fast_prompt
                | self.chat_model
                | StrOutputParser()
            )
            
            # Generate response
            response = chain.invoke(query)
            logger.info("Generated fast response successfully")
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error in fast response generation: {str(e)}")
            return self.fallback_chain.invoke(query)

    def generate_response(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        use_fallback: bool = False
    ) -> str:
        """
        Generate a response to user query using RAG.
        
        Args:
            query: User's question or message
            filters: Optional metadata filters for retrieval
            use_fallback: Whether to use fallback response (no retrieval)
            
        Returns:
            Generated response
        """
        try:
            if use_fallback or not self.vector_store:
                # Use fallback chain without retrieval
                response = self.fallback_chain.invoke(query)
                logger.info("Generated fallback response")
                return response
            
            # Retrieve relevant documents first
            relevant_docs = self.retrieve_relevant_entries(query, filters)
            
            if not relevant_docs:
                # No relevant documents found, use fallback
                response = self.fallback_chain.invoke(query)
                logger.info("No relevant docs found, used fallback response")
                return response
            
            # Use RAG chain with retrieved context
            response = self.rag_chain.invoke(query)
            logger.info("Generated RAG response with context")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Xin lỗi, tôi gặp lỗi khi xử lý câu hỏi của bạn: {str(e)}"
    
    def generate_summary(self, date_range: Optional[Tuple[str, str]] = None) -> str:
        """
        Generate a summary of diary entries.
        
        Args:
            date_range: Optional tuple of (start_date, end_date) in YYYY-MM-DD format
            
        Returns:
            Generated summary
        """
        try:
            if not self.vector_store:
                return "Không thể tạo summary: vector database không khả dụng."
            
            # Build filter for date range if provided
            filters = {}
            if date_range:
                start_date, end_date = date_range
                # Note: This depends on how dates are stored in metadata
                # May need adjustment based on actual metadata structure
                pass
            
            # Retrieve documents for summary (more documents for better overview)
            docs = self.vector_store.similarity_search(
                query="nhật ký cảm xúc thoughts feelings",  # General query
                k=min(10, self.max_retrieval_docs * 2)  # More docs for summary
            )
            
            if not docs:
                return "Không tìm thấy nhật ký để tạo summary."
            
            # Format context for summary
            context = self._format_docs(docs)
            
            # Generate summary
            summary_chain = (
                {"context": lambda x: context}
                | self.summary_prompt
                | self.chat_model
                | StrOutputParser()
            )
            
            summary = summary_chain.invoke({})
            logger.info("Generated diary summary")
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return f"Lỗi khi tạo summary: {str(e)}"
    
    def search_by_tags(self, tags: List[str], k: int = 5) -> List[Document]:
        """
        Search diary entries by specific tags.
        
        Args:
            tags: List of tags to search for
            k: Number of documents to return
            
        Returns:
            List of documents matching the tags
        """
        if not self.vector_store or not tags:
            return []
        
        try:
            # Build tag query
            tag_query = " ".join([f"#{tag}" for tag in tags])
            
            # Search with tag-based query
            docs = self.vector_store.similarity_search(
                query=tag_query,
                k=k
            )
            
            # Filter by tags in metadata if available
            filtered_docs = []
            for doc in docs:
                doc_tags = doc.metadata.get('tags_list', '')
                if any(tag.lower() in doc_tags.lower() for tag in tags):
                    filtered_docs.append(doc)
            
            logger.info(f"Found {len(filtered_docs)} documents with tags: {tags}")
            return filtered_docs
            
        except Exception as e:
            logger.error(f"Error searching by tags: {str(e)}")
            return []
    
    def get_conversation_context(self, chat_history: List[Dict[str, str]]) -> str:
        """
        Process chat history to maintain conversation context.
        
        Args:
            chat_history: List of chat messages with 'role' and 'content'
            
        Returns:
            Formatted conversation context
        """
        if not chat_history:
            return ""
        
        # Take last few messages for context
        recent_messages = chat_history[-5:]  # Last 5 messages
        
        context_parts = []
        for msg in recent_messages:
            role = "Người dùng" if msg['role'] == 'user' else "Trợ lý"
            context_parts.append(f"{role}: {msg['content']}")
        
        return "\n".join(context_parts)
    
    def generate_contextual_response(
        self, 
        query: str, 
        chat_history: List[Dict[str, str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate response with conversation context.
        
        Args:
            query: Current user query
            chat_history: Previous conversation messages
            filters: Optional metadata filters
            
        Returns:
            Contextual response
        """
        # Get conversation context
        conv_context = self.get_conversation_context(chat_history or [])
        
        # Enhance query with conversation context
        if conv_context:
            enhanced_query = f"Bối cảnh cuộc trò chuyện:\n{conv_context}\n\nCâu hỏi hiện tại: {query}"
        else:
            enhanced_query = query
        
        # Generate response
        return self.generate_response(enhanced_query, filters)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the RAG system.
        
        Returns:
            Dictionary with system status information
        """
        status = {
            "vector_store_available": self.vector_store is not None,
            "vector_db_path": self.vector_db_path,
            "models_initialized": True,
            "embedding_model": "models/embedding-001",
            "chat_model": "gemini-2.0-flash-exp"
        }
        
        if self.vector_store:
            try:
                doc_count = self.vector_store._collection.count()
                status["document_count"] = doc_count
                status["vector_store_healthy"] = True
            except Exception as e:
                status["vector_store_healthy"] = False
                status["vector_store_error"] = str(e)
        else:
            status["document_count"] = 0
            status["vector_store_healthy"] = False
        
        return status

# ========================================
# CONVENIENCE FUNCTIONS
# ========================================

def create_rag_system(
    user_id: int = 1,
    base_vector_path: str = "./src/Indexingstep",
    google_api_key: Optional[str] = None
) -> DiaryRAGSystem:
    """
    Create and initialize a user-specific DiaryRAGSystem instance.
    
    Args:
        user_id: User ID for user-specific vector database
        base_vector_path: Base path for vector databases
        google_api_key: Google API key
        
    Returns:
        Initialized DiaryRAGSystem for the specific user
    """
    return DiaryRAGSystem(
        user_id=user_id,
        base_vector_path=base_vector_path,
        google_api_key=google_api_key
    )

def quick_query(
    query: str, 
    user_id: int = 1,
    base_vector_path: str = "./src/VectorDB"
) -> str:
    """
    Quick query function for testing with user-specific database.
    
    Args:
        query: Question to ask
        user_id: User ID for user-specific vector database
        base_vector_path: Base path for vector databases
        
    Returns:
        Response string
    """
    try:
        rag = create_rag_system(user_id, base_vector_path)
        return rag.generate_response(query)
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    # Example usage
    print("🤖 Diary RAG System - Example Usage")
    print("=" * 50)
    
    try:
        # Initialize system
        rag = create_rag_system()
        
        # Health check
        status = rag.health_check()
        print("System Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # Example queries
        if status.get("vector_store_healthy"):
            print("\n📝 Example Queries:")
            
            queries = [
                "Tôi cảm thấy như thế nào trong tuần này?",
                "Có những hoạt động nào tôi đã làm gần đây?",
                "Tâm trạng của tôi đã thay đổi như thế nào?"
            ]
            
            for query in queries:
                print(f"\n❓ Query: {query}")
                response = rag.generate_response(query)
                print(f"🤖 Response: {response[:200]}...")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Make sure to:")
        print("1. Set GOOGLE_API_KEY environment variable")
        print("2. Run the indexing pipeline first")
        print("3. Check vector database path")

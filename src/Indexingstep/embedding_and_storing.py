from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from typing import List, Optional, Dict, Any
import os
import logging
from pathlib import Path
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiaryEmbeddingAndStorage:
    """
    Class for embedding diary documents and storing them in Chroma vector database.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        persist_directory: str = "./chroma_db",
        collection_name: str = "diary_collection",
        embedding_model: str = "models/embedding-001",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        Initialize the embedding and storage system.
        
        Args:
            api_key (str, optional): Google API key for embeddings
            persist_directory (str): Directory to persist the vector database
            collection_name (str): Name of the Chroma collection
            embedding_model (str): Google embedding model to use
            chunk_size (int): Size of text chunks for embedding
            chunk_overlap (int): Overlap between chunks
        """
        # Set up Google API key
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        elif "GOOGLE_API_KEY" not in os.environ:
            raise ValueError("Google API key must be provided either as parameter or environment variable")
        
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize embedding model
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=embedding_model
            )
            logger.info(f"Initialized Google embeddings with model: {embedding_model}")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise
        
        # Initialize or load existing vector store
        self.vector_store = None
        self._setup_vector_store()
    
    def _setup_vector_store(self):
        """Set up the Chroma vector store."""
        try:
            # Create persist directory if it doesn't exist
            Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
            
            # Initialize Chroma vector store
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            logger.info(f"Vector store initialized with persist directory: {self.persist_directory}")
            
        except Exception as e:
            logger.error(f"Failed to setup vector store: {e}")
            raise
    
    def embed_and_store_documents(self, documents: List[Document]) -> List[str]:
        """
        Embed and store documents in the vector database.
        
        Args:
            documents (List[Document]): List of LangChain Document objects
            
        Returns:
            List[str]: List of document IDs
        """
        if not documents:
            logger.warning("No documents provided for embedding")
            return []
        
        try:
            # Add documents to vector store
            document_ids = self.vector_store.add_documents(documents)
            
            # Persist the vector store
            self.vector_store.persist()
            
            logger.info(f"Successfully embedded and stored {len(documents)} documents")
            return document_ids
            
        except Exception as e:
            logger.error(f"Failed to embed and store documents: {e}")
            raise
    
    def embed_and_store_texts(
        self, 
        texts: List[str], 
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Embed and store raw texts in the vector database.
        
        Args:
            texts (List[str]): List of text strings
            metadatas (List[Dict], optional): List of metadata dictionaries
            
        Returns:
            List[str]: List of document IDs
        """
        if not texts:
            logger.warning("No texts provided for embedding")
            return []
        
        try:
            # Add texts to vector store
            document_ids = self.vector_store.add_texts(
                texts=texts,
                metadatas=metadatas
            )
            
            # Persist the vector store
            self.vector_store.persist()
            
            logger.info(f"Successfully embedded and stored {len(texts)} text documents")
            return document_ids
            
        except Exception as e:
            logger.error(f"Failed to embed and store texts: {e}")
            raise
    
    def similarity_search(
        self, 
        query: str, 
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Perform similarity search on stored documents.
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            filter (Dict, optional): Metadata filter
            
        Returns:
            List[Document]: List of similar documents
        """
        try:
            results = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter
            )
            
            logger.info(f"Found {len(results)} similar documents for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search: {e}")
            raise
    
    def similarity_search_with_score(
        self, 
        query: str, 
        k: int = 4,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[tuple]:
        """
        Perform similarity search with relevance scores.
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            filter (Dict, optional): Metadata filter
            
        Returns:
            List[tuple]: List of (Document, score) tuples
        """
        try:
            results = self.vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter
            )
            
            logger.info(f"Found {len(results)} similar documents with scores for query: '{query[:50]}...'")
            return results
            
        except Exception as e:
            logger.error(f"Failed to perform similarity search with scores: {e}")
            raise
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get information about the vector store collection.
        
        Returns:
            Dict: Collection information
        """
        try:
            collection = self.vector_store._collection
            count = collection.count()
            
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": self.persist_directory
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}
    
    def delete_documents(self, ids: List[str]) -> bool:
        """
        Delete documents by their IDs.
        
        Args:
            ids (List[str]): List of document IDs to delete
            
        Returns:
            bool: Success status
        """
        try:
            self.vector_store.delete(ids=ids)
            self.vector_store.persist()
            
            logger.info(f"Successfully deleted {len(ids)} documents")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False
    
    def delete_documents_by_metadata(self, filter_criteria: Dict[str, Any]) -> bool:
        """
        Delete documents based on metadata criteria.
        
        Args:
            filter_criteria (Dict): Metadata criteria to filter documents for deletion
            
        Returns:
            bool: Success status
        """
        try:
            collection = self.vector_store._collection
            
            # Get all documents with their metadata
            all_data = collection.get(include=['metadatas'])
            ids_to_delete = []
            
            # Find documents that match the criteria
            for i, metadata in enumerate(all_data['metadatas']):
                match = True
                for key, value in filter_criteria.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                
                if match:
                    ids_to_delete.append(all_data['ids'][i])
            
            if ids_to_delete:
                self.vector_store.delete(ids=ids_to_delete)
                self.vector_store.persist()
                logger.info(f"Successfully deleted {len(ids_to_delete)} documents matching criteria: {filter_criteria}")
                return True
            else:
                logger.info(f"No documents found matching criteria: {filter_criteria}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete documents by metadata: {e}")
            return False

    def clear_collection(self) -> bool:
        """
        Clear all documents from the collection.
        
        Returns:
            bool: Success status
        """
        try:
            # Get all document IDs and delete them
            collection = self.vector_store._collection
            all_ids = collection.get()['ids']
            
            if all_ids:
                self.vector_store.delete(ids=all_ids)
                self.vector_store.persist()
                logger.info(f"Cleared {len(all_ids)} documents from collection")
            else:
                logger.info("Collection is already empty")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
    
    def batch_process_documents(
        self, 
        documents: List[Document], 
        batch_size: int = 100
    ) -> List[str]:
        """
        Process documents in batches for large datasets.
        
        Args:
            documents (List[Document]): List of documents to process
            batch_size (int): Size of each batch
            
        Returns:
            List[str]: List of all document IDs
        """
        all_ids = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
            
            try:
                batch_ids = self.embed_and_store_documents(batch)
                all_ids.extend(batch_ids)
            except Exception as e:
                logger.error(f"Failed to process batch {i//batch_size + 1}: {e}")
                continue
        
        logger.info(f"Completed batch processing. Total documents processed: {len(all_ids)}")
        return all_ids

class EmbeddingDemo:
    def __init__(self, api_key=None):
        """Initialize the embedding model with Google API key."""
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001"
        )
    
    def embed_text(self, text):
        """Generate embedding for a single text."""
        return self.embeddings.embed_query(text)
    
    def embed_documents(self, documents):
        """Generate embeddings for multiple documents."""
        return self.embeddings.embed_documents(documents)
    
    def demonstrate(self):
        """Show basic embedding functionality."""
        sample_text = "This is a sample text for embedding."
        sample_docs = ["First document", "Second document", "Third document"]
        
        # Single text embedding
        text_embedding = self.embed_text(sample_text)
        print(f"Text embedding dimension: {len(text_embedding)}")
        
        # Multiple documents embedding
        doc_embeddings = self.embed_documents(sample_docs)
        print(f"Number of document embeddings: {len(doc_embeddings)}")
        print(f"Each embedding dimension: {len(doc_embeddings[0])}")

# Usage example
if __name__ == "__main__":
    # Initialize the embedding and storage system
    try:
        # You need to set your Google API key
        embedding_storage = DiaryEmbeddingAndStorage(
            api_key="your_google_api_key_here",  # Replace with your actual API key
            persist_directory="./diary_vector_db",
            collection_name="diary_entries"
        )
        
        # Example documents
        sample_documents = [
            Document(
                page_content="Today was a wonderful day. I went to the park and enjoyed the sunshine.",
                metadata={"date": "2024-01-15", "mood": "happy"}
            ),
            Document(
                page_content="Had a challenging day at work but learned a lot of new things.",
                metadata={"date": "2024-01-16", "mood": "productive"}
            ),
            Document(
                page_content="Spent time with family and friends. Made some great memories.",
                metadata={"date": "2024-01-17", "mood": "grateful"}
            )
        ]
        
        # Embed and store documents
        doc_ids = embedding_storage.embed_and_store_documents(sample_documents)
        print(f"Stored documents with IDs: {doc_ids}")
        
        # Get collection info
        info = embedding_storage.get_collection_info()
        print(f"Collection info: {info}")
        
        # Perform similarity search
        query = "happy day at the park"
        results = embedding_storage.similarity_search(query, k=2)
        
        print(f"\nSimilarity search results for '{query}':")
        for i, doc in enumerate(results):
            print(f"Result {i+1}: {doc.page_content[:100]}...")
            print(f"Metadata: {doc.metadata}")
        
        # Search with scores
        scored_results = embedding_storage.similarity_search_with_score(query, k=2)
        
        print(f"\nSimilarity search with scores:")
        for doc, score in scored_results:
            print(f"Score: {score:.4f} - {doc.page_content[:50]}...")
        
    except Exception as e:
        print(f"Error in example: {e}")
        
    # Original demo
    # demo = EmbeddingDemo(api_key="your_google_api_key_here")
    # demo.demonstrate()
# RAG Architecture - Personal Diary Chatbot

## 🏗️ Tổng quan kiến trúc RAG

Kiến trúc RAG (Retrieval-Augmented Generation) trong dự án này được thiết kế để cung cấp khả năng tìm kiếm và trả lời thông minh dựa trên dữ liệu nhật ký cá nhân của người dùng.

## 🔄 Luồng xử lý RAG

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Input Query   │───►│   Query         │───►│   Vector        │
│   (User Question)│    │   Processing    │    │   Search        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Final Answer  │◄───│   Answer        │◄───│   Context       │
│   (Response)    │    │   Generation    │    │   Retrieval     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📊 Chi tiết các thành phần

### 1. Data Ingestion & Indexing

#### 1.1 Document Loading
- **Input formats**: PDF, DOCX, TXT
- **Processing**: Text extraction, cleaning, normalization
- **Output**: Structured text data

#### 1.2 Text Chunking
```python
# Chunking strategy
chunk_size = 1000  # characters
chunk_overlap = 200  # characters
chunking_method = "recursive_character_splitter"
```

#### 1.3 Embedding Generation
- **Model**: Google Universal Sentence Encoder (USE)
- **Vector dimension**: 512
- **Normalization**: L2 normalization
- **Storage**: ChromaDB vector database

### 2. Vector Database Architecture

#### 2.1 ChromaDB Configuration
```python
# Database settings
collection_name = f"user_{user_id}_diary"
metadata = {
    "user_id": user_id,
    "source": "diary_entry",
    "date": entry_date,
    "chunk_id": chunk_id
}
```

#### 2.2 Index Structure
- **Primary key**: `user_id + chunk_id`
- **Vector index**: HNSW (Hierarchical Navigable Small World)
- **Distance metric**: Cosine similarity
- **Sharding**: Per-user collections

### 3. Retrieval Engine

#### 3.1 Query Processing
```python
# Query preprocessing
def process_query(query: str):
    # 1. Text cleaning
    # 2. Stop word removal
    # 3. Lemmatization
    # 4. Query expansion
    return processed_query
```

#### 3.2 Vector Search
- **Search algorithm**: K-Nearest Neighbors (KNN)
- **Top-k results**: 5-10 most relevant chunks
- **Similarity threshold**: 0.7 (cosine similarity)
- **Reranking**: Semantic relevance scoring

#### 3.3 Context Assembly
```python
# Context building
def build_context(retrieved_chunks, query):
    # 1. Sort by relevance score
    # 2. Remove duplicates
    # 3. Truncate to token limit
    # 4. Add metadata context
    return final_context
```

### 4. Generation Engine

#### 4.1 LLM Integration
- **Primary model**: OpenAI GPT-3.5/4
- **Fallback model**: Local model (nếu cần)
- **Temperature**: 0.7 (balanced creativity)
- **Max tokens**: 500 (response length)

#### 4.2 Prompt Engineering
```python
# System prompt template
SYSTEM_PROMPT = """
You are a helpful AI assistant that answers questions about personal diary entries.
Use only the provided context to answer questions.
If the information is not in the context, say so.
Be conversational but professional.
"""
```

#### 4.3 Response Generation
```python
# Generation pipeline
def generate_response(query, context, chat_history):
    # 1. Build prompt with context
    # 2. Call LLM API
    # 3. Post-process response
    # 4. Validate against context
    # 5. Return final answer
```

## 🔧 Cấu hình kỹ thuật

### Performance Tuning

#### 1. Chunking Optimization
- **Optimal chunk size**: 1000 characters
- **Overlap ratio**: 20%
- **Chunking strategy**: Recursive character splitter

#### 2. Vector Search Optimization
- **Index type**: HNSW
- **Search parameters**: 
  - `ef_construction`: 200
  - `ef_search`: 100
  - `m`: 16

#### 3. Caching Strategy
- **Query cache**: Redis (in-memory)
- **Embedding cache**: Local file cache
- **Response cache**: TTL-based expiration

### Scalability Features

#### 1. Multi-User Support
- **User isolation**: Separate vector collections
- **Resource management**: Per-user memory limits
- **Concurrent access**: Async processing

#### 2. Horizontal Scaling
- **Load balancing**: Multiple RAG instances
- **Database sharding**: User-based distribution
- **Microservices**: Modular architecture

## 📈 Monitoring & Analytics

### 1. Performance Metrics
- **Query latency**: < 2 seconds
- **Retrieval accuracy**: > 85%
- **Generation quality**: User satisfaction score
- **System throughput**: Queries per second

### 2. Quality Assurance
- **Context relevance**: Similarity score tracking
- **Answer accuracy**: Human evaluation
- **User feedback**: Rating system
- **A/B testing**: Model comparison

## 🚀 Deployment Architecture

### 1. Development Environment
```
┌─────────────────┐    ┌─────────────────┐
│   Local Python │    │   Local         │
│   Environment  │◄──►│   ChromaDB      │
└─────────────────┘    └─────────────────┘
```

### 2. Production Environment
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer│    │   RAG Service   │    │   Vector DB     │
│   (Nginx)      │◄──►│   (FastAPI)     │◄──►│   (ChromaDB)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Redis Cache   │
                       └─────────────────┘
```

## 🔒 Security & Privacy

### 1. Data Protection
- **User isolation**: Strict separation of data
- **Encryption**: At-rest and in-transit
- **Access control**: Role-based permissions
- **Audit logging**: Complete access history

### 2. Privacy Compliance
- **GDPR compliance**: Data portability
- **Data retention**: Configurable policies
- **User consent**: Explicit permission management
- **Data anonymization**: Optional features

## 🧪 Testing Strategy

### 1. Unit Testing
- **Component testing**: Individual modules
- **Mock testing**: External API simulation
- **Coverage target**: > 90%

### 2. Integration Testing
- **End-to-end testing**: Complete RAG pipeline
- **Performance testing**: Load and stress tests
- **Security testing**: Vulnerability assessment


## 📚 Best Practices

### 1. Model Selection
- **Embedding models**: Domain-specific fine-tuning
- **LLM selection**: Cost-performance balance
- **Fallback strategies**: Graceful degradation

### 2. Data Quality
- **Input validation**: Strict data checking
- **Cleaning pipeline**: Automated preprocessing
- **Quality metrics**: Continuous monitoring

### 3. Error Handling
- **Graceful failures**: User-friendly error messages
- **Retry mechanisms**: Automatic recovery
- **Logging**: Comprehensive error tracking

## 🔮 Future Enhancements

### 1. Advanced Features
- **Multi-modal RAG**: Image and text processing
- **Temporal reasoning**: Time-based queries
- **Emotional analysis**: Sentiment-aware responses

### 2. Performance Improvements
- **Vector quantization**: Reduced memory usage
- **Approximate search**: Faster retrieval
- **Model distillation**: Smaller, faster models

### 3. Integration Capabilities
- **API ecosystem**: Third-party integrations
- **Mobile applications**: Native mobile support
- **Voice interface**: Speech-to-text integration

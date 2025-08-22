# Backend Architecture - Personal Diary Chatbot

## Tổng quan Backend

Backend của dự án được xây dựng trên nền tảng FastAPI, cung cấp API RESTful cho việc xử lý nhật ký, tìm kiếm và tương tác với chatbot RAG. Hệ thống được thiết kế theo kiến trúc microservices với khả năng mở rộng cao.

## 🏛️ Kiến trúc tổng thể

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   Core Services │
│   (Streamlit)   │◄──►│   (FastAPI)     │◄──►│   (RAG Engine)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Data Layer    │
                       │   (Vector DB)   │
                       └─────────────────┘
```

## 🔧 Cấu trúc thư mục Backend

```
src/
├── rag_service/                 # FastAPI service
│   ├── main.py                  # Main application entry point
│   ├── __init__.py
│   └── __pycache__/
├── Indexingstep/                # Data processing pipeline
│   ├── pipeline.py              # Main indexing pipeline
│   ├── dataloading.py           # Document loading utilities
│   ├── diary_text_splitter.py   # Text chunking logic
│   ├── embedding_and_storing.py # Vector embedding & storage
│   ├── database_utils.py        # Database operations
│   └── indexing_pipeline.py     # Pipeline orchestration
├── Retrivel_And_Generation/     # RAG core engine
│   ├── Retrieval_And_Generator.py # Main RAG system
│   └── __init__.py
├── VectorDB/                    # Vector database storage
└── streamlit_app/               # Frontend application
    ├── backend/                 # Backend utilities for UI
    ├── user_auth.py             # Authentication system
    ├── rag_client.py            # RAG service client
    └── interface.py             # Main UI interface
```
## 🔮 Future Enhancements

### 1. Microservices Architecture
- **User Service**: Dedicated user management
- **Document Service**: Document processing pipeline
- **Search Service**: Vector search optimization
- **Chat Service**: Conversation management

### 2. Advanced Features
- **Real-time synchronization**: WebSocket support
- **Multi-language support**: Internationalization
- **Advanced analytics**: User behavior tracking
- **Machine learning**: Continuous model improvement

### 3. Infrastructure Improvements
- **Kubernetes deployment**: Container orchestration
- **Service mesh**: Istio integration
- **Observability**: Distributed tracing
- **Auto-scaling**: Dynamic resource allocation

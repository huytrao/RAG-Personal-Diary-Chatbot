# Indexing Module - Refactored

This module handles the indexing pipeline for the Personal Diary Chatbot with clean code principles and better architecture.

## 🏗️ Architecture

The refactored indexing module follows clean code principles with separated concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Layer     │    │  Models Layer   │    │ Database Layer  │
│                 │    │                 │    │                 │
│ cli_user_       │    │ DiaryEntry      │    │ database_utils  │
│ indexing.py     │    │ DiaryChunk      │    │ repository.py   │
└─────────────────┘    │ IndexingConfig  │    └─────────────────┘
                       │ IndexingStats   │
                       └─────────────────┘
                               │
                       ┌─────────────────┐
                       │ Core Logic      │
                       │                 │
                       │ IndexingOrch-   │
                       │ estrator        │
                       │ sync_state.py   │
                       └─────────────────┘
```

## 📁 Files Structure

### Core Components

- **`models.py`**: Data models and configuration
  - `DiaryEntry`: Represents a diary entry
  - `DiaryChunk`: Represents a processed text chunk
  - `IndexingConfig`: Configuration object
  - `IndexingStats`: Statistics data structure

- **`database_utils.py`**: Database utilities and context managers
  - `open_db()`: Context manager for database connections
  - `ensure_database_exists()`: Database creation helper
  - `migrate_user_data()`: Data migration utilities

- **`repository.py`**: Data access layer
  - `DiaryRepository`: Handles all database operations
  - Clean separation of data access logic

- **`sync_state.py`**: Sync state management
  - `SyncStateStore`: Manages last processed timestamps
  - File-based state tracking (TODO: move to database)

- **`run_user_indexing.py`**: Main indexing orchestrator
  - `IndexingOrchestrator`: Coordinates the entire pipeline
  - Clean, focused responsibilities

### Interface Layer

- **`cli_user_indexing.py`**: Command-line interface
  - User-friendly CLI with proper argument parsing
  - Separated from core logic for reusability

### Testing

- **`test_refactored.py`**: Unit tests for refactored components
  - Tests for models, database utils, repository, sync state

## 🚀 Usage

### Basic Commands

```bash
# Incremental indexing for user 1
python cli_user_indexing.py --user-id 1

# Full reindexing for user 2
python cli_user_indexing.py --user-id 2 --full-reindex

# Show statistics only
python cli_user_indexing.py --user-id 1 --stats-only

# Verbose logging
python cli_user_indexing.py --user-id 1 --verbose
```

### Advanced Configuration

```bash
# Custom chunk size and batch size
python cli_user_indexing.py --user-id 1 --chunk-size 1000 --chunk-overlap 150 --batch-size 100

# Custom database paths
python cli_user_indexing.py --user-id 1 --base-db-path /path/to/db --base-persist-dir /path/to/vectors
```

### Programmatic Usage

```python
from models import IndexingConfig
from run_user_indexing import IndexingOrchestrator

# Create configuration
config = IndexingConfig(
    user_id=1,
    google_api_key="your-api-key",
    chunk_size=800,
    batch_size=50
)

# Initialize orchestrator
orchestrator = IndexingOrchestrator(config)

# Run incremental indexing
success = orchestrator.run_incremental_indexing()

# Get statistics
stats = orchestrator.get_indexing_stats()
print(f"Processed {stats.vector_documents} documents")
```

## 🧪 Testing

Run the unit tests:

```bash
cd src/Indexingstep
python test_refactored.py
```

Run with verbose output:

```bash
python test_refactored.py -v
```

## 🔧 Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Google AI API key for embeddings (required for indexing)

### Configuration Options

All configuration is managed through the `IndexingConfig` class:

- `user_id`: User ID for isolation
- `google_api_key`: Google API key
- `base_db_path`: Base path for user databases
- `base_persist_directory`: Base directory for vector databases
- `embedding_model`: Google embedding model to use
- `chunk_size`: Size of text chunks (default: 800)
- `chunk_overlap`: Overlap between chunks (default: 100)
- `batch_size`: Processing batch size (default: 50)

## 📊 Statistics and Monitoring

The `--stats-only` command provides detailed information:

```
📊 Indexing Statistics for User 1
============================================================
👤 User ID:           1
📝 Database Entries:  150
🔍 Vector Documents:  423
🕐 Last Sync:         2025-08-20T14:30:00
📂 Vector DB Path:    ./user_1_vector_db
💾 Database Path:     ../streamlit_app/backend/VectorDatabase/user_1_diary.db
📊 Sync Status:       ✅ Well synced (94.7%)
============================================================
```

## 🔄 Migration from Legacy Code

The refactored code is backward compatible. The old `UserIsolatedIndexingPipeline` class functionality is now provided by `IndexingOrchestrator` with improved architecture.

### Key Improvements

1. **Separated Concerns**: Each component has a single responsibility
2. **Type Safety**: Proper data models instead of dictionaries
3. **Better Error Handling**: Specific exceptions and proper logging
4. **Testability**: Modular design allows for easy unit testing
5. **Configuration**: Centralized configuration management
6. **CLI Separation**: CLI logic separated from core business logic

## 🚧 TODO / Future Improvements

1. **Database-based Sync State**: Move from file-based to database-based sync tracking
2. **Retry Mechanisms**: Add retry logic for embedding API calls
3. **Metrics Collection**: Add performance metrics (processing time, token usage)
4. **Deduplication**: Implement content-based deduplication
5. **Background Processing**: Add support for async/background processing
6. **Health Checks**: Add health check endpoints for monitoring

## 🤝 Contributing

When contributing to this module:

1. Follow the existing architecture patterns
2. Add unit tests for new functionality
3. Update this README for significant changes
4. Use type hints for all new code
5. Follow the logging conventions (`[user={user_id}] message`)

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the correct directory
2. **Database Permissions**: Ensure write permissions for database directories
3. **API Key Issues**: Verify `GOOGLE_API_KEY` environment variable is set
4. **Memory Issues**: Reduce `batch_size` for large datasets

### Debug Mode

Use `--verbose` flag for detailed logging:

```bash
python cli_user_indexing.py --user-id 1 --verbose
```

This will show detailed debug information including:
- Database connection details
- Processing batch information
- API call details
- Error stack traces

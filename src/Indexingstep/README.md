# Diary Indexing Pipeline

This directory contains the complete indexing pipeline for the RAG Personal Diary Chatbot. The pipeline processes diary entries from a SQLite database, creates text embeddings, and stores them in a vector database for efficient similarity search.

## Overview

The indexing pipeline consists of four main components:

1. **Data Loading** (`dataloading.py`) - Loads diary entries from SQLite database
2. **Preprocessing** (`dataloading.py`) - Cleans and standardizes text content
3. **Text Splitting** (`Datasplitting.py`) - Splits documents into manageable chunks
4. **Embedding & Storage** (`embedding_and_storing.py`) - Generates embeddings and stores in vector database

## Files Structure

```
src/1. Indexingstep/
├── .env                    # Environment configuration
├── README.md              # This file
├── pipeline.py            # Main pipeline orchestrator
├── dataloading.py         # Data loading and preprocessing
├── Datasplitting.py       # Text splitting functionality
├── embedding_and_storing.py # Embedding generation and vector storage
├── run_indexing.py        # Command-line script to run pipeline
└── test_components.py     # Component testing script
```

## Setup

### 1. Install Dependencies

Ensure you have all required packages installed:

```bash
pip install streamlit fastapi uvicorn chromadb langchain-community langchain-google-genai langchain python-dotenv
```

### 2. Configure Environment

Edit the `.env` file with your configuration:

```env
# Google API Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Database Configuration
DATABASE_PATH=../streamlit_app/diary.db

# Vector Database Configuration
VECTOR_DB_PATH=./diary_vector_db
COLLECTION_NAME=diary_entries

# Embedding Configuration
EMBEDDING_MODEL=models/embedding-001
CHUNK_SIZE=800
CHUNK_OVERLAP=100
BATCH_SIZE=50
```

### 3. Get Google API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file

## Usage

### Option 1: Using the Command-Line Script (Recommended)

```bash
# Check configuration
python run_indexing.py --config-check

# Run full indexing pipeline
python run_indexing.py --mode full --clear-existing --show-stats --test-search

# Run incremental update for recent entries
python run_indexing.py --mode incremental --start-date 2024-08-01 --show-stats

# Index specific date range
python run_indexing.py --mode full --start-date 2024-01-01 --end-date 2024-12-31
```

#### Command-line Options:

- `--mode`: `full` or `incremental` indexing
- `--start-date`: Start date for processing (YYYY-MM-DD)
- `--end-date`: End date for processing (YYYY-MM-DD)
- `--clear-existing`: Clear existing vector database before indexing
- `--show-stats`: Display detailed statistics after indexing
- `--test-search`: Test search functionality after indexing
- `--config-check`: Only validate configuration and exit

### Option 2: Using the Pipeline Directly

```python
from pipeline import DiaryIndexingPipeline

# Initialize pipeline
pipeline = DiaryIndexingPipeline(
    db_path="../streamlit_app/diary.db",
    persist_directory="./diary_vector_db",
    collection_name="diary_entries",
    google_api_key="your_api_key_here",
    chunk_size=800,
    chunk_overlap=100
)

# Run full pipeline
results = pipeline.run_full_pipeline(clear_existing=True)

# Check results
if results["status"] == "completed_successfully":
    print(f"Indexed {results['documents_stored']} document chunks")
    
    # Test search
    search_results = pipeline.search_similar_entries("happy day", k=5)
    for doc in search_results:
        print(f"Found: {doc.page_content[:100]}...")
```

### Option 3: Component Testing

Before running the full pipeline, test individual components:

```bash
# Test all components (without embeddings)
python test_components.py

# Test with embeddings (requires API key)
python test_components.py --with-embeddings
```

## Pipeline Process

### 1. Data Loading
- Connects to SQLite database
- Loads diary entries with content and metadata
- Supports date range filtering
- Converts to LangChain Document format

### 2. Preprocessing
- Removes extra whitespace
- Normalizes line breaks
- Filters by content length
- Maintains document metadata

### 3. Text Splitting
- Splits long documents into smaller chunks
- Configurable chunk size and overlap
- Preserves document metadata across chunks
- Uses semantic separators (paragraphs)

### 4. Embedding & Storage
- Generates embeddings using Google's embedding model
- Stores in ChromaDB vector database
- Supports batch processing for large datasets
- Enables similarity search and filtering

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chunk_size` | 800 | Maximum characters per chunk |
| `chunk_overlap` | 100 | Character overlap between chunks |
| `batch_size` | 50 | Documents per batch for processing |
| `embedding_model` | `models/embedding-001` | Google embedding model |
| `collection_name` | `diary_entries` | ChromaDB collection name |

## Output

The pipeline creates:

1. **Vector Database**: ChromaDB collection with embedded diary chunks
2. **Log Files**: Detailed execution logs in `indexing.log`
3. **Statistics**: Database and vector store metrics

### Example Output:

```
======================================================================
INDEXING PIPELINE RESULTS
======================================================================
Status: COMPLETED_SUCCESSFULLY
Steps completed: 5/5
Documents loaded: 150
Documents preprocessed: 148
Chunks created: 342
Documents stored: 342
======================================================================

PIPELINE STATISTICS
==================================================
Database entries: 150
Database table: diary_entries
Vector store documents: 342
Collection name: diary_entries
Chunk size: 800
Chunk overlap: 100
Batch size: 50
==================================================
```

## Error Handling

The pipeline includes comprehensive error handling:

- **Database Connection**: Validates database existence and schema
- **API Key**: Checks for valid Google API key
- **Memory Management**: Processes large datasets in batches
- **Validation**: Validates configuration parameters
- **Recovery**: Continues processing even if individual documents fail

## Troubleshooting

### Common Issues:

1. **Database not found**
   ```
   FileNotFoundError: Database file not found: ../streamlit_app/diary.db
   ```
   - Check that the diary database exists
   - Verify the DATABASE_PATH in .env file

2. **Missing API key**
   ```
   ValueError: Google API key must be provided
   ```
   - Set GOOGLE_API_KEY in .env file
   - Get API key from Google AI Studio

3. **Empty results**
   ```
   No diary entries found in database
   ```
   - Check if diary database has entries
   - Verify table name is "diary_entries"
   - Check date range filters

4. **ChromaDB errors**
   ```
   Failed to setup vector store
   ```
   - Ensure ChromaDB is properly installed
   - Check write permissions for vector database directory
   - Clear existing database if corrupted

### Debug Mode:

Enable debug logging by modifying the logging level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Integration

The indexed data can be used by:

1. **RAG Pipeline** (`../rag_pipeline.py`) - For document retrieval
2. **Retriever** (`../retriever.py`) - For similarity search
3. **Web UI** (`../web_ui.py`) - For chatbot interactions

## Performance

### Indexing Speed:
- ~100-200 documents per minute (depends on document size)
- Batch processing reduces memory usage
- Parallel processing for large datasets

### Storage Requirements:
- ~1MB per 1000 document chunks
- Vector embeddings: 768 dimensions per chunk
- Metadata stored alongside embeddings

## Maintenance

### Regular Tasks:

1. **Incremental Updates**: Run daily/weekly for new entries
2. **Full Reindexing**: Run monthly or when configuration changes
3. **Database Cleanup**: Remove old vector data if needed
4. **Log Rotation**: Manage log file sizes

### Monitoring:

```bash
# Check indexing status
python run_indexing.py --show-stats

# Validate configuration
python run_indexing.py --config-check

# Test components
python test_components.py
```

## API Reference

See individual module documentation for detailed API references:

- [`DiaryDataLoader`](dataloading.py) - Database loading and preprocessing
- [`DataSplitting`](Datasplitting.py) - Text chunking functionality  
- [`DiaryEmbeddingAndStorage`](embedding_and_storing.py) - Embedding and vector storage
- [`DiaryIndexingPipeline`](pipeline.py) - Complete pipeline orchestration

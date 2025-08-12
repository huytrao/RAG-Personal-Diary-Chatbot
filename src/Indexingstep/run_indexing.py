#!/usr/bin/env python
"""
Script to run the complete diary indexing pipeline.
This script loads diary entries from the database, processes them, and stores embeddings.
"""

import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add the parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import DiaryIndexingPipeline
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('indexing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_environment_config():
    """Load configuration from environment variables."""
    # Load .env file
    load_dotenv()
    
    config = {
        "google_api_key": os.getenv("GOOGLE_API_KEY"),
        "db_path": os.getenv("DATABASE_PATH", "../streamlit_app/backend/diary.db"),
        "persist_directory": os.getenv("VECTOR_DB_PATH", "./diary_vector_db"),
        "collection_name": os.getenv("COLLECTION_NAME", "diary_entries"),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "models/embedding-001"),
        "chunk_size": int(os.getenv("CHUNK_SIZE", "800")),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "100")),
        "batch_size": int(os.getenv("BATCH_SIZE", "50"))
    }
    
    return config

def validate_config(config):
    """Validate the configuration."""
    errors = []
    
    # Check for required API key
    if not config["google_api_key"]:
        errors.append("GOOGLE_API_KEY is required. Please set it in the .env file.")
    
    # Check if database exists
    if not os.path.exists(config["db_path"]):
        errors.append(f"Database file not found: {config['db_path']}")
    
    # Validate numeric parameters
    if config["chunk_size"] <= 0:
        errors.append("CHUNK_SIZE must be a positive integer")
    
    if config["chunk_overlap"] < 0:
        errors.append("CHUNK_OVERLAP must be non-negative")
    
    if config["batch_size"] <= 0:
        errors.append("BATCH_SIZE must be a positive integer")
    
    return errors

def run_indexing_pipeline(config, args):
    """Run the complete indexing pipeline."""
    try:
        # Initialize pipeline
        logger.info("Initializing Diary Indexing Pipeline...")
        pipeline = DiaryIndexingPipeline(
            db_path=config["db_path"],
            persist_directory=config["persist_directory"],
            collection_name=config["collection_name"],
            google_api_key=config["google_api_key"],
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
            embedding_model=config["embedding_model"],
            batch_size=config["batch_size"]
        )
        
        # Run pipeline based on mode
        if args.mode == "full":
            logger.info("Running full indexing pipeline...")
            results = pipeline.run_full_pipeline(
                start_date=args.start_date,
                end_date=args.end_date,
                clear_existing=args.clear_existing
            )
        elif args.mode == "incremental":
            if not args.start_date:
                raise ValueError("Start date is required for incremental mode")
            logger.info("Running incremental update...")
            results = pipeline.incremental_update(
                start_date=args.start_date,
                end_date=args.end_date
            )
        else:
            raise ValueError(f"Unknown mode: {args.mode}")
        
        # Display results
        print_results(results)
        
        # Get and display statistics
        if args.show_stats:
            display_stats(pipeline)
        
        # Test search if requested
        if args.test_search:
            test_search_functionality(pipeline)
        
        return results["status"] in ["completed_successfully", "success"]
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        return False

def print_results(results):
    """Print pipeline execution results."""
    print("\n" + "="*70)
    print("INDEXING PIPELINE RESULTS")
    print("="*70)
    
    if "status" in results:
        print(f"Status: {results['status'].upper()}")
    
    if "steps_completed" in results and "total_steps" in results:
        print(f"Steps completed: {results['steps_completed']}/{results['total_steps']}")
    
    if "documents_loaded" in results:
        print(f"Documents loaded: {results['documents_loaded']}")
    
    if "documents_preprocessed" in results:
        print(f"Documents preprocessed: {results['documents_preprocessed']}")
    
    if "chunks_created" in results:
        print(f"Chunks created: {results['chunks_created']}")
    
    if "documents_stored" in results:
        print(f"Documents stored: {results['documents_stored']}")
    
    if "documents_added" in results:
        print(f"Documents added: {results['documents_added']}")
    
    if results.get("errors"):
        print(f"Errors: {results['errors']}")
    
    print("="*70)

def display_stats(pipeline):
    """Display pipeline statistics."""
    try:
        stats = pipeline.get_pipeline_stats()
        
        print("\n" + "="*50)
        print("PIPELINE STATISTICS")
        print("="*50)
        
        # Database stats
        db_stats = stats.get("database", {})
        print(f"Database entries: {db_stats.get('row_count', 'N/A')}")
        print(f"Database table: {db_stats.get('table_name', 'N/A')}")
        
        # Vector store stats
        vector_stats = stats.get("vector_store", {})
        print(f"Vector store documents: {vector_stats.get('document_count', 'N/A')}")
        print(f"Collection name: {vector_stats.get('collection_name', 'N/A')}")
        
        # Pipeline config
        config_stats = stats.get("pipeline_config", {})
        print(f"Chunk size: {config_stats.get('chunk_size', 'N/A')}")
        print(f"Chunk overlap: {config_stats.get('chunk_overlap', 'N/A')}")
        print(f"Batch size: {config_stats.get('batch_size', 'N/A')}")
        
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error displaying stats: {str(e)}")

def test_search_functionality(pipeline):
    """Test the search functionality."""
    try:
        print("\n" + "="*50)
        print("TESTING SEARCH FUNCTIONALITY")
        print("="*50)
        
        # Test queries
        test_queries = [
            "happy day",
            "work meeting",
            "family time",
            "feeling sad",
            "good mood"
        ]
        
        for query in test_queries:
            results = pipeline.search_similar_entries(query, k=2)
            print(f"\nQuery: '{query}'")
            print(f"Found {len(results)} results:")
            
            for i, doc in enumerate(results):
                content_preview = doc.page_content[:80].replace('\n', ' ')
                print(f"  {i+1}. {content_preview}...")
                print(f"     Date: {doc.metadata.get('date', 'N/A')}")
        
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error testing search: {str(e)}")

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run diary indexing pipeline")
    
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="Indexing mode: full or incremental"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date for processing (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date for processing (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Clear existing vector database before indexing"
    )
    
    parser.add_argument(
        "--show-stats",
        action="store_true",
        help="Display detailed statistics after indexing"
    )
    
    parser.add_argument(
        "--test-search",
        action="store_true",
        help="Test search functionality after indexing"
    )
    
    parser.add_argument(
        "--config-check",
        action="store_true",
        help="Only check configuration and exit"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_environment_config()
    
    # Validate configuration
    validation_errors = validate_config(config)
    if validation_errors:
        print("Configuration errors:")
        for error in validation_errors:
            print(f"  - {error}")
        return False
    
    # If only checking config, exit here
    if args.config_check:
        print("Configuration is valid!")
        return True
    
    # Display configuration
    print("Configuration:")
    print(f"  Database: {config['db_path']}")
    print(f"  Vector DB: {config['persist_directory']}")
    print(f"  Collection: {config['collection_name']}")
    print(f"  Chunk size: {config['chunk_size']}")
    print(f"  Batch size: {config['batch_size']}")
    print(f"  Mode: {args.mode}")
    
    # Run the pipeline
    success = run_indexing_pipeline(config, args)
    
    if success:
        logger.info("Indexing pipeline completed successfully!")
        return True
    else:
        logger.error("Indexing pipeline failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/en# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models import IndexingConfig
from orchestrator import IndexingOrchestrator
import logging
"""
Command Line Interface for User-Isolated Indexing Pipeline

This module provides CLI functionality for the indexing system,
keeping the main logic separate and reusable.
"""

import argparse
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import IndexingConfig
from run_user_indexing import IndexingOrchestrator
import logging

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description='User-Isolated Diary Indexing Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli_user_indexing.py --user-id 1                    # Incremental indexing for user 1
  python cli_user_indexing.py --user-id 2 --full-reindex    # Full reindex for user 2
  python cli_user_indexing.py --user-id 1 --stats-only      # Show statistics only
        """
    )
    
    parser.add_argument('--user-id', type=int, default=1, 
                       help='User ID to process (default: 1)')
    parser.add_argument('--full-reindex', action='store_true', 
                       help='Perform full reindexing instead of incremental')
    parser.add_argument('--api-key', 
                       help='Google API key (or set GOOGLE_API_KEY env var)')
    parser.add_argument('--stats-only', action='store_true', 
                       help='Only show indexing statistics without processing')
    parser.add_argument('--base-db-path', default="../streamlit_app/backend/VectorDatabase", 
                       help='Base path for databases (default: ../streamlit_app/backend/VectorDatabase)')
    parser.add_argument('--base-persist-dir', default="./", 
                       help='Base directory for vector databases (default: ./)')
    parser.add_argument('--chunk-size', type=int, default=800,
                       help='Text chunk size (default: 800)')
    parser.add_argument('--chunk-overlap', type=int, default=100,
                       help='Text chunk overlap (default: 100)')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Processing batch size (default: 50)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    return parser


def configure_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('indexing_user.log'),
            logging.StreamHandler()
        ]
    )


def print_stats(stats, user_id: int):
    """Print indexing statistics in a formatted way."""
    print(f"\n📊 Indexing Statistics for User {user_id}")
    print("=" * 60)
    print(f"👤 User ID:           {stats.user_id}")
    print(f"📝 Database Entries:  {stats.database_entries}")
    print(f"🔍 Vector Documents:  {stats.vector_documents}")
    print(f"🕐 Last Sync:         {stats.last_sync or 'Never'}")
    print(f"📂 Vector DB Path:    {stats.vector_db_path}")
    print(f"💾 Database Path:     {stats.database_path}")
    
    if stats.error:
        print(f"❌ Error:            {stats.error}")
    
    # Calculate sync status
    if stats.database_entries > 0:
        sync_ratio = stats.vector_documents / stats.database_entries
        if sync_ratio >= 0.9:
            status = "✅ Well synced"
        elif sync_ratio >= 0.5:
            status = "⚠️  Partially synced"
        else:
            status = "❌ Needs sync"
        print(f"📊 Sync Status:       {status} ({sync_ratio:.1%})")
    
    print("=" * 60)


def main():
    """Main CLI function."""
    # Load environment variables
    load_dotenv()
    
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging
    configure_logging(args.verbose)
    
    # Get API key
    api_key = args.api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key and not args.stats_only:
        logger.error("Google API key is required for indexing operations. Set GOOGLE_API_KEY environment variable or use --api-key")
        print("\n💡 Tip: You can use --stats-only to check statistics without an API key")
        sys.exit(1)
    
    try:
        # Create configuration
        config = IndexingConfig(
            user_id=args.user_id,
            google_api_key=api_key or "dummy",  # Use dummy for stats-only
            base_db_path=args.base_db_path,
            base_persist_directory=args.base_persist_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            batch_size=args.batch_size
        )
        
        # Initialize orchestrator
        orchestrator = IndexingOrchestrator(config)
        
        if args.stats_only:
            # Show statistics only
            stats = orchestrator.get_indexing_stats()
            print_stats(stats, args.user_id)
        
        elif args.full_reindex:
            # Run full reindexing
            print(f"🔄 Starting full reindexing for user {args.user_id}...")
            success = orchestrator.run_full_reindexing()
            
            if success:
                print(f"✅ Full reindexing completed successfully for user {args.user_id}")
                stats = orchestrator.get_indexing_stats()
                print_stats(stats, args.user_id)
            else:
                print(f"❌ Full reindexing failed for user {args.user_id}")
                sys.exit(1)
        
        else:
            # Run incremental indexing
            print(f"📈 Starting incremental indexing for user {args.user_id}...")
            success = orchestrator.run_incremental_indexing()
            
            if success:
                print(f"✅ Incremental indexing completed successfully for user {args.user_id}")
                stats = orchestrator.get_indexing_stats()
                print_stats(stats, args.user_id)
            else:
                print(f"❌ Incremental indexing failed for user {args.user_id}")
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        print(f"\n❌ Pipeline execution failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

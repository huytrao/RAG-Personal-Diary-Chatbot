import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.Indexingstep.dataloading import DiaryDataLoader

# Test the data loader
loader = DiaryDataLoader(
    db_path="src/streamlit_app/backend/diary.db",
    table_name="diary_entries",
    content_column="content",
    date_column="date"
)

# Load documents
try:
    documents = loader.load()
    print(f"Successfully loaded {len(documents)} documents")
    
    for i, doc in enumerate(documents):
        print(f"\nDocument {i+1}:")
        print(f"Content: {doc.page_content}")
        print(f"Metadata: {doc.metadata}")
        
    # Get table info
    table_info = loader.get_table_info()
    print(f"\nTable info: {table_info}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

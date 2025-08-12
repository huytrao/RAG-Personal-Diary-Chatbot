import sqlite3
import sys
import os

# Navigate to backend directory
backend_path = "src/streamlit_app/backend/diary.db"
if not os.path.exists(backend_path):
    print(f"Database not found at: {backend_path}")
    # Try other locations
    possible_paths = [
        "diary.db",
        "src/streamlit_app/diary.db", 
        "src/streamlit_app/backend/diary.db"
    ]
    for path in possible_paths:
        if os.path.exists(path):
            backend_path = path
            print(f"Found database at: {path}")
            break
    else:
        print("Database not found in any expected location")
        sys.exit(1)

try:
    conn = sqlite3.connect(backend_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)
    
    # Check table structure
    if tables:
        table_name = tables[0][0]  # Get first table name
        cursor.execute(f"PRAGMA table_info({table_name});")
        structure = cursor.fetchall()
        print(f"Table '{table_name}' structure:", structure)
        
        # Check row count
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()
        print(f'Row count in {table_name}:', count)
        
        # Check sample data
        cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
        sample_data = cursor.fetchall()
        print(f'Sample data from {table_name}:', sample_data)
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")

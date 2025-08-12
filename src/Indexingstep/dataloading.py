import sqlite3
from typing import List, Optional
from langchain.schema import Document
from langchain.document_loaders.base import BaseLoader
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiaryDataLoader(BaseLoader):
    """
    Custom LangChain document loader for diary entries from SQLite database.
    """
    
    def __init__(
        self, 
        db_path: str,
        table_name: str = "diary_entries",
        content_column: str = "content",
        date_column: str = "date",
        # title_column: Optional[str] = None
    ):
        """
        Initialize the DiaryDataLoader.
        
        Args:
            db_path (str): Path to the SQLite database file
            table_name (str): Name of the table containing diary entries
            content_column (str): Name of the column containing diary content
            date_column (str): Name of the column containing entry dates
            title_column (str, optional): Name of the column containing entry titles
        """
        self.db_path = db_path
        self.table_name = table_name
        self.content_column = content_column
        self.date_column = date_column
        # self.title_column = title_column
    
    def _extract_content_from_structured_format(self, raw_content: str) -> tuple:
        """
        Extract actual content from structured format like:
        Title: xxxx
        Type: Text
        Content: actual content here
        
        Returns:
            tuple: (title, actual_content)
        """
        lines = raw_content.strip().split('\n')
        title = ""
        content = ""
        
        for line in lines:
            if line.startswith("Title: "):
                title = line.replace("Title: ", "").strip()
            elif line.startswith("Content: "):
                content = line.replace("Content: ", "").strip()
        
        # If no structured format found, return original content
        if not content:
            content = raw_content
            
        return title, content
    
    def load(self) -> List[Document]:
        """
        Load diary entries from the database and convert them to LangChain Documents.
        
        Returns:
            List[Document]: List of LangChain Document objects
        """
        documents = []
        
        try:
            # Connect to the SQLite database
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable accessing columns by name
            cursor = conn.cursor()
            
            # Build the SQL query
            columns = [self.content_column, self.date_column]
            # if self.title_column:
            #     columns.append(self.title_column)
            
            query = f"SELECT {', '.join(columns)} FROM {self.table_name}"
            
            # Execute the query
            cursor.execute(query)
            rows = cursor.fetchall()
            
            logger.info(f"Loaded {len(rows)} diary entries from database")
            
            # Convert each row to a LangChain Document
            for row in rows:
                raw_content = row[self.content_column]
                date = row[self.date_column]
                
                # Extract structured content
                title, actual_content = self._extract_content_from_structured_format(raw_content)
                
                # Create metadata for the document
                metadata = {
                    "source": self.db_path,
                    "date": date,
                    "type": "diary_entry"
                }
                
                # Add title to metadata if available
                if title:
                    metadata["title"] = title
                
                # Create Document object with actual content
                document = Document(
                    page_content=actual_content,
                    metadata=metadata
                )
                
                documents.append(document)
            
            conn.close()
            logger.info(f"Successfully converted {len(documents)} entries to Documents")
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading diary data: {e}")
            raise
        
        return documents
    
    def load_by_date_range(self, start_date: str, end_date: str) -> List[Document]:
        """
        Load diary entries within a specific date range.
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            List[Document]: Filtered list of Document objects
        """
        documents = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            columns = [self.content_column, self.date_column]
            # if self.title_column:
            #     columns.append(self.title_column)
            
            query = f"""
                SELECT {', '.join(columns)} 
                FROM {self.table_name} 
                WHERE {self.date_column} BETWEEN ? AND ?
                ORDER BY {self.date_column}
            """
            
            cursor.execute(query, (start_date, end_date))
            rows = cursor.fetchall()
            
            logger.info(f"Loaded {len(rows)} diary entries from {start_date} to {end_date}")
            
            for row in rows:
                raw_content = row[self.content_column]
                date = row[self.date_column]
                
                # Extract structured content
                title, actual_content = self._extract_content_from_structured_format(raw_content)
                
                metadata = {
                    "source": self.db_path,
                    "date": date,
                    "type": "diary_entry",
                    "date_range": f"{start_date}_to_{end_date}"
                }
                
                # Add title to metadata if available
                if title:
                    metadata["title"] = title
                
                document = Document(
                    page_content=actual_content,
                    metadata=metadata
                )
                
                documents.append(document)
            
            conn.close()
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading diary data by date range: {e}")
            raise
        
        return documents
    
    def get_table_info(self) -> dict:
        """
        Get information about the database table structure.
        
        Returns:
            dict: Table information including columns and row count
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({self.table_name})")
            columns = cursor.fetchall()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            row_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "table_name": self.table_name,
                "columns": [{"name": col[1], "type": col[2]} for col in columns],
                "row_count": row_count
            }
            
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise

class DiaryContentPreprocessor:
    """
    Preprocessor for diary content to clean and standardize text before indexing.
    """
    
    def __init__(
        self,
        remove_extra_whitespace: bool = True,
        normalize_line_breaks: bool = True,
        min_content_length: int = 10,
        max_content_length: Optional[int] = None
    ):
        """
        Initialize the content preprocessor.
        
        Args:
            remove_extra_whitespace (bool): Remove extra spaces and tabs
            normalize_line_breaks (bool): Normalize line breaks to single newlines
            min_content_length (int): Minimum content length to keep
            max_content_length (int, optional): Maximum content length to keep
        """
        self.remove_extra_whitespace = remove_extra_whitespace
        self.normalize_line_breaks = normalize_line_breaks
        self.min_content_length = min_content_length
        self.max_content_length = max_content_length
    
    def preprocess_content(self, content: str) -> str:
        """
        Preprocess diary content text.
        
        Args:
            content (str): Raw diary content
            
        Returns:
            str: Preprocessed content
        """
        if not content or not isinstance(content, str):
            return ""
        
        processed_content = content
        
        # Remove extra whitespace
        if self.remove_extra_whitespace:
            processed_content = ' '.join(processed_content.split())
        
        # Normalize line breaks
        if self.normalize_line_breaks:
            processed_content = processed_content.replace('\r\n', '\n').replace('\r', '\n')
            # Remove multiple consecutive newlines
            processed_content = re.sub(r'\n+', '\n', processed_content)
        
        # Strip leading/trailing whitespace
        processed_content = processed_content.strip()
        
        # Check length constraints
        if len(processed_content) < self.min_content_length:
            logger.warning(f"Content too short ({len(processed_content)} chars), skipping")
            return ""
        
        if self.max_content_length and len(processed_content) > self.max_content_length:
            logger.warning(f"Content too long ({len(processed_content)} chars), truncating")
            processed_content = processed_content[:self.max_content_length]
        
        return processed_content
    
    def preprocess_documents(self, documents: List[Document]) -> List[Document]:
        """
        Preprocess a list of Document objects.
        
        Args:
            documents (List[Document]): List of documents to preprocess
            
        Returns:
            List[Document]: List of preprocessed documents
        """
        preprocessed_docs = []
        
        for doc in documents:
            processed_content = self.preprocess_content(doc.page_content)
            
            # Skip empty content after preprocessing
            if not processed_content:
                continue
            
            # Create new document with processed content
            preprocessed_doc = Document(
                page_content=processed_content,
                metadata=doc.metadata.copy()
            )
            
            preprocessed_docs.append(preprocessed_doc)
        
        logger.info(f"Preprocessed {len(documents)} documents, kept {len(preprocessed_docs)}")
        return preprocessed_docs

# Example usage
if __name__ == "__main__":
    # Initialize the loader
    loader = DiaryDataLoader(
        db_path="../streamlit_app/backend/diary.db",
        table_name="diary_entries",
        content_column="content",
        date_column="date" #,
        # title_column="title"  
    )
    
    # Load all documents
    documents = loader.load()
    print(f"Loaded {len(documents)} diary entries")
    
    # Load documents by date range
    filtered_docs = loader.load_by_date_range("2024-01-01", "2026-12-31")
    print(f"Loaded {len(filtered_docs)} entries from 2024")
    
    # Get table information
    table_info = loader.get_table_info()
    print(f"Table info: {table_info}")

    # view document contents
    for doc in documents:
        print(f"Document content: {doc.page_content}")

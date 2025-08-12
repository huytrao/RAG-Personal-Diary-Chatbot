import sqlite3
from typing import List, Optional, Dict, Any
from langchain.schema import Document
from langchain.document_loaders.base import BaseLoader
import logging
import re
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiaryDataLoader(BaseLoader):
    """
    Custom LangChain document loader for diary entries from SQLite database.
    Enhanced with detailed metadata extraction for better indexing.
    """
    
    def __init__(
        self, 
        db_path: str,
        table_name: str = "diary_entries",
        content_column: str = "content",
        date_column: str = "date",
        tags_column: str = "tags",
        id_column: str = "id"
    ):
        """
        Initialize the DiaryDataLoader.
        
        Args:
            db_path (str): Path to the SQLite database file
            table_name (str): Name of the table containing diary entries
            content_column (str): Name of the column containing diary content
            date_column (str): Name of the column containing entry dates
            tags_column (str): Name of the column containing entry tags
            id_column (str): Name of the column containing entry IDs
        """
        self.db_path = db_path
        self.table_name = table_name
        self.content_column = content_column
        self.date_column = date_column
        self.tags_column = tags_column
        self.id_column = id_column
    
    def _extract_tags_from_content(self, content: str) -> List[str]:
        """
        Extract #tags from content string.
        
        Args:
            content: The diary content string
            
        Returns:
            List of tags found (without # symbol)
        """
        if not content:
            return []
        
        # Find all #tags in content
        tag_pattern = r'#(\w+(?:[_-]\w+)*)'
        matches = re.findall(tag_pattern, content, re.IGNORECASE)
        
        # Remove duplicates and return lowercase tags
        return list(set([tag.lower() for tag in matches]))
    
    def _extract_location_from_content(self, content: str) -> Optional[str]:
        """
        Extract location information from content using common patterns.
        
        Args:
            content: The diary content string
            
        Returns:
            Location string if found, None otherwise
        """
        if not content:
            return None
        
        # Common location patterns
        location_patterns = [
            r'at\s+([A-Z][a-zA-Z\s]+(?:Park|Beach|Mall|Store|Restaurant|Cafe|Office|Home|School|University))',
            r'in\s+([A-Z][a-zA-Z\s]+(?:City|District|Area|Street|Road))',
            r'went\s+to\s+([A-Z][a-zA-Z\s]+)',
            r'visited\s+([A-Z][a-zA-Z\s]+)',
            r'location:\s*([A-Za-z\s]+)',
            r'place:\s*([A-Za-z\s]+)'
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return None
    
    def _extract_people_from_content(self, content: str) -> List[str]:
        """
        Extract people/relationships mentioned in content.
        
        Args:
            content: The diary content string
            
        Returns:
            List of people/relationships mentioned
        """
        if not content:
            return []
        
        # Common relationship patterns
        people_patterns = [
            r'with\s+(my\s+)?(\w+(?:\s+\w+)?)',
            r'(mom|dad|mother|father|sister|brother|friend|colleague|boss|teacher)',
            r'(family|friends|team|colleagues)',
            r'met\s+([\w\s]+)',
            r'talked\s+to\s+([\w\s]+)'
        ]
        
        people = set()
        for pattern in people_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    for part in match:
                        if part.strip():
                            people.add(part.strip().lower())
                else:
                    people.add(match.strip().lower())
        
        # Filter out common words that are not people
        exclude_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        people = [p for p in people if p not in exclude_words and len(p) > 2]
        
        return list(people)
    
    def _get_day_of_week(self, date_str: str) -> str:
        """
        Get day of week from date string.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Day of week (e.g., 'Monday', 'Tuesday', etc.)
        """
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%A')
        except:
            return 'Unknown'
    
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
            
            # Build the SQL query with all required columns
            columns = [self.id_column, self.date_column, self.content_column, self.tags_column]
            
            query = f"SELECT {', '.join(columns)} FROM {self.table_name} ORDER BY {self.date_column} DESC"
            
            # Execute the query
            cursor.execute(query)
            rows = cursor.fetchall()
            
            logger.info(f"Loaded {len(rows)} diary entries from database")
            
            # Convert each row to a LangChain Document with enhanced metadata
            for row in rows:
                row_dict = dict(row) if hasattr(row, 'keys') else {
                    self.id_column: row[0],
                    self.date_column: row[1], 
                    self.content_column: row[2],
                    self.tags_column: row[3] if len(row) > 3 else ""
                }
                
                raw_content = row_dict[self.content_column]
                date = row_dict[self.date_column]
                entry_id = row_dict.get(self.id_column, "unknown")
                db_tags = row_dict.get(self.tags_column, "")
                
                # Extract structured content
                title, actual_content = self._extract_content_from_structured_format(raw_content)
                
                # Extract comprehensive metadata
                content_tags = self._extract_tags_from_content(actual_content)
                db_tag_list = [tag.strip() for tag in db_tags.split(',') if tag.strip()] if db_tags else []
                all_tags = list(set(content_tags + db_tag_list))  # Combine and deduplicate
                
                location = self._extract_location_from_content(actual_content)
                people = self._extract_people_from_content(actual_content)
                day_of_week = self._get_day_of_week(date)
                
                # Create comprehensive metadata for the document
                metadata = {
                    "source": self.db_path,
                    "entry_id": str(entry_id),
                    "date": date,
                    "day_of_week": day_of_week,
                    "type": "diary_entry",
                    "tags": all_tags,
                    "tag_count": len(all_tags),
                    "content_length": len(actual_content),
                    "word_count": len(actual_content.split())
                }
                
                # Add optional metadata if available
                if title:
                    metadata["title"] = title
                if location:
                    metadata["location"] = location
                if people:
                    metadata["people"] = people
                    metadata["people_count"] = len(people)
                
                # Add mood/sentiment tags if present
                mood_tags = [tag for tag in all_tags if tag in ['happy', 'sad', 'excited', 'tired', 'angry', 'peaceful', 'stressed', 'grateful', 'frustrated', 'motivated']]
                if mood_tags:
                    metadata["mood_tags"] = mood_tags
                
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

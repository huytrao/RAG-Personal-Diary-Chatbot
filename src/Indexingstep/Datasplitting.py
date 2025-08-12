from langchain_text_splitters import CharacterTextSplitter

class DataSplitting:
    def __init__(self, chunk_size=1000, chunk_overlap=200, separator="\n\n"):
        """
        Initialize the DataSplitting class.
        
        Args:
            chunk_size (int): Maximum size of each chunk
            chunk_overlap (int): Number of characters to overlap between chunks
            separator (str): Character(s) to split on
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator
        self.text_splitter = CharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separator=self.separator
        )
    
    def split_text(self, text):
        """
        Split the input text into chunks.
        
        Args:
            text (str): The text to be split
            
        Returns:
            list: List of text chunks
        """
        return self.text_splitter.split_text(text)
    
    def split_documents(self, documents):
        """
        Split documents into chunks.
        
        Args:
            documents (list): List of documents to be split
            
        Returns:
            list: List of document chunks
        """
        return self.text_splitter.split_documents(documents)
import os
import re
import logging
import hashlib
import pandas as pd
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse, parse_qs
from urllib.robotparser import RobotFileParser
import time
import threading
import json
import sys
from typing import Set, List, Dict, Optional

from django.conf import settings
from django.apps import AppConfig
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate

from .models import Website, ScrapedContent
from .serializers import WebsiteSerializer, ScrapedContentSerializer
from .sample_data import create_sample_data
from .cleanup import cleanup_incomplete_vectorizations

def check_ollama_status():
    """Check if Ollama is running and return status"""
    try:
        response = requests.get("http://localhost:11434/api/version")
        if response.status_code == 200:
            print("\n✅ Ollama is running successfully!")
            print(f"   Version: {response.json().get('version', 'unknown')}")
            return True
        else:
            print("\n❌ Ollama returned an unexpected status code:", response.status_code)
            return False
    except requests.exceptions.ConnectionError:
        print("\n❌ Ollama is not running. Please start Ollama before using the application.")
        print("   Run 'ollama serve' in a separate terminal.")
        return False
    except Exception as e:
        print("\n❌ Error checking Ollama status:", str(e))
        return False

def list_vectorized_databases():
    """List all vectorized databases in the system"""
    try:
        # Get the path to the vector databases directory
        vector_db_path = settings.VECTOR_DB_PATH
        
        if not os.path.exists(vector_db_path):
            print("\n📂 Vector database directory does not exist yet.")
            return []
        
        # Get all subdirectories in the vector_db_path that contain a chroma.sqlite3 file
        # This ensures we only list properly vectorized websites
        subdirs = []
        for d in os.listdir(vector_db_path):
            full_path = os.path.join(vector_db_path, d)
            if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, 'chroma.sqlite3')):
                subdirs.append(d)
        
        if not subdirs:
            print("\n📂 No vectorized databases found.")
            return []
        
        print("\n📂 Vectorized databases available:")
        vectorized_websites = []
        for idx, subdir in enumerate(subdirs, 1):
            # Try to find the corresponding website
            try:
                website = Website.objects.get(vector_db_id=subdir)
                print(f"   {idx}. {website.url} (ID: {subdir})")
                vectorized_websites.append({
                    'id': website.id,
                    'url': website.url,
                    'vector_db_id': subdir
                })
            except Website.DoesNotExist:
                print(f"   {idx}. Unknown website (ID: {subdir})")
        
        # Also update any websites in the database that have vector_db_id set but no actual vector database
        # This is a safety measure to keep the database consistent with the file system
        cleanup_incomplete_vectorizations()
        
        return vectorized_websites
    except Exception as e:
        print("\n❌ Error listing vectorized databases:", str(e))
        return []

def startup_checks():
    """Perform startup checks and display information"""
    print("\n" + "="*50)
    print("🚀 Starting Chat-with-Website Backend Server")
    print("="*50)
    
    # Check if Ollama is running
    ollama_running = check_ollama_status()
    
    # Clean up any incomplete vectorizations
    fixed_count = cleanup_incomplete_vectorizations()
    if fixed_count > 0:
        print(f"\n🧹 Cleaned up {fixed_count} incomplete vectorization(s)")
    
    # List vectorized databases
    vectorized_dbs = list_vectorized_databases()
    
    print("\n💡 API Endpoints available at:")
    print("   - GET /api/websites/ - List all vectorized websites")
    print("   - POST /api/websites/scrape/ - Scrape and vectorize a new website")
    print("   - POST /api/websites/chat/ - Chat with a vectorized website")
    print("="*50 + "\n")
    
    return ollama_running

# Run startup checks when the module is loaded
startup_checks()

class WebsiteViewSet(viewsets.ModelViewSet):
    """ViewSet for managing websites"""
    queryset = Website.objects.all()
    serializer_class = WebsiteSerializer
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Setup logger for this class
        self.logger = logging.getLogger(__name__)
    
    @action(detail=False, methods=['get'])
    def system_info(self, request):
        """Get system information including Ollama status and vectorized databases"""
        # First, clean up any inconsistencies in the database
        cleanup_count = cleanup_incomplete_vectorizations()
        if cleanup_count > 0:
            self.logger.info(f"Cleaned up {cleanup_count} incomplete vectorization entries")
        
        # Check Ollama status
        ollama_status = check_ollama_status()
        
        # List vectorized databases
        vectorized_websites = list_vectorized_databases()
        
        # Double-check that we're only returning websites with valid vector databases
        valid_vector_db_ids = set()
        vector_db_path = settings.VECTOR_DB_PATH
        
        if os.path.exists(vector_db_path):
            for d in os.listdir(vector_db_path):
                full_path = os.path.join(vector_db_path, d)
                if os.path.isdir(full_path) and os.path.exists(os.path.join(full_path, 'chroma.sqlite3')):
                    valid_vector_db_ids.add(d)
        
        # Final verification - only include websites with valid vector DBs
        verified_websites = []
        for website in vectorized_websites:
            if website.get('vector_db_id') in valid_vector_db_ids:
                verified_websites.append(website)
        
        return Response({
            'ollama_running': ollama_status,
            'vectorized_databases': verified_websites,
        })
        
    @action(detail=False, methods=['post'])
    def cleanup_databases(self, request):
        """Clean up any incomplete vector databases and inconsistencies"""
        try:
            # Run the cleanup function
            fixed_count = cleanup_incomplete_vectorizations()
            
            # Get the updated list of properly vectorized websites
            vectorized_websites = list_vectorized_databases()
            
            return Response({
                'message': f'Cleanup completed successfully. Fixed {fixed_count} inconsistencies.',
                'vectorized_databases': vectorized_websites
            })
        except Exception as e:
            self.logger.error(f"Error during database cleanup: {str(e)}")
            return Response({
                'error': f'An error occurred during cleanup: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def delete_vectorized_data(self, request):
        """Delete vectorized data including vector DB, scraped data, and database entries"""
        vector_db_id = request.data.get('vector_db_id')
        
        if not vector_db_id:
            return Response({'error': 'vector_db_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            import shutil
            
            # Get the website from database
            try:
                website = Website.objects.get(vector_db_id=vector_db_id)
                website_url = website.url
            except Website.DoesNotExist:
                return Response({'error': 'Website not found in database'}, 
                              status=status.HTTP_404_NOT_FOUND)
            
            # Delete vector database directory
            vector_db_path = os.path.join(settings.VECTOR_DB_PATH, vector_db_id)
            if os.path.exists(vector_db_path):
                shutil.rmtree(vector_db_path)
                self.logger.info(f"Deleted vector database: {vector_db_path}")
            
            # Delete scraped CSV file
            csv_filename = os.path.join(settings.SCRAPED_DATA_PATH, f"{vector_db_id}_scraped_data.csv")
            if os.path.exists(csv_filename):
                os.remove(csv_filename)
                self.logger.info(f"Deleted scraped data file: {csv_filename}")
            
            # Delete scraped content from database
            scraped_count = ScrapedContent.objects.filter(website=website).count()
            ScrapedContent.objects.filter(website=website).delete()
            self.logger.info(f"Deleted {scraped_count} scraped content entries from database")
            
            # Delete website entry from database
            website.delete()
            self.logger.info(f"Deleted website entry: {website_url}")
            
            # Get updated list of vectorized websites
            vectorized_websites = list_vectorized_databases()
            
            return Response({
                'message': f'Successfully deleted vectorized data for {website_url}',
                'deleted_vector_db_id': vector_db_id,
                'vectorized_databases': vectorized_websites
            })
            
        except Exception as e:
            self.logger.error(f"Error deleting vectorized data: {str(e)}")
            return Response({
                'error': f'An error occurred while deleting: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def scrape(self, request):
        """Scrape a website and store its content"""
        url = request.data.get('url')
        if not url:
            return Response({'error': 'URL is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create or get website
            website, created = Website.objects.get_or_create(url=url)
            
            # Scrape the website
            scraper = WebScraper(base_url=url)
            scraper.crawl_website()
            
            # Save scraped data
            scraped_data = scraper.scraped_data
            
            # Generate a unique filename based on the website URL
            url_hash = hashlib.md5(url.encode()).hexdigest()
            csv_filename = os.path.join(settings.SCRAPED_DATA_PATH, f"{url_hash}_scraped_data.csv")
            
            # Check if we have any data to process
            if not scraped_data:
                self.logger.warning(f"No content was scraped from {url}. Using sample data instead.")
                
                # Create sample data as fallback
                csv_filename = create_sample_data(url)
                
                # Load the sample data for database storage
                sample_df = pd.read_csv(csv_filename)
                scraped_data = sample_df.to_dict('records')
            else:
                # Create a directory for storing CSV files if it doesn't exist
                os.makedirs(settings.SCRAPED_DATA_PATH, exist_ok=True)
                
                # Save data to CSV
                scraped_df = pd.DataFrame(scraped_data)
                if not scraped_df.empty:
                    scraped_df.to_csv(csv_filename, index=False)
                else:
                    # Use sample data if DataFrame is empty
                    csv_filename = create_sample_data(url)
                    sample_df = pd.read_csv(csv_filename)
                    scraped_data = sample_df.to_dict('records')
            
            # Save scraped content to database
            for item in scraped_data:
                ScrapedContent.objects.create(
                    website=website,
                    url=item.get('url', ''),
                    title=item.get('title', ''),
                    meta_description=item.get('meta_description', ''),
                    headings=item.get('headings', ''),
                    paragraphs=item.get('paragraphs', ''),
                    list_items=item.get('list_items', ''),
                    combined_text=item.get('combined_text', ''),
                    word_count=item.get('word_count', 0),
                    url_hash=item.get('url_hash', '')
                )
            
            # Vectorize the scraped data
            vector_db_id = self.vectorize_data(csv_filename, url_hash)
            
            # Update website with vector_db_id
            website.vector_db_id = vector_db_id
            website.save()
            
            # Inform the user if we used sample data
            if not scraper.scraped_data:
                return Response({
                    'message': 'Website could not be scraped (possibly due to robots.txt restrictions). Sample data was used instead.',
                    'website_id': website.id,
                    'vector_db_id': vector_db_id,
                    'pages_scraped': len(scraped_data),
                    'used_sample_data': True
                })
            
            return Response({
                'message': 'Website scraped and vectorized successfully',
                'website_id': website.id,
                'vector_db_id': vector_db_id,
                'pages_scraped': len(scraped_data)
            })
            
        except Exception as e:
            # Log the error
            self.logger.error(f"Error during scraping process: {str(e)}")
            
            # Return an error response
            return Response({
                'error': f'An error occurred during the scraping process: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def vectorize_data(self, csv_filename, url_hash):
        """Vectorize the scraped data"""
        try:
            # Ensure CSV file exists
            if not os.path.exists(csv_filename):
                self.logger.error(f"CSV file not found: {csv_filename}")
                raise FileNotFoundError(f"The scraped data file was not found: {csv_filename}")
            
            # Load scraped website data
            dataframe = pd.read_csv(csv_filename)
            
            if dataframe.empty:
                self.logger.error(f"CSV file is empty: {csv_filename}")
                raise ValueError("The scraped data file is empty")
            
            # Initialize embedding model from Ollama
            # Check if Ollama is running first
            if not check_ollama_status():
                raise ConnectionError("Ollama service is not running. Please start Ollama and try again.")
                
            embedding_model = OllamaEmbeddings(model="mxbai-embed-large")
            
            # Define path to store the vector database
            vector_db_path = os.path.join(settings.VECTOR_DB_PATH, url_hash)
            os.makedirs(vector_db_path, exist_ok=True)
            
            # Check whether we need to add documents to the database (if it doesn't exist)
            should_add_docs = not os.path.exists(os.path.join(vector_db_path, 'chroma.sqlite3'))
            
            if should_add_docs:
                # Prepare lists to store Document objects and their IDs
                doc_objects = []
                doc_ids = []
                
                # Iterate over each row in the dataset
                for index, row in dataframe.iterrows():
                    # Use the combined_text as the main content for vectorization
                    content = row['combined_text']
                    
                    # Convert to string and handle NaN/None values
                    if pd.isna(content):
                        continue
                    
                    content = str(content).strip()
                    
                    # Skip rows with insufficient content
                    if not content or len(content) < 10:
                        continue
                    
                    # Helper function to safely convert metadata values
                    def safe_str(value):
                        if pd.isna(value):
                            return ""
                        return str(value).strip()
                    
                    # Create a Document object with metadata
                    doc = Document(
                        page_content=content,
                        metadata={
                            "url": safe_str(row["url"]),
                            "title": safe_str(row["title"]),
                            "meta_description": safe_str(row["meta_description"]),
                            "word_count": int(row["word_count"]) if not pd.isna(row["word_count"]) else 0,
                            "url_hash": safe_str(row["url_hash"])
                        }
                    )
                    
                    doc_objects.append(doc)
                    doc_ids.append(str(index))
                
                # Check if we have any documents to add
                if not doc_objects:
                    self.logger.warning(f"No valid content found to vectorize in {csv_filename}")
                    raise ValueError("No valid content found to vectorize")
                    
                # Initialize Chroma vector store with embeddings
                vector_store = Chroma(
                    collection_name=f"website_content_{url_hash}",
                    persist_directory=vector_db_path,
                    embedding_function=embedding_model
                )
                
                # Add documents to the vector store
                vector_store.add_documents(documents=doc_objects, ids=doc_ids)
                
                # Verify the database was created successfully
                if not os.path.exists(os.path.join(vector_db_path, 'chroma.sqlite3')):
                    raise ValueError("Vector database was not created successfully")
                
                self.logger.info(f"Successfully vectorized {len(doc_objects)} documents for {url_hash}")
            
            return url_hash
            
        except FileNotFoundError as e:
            self.logger.error(f"File not found error during vectorization: {str(e)}")
            raise
        except ValueError as e:
            self.logger.error(f"Value error during vectorization: {str(e)}")
            raise
        except ConnectionError as e:
            self.logger.error(f"Connection error during vectorization: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during vectorization: {str(e)}")
            raise
    
    @action(detail=False, methods=['post'])
    def chat(self, request):
        """Chat with a vectorized website content"""
        vector_db_id = request.data.get('vector_db_id')
        query = request.data.get('query')
        
        if not vector_db_id or not query:
            return Response({'error': 'vector_db_id and query are required'}, 
                           status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Check if Ollama is running
            if not check_ollama_status():
                return Response({'error': 'Ollama is not running. Please start Ollama and try again.'}, 
                               status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
            # Get the vector store path
            vector_db_path = os.path.join(settings.VECTOR_DB_PATH, vector_db_id)
            
            if not os.path.exists(vector_db_path):
                return Response({'error': 'Vector database not found. Please check if the website was properly vectorized.'},
                               status=status.HTTP_404_NOT_FOUND)
            
            # Initialize the LLM model
            llm = OllamaLLM(model="qwen3:8b")
            
            # Define the prompt template
            prompt_text = """
            You are a concise and direct assistant providing answers about websites.

            Consider this relevant website content: {content}

            Question: {query}

            Instructions:
            1. Provide a clear, concise answer, answer that is directly relevant to the question
            2. Focus only on the most important information that directly answers the question
            3. Do NOT include any of your thinking process in your response
            4. NEVER use <think> tags or show your reasoning process
            5. Present only the final, polished answer
            6. If the information is not in the content, briefly state that you don't know based on the provided content
            7. Never mention how you formed your answer or reference the content provided to you
            
            Remember: Users should only see your final, concise answer - no thinking, no process, no explanation of how you arrived at it.
            """
            
            # Convert the text template into a LangChain ChatPromptTemplate
            prompt_template = ChatPromptTemplate.from_template(prompt_text)
            
            # Combine the prompt with the LLM to create a processing pipeline
            qa_chain = prompt_template | llm
            
            # Initialize embedding model
            embedding_model = OllamaEmbeddings(model="mxbai-embed-large")
            
            # Initialize vector store
            vector_store = Chroma(
                collection_name=f"website_content_{vector_db_id}",
                persist_directory=vector_db_path,
                embedding_function=embedding_model
            )
        
            
            # Create a retriever
            retriever = vector_store.as_retriever(search_kwargs={"k": 5})
            
            # Retrieve relevant documents
            relevant_docs = retriever.invoke(query)
            
            # Extract text content from the Document objects
            relevant_content = "\n\n".join([doc.page_content for doc in relevant_docs])
            
            # Generate a response
            response = qa_chain.invoke({"content": relevant_content, "query": query})
            
            # Strip any <think>...</think> content from the response
            import re
            cleaned_response = re.sub(r'<think>.*?</think>', '', str(response), flags=re.DOTALL).strip()
            
            return Response({
                'answer': cleaned_response,
                'relevant_content': relevant_content,
                'source_count': len(relevant_docs)
            })
            
        except Exception as e:
            print(f"Error in chat endpoint: {str(e)}")
            return Response({'error': f'An error occurred: {str(e)}'}, 
                           status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class WebScraper:
    """Professional web scraper with text cleaning and CSV export"""
    
    def __init__(self, base_url: str, delay: float = 1.0, max_pages: int = 50):
        """
        Initialize the scraper
        
        Args:
            base_url (str): Base URL to start scraping
            delay (float): Delay between requests in seconds
            max_pages (int): Maximum number of pages to scrape
        """
        self.base_url = base_url
        self.delay = delay
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.scraped_data: List[Dict] = []
        self.session = requests.Session()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup session headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def check_robots_txt(self, url: str) -> bool:
        """
        Check if the URL is allowed by robots.txt
        
        Args:
            url (str): URL to check
            
        Returns:
            bool: True if allowed, False otherwise
        """
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            rp = RobotFileParser()
            rp.set_url(robots_url)
            
            # Try to fetch the robots.txt with a timeout
            response = self.session.get(robots_url, timeout=5)
            if response.status_code == 200:
                rp.parse(response.text.splitlines())
            else:
                # If robots.txt can't be fetched, assume it's allowed
                self.logger.warning(f"Couldn't fetch robots.txt ({response.status_code}), assuming allowed: {robots_url}")
                return True
            
            allowed = rp.can_fetch("*", url)
            if not allowed:
                self.logger.warning(f"URL disallowed by robots.txt: {url}")
            
            return allowed
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error requesting robots.txt: {e} - Assuming allowed")
            return True
        except Exception as e:
            self.logger.warning(f"Error checking robots.txt: {e} - Assuming allowed")
            return True
    
    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid and belongs to the same domain
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            parsed_url = urlparse(url)
            parsed_base = urlparse(self.base_url)
            
            # Check if the URL is relative or from the same domain
            return (not parsed_url.netloc or 
                    parsed_url.netloc == parsed_base.netloc or
                    parsed_url.netloc.endswith('.' + parsed_base.netloc))
        except Exception:
            return False
    
    def extract_links(self, soup: BeautifulSoup, current_url: str) -> Set[str]:
        """
        Extract all valid links from the page
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            current_url (str): Current page URL
            
        Returns:
            Set[str]: Set of valid URLs
        """
        links = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip anchor links
            if href.startswith('#'):
                continue
                
            # Convert relative URL to absolute
            absolute_url = urljoin(current_url, href)
            
            # Check if URL is valid
            if self.is_valid_url(absolute_url):
                links.add(absolute_url)
        
        return links
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text for vectorization
        
        Args:
            text (str): Raw text to clean
            
        Returns:
            str: Cleaned text
        """
        if not text or text is None:
            return ""
        
        # Convert to string in case it's not
        text = str(text)
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)]', '', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Remove extra spaces
        text = ' '.join(text.split())
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def extract_text_content(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract and clean text content from the page
        
        Args:
            soup (BeautifulSoup): Parsed HTML content
            
        Returns:
            Dict[str, str]: Dictionary with extracted text content
        """
        content = {}
        
        # Extract title
        title_tag = soup.find('title')
        content['title'] = self.clean_text(title_tag.get_text()) if title_tag else ""
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        content['meta_description'] = self.clean_text(meta_desc.get('content', '')) if meta_desc else ""
        
        # Extract headings
        headings = []
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            clean_heading = self.clean_text(heading.get_text())
            if clean_heading:
                headings.append(clean_heading)
        content['headings'] = ' | '.join(headings)
        
        # Extract main content (remove script, style, nav, footer, header)
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        # Extract paragraph text
        paragraphs = []
        for p in soup.find_all('p'):
            clean_p = self.clean_text(p.get_text())
            if clean_p:
                paragraphs.append(clean_p)
        content['paragraphs'] = ' '.join(paragraphs)
        
        # Extract list items
        list_items = []
        for li in soup.find_all('li'):
            clean_li = self.clean_text(li.get_text())
            if clean_li:
                list_items.append(clean_li)
        content['list_items'] = ' | '.join(list_items)
        
        # Combined content for vectorization
        combined_text = ' '.join([
            content.get('title', ''),
            content.get('meta_description', ''),
            content.get('headings', ''),
            content.get('paragraphs', ''),
            content.get('list_items', '')
        ])
        
        content['combined_text'] = self.clean_text(combined_text)
        content['word_count'] = len(content['combined_text'].split())
        
        return content
    
    def scrape_page(self, url: str) -> Optional[Dict]:
        """
        Scrape a single page
        
        Args:
            url (str): URL to scrape
            
        Returns:
            Optional[Dict]: Dictionary with scraped data or None on error
        """
        # Skip if already visited
        if url in self.visited_urls:
            return None
        
        # Add to visited URLs
        self.visited_urls.add(url)
        
        # Check robots.txt
        if not self.check_robots_txt(url):
            self.logger.info(f"Skipping {url} (disallowed by robots.txt)")
            return None
        
        try:
            # Delay before request
            time.sleep(self.delay)
            
            # Send request
            self.logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=10)
            
            # Check response
            if response.status_code != 200:
                self.logger.warning(f"Failed to get {url}: {response.status_code}")
                return None
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract content
            content = self.extract_text_content(soup)
            
            # Add URL and hash
            content['url'] = url
            content['url_hash'] = hashlib.md5(url.encode()).hexdigest()
            
            # Extract links for next pages
            links = self.extract_links(soup, url)
            
            # Add to scraped data
            self.scraped_data.append(content)
            
            return {
                'content': content,
                'links': links
            }
        
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {e}")
            return None
    
    def crawl_website(self) -> None:
        """
        Crawl the website starting from the base URL
        """
        # Queue of URLs to scrape
        queue = [self.base_url]
        
        # Reset visited URLs and scraped data
        self.visited_urls = set()
        self.scraped_data = []
        
        while queue and len(self.visited_urls) < self.max_pages:
            # Get next URL
            url = queue.pop(0)
            
            # Scrape page
            result = self.scrape_page(url)
            
            if result:
                # Add new links to queue
                links = result.get('links', set())
                
                for link in links:
                    if link not in self.visited_urls and link not in queue:
                        queue.append(link)
    
    def get_summary(self) -> Dict:
        """
        Get summary of scraped data
        
        Returns:
            Dict: Summary information
        """
        return {
            'pages_scraped': len(self.scraped_data),
            'total_words': sum(item.get('word_count', 0) for item in self.scraped_data),
            'base_url': self.base_url
        }
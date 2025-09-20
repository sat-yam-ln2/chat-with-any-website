"""
Cleanup utilities for the chat-bot-rag system.
Used to clean up incomplete or failed vectorization attempts.
"""

import os
import logging
from django.conf import settings
from .models import Website

logger = logging.getLogger(__name__)

def cleanup_incomplete_vectorizations():
    """
    Clean up any incomplete vectorization attempts by:
    1. Checking all vector_db_id values in the Website model
    2. Verifying that corresponding vector database folders exist and contain chroma.sqlite3
    3. Removing vector_db_id values from Website objects if the vector database is incomplete
    
    Returns:
        int: Number of Website records fixed
    """
    fixed_count = 0
    
    try:
        # Get the vector database path
        vector_db_path = settings.VECTOR_DB_PATH
        
        # Get all websites with vector_db_id values
        websites = Website.objects.filter(vector_db_id__isnull=False)
        
        for website in websites:
            # Check if the vector database exists and is complete
            db_folder = os.path.join(vector_db_path, website.vector_db_id)
            chroma_db = os.path.join(db_folder, 'chroma.sqlite3')
            
            if not os.path.exists(db_folder) or not os.path.exists(chroma_db):
                # The vector database is incomplete or missing
                logger.warning(f"Found incomplete vector database for {website.url} (ID: {website.vector_db_id})")
                
                # Clear the vector_db_id
                website.vector_db_id = None
                website.save()
                
                fixed_count += 1
                logger.info(f"Cleared vector_db_id for {website.url}")
        
        return fixed_count
    
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        return 0
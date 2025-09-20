"""
This module provides sample data for testing the application 
when scraping fails due to robots.txt or other issues.
"""
import os
import csv
import hashlib
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

SAMPLE_DATA = [
    {
        "url": "https://example.com/",
        "title": "Example Domain",
        "meta_description": "This is a sample website for testing purposes",
        "headings": "Example Domain | Welcome to Example",
        "paragraphs": "This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission. More information can be found at example.com.",
        "list_items": "Example 1 | Example 2 | Example 3",
        "combined_text": "Example Domain This is a sample website for testing purposes Example Domain | Welcome to Example This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission. More information can be found at example.com. Example 1 | Example 2 | Example 3",
        "word_count": 48,
        "url_hash": ""  # Will be filled in by the function
    }
]

def create_sample_data(url):
    """
    Create sample data for a website that couldn't be scraped
    
    Args:
        url (str): The URL of the website
        
    Returns:
        str: Path to the CSV file with sample data
    """
    try:
        # Generate URL hash
        url_hash = hashlib.md5(url.encode()).hexdigest()
        
        # Create sample data with the URL and hash
        sample_data = SAMPLE_DATA.copy()
        for item in sample_data:
            item["url"] = url
            item["url_hash"] = url_hash
            
        # Create directory if it doesn't exist
        os.makedirs(settings.SCRAPED_DATA_PATH, exist_ok=True)
        
        # Generate CSV filename
        csv_filename = os.path.join(settings.SCRAPED_DATA_PATH, f"{url_hash}_scraped_data.csv")
        
        # Write to CSV
        with open(csv_filename, 'w', newline='') as csvfile:
            fieldnames = sample_data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for item in sample_data:
                writer.writerow(item)
        
        logger.info(f"Created sample data for {url} at {csv_filename}")
        return csv_filename
    except Exception as e:
        logger.error(f"Error creating sample data: {str(e)}")
        raise
from rest_framework import serializers
from .models import Website, ScrapedContent

class WebsiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Website
        fields = ['id', 'url', 'title', 'meta_description', 'date_scraped', 'vector_db_id']

class ScrapedContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapedContent
        fields = ['id', 'website', 'url', 'title', 'meta_description', 'headings', 
                  'paragraphs', 'list_items', 'combined_text', 'word_count', 'url_hash']
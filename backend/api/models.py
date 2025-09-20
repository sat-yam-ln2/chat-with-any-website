from django.db import models

class Website(models.Model):
    """Model to store information about scraped websites"""
    url = models.URLField(unique=True)
    title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    date_scraped = models.DateTimeField(auto_now_add=True)
    vector_db_id = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.url

class ScrapedContent(models.Model):
    """Model to store scraped content from websites"""
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='contents')
    url = models.URLField()
    title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    headings = models.TextField(blank=True)
    paragraphs = models.TextField(blank=True)
    list_items = models.TextField(blank=True)
    combined_text = models.TextField(blank=True)
    word_count = models.IntegerField(default=0)
    url_hash = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.website.url} - {self.url}"
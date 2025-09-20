import React, { useState } from 'react';
import axios from 'axios';
import './URLInput.css';

const URLInput = ({ onWebsiteVectorized }) => {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!url) {
      setError('Please enter a URL');
      return;
    }
    
    // Validate URL format
    try {
      new URL(url);
    } catch (err) {
      setError('Please enter a valid URL (including http:// or https://)');
      return;
    }
    
    setIsLoading(true);
    setError('');
    setSuccess('');
    
    try {
      const response = await axios.post('/api/websites/scrape/', { url });
      setSuccess(`Successfully scraped and vectorized ${response.data.pages_scraped} pages from ${url}`);
      
      // Pass the vectorized website data to parent component
      if (onWebsiteVectorized) {
        onWebsiteVectorized({
          websiteId: response.data.website_id,
          vectorDbId: response.data.vector_db_id,
          url
        });
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to scrape the website. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="url-input-container">
      <h2>Enter Website URL</h2>
      <form onSubmit={handleSubmit}>
        <div className="input-group">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            disabled={isLoading}
            className="url-input"
          />
          <button type="submit" disabled={isLoading} className="submit-button">
            {isLoading ? 'Processing...' : 'Scrape & Vectorize'}
          </button>
        </div>
      </form>
      
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}
      
      {isLoading && (
        <div className="loading-message">
          <p>This process may take a few minutes depending on the website size...</p>
          <div className="loading-spinner"></div>
        </div>
      )}
    </div>
  );
};

export default URLInput;
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './VectorSelection.css';

const VectorSelection = ({ onSelectWebsite }) => {
  const [websites, setWebsites] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedWebsite, setSelectedWebsite] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchWebsites = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('/api/websites/');
      // Filter out websites without a vector_db_id
      const vectorizedWebsites = response.data.filter(website => website.vector_db_id);
      setWebsites(vectorizedWebsites);
      setIsLoading(false);
    } catch (err) {
      setError('Failed to load vectorized websites');
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWebsites();
  }, []);

  const handleSelectWebsite = (website) => {
    setSelectedWebsite(website);
    
    if (onSelectWebsite) {
      onSelectWebsite({
        websiteId: website.id,
        vectorDbId: website.vector_db_id,
        url: website.url
      });
    }
  };

  const handleDeleteWebsite = async (website, event) => {
    // Prevent the click from selecting the website
    event.stopPropagation();
    
    // Confirm deletion
    const confirmDelete = window.confirm(
      `Are you sure you want to delete "${website.url}"?\n\nThis will permanently remove:\n- Vector database\n- Scraped data\n- All chat history\n\nThis action cannot be undone.`
    );
    
    if (!confirmDelete) return;
    
    try {
      setDeletingId(website.id);
      setError('');
      
      // Call the delete endpoint
      await axios.post('/api/websites/delete_vectorized_data/', {
        vector_db_id: website.vector_db_id
      });
      
      // If the deleted website was selected, clear the selection
      if (selectedWebsite?.id === website.id) {
        setSelectedWebsite(null);
        if (onSelectWebsite) {
          onSelectWebsite(null);
        }
      }
      
      // Refresh the websites list
      await fetchWebsites();
      
    } catch (err) {
      console.error('Error deleting website:', err);
      const errorMessage = err.response?.data?.error || err.message;
      
      // Check if it's a file lock error
      if (errorMessage.includes('process is using') || errorMessage.includes('restart the server')) {
        setError(
          `⚠️ Cannot delete: Database files are in use.\n\n` +
          `Please restart the Django server and try again. This ensures all database connections are properly closed.`
        );
      } else {
        setError(`Failed to delete website: ${errorMessage}`);
      }
    } finally {
      setDeletingId(null);
    }
  };

  if (isLoading) {
    return <div className="loading">Loading vectorized websites...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (websites.length === 0) {
    return (
      <div className="no-websites">
        <p>No vectorized websites found. Please scrape a website first.</p>
      </div>
    );
  }

  return (
    <div className="vector-selection-container">
      <h2>Select Vectorized Website</h2>
      {error && <div className="error">{error}</div>}
      <div className="websites-list">
        {websites.map((website) => (
          <div 
            key={website.id}
            className={`website-item ${selectedWebsite?.id === website.id ? 'selected' : ''}`}
            onClick={() => handleSelectWebsite(website)}
          >
            <div className="website-item-content">
              <h3>{website.title || website.url}</h3>
              <p className="website-url">{website.url}</p>
              <p className="website-date">Scraped on: {new Date(website.date_scraped).toLocaleString()}</p>
            </div>
            <button
              className="delete-button"
              onClick={(e) => handleDeleteWebsite(website, e)}
              disabled={deletingId === website.id}
              title="Delete this website"
            >
              {deletingId === website.id ? '⏳' : '🗑️'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default VectorSelection;
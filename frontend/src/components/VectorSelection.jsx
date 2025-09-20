import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './VectorSelection.css';

const VectorSelection = ({ onSelectWebsite }) => {
  const [websites, setWebsites] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedWebsite, setSelectedWebsite] = useState(null);

  useEffect(() => {
    const fetchWebsites = async () => {
      try {
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
      <div className="websites-list">
        {websites.map((website) => (
          <div 
            key={website.id}
            className={`website-item ${selectedWebsite?.id === website.id ? 'selected' : ''}`}
            onClick={() => handleSelectWebsite(website)}
          >
            <h3>{website.title || website.url}</h3>
            <p className="website-url">{website.url}</p>
            <p className="website-date">Scraped on: {new Date(website.date_scraped).toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default VectorSelection;
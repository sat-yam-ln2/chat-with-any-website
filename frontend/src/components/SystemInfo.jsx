import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './SystemInfo.css';

const SystemInfo = () => {
  const [systemInfo, setSystemInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    const fetchSystemInfo = async () => {
      try {
        const response = await axios.get('/api/websites/system_info/');
        setSystemInfo(response.data);
        setIsLoading(false);
      } catch (err) {
        setError('Failed to load system information');
        setIsLoading(false);
      }
    };

    fetchSystemInfo();
  }, []);

  const toggleExpand = () => {
    setIsExpanded(!isExpanded);
  };

  if (isLoading) {
    return <div className="system-info-loading">Loading system information...</div>;
  }

  if (error) {
    return <div className="system-info-error">{error}</div>;
  }

  return (
    <div className={`system-info-container ${isExpanded ? 'expanded' : ''}`}>
      <div className="system-info-header" onClick={toggleExpand}>
        <h3>System Status</h3>
        <div className="system-info-indicators">
          <div className={`status-indicator ${systemInfo?.ollama_running ? 'online' : 'offline'}`}>
            Ollama: {systemInfo?.ollama_running ? 'Online' : 'Offline'}
          </div>
          <div className="database-count">
            Vectorized Databases: {systemInfo?.vectorized_databases?.length || 0}
          </div>
          <div className="expand-icon">{isExpanded ? '▲' : '▼'}</div>
        </div>
      </div>
      
      {isExpanded && (
        <div className="system-info-details">
          <div className="system-info-section">
            <h4>Ollama Status</h4>
            {systemInfo?.ollama_running ? (
              <p className="status-success">Ollama is running properly</p>
            ) : (
              <div className="status-error">
                <p>Ollama is not running!</p>
                <p>Please start Ollama before using the application.</p>
              </div>
            )}
          </div>
          
          <div className="system-info-section">
            <h4>Vectorized Databases</h4>
            {systemInfo?.vectorized_databases?.length > 0 ? (
              <ul className="database-list">
                {systemInfo.vectorized_databases.map((dbId, index) => {
                  // Try to find the corresponding website
                  const website = systemInfo.websites.find(w => w.vector_db_id === dbId);
                  return (
                    <li key={dbId}>
                      {website ? (
                        <span>{website.url} <small>(ID: {dbId})</small></span>
                      ) : (
                        <span>Unknown website <small>(ID: {dbId})</small></span>
                      )}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p>No vectorized databases found. Try scraping a website first.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemInfo;
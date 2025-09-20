import React, { useState } from 'react';
import URLInput from './components/URLInput';
import VectorSelection from './components/VectorSelection';
import ChatBox from './components/ChatBox';
import SystemInfo from './components/SystemInfo';
import './App.css';

function App() {
  const [selectedWebsite, setSelectedWebsite] = useState(null);

  const handleWebsiteVectorized = (website) => {
    setSelectedWebsite(website);
  };

  const handleSelectWebsite = (website) => {
    setSelectedWebsite(website);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Chat with Website</h1>
        <p>Enter a URL to scrape, vectorize, and chat with any website</p>
      </header>

      <main className="app-main">
        <section className="app-controls">
          <SystemInfo />
          <URLInput onWebsiteVectorized={handleWebsiteVectorized} />
          <VectorSelection onSelectWebsite={handleSelectWebsite} />
        </section>

        <section className="app-chat">
          <ChatBox selectedWebsite={selectedWebsite} />
        </section>
      </main>

      <footer className="app-footer">
        <p>Powered by Ollama, LangChain, and ChromaDB</p>
      </footer>
    </div>
  );
}

export default App;
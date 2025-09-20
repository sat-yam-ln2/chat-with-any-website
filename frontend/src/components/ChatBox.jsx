import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './ChatBox.css';

const ChatBox = ({ selectedWebsite }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Clear chat when website changes
    setMessages([]);
  }, [selectedWebsite]);

  useEffect(() => {
    // Scroll to bottom of chat
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!input.trim() || !selectedWebsite) return;
    
    // Add user message to chat
    const userMessage = {
      id: Date.now(),
      text: input,
      sender: 'user'
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    try {
      const response = await axios.post('/api/websites/chat/', {
        vector_db_id: selectedWebsite.vectorDbId,
        query: input
      });
      
      // Add AI response to chat
      const aiMessage = {
        id: Date.now() + 1,
        text: response.data.answer,
        sender: 'ai'
      };
      
      setMessages(prev => [...prev, aiMessage]);
    } catch (err) {
      // Add error message to chat
      const errorMessage = {
        id: Date.now() + 1,
        text: 'Sorry, there was an error processing your request. Please try again.',
        sender: 'system',
        isError: true
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!selectedWebsite) {
    return (
      <div className="chat-placeholder">
        <p>Please select or scrape a website to start chatting</p>
      </div>
    );
  }

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>Chat with {selectedWebsite.url}</h2>
      </div>
      
      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h3>👋 Welcome to Website Chat!</h3>
            <p>Ask questions about the content of {selectedWebsite.url}</p>
            <p>Example questions:</p>
            <ul>
              <li>What is this website about?</li>
              <li>What services do they offer?</li>
              <li>How does their product work?</li>
            </ul>
          </div>
        )}
        
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.sender}`}>
            <div className="message-content">
              <ReactMarkdown>{message.text}</ReactMarkdown>
            </div>
          </div>
        ))}
        
        {isLoading && (
          <div className="message ai loading">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about the website..."
          disabled={isLoading}
          className="chat-input"
        />
        <button 
          type="submit" 
          disabled={isLoading || !input.trim()} 
          className="send-button"
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatBox;
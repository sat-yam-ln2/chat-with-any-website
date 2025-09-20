# Chat with Website - RAG System

A Retrieval-Augmented Generation (RAG) system that allows users to chat with website content through a conversational interface.

## System Features

### Backend Components

- **Ollama Integration**: Utilizes Ollama for local language model processing
- **Vector Database Management**: Stores and retrieves website content embeddings
- **Django REST Framework**: Provides a robust API interface

### Startup Processes

The system performs several checks during startup:
- Verifies Ollama availability and version
- Lists all vectorized databases
- Displays available API endpoints

## API Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/api/websites/` | GET | Lists all vectorized websites | None |
| `/api/websites/system_info/` | GET | Returns system information | None |
| `/api/websites/scrape/` | POST | Scrapes and vectorizes a website | `url`: Website URL |
| `/api/websites/chat/` | POST | Chats with vectorized content | `vector_db_id`: Database ID, `query`: User question |

## Setup and Running

1. Ensure Ollama is installed and running locally
2. Execute the `start_backend.bat` script which:
   - Activates the virtual environment
   - Creates necessary directories
   - Applies database migrations
   - Starts the Django server

## Data Management

- Website content: Stored in CSV format and database
- Vector embeddings: Maintained in ChromaDB format
- Website metadata: Tracked in Django database

## Error Handling

The system implements comprehensive error handling:
- Validates Ollama availability
- Verifies vector database existence
- Provides detailed error messages
- Handles exceptions with appropriate HTTP status codes
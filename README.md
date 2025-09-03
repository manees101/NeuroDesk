# NeuroDesk Backend

A FastAPI backend for processing PDF documents with LangChain and OpenAI embeddings, with user-specific document storage and retrieval.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration:**
   Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. **Run the application:**
   ```bash
   uvicorn main:app --reload
   ```

## API Endpoints

### 1. Upload Document
- **POST** `/document/upload`
- **Description:** Upload a PDF document for processing
- **Parameters:** 
  - `file`: PDF file (multipart/form-data)
  - `user_id`: User identifier (form data)
- **Response:**
  ```json
  {
    "message": "Document uploaded and processed successfully",
    "filename": "document.pdf",
    "user_id": "user123",
    "collection_name": "user_user123_doc_document",
    "pages_loaded": 5,
    "chunks_created": 15
  }
  ```

### 2. Search Documents
- **GET** `/documents/search`
- **Description:** Search documents using semantic similarity for a specific user
- **Parameters:**
  - `query`: Search query string
  - `user_id`: User identifier
  - `collection_name`: (Optional) Specific collection name to search
  - `n_results`: Number of results to return (default: 5)
- **Response:**
  ```json
  {
    "query": "your search query",
    "user_id": "user123",
    "collection_name": "user_user123_doc_document",
    "results": [
      {
        "document": "document content...",
        "metadata": {...},
        "rank": 1,
        "collection_name": "user_user123_doc_document"
      }
    ]
  }
  ```

### 3. List Collections
- **GET** `/documents/collections`
- **Description:** List all available document collections for a specific user
- **Parameters:**
  - `user_id`: User identifier
- **Response:**
  ```json
  {
    "user_id": "user123",
    "collections": [
      {
        "name": "user_user123_doc_document1",
        "document_name": "document1",
        "count": 15
      }
    ]
  }
  ```

### 4. Delete Collection
- **DELETE** `/documents/collection/{collection_name}`
- **Description:** Delete a specific collection for a user
- **Parameters:**
  - `collection_name`: Name of the collection to delete
  - `user_id`: User identifier
- **Response:**
  ```json
  {
    "message": "Collection deleted successfully",
    "collection_name": "user_user123_doc_document",
    "user_id": "user123"
  }
  ```

## Features

- **User-Specific Storage:** Each user's documents are stored in separate collections
- **PDF Processing:** Uses LangChain's PyPDFLoader for robust PDF text extraction
- **Text Chunking:** RecursiveCharacterTextSplitter with 1000 character chunks and 200 character overlap
- **OpenAI Embeddings:** Uses text-embedding-3-small model for high-quality embeddings
- **ChromaDB Storage:** Persistent vector database with user-specific collections
- **Semantic Search:** Advanced similarity search with metadata preservation
- **Security:** Users can only access their own documents
- **Cross-Collection Search:** Search across all user's documents or specific collections

## User Management

### Collection Naming Convention
Collections are named using the pattern: `user_{user_id}_doc_{filename}`
- Example: `user_user123_doc_annual_report_2024`

### Security Features
- Users can only access collections that start with their user_id
- All endpoints require user_id validation
- Automatic access control prevents cross-user data access

## File Structure

```
backend/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── .env                # Environment variables (create this)
└── chroma_db/         # ChromaDB storage (auto-created)
```

## Usage Example

1. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

2. Upload a PDF document for a user:
   ```bash
   curl -X POST "http://localhost:8000/document/upload" \
        -F "file=@document.pdf" \
        -F "user_id=user123"
   ```

3. Search the user's documents:
   ```bash
   # Search across all user's documents
   curl "http://localhost:8000/documents/search?query=your question&user_id=user123"
   
   # Search in specific collection
   curl "http://localhost:8000/documents/search?query=your question&user_id=user123&collection_name=user_user123_doc_document"
   ```

4. List user's collections:
   ```bash
   curl "http://localhost:8000/documents/collections?user_id=user123"
   ```

5. Delete a collection:
   ```bash
   curl -X DELETE "http://localhost:8000/documents/collection/user_user123_doc_document?user_id=user123"
   ```

## API Documentation

Once the server is running, visit `http://localhost:8000/docs` for interactive API documentation. 

## Phase 2 Roadmap
| Stage                   | Goal                                       |
| ----------------------- | ------------------------------------------ |
| 1. Logging              | Track queries, answers, and feedback       |
| 2. Feedback UI          | Collect useful data for training           |
| 3. Context Improvement  | Refine retrieval based on feedback         |
| 4. Response Learning    | Train on user-corrected answers            |
| 5. Memory Systems       | Personalize per-user context               |
| 6. Clarifying Questions | Improve user experience on edge cases      |
| 7. Fine-Tuning          | Enhance RAG pipeline with learned patterns |
| 8. Evaluation           | Continuously measure and evolve            |

# NeuroDesk Backend

FastAPI backend for authenticated PDF chat with RAG. Users upload PDFs, which are embedded with OpenAI embeddings and stored in Chroma Cloud per-user collections. Queries are answered via an agent that retrieves relevant chunks and uses OpenAI or Google Gemini to respond. MongoDB stores users, chat history, password reset tokens, and email logs. Optional SMTP sends password reset emails.

## Architecture

- **API**: FastAPI (`main.py`)
- **Auth**: JWT bearer tokens (`auth.py`) with bcrypt hashing
- **Vector DB**: Chroma Cloud (per-user collections)
- **Embeddings**: `text-embedding-3-small`
- **LLM**: OpenAI GPT-4o or Google Gemini (auto-selected via env)
- **RAG Agent**: LangGraph agent orchestrating retrieval + response (`agent.py`, tools in `utils.py`)
- **DB**: MongoDB (users, chats, password reset, email logs)
- **Email**: SMTP (e.g., Gmail App Password) for password reset (`emailer.py`)
- **Logging**: `app.log` file + console

## Requirements

- Python 3.11.x
- MongoDB instance
- Chroma Cloud account + API key
- OpenAI or Google API key (at least one)

## Environment Variables (.env)

Minimum to run:
```
DB_URI=mongodb://localhost:27017
DB_NAME=neurodesk

# Auth
JWT_SECRET=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRES_HOURS=24

# Chroma Cloud
CHROMA_API_KEY=your_chroma_api_key
CHROMA_TENANT=your_tenant
CHROMA_DATABASE=your_database

# LLMs (provide at least one)
OPENAI_API_KEY=sk-...
# or
GOOGLE_API_KEY=...

# SMTP (optional for password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your@gmail.com
```

## Setup

1) Create and activate venv
```
python -m venv venv
./venv/Scripts/activate  # Windows PowerShell: .\venv\Scripts\Activate.ps1
```

2) Install deps
```
pip install -r requirements.txt
```

3) Run server
```
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`.

## API Summary

All routes except signup/login require `Authorization: Bearer <token>`.

Auth
- POST `/auth/signup` → create user; body: `{ name, email, password }`
- POST `/auth/login` → returns `{ access_token, token_type, user }`
- GET `/auth/me` → current user info
- POST `/auth/password-reset/request` → starts reset flow (always 200)
- POST `/auth/password-reset/confirm` → `{ token, new_password }`

Documents
- POST `/documents/upload` → multipart `file` (PDF). Creates user collection and stores embeddings.
- GET `/documents/search?query=...&collection_name=...` → search within specific collection; omit `collection_name` to search across user collections.
- GET `/documents/collections?page=1&limit=20` → list user collections.
- DELETE `/documents/collections/{collection_name}` → delete a collection (must belong to user).

Chat / RAG
- GET `/ai/ask?query=...&collection_name=...` → answer a question (returns string)
- GET `/documents/{collection_name}/messages?limit=20&cursor=ISO_DATE` → paginated chat history (newest first)
- POST `/ai/ask/feedback` → `{ chat_id?, query?, is_positive_feedback?, comments? }` to log feedback and mark chat

## Data & Collections

- `users`: `{ id, name, email, hashed_password, is_active, created_at, updated_at }`
- `user_chat`: chat history per user `{ query, llm_response, collection_name, is_feedback_submitted, created_at }`
- `password_reset_tokens`: `{ user_id, email, token, expires_at, used }`
- `email_logs`: sent/failed emails
- `doc_summary`: LLM-generated short summary of each uploaded PDF

Vector collections are named: `user_{userId}_doc_{safeFilename}`.

## RAG Flow

1) PDF upload → chunk → embed → store in Chroma collection
2) Question → agent selects tool(s) → retrieve chunks (collection-specific or cross-collection)
3) LLM composes answer; chat saved in Mongo; optional feedback stored in a dedicated Chroma collection `feedback`

## Security Notes

- JWT-based auth; bcrypt for passwords
- Collection access is restricted by prefix `user_{userId}_` and enforced server-side
- CORS allows localhost dev origins (adjust in `main.py`)

## Troubleshooting

- Missing embeddings/Chroma keys → `/ai/ask` returns an error message; set `OPENAI_API_KEY` or `GOOGLE_API_KEY` and Chroma keys
- Ensure Mongo is reachable via `DB_URI`
- PDF uploads limited to 10MB and `.pdf` only

## Scripts

```
uvicorn main:app --reload --port 8000
```

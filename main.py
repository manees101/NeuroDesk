import tempfile
from typing import Union
from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import utils
from agent import rag_ai
from langchain_core.messages import HumanMessage
from db.feedback import FeedbackRequest
from db.mongo import db
from db.users import (
    UserCreate,
    UserPublic,
    UserLogin,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetToken,
)
from auth import get_current_user, hash_password, verify_password, create_access_token
from datetime import datetime, timedelta
import secrets
from emailer import send_email
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UploadRequest(BaseModel):
    user_id: str

@app.post("/auth/signup", response_model=UserPublic)
def signup(payload: UserCreate):
    existing = db["users"].find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user_id = secrets.token_hex(16)
    user_doc = {
        "id": user_id,
        "name": payload.name,
        "email": payload.email,
        "hashed_password": hash_password(payload.password),
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    db["users"].insert_one(user_doc)
    return UserPublic(id=user_id, name=payload.name, email=payload.email, created_at=user_doc["created_at"])

@app.post("/auth/login")
def login(payload: UserLogin):
    user = db["users"].find_one({"email": payload.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(payload.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(sub=user["id"], email=user["email"])
    user_public = UserPublic(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        created_at=user["created_at"],
    )
    return {"access_token": token, "token_type": "bearer", "user": user_public.model_dump()}

@app.get("/auth/me", response_model=UserPublic)
def me(current_user=Depends(get_current_user)):
    user = db["users"].find_one({"id": current_user.id})
    return UserPublic(id=user["id"], name=user["name"], email=user["email"], created_at=user["created_at"])

@app.post("/auth/password-reset/request")
def request_password_reset(payload: PasswordResetRequest):
    user = db["users"].find_one({"email": payload.email})
    # Always respond success to avoid user enumeration, but only create token if user exists
    if user:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=1)
        reset = PasswordResetToken(
            user_id=user["id"],
            email=user["email"],
            token=token,
            expires_at=expires_at,
        )
        db["password_reset_tokens"].insert_one(reset.model_dump())
        # Compose email content
        subject = "Password Reset"
        content = f"Use this token to reset your password: {token}\nThis token expires at {expires_at.isoformat()}"
        send_email(email=payload.email, subject=subject, content=content, type="password_reset")
    return {"message": "If the email exists, a reset link has been sent"}

@app.post("/auth/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm):
    reset = db["password_reset_tokens"].find_one({"token": payload.token})
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid token")
    if reset.get("used"):
        raise HTTPException(status_code=400, detail="Token already used")
    if reset["expires_at"] < datetime.now():
        raise HTTPException(status_code=400, detail="Token expired")
    # Update user password
    hashed = hash_password(payload.new_password)
    db["users"].update_one({"id": reset["user_id"]}, {"$set": {"hashed_password": hashed, "updated_at": datetime.now()}})
    # Mark token used
    db["password_reset_tokens"].update_one({"token": payload.token}, {"$set": {"used": True}})
    return {"message": "Password has been reset"}

@app.get("/")
def read_root():
    utils.logger.info("Root endpoint accessed")
    return JSONResponse(content="Hellow from server.")

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    utils.logger.info(f"Items endpoint accessed with item_id: {item_id}, q: {q}")
    return {"item_id": item_id, "q": q}

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
):
    user_id = current_user.id
    utils.logger.info(f"Document upload request received for user: {user_id}, filename: {file.filename}")
    
    # Validate PDF file
    utils.validate_pdf_file(file.filename, file.size)
    
    temp_file_path = None
    try:
        # Save uploaded file temporarily
        utils.logger.debug("Creating temporary file for uploaded PDF...")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        utils.logger.info(f"Temporary file created: {temp_file_path}")
        
        # Process PDF using LangChain
        utils.logger.info("Starting PDF processing...")
        result = utils.process_pdf_file(temp_file_path, file.filename, user_id)
        
        # Clean up temporary file
        utils.cleanup_temp_file(temp_file_path)
        temp_file_path = None
        
        response_data = {
            "message": "Document uploaded and processed successfully",
            "filename": file.filename,
            "user_id": user_id,
            "collection_name": result["collection_name"],
            "pages_loaded": result["pages_loaded"],
            "chunks_created": result["chunks_created"]
        }
        
        utils.logger.info(f"Document upload completed successfully: {response_data}")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        utils.logger.error(f"HTTPException during document upload for user: {user_id}, file: {file.filename}")
        raise
    except Exception as e:
        utils.logger.error(f"Unexpected error during document upload for user: {user_id}, file: {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    finally:
        # Clean up temporary file if it exists
        if temp_file_path:
            utils.cleanup_temp_file(temp_file_path)

@app.get("/documents/search")
async def search_documents(
    query: str,
    collection_name: str = None,
    n_results: int = 5,
    current_user = Depends(get_current_user),
):
    user_id = current_user.id
    utils.logger.info(f"Search request received - Query: '{query}', User: {user_id}, Collection: {collection_name}, Results: {n_results}")
    
    try:
        if collection_name:
            # Search in specific collection
            results = utils.search_in_collection(query, collection_name, user_id, n_results)
            
            response_data = {
                "query": query,
                "user_id": user_id,
                "collection_name": collection_name,
                "results": results
            }
            
            utils.logger.info(f"Search completed successfully: {len(results)} results returned")
            return response_data
            
        else:
            # Search across all user's collections
            top_results, collections_count = utils.search_across_user_collections(query, user_id, n_results)
            
            if not top_results:
                return {
                    "query": query,
                    "user_id": user_id,
                    "message": "No documents found for this user",
                    "results": []
                }
            
            response_data = {
                "query": query,
                "user_id": user_id,
                "message": f"Searched across {collections_count} collections",
                "results": top_results
            }
            
            return response_data
            
    except HTTPException:
        utils.logger.error(f"HTTPException during search for user: {user_id}, query: '{query}'")
        raise
    except Exception as e:
        utils.logger.error(f"Error searching documents for user: {user_id}, query: '{query}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching documents: {str(e)}")

@app.get("/documents/collections")
async def list_collections(current_user = Depends(get_current_user)):
    user_id = current_user.id
    utils.logger.info(f"List collections request received for user: {user_id}")
    
    try:
        # Get user collections
        collection_info = utils.get_user_collections(user_id)
        
        response_data = {
            "user_id": user_id,
            "collections": collection_info
        }
        
        utils.logger.info(f"List collections completed successfully: {len(collection_info)} collections returned")
        return response_data
        
    except HTTPException:
        utils.logger.error(f"HTTPException during list collections for user: {user_id}")
        raise
    except Exception as e:
        utils.logger.error(f"Error listing collections for user: {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing collections: {str(e)}")

@app.delete("/documents/collections/{collection_name}")
async def delete_collection(collection_name: str, current_user = Depends(get_current_user)):
    user_id = current_user.id
    utils.logger.info(f"Delete collection request received - Collection: {collection_name}, User: {user_id}")
    
    try:
        # Delete the collection
        utils.delete_user_collection(collection_name, user_id)
        
        response_data = {
            "message": "Collection deleted successfully",
            "collection_name": collection_name,
            "user_id": user_id
        }
        
        return response_data
        
    except HTTPException:
        utils.logger.error(f"HTTPException during delete collection - Collection: {collection_name}, User: {user_id}")
        raise
    except Exception as e:
        utils.logger.error(f"Error deleting collection {collection_name} for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")

@app.get("/ai/ask")
def ask_ai(query: str, current_user = Depends(get_current_user)):
    try:
        response = rag_ai.invoke({'messages':[HumanMessage(content=str(query))],'user_id':current_user.id}) 
        return JSONResponse(content=response['messages'][-1].content)
    except Exception as e:
        utils.logger.error(f"Error during asking AI: {e}")
        return HTTPException(status_code=500, detail=f"Error during asking AI: {e}")

@app.post('/ai/ask/feedback')
def feedback(payload: FeedbackRequest = Body(...), current_user = Depends(get_current_user)):
    try:
        user_id = current_user.id
        query = payload.query if payload.query else None
        is_positive_feedback = payload.is_positive_feedback if  payload.is_positive_feedback else None
        comments = payload.comments if payload.comments else None

        target_chat = utils.get_latest_or_previous_chat(user_id, query)
        if not target_chat:
            return JSONResponse(status_code=404, content="Chat not found")
        # utils.logger.info(f"chat target {target_chat}")
        utils.logger.info(f"payload: {target_chat['query']}")
        input = target_chat['query']
        output = target_chat['llm_response']
        feedback = {
            "user_id": user_id,
            "input": input,
            "output": output,
            "is_positive_feedback": is_positive_feedback,
            "comments": comments
        }
        feedback_document = utils.prepare_feedback_document(feedback)
        utils.logger.info(f"prepared document: {feedback_document}")
        utils.save_feedback_document(feedback_document)
        # utils.logger.info(f"Feedback saved for user: {user_id}, query: {payload.query if payload.query else None}, is_positive_feed: {payload.is_positive_feedback}, comments: {comments}")
        return JSONResponse(content={"message": "Feedback saved successfully"})
    except Exception as e:
        utils.logger.error(f"Error during feedback: {e}")
        return JSONResponse(status_code=500, content=f"Error during feedback: {e}")

# Log application startup
utils.logger.info("NeuroDesk Backend application started successfully")

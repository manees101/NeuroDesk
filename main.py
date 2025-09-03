import tempfile
from typing import Union
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import utils
from agent import rag_ai
from langchain_core.messages import HumanMessage
from db.feedback import FeedbackRequest
from generate_pdf import generatePdf
app = FastAPI()
# generatePdf() // TODO: delete this file not needed in  the project
class UploadRequest(BaseModel):
    user_id: str

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
    user_id: str = Form(...)
):
    """
    Upload a PDF document, extract text, create embeddings, and store in ChromaDB.
    Requires user_id in the form data.
    """
    utils.logger.info(f"Document upload request received for user: {user_id}, filename: {file.filename}")
    
    # Validate user_id
    utils.validate_user_id(user_id)
    
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
    user_id: str, 
    collection_name: str = None,
    n_results: int = 5
):
    """
    Search documents using semantic similarity for a specific user.
    If collection_name is not provided, searches across all user's collections.
    """
    utils.logger.info(f"Search request received - Query: '{query}', User: {user_id}, Collection: {collection_name}, Results: {n_results}")
    
    try:
        # Validate user_id
        utils.validate_user_id(user_id)
        
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
async def list_collections(user_id: str):
    """
    List all available document collections for a specific user.
    """
    utils.logger.info(f"List collections request received for user: {user_id}")
    
    try:
        # Validate user_id
        utils.validate_user_id(user_id)
        
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
async def delete_collection(collection_name: str, user_id: str):
    """
    Delete a specific collection for a user.
    """
    utils.logger.info(f"Delete collection request received - Collection: {collection_name}, User: {user_id}")
    
    try:
        # Validate user_id
        utils.validate_user_id(user_id)
        
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
def ask_ai(query: str, user_id: str):
    """
    Ask the AI a question.
    """
    try:
        response = rag_ai.invoke({'messages':[HumanMessage(content=str(query))],'user_id':user_id}) 
        return JSONResponse(content=response['messages'][-1].content)
    except Exception as e:
        utils.logger.error(f"Error during asking AI: {e}")
        return HTTPException(status_code=500, detail=f"Error during asking AI: {e}")
# Log application startup
utils.logger.info("NeuroDesk Backend application started successfully")

@app.post('/ai/ask/feedback')
def feedback(payload: FeedbackRequest = Body(...)):
    """
    Feedback on the AI's response.
    """
    try:
        query = payload.query if payload.query else None
        user_id = payload.user_id
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
        # utils.logger.info(f"Feedback saved for user: {payload.user_id}, query: {payload.query if payload.query else None}, is_positive_feed: {payload.is_positive_feed}, comments: {comments}")
        return JSONResponse(content={"message": "Feedback saved successfully"})
    except Exception as e:
        utils.logger.error(f"Error during feedback: {e}")
        return JSONResponse(status_code=500, content=f"Error during feedback: {e}")


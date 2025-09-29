import os
import logging
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from fastapi import HTTPException
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import re
from db.users import UserChat, DocSummary
from db.mongo import db
from datetime import datetime
from typing import Optional
from langchain_core.documents import Document
from chromadb import CloudClient
from pymongo import DESCENDING
from langchain_openai import ChatOpenAI
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

# Initialize OpenAI embeddings
logger.info("Initializing OpenAI embeddings...")
try:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    logger.info("OpenAI embeddings initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI embeddings: {str(e)}")
    raise

client = CloudClient(
    api_key=os.environ["CHROMA_API_KEY"],
    tenant=os.environ["CHROMA_TENANT"],
    database=os.environ["CHROMA_DATABASE"]
)
# Initialize text splitter
logger.info("Initializing text splitter...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, 
    chunk_overlap=200
)
logger.info("Text splitter initialized successfully")

# Persist directory for ChromaDB
# persist_directory = "./chroma_db"   
# if not os.path.exists(persist_directory):
#     logger.info(f"Creating persist directory: {persist_directory}")
#     os.makedirs(persist_directory)
# else:
#     logger.info(f"Using existing persist directory: {persist_directory}")

def create_safe_filename(filename: str) -> str:
    """
    Create a safe filename by removing or replacing problematic characters.
    Complies with ChromaDB collection name validation rules.
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Safe filename with problematic characters replaced
    """
    # Remove .pdf extension first
    safe_name = filename.replace('.pdf', '').replace('.PDF', '')
    
    # Replace problematic characters with underscores
    # Only allow [a-zA-Z0-9._-] characters
    problematic_chars = r'[^a-zA-Z0-9._-]'
    safe_name = re.sub(problematic_chars, '_', safe_name)
    
    # Remove multiple consecutive underscores
    safe_name = re.sub(r'_+', '_', safe_name)
    
    # Remove leading/trailing underscores and dots
    safe_name = safe_name.strip('_.')
    
    # Ensure the name is not empty
    if not safe_name:
        safe_name = 'document'
    
    # Ensure it starts with alphanumeric character
    if safe_name and not safe_name[0].isalnum():
        safe_name = 'doc_' + safe_name
    
    # Ensure it ends with alphanumeric character
    if safe_name and not safe_name[-1].isalnum():
        safe_name = safe_name + '_doc'
    
    # Limit length to avoid extremely long collection names (ChromaDB limit is 512)
    if len(safe_name) > 50:
        safe_name = safe_name[:50]
    
    # Final check: ensure it's at least 3 characters
    if len(safe_name) < 3:
        safe_name = 'doc_' + safe_name
    
    return safe_name

def process_pdf_file(file_path: str, filename: str, user_id: str):
    """Process PDF file using LangChain components."""
    logger.info(f"Processing PDF file: {filename} for user: {user_id}")
    
    try:
        # Load PDF using PyPDFLoader
        logger.debug(f"Loading PDF from path: {file_path}")
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        
        logger.info(f"PDF loaded successfully. Pages found: {len(pages)}")
        
        if not pages:
            logger.warning(f"No content found in PDF: {filename}")
            raise HTTPException(status_code=400, detail="No content found in PDF")
        
        # Split documents into chunks
        logger.debug("Splitting documents into chunks...")
        pages_split = text_splitter.split_documents(pages)
        logger.info(f"Documents split into {len(pages_split)} chunks")
        
        # Create collection name based on user_id and filename
        safe_filename = create_safe_filename(filename)
        collection_name = f"user_{user_id}_doc_{safe_filename}"
        logger.info(f"Created collection name: {collection_name}")
        
        # Create vector store
        logger.debug("Creating vector store with ChromaDB...")
        Chroma.from_documents(
            pages_split,
            embeddings,
            # persist_directory=persist_directory,
            client=client,
            collection_name=collection_name
        )
        logger.info(f"Vector store created successfully for collection: {collection_name}")
        all_text = " ".join([doc.page_content for doc in pages_split[:10]])
        prompt = f"""
                You are an expert document summarizer. Read the following PDF text and generate a concise summary.

                Requirements:
                - Capture the main ideas, key points, and overall purpose of the document.
                - Keep the summary clear, factual, and to the point.
                - Do not copy large portions of text verbatim.
                - Write in 1–3 short paragraphs.

                Text to summarize:
                \"\"\"{all_text}\"\"\"

                Summary:
                """
        llm_response = llm.invoke(prompt)
        pdf_summary_obj = DocSummary(user_id=user_id, filename=filename, collection_name = collection_name, summary = llm_response.content)
        summary_saved_response = db["doc_summary"].insert_one(pdf_summary_obj.model_dump())
        logger.info(f"{filename} Summary saved in DB successfully: {summary_saved_response}")
        result = {
            "pages_loaded": len(pages),
            "chunks_created": len(pages_split),
            "collection_name": collection_name,
            "user_id": user_id
        }
        
        logger.info(f"PDF processing completed successfully. Result: {result}")
        return result
        
    except HTTPException:
        logger.error(f"HTTPException during PDF processing: {filename}")
        raise
    except Exception as e:
        logger.error(f"Error processing PDF {filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@tool()
def search_in_collection(query: str, collection_name: str, user_id: str, n_results: int = 5):
    """
    Search a specific document collection for relevant information for a user.

    Args:
        query (str): The search query string.
        collection_name (str): The name of the collection to search within.
        user_id (str): The unique identifier for the user who owns the collection.
        n_results (int, optional): The maximum number of results to return. Defaults to 5.

    Returns:
        list: List of the top matching document chunks with metadata from the specified collection.
    """
    logger.info(f"Searching in specific collection: {collection_name}")
    
    # Verify the collection belongs to the user
    if not collection_name.startswith(f"user_{user_id}_"):
        logger.warning(f"Access denied: User {user_id} attempted to access collection {collection_name}")
        raise HTTPException(status_code=403, detail="Access denied to this collection")
    
    logger.debug(f"Collection access validation passed: {collection_name}")
    
    vector_store = Chroma(
        # persist_directory=persist_directory,
        client=client,
        embedding_function=embeddings,
        collection_name=collection_name
    )
    
    retriever = vector_store.as_retriever(
        search_type="similarity", 
        search_kwargs={"k": n_results}
    )
    
    logger.debug(f"Executing search query: '{query}'")
    docs = retriever.invoke(query)
    logger.info(f"Search completed. Found {len(docs)} documents")
    
    results = []
    for i, doc in enumerate(docs):
        results.append({
            "document": doc.page_content,
            "metadata": doc.metadata,
            "rank": i + 1,
            "collection_name": collection_name
        })
    
    return results

@tool()
def search_across_user_collections(query: str, user_id: str, n_results: int = 5, state_context: dict = None) -> tuple[list, int]:
    """
    Search all documents uploaded by a user for relevant information.

    Args:
        query (str): The search query string.
        user_id (str): The unique identifier for the user whose documents will be searched.
        n_results (int, optional): The maximum number of results to return. Defaults to 5.
        state_context (dict, optional): Current agent state context for accessing resolved values.

    Returns:
        tuple: (top_results, collections_count)
            - top_results (list): List of the top matching document chunks with metadata.
            - collections_count (int): The number of collections searched for the user.
    """
    # If state_context is provided, try to resolve user_id from it
    if state_context and isinstance(user_id, str) and user_id in state_context:
        user_id = state_context[user_id]
    
    logger.info(f"Searching across all collections for user: {user_id}")
    
    # import chromadb
    # client = chromadb.PersistentClient()  ---> for local dev
    collections = client.list_collections()
    
    user_collections = [col for col in collections if col.name.startswith(f"user_{user_id}_")]
    logger.info(f"Found {len(user_collections)} collections for user {user_id}")
    
    if not user_collections:
        logger.warning(f"No collections found for user: {user_id}")
        return ([],0)
    
    all_results = []
    for collection in user_collections:
        logger.debug(f"Searching in collection: {collection.name}")
        
        vector_store = Chroma(
            # persist_directory=persist_directory,
            client=client,
            embedding_function=embeddings,
            collection_name=collection.name
        )
        
        retriever = vector_store.as_retriever(
            search_type="similarity", 
            search_kwargs={"k": n_results}
        )
        
        docs = retriever.invoke(query)
        logger.debug(f"Found {len(docs)} documents in collection {collection.name}")
        
        for i, doc in enumerate(docs):
            all_results.append({
                "document": doc.page_content,
                "metadata": doc.metadata,
                "rank": i + 1,
                "collection_name": collection.name
            })
    
    # Sort by rank and take top n_results
    all_results.sort(key=lambda x: x["rank"])
    top_results = all_results[:n_results]
    
    logger.info(f"Cross-collection search completed: {len(top_results)} results returned from {len(user_collections)} collections")
    return top_results, len(user_collections)

def get_user_collections(user_id: str):
    """Get all collections for a specific user."""
    collections = client.list_collections()
    logger.debug(f"Total collections in database: {len(collections)}")
    
    # Filter collections for the specific user
    user_collections = [col for col in collections if col.name.startswith(f"user_{user_id}_")]
    logger.info(f"Found {len(user_collections)} collections for user {user_id}")
    
    collection_info = []
    for collection in user_collections:
        # Extract document name from collection name
        doc_name = collection.name.replace(f"user_{user_id}_doc_", "")
        count = collection.count()
        logger.debug(f"Collection: {collection.name}, Document: {doc_name}, Count: {count}")
        
        collection_info.append({
            "name": collection.name,
            "document_name": doc_name,
            "count": count
        })
    
    return collection_info

def delete_user_collection(collection_name: str, user_id: str):
    """Delete a specific collection for a user."""
    logger.info(f"Delete collection request received - Collection: {collection_name}, User: {user_id}")
    
    # Verify the collection belongs to the user
    if not collection_name.startswith(f"user_{user_id}_"):
        logger.warning(f"Access denied: User {user_id} attempted to delete collection {collection_name}")
        raise HTTPException(status_code=403, detail="Access denied to this collection")
    
    logger.debug(f"Collection access validation passed: {collection_name}")
    
    # Check if collection exists
    collections = client.list_collections()
    collection_names = [col.name for col in collections]
    
    if collection_name not in collection_names:
        logger.warning(f"Collection not found: {collection_name}")
        raise HTTPException(status_code=404, detail="Collection not found")
    
    logger.info(f"Collection found, proceeding with deletion: {collection_name}")
    
    # Delete the collection
    client.delete_collection(collection_name)
    logger.info(f"Collection deleted successfully: {collection_name}")

def validate_user_id(user_id: str):
    """Validate user_id parameter."""
    if not user_id or user_id.strip() == "":
        logger.warning("Request rejected: user_id is empty")
        raise HTTPException(status_code=400, detail="user_id is required")
    
    logger.debug(f"User ID validation passed: {user_id}")
    return user_id

def validate_pdf_file(filename: str, file_size: int = None):
    """Validate PDF file upload."""
    # Check if file is PDF
    if not filename.lower().endswith('.pdf'):
        logger.warning(f"Upload request rejected: Non-PDF file attempted: {filename}")
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    logger.debug(f"File type validation passed: {filename}")
    
    # Check file size (optional: limit to 10MB)
    if file_size and file_size > 10 * 1024 * 1024:
        logger.warning(f"Upload request rejected: File too large: {filename}, size: {file_size}")
        raise HTTPException(status_code=400, detail="File size too large. Maximum 10MB allowed.")
    
    logger.debug(f"File size validation passed: {filename}, size: {file_size}")

def cleanup_temp_file(temp_file_path: str):
    """Clean up temporary file with error handling."""
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            logger.debug(f"Cleaning up temporary file: {temp_file_path}")
            os.unlink(temp_file_path)
        except Exception as cleanup_error:
            logger.error(f"Error cleaning up temporary file {temp_file_path}: {str(cleanup_error)}")

def save_chat_history(user_id: str, messages, save_to_text_file: bool = False):
    """
    Save chat history for a user either to a text file or MongoDB.
    
    Args:
        user_id (str): The user's unique identifier.
        messages (list): List of HumanMessage and AIMessage objects in sequence.
        save_to_text_file (bool): Whether to save the conversation to a text file.
    """
    filename = f"{user_id}.txt"

    try:
        if save_to_text_file:
            with open(filename, "w") as log_file:
                for message in messages:
                    if hasattr(message, 'content') and message.content.strip() != "exit":
                        if isinstance(message, HumanMessage):
                            log_file.write(f"You: {message.content}\n")
                        elif isinstance(message, AIMessage):
                            log_file.write(f"AI: {message.content}\n")
            logger.info(f"Conversation logged to {filename}")
        else:
            ai_msg:AIMessage = messages[-1]
            user_msg = None
            tool_msg = None
            logger.info(f"saving chat history { len(messages)}")
            i = len(messages) - 2
            while i >= 0:
                target_msg = messages[i]
                logger.info(f"\n is_user_msg: {isinstance(target_msg, HumanMessage)}")
                if not user_msg and isinstance(target_msg, HumanMessage):
                    user_msg = target_msg
                elif not tool_msg and isinstance(target_msg, ToolMessage):
                    tool_msg = target_msg
                if tool_msg and user_msg:
                    break
                i -= 1
            if ai_msg and user_msg:
                user_chat = UserChat(
                            user_id = user_id,
                            query = user_msg.content,
                            retrieved_documents = tool_msg.content if tool_msg else None,
                            llm_response = ai_msg.content,
                            created_at = datetime.now(),
                            updated_at = datetime.now(),
                        )
                response = db['user_chat'].insert_one(user_chat.model_dump())
                logger.info(f"chat saved {response}")

    except Exception as e:
        logger.error(f"Failed to save chat history for {user_id}: {str(e)}")

def load_chat_history(user_id: str, save_to_text_file: bool = False):
    """
    Load chat history for a user from a text file named <user_id>.txt.
    Args:
        user_id (str): The user's unique identifier.
    Returns:
        list: List of HumanMessage and AIMessage objects.
    """
    filename = f"{user_id}.txt"
    messages = []
    try:
        if save_to_text_file:
            with open(filename, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("You:"):
                        content = line[len("You:"):].strip()
                        messages.append(HumanMessage(content=content))
                    elif line.startswith("AI:"):
                        content = line[len("AI:"):].strip()
                        messages.append(AIMessage(content=content))
            logger.info(f"Loaded chat history from {filename}")
        else:
            user_chats = list(db['user_chat'].find({"user_id": user_id}).sort("created_at", DESCENDING))
            logger.info(f"Loaded chat history from DB {len(user_chats)}")
            for chat in user_chats:
                messages.append(HumanMessage(content=chat.get("query")))
                messages.append(AIMessage(content=chat.get("llm_response")))
    except FileNotFoundError:
        logger.info(f"No previous conversation log found for {user_id}. Starting fresh.")
    except Exception as e:
        logger.error(f"Failed to load chat history for {user_id}: {str(e)}")
    return messages

# Log utility module initialization
logger.info("Utils module initialized successfully")

def get_latest_or_previous_chat(user_id: str, query: Optional[str] = None):
    """ utility function which returns the latest chat if only user_id is provided, otherwise returns the previous chat if query is provided """
    if user_id and query:
        chats = db['user_chat'].find({'user_id':user_id,"query":query}).sort("created_at", DESCENDING).limit(1)
        chats = list(chats)
        return chats[0] if chats else None
    elif user_id:
        chats = db['user_chat'].find({"user_id": user_id}).sort('created_at', DESCENDING)
        chats = list(chats)
        return chats[0] if chats else None
    else:
        raise HTTPException(status_code=400, detail="user_id and query are required")
    
def prepare_feedback_document(feedback_entry: dict) -> Document:
    content = (
        f"User ID: {feedback_entry['user_id']}\n"
        f"Input: {feedback_entry['input']}\n"
        f"Output: {feedback_entry['output']}\n"
        f"Is Feedback Positive: {feedback_entry['is_positive_feedback']}\n"
        f"Comments: {feedback_entry['comments']}"
    )
    return Document(page_content=content, metadata={"type": "feedback"})

def save_feedback_document(feedback_document: Document):
    """Save feedback document to ChromaDB."""
    # ========== Use for local ===============
    # persist_directory = "./feedback_db"
    # if not os.path.exists(persist_directory):
    #     os.makedirs(persist_directory)
    logger.info(f"document", feedback_document)
    vector_store = Chroma(
        # persist_directory=persist_directory,
        client=client,
        embedding_function=embeddings,
        collection_name="feedback"
    )
    vector_store.add_documents([feedback_document])

def get_similar_feedback_documents(query: str, n_results: int = 5):
    """Get similar feedback documents from ChromaDB."""
    # persist_directory = "./feedback_db"
    vector_store = Chroma(
        # persist_directory=persist_directory,
        client=client,
        embedding_function=embeddings,
        collection_name="feedback"
    )
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": n_results})
    return retriever.invoke(query)
"""
FastAPI application for Jurix - Legal Document Assistant
Provides REST API endpoints for document ingestion and legal query answering.
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from pathlib import Path
import shutil

from ingestion import add_documents_to_db
from llm import answer_query_unified, analyze_and_generate_queries
from db import test_connection

# Initialize FastAPI app
app = FastAPI(
    title="Jurix Legal Assistant API",
    description="AI-powered legal document ingestion and query system",
    version="1.0.0"
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create documents directory
DOCUMENTS_DIR = Path("documents")
DOCUMENTS_DIR.mkdir(exist_ok=True)

# Pydantic models
class QueryRequest(BaseModel):
    query: str
    debug: bool = False

class QueryResponse(BaseModel):
    answer: str
    query_plan: Optional[dict] = None
    debug_info: Optional[dict] = None

class HealthResponse(BaseModel):
    status: str
    database_connected: bool
    message: str

class DocumentUploadResponse(BaseModel):
    success: bool
    filename: str
    title: str
    message: str

class StatsResponse(BaseModel):
    documents_processed: int
    total_queries: int

# Global stats (in production, use a database)
stats = {
    "documents_processed": 0,
    "total_queries": 0
}

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check if the API and database are healthy.
    """
    try:
        test_connection()
        return HealthResponse(
            status="healthy",
            database_connected=True,
            message="API and database are operational"
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            database_connected=False,
            message=f"Database connection failed: {str(e)}"
        )

# Document ingestion endpoint
@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...)
):
    """
    Upload and process a PDF document for ingestion into the database.
    
    Args:
        file: PDF file to upload
        title: Title/description of the document
    
    Returns:
        Success status and message
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Save uploaded file
        file_path = DOCUMENTS_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the document
        add_documents_to_db(file.filename, title)
        
        # Update stats
        stats["documents_processed"] += 1
        
        return DocumentUploadResponse(
            success=True,
            filename=file.filename,
            title=title,
            message=f"Document '{file.filename}' processed successfully"
        )
    
    except Exception as e:
        # Clean up file if it exists
        if file_path.exists():
            os.remove(file_path)
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}"
        )

# Query endpoint with debug support
@app.post("/api/query", response_model=QueryResponse)
async def query_legal_assistant(request: QueryRequest):
    """
    Query the legal assistant with natural language questions.
    
    Args:
        request: QueryRequest containing the user's query and debug flag
    
    Returns:
        AI-generated answer and optional debug information
    """
    try:
        # Update stats
        stats["total_queries"] += 1
        
        debug_info = {}
        
        # Analyze query if debug mode is enabled
        if request.debug:
            query_plan = analyze_and_generate_queries(request.query)
            debug_info["query_plan"] = query_plan
            debug_info["legal_docs_queries"] = len(query_plan.get("legal_docs", []))
            debug_info["cases_queries"] = len(query_plan.get("cases", []))
        
        # Get answer from unified query system
        answer = answer_query_unified(request.query)
        
        return QueryResponse(
            answer=answer,
            query_plan=debug_info.get("query_plan") if request.debug else None,
            debug_info=debug_info if request.debug else None
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

# Analyze query endpoint (returns query plan without executing)
@app.post("/api/query/analyze")
async def analyze_query(request: QueryRequest):
    """
    Analyze a query and return the search plan without executing it.
    
    Args:
        request: QueryRequest containing the user's query
    
    Returns:
        Query analysis plan
    """
    try:
        query_plan = analyze_and_generate_queries(request.query)
        
        return {
            "query": request.query,
            "legal_docs_queries": query_plan.get("legal_docs", []),
            "cases_queries": query_plan.get("cases", []),
            "will_search_legal_docs": len(query_plan.get("legal_docs", [])) > 0,
            "will_search_cases": len(query_plan.get("cases", [])) > 0
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing query: {str(e)}"
        )

# Statistics endpoint
@app.get("/api/stats", response_model=StatsResponse)
async def get_statistics():
    """
    Get current system statistics.
    
    Returns:
        Number of documents processed and total queries
    """
    return StatsResponse(
        documents_processed=stats["documents_processed"],
        total_queries=stats["total_queries"]
    )

# Test database connection endpoint
@app.get("/api/database/test")
async def test_database_connection():
    """
    Test database connectivity.
    
    Returns:
        Connection status and message
    """
    try:
        test_connection()
        return {
            "connected": True,
            "message": "Database connection successful"
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Database connection failed: {str(e)}"
        }

# Root endpoint
@app.get("/")
async def root():
    """
    API root endpoint with welcome message and available endpoints.
    """
    return {
        "message": "Welcome to Jurix Legal Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "upload_document": "/api/documents/upload",
            "query": "/api/query",
            "analyze_query": "/api/query/analyze",
            "statistics": "/api/stats",
            "test_database": "/api/database/test",
            "docs": "/docs"
        }
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

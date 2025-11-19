# Jurix - Legal Document RAG System

A comprehensive legal document retrieval and question-answering system using RAG (Retrieval-Augmented Generation) architecture with vector embeddings.

---

## 🚀 FastAPI Endpoints

### Base URL
```
http://localhost:8000
```

### 📝 **1. Query Legal Assistant**

**POST** `/api/query`

Query the legal assistant with natural language questions. Supports both legal documents (Constitution, IPC, IT Act) and case law.

**Request Body:**
```json
{
  "query": "What is Article 21?",
  "debug": false
}
```

**Response:**
```json
{
  "answer": "Article 21 of the Constitution states...",
  "query_plan": {
    "legal_docs": ["Article 21"],
    "cases": []
  },
  "debug_info": {
    "legal_docs_queries": 1,
    "cases_queries": 0
  }
}
```

**Parameters:**
- `query` (string, required): User's legal question
- `debug` (boolean, optional): Enable debug mode to see query analysis

---

### 📤 **2. Upload Document**

**POST** `/api/documents/upload`

Upload PDF documents for ingestion into the database.

**Request:** `multipart/form-data`
- `file`: PDF file
- `title`: Document title/description

**Example (cURL):**
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@constitution.pdf" \
  -F "title=Constitution of India"
```

**Response:**
```json
{
  "success": true,
  "filename": "constitution.pdf",
  "title": "Constitution of India",
  "message": "Document 'constitution.pdf' processed successfully"
}
```

---

### 🔍 **3. Analyze Query**

**POST** `/api/query/analyze`

Analyze a query to see which databases will be searched without executing the query.

**Request Body:**
```json
{
  "query": "What does Article 21 say and show me related case law"
}
```

**Response:**
```json
{
  "query": "What does Article 21 say and show me related case law",
  "legal_docs_queries": ["Article 21"],
  "cases_queries": ["Article 21 case law"],
  "will_search_legal_docs": true,
  "will_search_cases": true
}
```

---

### ❤️ **4. Health Check**

**GET** `/health`

Check API and database health status.

**Response:**
```json
{
  "status": "healthy",
  "database_connected": true,
  "message": "API and database are operational"
}
```

---

### 📊 **5. Statistics**

**GET** `/api/stats`

Get system statistics (documents processed and total queries).

**Response:**
```json
{
  "documents_processed": 15,
  "total_queries": 342
}
```

---

### 🗄️ **6. Test Database**

**GET** `/api/database/test`

Test database connectivity.

**Response:**
```json
{
  "connected": true,
  "message": "Database connection successful"
}
```

---

### 🏠 **7. Root Endpoint**

**GET** `/`

API information and available endpoints.

**Response:**
```json
{
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
```

---

## 🛠️ Running the API

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Start Server

```bash
# Run with Python
python main.py

# Or use uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

---

## 📋 API Examples

### Example 1: Simple Query
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Section 420 IPC?",
    "debug": false
  }'
```

### Example 2: Query with Debug
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me case law on property disputes",
    "debug": true
  }'
```

### Example 3: Upload Document
```bash
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@ipc.pdf" \
  -F "title=Indian Penal Code"
```

### Example 4: Analyze Query
```bash
curl -X POST http://localhost:8000/api/query/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Article 14 and related judgments"
  }'
```

### Example 5: Health Check
```bash
curl http://localhost:8000/health
```

### Example 6: Get Statistics
```bash
curl http://localhost:8000/api/stats
```

---

## 🔧 Error Responses

All endpoints return standard HTTP status codes:

- `200 OK`: Successful request
- `400 Bad Request`: Invalid input (e.g., non-PDF file)
- `500 Internal Server Error`: Server/processing error

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## 🌐 CORS

CORS is enabled for all origins by default. For production, update the `allow_origins` in `main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📦 Dependencies

```
fastapi
uvicorn[standard]
python-multipart
psycopg2-binary
google-genai
langchain
langchain-community
python-dotenv
```
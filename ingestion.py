import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from google import genai
import json
from typing import Optional
from db import insert_many

from dotenv import load_dotenv
load_dotenv()

# Initialize Gemini AI Client
client = genai.Client(api_key=f"{os.getenv('GOOGLE_API_KEY')}")

def get_embeddings(chunks: list[str]) -> list[list[float]]:
    """
    Fetch embedding vector using Google Gemini API.
    """
    try:
        print("Fetching embeddings from Gemini API...")
        embeddings = []

        # Split chunks into batches of 100
        for i in range(0, len(chunks), 100):
            batch = chunks[i:i + 100]
            result = client.models.embed_content(
                model="text-embedding-004",
                contents=batch,
            )
            embeddings.extend([embedding.values for embedding in result.embeddings])
        print("Embeddings fetched successfully.")
        return embeddings
    
    except Exception as e:
        print(f"❌ Error fetching embedding: {e}")
        return None

def process_pdf(file_name: str) -> list[str]:
    """
    Process PDF file and return text chunks.
    """
    try:
        print("Processing PDF...")
        file_path = os.path.join("documents", file_name)
        loader = PyPDFLoader(file_path)
        pages = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(pages)
        print(f"PDF processed into {len(chunks)} chunks.")
        return [chunk.page_content for chunk in chunks]
    
    except Exception as e:
        print(f"❌ Error processing PDF: {e}")
        return None
    
def add_documents_to_db(
    file_name: str,
    title: str,
):
    """
    Process PDF and add documents to the database.
    """
    print(f"Adding documents from {file_name} to the database...")
    chunks = process_pdf(file_name)
    if not chunks:
        print("No valid chunks found.")
        return

    embeddings = get_embeddings(chunks)
    if not embeddings:
        print("Failed to get embeddings.")
        return
    
    records = [(chunk, embedding, title) for chunk, embedding in zip(chunks, embeddings)]
    insert_many("legal_docs", records)
    print(f"Document {file_name} added to the database.")

def add_texts_to_db(
    texts: list[str],
    title: str,
):
    """
    Add plain text documents to the database.
    """
    print(f"Adding {len(texts)} text documents to the database...")
    embeddings = get_embeddings(texts)
    if not embeddings:
        print("Failed to get embeddings.")
        return
    
    records = [(text, embedding, title) for text, embedding in zip(texts, embeddings)]
    insert_many("legal_docs", records)
    print(f"{len(texts)} text documents added to the database.")

def process_case_for_ingestion(structured_content: dict) -> list[dict]:
    """
    Process the 4 key sections with optimized chunk sizes.
    Returns None if critical processing fails (e.g., fact summarization).
    """
    chunks = []
    
    # 1. FACTS - Summarize (no splitting)
    if "Facts" in structured_content and structured_content["Facts"]:
        from llm import summarise
        print("   Summarizing facts...")
        summary = summarise(structured_content["Facts"])
        if not summary:
            print("❌ Failed to summarize facts. Aborting case processing.")
            return None
        chunks.append({
            "section_type": "Facts",
            "chunk_id": 0,
            "content": summary,
            "char_count": len(summary)
        })
        print(f"   ✓ Facts summarized ({len(summary)} chars)")
    
    # 2. ISSUES - Split with smaller chunks
    if "Issues" in structured_content and structured_content["Issues"]:
        content = structured_content["Issues"]
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200,  # ~180 words
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " "]
        )
        issue_chunks = splitter.split_text(content)
        for i, chunk in enumerate(issue_chunks):
            chunks.append({
                "section_type": "Issues",
                "chunk_id": i,
                "content": chunk,
                "char_count": len(chunk)
            })
    
    # 3. COURT'S REASONING - Split with moderate chunks
    if "Court's Reasoning" in structured_content and structured_content["Court's Reasoning"]:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,  # ~225 words
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " "]
        )
        reasoning_chunks = splitter.split_text(structured_content["Court's Reasoning"])
        for i, chunk in enumerate(reasoning_chunks):
            chunks.append({
                "section_type": "Court's Reasoning",
                "chunk_id": i,
                "content": chunk,
                "char_count": len(chunk)
            })
    
    # 4. CONCLUSION - Usually keep as-is, split only if very long
    if "Conclusion" in structured_content and structured_content["Conclusion"]:
        content = structured_content["Conclusion"]
        if len(content) > 2000:  # Lower threshold
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1200,
                chunk_overlap=150,
                separators=["\n\n", "\n", ". ", " "]
            )
            conclusion_chunks = splitter.split_text(content)
            for i, chunk in enumerate(conclusion_chunks):
                chunks.append({
                    "section_type": "Conclusion",
                    "chunk_id": i,
                    "content": chunk,
                    "char_count": len(chunk)
                })
        else:
            chunks.append({
                "section_type": "Conclusion",
                "chunk_id": 0,
                "content": content,
                "char_count": len(content)
            })
    
    return chunks

def insert_case_into_db(
    doc_id: str,
    case_title: str,
    structured_content: dict,
):
    """
    Process case sections and insert into the database.
    Returns True if successful, False if failed.
    """
    print(f"Processing case ID {doc_id} and name {case_title} for database insertion...")
    chunks = process_case_for_ingestion(structured_content)
    if not chunks:
        print("❌ Failed to process case. Skipping database insertion.")
        return False

    # with open('debug_chunks.json', 'w', encoding='utf-8') as f:
    #    json.dump(chunks, f, indent=2, ensure_ascii=False)

    texts = [chunk["content"] for chunk in chunks]
    embeddings = get_embeddings(texts)
    if not embeddings:
        print("❌ Failed to get embeddings for the case. Skipping database insertion.")
        return False
    
    # Prepare records for insertion
    records = []
    for chunk, embedding in zip(chunks, embeddings):
        records.append((
            doc_id,
            case_title,
            chunk["section_type"],
            chunk["content"],
            embedding
        ))
    
    # Insert into database
    try:
        insert_many("cases", records)
        print(f"✅ Case ID {doc_id} inserted into database with {len(chunks)} chunks.")
        return True
    except Exception as e:
        print(f"❌ Failed to insert case into database: {e}")
        return False
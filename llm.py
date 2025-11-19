import os
from typing import Optional
from google import genai
from ingestion import get_embeddings
from db import fetch_similar_documents
from dotenv import load_dotenv
load_dotenv()

from prompts import (
    SUMMARIZE_FACTS_PROMPT,
)

# Initialize Gemini AI Client
client = genai.Client(api_key=f"{os.getenv('GOOGLE_API_KEY')}")

def get_gemini_response(context: list[dict], query: str) -> str:
    """
    Fetch response from Google Gemini API.
    """
    prompt = f"""
        You are a helpful legal assistant for Indian common people.  
        You have access to three key legal documents:  
        - The Indian Constitution  
        - The Indian Penal Code (IPC)  
        - The Information Technology (IT) Act  

        You will be given:
        1. A user’s question
        2. Retrieved context passages from these documents (if any)

        Your instructions:
        1. First, carefully read the retrieved context.  
        2. If the answer is clearly in the context, use it to answer concisely in points with headings.  
        3. After your answer, include a short citation in parentheses showing the source (for example, “(Constitution, Article 21)” or “(IPC, Section 420)”).  
        - If several passages contribute, cite each briefly (separated by commas).  
        - If no document name/section is obvious, cite the document name only.  
        4. If the context does not contain the answer, then use your own general knowledge to provide a best-effort answer. In that case, say “(Knowledge Base)” at the end.  
        5. Be factual and clear. Use simple English suitable for common people.  
        6. If you are unsure or the law has changed recently, include a brief note such as  
        “Please verify this information with the latest official sources.”  

        Format your output as:
        **Answer:** <your answer here>  
        **Source:** <document name/section or Knowledge Base”>  

        ---

        Context:
        {context}

        Question:
        {query}

        Answer:
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text
    
    except Exception as e:
        print(f"❌ Error fetching response: {e}")
        return "Error fetching response from Gemini API."

def answer_query(table_name: str, query: str) -> str:
    """
    Answer user query using context from the database and Google Gemini API.
    """
    try:
        # Step 1: Get embedding for the query
        query_embedding = get_embeddings([query])[0]
        
        # Step 2: Fetch similar documents from the database
        similar_docs = fetch_similar_documents(table_name, query_embedding, top_k=5)
        
        if not similar_docs:
            return "No relevant context found in the database."
        
        # Step 3: Prepare context for Gemini API
        context = [{"content": doc["content"], "title": doc["title"], "similarity": doc["similarity"]} for doc in similar_docs]
        
        # Step 4: Get response from Gemini API
        response = get_gemini_response(context, query)
        
        return response
    
    except Exception as e:
        print(f"❌ Error answering query: {e}")
        return "Error processing your query."

def summarise(text: str) -> Optional[str]:
    """
    Summarise given text using Google Gemini API.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=SUMMARIZE_FACTS_PROMPT.format(facts=text),
        )
        return response.text
    
    except Exception as e:
        print(f"❌ Error summarising text: {e}")
        return None
    
def analyze_and_generate_queries(user_query: str) -> dict:
    """
    Analyze user query and generate optimized search queries for both legal_docs and cases.
    
    Returns:
    {
        "legal_docs": ["query1", "query2", ...],
        "cases": ["query1", "query2", ...]
    }
    """
    prompt = f"""You are a legal research assistant for Indian law. Analyze the user's query and generate optimized search queries.

Your task:
1. Determine if the query needs information from:
   - **legal_docs** (Constitution, IPC, IT Act - statutory provisions)
   - **cases** (Court judgments - interpretations, precedents)
   - **both** (hybrid queries)

2. Generate SIMPLE, DIRECT search queries
3. For simple statutory queries (Article X, Section Y), keep it simple - just use the exact reference
4. Only search cases if user EXPLICITLY asks for: case law, judgments, precedents, court decisions, interpretations
5. For complex queries, generate 2-3 focused queries maximum
6. If a table is not needed, return empty array []

Guidelines for legal_docs queries:
- Keep it simple and direct
- For articles: just "Article 21" or "Article 21 Constitution"
- For sections: just "Section 420 IPC" or "Section 66A IT Act"
- Don't add unnecessary words

Guidelines for cases queries:
- Only generate if user explicitly asks about cases/judgments/precedents
- Frame as "Whether..." for legal issues
- Keep focused on one issue per query

Output ONLY valid JSON (no markdown, no explanation):
{{
    "legal_docs": ["query1", "query2"],
    "cases": ["query1", "query2"]
}}

Examples:

User: "What is Article 21?"
{{
    "legal_docs": ["Article 21"],
    "cases": []
}}

User: "explain article 21 of constitution"
{{
    "legal_docs": ["Article 21 Constitution"],
    "cases": []
}}

User: "What is punishment for cheating under IPC?"
{{
    "legal_docs": ["Section 420 IPC"],
    "cases": []
}}

User: "Can a society be treated as a trust? Show me case law"
{{
    "legal_docs": [],
    "cases": ["society treated as trust precedents"]
}}

User: "What does Article 14 say and how have courts interpreted it?"
{{
    "legal_docs": ["Article 14"],
    "cases": ["Article 14 interpretation judicial review"]
}}

User Query: {user_query}

JSON Output:"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        
        # Parse JSON response
        import json
        import re
        
        # Extract JSON from response (handle markdown code blocks)
        text = response.text.strip()
        # Remove markdown code blocks if present
        text = re.sub(r'^```json?\s*|\s*```$', '', text, flags=re.MULTILINE)
        
        queries = json.loads(text)
        
        # Validate structure
        if not isinstance(queries, dict) or "legal_docs" not in queries or "cases" not in queries:
            raise ValueError("Invalid query structure")
        
        print(f"🔍 Query Analysis:")
        print(f"  legal_docs: {len(queries['legal_docs'])} queries")
        print(f"  cases: {len(queries['cases'])} queries")
        for i, q in enumerate(queries['legal_docs'], 1):
            print(f"    L{i}. {q}")
        for i, q in enumerate(queries['cases'], 1):
            print(f"    C{i}. {q}")
        
        return queries
    
    except Exception as e:
        print(f"⚠️ Query analysis failed: {e}")
        # Fallback: simple heuristic routing
        return {
            "legal_docs": [user_query] if any(keyword in user_query.lower() for keyword in ['section', 'article', 'act', 'ipc', 'constitution']) else [],
            "cases": [user_query] if any(keyword in user_query.lower() for keyword in ['case', 'judgment', 'precedent', 'court', 'interpretation']) else []
        }


def answer_query_unified(query: str) -> str:
    """
    Unified query answering using smart routing across legal_docs and cases.
    """
    try:
        print("\n" + "="*80)
        print("🔍 UNIFIED QUERY PROCESSING")
        print("="*80)
        print(f"📝 User Query: {query}")
        
        # Step 1: Analyze query and generate table-specific search queries
        print("\n[STEP 1] Analyzing query and generating search queries...")
        query_plan = analyze_and_generate_queries(query)
        
        print(f"\n📊 Query Plan Generated:")
        print(f"   - legal_docs queries: {len(query_plan['legal_docs'])}")
        print(f"   - cases queries: {len(query_plan['cases'])}")
        
        # Step 2: Execute searches across both tables
        print("\n[STEP 2] Executing vector searches...")
        all_results = []
        seen_content = set()  # Deduplication
        
        # Search legal_docs
        if query_plan["legal_docs"]:
            print(f"\n📚 Searching legal_docs table...")
            for idx, search_query in enumerate(query_plan["legal_docs"], 1):
                print(f"   Query {idx}: {search_query}")
                query_embedding = get_embeddings([search_query])[0]
                results = fetch_similar_documents("legal_docs", query_embedding, top_k=5)
                print(f"   ✓ Found {len(results)} results")
                
                for doc in results:
                    content_hash = hash(doc["content"][:100])
                    if content_hash not in seen_content:
                        seen_content.add(content_hash)
                        doc["source_table"] = "legal_docs"
                        all_results.append(doc)
        
        # Search cases
        if query_plan["cases"]:
            print(f"\n⚖️  Searching cases table...")
            for idx, search_query in enumerate(query_plan["cases"], 1):
                print(f"   Query {idx}: {search_query}")
                query_embedding = get_embeddings([search_query])[0]
                results = fetch_similar_documents("cases", query_embedding, top_k=5)
                print(f"   ✓ Found {len(results)} results")
                
                for doc in results:
                    content_hash = hash(doc["content"][:100])
                    if content_hash not in seen_content:
                        seen_content.add(content_hash)
                        doc["source_table"] = "cases"
                        all_results.append(doc)
        
        if not all_results:
            print("\n⚠️  No relevant legal information found")
            return "I couldn't find relevant information in the legal database for your query. Please try rephrasing your question or ensure the documents are uploaded."
        
        # Step 3: Rank by similarity and select top results
        print(f"\n[STEP 3] Ranking results...")
        print(f"   Total unique results: {len(all_results)}")
        all_results.sort(key=lambda x: x["similarity"], reverse=True)
        top_results = all_results[:8]  # Top 8 across both tables
        print(f"   Selecting top {len(top_results)} results")
        
        # Step 4: Prepare context with source information
        print("\n[STEP 4] Preparing context...")
        context = []
        for idx, doc in enumerate(top_results, 1):
            source = doc["source_table"]
            similarity = doc["similarity"]
            title = doc.get("title") or doc.get("case_title", "Untitled")
            section = doc.get("section_type", "")
            
            print(f"   {idx}. [{source}] {title[:50]}... (similarity: {similarity:.3f})")
            if section:
                print(f"      Section: {section}")
            
            context.append({
                "content": doc["content"],
                "title": title,
                "section_type": section,
                "source_table": source,
                "similarity": similarity
            })
        
        # Step 5: Generate comprehensive response
        print("\n[STEP 5] Generating AI response...")
        response = get_gemini_response_unified(context, query)
        print("   ✓ Response generated")
        
        print("\n" + "="*80)
        print("✅ QUERY PROCESSING COMPLETE")
        print("="*80 + "\n")
        
        return response
    
    except Exception as e:
        print(f"\n❌ Error answering query: {e}")
        import traceback
        traceback.print_exc()
        return "Error processing your query. Please try again."


def get_gemini_response_unified(context: list[dict], query: str) -> str:
    """
    Generate response from mixed context (legal_docs + cases).
    """
    # Separate context by source
    statutory_context = [c for c in context if c["source_table"] == "legal_docs"]
    case_context = [c for c in context if c["source_table"] == "cases"]
    
    # Format context
    formatted_context = ""
    
    if statutory_context:
        formatted_context += "\n## Statutory Provisions (Constitution, IPC, IT Act):\n"
        for i, doc in enumerate(statutory_context, 1):
            formatted_context += f"{i}. [{doc['title']}]\n{doc['content'][:600]}...\n\n"
    
    if case_context:
        formatted_context += "\n## Court Judgments & Precedents:\n"
        for i, doc in enumerate(case_context, 1):
            section = doc.get('section_type', '')
            section_info = f" ({section})" if section else ""
            formatted_context += f"{i}. [{doc['title']}]{section_info}\n{doc['content'][:600]}...\n\n"
    
    prompt = f"""You are a legal assistant helping common people understand Indian law.

You have retrieved relevant information from:
1. Statutory documents (Constitution, IPC, IT Act)
2. Court judgments and precedents

CRITICAL INSTRUCTIONS:
1. ONLY use information from the retrieved context below
2. DO NOT use your own knowledge or training data
3. If the context doesn't contain the answer, clearly state: "The provided documents don't contain information about this specific query."
4. For each answer, cite the exact source from the context

How to answer:
1. Analyze the user's question
2. Look for the answer ONLY in the retrieved context
3. Structure your response clearly:
   - Start with the statutory provision (if available in context)
   - Then explain court interpretations (if available in context)
4. Use simple language for common people
5. Cite sources clearly:
   - For statutes: (IPC Section 420), (Constitution Article 21)
   - For cases: (Case Name, Section Type)
6. If context doesn't answer the question, say so clearly and stop
7. Do NOT make assumptions or provide information not in the context

Retrieved Context:
{formatted_context}

User Question:
{query}

Answer (ONLY from context, with citations):"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text if response.text else "Error: Empty response from AI."
    
    except Exception as e:
        print(f"❌ Error generating response: {e}")
        return "Error generating response from AI."
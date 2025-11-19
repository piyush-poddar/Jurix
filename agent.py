from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool
from .ingestion import get_embeddings
from .db import fetch_similar_documents

MODEL_GEMINI_2_5_FLASH = "gemini-live-2.5-flash-preview"

def get_context(query: str):
    """
    Retrieve relevant context from the database for a given query.
    Args:
        query (str) [Always in english, irrespective of user query] : Relevant query derived from user question to obtain meaningful chunks from Vector DB.
    Returns:
        str: The relevant context for the user's query.
    """
    try:
        # Step 1: Get embedding for the query
        query_embedding = get_embeddings([query])[0]
        
        # Step 2: Fetch similar documents from the database
        similar_docs = fetch_similar_documents("legal_docs", query_embedding, top_k=5)
        
        if not similar_docs:
            return "No relevant context found in the database."
        
        # Step 3: Prepare context for Gemini API
        context = [{"content": doc["content"], "title": doc["title"], "similarity": doc["similarity"]} for doc in similar_docs]
        
        # Step 4: Get response from Gemini API
        # response = get_gemini_response(context, query)
        
        return context
    
    except Exception as e:
        print(f"❌ Error answering query: {e}")
        return "Error processing your query."

root_agent = LlmAgent(
    name="Jurix",
    model=MODEL_GEMINI_2_5_FLASH,
    description="A legal assistant for Indian common people.",
    instruction=f"""
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

        **
        Important: Always Generate a short response not more than 2-3 sentences.
        **

        Format your response as (always answer in the language which user wants):
        [your response here]  
        [source of response like document name/section or Knowledge Base” (include this in response only if the query is answered using context, otherwise NOT)]
        ---

        Context:
        Use `get_context` tool to retrieve relevant context for a user's query, when user asks about anything legal, otherwise use your intelligence to answer user's query.
        Use your intelligence to craft a meaningful query to obtain most relevant context from vector db.
        Keep this query concise and to the point to enhance retrieval.
        If you do not obtain a context from the vector db, then use your own knowledge to answer the user's query.
        Never say that you could not find any context, instead use your intelligence to answer user's query.
    """,
    tools=[get_context]
)
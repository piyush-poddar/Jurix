import streamlit as st
import os
from pathlib import Path
from ingestion import add_documents_to_db
from llm import answer_query_unified
from db import test_connection

# Set page configuration
st.set_page_config(
    page_title="Jurix - Legal Document Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f4e79;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .sub-header {
        color: #2c5aa0;
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'documents_uploaded' not in st.session_state:
        st.session_state.documents_uploaded = 0

def check_database_connection():
    """Check if database connection is working."""
    try:
        test_connection()
        return True
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return False

def document_ingestion_page():
    """Document ingestion functionality."""
    st.markdown('<h2 class="sub-header">📄 Document Ingestion</h2>', unsafe_allow_html=True)
    
    # Create documents directory if it doesn't exist
    documents_dir = Path("documents")
    documents_dir.mkdir(exist_ok=True)
    
    st.info("Upload PDF documents to add them to the knowledge base for querying.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose PDF files",
        type=['pdf'],
        accept_multiple_files=True,
        help="Upload one or more PDF files to ingest into the database"
    )
    
    # Document title input
    if uploaded_files:
        st.subheader("Document Details")
        
        # Process each uploaded file
        for i, uploaded_file in enumerate(uploaded_files):
            with st.expander(f"📁 {uploaded_file.name}", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Title input for each document
                    title = st.text_input(
                        f"Document Title",
                        value=uploaded_file.name.replace('.pdf', ''),
                        key=f"title_{i}",
                        help="Enter a descriptive title for this document"
                    )
                
                with col2:
                    st.write("**File Info:**")
                    st.write(f"Size: {uploaded_file.size / 1024:.1f} KB")
                    st.write(f"Type: {uploaded_file.type}")
                
                # Process button for individual file
                if st.button(f"Process {uploaded_file.name}", key=f"process_{i}"):
                    current_title = st.session_state.get(f"title_{i}", "")
                    if current_title and current_title.strip():
                        with st.spinner(f"Processing {uploaded_file.name}..."):
                            try:
                                # Save uploaded file temporarily
                                temp_path = documents_dir / uploaded_file.name
                                with open(temp_path, "wb") as f:
                                    f.write(uploaded_file.getbuffer())
                                
                                # Process the document
                                add_documents_to_db(uploaded_file.name, current_title.strip())
                                
                                # Clean up temporary file
                                # os.remove(temp_path)
                                
                                st.success(f"✅ {uploaded_file.name} processed successfully!")
                                st.session_state.documents_uploaded += 1
                                
                            except Exception as e:
                                st.error(f"❌ Error processing {uploaded_file.name}: {str(e)}")
                                # Clean up temporary file if it exists
                                if temp_path.exists():
                                    os.remove(temp_path)
                    else:
                        st.warning("Please enter a title for the document.")

def chatbot_page():
    """Chatbot functionality for querying documents - Simple Streamlit chat interface."""
    st.markdown('<h2 class="sub-header">🤖 Legal Assistant Chatbot</h2>', unsafe_allow_html=True)
    
    # Initialize chat messages
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Add debug mode toggle
    st.sidebar.markdown("### 🐛 Debug Mode")
    debug_mode = st.sidebar.checkbox("Enable Debug Logs", value=True, help="Show detailed processing logs")
    
    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Accept user input
    if prompt := st.chat_input("Ask me about your legal documents..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            # Create debug container if debug mode is on
            debug_container = st.expander("🔍 Debug Information", expanded=False) if debug_mode else None
            
            with st.spinner("🤔 Analyzing your question..."):
                try:
                    if debug_mode and debug_container:
                        with debug_container:
                            st.markdown("**Step 1:** Analyzing query and generating search queries...")
                            st.code(f"User Query: {prompt}", language="text")
                    
                    # Call unified query answering
                    response = answer_query_unified(prompt)
                    
                    if debug_mode and debug_container:
                        with debug_container:
                            st.markdown("**Step 2:** ✅ Query analysis complete")
                            st.markdown("**Step 3:** 🔍 Searching across legal_docs and cases...")
                            st.markdown("**Step 4:** 📝 Generating response...")
                            st.success("✅ Response generated successfully!")
                    
                    # Display the response
                    st.markdown(response)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"I apologize, but I encountered an error: {str(e)}. Please make sure you have uploaded some documents and check your database connection."
                    
                    if debug_mode and debug_container:
                        with debug_container:
                            st.error("❌ Error occurred!")
                            st.code(str(e), language="text")
                            import traceback
                            st.code(traceback.format_exc(), language="text")
                    
                    st.markdown(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Clear chat button
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

def main():
    """Main application function."""
    # Initialize session state
    initialize_session_state()
    
    # App header
    st.markdown('<h1 class="main-header">⚖️ Jurix - Legal Document Assistant</h1>', unsafe_allow_html=True)
    st.markdown("**An AI-powered legal document ingestion and query system**")
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1f4e79/ffffff?text=JURIX", width='stretch')
        
        st.markdown("### 🔧 Navigation")
        page = st.radio(
            "Choose functionality:",
            ["📄 Document Ingestion", "🤖 Ask Questions"],
            help="Select between uploading documents or querying them"
        )
        
        st.markdown("---")
        st.markdown("### 📊 Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Documents", st.session_state.documents_uploaded)
        with col2:
            # Count user messages only
            user_messages = len([msg for msg in st.session_state.messages if msg["role"] == "user"])
            st.metric("Questions", user_messages)
        
        st.markdown("---")
        st.markdown("### ⚙️ System Status")
        if st.button("🔄 Check Database Connection"):
            if check_database_connection():
                st.success("✅ Database Connected")
            else:
                st.error("❌ Database Connection Failed")
        
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        **Jurix** helps you:
        - 📄 Upload and process legal documents
        - 🔍 Search through document content
        - 🤖 Get AI-powered answers to legal questions
        - ⚡ Quick and accurate document analysis
        
        **Data Sources:**
        - 📚 Legal Documents (Constitution, IPC, IT Act)
        - ⚖️ Court Case Judgments
        """)
        
        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.markdown("""
        - Ask specific questions for better results
        - Complex queries are automatically analyzed
        - Enable debug mode to see processing details
        """)
    
    # Main content based on selected page
    if page == "📄 Document Ingestion":
        document_ingestion_page()
    else:
        chatbot_page()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; font-size: 0.8rem;'>"
        "Built with Streamlit • Powered by Google Gemini AI • PostgreSQL Vector Database"
        "</div>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
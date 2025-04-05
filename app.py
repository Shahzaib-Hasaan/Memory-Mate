import streamlit as st
import json
import uuid
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from agno.agent import Agent, AgentMemory
from agno.memory.db.sqlite import SqliteMemoryDb
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.models.openai.like import OpenAILike
from agno.memory.classifier import MemoryClassifier
from agno.memory.summarizer import MemorySummarizer
from agno.memory.manager import MemoryManager
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# Create data directory if it doesn't exist
Path("data").mkdir(exist_ok=True)

# Set up database file paths
AGENT_MEMORY_FILE = "data/agent_memory.db"
AGENT_STORAGE_FILE = "data/agent_storage.db"

# Set page configuration
st.set_page_config(
    page_title="MemoryMate",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS with error handling
def load_css():
    try:
        with open("style.css", "r", encoding="utf-8", errors="ignore") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Could not load custom CSS: {str(e)}")
        # Add minimal required styling inline
        st.markdown("""
        <style>
        /* Essential styling */
        .chat-app-container {
            position: relative;
            height: 100vh;
            width: 100%;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .chat-messages-wrapper {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 80px;
            overflow-y: auto;
            padding: 20px;
            z-index: 1;
        }
        .chat-input-fixed {
            position: fixed;
            bottom: 0;
            left: 350px;
            right: 0;
            background: #f9fafb;
            border-top: 1px solid rgba(226, 232, 240, 0.8);
            padding: 15px 30px;
            z-index: 100;
        }
        .memory-item {
            background: rgba(108, 99, 255, 0.1);
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }
        .memory-container {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin: 10px 0;
        }
        .user-header {
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 10px;
        }
        .sidebar-header {
            font-size: 1.1rem;
            font-weight: bold;
            margin: 15px 0 10px 0;
        }
        .memory-header, .summary-header {
            font-size: 1rem;
            font-weight: bold;
            margin: 10px 0;
        }
        .summary-content {
            background: rgba(98, 189, 120, 0.1);
            padding: 10px;
            border-radius: 8px;
            font-size: 0.9rem;
        }
        .no-memories, .no-summary {
            color: #888;
            font-style: italic;
            font-size: 0.9rem;
            margin: 10px 0;
        }
        .loading-indicator {
            display: inline-block;
            animation: blink 1s steps(1) infinite;
        }
        @keyframes blink {
            50% { opacity: 0; }
        }
        .login-container {
            max-width: 500px;
            margin: 100px auto;
            padding: 30px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        .attribution {
            font-size: 0.8rem;
            color: #888;
            text-align: center;
            padding: 10px 0;
            margin-top: 20px;
        }
        .attribution a {
            color: #6c63ff;
            text-decoration: none;
        }
        .attribution a:hover {
            text-decoration: underline;
        }
        </style>
        """, unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = None

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "user_id" not in st.session_state:
    st.session_state.user_id = None
    
if "loading" not in st.session_state:
    st.session_state.loading = False

# Create model for all memory components
try:
    deepseek_model = OpenAILike(
        id=st.secrets["DEEPSEEK_MODEL_ID"],
        base_url=st.secrets["DEEPSEEK_API_ENDPOINT"],
        api_key=st.secrets["DEEPSEEK_API_KEY"]
    )
except Exception as e:
    st.error(f"Error initializing model: {str(e)}")
    st.stop()

# Create custom memory components with our model
memory_classifier = MemoryClassifier(model=deepseek_model)
memory_summarizer = MemorySummarizer(model=deepseek_model)
memory_manager = MemoryManager(model=deepseek_model)

def get_existing_sessions(user_id):
    """Get existing session IDs for the given user"""
    try:
        conn = sqlite3.connect(AGENT_STORAGE_FILE)
        cursor = conn.cursor()
        
        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agent_sessions'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            # Table doesn't exist yet
            conn.close()
            return []
        
        # Table exists, proceed with query
        cursor.execute("SELECT session_id FROM agent_sessions WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        session_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return session_ids
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return []

def initialize_agent(session_id=None):
    """Initialize or reinitialize the agent with an optional session_id"""
    # Make sure we have a user_id
    if not st.session_state.user_id:
        st.session_state.user_id = "default_user"
        
    agent = Agent(
        model=deepseek_model,
        # The memories are personalized for this user
        user_id=st.session_state.user_id,
        # Store the memories and summary in a table: agent_memory
        memory=AgentMemory(
            db=SqliteMemoryDb(
                table_name="agent_memory",
                db_file=AGENT_MEMORY_FILE,
            ),
            # Use our custom memory components
            classifier=memory_classifier,
            summarizer=memory_summarizer,
            manager=memory_manager,
            # Create and store personalized memories for this user
            create_user_memories=True,
            # Update memories for the user after each run
            update_user_memories_after_run=True,
            # Create and store session summaries
            create_session_summary=True,
            # Update session summaries after each run
            update_session_summary_after_run=True,
        ),
        # Store agent sessions in a database
        storage=SqliteAgentStorage(
            table_name="agent_sessions", 
            db_file=AGENT_STORAGE_FILE
        ),
        # Set add_history_to_messages=true to add the previous chat history
        add_history_to_messages=True,
        # Number of historical responses to add to the messages
        num_history_responses=10,
        # The session_id is used to identify the session in the database
        session_id=session_id,
        description="You are a helpful assistant that always responds in a polite, upbeat and positive manner.",
    )
    return agent

def create_or_continue_chat():
    """Create a new chat session if none exists"""
    if st.session_state.agent is None and st.session_state.user_id:
        # Check for existing sessions for this user
        existing_sessions = get_existing_sessions(st.session_state.user_id)
        
        if existing_sessions:
            # Continue with the most recent session
            st.session_state.agent = initialize_agent(session_id=existing_sessions[0])
            st.session_state.session_id = existing_sessions[0]
            
            # Load previous chat messages if they exist
            load_previous_messages(st.session_state.session_id)
        else:
            # Create a new session
            st.session_state.agent = initialize_agent()
            st.session_state.session_id = st.session_state.agent.session_id

def load_previous_messages(session_id):
    """Load previous messages for the current session"""
    try:
        conn = sqlite3.connect(AGENT_STORAGE_FILE)
        cursor = conn.cursor()
        
        # Get the messages from the storage
        cursor.execute("SELECT messages FROM agent_sessions WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            messages_str = result[0]
            try:
                messages = json.loads(messages_str)
                if isinstance(messages, list) and len(messages) > 0:
                    # Only keep the last 10 messages to avoid cluttering the UI
                    messages = messages[-10:]
                    st.session_state.messages = messages
            except json.JSONDecodeError:
                st.warning("Could not load previous messages.")
        
        conn.close()
    except sqlite3.Error as e:
        st.error(f"Database error when loading previous messages: {e}")

def display_memories():
    """Display the agent's memories for the current user"""
    if not st.session_state.agent or not st.session_state.agent.memory.memories:
        return "<div class='no-memories'>No memories created yet</div>"
    
    memories_html = "<div class='memory-container'>"
    
    for memory in st.session_state.agent.memory.memories:
        memories_html += f"<div class='memory-item'>{memory.memory}</div>"
    
    memories_html += "</div>"
    return memories_html

def clear_chat():
    """Clear the current chat session"""
    st.session_state.messages = []
    st.session_state.agent = None
    st.session_state.session_id = None
    create_or_continue_chat()

def handle_user_login():
    """Process user login or registration"""
    if st.session_state.user_id is None:
        with st.container():
            st.markdown("<div class='login-container'>", unsafe_allow_html=True)
            st.markdown("<h3>👋 Welcome to MemoryMate</h3>", unsafe_allow_html=True)
            st.markdown("<p>Enter your username to continue or create a new account.</p>", unsafe_allow_html=True)
            
            # Get or create user profile
            user_id = st.text_input("Username", key="username_input", placeholder="Type your username here...")
            
            login_button = st.button("Sign In", use_container_width=True, type="primary")
            
            if st.session_state.loading:
                st.markdown("<div class='loading-message'>Loading your memories...</div>", unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            if login_button and user_id:
                # Show loading indicator
                st.session_state.loading = True
                st.rerun()
            
            if st.session_state.loading and user_id:
                # Set the user ID
                st.session_state.user_id = user_id
                
                # Clear any existing agent to ensure it uses the new user_id
                st.session_state.agent = None
                st.session_state.session_id = None
                
                # Initialize the agent (will either continue existing session or create new one)
                create_or_continue_chat()
                
                # Reset loading state and refresh
                st.session_state.loading = False
                st.rerun()
            
            # Prevent showing chat until logged in
            return False
    return True

# Load the custom CSS
load_css()

# Handle user login first
user_logged_in = handle_user_login()

# Only show the main app if a user is logged in
if user_logged_in:
    # Initialize agent if not already initialized
    create_or_continue_chat()
    
    # Sidebar with memory display - using Streamlit's actual sidebar
    with st.sidebar:
        # Show current user
        st.markdown(f"<div class='user-header'>👤 <span>{st.session_state.user_id}</span></div>", unsafe_allow_html=True)
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user_id = None
            st.session_state.agent = None
            st.session_state.session_id = None
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("<div class='sidebar-header'>🧠 Memory & Knowledge</div>", unsafe_allow_html=True)
        
        # Button to clear chat
        if st.button("🧹 Clear Chat", use_container_width=True):
            clear_chat()
            st.rerun()
        
        st.divider()
        
        # Display user memories
        st.markdown("<div class='memory-header'>💡 User Memories</div>", unsafe_allow_html=True)
        if st.session_state.agent and st.session_state.agent.memory.memories:
            # Display HTML memory structure
            st.markdown(display_memories(), unsafe_allow_html=True)
        else:
            st.markdown("<div class='no-memories'>No memories created yet</div>", unsafe_allow_html=True)
        
        # Display the summary of the current conversation
        st.divider()
        st.markdown("<div class='summary-header'>📝 Conversation Summary</div>", unsafe_allow_html=True)
        if st.session_state.agent and st.session_state.agent.memory.summary:
            summary = st.session_state.agent.memory.summary
            if summary and hasattr(summary, 'summary') and summary.summary:
                st.markdown(f"<div class='summary-content'>{summary.summary}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='no-summary'>No summary available yet</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='no-summary'>No summary available yet</div>", unsafe_allow_html=True)
            
        # Add attribution at the bottom of the sidebar
        st.divider()
        st.markdown(
            "<div class='attribution'>Developed by "
            "<a href='https://www.linkedin.com/in/shahzaib-ai-developer/' target='_blank'>Shahzaib Hassan</a></div>", 
            unsafe_allow_html=True
        )

    # Main chat interface - full width 
    # Chat container with fixed height and input at bottom
    st.markdown("<div class='chat-app-container'>", unsafe_allow_html=True)
    
    # Message history container (scrollable)
    st.markdown("<div class='chat-messages-wrapper'>", unsafe_allow_html=True)
    
    # Display chat messages
    message_container = st.container()
    with message_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Fixed input container at the bottom
    st.markdown("<div class='chat-input-fixed'>", unsafe_allow_html=True)
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message in chat message container
        with st.chat_message("user"):
            st.write(prompt)
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            # Generate response
            full_response = ""
            for chunk in st.session_state.agent.run(prompt, stream=True):
                if hasattr(chunk, 'content') and chunk.content:
                    full_response += chunk.content
                    message_placeholder.markdown(full_response + "<span class='loading-indicator'>▌</span>", unsafe_allow_html=True)
            message_placeholder.markdown(full_response)
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        # Force-refresh the memory and summary displays
        st.rerun()
    
    # JavaScript for auto-scrolling to bottom when new messages arrive
    st.markdown("""
    <script>
        const messageContainer = document.querySelector('[data-testid="stChatMessageContainer"]');
        if (messageContainer) {
            messageContainer.scrollTop = messageContainer.scrollHeight;
            const observer = new MutationObserver(() => {
                messageContainer.scrollTop = messageContainer.scrollHeight;
            });
            observer.observe(messageContainer, { childList: true, subtree: true });
        }
    </script>
    """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

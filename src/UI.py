import streamlit as st
import time
import os
import sys
from datetime import datetime
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

# Add the current directory to Python path to import the agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Initialize the agent (import after path setup)
try:
    from ageent import agent, mcp_client
    AGENT_AVAILABLE = True
except ImportError as e:
    st.error(f"Failed to import agent: {e}")
    AGENT_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="SmolAgent AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern UI Design
st.markdown("""
<style>
    /* Import modern fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono&display=swap');
    
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Global styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Full height layout */
    .main .block-container {
        padding: 0;
        max-width: 100%;
        height: 100vh;
    }
    
    .stApp {
        background: #0e1117;
    }
    
    /* Header */
    .app-header {
        background: linear-gradient(90deg, #1e3a8a 0%, #3730a3 100%);
        padding: 0.75rem 2rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 999;
        backdrop-filter: blur(10px);
        height: 60px;
    }
    
    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 1400px;
        margin: 0 auto;
        height: 100%;
    }
    
    .app-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: white;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .status-badge {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(255,255,255,0.1);
        padding: 0.4rem 0.8rem;
        border-radius: 100px;
        backdrop-filter: blur(10px);
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #10b981;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
    }
    
    .status-text {
        color: white;
        font-size: 0.875rem;
        font-weight: 500;
    }
    
    /* Main chat container */
    .chat-wrapper {
        background: #0e1117;
    }
    
    /* Chat area */
    .chat-area {
        flex: 1;
        display: flex;
        flex-direction: column;
        background: #0e1117;
        position: relative;
        padding-top: 70px; /* Add space for header */
    }
    
    /* Messages container */
    .messages-container {
        flex: 1;
        overflow-y: auto;
        padding: 0.5rem 2rem 0.5rem 2rem;
        scroll-behavior: smooth;
    }
    
    .messages-container::-webkit-scrollbar {
        width: 6px;
    }
    
    .messages-container::-webkit-scrollbar-track {
        background: rgba(255,255,255,0.05);
    }
    
    .messages-container::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.1);
        border-radius: 3px;
    }
    
    /* Message styles */
    .message {
        display: flex;
        margin-bottom: 1.5rem;
        animation: fadeIn 0.3s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .message-user {
        justify-content: flex-end;
    }
    
    .message-assistant {
        justify-content: flex-start;
    }
    
    .message-content {
        max-width: 70%;
        position: relative;
    }
    
    .message-bubble {
        padding: 1rem 1.25rem;
        border-radius: 1rem;
        font-size: 0.95rem;
        line-height: 1.6;
        word-wrap: break-word;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    .message-user .message-bubble {
        background: linear-gradient(135deg, #3730a3 0%, #4c1d95 100%);
        color: white;
        border-bottom-right-radius: 0.25rem;
    }
    
    .message-assistant .message-bubble {
        background: #1e293b;
        color: #e2e8f0;
        border: 1px solid #334155;
        border-bottom-left-radius: 0.25rem;
    }
    
    .message-time {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 0.5rem;
        padding: 0 0.25rem;
    }
    
    .message-user .message-time {
        text-align: right;
    }
    
    /* Input area */
    .input-area {
        background: #1e293b;
        border-top: 1px solid #334155;
        padding: 1rem 2rem;
        backdrop-filter: blur(10px);
    }
    
    .input-container {
        max-width: 1000px;
        margin: 0 auto;
        display: flex;
        gap: 1rem;
        align-items: flex-end;
    }
    
    .input-wrapper {
        flex: 1;
        position: relative;
    }
    
    .stTextInput > div > div > input {
        background: #0f172a;
        border: 2px solid #334155;
        color: #e2e8f0;
        padding: 0.875rem 1.25rem;
        border-radius: 12px;
        font-size: 1rem;
        transition: all 0.2s ease;
        width: 100%;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3730a3;
        box-shadow: 0 0 0 3px rgba(55, 48, 163, 0.1);
        outline: none;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #64748b;
    }
    
    /* Send button */
    .send-btn-wrapper .stButton > button {
        background: linear-gradient(135deg, #3730a3 0%, #4c1d95 100%);
        color: white;
        border: none;
        padding: 0.875rem 2rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.2s ease;
        box-shadow: 0 4px 6px rgba(55, 48, 163, 0.2);
        height: 100%;
    }
    
    .send-btn-wrapper .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 12px rgba(55, 48, 163, 0.3);
    }
    
    /* Transcript panel */
    .transcript-panel {
        background: #1e293b;
        border-left: 1px solid #334155;
        width: 400px;
        padding: 1.5rem;
        overflow-y: auto;
        transition: all 0.3s ease;
    }
    
    .transcript-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid #334155;
    }
    
    .transcript-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #e2e8f0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .transcript-content {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        font-size: 0.875rem;
        line-height: 1.6;
        color: #cbd5e1;
        max-height: calc(100vh - 250px);
        overflow-y: auto;
    }
    
    /* Example queries */
    .examples-section {
        background: #1e293b;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border: 1px solid #334155;
    }
    
    .examples-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: #94a3b8;
        margin-bottom: 1rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .example-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
    }
    
    .example-chip {
        background: #0f172a;
        border: 1px solid #334155;
        color: #e2e8f0;
        padding: 0.625rem 1.25rem;
        border-radius: 100px;
        font-size: 0.875rem;
        cursor: pointer;
        transition: all 0.2s ease;
        white-space: nowrap;
    }
    
    .example-chip:hover {
        background: #334155;
        border-color: #475569;
        transform: translateY(-1px);
    }
    
    /* Welcome message */
    .welcome-message {
        text-align: center;
        padding: 1rem 2rem 0.5rem 2rem;
        color: #64748b;
    }
    
    .welcome-title {
        font-size: 2rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 0.5rem;
    }
    
    .welcome-subtitle {
        font-size: 1.1rem;
        margin-bottom: 1rem;
        color: #94a3b8;
    }
    
    /* Action buttons */
    .action-buttons {
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        display: flex;
        gap: 0.75rem;
        z-index: 100;
    }
    
    .action-btn {
        background: #1e293b;
        border: 1px solid #334155;
        color: #e2e8f0;
        padding: 0.625rem 1.25rem;
        border-radius: 8px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .action-btn:hover {
        background: #334155;
        transform: translateY(-1px);
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .transcript-panel {
            display: none;
        }
        
        .message-content {
            max-width: 85%;
        }
        
        .app-header {
            padding: 0.5rem 1rem;
            height: 50px;
        }
        
        .app-title {
            font-size: 1.2rem;
        }
        
        .chat-wrapper {
            height: calc(100vh - 50px);
            margin-top: 50px;
        }
        
        .messages-container {
            padding: 1rem;
        }
        
        .input-area {
            padding: 1rem;
        }
        
        .action-buttons {
            bottom: 1rem;
            right: 1rem;
        }
        
        .welcome-message {
            padding: 1.5rem;
        }
        
        .welcome-title {
            font-size: 1.5rem;
        }
    }
    
    /* Loading animation */
    .typing-indicator {
        display: flex;
        gap: 4px;
        padding: 1rem;
    }
    
    .typing-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #64748b;
        animation: typing 1.4s infinite;
    }
    
    .typing-dot:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .typing-dot:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes typing {
        0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
        30% { opacity: 1; transform: scale(1); }
    }
    
    /* Code blocks */
    .code-block {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 1rem;
        margin: 0.5rem 0;
        overflow-x: auto;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.875rem;
        color: #e2e8f0;
    }
    
    /* Success/Error messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 8px;
        border: none;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        font-size: 0.875rem;
    }
    
    .stSuccess {
        background: rgba(16, 185, 129, 0.1);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'current_transcript' not in st.session_state:
    st.session_state.current_transcript = ""
if 'current_video_url' not in st.session_state:
    st.session_state.current_video_url = ""

def format_response(response: str) -> str:
    """Format the agent response with proper styling"""
    # Code blocks
    response = re.sub(r'```(\w+)?\n(.*?)```', r'<div class="code-block">\2</div>', response, flags=re.DOTALL)
    
    # Headers
    response = re.sub(r'^# (.*)', r'<h2 style="color: #e2e8f0; margin: 1.5rem 0 0.75rem 0; font-size: 1.5rem;">\1</h2>', response, flags=re.MULTILINE)
    response = re.sub(r'^## (.*)', r'<h3 style="color: #e2e8f0; margin: 1.25rem 0 0.5rem 0; font-size: 1.25rem;">\1</h3>', response, flags=re.MULTILINE)
    response = re.sub(r'^### (.*)', r'<h4 style="color: #e2e8f0; margin: 1rem 0 0.5rem 0; font-size: 1.1rem;">\1</h4>', response, flags=re.MULTILINE)
    
    # Lists
    response = re.sub(r'^- (.*)', r'<li style="margin-bottom: 0.5rem; color: #cbd5e1;">\1</li>', response, flags=re.MULTILINE)
    response = re.sub(r'(<li.*?</li>)', r'<ul style="margin: 0.5rem 0; padding-left: 1.5rem;">\1</ul>', response)
    
    # Bold and italic
    response = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color: #f1f5f9;">\1</strong>', response)
    response = re.sub(r'\*(.*?)\*', r'<em>\1</em>', response)
    
    return response

def extract_transcript_from_response(response: str) -> str:
    """Extract transcript from agent response"""
    patterns = [
        r'Transcript for YouTube Video:.*?\n\n(.*?)(?=\n\n|$)',
        r'Full Transcript \(Single Paragraph\):\n(.*?)(?=\n\n|$)',
        r'transcript:\s*(.*?)(?=\n\n|$)',
        r'Video ID:.*?Word Count:.*?\n\n(.*?)(?=\n\n|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            transcript = match.group(1).strip()
            if len(transcript) > 100:
                return transcript
    return ""

def get_agent_status():
    """Get current agent and MCP status"""
    if not AGENT_AVAILABLE:
        return "error", "Agent offline"
    
    if mcp_client:
        try:
            tools = mcp_client.get_tools()
            return "success", f"{len(tools)} tools ready"
        except:
            return "warning", "Limited tools"
    return "warning", "Basic mode"

# Header
status_type, status_text = get_agent_status()
status_color = "#10b981" if status_type == "success" else "#f59e0b" if status_type == "warning" else "#ef4444"

st.markdown(f"""
<div class="app-header">
    <div class="header-content">
        <div class="app-title">
            <span style="font-size: 1.75rem;">🤖</span>
            SmolAgent AI
        </div>
        <div class="status-badge">
            <div class="status-dot" style="background: {status_color};"></div>
            <span class="status-text">{status_text}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main chat wrapper
st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

# Chat area
st.markdown('<div class="chat-area">', unsafe_allow_html=True)

# Messages container
st.markdown('<div class="messages-container">', unsafe_allow_html=True)

if not st.session_state.messages:
    # Welcome message
    st.markdown("""
    <div class="welcome-message">
        <div class="welcome-title">👋 Welcome to SmolAgent AI</div>
        <div class="welcome-subtitle">Your intelligent assistant for databases, YouTube analysis, and web research</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Example queries
    st.markdown("""
    <div class="examples-section">
        <div class="examples-title">Try these examples</div>
        <div class="example-chips">
            <div class="example-chip" onclick="document.querySelector('input').value='Show me all tables in the database'; document.querySelector('input').dispatchEvent(new Event('input', {bubbles: true}));">
                📊 Show database tables
            </div>
            <div class="example-chip" onclick="document.querySelector('input').value='Analyze this YouTube video: https://www.youtube.com/watch?v=dQw4w9WgXcQ'; document.querySelector('input').dispatchEvent(new Event('input', {bubbles: true}));">
                🎥 Analyze YouTube video
            </div>
            <div class="example-chip" onclick="document.querySelector('input').value='Visit and summarize https://example.com'; document.querySelector('input').dispatchEvent(new Event('input', {bubbles: true}));">
                🌐 Summarize webpage
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Display messages
    for i, message in enumerate(st.session_state.messages):
        timestamp = datetime.now().strftime("%I:%M %p")
        
        if message["role"] == "user":
            st.markdown(f"""
            <div class="message message-user">
                <div class="message-content">
                    <div class="message-bubble">
                        {message["content"]}
                    </div>
                    <div class="message-time">{timestamp}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            formatted_content = format_response(message["content"])
            st.markdown(f"""
            <div class="message message-assistant">
                <div class="message-content">
                    <div class="message-bubble">
                        {formatted_content}
                    </div>
                    <div class="message-time">{timestamp}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close messages-container

# Input area
st.markdown('<div class="input-area">', unsafe_allow_html=True)
st.markdown('<div class="input-container">', unsafe_allow_html=True)

# Check for example query
default_query = ""
if hasattr(st.session_state, 'example_query'):
    default_query = st.session_state.example_query
    delattr(st.session_state, 'example_query')

# Input form
with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([6, 1])
    
    with col1:
        st.markdown('<div class="input-wrapper">', unsafe_allow_html=True)
        user_input = st.text_input(
            "Message",
            value=default_query,
            placeholder="Ask me anything...",
            label_visibility="collapsed",
            key="user_input"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="send-btn-wrapper">', unsafe_allow_html=True)
        submit_button = st.form_submit_button("Send", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div></div>', unsafe_allow_html=True)  # Close input-container and input-area

st.markdown('</div>', unsafe_allow_html=True)  # Close chat-area

# Transcript panel (only show if there's content)
if st.session_state.current_transcript and len(st.session_state.current_transcript.strip()) > 0:
    st.markdown(f"""
    <div class="transcript-panel">
        <div class="transcript-header">
            <div class="transcript-title">
                📝 Video Transcript
            </div>
        </div>
        <div class="transcript-content">
            {st.session_state.current_transcript}
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # Close chat-wrapper

# Process user input
if submit_button and user_input and AGENT_AVAILABLE:
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.spinner(""):
        # Show typing indicator
        st.markdown("""
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
        """, unsafe_allow_html=True)
        
        start_time = time.time()
        
        try:
            response = agent.run(user_input)
            response_time = time.time() - start_time
            
            # Extract transcript if YouTube video
            if "youtube.com" in user_input.lower() or "youtu.be" in user_input.lower():
                transcript = extract_transcript_from_response(str(response))
                if transcript:
                    st.session_state.current_transcript = transcript
                    url_match = re.search(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', user_input)
                    if url_match:
                        st.session_state.current_video_url = url_match.group(0)
            
            st.session_state.messages.append({"role": "assistant", "content": str(response)})
            st.success(f"✅ Response in {response_time:.1f}s")
            
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"I encountered an error: {str(e)}"})
            st.error(f"❌ Error: {str(e)}")
    
    st.rerun()

elif submit_button and user_input and not AGENT_AVAILABLE:
    st.error("❌ Agent is not available. Please check the configuration.")

# Action buttons
st.markdown("""
<div class="action-buttons">
    <button class="action-btn" onclick="if(confirm('Clear all messages?')) { window.location.href = '?clear=true'; }">
        🗑️ Clear
    </button>
</div>
""", unsafe_allow_html=True)

# Handle clear action
if st.query_params.get("clear") == "true":
    st.session_state.messages = []
    st.session_state.current_transcript = ""
    st.session_state.current_video_url = ""
    st.query_params.clear()
    st.rerun()
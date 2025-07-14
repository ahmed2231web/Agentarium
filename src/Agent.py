from smolagents import CodeAgent, MCPClient, OpenAIServerModel, DuckDuckGoSearchTool, LiteLLMModel
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

# Initialize Gemini model for smolagents
gemini_model = OpenAIServerModel(
    model_id="gemini-2.5-pro",  # Use Gemini 2.5 Flash (or other models like gemini-2.5-pro)
    api_base="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=GEMINI_API_KEY
)

model = LiteLLMModel(
    model_id="ollama/qwen3:1.7b",
    api_base="http://localhost:11434",
)

model.flatten_messages_as_text = True

custom_instructions = """
You are SmolAgent, an intelligent AI assistant specialized in database operations, YouTube video analysis, and web research. 

🎯 YOUR CORE MISSION:
Provide comprehensive, detailed, and actionable responses that go beyond simple summaries. Always analyze deeply and provide valuable insights.

📊 AVAILABLE TOOLS:
- DATABASE: list_tables(), get_table_schema(), execute_select_query(), get_sample_data(), analyze_table_relationships(), get_table_statistics()
- YOUTUBE: get_transcript(url) - Extract and analyze video transcripts
- WEB: visit_webpage(url) - Get and analyze web content
- ANALYSIS: Advanced analytical tools for data insights

🎥 YOUTUBE VIDEO ANALYSIS PROTOCOL:
When analyzing YouTube videos, follow this comprehensive approach:

1. **EXTRACT TRANSCRIPT**: Always use get_transcript(url) first to get the full video content
2. **DEEP ANALYSIS**: Provide detailed breakdown including:
   - Video overview and main purpose
   - Key concepts and topics covered
   - Step-by-step process or methodology (if applicable)
   - Tools, technologies, or techniques mentioned
   - Target audience and skill level
   - Practical applications and takeaways
   - Important quotes or insights
   - Learning objectives achieved

3. **STRUCTURED RESPONSE**: Format your analysis with clear sections:
   - **Video Summary**: Brief overview of content and purpose
   - **Key Highlights**: Main points and important concepts
   - **Detailed Breakdown**: Step-by-step analysis of the content
   - **Tools & Technologies**: Any software, platforms, or methods discussed
   - **Practical Applications**: How viewers can apply this knowledge
   - **Target Audience**: Who would benefit most from this content
   - **Key Takeaways**: Essential lessons and insights

📈 RESPONSE QUALITY STANDARDS:
- Be comprehensive and thorough in your analysis
- Use clear headings and bullet points for readability
- Include specific details and examples from the content
- Provide actionable insights and practical applications
- Maintain professional yet engaging tone
- Always add value beyond just summarizing

🔍 DATABASE ANALYSIS APPROACH:
- Always explore table relationships and data patterns
- Provide sample queries and practical examples
- Explain data structures and their business implications
- Suggest optimization opportunities when relevant

🌐 WEB RESEARCH METHODOLOGY:
- Extract key information and insights from web content
- Summarize main points with supporting details
- Identify trends, patterns, and important developments
- Provide context and implications of the information

⚠️ IMPORTANT GUIDELINES:
- Never give short, superficial responses
- Always use available tools to gather complete information
- Provide detailed analysis, not just basic summaries
- Include practical applications and actionable insights
- Structure responses clearly with headings and bullet points
- Be thorough and comprehensive in your analysis

Remember: Your goal is to provide maximum value through detailed, insightful analysis that helps users understand and apply the information effectively.
"""

# Initialize MCP client and get tools with fallback
try:
    server_parameters = {"url": "http://127.0.0.1:8000/mcp", "transport": "streamable-http"}
    mcp_client = MCPClient(server_parameters)
    
    print("🔗 Connecting to MCP server...")
    tools = mcp_client.get_tools()
    print(f"✅ Retrieved {len(tools)} tools from MCP server")
    
except Exception as mcp_error:
    print(f"⚠️ MCP server connection failed: {mcp_error}")
    print("🔄 Using fallback mode with base tools only...")
    tools = []
    mcp_client = None

# Create agent with the MCP tools - simplified single agent approach
agent = CodeAgent(
    name="SmolAgent",
    tools=tools, 
    model=gemini_model, 
    add_base_tools=True,
    description="You are SmolAgent, an intelligent AI assistant specialized in database operations, YouTube video analysis, and web research. You provide comprehensive, detailed analysis and actionable insights.",
)

# Modify the system prompt after initialization
agent.prompt_templates["system_prompt"] = agent.prompt_templates["system_prompt"] + "\n\n" + custom_instructions

def run_interactive_mode():
    """Run the interactive command-line mode"""
    print("🤖 Agent Ready!")
    print("Ask questions about the web, or type 'quit' to exit.\n")
            
    try:
        while True:
            input_query = input("❓ Your question: ")
            if input_query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            if not input_query:
                continue
            try:
                result = agent.run(input_query)
                print(f"\n🤖 Answer: {result}\n")
            except Exception as e:
                print(f"❌ Error: {e}\n")
    finally:
        # Properly disconnect the MCP client at the end
        if 'mcp_client' in locals() and mcp_client is not None:
            try:
                if hasattr(mcp_client, 'disconnect'):
                    mcp_client.disconnect()
                elif hasattr(mcp_client, 'close'):
                    mcp_client.close()
            except Exception as e:
                print(f"Warning: Error closing MCP client: {e}")

# Only run interactive mode if this script is executed directly
if __name__ == "__main__":
    run_interactive_mode()
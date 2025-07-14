
"""
Enhanced MCP Server for Database Operations, YouTube Transcripts, and Web Content with Pydantic Models

Uses FastMCP to create database tools for SmolAgents with structured responses.
"""

from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator
from postgres_db import PostgreSQLManager, TableSchema, DatabaseSchema, QueryResult, SampleData
from enum import Enum
from youtube_transcript_api import YouTubeTranscriptApi
import re
import requests
from requests.exceptions import RequestException
from markdownify import markdownify

# Create MCP server
mcp = FastMCP("DatabaseMCP")

# Initialize database manager
db_manager = PostgreSQLManager()

class QueryType(str, Enum):
    """Supported query types"""
    SELECT = "SELECT"

class TableListResponse(BaseModel):
    """Response model for listing tables"""
    success: bool = Field(..., description="Whether the operation was successful")
    tables: List[str] = Field(default_factory=list, description="List of table names")
    total_count: int = Field(default=0, description="Total number of tables")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    def get_formatted_response(self) -> str:
        """Get formatted string response"""
        if not self.success:
            return f"Error: {self.error}"
        
        if not self.tables:
            return "No tables found in the database"
        
        response = f"Found {self.total_count} tables in the database:\n"
        for i, table in enumerate(self.tables, 1):
            response += f"{i}. {table}\n"
        
        return response.strip()

class TableSchemaResponse(BaseModel):
    """Response model for table schema information"""
    success: bool = Field(..., description="Whether the operation was successful")
    table_name: str = Field(..., description="Name of the table")
    table_schema: Optional[TableSchema] = Field(None, description="Table schema information")  # Changed from 'schema' to 'table_schema'
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    def get_formatted_response(self) -> str:
        """Get formatted string response"""
        if not self.success:
            return f"Error getting schema for table '{self.table_name}': {self.error}"
        
        if not self.table_schema or not self.table_schema.columns:  # Updated reference
            return f"No schema information found for table '{self.table_name}'"
        
        response = f"Schema for table '{self.table_name}':\n\n"
        response += f"Columns ({len(self.table_schema.columns)}):\n"  # Updated reference
        
        for col in self.table_schema.columns:  # Updated reference
            nullable = "NULL" if col.nullable else "NOT NULL"
            pk_indicator = " 🔑" if col.primary_key else ""
            fk_indicator = " 🔗" if col.foreign_key else ""
            
            response += f"  • {col.name}: {col.type} ({nullable}){pk_indicator}{fk_indicator}\n"
            
            if col.default:
                response += f"    DEFAULT: {col.default}\n"
        
        if self.table_schema.foreign_keys:  # Updated reference
            response += f"\nForeign Keys ({len(self.table_schema.foreign_keys)}):\n"
            for fk in self.table_schema.foreign_keys:
                response += f"  • {', '.join(fk.constrained_columns)} → {fk.referred_table}.{', '.join(fk.referred_columns)}\n"
        
        if self.table_schema.indexes:  # Updated reference
            response += f"\nIndexes ({len(self.table_schema.indexes)}):\n"
            for idx in self.table_schema.indexes:
                unique_indicator = " (UNIQUE)" if idx.unique else ""
                response += f"  • {idx.name}: {', '.join(idx.columns)}{unique_indicator}\n"
        
        return response

class QueryExecutionResponse(BaseModel):
    """Response model for query execution"""
    success: bool = Field(..., description="Whether the query was successful")
    query: str = Field(..., description="The executed query")
    result: Optional[QueryResult] = Field(None, description="Query execution result")
    error: Optional[str] = Field(None, description="Error message if query failed")
    
    def get_formatted_response(self) -> str:
        """Get formatted string response"""
        if not self.success:
            return f"Query failed: {self.error}\nQuery: {self.query}"
        
        if not self.result:
            return f"Query executed but no result returned\nQuery: {self.query}"
        
        if not self.result.success:
            return f"Query execution failed: {self.result.error}\nQuery: {self.query}"
        
        response = f"Query executed successfully"
        if self.result.execution_time:
            response += f" (took {self.result.execution_time:.3f}s)"
        response += f"\nQuery: {self.query}\n\n"
        
        if self.result.data:
            response += f"Results ({len(self.result.data)} rows):\n"
            
            # Show column headers
            if self.result.columns:
                headers = " | ".join(self.result.columns)
                response += f"  {headers}\n"
                response += f"  {'-' * len(headers)}\n"
            
            # Show data rows (limit to first 10)
            for i, row in enumerate(self.result.data[:10]):
                if isinstance(row, dict):
                    values = " | ".join([str(row.get(col, 'NULL')) for col in (self.result.columns or row.keys())])
                    response += f"  {values}\n"
                else:
                    response += f"  {row}\n"
            
            if len(self.result.data) > 10:
                response += f"  ... and {len(self.result.data) - 10} more rows\n"
        
        elif self.result.rows_affected is not None:
            response += f"Rows affected: {self.result.rows_affected}\n"
        
        return response

class SampleDataResponse(BaseModel):
    """Response model for sample data"""
    success: bool = Field(..., description="Whether the operation was successful")
    table_name: str = Field(..., description="Name of the table")
    sample_data: Optional[SampleData] = Field(None, description="Sample data from the table")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    def get_formatted_response(self) -> str:
        """Get formatted string response"""
        if not self.success:
            return f"Error getting sample data from table '{self.table_name}': {self.error}"
        
        if not self.sample_data or not self.sample_data.rows:
            return f"No sample data found in table '{self.table_name}'"
        
        response = f"Sample data from '{self.table_name}' ({self.sample_data.total_rows_sampled} rows):\n\n"
        
        # Show column headers
        if self.sample_data.columns:
            headers = " | ".join(self.sample_data.columns)
            response += f"  {headers}\n"
            response += f"  {'-' * len(headers)}\n"
        
        # Show sample rows
        for i, row in enumerate(self.sample_data.rows):
            if isinstance(row, dict):
                values = " | ".join([str(row.get(col, 'NULL')) for col in (self.sample_data.columns or row.keys())])
                response += f"  {values}\n"
            else:
                response += f"  {row}\n"
        
        return response

class DatabaseOverviewResponse(BaseModel):
    """Response model for database overview"""
    success: bool = Field(..., description="Whether the operation was successful")
    database_name: str = Field(..., description="Name of the database")
    db_schema: Optional[DatabaseSchema] = Field(None, description="Complete database schema")  # Changed from 'schema' to 'db_schema'
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    def get_formatted_response(self) -> str:
        """Get formatted string response"""
        if not self.success:
            return f"Error getting database overview: {self.error}"
        
        if not self.db_schema:  # Updated reference
            return f"No schema information found for database '{self.database_name}'"
        
        response = f"Database Overview: '{self.database_name}'\n"
        response += f"{'-' * (len(self.database_name) + 20)}\n\n"
        response += f"Total Tables: {self.db_schema.total_tables}\n\n"  # Updated reference
        
        if self.db_schema.tables:  # Updated reference
            response += "Tables Summary:\n"
            for table_name in self.db_schema.get_table_names():  # Updated reference
                table = self.db_schema.get_table_by_name(table_name)  # Updated reference
                if table:
                    response += f"  • {table_name}: {len(table.columns)} columns"
                    if table.primary_keys:
                        response += f", PK: {', '.join(table.primary_keys)}"
                    if table.foreign_keys:
                        response += f", {len(table.foreign_keys)} FK(s)"
                    response += "\n"
        
        return response

class YouTubeVideo(BaseModel):
    """Model for YouTube video information"""
    video_id: str = Field(..., description="The YouTube video ID")
    url: str = Field(..., description="The full YouTube video URL")
    
    @field_validator('video_id')
    @classmethod
    def validate_video_id(cls, v):
        if not v or not re.match(r'^[A-Za-z0-9_-]{11}$', v):
            raise ValueError("Invalid YouTube video ID format")
        return v

class VideoIdResponse(BaseModel):
    """Response model for video ID extraction"""
    success: bool = Field(..., description="Whether the operation was successful")
    video_id: Optional[str] = Field(None, description="The extracted YouTube video ID")
    url: str = Field(..., description="The input YouTube video URL")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    def get_formatted_response(self) -> str:
        """Get formatted string response"""
        if not self.success:
            return f"Error extracting video ID: {self.error}\nURL: {self.url}"
        
        return f"Video ID extracted successfully\nURL: {self.url}\nVideo ID: {self.video_id}"

class TranscriptResponse(BaseModel):
    """Response model for video transcript"""
    success: bool = Field(..., description="Whether the operation was successful")
    video_id: str = Field(..., description="The YouTube video ID")
    url: str = Field(..., description="The YouTube video URL")
    transcript: Optional[str] = Field(None, description="The full video transcript text as a single paragraph")
    word_count: Optional[int] = Field(None, description="Number of words in the transcript")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    def get_formatted_response(self) -> str:
        """Get formatted string response"""
        if not self.success:
            return f"Error fetching transcript: {self.error}\nURL: {self.url}"
        
        if not self.transcript:
            return f"No transcript found for video: {self.url}"
        
        response = f"Transcript for YouTube Video: {self.url}\n"
        response += f"{'-' * (len(self.url) + 20)}\n\n"
        response += f"Video ID: {self.video_id}\n"
        response += f"Word Count: {self.word_count:,}\n\n"
        response += "Full Transcript (Single Paragraph):\n"
        response += f"{self.transcript}\n"
        
        return response.strip()

class WebpageResponse(BaseModel):
    """Response model for webpage content retrieval"""
    success: bool = Field(..., description="Whether the operation was successful")
    url: str = Field(..., description="The input webpage URL")
    content: Optional[str] = Field(None, description="The webpage content converted to Markdown")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    
    def get_formatted_response(self) -> str:
        """Get formatted string response"""
        if not self.success:
            return f"Error fetching webpage content: {self.error}\nURL: {self.url}"
        
        if not self.content:
            return f"No content retrieved for webpage: {self.url}"
        
        response = f"Webpage Content for: {self.url}\n"
        response += f"{'-' * (len(self.url) + 20)}\n\n"
        response += "Content (Markdown):\n"
        response += f"{self.content}\n"
        
        return response.strip()

# Enhanced MCP Tools with Pydantic responses

@mcp.tool()
def list_tables() -> str:
    """
    Retrieves a list of all tables in the connected database.

    This tool connects to the database, fetches the names of all tables,
    and returns them in a structured and formatted response. It also
    includes the total count of tables found.

    Returns:
        A formatted string containing the list of table names, or an
        error message if the operation fails.
    """
    try:
        tables = db_manager.list_tables()
        
        response = TableListResponse(
            success=True,
            tables=tables,
            total_count=len(tables)
        )
        
        print(f"DEBUG: Found {len(tables)} tables")
        return response.get_formatted_response()
        
    except Exception as e:
        print(f"ERROR in list_tables: {e}")
        response = TableListResponse(
            success=False,
            error=str(e)
        )
        return response.get_formatted_response()


@mcp.tool()
def get_table_schema(table_name: str) -> str:
    """
    Get comprehensive schema information for a specific table.

    This tool retrieves the detailed schema for a given table, including
    column names, data types, nullability, primary and foreign keys,
    and indexes. The information is returned in a structured and
    human-readable format.

    Args:
        table_name: The name of the table to retrieve the schema for.

    Returns:
        A formatted string containing the detailed table schema, or an
        error message if the table is not found or the operation fails.
    """
    try:
        schema = db_manager.get_table_schema(table_name)
        
        response = TableSchemaResponse(
            success=True,
            table_name=table_name,
            table_schema=schema
        )
        
        return response.get_formatted_response()
        
    except Exception as e:
        print(f"ERROR in get_table_schema: {e}")
        response = TableSchemaResponse(
            success=False,
            table_name=table_name,
            error=str(e)
        )
        return response.get_formatted_response()


@mcp.tool()
def execute_select_query(sql_query: str) -> str:
    """
    Execute a SELECT query with comprehensive result formatting and helpful error messages.

    This tool executes a SQL SELECT query against the database. It includes a
    security check to ensure that only SELECT statements are executed. The
    results are formatted in a clear, readable table, and it provides
    helpful suggestions for common errors, such as incorrect column names.

    Args:
        sql_query: The SELECT query to execute.

    Returns:
        A formatted string containing the query results or a detailed
        error message with suggestions if the query fails.
    """
    try:
        print(f"DEBUG: Executing query: {sql_query}")
        
        # Safety check: only allow SELECT queries
        if not sql_query.strip().upper().startswith('SELECT'):
            response = QueryExecutionResponse(
                success=False,
                query=sql_query,
                error="Only SELECT queries are allowed for security reasons"
            )
            return response.get_formatted_response()
        
        result = db_manager.execute_query(sql_query)
        
        if not result.success:
            # Enhanced error handling with suggestions
            error_msg = result.error
            suggestions = ""
            
            # Check for common column name errors
            if "column" in error_msg.lower() and "does not exist" in error_msg.lower():
                # Extract table name from query
                import re
                table_match = re.search(r'FROM\s+(\w+)', sql_query, re.IGNORECASE)
                if table_match:
                    table_name = table_match.group(1)
                    suggestions = f"\n\nSUGGESTION: The column name might be incorrect. Please use get_table_schema(table_name='{table_name}') to check the exact column names available in the table."
            
            enhanced_error = f"{error_msg}{suggestions}"
            
            response = QueryExecutionResponse(
                success=False,
                query=sql_query,
                error=enhanced_error
            )
            return response.get_formatted_response()
        
        response = QueryExecutionResponse(
            success=True,
            query=sql_query,
            result=result
        )
        
        return response.get_formatted_response()
        
    except Exception as e:
        print(f"ERROR in execute_select_query: {e}")
        response = QueryExecutionResponse(
            success=False,
            query=sql_query,
            error=f"Unexpected error: {str(e)}. Please check your SQL syntax and table/column names."
        )
        return response.get_formatted_response()


@mcp.tool()
def get_sample_data(table_name: str, limit: int = 5) -> str:
    """
    Get sample data from a table with structured formatting.

    This tool retrieves a specified number of sample rows from a given
    table. It helps in quickly inspecting the data within a table without
    querying the entire dataset. The number of rows is limited to 20
    to prevent excessive output.

    Args:
        table_name: The name of the table to fetch sample data from.
        limit: The maximum number of rows to return (default is 5).

    Returns:
        A formatted string containing the sample data, or an error
        message if the operation fails.
    """
    try:
        # Limit the maximum number of rows to prevent overwhelming responses
        safe_limit = min(limit, 20)
        
        sample_data = db_manager.get_sample_data(table_name, safe_limit)
        
        response = SampleDataResponse(
            success=True,
            table_name=table_name,
            sample_data=sample_data
        )
        
        return response.get_formatted_response()
        
    except Exception as e:
        print(f"ERROR in get_sample_data: {e}")
        response = SampleDataResponse(
            success=False,
            table_name=table_name,
            error=str(e)
        )
        return response.get_formatted_response()


@mcp.tool()
def get_database_overview() -> str:
    """
    Get a comprehensive overview of the entire database.

    This tool provides a high-level summary of the database, including
    the total number of tables and a summary of each table's columns,
    primary keys, and foreign keys. It is useful for understanding the
    overall structure of the database at a glance.

    Returns:
        A formatted string with the database overview, or an error
        message if the operation fails.
    """
    try:
        schema = db_manager.get_database_schema()
        
        response = DatabaseOverviewResponse(
            success=True,
            database_name=schema.database_name,
            db_schema=schema
        )
        
        return response.get_formatted_response()
        
    except Exception as e:
        print(f"ERROR in get_database_overview: {e}")
        response = DatabaseOverviewResponse(
            success=False,
            database_name="unknown",
            error=str(e)
        )
        return response.get_formatted_response()


@mcp.tool()
def analyze_table_relationships() -> str:
    """
    Analyzes and displays the relationships between tables in the database.

    This tool inspects the database schema to identify all foreign key
    relationships between tables. It then presents these relationships in a
    clear, easy-to-understand format. It also provides a summary of which
    tables are connected and which are isolated.

    Returns:
        A formatted string detailing the table relationships, or an error
        message if the analysis fails.
    """
    try:
        schema = db_manager.get_database_schema()
        
        if not schema.tables:
            return "No tables found in the database"
        
        response = f"Table Relationships Analysis\n"
        response += f"{'-' * 35}\n\n"
        
        # Find all foreign key relationships
        relationships = []
        for table_name, table_schema in schema.tables.items():
            for fk in table_schema.foreign_keys:
                relationships.append({
                    'from_table': table_name,
                    'from_columns': fk.constrained_columns,
                    'to_table': fk.referred_table,
                    'to_columns': fk.referred_columns
                })
        
        if not relationships:
            response += "No foreign key relationships found.\n"
        else:
            response += f"Found {len(relationships)} foreign key relationships:\n\n"
            for rel in relationships:
                response += f"  • {rel['from_table']}.{', '.join(rel['from_columns'])} → "
                response += f"{rel['to_table']}.{', '.join(rel['to_columns'])}\n"
        
        # Analyze table connectivity
        response += f"\nTable Connectivity:\n"
        connected_tables = set()
        for rel in relationships:
            connected_tables.add(rel['from_table'])
            connected_tables.add(rel['to_table'])
        
        isolated_tables = set(schema.tables.keys()) - connected_tables
        
        if connected_tables:
            response += f"  • Connected tables ({len(connected_tables)}): {', '.join(sorted(connected_tables))}\n"
        
        if isolated_tables:
            response += f"  • Isolated tables ({len(isolated_tables)}): {', '.join(sorted(isolated_tables))}\n"
        
        return response
        
    except Exception as e:
        print(f"ERROR in analyze_table_relationships: {e}")
        return f"Error analyzing table relationships: {str(e)}"


@mcp.tool()
def get_table_statistics(table_name: str) -> str:
    """
    Get detailed statistics for a specific table.

    This tool provides a detailed statistical overview of a specific table,
    including the total number of rows, column count, and information about
    primary keys, foreign keys, and indexes. It also lists each column
    with its data type, nullability, and default values.

    Args:
        table_name: The name of the table to get statistics for.

    Returns:
        A formatted string with the table's statistics, or an error
        message if the table is not found or the operation fails.
    """
    try:
        # Get basic schema info
        schema = db_manager.get_table_schema(table_name)
        
        if not schema.columns:
            return f"Table '{table_name}' not found or has no columns"
        
        response = f"Statistics for table '{table_name}'\n"
        response += f"{'-' * (len(table_name) + 25)}\n\n"
        
        # Basic info
        response += f"Column Count: {len(schema.columns)}\n"
        response += f"Primary Keys: {len(schema.primary_keys)}\n"
        response += f"Foreign Keys: {len(schema.foreign_keys)}\n"
        response += f"Indexes: {len(schema.indexes)}\n\n"
        
        # Get row count
        try:
            count_result = db_manager.execute_query(f"SELECT COUNT(*) as row_count FROM {table_name}")
            if count_result.success and count_result.data:
                row_count = count_result.data[0]['row_count']
                response += f"Total Rows: {row_count:,}\n\n"
        except Exception as e:
            response += f"Row count: Unable to determine ({str(e)})\n\n"
        
        # Column details
        response += "Column Details:\n"
        for col in schema.columns:
            response += f"  • {col.name}:\n"
            response += f"    - Type: {col.type}\n"
            response += f"    - Nullable: {'Yes' if col.nullable else 'No'}\n"
            if col.default:
                response += f"    - Default: {col.default}\n"
            if col.primary_key:
                response += f"    - Primary Key: Yes\n"
            response += "\n"
        
        return response
        
    except Exception as e:
        print(f"ERROR in get_table_statistics: {e}")
        return f"Error getting statistics for table '{table_name}': {str(e)}"


@mcp.tool()
def suggest_useful_queries(table_name: str) -> str:
    """
    Suggests useful queries for exploring a specific table.

    This tool generates a list of suggested SQL queries to help explore
    and analyze a given table. The suggestions include basic exploration
    queries, as well as more advanced queries for analyzing text, numeric,
    and date columns. It also suggests join queries if foreign key
    relationships are present.

    Args:
        table_name: The name of the table for which to suggest queries.

    Returns:
        A formatted string containing a list of suggested queries, or an
        error message if the table is not found or the operation fails.
    """
    try:
        schema = db_manager.get_table_schema(table_name)
        
        if not schema.columns:
            return f"Table '{table_name}' not found or has no columns"
        
        response = f"Suggested Queries for '{table_name}'\n"
        response += f"{'-' * (len(table_name) + 25)}\n\n"
        
        # Basic exploration queries
        response += "Basic Exploration:\n"
        response += f"  1. SELECT * FROM {table_name} LIMIT 10;\n"
        response += f"  2. SELECT COUNT(*) FROM {table_name};\n"
        
        # Column-specific queries
        text_columns = [col.name for col in schema.columns if 'char' in col.type.lower() or 'text' in col.type.lower()]
        numeric_columns = [col.name for col in schema.columns if any(t in col.type.lower() for t in ['int', 'float', 'decimal', 'numeric'])]
        date_columns = [col.name for col in schema.columns if any(t in col.type.lower() for t in ['date', 'time', 'timestamp'])]
        
        if text_columns:
            response += f"\nText Column Analysis:\n"
            for col in text_columns[:3]:  # Show first 3 text columns
                response += f"  • SELECT {col}, COUNT(*) FROM {table_name} GROUP BY {col} ORDER BY COUNT(*) DESC LIMIT 10;\n"
        
        if numeric_columns:
            response += f"\nNumeric Column Analysis:\n"
            for col in numeric_columns[:3]:  # Show first 3 numeric columns
                response += f"  • SELECT MIN({col}), MAX({col}), AVG({col}) FROM {table_name};\n"
        
        if date_columns:
            response += f"\nDate Column Analysis:\n"
            for col in date_columns[:2]:  # Show first 2 date columns
                response += f"  • SELECT MIN({col}), MAX({col}) FROM {table_name};\n"
        
        # Foreign key joins
        if schema.foreign_keys:
            response += f"\nJoin Queries:\n"
            for fk in schema.foreign_keys[:2]:  # Show first 2 foreign keys
                response += f"  • SELECT * FROM {table_name} t1 JOIN {fk.referred_table} t2 ON t1.{fk.constrained_columns[0]} = t2.{fk.referred_columns[0]} LIMIT 10;\n"
        
        return response
        
    except Exception as e:
        print(f"ERROR in suggest_useful_queries: {e}")
        return f"Error suggesting queries for table '{table_name}': {str(e)}"


@mcp.tool()
def get_transcript(url: str) -> str:
    """
    Fetch the complete transcript of a YouTube video.
    
    Args:
        url: YouTube video URL
    
    Returns:
        Formatted text containing the full video transcript as received from YouTube,
        NOT timestamp data. The response includes video metadata and the complete transcript text.
    
    Note: This tool extracts and returns the actual spoken content from the video,
    exactly as provided by the YouTube transcript API.
    """
    try:
        # Extract video ID
        video_id = None
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                break
        
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        # Validate video ID
        YouTubeVideo(video_id=video_id, url=url)
        
        # Fetch transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        # Keep transcript exactly as received, just extract the text content
        transcript_text = " ".join([item["text"] for item in transcript_list])
        word_count = len(transcript_text.split())
        
        response = TranscriptResponse(
            success=True,
            video_id=video_id,
            url=url,
            transcript=transcript_text,
            word_count=word_count
        )
        
        print(f"DEBUG: Fetched transcript for video ID: {video_id}, word count: {word_count}")
        return response.get_formatted_response()
    
    except Exception as e:
        print(f"ERROR in get_transcript: {e}")
        response = TranscriptResponse(
            success=False,
            video_id=video_id or "unknown",
            url=url,
            error=str(e)
        )
        return response.get_formatted_response()

@mcp.tool()
def visit_webpage(url: str) -> str:
    """
    Visits a webpage at the given URL and returns its content as a Markdown string.

    This tool sends a GET request to the specified URL, retrieves the HTML
    content, and converts it into a clean, readable Markdown format. It
    is useful for extracting the textual content from web pages for further
    analysis or processing.

    Args:
        url: The URL of the webpage to visit.

    Returns:
        A string containing the Markdown representation of the webpage
        content, or an error message if the webpage cannot be accessed.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Convert the HTML content to Markdown
        markdown_content = markdownify(response.text).strip()

        # Remove multiple line breaks
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        response_obj = WebpageResponse(
            success=True,
            url=url,
            content=markdown_content
        )
        
        print(f"DEBUG: Successfully fetched content for URL: {url}")
        return response_obj.get_formatted_response()
    
    except RequestException as e:
        print(f"ERROR in visit_webpage: {e}")
        response_obj = WebpageResponse(
            success=False,
            url=url,
            error=str(e)
        )
        return response_obj.get_formatted_response()
    
    except Exception as e:
        print(f"ERROR in visit_webpage: Unexpected error: {e}")
        response_obj = WebpageResponse(
            success=False,
            url=url,
            error=f"An unexpected error occurred: {str(e)}"
        )
        return response_obj.get_formatted_response()

@mcp.tool()
def find_similar_column_names(table_name: str, search_term: str) -> str:
    """
    Finds column names in a table that are similar to a given search term.

    This tool searches for column names in a specified table that match or
    are similar to a given search term. It provides exact matches, partial
    matches, and suggestions based on common naming conventions. This is
    helpful for finding the correct column name when it is not known.

    Args:
        table_name: The name of the table to search within.
        search_term: The term to search for in the column names.

    Returns:
        A formatted string with suggestions for similar column names, or
        a message if no similar columns are found.
    """
    try:
        schema = db_manager.get_table_schema(table_name)
        
        if not schema.columns:
            return f"Table '{table_name}' not found or has no columns"
        
        # Get all column names
        column_names = [col.name.lower() for col in schema.columns]
        search_lower = search_term.lower()
        
        # Find exact matches
        exact_matches = [name for name in column_names if name == search_lower]
        
        # Find partial matches
        partial_matches = [name for name in column_names if search_lower in name or name in search_lower]
        
        # Find similar matches (contains similar words)
        similar_words = ['name', 'category', 'title', 'label', 'type', 'kind', 'class']
        similar_matches = []
        for word in similar_words:
            if word in search_lower:
                similar_matches.extend([name for name in column_names if word in name])
        
        # Remove duplicates and organize results
        all_matches = list(set(exact_matches + partial_matches + similar_matches))
        
        response = f"Column name suggestions for '{search_term}' in table '{table_name}':\n\n"
        
        if exact_matches:
            response += f"✅ Exact matches: {exact_matches}\n"
        
        if partial_matches and not exact_matches:
            response += f"🔍 Partial matches: {partial_matches}\n"
        
        if similar_matches and not exact_matches and not partial_matches:
            response += f"💡 Similar matches: {list(set(similar_matches))}\n"
        
        if not all_matches:
            response += "❌ No similar column names found.\n"
        
        # Always show all available columns
        response += f"\n📋 All available columns in '{table_name}':\n"
        for col in schema.columns:
            response += f"  • {col.name} ({col.type})\n"
        
        return response
        
    except Exception as e:
        print(f"ERROR in find_similar_column_names: {e}")
        return f"Error searching for similar column names: {str(e)}"

if __name__ == "__main__":
    print("🚀 Starting Enhanced MCP Server ...... !")
    mcp.run(transport="streamable-http")

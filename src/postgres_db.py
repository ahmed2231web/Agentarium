"""
PostgreSQL Database Connection and Management with Pydantic Models

This module handles connections to a real PostgreSQL database server
and provides database introspection capabilities for the Text-to-SQL agent.
"""

import os
from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy import create_engine, MetaData, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationInfo
from enum import Enum

# Load environment variables
load_dotenv()

class ColumnType(str, Enum):
    """Common SQL column types"""
    INTEGER = "INTEGER"
    VARCHAR = "VARCHAR"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"
    DATE = "DATE"
    DECIMAL = "DECIMAL"
    FLOAT = "FLOAT"
    JSON = "JSON"
    UUID = "UUID"

class DatabaseColumn(BaseModel):
    """Represents a database column with all its properties"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Column data type")
    nullable: bool = Field(default=True, description="Whether column allows NULL values")
    default: Optional[str] = Field(None, description="Default value for the column")
    primary_key: bool = Field(default=False, description="Whether this column is a primary key")
    foreign_key: Optional[str] = Field(None, description="Foreign key reference if applicable")
    max_length: Optional[int] = Field(None, description="Maximum length for string columns")
    precision: Optional[int] = Field(None, description="Precision for numeric columns")
    scale: Optional[int] = Field(None, description="Scale for numeric columns")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Column name cannot be empty")
        return v.strip()

class ForeignKey(BaseModel):
    """Represents a foreign key constraint"""
    constrained_columns: List[str] = Field(..., description="Columns that are constrained")
    referred_table: str = Field(..., description="Referenced table name")
    referred_columns: List[str] = Field(..., description="Referenced columns")
    name: Optional[str] = Field(None, description="Foreign key constraint name")

class TableIndex(BaseModel):
    """Represents a database index"""
    name: str = Field(..., description="Index name")
    columns: List[str] = Field(..., description="Indexed columns")
    unique: bool = Field(default=False, description="Whether index is unique")

class TableSchema(BaseModel):
    """Complete schema information for a database table"""
    table_name: str = Field(..., description="Name of the table")
    columns: List[DatabaseColumn] = Field(default_factory=list, description="Table columns")
    primary_keys: List[str] = Field(default_factory=list, description="Primary key columns")
    foreign_keys: List[ForeignKey] = Field(default_factory=list, description="Foreign key constraints")
    indexes: List[TableIndex] = Field(default_factory=list, description="Table indexes")
    row_count: Optional[int] = Field(None, description="Approximate number of rows")
    
    @field_validator('table_name')
    @classmethod
    def validate_table_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Table name cannot be empty")
        return v.strip()

class DatabaseSchema(BaseModel):
    """Complete database schema information"""
    database_name: str = Field(..., description="Name of the database")
    tables: Dict[str, TableSchema] = Field(default_factory=dict, description="Database tables")
    total_tables: int = Field(default=0, description="Total number of tables")
    
    def get_table_names(self) -> List[str]:
        """Get sorted list of table names"""
        return sorted(self.tables.keys())
    
    def get_table_by_name(self, table_name: str) -> Optional[TableSchema]:
        """Get table schema by name"""
        return self.tables.get(table_name)

class QueryResult(BaseModel):
    """Represents the result of a database query"""
    success: bool = Field(..., description="Whether query executed successfully")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Query result data")
    error: Optional[str] = Field(None, description="Error message if query failed")
    rows_affected: Optional[int] = Field(None, description="Number of rows affected")
    execution_time: Optional[float] = Field(None, description="Query execution time in seconds")
    columns: Optional[List[str]] = Field(None, description="Column names in result")
    
    @field_validator('data')
    @classmethod
    def validate_data_with_success(cls, v, info: ValidationInfo):
        if info.data.get('success') and v is None:
            # If success is True but no data, it might be a non-SELECT query
            pass
        return v

class SampleData(BaseModel):
    """Represents sample data from a table"""
    table_name: str = Field(..., description="Name of the table")
    rows: List[Dict[str, Any]] = Field(default_factory=list, description="Sample data rows")
    total_rows_sampled: int = Field(default=0, description="Number of rows in sample")
    columns: List[str] = Field(default_factory=list, description="Column names")
    
    def get_formatted_preview(self, max_rows: int = 3) -> str:
        """Get a formatted preview of the sample data"""
        if not self.rows:
            return f"No sample data available for table '{self.table_name}'"
        
        preview = f"Sample data from '{self.table_name}' ({len(self.rows)} rows):\n"
        for i, row in enumerate(self.rows[:max_rows]):
            row_preview = ", ".join([f"{k}: {v}" for k, v in list(row.items())[:5]])
            if len(row) > 5:
                row_preview += "..."
            preview += f"  {i+1}. {row_preview}\n"
        
        if len(self.rows) > max_rows:
            preview += f"  ... and {len(self.rows) - max_rows} more rows"
        
        return preview

class ConnectionConfig(BaseModel):
    """Database connection configuration"""
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    username: str = Field(default="postgres", description="Database username")
    password: str = Field(default="", description="Database password")
    database: str = Field(default="postgres", description="Database name")
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    def get_connection_string(self) -> str:
        """Build PostgreSQL connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

class PostgreSQLManager:
    """
    Manages PostgreSQL database connections and operations with Pydantic models.
    """
    
    def __init__(self, database_name: Optional[str] = None):
        """
        Initialize PostgreSQL connection.
        
        Args:
            database_name (str): Optional specific database name to connect to
        """
        self.config = self._load_config(database_name)
        self.engine = None
        self.metadata_obj = MetaData()
        self._connect()
    
    def _load_config(self, database_name: Optional[str] = None) -> ConnectionConfig:
        """Load configuration from environment variables"""
        return ConnectionConfig(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', '5432')),
            username=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD', ''),
            database=database_name or os.getenv('POSTGRES_DB', 'postgres')
        )
    
    def _connect(self):
        """Establish connection to PostgreSQL database."""
        try:
            connection_string = self.config.get_connection_string()
            self.engine = create_engine(
                connection_string,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            
            # Test the connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            print(f"✅ Connected to 🐘 PostgreSQL database '{self.config.database}' successfully")
            
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            raise
    
    def list_databases(self) -> List[str]:
        """List all available databases on the PostgreSQL server."""
        try:
            temp_config = self.config.model_copy()
            temp_config.database = "postgres"
            temp_engine = create_engine(temp_config.get_connection_string())
            
            with temp_engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT datname FROM pg_database 
                    WHERE datistemplate = false 
                    ORDER BY datname
                """))
                databases = [row[0] for row in result]
            
            return databases
            
        except Exception as e:
            print(f"Error listing databases: {e}")
            return []
    
    def list_tables(self) -> List[str]:
        """List all tables in the current database."""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            return tables
        except Exception as e:
            print(f"Error listing tables: {e}")
            return []
    
    def get_table_schema(self, table_name: str) -> TableSchema:
        """Get detailed schema information for a specific table."""
        try:
            inspector = inspect(self.engine)
            
            # Get columns
            columns_info = inspector.get_columns(table_name)
            columns = []
            
            for col_info in columns_info:
                column = DatabaseColumn(
                    name=col_info['name'],
                    type=str(col_info['type']),
                    nullable=col_info['nullable'],
                    default=str(col_info['default']) if col_info['default'] is not None else None
                )
                columns.append(column)
            
            # Get primary keys
            pk_constraint = inspector.get_pk_constraint(table_name)
            primary_keys = pk_constraint.get('constrained_columns', [])
            
            # Update primary key info in columns
            for col in columns:
                if col.name in primary_keys:
                    col.primary_key = True
            
            # Get foreign keys
            fk_info = inspector.get_foreign_keys(table_name)
            foreign_keys = []
            for fk in fk_info:
                foreign_key = ForeignKey(
                    constrained_columns=fk['constrained_columns'],
                    referred_table=fk['referred_table'],
                    referred_columns=fk['referred_columns'],
                    name=fk.get('name')
                )
                foreign_keys.append(foreign_key)
            
            # Get indexes
            indexes_info = inspector.get_indexes(table_name)
            indexes = []
            for idx in indexes_info:
                index = TableIndex(
                    name=idx['name'],
                    columns=idx['column_names'],
                    unique=idx['unique']
                )
                indexes.append(index)
            
            return TableSchema(
                table_name=table_name,
                columns=columns,
                primary_keys=primary_keys,
                foreign_keys=foreign_keys,
                indexes=indexes
            )
            
        except Exception as e:
            print(f"Error getting schema for table {table_name}: {e}")
            return TableSchema(table_name=table_name)
    
    def get_database_schema(self) -> DatabaseSchema:
        """Get comprehensive schema information for the entire database."""
        schema = DatabaseSchema(database_name=self.config.database)
        
        tables = self.list_tables()
        for table in tables:
            table_schema = self.get_table_schema(table)
            schema.tables[table] = table_schema
        
        schema.total_tables = len(tables)
        return schema
    
    def execute_query(self, query: str) -> QueryResult:
        """Execute a SQL query and return structured results."""
        import time
        start_time = time.time()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                execution_time = time.time() - start_time
                
                if result.returns_rows:
                    rows = result.fetchall()
                    columns = list(result.keys())
                    data = [dict(zip(columns, row)) for row in rows]
                    
                    return QueryResult(
                        success=True,
                        data=data,
                        columns=columns,
                        execution_time=execution_time
                    )
                else:
                    return QueryResult(
                        success=True,
                        rows_affected=result.rowcount,
                        execution_time=execution_time
                    )
                    
        except SQLAlchemyError as e:
            return QueryResult(
                success=False,
                error=f"SQL Error: {str(e)}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return QueryResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> SampleData:
        """Get sample data from a table."""
        try:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            result = self.execute_query(query)
            
            if result.success and result.data:
                return SampleData(
                    table_name=table_name,
                    rows=result.data,
                    total_rows_sampled=len(result.data),
                    columns=result.columns or []
                )
            else:
                return SampleData(table_name=table_name)
                
        except Exception as e:
            print(f"Error getting sample data from {table_name}: {e}")
            return SampleData(table_name=table_name)
    
    def generate_table_description(self, table_name: str) -> str:
        """Generate a human-readable description of a table."""
        schema = self.get_table_schema(table_name)
        
        if not schema.columns:
            return f"Table '{table_name}' not found or has no columns."
        
        description = f"Table '{table_name}':\n"
        description += "Columns:\n"
        
        for col in schema.columns:
            nullable = "" if col.nullable else " (NOT NULL)"
            default = f" DEFAULT {col.default}" if col.default else ""
            pk = " (PRIMARY KEY)" if col.primary_key else ""
            
            description += f"  - {col.name}: {col.type}{nullable}{default}{pk}\n"
        
        if schema.foreign_keys:
            description += "Foreign Keys:\n"
            for fk in schema.foreign_keys:
                description += f"  - {fk.constrained_columns} -> {fk.referred_table}.{fk.referred_columns}\n"
        
        return description
    
    def close(self):
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            print()
            print("Database connection closed.")


def main():
    """Test the PostgreSQL connection and display database information."""
    print()
    print("=" * 60)
    print()
    
    try:
        # Create database manager
        db_manager = PostgreSQLManager()
        
        # Get database schema
        schema = db_manager.get_database_schema()
        print(f"\n📊 Database: {schema.database_name}")
        print(f"Total tables: {schema.total_tables}")
        
        # List tables
        if schema.tables:
            print(f"\n📋 Tables:")
            for table_name in schema.get_table_names():
                table_schema = schema.get_table_by_name(table_name)
                print(f"  - {table_name} ({len(table_schema.columns)} columns)")
                
                # Get sample data
                sample = db_manager.get_sample_data(table_name, limit=2)
                if sample.rows:
                    print(f"    Sample: {sample.get_formatted_preview(1)}")
        
        db_manager.close()

        print()
        print("=" * 60)
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
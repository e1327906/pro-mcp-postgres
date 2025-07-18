from typing import Any, Optional, Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor
from mcp.server.fastmcp import FastMCP
import sys
import logging
import os
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('postgres-mcp-server')

# Initialize server with capabilities
mcp = FastMCP(
    "PostgreSQL Multi-Database Explorer",
    capabilities={
        "tools": True,      # Enable tool support
        "logging": True,    # Enable logging support
        "resources": False, # We don't use resources
        "prompts": False   # We don't use prompts
    }
)

# Database connection manager
class DatabaseManager:
    def __init__(self):
        self.connections: Dict[str, str] = {}
        self.current_db: Optional[str] = None
        self._load_connections()
    
    def _load_connections(self):
        """Load database connections from environment variables and command line."""
        parser = argparse.ArgumentParser(description="PostgreSQL Multi-Database Explorer MCP server")
        parser.add_argument(
            "--conn",
            dest="conn",
            help="PostgreSQL connection string or DSN (overrides env vars)"
        )
        args, _ = parser.parse_known_args()
        
        # Load from command line argument first (highest priority)
        if args.conn:
            db_name = "primary"
            self.connections[db_name] = args.conn
            self.current_db = db_name
            logger.info(f"Using command line connection as primary database")
        
        # Load from POSTGRES_CONNECTION_STRING (can be comma-separated)
        connection_string = os.getenv("POSTGRES_CONNECTION_STRING")
        if connection_string:
            # Split by comma and process each connection
            connections = [conn.strip() for conn in connection_string.split(",")]
            for i, conn in enumerate(connections):
                if conn:  # Skip empty connections
                    if i == 0 and not self.current_db:
                        # First connection becomes primary if no command line arg
                        db_name = "primary"
                        self.current_db = db_name
                    else:
                        # Subsequent connections get numbered names
                        db_name = f"db_{i + 1}"
                    
                    self.connections[db_name] = conn
                    logger.info(f"Added database connection: {db_name}")
        
        # Load additional individual connections from environment variables
        # Format: POSTGRES_DB_<NAME>=connection_string
        for key, value in os.environ.items():
            if key.startswith("POSTGRES_DB_"):
                db_name = key[12:].lower()  # Remove "POSTGRES_DB_" prefix
                self.connections[db_name] = value
                if not self.current_db:
                    self.current_db = db_name
                logger.info(f"Added named database connection: {db_name}")
        
        logger.info(f"Initialized with {len(self.connections)} database connections")
        if self.current_db:
            logger.info(f"Current database: {self.current_db}")
        elif not self.connections:
            logger.warning("No database connections configured!")
    
    def get_connection(self, db_name: Optional[str] = None) -> psycopg2.extensions.connection:
        """Get a connection to the specified database or current database."""
        target_db = db_name or self.current_db
        
        if not target_db:
            raise RuntimeError("No database selected. Use switch_database() or provide db_name parameter.")
        
        if target_db not in self.connections:
            raise RuntimeError(f"Database '{target_db}' not found. Available databases: {list(self.connections.keys())}")
        
        connection_string = self.connections[target_db]
        try:
            conn = psycopg2.connect(connection_string)
            logger.debug(f"Database connection established successfully to '{target_db}'")
            return conn
        except Exception as e:
            logger.error(f"Failed to establish database connection to '{target_db}': {str(e)}")
            raise
    
    def switch_database(self, db_name: str) -> bool:
        """Switch to a different database."""
        if db_name not in self.connections:
            return False
        self.current_db = db_name
        logger.info(f"Switched to database: {db_name}")
        return True
    
    def list_databases(self) -> List[str]:
        """List all available database connections."""
        return list(self.connections.keys())
    
    def get_current_database(self) -> Optional[str]:
        """Get the name of the current database."""
        return self.current_db
    
    def add_database(self, name: str, connection_string: str) -> bool:
        """Add a new database connection."""
        try:
            # Test the connection
            conn = psycopg2.connect(connection_string)
            conn.close()
            
            self.connections[name] = connection_string
            logger.info(f"Added database connection: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add database connection '{name}': {str(e)}")
            return False
    
    def remove_database(self, name: str) -> bool:
        """Remove a database connection."""
        if name not in self.connections:
            return False
        
        del self.connections[name]
        if self.current_db == name:
            self.current_db = next(iter(self.connections.keys())) if self.connections else None
        
        logger.info(f"Removed database connection: {name}")
        return True

# Initialize database manager
db_manager = DatabaseManager()

logger.info(
    "Starting PostgreSQL Multi-Database MCP server – %d database(s) configured",
    len(db_manager.connections)
)

@mcp.tool()
def list_databases() -> str:
    """List all available database connections."""
    databases = db_manager.list_databases()
    current = db_manager.get_current_database()
    
    if not databases:
        return "No database connections configured."
    
    result_lines = ["Available databases:", "-------------------"]
    for db in databases:
        marker = " (current)" if db == current else ""
        result_lines.append(f"• {db}{marker}")
    
    return "\n".join(result_lines)

@mcp.tool()
def switch_database(db_name: str) -> str:
    """Switch to a different database connection.
    
    Args:
        db_name: The name of the database to switch to
    """
    if db_manager.switch_database(db_name):
        return f"Switched to database: {db_name}"
    else:
        available = db_manager.list_databases()
        return f"Database '{db_name}' not found. Available databases: {', '.join(available)}"

@mcp.tool()
def get_current_database() -> str:
    """Get the name of the currently selected database."""
    current = db_manager.get_current_database()
    if current:
        return f"Current database: {current}"
    else:
        return "No database currently selected."

@mcp.tool()
def add_database_connection(name: str, connection_string: str) -> str:
    """Add a new database connection dynamically.
    
    Args:
        name: Name for the new database connection
        connection_string: PostgreSQL connection string
    """
    if db_manager.add_database(name, connection_string):
        return f"Successfully added database connection: {name}"
    else:
        return f"Failed to add database connection: {name}"

@mcp.tool()
def remove_database_connection(name: str) -> str:
    """Remove a database connection.
    
    Args:
        name: Name of the database connection to remove
    """
    if name == "primary":
        return "Cannot remove the primary database connection."
    
    if db_manager.remove_database(name):
        return f"Successfully removed database connection: {name}"
    else:
        return f"Database connection '{name}' not found."

@mcp.tool()
def query(sql: str, parameters: Optional[list] = None, database: Optional[str] = None) -> str:
    """Execute a SQL query against the PostgreSQL database.
    
    Args:
        sql: The SQL query to execute
        parameters: Optional list of parameters for the query
        database: Optional database name to execute against (uses current if not specified)
    """
    conn = None
    try:
        try:
            conn = db_manager.get_connection(database)
            target_db = database or db_manager.get_current_database()
        except RuntimeError as e:
            return str(e)
        
        logger.info(f"Executing query on '{target_db}': {sql[:100]}{'...' if len(sql) > 100 else ''}")
        
        # Use RealDictCursor for better handling of special characters in column names
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                # Properly escape the query using mogrify
                if parameters:
                    query_string = cur.mogrify(sql, parameters).decode('utf-8')
                    logger.debug(f"Query with parameters: {query_string}")
                else:
                    query_string = sql
                
                # Execute the escaped query
                cur.execute(query_string)
                
                # For non-SELECT queries
                if cur.description is None:
                    conn.commit()
                    affected_rows = cur.rowcount
                    logger.info(f"Non-SELECT query executed successfully on '{target_db}'. Rows affected: {affected_rows}")
                    return f"Query executed successfully on '{target_db}'. Rows affected: {affected_rows}"
                
                # For SELECT queries
                rows = cur.fetchall()
                if not rows:
                    logger.info(f"Query on '{target_db}' returned no results")
                    return f"No results found on '{target_db}'"
                
                logger.info(f"Query on '{target_db}' returned {len(rows)} rows")
                
                # Format results with proper string escaping
                result_lines = ["Results:", "--------"]
                for row in rows:
                    try:
                        # Convert each value to string safely
                        line_items = []
                        for key, val in row.items():
                            if val is None:
                                formatted_val = "NULL"
                            elif isinstance(val, (bytes, bytearray)):
                                formatted_val = val.decode('utf-8', errors='replace')
                            else:
                                formatted_val = str(val).replace('%', '%%')
                            line_items.append(f"{key}: {formatted_val}")
                        result_lines.append(" | ".join(line_items))
                    except Exception as row_error:
                        error_msg = f"Error formatting row: {str(row_error)}"
                        logger.error(error_msg)
                        result_lines.append(error_msg)
                        continue
                
                return "\n".join(result_lines)
                
            except Exception as exec_error:
                error_msg = f"Query error: {str(exec_error)}\nQuery: {sql}"
                logger.error(error_msg)
                return error_msg
    except Exception as conn_error:
        error_msg = f"Connection error: {str(conn_error)}"
        logger.error(error_msg)
        return error_msg
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")

@mcp.tool()
def list_schemas(database: Optional[str] = None) -> str:
    """List all schemas in the database.
    
    Args:
        database: Optional database name to query (uses current if not specified)
    """
    target_db = database or db_manager.get_current_database()
    logger.info(f"Listing database schemas from '{target_db}'")
    return query("SELECT schema_name FROM information_schema.schemata ORDER BY schema_name", database=database)

@mcp.tool()
def list_tables(db_schema: str = 'public', database: Optional[str] = None) -> str:
    """List all tables in a specific schema.
    
    Args:
        db_schema: The schema name to list tables from (defaults to 'public')
        database: Optional database name to query (uses current if not specified)
    """
    target_db = database or db_manager.get_current_database()
    logger.info(f"Listing tables in schema '{db_schema}' from database '{target_db}'")
    sql = """
    SELECT table_name, table_type
    FROM information_schema.tables
    WHERE table_schema = %s
    ORDER BY table_name
    """
    return query(sql, [db_schema], database=database)

@mcp.tool()
def describe_table(table_name: str, db_schema: str = 'public', database: Optional[str] = None) -> str:
    """Get detailed information about a table.
    
    Args:
        table_name: The name of the table to describe
        db_schema: The schema name (defaults to 'public')
        database: Optional database name to query (uses current if not specified)
    """
    target_db = database or db_manager.get_current_database()
    logger.info(f"Describing table '{db_schema}.{table_name}' from database '{target_db}'")
    sql = """
    SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default,
        character_maximum_length
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    ORDER BY ordinal_position
    """
    return query(sql, [db_schema, table_name], database=database)

@mcp.tool()
def get_foreign_keys(table_name: str, db_schema: str = 'public', database: Optional[str] = None) -> str:
    """Get foreign key information for a table.
    
    Args:
        table_name: The name of the table to get foreign keys from
        db_schema: The schema name (defaults to 'public')
        database: Optional database name to query (uses current if not specified)
    """
    target_db = database or db_manager.get_current_database()
    logger.info(f"Getting foreign keys for table '{db_schema}.{table_name}' from database '{target_db}'")
    sql = """
    SELECT 
        tc.constraint_name,
        kcu.column_name as fk_column,
        ccu.table_schema as referenced_schema,
        ccu.table_name as referenced_table,
        ccu.column_name as referenced_column
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.referential_constraints rc
        ON tc.constraint_name = rc.constraint_name
    JOIN information_schema.constraint_column_usage ccu
        ON rc.unique_constraint_name = ccu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = %s
        AND tc.table_name = %s
    ORDER BY tc.constraint_name, kcu.ordinal_position
    """
    return query(sql, [db_schema, table_name], database=database)

@mcp.tool()
def find_relationships(table_name: str, db_schema: str = 'public', database: Optional[str] = None) -> str:
    """Find both explicit and implied relationships for a table.
    
    Args:
        table_name: The name of the table to analyze relationships for
        db_schema: The schema name (defaults to 'public')
        database: Optional database name to query (uses current if not specified)
    """
    target_db = database or db_manager.get_current_database()
    logger.info(f"Finding relationships for table '{db_schema}.{table_name}' from database '{target_db}'")
    try:
        # First get explicit foreign key relationships
        fk_sql = """
        SELECT 
            kcu.column_name,
            ccu.table_name as foreign_table,
            ccu.column_name as foreign_column,
            'Explicit FK' as relationship_type,
            1 as confidence_level
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = %s
            AND tc.table_name = %s
        """
        
        logger.debug("Querying explicit foreign key relationships")
        explicit_results = query(fk_sql, [db_schema, table_name], database=database)
        
        # Then look for implied relationships based on common patterns
        logger.debug("Querying implied relationships")
        implied_sql = """
        WITH source_columns AS (
            -- Get all ID-like columns from our table
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = %s 
            AND table_name = %s
            AND (
                column_name LIKE '%%id' 
                OR column_name LIKE '%%_id'
                OR column_name LIKE '%%_fk'
            )
        ),
        potential_references AS (
            -- Find tables that might be referenced by our ID columns
            SELECT DISTINCT
                sc.column_name as source_column,
                sc.data_type as source_type,
                t.table_name as target_table,
                c.column_name as target_column,
                c.data_type as target_type,
                CASE
                    -- Highest confidence: column matches table_id pattern and types match
                    WHEN sc.column_name = t.table_name || '_id' 
                        AND sc.data_type = c.data_type THEN 2
                    -- High confidence: column ends with _id and types match
                    WHEN sc.column_name LIKE '%%_id' 
                        AND sc.data_type = c.data_type THEN 3
                    -- Medium confidence: column contains table name and types match
                    WHEN sc.column_name LIKE '%%' || t.table_name || '%%'
                        AND sc.data_type = c.data_type THEN 4
                    -- Lower confidence: column ends with id and types match
                    WHEN sc.column_name LIKE '%%id'
                        AND sc.data_type = c.data_type THEN 5
                END as confidence_level
            FROM source_columns sc
            CROSS JOIN information_schema.tables t
            JOIN information_schema.columns c 
                ON c.table_schema = t.table_schema 
                AND c.table_name = t.table_name
                AND (c.column_name = 'id' OR c.column_name = sc.column_name)
            WHERE t.table_schema = %s
                AND t.table_name != %s  -- Exclude self-references
        )
        SELECT 
            source_column as column_name,
            target_table as foreign_table,
            target_column as foreign_column,
            CASE 
                WHEN confidence_level = 2 THEN 'Strong implied relationship (exact match)'
                WHEN confidence_level = 3 THEN 'Strong implied relationship (_id pattern)'
                WHEN confidence_level = 4 THEN 'Likely implied relationship (name match)'
                ELSE 'Possible implied relationship'
            END as relationship_type,
            confidence_level
        FROM potential_references
        WHERE confidence_level IS NOT NULL
        ORDER BY confidence_level, source_column;
        """
        implied_results = query(implied_sql, [db_schema, table_name], database=database)
        
        return "Explicit Relationships:\n" + explicit_results + "\n\nImplied Relationships:\n" + implied_results
        
    except Exception as e:
        error_msg = f"Error finding relationships: {str(e)}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    try:
        logger.info("Starting MCP Postgres server...")
        mcp.run()
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        sys.exit(1)

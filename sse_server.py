#!/usr/bin/env python3
"""
Standalone SSE MCP Server for PostgreSQL
Simplified version that works independently
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Optional, Dict, List
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleDBManager:
    """Simple database manager for SSE server."""
    
    def __init__(self):
        self.connections = {}
        self.current_db = None
        self.load_connections()
    
    def load_connections(self):
        """Load database connections from environment."""
        conn_str = os.getenv("POSTGRES_CONNECTION_STRING")
        if conn_str:
            connections = [conn.strip() for conn in conn_str.split(',')]
            for i, conn in enumerate(connections):
                name = f"db_{i+1}" if i > 0 else "primary"
                self.connections[name] = conn
                if self.current_db is None:
                    self.current_db = name
        
        logger.info(f"Loaded {len(self.connections)} database connections")
    
    def get_connection(self, db_name: Optional[str] = None):
        """Get database connection."""
        if db_name and db_name in self.connections:
            conn_str = self.connections[db_name]
        elif self.current_db:
            conn_str = self.connections[self.current_db]
        else:
            raise Exception("No database connection available")
        
        return psycopg2.connect(conn_str, cursor_factory=RealDictCursor)
    
    def list_databases(self) -> List[str]:
        """List available databases."""
        return list(self.connections.keys())
    
    def add_database(self, name: str, connection_string: str) -> bool:
        """Add a new database connection."""
        try:
            # Test the connection
            conn = psycopg2.connect(connection_string, cursor_factory=RealDictCursor)
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
    
    def execute_query(self, sql: str, db_name: Optional[str] = None) -> str:
        """Execute SQL query and return results."""
        try:
            with self.get_connection(db_name) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    
                    if cur.description:
                        results = cur.fetchall()
                        if results:
                            return json.dumps([dict(row) for row in results], indent=2, default=str)
                        else:
                            return "No results returned"
                    else:
                        return f"Query executed successfully. Rows affected: {cur.rowcount}"
        except Exception as e:
            return f"Database error: {str(e)}"

# Initialize database manager
db_manager = SimpleDBManager()

# Create FastAPI app
app = FastAPI(title="PostgreSQL SSE MCP Server", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "PostgreSQL SSE MCP Server",
        "version": "1.0.0",
        "protocol": "sse",
        "databases": len(db_manager.connections),
        "status": "running"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "databases": len(db_manager.connections),
        "current_db": db_manager.current_db
    }

# Store active SSE connections for message handling
sse_connections = []

@app.post("/sse")
async def sse_post_endpoint(request: Request):
    """Handle MCP messages via POST to SSE endpoint."""
    try:
        body = await request.body()
        message = json.loads(body)
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id", 1)
        
        logger.info(f"Received MCP message: {method}")
        
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "PostgreSQL SSE MCP Server",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "list_databases",
                            "description": "List all available database connections",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "switch_database", 
                            "description": "Switch to a different database connection",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"db_name": {"type": "string", "description": "Database name to switch to"}},
                                "required": ["db_name"]
                            }
                        },
                        {
                            "name": "get_current_database",
                            "description": "Get the name of the currently selected database",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "query",
                            "description": "Execute a SQL query against the PostgreSQL database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sql": {"type": "string", "description": "SQL query to execute"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                },
                                "required": ["sql"]
                            }
                        },
                        {
                            "name": "list_schemas",
                            "description": "List all schemas in the database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"database": {"type": "string", "description": "Database name (optional)"}}
                            }
                        },
                        {
                            "name": "list_tables",
                            "description": "List all tables in a specific schema",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "db_schema": {"type": "string", "description": "Schema name", "default": "public"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                }
                            }
                        },
                        {
                            "name": "describe_table",
                            "description": "Get detailed information about a table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "Table name"},
                                    "db_schema": {"type": "string", "description": "Schema name", "default": "public"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                },
                                "required": ["table_name"]
                            }
                        },
                        {
                            "name": "add_database_connection",
                            "description": "Add a new database connection dynamically",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name for the new database connection"},
                                    "connection_string": {"type": "string", "description": "PostgreSQL connection string"}
                                },
                                "required": ["name", "connection_string"]
                            }
                        },
                        {
                            "name": "remove_database_connection",
                            "description": "Remove a database connection",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the database connection to remove"}
                                },
                                "required": ["name"]
                            }
                        },
                        {
                            "name": "get_foreign_keys",
                            "description": "Get foreign key information for a table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "The name of the table to get foreign keys from"},
                                    "db_schema": {"type": "string", "description": "Schema name", "default": "public"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                },
                                "required": ["table_name"]
                            }
                        },
                        {
                            "name": "find_relationships",
                            "description": "Find both explicit and implied relationships for a table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "The name of the table to analyze relationships for"},
                                    "db_schema": {"type": "string", "description": "Schema name", "default": "public"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                },
                                "required": ["table_name"]
                            }
                        }
                    ]
                }
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            try:
                if tool_name == "list_databases":
                    databases = db_manager.list_databases()
                    result = f"Available databases: {', '.join(databases)}"
                elif tool_name == "switch_database":
                    db_name = tool_args.get("db_name")
                    if db_name and db_name in db_manager.connections:
                        db_manager.current_db = db_name
                        result = f"Switched to database: {db_name}"
                    else:
                        available = db_manager.list_databases()
                        result = f"Database '{db_name}' not found. Available: {', '.join(available)}"
                elif tool_name == "get_current_database":
                    current = db_manager.current_db or "None"
                    result = f"Current database: {current}"
                elif tool_name == "query":
                    sql = tool_args.get("sql")
                    database = tool_args.get("database")
                    if sql:
                        result = db_manager.execute_query(sql, database)
                    else:
                        result = "Error: SQL query is required"
                elif tool_name == "list_schemas":
                    database = tool_args.get("database")
                    sql = "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
                    result = db_manager.execute_query(sql, database)
                elif tool_name == "list_tables":
                    db_schema = tool_args.get("db_schema", "public")
                    database = tool_args.get("database")
                    sql = f"""
                    SELECT table_name, table_type 
                    FROM information_schema.tables 
                    WHERE table_schema = '{db_schema}' 
                    ORDER BY table_name
                    """
                    result = db_manager.execute_query(sql, database)
                elif tool_name == "describe_table":
                    table_name = tool_args.get("table_name")
                    db_schema = tool_args.get("db_schema", "public")
                    database = tool_args.get("database")
                    sql = f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_schema = '{db_schema}' AND table_name = '{table_name}'
                    ORDER BY ordinal_position
                    """
                    result = db_manager.execute_query(sql, database)
                elif tool_name == "add_database_connection":
                    name = tool_args.get("name")
                    connection_string = tool_args.get("connection_string")
                    if name and connection_string:
                        if db_manager.add_database(name, connection_string):
                            result = f"Successfully added database connection: {name}"
                        else:
                            result = f"Failed to add database connection: {name}"
                    else:
                        result = "Error: Both name and connection_string are required"
                elif tool_name == "remove_database_connection":
                    name = tool_args.get("name")
                    if name:
                        if name == "primary":
                            result = "Cannot remove the primary database connection."
                        elif db_manager.remove_database(name):
                            result = f"Successfully removed database connection: {name}"
                        else:
                            result = f"Database connection '{name}' not found."
                    else:
                        result = "Error: name parameter is required"
                elif tool_name == "get_foreign_keys":
                    table_name = tool_args.get("table_name")
                    db_schema = tool_args.get("db_schema", "public")
                    database = tool_args.get("database")
                    if table_name:
                        sql = f"""
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
                            AND tc.table_schema = '{db_schema}'
                            AND tc.table_name = '{table_name}'
                        ORDER BY tc.constraint_name, kcu.ordinal_position
                        """
                        result = db_manager.execute_query(sql, database)
                    else:
                        result = "Error: table_name parameter is required"
                elif tool_name == "find_relationships":
                    table_name = tool_args.get("table_name")
                    db_schema = tool_args.get("db_schema", "public")
                    database = tool_args.get("database")
                    if table_name:
                        try:
                            # First get explicit foreign key relationships
                            fk_sql = f"""
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
                                AND tc.table_schema = '{db_schema}'
                                AND tc.table_name = '{table_name}'
                            """
                            explicit_results = db_manager.execute_query(fk_sql, database)
                            
                            # Then look for implied relationships
                            implied_sql = f"""
                            WITH source_columns AS (
                                SELECT column_name, data_type
                                FROM information_schema.columns
                                WHERE table_schema = '{db_schema}' 
                                AND table_name = '{table_name}'
                                AND (
                                    column_name LIKE '%id' 
                                    OR column_name LIKE '%_id'
                                    OR column_name LIKE '%_fk'
                                )
                            ),
                            potential_references AS (
                                SELECT DISTINCT
                                    sc.column_name as source_column,
                                    sc.data_type as source_type,
                                    t.table_name as target_table,
                                    c.column_name as target_column,
                                    c.data_type as target_type,
                                    CASE
                                        WHEN sc.column_name = t.table_name || '_id' 
                                            AND sc.data_type = c.data_type THEN 2
                                        WHEN sc.column_name LIKE '%_id' 
                                            AND sc.data_type = c.data_type THEN 3
                                        WHEN sc.column_name LIKE '%' || t.table_name || '%'
                                            AND sc.data_type = c.data_type THEN 4
                                        WHEN sc.column_name LIKE '%id'
                                            AND sc.data_type = c.data_type THEN 5
                                    END as confidence_level
                                FROM source_columns sc
                                CROSS JOIN information_schema.tables t
                                JOIN information_schema.columns c 
                                    ON c.table_schema = t.table_schema 
                                    AND c.table_name = t.table_name
                                    AND (c.column_name = 'id' OR c.column_name = sc.column_name)
                                WHERE t.table_schema = '{db_schema}'
                                    AND t.table_name != '{table_name}'
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
                            ORDER BY confidence_level, source_column
                            """
                            implied_results = db_manager.execute_query(implied_sql, database)
                            
                            result = f"Explicit Relationships:\\n{explicit_results}\\n\\nImplied Relationships:\\n{implied_results}"
                        except Exception as e:
                            result = f"Error finding relationships: {str(e)}"
                    else:
                        result = "Error: table_name parameter is required"
                else:
                    result = f"Unknown tool: {tool_name}"
                
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": str(result)
                            }
                        ]
                    }
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": f"Tool execution error: {str(e)}"
                    }
                }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
        
        return response
        
    except Exception as e:
        logger.error(f"SSE POST endpoint error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

@app.get("/sse")
async def sse_endpoint():
    """SSE endpoint for MCP communication."""
    async def event_generator():
        try:
            logger.info("SSE connection established")
            
            # Just keep the connection alive - actual messages handled via POST
            counter = 0
            while True:
                await asyncio.sleep(30)  # Send keepalive every 30 seconds
                counter += 1
                keepalive = {
                    "jsonrpc": "2.0",
                    "method": "notifications/ping",
                    "params": {
                        "counter": counter,
                        "databases": len(db_manager.connections),
                        "timestamp": counter * 30
                    }
                }
                yield f"data: {json.dumps(keepalive)}\n\n"
                
        except asyncio.CancelledError:
            logger.info("SSE connection closed")
            return
        except Exception as e:
            logger.error(f"SSE error: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            yield f"data: {json.dumps(error_response)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )

@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Handle MCP JSON-RPC requests."""
    try:
        body = await request.body()
        message = json.loads(body)
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id", 1)
        
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "PostgreSQL SSE MCP Server",
                        "version": "1.0.0"
                    }
                }
            }
        elif method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "list_databases",
                            "description": "List all available database connections",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "switch_database", 
                            "description": "Switch to a different database connection",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"db_name": {"type": "string", "description": "Database name to switch to"}},
                                "required": ["db_name"]
                            }
                        },
                        {
                            "name": "get_current_database",
                            "description": "Get the name of the currently selected database",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "query",
                            "description": "Execute a SQL query against the PostgreSQL database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sql": {"type": "string", "description": "SQL query to execute"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                },
                                "required": ["sql"]
                            }
                        },
                        {
                            "name": "list_schemas",
                            "description": "List all schemas in the database",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"database": {"type": "string", "description": "Database name (optional)"}}
                            }
                        },
                        {
                            "name": "list_tables",
                            "description": "List all tables in a specific schema",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "db_schema": {"type": "string", "description": "Schema name", "default": "public"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                }
                            }
                        },
                        {
                            "name": "describe_table",
                            "description": "Get detailed information about a table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "Table name"},
                                    "db_schema": {"type": "string", "description": "Schema name", "default": "public"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                },
                                "required": ["table_name"]
                            }
                        },
                        {
                            "name": "add_database_connection",
                            "description": "Add a new database connection dynamically",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name for the new database connection"},
                                    "connection_string": {"type": "string", "description": "PostgreSQL connection string"}
                                },
                                "required": ["name", "connection_string"]
                            }
                        },
                        {
                            "name": "remove_database_connection",
                            "description": "Remove a database connection",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Name of the database connection to remove"}
                                },
                                "required": ["name"]
                            }
                        },
                        {
                            "name": "get_foreign_keys",
                            "description": "Get foreign key information for a table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "The name of the table to get foreign keys from"},
                                    "db_schema": {"type": "string", "description": "Schema name", "default": "public"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                },
                                "required": ["table_name"]
                            }
                        },
                        {
                            "name": "find_relationships",
                            "description": "Find both explicit and implied relationships for a table",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "table_name": {"type": "string", "description": "The name of the table to analyze relationships for"},
                                    "db_schema": {"type": "string", "description": "Schema name", "default": "public"},
                                    "database": {"type": "string", "description": "Database name (optional)"}
                                },
                                "required": ["table_name"]
                            }
                        }
                    ]
                }
            }
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            
            try:
                if tool_name == "list_databases":
                    databases = db_manager.list_databases()
                    result = f"Available databases: {', '.join(databases)}"
                elif tool_name == "switch_database":
                    db_name = tool_args.get("db_name")
                    if db_name and db_name in db_manager.connections:
                        db_manager.current_db = db_name
                        result = f"Switched to database: {db_name}"
                    else:
                        available = db_manager.list_databases()
                        result = f"Database '{db_name}' not found. Available: {', '.join(available)}"
                elif tool_name == "get_current_database":
                    current = db_manager.current_db or "None"
                    result = f"Current database: {current}"
                elif tool_name == "query":
                    sql = tool_args.get("sql")
                    database = tool_args.get("database")
                    if sql:
                        result = db_manager.execute_query(sql, database)
                    else:
                        result = "Error: SQL query is required"
                elif tool_name == "list_schemas":
                    database = tool_args.get("database")
                    sql = "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
                    result = db_manager.execute_query(sql, database)
                elif tool_name == "list_tables":
                    db_schema = tool_args.get("db_schema", "public")
                    database = tool_args.get("database")
                    sql = f"""
                    SELECT table_name, table_type 
                    FROM information_schema.tables 
                    WHERE table_schema = '{db_schema}' 
                    ORDER BY table_name
                    """
                    result = db_manager.execute_query(sql, database)
                elif tool_name == "describe_table":
                    table_name = tool_args.get("table_name")
                    db_schema = tool_args.get("db_schema", "public")
                    database = tool_args.get("database")
                    sql = f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_schema = '{db_schema}' AND table_name = '{table_name}'
                    ORDER BY ordinal_position
                    """
                    result = db_manager.execute_query(sql, database)
                elif tool_name == "add_database_connection":
                    name = tool_args.get("name")
                    connection_string = tool_args.get("connection_string")
                    if name and connection_string:
                        if db_manager.add_database(name, connection_string):
                            result = f"Successfully added database connection: {name}"
                        else:
                            result = f"Failed to add database connection: {name}"
                    else:
                        result = "Error: Both name and connection_string are required"
                elif tool_name == "remove_database_connection":
                    name = tool_args.get("name")
                    if name:
                        if name == "primary":
                            result = "Cannot remove the primary database connection."
                        elif db_manager.remove_database(name):
                            result = f"Successfully removed database connection: {name}"
                        else:
                            result = f"Database connection '{name}' not found."
                    else:
                        result = "Error: name parameter is required"
                elif tool_name == "get_foreign_keys":
                    table_name = tool_args.get("table_name")
                    db_schema = tool_args.get("db_schema", "public")
                    database = tool_args.get("database")
                    if table_name:
                        sql = f"""
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
                            AND tc.table_schema = '{db_schema}'
                            AND tc.table_name = '{table_name}'
                        ORDER BY tc.constraint_name, kcu.ordinal_position
                        """
                        result = db_manager.execute_query(sql, database)
                    else:
                        result = "Error: table_name parameter is required"
                elif tool_name == "find_relationships":
                    table_name = tool_args.get("table_name")
                    db_schema = tool_args.get("db_schema", "public")
                    database = tool_args.get("database")
                    if table_name:
                        try:
                            # First get explicit foreign key relationships
                            fk_sql = f"""
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
                                AND tc.table_schema = '{db_schema}'
                                AND tc.table_name = '{table_name}'
                            """
                            explicit_results = db_manager.execute_query(fk_sql, database)
                            
                            # Then look for implied relationships
                            implied_sql = f"""
                            WITH source_columns AS (
                                SELECT column_name, data_type
                                FROM information_schema.columns
                                WHERE table_schema = '{db_schema}' 
                                AND table_name = '{table_name}'
                                AND (
                                    column_name LIKE '%id' 
                                    OR column_name LIKE '%_id'
                                    OR column_name LIKE '%_fk'
                                )
                            ),
                            potential_references AS (
                                SELECT DISTINCT
                                    sc.column_name as source_column,
                                    sc.data_type as source_type,
                                    t.table_name as target_table,
                                    c.column_name as target_column,
                                    c.data_type as target_type,
                                    CASE
                                        WHEN sc.column_name = t.table_name || '_id' 
                                            AND sc.data_type = c.data_type THEN 2
                                        WHEN sc.column_name LIKE '%_id' 
                                            AND sc.data_type = c.data_type THEN 3
                                        WHEN sc.column_name LIKE '%' || t.table_name || '%'
                                            AND sc.data_type = c.data_type THEN 4
                                        WHEN sc.column_name LIKE '%id'
                                            AND sc.data_type = c.data_type THEN 5
                                    END as confidence_level
                                FROM source_columns sc
                                CROSS JOIN information_schema.tables t
                                JOIN information_schema.columns c 
                                    ON c.table_schema = t.table_schema 
                                    AND c.table_name = t.table_name
                                    AND (c.column_name = 'id' OR c.column_name = sc.column_name)
                                WHERE t.table_schema = '{db_schema}'
                                    AND t.table_name != '{table_name}'
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
                            ORDER BY confidence_level, source_column
                            """
                            implied_results = db_manager.execute_query(implied_sql, database)
                            
                            result = f"Explicit Relationships:\\n{explicit_results}\\n\\nImplied Relationships:\\n{implied_results}"
                        except Exception as e:
                            result = f"Error finding relationships: {str(e)}"
                    else:
                        result = "Error: table_name parameter is required"
                else:
                    result = f"Unknown tool: {tool_name}"
                
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": str(result)
                            }
                        ]
                    }
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32603,
                        "message": f"Tool execution error: {str(e)}"
                    }
                }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
        
        return response
        
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}")
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

async def main():
    """Run the SSE server."""
    host = "localhost"
    port = 8000
    
    logger.info(f"Starting PostgreSQL SSE MCP Server on {host}:{port}")
    logger.info(f"Available databases: {len(db_manager.connections)}")
    logger.info(f"SSE endpoint: http://{host}:{port}/sse")
    logger.info(f"MCP endpoint: http://{host}:{port}/mcp")
    
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

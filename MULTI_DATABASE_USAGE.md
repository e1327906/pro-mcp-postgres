# Multi-Database PostgreSQL MCP Server Usage Examples

## Protocol Support

### STDIO Protocol (Default - for MCP clients)
```bash
# Single database with stdio
python postgres_server.py --protocol stdio

# Multi-database with stdio (Claude Desktop, etc.)
python postgres_server.py --protocol stdio
```

### SSE Protocol (for web interfaces)
```bash
# Start SSE server
python postgres_server.py --protocol sse

# Custom host and port
python postgres_server.py --protocol sse --host 0.0.0.0 --port 8080

# Visit http://localhost:8000 to interact with the server
```

## Database Configuration Examples

### Example 1: Single Database (Backwards Compatible)
```bash
# Your existing setup still works
export POSTGRES_CONNECTION_STRING="postgresql://ab_own:W4bL8xP2r7Tz@localhost:5432/afcdb_ab"
python postgres_server.py
```

### Example 2: Multiple Databases - Comma Separated
```bash
# Multiple databases in .env file
POSTGRES_CONNECTION_STRING=postgresql://ab_own:W4bL8xP2r7Tz@localhost:5432/afcdb_ab,postgresql://user2:pass2@host2:5432/db2,postgresql://user3:pass3@host3:5432/db3
```

### Example 3: Named Database Connections
```bash
# In .env file
POSTGRES_DB_PRODUCTION=postgresql://prod_user:prod_pass@prod-host:5432/prod_db
POSTGRES_DB_STAGING=postgresql://staging_user:staging_pass@staging-host:5432/staging_db
POSTGRES_DB_DEVELOPMENT=postgresql://dev_user:dev_pass@localhost:5432/dev_db
```

### Example 4: Combined Approach
```bash
# Mix both approaches in .env file
POSTGRES_CONNECTION_STRING=postgresql://ab_own:W4bL8xP2r7Tz@localhost:5432/afcdb_ab
POSTGRES_DB_BACKUP=postgresql://backup_user:backup_pass@backup-host:5432/backup_db
POSTGRES_DB_ANALYTICS=postgresql://analytics_user:analytics_pass@analytics-host:5432/analytics_db
```

## Protocol-Specific Usage

### For MCP Clients (STDIO)
```bash
# Start server for Claude Desktop
python postgres_server.py --protocol stdio

# Or simply (stdio is default)
python postgres_server.py
```

### For Web Applications (SSE)
```bash
# Start SSE server
python postgres_server.py --protocol sse --host localhost --port 8000

# Then visit: http://localhost:8000
# Or integrate with web applications using HTTP requests
```

## New Tools Available

### Database Management
- `list_databases()` - Shows all configured database connections
- `switch_database("production")` - Switch to production database
- `get_current_database()` - Shows current database
- `add_database_connection("test", "postgresql://...")` - Add new database
- `remove_database_connection("test")` - Remove database

### Database Operations with Database Parameter
- `query("SELECT * FROM users", database="production")` - Run query on specific database
- `list_tables(database="staging")` - List tables in staging database
- `describe_table("users", database="development")` - Describe table in development database

## Usage Flow
1. **Start server**: 
   - STDIO: `python postgres_server.py --protocol stdio`
   - SSE: `python postgres_server.py --protocol sse`
2. **Check available databases**: `list_databases()`
3. **Switch to desired database**: `switch_database("production")`
4. **Run queries**: `query("SELECT * FROM users")`
5. **Or run queries on specific database**: `query("SELECT * FROM users", database="staging")`
5. Or run queries on specific database: `query("SELECT * FROM users", database="staging")`

# PostgreSQL Multi-Database MCP Server

[![smithery badge](https://smithery.ai/badge/@gldc/mcp-postgres)](https://smithery.ai/server/@gldc/mcp-postgres)

<a href="https://glama.ai/mcp/servers/@gldc/mcp-postgres">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@gldc/mcp-postgres/badge" />
</a>

A PostgreSQL MCP server implementation using the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) Python SDK- an open protocol that enables seamless integration between LLM applications and external data sources. This server allows AI agents to interact with multiple PostgreSQL databases through a standardized interface.

## Features

- **Multi-database support**: Connect to multiple PostgreSQL databases simultaneously
- **Dynamic database switching**: Switch between databases during conversation
- **Database management**: Add/remove database connections at runtime
- List database schemas across different databases
- List tables within schemas
- Describe table structures
- List table constraints and relationships
- Get foreign key information
- Execute SQL queries on specific databases
- Find explicit and implied table relationships

## Multi-Database Configuration

The server supports multiple methods for configuring database connections:

### Method 1: Comma-separated connections in .env
```bash
# Multiple databases in one line (comma-separated)
POSTGRES_CONNECTION_STRING=postgresql://user1:pass1@host1:5432/db1,postgresql://user2:pass2@host2:5432/db2
```

### Method 2: Named database connections
```bash
# Individual named database connections
POSTGRES_DB_PRODUCTION=postgresql://prod_user:prod_pass@prod-host:5432/prod_db
POSTGRES_DB_STAGING=postgresql://staging_user:staging_pass@staging-host:5432/staging_db
POSTGRES_DB_DEVELOPMENT=postgresql://dev_user:dev_pass@localhost:5432/dev_db
```

### Method 3: Combined approach
```bash
# Mix both approaches
POSTGRES_CONNECTION_STRING=postgresql://primary_user:primary_pass@primary-host:5432/primary_db
POSTGRES_DB_BACKUP=postgresql://backup_user:backup_pass@backup-host:5432/backup_db
```

## Available Tools

### Database Management
- `list_databases()` - List all configured database connections
- `switch_database(db_name)` - Switch to a different database
- `get_current_database()` - Get the currently selected database
- `add_database_connection(name, connection_string)` - Add a new database connection
- `remove_database_connection(name)` - Remove a database connection

### Database Operations
All database operation tools now accept an optional `database` parameter:
- `query(sql, parameters=None, database=None)` - Execute SQL query
- `list_schemas(database=None)` - List schemas
- `list_tables(db_schema='public', database=None)` - List tables
- `describe_table(table_name, db_schema='public', database=None)` - Describe table
- `get_foreign_keys(table_name, db_schema='public', database=None)` - Get foreign keys
- `find_relationships(table_name, db_schema='public', database=None)` - Find relationships

## Quick Start

## Quick Start

```bash
# Single database (original format still supported)
python postgres_server.py

# Multi-database setup with .env file (recommended)
cp .env.example .env
# Edit .env file with your database credentials
python postgres_server.py

# Single database with environment variable
export POSTGRES_CONNECTION_STRING="postgresql://user:pass@host:5432/db"
python postgres_server.py

# Single database with command line argument
python postgres_server.py --conn "postgresql://user:pass@host:5432/db"

# Multi-database with environment variables
export POSTGRES_CONNECTION_STRING="postgresql://user1:pass1@host1:5432/db1,postgresql://user2:pass2@host2:5432/db2"
export POSTGRES_DB_PRODUCTION="postgresql://prod_user:prod_pass@prod-host:5432/prod_db"
python postgres_server.py

# Or using Docker (build once, then run):
# docker build -t mcp-postgres . && docker run -p 8000:8000 mcp-postgres
```

## Installation

### Installing via Smithery

To install PostgreSQL MCP Server for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@gldc/mcp-postgres):

```bash
npx -y @smithery/cli install @gldc/mcp-postgres --client claude
```

### Manual Installation
1. Clone this repository:
```bash
git clone <repository-url>
cd mcp-postgres
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your database connections:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your PostgreSQL credentials
# For single database:
# POSTGRES_CONNECTION_STRING=postgresql://username:password@host:port/database

# For multiple databases (comma-separated):
# POSTGRES_CONNECTION_STRING=postgresql://user1:pass1@host1:5432/db1,postgresql://user2:pass2@host2:5432/db2

# For named databases:
# POSTGRES_DB_PRODUCTION=postgresql://prod_user:prod_pass@prod-host:5432/prod_db
# POSTGRES_DB_STAGING=postgresql://staging_user:staging_pass@staging-host:5432/staging_db
```

## Usage

### Starting the Server

1. Start the MCP server:
   ```bash
   # Start with configured databases from .env
   python postgres_server.py

   # Or use command line (single database)
   python postgres_server.py --conn "postgresql://username:password@host:port/database"
   ```

### Multi-Database Operations

1. **List available databases:**
   ```bash
   # Use the list_databases() tool
   ```

2. **Switch between databases:**
   ```bash
   # Use switch_database("database_name") tool
   ```

3. **Query specific databases:**
   ```bash
   # Use query("SELECT * FROM users", database="production") tool
   ```

4. **Add databases at runtime:**
   ```bash
   # Use add_database_connection("new_db", "postgresql://...") tool
   ```

### Legacy Single Database Usage

The server maintains full backwards compatibility:

   # Method 3: Pass it using the --conn flag:
   python postgres_server.py --conn "postgresql://username:password@host:port/database"
   ```
2. The server provides the following tools:

- `query`: Execute SQL queries against the database
- `list_schemas`: List all available schemas
- `list_tables`: List all tables in a specific schema
- `describe_table`: Get detailed information about a table's structure
- `get_foreign_keys`: Get foreign key relationships for a table
- `find_relationships`: Discover both explicit and implied relationships for a table

### Connection String Priority

The server looks for the PostgreSQL connection string in the following order:
1. Command line argument (`--conn`)
2. Environment variable (`POSTGRES_CONNECTION_STRING`)
3. `.env` file (`POSTGRES_CONNECTION_STRING`)

If none of these are provided, the server will start but database operations will return a friendly error message.

### Running with Docker

Build the image:

```bash
docker build -t mcp-postgres .
```

Run the container without a database connection (the server stays inspectable):

```bash
docker run -p 8000:8000 mcp-postgres
```

Run with a live PostgreSQL database by supplying `POSTGRES_CONNECTION_STRING`:

```bash
docker run \
  -e POSTGRES_CONNECTION_STRING="postgresql://username:password@host:5432/database" \
  -p 8000:8000 \
  mcp-postgres
```

*If the environment variable is omitted, the server boots normally and all database‑backed tools return a friendly “connection string is not set” message until you provide it.*

### Configuration with MCP-Compatible Tools

#### Visual Studio Code

To integrate this server with Visual Studio Code, add it to your `~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json` (Linux/macOS) or `%APPDATA%\Code\User\globalStorage\rooveterinaryinc.roo-cline\settings\cline_mcp_settings.json` (Windows):

```json
{
  "mcpServers": {
    "postgres": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "/path/to/postgres_server.py"
      ],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://username:password@host:5432/database?ssl=true"
      }
    }
  }
}
```

Alternatively, you can use the VS Code settings.json approach if using a different MCP extension:

```json
{
  "mcp.servers": {
    "postgres": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "/path/to/postgres_server.py"
      ],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://username:password@host:5432/database?ssl=true"
      }
    }
  }
}
```

#### Cursor

To integrate this server with Cursor, add it to your `~/.cursor/mcp.json`:

```json
{
  "servers": {
    "postgres": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "/path/to/postgres_server.py"
      ],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://username:password@host:5432/database?ssl=true"
      }
    }
  }
}
```

#### Claude Desktop

For Claude Desktop, add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "/path/to/postgres_server.py"
      ],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://username:password@host:5432/database?ssl=true"
      }
    }
  }
}
```

**Configuration Notes:**
- *If `POSTGRES_CONNECTION_STRING` is omitted, the server still starts and is fully inspectable; database‑backed tools will simply return an informative error until the variable is provided.*
- Replace `/path/to/venv` with your virtual environment path
- Replace `/path/to/postgres_server.py` with the absolute path to the server script
- On Windows, use backslashes in paths or forward slashes (both work)

## Security

- **Never commit your `.env` file to version control** - it contains sensitive credentials
- Use the provided `.env.example` as a template and copy it to `.env` for local development
- Never expose sensitive database credentials in your code
- Use environment variables or secure configuration files for database connection strings
- Consider using connection pooling for better resource management
- Implement proper access controls and user authentication

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Related Projects

- [MCP Specification](https://github.com/modelcontextprotocol/specification)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Servers](https://github.com/modelcontextprotocol/servers)

## License

MIT License

Copyright (c) 2025 gldc

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
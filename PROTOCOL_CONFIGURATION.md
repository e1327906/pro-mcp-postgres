# MCP Configuration Examples

## For Claude Desktop (STDIO Protocol)
Add to your `mcp.json`:
```json
{
  "servers": {
    "postgres": {
      "command": "python",
      "args": [
        "D:/Projects/AI/pro-mcp-postgres/postgres_server.py"
      ],
      "type": "stdio"
    }
  }
}
```

## For SSE Protocol (Web/HTTP clients)
Add to your `mcp.json`:
```json
{
  "servers": {
    "postgres-sse": {
      "command": "python",
      "args": [
        "D:/Projects/AI/pro-mcp-postgres/postgres_server.py",
        "--protocol",
        "sse",
        "--host",
        "localhost",
        "--port",
        "8000"
      ],
      "type": "sse"
    }
  }
}
```

## Installation for SSE Support
```bash
pip install uvicorn fastapi
```

## Command Line Usage

### STDIO Mode (Default)
```bash
# Default stdio mode
python postgres_server.py

# Explicit stdio mode
python postgres_server.py --protocol stdio
```

### SSE Mode
```bash
# SSE mode with defaults (localhost:8000)
python postgres_server.py --protocol sse

# SSE mode with custom host/port
python postgres_server.py --protocol sse --host 0.0.0.0 --port 8080
```

### Combined with Database Configuration
```bash
# SSE mode with database connection
python postgres_server.py --protocol sse --conn "postgresql://user:pass@host:5432/db"

# STDIO mode with multiple databases (from .env)
python postgres_server.py --protocol stdio
```

## Access Methods

### STDIO Protocol
- **For**: MCP clients like Claude Desktop
- **Access**: Through MCP client interface
- **Configuration**: Via `mcp.json` in client

### SSE Protocol  
- **For**: Web applications, HTTP clients, testing
- **Access**: HTTP requests to `http://localhost:8000`
- **Configuration**: Direct server startup with uvicorn

## Testing the Server

### Test STDIO Mode
```bash
python postgres_server.py --protocol stdio
# Server will wait for MCP client connections
```

### Test SSE Mode
```bash
python postgres_server.py --protocol sse
# Visit http://localhost:8000 in browser
# Server runs with uvicorn for HTTP access
```

# Linear MCP Server

A Model Context Protocol (MCP) server that integrates with Linear's project management platform, enabling MCP clients like Claude Desktop and Cursor to create work items from feature lists and search across Linear resources.

## Features

- **Feature List Conversion**: Convert feature lists from various formats (plain text, markdown, JSON) into Linear issues
- **Comprehensive Search**: Search across Linear issues, projects, teams, and more with advanced filtering
- **MCP Protocol Support**: Full implementation of the Model Context Protocol
- **Secure Authentication**: API key-based authentication with Linear

## Requirements

- Python 3.9+
- Linear API key (get from your Linear account settings)
- Claude Desktop or other MCP-compatible client

## Quick Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/username/linear-mcp-server.git
   cd linear-mcp-server
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up your Linear API key:
   - Copy the `.env.example` file:
     ```bash
     cp config/.env.example .env
     ```
   - Edit `.env` and add your Linear API key:
     ```
     LINEAR_MCP_LINEAR_API_KEY=your_linear_api_key_here
     ```

4. Start the server:
   ```bash
   python -m src.main --env-file .env
   ```

The server will start on http://127.0.0.1:8000 by default.

## Configuring Claude Desktop

To connect Claude Desktop to your local Linear MCP server:

1. Open Claude Desktop
2. Go to Settings (gear icon)
3. Navigate to "Tools" or "MCP Tools" section
4. Click "Add Custom MCP Tool"
5. Enter the following details:
   - Name: Linear MCP
   - Description: Linear project management integration
   - Base URL: http://127.0.0.1:8000
   - Tool Type: MCP
   - Authentication: None (the server handles Linear authentication)
6. Click "Save" or "Add Tool"

Now you can access Linear functionality through Claude Desktop by using the Linear MCP tool.

## Advanced Configuration

For advanced configuration, copy and edit the configuration file:

```bash
cp config/config.yaml config/config.local.yaml
# Edit config.local.yaml with your settings
```

Then start the server with:

```bash
python -m src.main --config config/config.local.yaml
```

### Configuration Options

The following configuration options are available:

**Linear API Settings**:
- `linear.api_key`: Your Linear API key
- `linear.api_url`: Linear API URL (default: https://api.linear.app/graphql)
- `linear.timeout`: API request timeout in seconds (default: 30)

**Server Settings**:
- `server.host`: Server host address (default: 127.0.0.1)
- `server.port`: Server port (default: 8000)
- `server.cors_origins`: CORS allowed origins (default: ["*"])

**Logging Settings**:
- `logging.level`: Logging level (default: INFO)
- `logging.log_file`: Log file path

You can also set these options using environment variables. See `.env.example` for examples.

## Development

### Testing

Run tests:

```bash
pytest
```

With coverage:

```bash
pytest --cov=src
```

### Linting and Formatting

Format code:

```bash
black src tests
isort src tests
```

Check code quality:

```bash
flake8 src tests
mypy src tests
```

## Usage with Claude

Once set up, you can use commands like:

1. Create issues from a feature list:
   ```
   Can you create Linear issues from this feature list: 
   - Add dark mode support
   - Fix login bug on Safari
   - Improve performance on mobile devices
   ```

2. Search for issues:
   ```
   Find all open issues related to performance in our Linear project
   ```

3. Get project information:
   ```
   What's the status of the Q2 Roadmap project in Linear?
   ```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
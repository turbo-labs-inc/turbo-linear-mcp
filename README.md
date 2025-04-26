# Linear MCP Server

A Model Context Protocol (MCP) server that integrates with Linear's project management platform, enabling MCP clients like Claude Desktop and Cursor to create work items from feature lists and search across Linear resources.

## Features

- **Feature List Conversion**: Convert feature lists from various formats (plain text, markdown, JSON) into Linear issues
- **Comprehensive Search**: Search across Linear issues, projects, teams, and more with advanced filtering
- **MCP Protocol Support**: Full implementation of the Model Context Protocol
- **Secure Authentication**: API key-based authentication with Linear

## Requirements

- Python 3.9+
- Linear API access

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/username/linear-mcp-server.git
   cd linear-mcp-server
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   pip install -e ".[dev]"  # Install with development dependencies
   ```

3. Configure the server:
   ```bash
   cp config/config.example.yaml config/config.yaml
   # Edit config.yaml with your settings
   ```

## Usage

Start the server:

```bash
python -m src.main --config config/config.yaml
```

Or with custom log level:

```bash
python -m src.main --config config/config.yaml --log-level DEBUG
```

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

## Documentation

Build documentation:

```bash
cd docs
make html
```

View the documentation at `docs/_build/html/index.html`.

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome\! Please feel free to submit a Pull Request.
EOF < /dev/null
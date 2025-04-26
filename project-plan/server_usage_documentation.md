# Linear MCP Server Usage Documentation

## Overview

This document provides comprehensive usage instructions for the Linear MCP Server, which enables MCP clients like Claude Desktop and Cursor to interact with Linear's project management platform. The server implements the Model Context Protocol (MCP) to provide a standardized interface for creating work items from feature lists and searching for issues, projects, documents, templates, and other resources in Linear.

## Getting Started

### Prerequisites

Before using the Linear MCP Server, ensure you have:

1. A Linear account with API access
2. An API key from Linear (or OAuth credentials if using OAuth authentication)
3. An MCP client (such as Claude Desktop or Cursor)

### Installation

#### Using Docker (Recommended)

The simplest way to run the Linear MCP Server is using Docker:

```bash
# Pull the image
docker pull linearapp/mcp-server:latest

# Run the server with API key authentication
docker run -p 8080:8080 \
  -e LINEAR_API_KEY=your_linear_api_key \
  linearapp/mcp-server:latest
```

#### Manual Installation

For manual installation:

1. Clone the repository:
   ```bash
   git clone https://github.com/linearapp/mcp-server.git
   cd mcp-server
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a configuration file (see Configuration section)

4. Run the server:
   ```bash
   python src/main.py --config config/your_config.yaml
   ```

### Configuration

The server can be configured using a YAML file and/or environment variables.

#### Basic Configuration File

Create a file named `config.yaml` with the following minimal configuration:

```yaml
server:
  port: 8080

linear:
  auth:
    method: "api_key"
    # API key provided via LINEAR_API_KEY environment variable

logging:
  level: "info"
```

#### Environment Variables

Key environment variables:

| Variable | Description |
|----------|-------------|
| `LINEAR_API_KEY` | Your Linear API key |
| `LINEAR_MCP_SERVER_PORT` | Port for the MCP server (default: 8080) |
| `LINEAR_MCP_LOG_LEVEL` | Logging level (default: info) |

See the [Server Configuration](server_configuration.md) document for a complete list of configuration options.

## Connecting MCP Clients

### Claude Desktop

To connect Claude Desktop to the Linear MCP Server:

1. Open Claude Desktop
2. Go to Settings > Plugins
3. Click "Add Custom Plugin"
4. Enter the following details:
   - Name: Linear
   - URL: `ws://localhost:8080` (or your server URL)
   - API Key: (leave blank or enter your MCP server API key if configured)
5. Click "Save"

### Cursor

To connect Cursor to the Linear MCP Server:

1. Open Cursor
2. Go to Settings > AI > MCP
3. Click "Add MCP Server"
4. Enter the following details:
   - Name: Linear
   - URL: `ws://localhost:8080` (or your server URL)
   - API Key: (leave blank or enter your MCP server API key if configured)
5. Click "Add"

## Using the Linear MCP Server

Once connected, your MCP client can interact with Linear through the server. The server exposes the following capabilities:

### Resources

Resources allow you to search and retrieve data from Linear.

#### Issues Resource

Search for issues in Linear with various filters:

```
Resource: issues
Parameters:
  - query: Text to search for in issue title and description
  - teamIds: IDs of teams to filter issues by
  - projectIds: IDs of projects to filter issues by
  - stateIds: IDs of states to filter issues by
  - assigneeIds: IDs of users to filter issues by assignee
  - labelIds: IDs of labels to filter issues by
  - priority: Priority values to filter issues by
  - createdAfter: Filter issues created after this date
  - createdBefore: Filter issues created before this date
  - updatedAfter: Filter issues updated after this date
  - updatedBefore: Filter issues updated before this date
  - includeArchived: Whether to include archived issues
  - sortBy: Field to sort results by
  - sortOrder: Sort order (asc or desc)
  - limit: Maximum number of results to return
  - offset: Offset for pagination
```

Example usage in Claude Desktop:

```
Find all high priority issues in the Frontend team that are assigned to me.
```

#### Projects Resource

Search for projects in Linear:

```
Resource: projects
Parameters:
  - query: Text to search for in project name and description
  - teamIds: IDs of teams to filter projects by
  - states: Project states to filter by
  - includeArchived: Whether to include archived projects
  - sortBy: Field to sort results by
  - sortOrder: Sort order (asc or desc)
  - limit: Maximum number of results to return
  - offset: Offset for pagination
```

Example usage in Claude Desktop:

```
Show me all active projects in the Backend team.
```

#### Unified Search

Search across multiple resource types:

```
Resource: search
Parameters:
  - query: Text to search for across all resources
  - resourceTypes: Types of resources to include in search results
  - teamIds: IDs of teams to filter results by
  - includeArchived: Whether to include archived resources
  - limit: Maximum number of results to return per resource type
```

Example usage in Claude Desktop:

```
Search for "authentication" across all Linear resources.
```

### Tools

Tools allow you to perform actions in Linear.

#### Create Work Items from Feature List

Create Linear issues from a feature list:

```
Tool: createWorkItemsFromFeatureList
Parameters:
  - featureList: Feature list in plain text, markdown, or JSON format
  - projectId: ID of the Linear project to create issues in (optional)
  - teamId: ID of the Linear team to create issues in (optional)
  - labelIds: IDs of labels to apply to all created issues (optional)
  - stateId: ID of the state to set for created issues (optional)
  - assigneeId: ID of the user to assign issues to (optional)
  - parentIssueId: ID of a parent issue to link created issues to (optional)
  - format: Format of the feature list (defaults to auto-detect)
```

Example usage in Claude Desktop:

```
Create work items in Linear for the following features:

# New Authentication System
- Add Google OAuth support
- Implement two-factor authentication
- Create password reset flow
- Add session management

Please create these in the Authentication project.
```

## Feature List Formats

The server supports multiple formats for feature lists:

### Plain Text Format

Simple line-by-line feature descriptions:

```
Add user authentication
Implement dashboard analytics
Create export functionality for reports
Add dark mode support
```

### Markdown Format

Features with optional descriptions and metadata:

```markdown
# Feature List

## Add user authentication
- Priority: High
- Description: Implement OAuth2 authentication with support for Google and GitHub providers

## Implement dashboard analytics
- Priority: Medium
- Description: Create analytics dashboard with charts for key metrics

## Create export functionality for reports
- Formats: PDF, CSV, Excel
- Priority: Low

## Add dark mode support
- Description: Implement system-wide dark mode with automatic detection of system preferences
```

### JSON Format

Fully structured feature data:

```json
{
  "features": [
    {
      "title": "Add user authentication",
      "description": "Implement OAuth2 authentication with support for Google and GitHub providers",
      "priority": "High",
      "labels": ["authentication", "security"]
    },
    {
      "title": "Implement dashboard analytics",
      "description": "Create analytics dashboard with charts for key metrics",
      "priority": "Medium",
      "labels": ["analytics", "frontend"]
    },
    {
      "title": "Create export functionality for reports",
      "description": "Add ability to export reports in multiple formats",
      "priority": "Low",
      "metadata": {
        "formats": ["PDF", "CSV", "Excel"]
      }
    },
    {
      "title": "Add dark mode support",
      "description": "Implement system-wide dark mode with automatic detection of system preferences",
      "labels": ["ui", "enhancement"]
    }
  ],
  "metadata": {
    "project": "Website Redesign",
    "team": "Frontend Team",
    "milestone": "Q2 Release"
  }
}
```

## Common Workflows

### Creating Issues from a Feature List

1. In your MCP client, describe the features you want to create
2. Optionally specify the project, team, labels, or other metadata
3. The server will create the issues in Linear and return the results

Example in Claude Desktop:

```
Create the following features in the "Website Redesign" project:

1. Implement responsive design for mobile devices
2. Add dark mode support
3. Optimize image loading for better performance
4. Create new contact form with validation
```

### Searching for Issues

1. In your MCP client, describe what you're looking for
2. Optionally specify filters like team, project, state, or assignee
3. The server will search Linear and return the matching issues

Example in Claude Desktop:

```
Find all high priority bugs assigned to John in the Frontend project.
```

### Finding Project Information

1. In your MCP client, ask about a specific project
2. The server will search for the project and return its details

Example in Claude Desktop:

```
Show me the status and timeline of the Authentication project.
```

## Troubleshooting

### Connection Issues

If you're having trouble connecting to the server:

1. Verify the server is running (`docker ps` or check process)
2. Ensure the port is accessible (try `curl http://localhost:8080/health`)
3. Check firewall settings if connecting remotely
4. Verify the WebSocket URL is correct in your MCP client

### Authentication Issues

If you're experiencing authentication problems:

1. Verify your Linear API key is correct
2. Check the server logs for authentication errors
3. Ensure your Linear account has the necessary permissions
4. Try regenerating your API key in Linear

### Feature List Processing Issues

If feature lists aren't being processed correctly:

1. Check the format of your feature list
2. Ensure you're providing required metadata (team ID, project ID, etc.)
3. Verify the server logs for parsing errors
4. Try simplifying the feature list format

## Advanced Configuration

### SSL/TLS Configuration

For secure WebSocket connections (WSS):

```yaml
security:
  ssl:
    enabled: true
    cert_file: "/path/to/cert.pem"
    key_file: "/path/to/key.pem"
```

### Rate Limiting

Configure rate limiting to prevent abuse:

```yaml
mcp:
  tools:
    rate_limit:
      enabled: true
      max_per_minute: 60
```

### Caching

Configure caching for better performance:

```yaml
linear:
  search:
    cache_results: true
    cache_ttl: 60  # seconds
```

## API Reference

For detailed API reference, see the [API Documentation](api_documentation.md).

## Security Considerations

### API Key Protection

Your Linear API key provides access to your Linear account. Protect it by:

1. Using environment variables instead of configuration files
2. Restricting access to the server
3. Using HTTPS/WSS for all communications
4. Implementing MCP server authentication if exposed publicly

### Access Control

The server respects Linear's permission model. Users will only be able to access resources and perform actions that their Linear API key allows.

## Performance Optimization

For optimal performance:

1. Enable caching for search results
2. Use specific filters when searching to reduce result set size
3. Batch create issues when possible
4. Increase connection timeout for large operations

## Conclusion

The Linear MCP Server provides a powerful interface between MCP clients and Linear, enabling seamless creation of work items from feature lists and comprehensive search capabilities. By following this documentation, you can effectively set up and use the server to enhance your workflow with Linear.

For more information, refer to the following resources:

- [Server Configuration](server_configuration.md)
- [API Documentation](api_documentation.md)
- [Implementation Blueprint](implementation_blueprint.md)
- [Error Handling and Logging](error_handling_logging.md)

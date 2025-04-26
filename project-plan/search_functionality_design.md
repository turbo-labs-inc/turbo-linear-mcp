# Search Functionality Design for Linear MCP Server

## Overview
This document outlines the design for the search functionality in the Linear MCP server. The search capabilities will allow MCP clients to search for issues, projects, documents, templates, and other resources in Linear through a standardized interface.

## Search Capabilities

### Searchable Resources
The search functionality will support the following Linear resources:

1. **Issues**
   - Search by title, description, ID, and other fields
   - Filter by status, assignee, project, team, labels, etc.
   - Sort by various criteria (created date, updated date, priority, etc.)

2. **Projects**
   - Search by name, description, and other fields
   - Filter by status, team, etc.

3. **Teams**
   - Search by name and description

4. **Documents**
   - Search by title and content

5. **Templates**
   - Search by name and description

6. **Users**
   - Search by name and email

7. **Labels**
   - Search by name

### Search Parameters
The search functionality will support a rich set of parameters:

1. **Text Search**
   - Full-text search across specified fields
   - Support for exact phrases and keyword matching
   - Case-insensitive by default

2. **Field-Specific Filters**
   - Filter by specific field values
   - Support for multiple filter conditions
   - Logical operators (AND, OR, NOT)

3. **Relationship Filters**
   - Filter by related entities (e.g., issues in a specific project)
   - Nested relationship filtering

4. **Date Range Filters**
   - Filter by creation date, update date, etc.
   - Support for relative dates (e.g., "last 7 days")

5. **State Filters**
   - Filter by workflow state
   - Include/exclude archived items

6. **Pagination**
   - Control result set size
   - Navigate through large result sets

7. **Sorting**
   - Sort by various fields
   - Ascending or descending order

## MCP Resource Interface

The search functionality will be exposed as MCP resources with the following interfaces:

### 1. Issues Resource

```typescript
interface IssuesResource {
  name: "issues";
  description: "Search for Linear issues";
  parameters: {
    query?: {
      type: "string";
      description: "Text to search for in issue title and description";
    };
    teamIds?: {
      type: "array";
      items: {
        type: "string";
      };
      description: "IDs of teams to filter issues by";
    };
    projectIds?: {
      type: "array";
      items: {
        type: "string";
      };
      description: "IDs of projects to filter issues by";
    };
    stateIds?: {
      type: "array";
      items: {
        type: "string";
      };
      description: "IDs of states to filter issues by";
    };
    assigneeIds?: {
      type: "array";
      items: {
        type: "string";
      };
      description: "IDs of users to filter issues by assignee";
    };
    labelIds?: {
      type: "array";
      items: {
        type: "string";
      };
      description: "IDs of labels to filter issues by";
    };
    priority?: {
      type: "array";
      items: {
        type: "number";
      };
      description: "Priority values to filter issues by";
    };
    createdAfter?: {
      type: "string";
      format: "date-time";
      description: "Filter issues created after this date";
    };
    createdBefore?: {
      type: "string";
      format: "date-time";
      description: "Filter issues created before this date";
    };
    updatedAfter?: {
      type: "string";
      format: "date-time";
      description: "Filter issues updated after this date";
    };
    updatedBefore?: {
      type: "string";
      format: "date-time";
      description: "Filter issues updated before this date";
    };
    includeArchived?: {
      type: "boolean";
      description: "Whether to include archived issues";
      default: false;
    };
    sortBy?: {
      type: "string";
      enum: ["createdAt", "updatedAt", "priority", "dueDate", "title"];
      description: "Field to sort results by";
      default: "updatedAt";
    };
    sortOrder?: {
      type: "string";
      enum: ["asc", "desc"];
      description: "Sort order";
      default: "desc";
    };
    limit?: {
      type: "number";
      description: "Maximum number of results to return";
      default: 25;
      maximum: 100;
    };
    offset?: {
      type: "number";
      description: "Offset for pagination";
      default: 0;
    };
  };
  returns: {
    type: "object";
    properties: {
      issues: {
        type: "array";
        items: {
          type: "object";
          properties: {
            id: {
              type: "string";
              description: "Issue ID";
            };
            title: {
              type: "string";
              description: "Issue title";
            };
            description: {
              type: "string";
              description: "Issue description";
            };
            state: {
              type: "object";
              properties: {
                id: {
                  type: "string";
                  description: "State ID";
                };
                name: {
                  type: "string";
                  description: "State name";
                };
                type: {
                  type: "string";
                  description: "State type";
                };
              };
            };
            assignee: {
              type: "object";
              properties: {
                id: {
                  type: "string";
                  description: "User ID";
                };
                name: {
                  type: "string";
                  description: "User name";
                };
                email: {
                  type: "string";
                  description: "User email";
                };
              };
            };
            project: {
              type: "object";
              properties: {
                id: {
                  type: "string";
                  description: "Project ID";
                };
                name: {
                  type: "string";
                  description: "Project name";
                };
              };
            };
            team: {
              type: "object";
              properties: {
                id: {
                  type: "string";
                  description: "Team ID";
                };
                name: {
                  type: "string";
                  description: "Team name";
                };
              };
            };
            labels: {
              type: "array";
              items: {
                type: "object";
                properties: {
                  id: {
                    type: "string";
                    description: "Label ID";
                  };
                  name: {
                    type: "string";
                    description: "Label name";
                  };
                  color: {
                    type: "string";
                    description: "Label color";
                  };
                };
              };
            };
            priority: {
              type: "number";
              description: "Issue priority";
            };
            createdAt: {
              type: "string";
              format: "date-time";
              description: "Creation timestamp";
            };
            updatedAt: {
              type: "string";
              format: "date-time";
              description: "Last update timestamp";
            };
            url: {
              type: "string";
              description: "URL to access the issue in Linear";
            };
          };
        };
      };
      totalCount: {
        type: "number";
        description: "Total number of issues matching the query";
      };
      pageInfo: {
        type: "object";
        properties: {
          hasNextPage: {
            type: "boolean";
            description: "Whether there are more results available";
          };
          endCursor: {
            type: "string";
            description: "Cursor for pagination";
          };
        };
      };
    };
  };
}
```

### 2. Projects Resource

```typescript
interface ProjectsResource {
  name: "projects";
  description: "Search for Linear projects";
  parameters: {
    query?: {
      type: "string";
      description: "Text to search for in project name and description";
    };
    teamIds?: {
      type: "array";
      items: {
        type: "string";
      };
      description: "IDs of teams to filter projects by";
    };
    states?: {
      type: "array";
      items: {
        type: "string";
        enum: ["planned", "started", "paused", "completed", "canceled"];
      };
      description: "Project states to filter by";
    };
    includeArchived?: {
      type: "boolean";
      description: "Whether to include archived projects";
      default: false;
    };
    sortBy?: {
      type: "string";
      enum: ["createdAt", "updatedAt", "name", "startDate", "targetDate"];
      description: "Field to sort results by";
      default: "updatedAt";
    };
    sortOrder?: {
      type: "string";
      enum: ["asc", "desc"];
      description: "Sort order";
      default: "desc";
    };
    limit?: {
      type: "number";
      description: "Maximum number of results to return";
      default: 25;
      maximum: 100;
    };
    offset?: {
      type: "number";
      description: "Offset for pagination";
      default: 0;
    };
  };
  returns: {
    type: "object";
    properties: {
      projects: {
        type: "array";
        items: {
          type: "object";
          properties: {
            id: {
              type: "string";
              description: "Project ID";
            };
            name: {
              type: "string";
              description: "Project name";
            };
            description: {
              type: "string";
              description: "Project description";
            };
            state: {
              type: "string";
              description: "Project state";
            };
            team: {
              type: "object";
              properties: {
                id: {
                  type: "string";
                  description: "Team ID";
                };
                name: {
                  type: "string";
                  description: "Team name";
                };
              };
            };
            createdAt: {
              type: "string";
              format: "date-time";
              description: "Creation timestamp";
            };
            updatedAt: {
              type: "string";
              format: "date-time";
              description: "Last update timestamp";
            };
            startDate: {
              type: "string";
              format: "date";
              description: "Project start date";
            };
            targetDate: {
              type: "string";
              format: "date";
              description: "Project target completion date";
            };
            url: {
              type: "string";
              description: "URL to access the project in Linear";
            };
          };
        };
      };
      totalCount: {
        type: "number";
        description: "Total number of projects matching the query";
      };
      pageInfo: {
        type: "object";
        properties: {
          hasNextPage: {
            type: "boolean";
            description: "Whether there are more results available";
          };
          endCursor: {
            type: "string";
            description: "Cursor for pagination";
          };
        };
      };
    };
  };
}
```

### 3. Search Resource (Unified Search)

```typescript
interface SearchResource {
  name: "search";
  description: "Unified search across Linear resources";
  parameters: {
    query: {
      type: "string";
      description: "Text to search for across all resources";
    };
    resourceTypes?: {
      type: "array";
      items: {
        type: "string";
        enum: ["issues", "projects", "teams", "documents", "templates", "users", "labels"];
      };
      description: "Types of resources to include in search results";
      default: ["issues", "projects", "documents"];
    };
    teamIds?: {
      type: "array";
      items: {
        type: "string";
      };
      description: "IDs of teams to filter results by";
    };
    includeArchived?: {
      type: "boolean";
      description: "Whether to include archived resources";
      default: false;
    };
    limit?: {
      type: "number";
      description: "Maximum number of results to return per resource type";
      default: 10;
      maximum: 50;
    };
  };
  returns: {
    type: "object";
    properties: {
      issues: {
        type: "array";
        items: {
          type: "object";
          properties: {
            id: {
              type: "string";
              description: "Issue ID";
            };
            title: {
              type: "string";
              description: "Issue title";
            };
            type: {
              type: "string";
              const: "issue";
              description: "Resource type";
            };
            url: {
              type: "string";
              description: "URL to access the resource in Linear";
            };
          };
        };
      };
      projects: {
        type: "array";
        items: {
          type: "object";
          properties: {
            id: {
              type: "string";
              description: "Project ID";
            };
            name: {
              type: "string";
              description: "Project name";
            };
            type: {
              type: "string";
              const: "project";
              description: "Resource type";
            };
            url: {
              type: "string";
              description: "URL to access the resource in Linear";
            };
          };
        };
      };
      documents: {
        type: "array";
        items: {
          type: "object";
          properties: {
            id: {
              type: "string";
              description: "Document ID";
            };
            title: {
              type: "string";
              description: "Document title";
            };
            type: {
              type: "string";
              const: "document";
              description: "Resource type";
            };
            url: {
              type: "string";
              description: "URL to access the resource in Linear";
            };
          };
        };
      };
      // Similar structures for other resource types
    };
  };
}
```

## Search Implementation

### Query Translation
The search functionality will translate MCP resource requests into Linear GraphQL queries:

1. **Parameter Mapping**
   - Map MCP resource parameters to Linear GraphQL query parameters
   - Handle special cases and defaults

2. **Filter Construction**
   - Build Linear filter objects from MCP parameters
   - Implement logical operators (AND, OR, NOT)
   - Handle relationship filters

3. **Query Optimization**
   - Optimize queries for performance
   - Request only necessary fields
   - Use pagination appropriately

### Result Processing
The search functionality will process Linear API responses:

1. **Data Transformation**
   - Map Linear GraphQL response to MCP resource format
   - Handle nested data structures
   - Format dates and other special fields

2. **Pagination Handling**
   - Process Linear pagination information
   - Generate appropriate MCP pagination metadata
   - Support cursor-based and offset-based pagination

3. **Error Handling**
   - Handle Linear API errors
   - Provide meaningful error messages
   - Implement fallback strategies where appropriate

## Performance Considerations

### Caching
The search functionality will implement caching to improve performance:

1. **Result Caching**
   - Cache search results with appropriate TTL
   - Invalidate cache on relevant updates
   - Use cache keys based on search parameters

2. **Metadata Caching**
   - Cache team, project, and other metadata
   - Refresh periodically or on demand
   - Use for query optimization

### Query Optimization
The search functionality will optimize queries:

1. **Field Selection**
   - Request only necessary fields
   - Use fragments for common field sets
   - Avoid over-fetching

2. **Batching**
   - Batch related queries where possible
   - Implement dataloader pattern for efficient data fetching

3. **Pagination**
   - Use appropriate page sizes
   - Implement cursor-based pagination for large result sets
   - Support efficient navigation through results

## Error Handling

The search functionality will handle various error scenarios:

1. **Linear API Errors**
   - Authentication failures
   - Rate limiting
   - Query errors
   - Network issues

2. **Parameter Validation Errors**
   - Invalid parameter values
   - Unsupported filter combinations
   - Pagination limits

3. **Resource Access Errors**
   - Permission issues
   - Resource not found
   - Archived resources

## Implementation Considerations

1. **Extensibility**
   - Design for adding new resource types
   - Support custom filters and sorting
   - Allow for future Linear API changes

2. **Security**
   - Respect Linear permissions
   - Validate and sanitize input
   - Handle sensitive data appropriately

3. **Monitoring**
   - Log search performance metrics
   - Track error rates
   - Monitor cache effectiveness

This design provides a comprehensive approach to implementing search functionality in the Linear MCP server, supporting various resource types and search parameters while ensuring good performance and error handling.

# Feature List to Work Item Conversion Design

## Overview
This document outlines the design for converting feature lists into Linear work items (issues) through the MCP server. This functionality is a core requirement of the server, enabling users to easily create work items from feature lists using MCP clients like Claude Desktop or Cursor.

## Feature List Formats
The system will support multiple input formats for feature lists:

### 1. Plain Text Format
Simple line-by-line feature descriptions:

```
Add user authentication
Implement dashboard analytics
Create export functionality for reports
Add dark mode support
```

### 2. Markdown Format
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

### 3. Structured JSON Format
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

## Conversion Process

### 1. Input Parsing
The feature list processor will:
1. Detect the input format (plain text, markdown, or JSON)
2. Parse the input according to the detected format
3. Extract feature titles, descriptions, and metadata
4. Validate the parsed data for completeness and correctness

### 2. Metadata Extraction and Enrichment
For each feature, the processor will:
1. Extract explicit metadata (priority, labels, etc.)
2. Apply default metadata from configuration if not specified
3. Enrich with additional metadata if configured (e.g., auto-labeling)
4. Validate metadata against Linear API constraints

### 3. Linear Issue Creation
The processor will:
1. Convert each feature to Linear issue format
2. Apply team and project context if specified
3. Set appropriate state, priority, and labels
4. Create issues in Linear via the API
5. Handle batch creation for multiple features
6. Track creation status and results

### 4. Result Processing
The processor will:
1. Collect results from Linear API responses
2. Format results according to MCP protocol
3. Include success/failure status for each feature
4. Provide issue IDs and URLs for created issues
5. Include detailed error information for failures

## MCP Tool Interface

The feature list processor will be exposed as an MCP tool with the following interface:

```typescript
interface CreateWorkItemsFromFeatureListTool {
  name: "createWorkItemsFromFeatureList";
  description: "Creates Linear work items from a feature list";
  parameters: {
    featureList: {
      type: "string";
      description: "Feature list in plain text, markdown, or JSON format";
    };
    projectId?: {
      type: "string";
      description: "ID of the Linear project to create issues in (optional)";
    };
    teamId?: {
      type: "string";
      description: "ID of the Linear team to create issues in (optional)";
    };
    labelIds?: {
      type: "array";
      items: {
        type: "string";
      };
      description: "IDs of labels to apply to all created issues (optional)";
    };
    stateId?: {
      type: "string";
      description: "ID of the state to set for created issues (optional)";
    };
    assigneeId?: {
      type: "string";
      description: "ID of the user to assign issues to (optional)";
    };
    parentIssueId?: {
      type: "string";
      description: "ID of a parent issue to link created issues to (optional)";
    };
    format?: {
      type: "string";
      enum: ["auto", "text", "markdown", "json"];
      description: "Format of the feature list (defaults to auto-detect)";
    };
  };
  returns: {
    type: "object";
    properties: {
      success: {
        type: "boolean";
        description: "Whether the operation was successful overall";
      };
      createdIssues: {
        type: "array";
        items: {
          type: "object";
          properties: {
            id: {
              type: "string";
              description: "ID of the created issue";
            };
            title: {
              type: "string";
              description: "Title of the created issue";
            };
            url: {
              type: "string";
              description: "URL to access the issue in Linear";
            };
          };
        };
        description: "List of successfully created issues";
      };
      failedFeatures: {
        type: "array";
        items: {
          type: "object";
          properties: {
            title: {
              type: "string";
              description: "Title of the feature that failed to create";
            };
            error: {
              type: "string";
              description: "Error message explaining the failure";
            };
          };
        };
        description: "List of features that failed to create";
      };
    };
  };
}
```

## Feature Parsing Logic

### Plain Text Parsing
- Each line is treated as a separate feature title
- Empty lines are ignored
- No additional metadata is extracted

### Markdown Parsing
- Level 1 headings (`#`) are treated as section titles (not features)
- Level 2 headings (`##`) are treated as feature titles
- Lists under a heading are parsed for metadata:
  - Items with `Key: Value` format are treated as metadata
  - Other items contribute to the description
- Features without explicit headings are extracted from lists

### JSON Parsing
- The JSON structure is validated against a schema
- Features are extracted from the `features` array
- Global metadata is extracted from the `metadata` object
- Each feature object is mapped to Linear issue fields

## Metadata Mapping

The following mappings will be applied when converting features to Linear issues:

| Feature Metadata | Linear Issue Field | Notes |
|------------------|-------------------|-------|
| title | title | Required |
| description | description | Markdown supported |
| priority | priority | Mapped to Linear priority values |
| labels | labelIds | Labels are created if they don't exist |
| assignee | assigneeId | User lookup by name if needed |
| state | stateId | Mapped to appropriate workflow state |
| dueDate | dueDate | ISO 8601 format |
| estimate | estimate | Numeric value |

## Error Handling

The feature list processor will handle various error scenarios:

1. **Input Format Errors**
   - Invalid JSON
   - Malformed markdown
   - Empty input

2. **Validation Errors**
   - Missing required fields
   - Invalid field values
   - Unsupported metadata

3. **Linear API Errors**
   - Authentication failures
   - Rate limiting
   - Resource not found (e.g., invalid project ID)
   - Permission issues

4. **Partial Success Handling**
   - Continue processing remaining features if some fail
   - Provide detailed error information for failed features
   - Return both successful and failed results

## Implementation Considerations

1. **Performance Optimization**
   - Batch API requests when possible
   - Parallel processing for large feature lists
   - Caching of Linear metadata (teams, projects, states, etc.)

2. **Extensibility**
   - Plugin architecture for custom format parsers
   - Configurable metadata mapping
   - Hooks for pre/post-processing

3. **User Experience**
   - Clear error messages
   - Helpful suggestions for fixing issues
   - Progress reporting for large feature lists

This design provides a comprehensive approach to converting feature lists into Linear work items, supporting various input formats and providing robust error handling.

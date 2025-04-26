# MCP Client Usage Guide for Linear Integration

## Overview

This guide demonstrates how to use MCP clients like Claude Desktop and Cursor to interact with Linear through the Linear MCP Server. It provides practical examples, prompts, and workflows to help you get the most out of the integration.

## Claude Desktop Examples

### Setting Up the Linear Connection

1. Open Claude Desktop
2. Navigate to Settings > Plugins
3. Click "Add Custom Plugin"
4. Enter the following details:
   - Name: Linear
   - URL: `ws://localhost:8080` (or your server URL)
   - API Key: (leave blank or enter your MCP server API key if configured)
5. Click "Save"

### Creating Work Items from Feature Lists

#### Example 1: Simple Feature List

**Prompt to Claude:**
```
Create the following work items in Linear:

1. Implement user authentication
2. Add dashboard analytics
3. Create export functionality
4. Add dark mode support

Please create these in the Frontend project.
```

**Expected Result:**
Claude will use the Linear MCP Server to create four issues in the Frontend project with the titles as specified.

#### Example 2: Detailed Feature List with Metadata

**Prompt to Claude:**
```
Create the following features in Linear for our Q2 Release:

## User Authentication System
- Priority: High
- Description: Implement OAuth2 authentication with support for Google and GitHub providers
- Labels: security, authentication

## Analytics Dashboard
- Priority: Medium
- Description: Create analytics dashboard with charts for key metrics
- Labels: analytics, frontend

## Report Export Functionality
- Priority: Low
- Description: Add ability to export reports in multiple formats (PDF, CSV, Excel)
- Labels: reporting

## Dark Mode Support
- Description: Implement system-wide dark mode with automatic detection of system preferences
- Labels: ui, enhancement

Please assign these to John and add them to the Website Redesign project.
```

**Expected Result:**
Claude will create four detailed issues with priorities, descriptions, and labels as specified, all assigned to John in the Website Redesign project.

#### Example 3: JSON Format for Complex Features

**Prompt to Claude:**
```
Create the following features in Linear using this JSON structure:

```json
{
  "features": [
    {
      "title": "Implement SSO Authentication",
      "description": "Add support for SAML and OIDC single sign-on providers",
      "priority": "High",
      "labels": ["security", "authentication", "enterprise"],
      "estimate": 8
    },
    {
      "title": "Real-time Collaboration",
      "description": "Implement real-time editing and presence indicators",
      "priority": "Medium",
      "labels": ["collaboration", "frontend"],
      "estimate": 13
    },
    {
      "title": "Automated PDF Reports",
      "description": "Generate PDF reports on a schedule and deliver via email",
      "priority": "Low",
      "labels": ["reporting", "automation"],
      "estimate": 5
    }
  ],
  "metadata": {
    "project": "Enterprise Features",
    "team": "Platform Team",
    "milestone": "Q3 Release"
  }
}
```

Please create these in Linear.
```

**Expected Result:**
Claude will create three detailed issues with all the specified metadata in the Enterprise Features project under the Platform Team.

### Searching for Issues

#### Example 1: Basic Search

**Prompt to Claude:**
```
Find all high priority issues in Linear that are currently in progress.
```

**Expected Result:**
Claude will search Linear for high priority issues with an "In Progress" status and display the results.

#### Example 2: Filtered Search

**Prompt to Claude:**
```
Show me all bugs assigned to Sarah in the Backend project that were created in the last week.
```

**Expected Result:**
Claude will search Linear for issues with type "Bug", assigned to Sarah, in the Backend project, created within the last 7 days.

#### Example 3: Complex Search

**Prompt to Claude:**
```
Find all issues related to authentication that are either high priority or have the "security" label, excluding any that are already completed.
```

**Expected Result:**
Claude will perform a complex search with multiple conditions and return the matching issues.

### Project Management Workflows

#### Example 1: Project Status Overview

**Prompt to Claude:**
```
Give me an overview of the current status of the "Mobile App Redesign" project in Linear, including progress, issues by status, and team members involved.
```

**Expected Result:**
Claude will retrieve project information, issue statistics, and team member details to provide a comprehensive overview.

#### Example 2: Creating a Sprint

**Prompt to Claude:**
```
Help me set up a new sprint in Linear for the Frontend team. We need to include all high priority issues related to the user profile feature that aren't already assigned to a cycle.
```

**Expected Result:**
Claude will search for relevant issues and suggest how to create a new cycle (sprint) with those issues.

#### Example 3: Dependency Management

**Prompt to Claude:**
```
Find all issues that are blocking the completion of the "Payment Processing" feature in Linear.
```

**Expected Result:**
Claude will search for issues that are dependencies for the Payment Processing feature and display them.

## Cursor Examples

### Setting Up the Linear Connection

1. Open Cursor
2. Go to Settings > AI > MCP
3. Click "Add MCP Server"
4. Enter the following details:
   - Name: Linear
   - URL: `ws://localhost:8080` (or your server URL)
   - API Key: (leave blank or enter your MCP server API key if configured)
5. Click "Add"

### Code-to-Issue Workflows

#### Example 1: Creating Issues from Code Comments

**Code with TODO Comments:**
```javascript
// TODO: Implement user authentication with OAuth
function authenticateUser() {
  // Placeholder for authentication logic
  console.log("Authentication not implemented yet");
  return false;
}

// TODO: Add input validation for all form fields
function validateForm() {
  // Basic validation only
  return true;
}

// TODO: Implement error handling for API requests
async function fetchData() {
  const response = await fetch('/api/data');
  const data = await response.json();
  return data;
}
```

**Prompt to Cursor:**
```
Create Linear issues for all the TODO items in this file. Assign them to the Authentication project with appropriate priorities.
```

**Expected Result:**
Cursor will extract the TODO comments and create three issues in Linear under the Authentication project.

#### Example 2: Creating Issues from Feature Requirements

**Feature Requirement Document:**
```markdown
# User Profile Feature Requirements

## Requirements:
1. Users should be able to upload a profile picture
2. Users should be able to edit their personal information
3. Users should be able to set visibility preferences for their profile
4. Users should be able to link social media accounts
5. System should validate email addresses when updated
```

**Prompt to Cursor:**
```
Create Linear issues for each of these user profile requirements. Add them to the User Management project and tag them with the "user-profile" label.
```

**Expected Result:**
Cursor will create five issues in Linear based on the requirements, adding them to the User Management project with the user-profile label.

#### Example 3: Bug Report to Issue

**Bug Report:**
```
Bug: Application crashes when uploading large images

Steps to reproduce:
1. Go to the profile page
2. Click "Upload Profile Picture"
3. Select an image larger than 5MB
4. Click "Save"

Expected behavior: The application should either compress the image or show an error message about file size limits.

Actual behavior: The application freezes and then crashes with a memory error.

Environment:
- Browser: Chrome 112.0.5615.138
- OS: Windows 11
- Device: Dell XPS 15
```

**Prompt to Cursor:**
```
Create a bug ticket in Linear based on this bug report. Set priority to High and assign it to the Frontend team.
```

**Expected Result:**
Cursor will create a detailed bug ticket in Linear with all the information from the report, set to high priority and assigned to the Frontend team.

### Project Planning Workflows

#### Example 1: Breaking Down a Feature

**Feature Description:**
```
Feature: User Authentication System

We need to implement a comprehensive authentication system that supports:
- Email/password registration and login
- Social login (Google, GitHub, Twitter)
- Two-factor authentication
- Password reset functionality
- Session management
- Account lockout after failed attempts
```

**Prompt to Cursor:**
```
Break down this authentication feature into individual tasks in Linear. Create a parent issue for the overall feature and child issues for each component. Assign to the Security team.
```

**Expected Result:**
Cursor will create a parent issue for the authentication system and child issues for each component, all assigned to the Security team.

#### Example 2: Sprint Planning

**Prompt to Cursor:**
```
Help me plan our next two-week sprint in Linear. We need to focus on the checkout process. Create a cycle called "Sprint 23 - Checkout Flow" and add appropriate issues from our backlog that relate to the checkout process. Prioritize any high-priority items and bugs.
```

**Expected Result:**
Cursor will search for checkout-related issues, suggest which ones to include in the sprint, and help create a new cycle with those issues.

## Advanced Usage Patterns

### Automating Repetitive Tasks

#### Example 1: Weekly Bug Triage

**Prompt to Claude/Cursor:**
```
Find all bugs reported in the last week that haven't been triaged yet. For each one:
1. Assess its priority based on the description
2. Suggest which team should handle it
3. Add appropriate labels
4. Create a summary of all bugs for our weekly triage meeting
```

**Expected Result:**
The MCP client will search for untriaged bugs, analyze each one, update them in Linear with suggested metadata, and create a summary report.

#### Example 2: Release Notes Generation

**Prompt to Claude/Cursor:**
```
Generate release notes for our upcoming v2.5 release. Find all issues in Linear that are in the "Ready for Release" state and part of the v2.5 milestone. Organize them by feature category and create a user-friendly summary of changes.
```

**Expected Result:**
The MCP client will search for relevant issues, categorize them, and generate formatted release notes.

### Integration with Development Workflow

#### Example 1: Code Review to Issue Linking

**Prompt to Cursor:**
```
Review this pull request and create Linear issues for any technical debt or future improvements you identify. Link the issues back to this PR in the description.
```

**Expected Result:**
Cursor will analyze the code, identify areas for improvement, create issues in Linear, and include references to the PR.

#### Example 2: Issue Status Updates from Code

**Prompt to Cursor:**
```
I've just completed implementing the user authentication feature. Update the corresponding Linear issue (AUTH-42) to "Ready for Review" and add a comment with a summary of the implementation details.
```

**Expected Result:**
Cursor will update the status of the specified issue and add a detailed comment.

## Best Practices

### Effective Feature List Creation

1. **Be Specific**: Provide clear, specific titles for each feature
2. **Include Context**: Add descriptions that explain the purpose and requirements
3. **Add Metadata**: Include priority, labels, and other relevant metadata
4. **Organize Hierarchically**: Use parent-child relationships for complex features
5. **Use Consistent Formatting**: Stick to a consistent format for feature lists

### Optimizing Search Queries

1. **Be Specific**: Include key details like project, assignee, or status
2. **Use Natural Language**: Phrase queries in natural language
3. **Combine Filters**: Use multiple filters to narrow down results
4. **Specify Time Ranges**: Include time constraints when relevant
5. **Use Labels**: Reference labels to categorize and filter issues

### Managing Large Projects

1. **Create Parent Issues**: Use parent issues for epics or large features
2. **Use Consistent Labels**: Develop a consistent labeling system
3. **Leverage Projects**: Organize issues into projects for better management
4. **Track Dependencies**: Explicitly mark dependencies between issues
5. **Regular Status Updates**: Keep issue statuses up to date

## Troubleshooting Client Issues

### Common Claude Desktop Issues

1. **Connection Problems**:
   - Verify the server URL is correct
   - Check that the Linear MCP Server is running
   - Restart Claude Desktop

2. **Authentication Issues**:
   - Verify the API key is correct
   - Check server logs for authentication errors

3. **Feature List Processing Problems**:
   - Simplify the format of your feature list
   - Check for syntax errors in JSON or Markdown
   - Provide explicit metadata (project ID, team ID)

### Common Cursor Issues

1. **Connection Problems**:
   - Verify the server URL is correct
   - Check that the Linear MCP Server is running
   - Restart Cursor

2. **Context Limitations**:
   - Break large code bases into smaller chunks
   - Focus queries on specific files or functions

3. **Specificity Issues**:
   - Be more explicit in your requests
   - Provide specific project or team information

## Conclusion

This guide demonstrates the power of integrating Linear with MCP clients through the Linear MCP Server. By following these examples and best practices, you can streamline your project management workflow, automate repetitive tasks, and seamlessly create and manage work items directly from your development environment.

Remember that the effectiveness of your interactions depends on:

1. The quality and specificity of your prompts
2. The configuration of your Linear MCP Server
3. The capabilities of your MCP client

As you become more familiar with the integration, you'll discover additional workflows and optimizations that suit your specific needs and development process.

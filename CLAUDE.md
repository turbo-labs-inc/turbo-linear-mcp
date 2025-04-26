# CLAUDE.md

This document provides best practices and guidelines for implementing the Linear MCP server. Follow these approaches to maximize development effectiveness.

## Development Workflow

### Explore First, Code Later

1. **Read and understand the codebase**
   - Explore relevant files before making changes
   - Use "read the file that handles X" to understand components
   - Examine existing patterns and conventions

2. **Plan before implementing**
   - Create a detailed plan before writing code
   - Use thinking mode for complex problems:
     - "think" < "think hard" < "think harder" < "ultrathink"
   - Document your plan for reference

3. **Verify understanding with subagents**
   - Use subagents to verify details or investigate questions
   - Have subagents explore alternative approaches
   - Preserve context by delegating specific research tasks

4. **Implement incrementally**
   - Build functionality in small, testable increments
   - Verify each component before moving to the next
   - Document key decisions and approaches
   - Commit completed tasks with descriptive messages

## Test-Driven Development

1. **Write tests first**
   - Create tests based on expected behavior
   - Be explicit about using test-driven development
   - Avoid creating mock implementations prematurely

2. **Verify tests fail appropriately**
   - Run tests to confirm they fail as expected
   - Explicitly avoid writing implementation code at this stage

3. **Implement to pass tests**
   - Write code focused on making tests pass
   - Keep implementation simple initially
   - Iterate until all tests pass

4. **Use independent verification**
   - Have subagents verify implementation isn't overfitting to tests
   - Check edge cases and error conditions
   - Ensure implementation meets requirements beyond tests

5. **Refactor with confidence**
   - Improve code quality while maintaining test coverage
   - Extract common patterns into reusable components
   - Optimize only after functionality is verified

## Iteration and Feedback

1. **Iterate on implementations**
   - First versions are rarely optimal
   - Expect 2-3 iterations for quality results
   - Be willing to restart if approach isn't working

2. **Course correct early and often**
   - Identify issues as early as possible
   - Don't hesitate to change direction when needed
   - Use escape key to interrupt and redirect

3. **Verify against clear targets**
   - Use tests as objective verification
   - Compare against specifications
   - Validate against expected outputs

4. **Document learnings**
   - Update this file with new insights
   - Document patterns that work well
   - Note areas that need special attention

## Context Management

1. **Use /clear between tasks**
   - Clear context when switching between components
   - Start fresh for new major tasks
   - Maintain clean context for better performance

2. **Document important information**
   - Use # command to add information to this file
   - Document commands, files, and style guidelines
   - Keep track of key decisions and approaches

3. **Focus context on relevant information**
   - Mention specific files needed for current task
   - Provide only necessary context
   - Avoid overwhelming with irrelevant details

## Tool Usage

1. **Leverage bash tools effectively**
   - Use appropriate tools for each task
   - Chain commands with && for efficiency
   - Save outputs to files when needed

2. **Use git effectively**
   - Make atomic, focused commits
   - Write clear commit messages
   - Use git for exploring code history
   - Commit after each task completion
   - Reference project plan in commit messages

3. **Automate repetitive tasks**
   - Create scripts for common operations
   - Use custom slash commands for workflows
   - Batch similar operations

## Implementation Specifics

### Code Organization

- Follow modular architecture as outlined in implementation blueprint
- Keep components loosely coupled
- Use dependency injection for testability
- Maintain clear separation of concerns

### Error Handling

- Implement comprehensive error handling
- Use structured error responses
- Log errors with appropriate detail
- Provide helpful error messages

### Testing Strategy

- Unit tests for individual components
- Integration tests for component interactions
- End-to-end tests for complete workflows
- Mock external dependencies appropriately

### Performance Considerations

- Implement caching where appropriate
- Optimize database queries
- Use efficient algorithms and data structures
- Consider pagination for large result sets

## Specific Instructions

### When implementing feature list processing:

1. Start with parser implementation
2. Write comprehensive tests for different formats
3. Implement validation and error handling
4. Connect to Linear API client
5. Add batch processing capabilities

### When implementing search functionality:

1. Start with query builder implementation
2. Create result processing utilities
3. Implement filtering and pagination
4. Add caching layer
5. Connect to Linear API client

### When implementing authentication:

1. Start with API key validation
2. Implement secure storage
3. Add permission checking
4. Create authentication middleware
5. Add OAuth support if needed

## Best Practices

- Be specific in your approach
- Verify understanding before implementation
- Test thoroughly
- Document as you go
- Refactor for clarity and maintainability
- Use consistent patterns
- Follow the implementation blueprint
- Iterate to improve quality

Remember to use thinking mode for complex problems and leverage subagents for verification and research.

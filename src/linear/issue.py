"""
Linear issue resource module.

This module provides functionality for interacting with Linear issues.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from src.linear.client import LinearClient
from src.utils.errors import LinearAPIError, NotFoundError, ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class IssueState(str, Enum):
    """Linear issue states."""

    BACKLOG = "backlog"
    UNSTARTED = "unstarted"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELED = "canceled"


class IssueCreateInput(BaseModel):
    """Input for creating a Linear issue."""

    title: str
    description: Optional[str] = None
    team_id: Optional[str] = None
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    state_id: Optional[str] = None
    priority: Optional[int] = None
    labels: Optional[List[str]] = None
    parent_id: Optional[str] = None
    cycle_id: Optional[str] = None
    estimate: Optional[float] = None
    due_date: Optional[datetime] = None


class IssueUpdateInput(BaseModel):
    """Input for updating a Linear issue."""

    title: Optional[str] = None
    description: Optional[str] = None
    team_id: Optional[str] = None
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    state_id: Optional[str] = None
    priority: Optional[int] = None
    labels: Optional[List[str]] = None
    parent_id: Optional[str] = None
    cycle_id: Optional[str] = None
    estimate: Optional[float] = None
    due_date: Optional[datetime] = None


class IssueFindInput(BaseModel):
    """Input for finding Linear issues."""

    id: Optional[str] = None
    team_id: Optional[str] = None
    project_id: Optional[str] = None
    assignee_id: Optional[str] = None
    state_id: Optional[str] = None
    priority: Optional[int] = None
    labels: Optional[List[str]] = None
    created_at_gt: Optional[datetime] = None
    created_at_lt: Optional[datetime] = None
    updated_at_gt: Optional[datetime] = None
    updated_at_lt: Optional[datetime] = None
    due_date_gt: Optional[datetime] = None
    due_date_lt: Optional[datetime] = None


class LinearIssueClient:
    """
    Client for interacting with Linear issues.
    
    This class provides methods for creating, updating, and querying Linear issues.
    """

    def __init__(self, linear_client: LinearClient):
        """
        Initialize the Linear issue client.
        
        Args:
            linear_client: Linear API client
        """
        self.client = linear_client
        logger.info("Linear issue client initialized")

    async def create_issue(self, input_data: IssueCreateInput) -> Dict[str, Any]:
        """
        Create a new Linear issue.
        
        Args:
            input_data: Issue creation input
            
        Returns:
            Created issue data
            
        Raises:
            LinearAPIError: If the API request fails
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue {
              id
              title
              description
              identifier
              url
              state {
                id
                name
                color
                type
              }
              team {
                id
                name
                key
              }
              project {
                id
                name
              }
              assignee {
                id
                name
                email
              }
              labels {
                nodes {
                  id
                  name
                  color
                }
              }
              priority
              estimate
              dueDate
              createdAt
              updatedAt
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        variables = {
            "input": {
                "title": input_data.title,
                "description": input_data.description,
                "teamId": input_data.team_id,
                "projectId": input_data.project_id,
                "assigneeId": input_data.assignee_id,
                "stateId": input_data.state_id,
                "priority": input_data.priority,
                "parentId": input_data.parent_id,
                "cycleId": input_data.cycle_id,
                "estimate": input_data.estimate,
                "dueDate": input_data.due_date.isoformat() if input_data.due_date else None,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        # Add labels if provided
        if input_data.labels:
            variables["input"]["labelIds"] = input_data.labels
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("issueCreate", {}).get("success"):
                raise LinearAPIError("Failed to create issue")
            
            return result["issueCreate"]["issue"]
        
        except LinearAPIError as e:
            logger.error(f"Error creating Linear issue: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error creating Linear issue: {e}")
            raise LinearAPIError(f"Unexpected error creating issue: {e}")

    async def update_issue(self, issue_id: str, input_data: IssueUpdateInput) -> Dict[str, Any]:
        """
        Update an existing Linear issue.
        
        Args:
            issue_id: ID of the issue to update
            input_data: Issue update input
            
        Returns:
            Updated issue data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue is not found
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue {
              id
              title
              description
              identifier
              url
              state {
                id
                name
                color
                type
              }
              team {
                id
                name
                key
              }
              project {
                id
                name
              }
              assignee {
                id
                name
                email
              }
              labels {
                nodes {
                  id
                  name
                  color
                }
              }
              priority
              estimate
              dueDate
              createdAt
              updatedAt
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        variables = {
            "id": issue_id,
            "input": {
                "title": input_data.title,
                "description": input_data.description,
                "teamId": input_data.team_id,
                "projectId": input_data.project_id,
                "assigneeId": input_data.assignee_id,
                "stateId": input_data.state_id,
                "priority": input_data.priority,
                "parentId": input_data.parent_id,
                "cycleId": input_data.cycle_id,
                "estimate": input_data.estimate,
                "dueDate": input_data.due_date.isoformat() if input_data.due_date else None,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        # Add labels if provided
        if input_data.labels is not None:
            variables["input"]["labelIds"] = input_data.labels
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("issueUpdate", {}).get("success"):
                raise LinearAPIError("Failed to update issue")
            
            return result["issueUpdate"]["issue"]
        
        except NotFoundError:
            logger.error(f"Issue not found: {issue_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error updating Linear issue: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error updating Linear issue: {e}")
            raise LinearAPIError(f"Unexpected error updating issue: {e}")

    async def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """
        Get a Linear issue by ID.
        
        Args:
            issue_id: ID of the issue to retrieve
            
        Returns:
            Issue data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue is not found
        """
        # Define the GraphQL query
        query = """
        query GetIssue($id: String!) {
          issue(id: $id) {
            id
            title
            description
            identifier
            url
            state {
              id
              name
              color
              type
            }
            team {
              id
              name
              key
            }
            project {
              id
              name
            }
            assignee {
              id
              name
              email
            }
            labels {
              nodes {
                id
                name
                color
              }
            }
            priority
            estimate
            dueDate
            createdAt
            updatedAt
            parent {
              id
              title
            }
            children {
              nodes {
                id
                title
              }
            }
            comments {
              nodes {
                id
                body
                user {
                  id
                  name
                }
                createdAt
              }
            }
          }
        }
        """
        
        variables = {
            "id": issue_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("issue"):
                raise NotFoundError(f"Issue not found: {issue_id}")
            
            return result["issue"]
        
        except NotFoundError:
            logger.error(f"Issue not found: {issue_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear issue: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear issue: {e}")
            raise LinearAPIError(f"Unexpected error getting issue: {e}")

    async def find_issues(
        self, 
        input_data: Optional[IssueFindInput] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Find Linear issues matching the given criteria.
        
        Args:
            input_data: Search criteria
            limit: Maximum number of issues to return
            offset: Offset for pagination
            
        Returns:
            List of matching issues
            
        Raises:
            LinearAPIError: If the API request fails
        """
        # Define the GraphQL query
        query = """
        query FindIssues($filter: IssueFilter, $first: Int, $after: String) {
          issues(filter: $filter, first: $first, after: $after, orderBy: updatedAt) {
            nodes {
              id
              title
              description
              identifier
              url
              state {
                id
                name
                color
                type
              }
              team {
                id
                name
                key
              }
              project {
                id
                name
              }
              assignee {
                id
                name
                email
              }
              labels {
                nodes {
                  id
                  name
                  color
                }
              }
              priority
              estimate
              dueDate
              createdAt
              updatedAt
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        # Build filter from input data
        filter_vars = {}
        if input_data:
            if input_data.id:
                filter_vars["id"] = {"eq": input_data.id}
            if input_data.team_id:
                filter_vars["team"] = {"id": {"eq": input_data.team_id}}
            if input_data.project_id:
                filter_vars["project"] = {"id": {"eq": input_data.project_id}}
            if input_data.assignee_id:
                filter_vars["assignee"] = {"id": {"eq": input_data.assignee_id}}
            if input_data.state_id:
                filter_vars["state"] = {"id": {"eq": input_data.state_id}}
            if input_data.priority is not None:
                filter_vars["priority"] = {"eq": input_data.priority}
            
            # Date filters
            if input_data.created_at_gt:
                filter_vars["createdAt"] = {"gt": input_data.created_at_gt.isoformat()}
            if input_data.created_at_lt:
                filter_vars["createdAt"] = filter_vars.get("createdAt", {})
                filter_vars["createdAt"]["lt"] = input_data.created_at_lt.isoformat()
            
            if input_data.updated_at_gt:
                filter_vars["updatedAt"] = {"gt": input_data.updated_at_gt.isoformat()}
            if input_data.updated_at_lt:
                filter_vars["updatedAt"] = filter_vars.get("updatedAt", {})
                filter_vars["updatedAt"]["lt"] = input_data.updated_at_lt.isoformat()
            
            if input_data.due_date_gt:
                filter_vars["dueDate"] = {"gt": input_data.due_date_gt.isoformat()}
            if input_data.due_date_lt:
                filter_vars["dueDate"] = filter_vars.get("dueDate", {})
                filter_vars["dueDate"]["lt"] = input_data.due_date_lt.isoformat()
            
            # Label filters
            if input_data.labels:
                filter_vars["labels"] = {"some": {"id": {"in": input_data.labels}}}
        
        variables = {
            "filter": filter_vars,
            "first": limit,
        }
        
        if offset > 0:
            # Linear uses cursor-based pagination, so we need to get the cursor for the offset
            # This is a simplification; in a real implementation, you might need to fetch
            # issues up to the offset to get the correct cursor
            variables["after"] = f"offset:{offset}"
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("issues", {}).get("nodes"):
                return []
            
            return result["issues"]["nodes"]
        
        except LinearAPIError as e:
            logger.error(f"Error finding Linear issues: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error finding Linear issues: {e}")
            raise LinearAPIError(f"Unexpected error finding issues: {e}")

    async def delete_issue(self, issue_id: str) -> bool:
        """
        Delete a Linear issue.
        
        Args:
            issue_id: ID of the issue to delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue is not found
        """
        # Define the GraphQL mutation
        mutation = """
        mutation DeleteIssue($id: String!) {
          issueDelete(id: $id) {
            success
          }
        }
        """
        
        variables = {
            "id": issue_id,
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("issueDelete", {}).get("success", False)
        
        except NotFoundError:
            logger.error(f"Issue not found: {issue_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error deleting Linear issue: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error deleting Linear issue: {e}")
            raise LinearAPIError(f"Unexpected error deleting issue: {e}")

    async def get_issue_by_identifier(self, identifier: str) -> Dict[str, Any]:
        """
        Get a Linear issue by identifier (e.g., "PROJ-123").
        
        Args:
            identifier: Issue identifier
            
        Returns:
            Issue data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue is not found
        """
        # Define the GraphQL query
        query = """
        query GetIssueByIdentifier($identifier: String!) {
          issueVcsBranchSearch(identifier: $identifier) {
            id
            title
            description
            identifier
            url
            state {
              id
              name
              color
              type
            }
            team {
              id
              name
              key
            }
            project {
              id
              name
            }
            assignee {
              id
              name
              email
            }
            labels {
              nodes {
                id
                name
                color
              }
            }
            priority
            estimate
            dueDate
            createdAt
            updatedAt
          }
        }
        """
        
        variables = {
            "identifier": identifier,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("issueVcsBranchSearch"):
                raise NotFoundError(f"Issue not found: {identifier}")
            
            return result["issueVcsBranchSearch"]
        
        except NotFoundError:
            logger.error(f"Issue not found: {identifier}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear issue by identifier: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear issue by identifier: {e}")
            raise LinearAPIError(f"Unexpected error getting issue: {e}")

    async def create_comment(self, issue_id: str, body: str) -> Dict[str, Any]:
        """
        Create a comment on a Linear issue.
        
        Args:
            issue_id: ID of the issue to comment on
            body: Comment text
            
        Returns:
            Created comment data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue is not found
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation CreateComment($input: CommentCreateInput!) {
          commentCreate(input: $input) {
            success
            comment {
              id
              body
              user {
                id
                name
              }
              createdAt
              issue {
                id
                title
              }
            }
          }
        }
        """
        
        variables = {
            "input": {
                "issueId": issue_id,
                "body": body,
            }
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("commentCreate", {}).get("success"):
                raise LinearAPIError("Failed to create comment")
            
            return result["commentCreate"]["comment"]
        
        except NotFoundError:
            logger.error(f"Issue not found: {issue_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error creating Linear comment: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error creating Linear comment: {e}")
            raise LinearAPIError(f"Unexpected error creating comment: {e}")

    async def create_issues_batch(
        self, issues: List[IssueCreateInput]
    ) -> List[Dict[str, Any]]:
        """
        Create multiple Linear issues in batch.
        
        Args:
            issues: List of issue creation inputs
            
        Returns:
            List of created issues
            
        Raises:
            LinearAPIError: If the API request fails
            ValidationError: If the input data is invalid
        """
        created_issues = []
        
        for issue_input in issues:
            try:
                issue = await self.create_issue(issue_input)
                created_issues.append(issue)
            except Exception as e:
                logger.error(f"Error creating issue in batch: {e}")
                # Continue with next issue
                continue
        
        return created_issues
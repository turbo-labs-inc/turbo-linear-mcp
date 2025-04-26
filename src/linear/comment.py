"""
Linear comment resource module.

This module provides functionality for interacting with Linear comments.
"""

from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from src.linear.client import LinearClient
from src.utils.errors import LinearAPIError, NotFoundError, ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CommentCreateInput(BaseModel):
    """Input for creating a Linear comment."""

    issue_id: str
    body: str
    parent_id: Optional[str] = None


class CommentUpdateInput(BaseModel):
    """Input for updating a Linear comment."""

    body: str


class LinearCommentClient:
    """
    Client for interacting with Linear comments.
    
    This class provides methods for creating, updating, and querying Linear comments.
    """

    def __init__(self, linear_client: LinearClient):
        """
        Initialize the Linear comment client.
        
        Args:
            linear_client: Linear API client
        """
        self.client = linear_client
        logger.info("Linear comment client initialized")

    async def create_comment(self, input_data: CommentCreateInput) -> Dict[str, Any]:
        """
        Create a new Linear comment.
        
        Args:
            input_data: Comment creation input
            
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
                email
              }
              issue {
                id
                title
                identifier
              }
              parent {
                id
              }
              children {
                nodes {
                  id
                }
              }
              createdAt
              updatedAt
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        variables = {
            "input": {
                "issueId": input_data.issue_id,
                "body": input_data.body,
            }
        }
        
        # Add parent ID if provided
        if input_data.parent_id:
            variables["input"]["parentId"] = input_data.parent_id
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("commentCreate", {}).get("success"):
                raise LinearAPIError("Failed to create comment")
            
            return result["commentCreate"]["comment"]
        
        except NotFoundError:
            logger.error(f"Issue not found: {input_data.issue_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error creating Linear comment: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error creating Linear comment: {e}")
            raise LinearAPIError(f"Unexpected error creating comment: {e}")

    async def update_comment(self, comment_id: str, input_data: CommentUpdateInput) -> Dict[str, Any]:
        """
        Update an existing Linear comment.
        
        Args:
            comment_id: ID of the comment to update
            input_data: Comment update input
            
        Returns:
            Updated comment data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the comment is not found
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation UpdateComment($id: String!, $input: CommentUpdateInput!) {
          commentUpdate(id: $id, input: $input) {
            success
            comment {
              id
              body
              user {
                id
                name
                email
              }
              issue {
                id
                title
                identifier
              }
              parent {
                id
              }
              children {
                nodes {
                  id
                }
              }
              createdAt
              updatedAt
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        variables = {
            "id": comment_id,
            "input": {
                "body": input_data.body,
            }
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("commentUpdate", {}).get("success"):
                raise LinearAPIError("Failed to update comment")
            
            return result["commentUpdate"]["comment"]
        
        except NotFoundError:
            logger.error(f"Comment not found: {comment_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error updating Linear comment: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error updating Linear comment: {e}")
            raise LinearAPIError(f"Unexpected error updating comment: {e}")

    async def get_comment(self, comment_id: str) -> Dict[str, Any]:
        """
        Get a Linear comment by ID.
        
        Args:
            comment_id: ID of the comment to retrieve
            
        Returns:
            Comment data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the comment is not found
        """
        # Define the GraphQL query
        query = """
        query GetComment($id: String!) {
          comment(id: $id) {
            id
            body
            user {
              id
              name
              email
            }
            issue {
              id
              title
              identifier
            }
            parent {
              id
              body
              user {
                id
                name
              }
            }
            children {
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
            createdAt
            updatedAt
          }
        }
        """
        
        variables = {
            "id": comment_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("comment"):
                raise NotFoundError(f"Comment not found: {comment_id}")
            
            return result["comment"]
        
        except NotFoundError:
            logger.error(f"Comment not found: {comment_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear comment: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear comment: {e}")
            raise LinearAPIError(f"Unexpected error getting comment: {e}")

    async def delete_comment(self, comment_id: str) -> bool:
        """
        Delete a Linear comment.
        
        Args:
            comment_id: ID of the comment to delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the comment is not found
        """
        # Define the GraphQL mutation
        mutation = """
        mutation DeleteComment($id: String!) {
          commentDelete(id: $id) {
            success
          }
        }
        """
        
        variables = {
            "id": comment_id,
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("commentDelete", {}).get("success", False)
        
        except NotFoundError:
            logger.error(f"Comment not found: {comment_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error deleting Linear comment: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error deleting Linear comment: {e}")
            raise LinearAPIError(f"Unexpected error deleting comment: {e}")

    async def get_issue_comments(self, issue_id: str) -> List[Dict[str, Any]]:
        """
        Get comments for an issue.
        
        Args:
            issue_id: ID of the issue
            
        Returns:
            List of comments
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue is not found
        """
        # Define the GraphQL query
        query = """
        query GetIssueComments($id: String!) {
          issue(id: $id) {
            comments {
              nodes {
                id
                body
                user {
                  id
                  name
                  email
                }
                parent {
                  id
                }
                children {
                  totalCount
                }
                createdAt
                updatedAt
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
            
            return result["issue"]["comments"]["nodes"]
        
        except NotFoundError:
            logger.error(f"Issue not found: {issue_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting issue comments: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting issue comments: {e}")
            raise LinearAPIError(f"Unexpected error getting issue comments: {e}")

    async def get_comment_replies(self, comment_id: str) -> List[Dict[str, Any]]:
        """
        Get replies to a comment.
        
        Args:
            comment_id: ID of the parent comment
            
        Returns:
            List of reply comments
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the comment is not found
        """
        # Define the GraphQL query
        query = """
        query GetCommentReplies($id: String!) {
          comment(id: $id) {
            children {
              nodes {
                id
                body
                user {
                  id
                  name
                  email
                }
                createdAt
                updatedAt
              }
            }
          }
        }
        """
        
        variables = {
            "id": comment_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("comment"):
                raise NotFoundError(f"Comment not found: {comment_id}")
            
            return result["comment"]["children"]["nodes"]
        
        except NotFoundError:
            logger.error(f"Comment not found: {comment_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting comment replies: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting comment replies: {e}")
            raise LinearAPIError(f"Unexpected error getting comment replies: {e}")
"""
Linear user resource module.

This module provides functionality for interacting with Linear users.
"""

from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from src.linear.client import LinearClient
from src.utils.errors import LinearAPIError, NotFoundError, ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class UserUpdateInput(BaseModel):
    """Input for updating a Linear user."""

    name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = None
    timezone: Optional[str] = None


class LinearUserClient:
    """
    Client for interacting with Linear users.
    
    This class provides methods for updating and querying Linear users.
    """

    def __init__(self, linear_client: LinearClient):
        """
        Initialize the Linear user client.
        
        Args:
            linear_client: Linear API client
        """
        self.client = linear_client
        logger.info("Linear user client initialized")

    async def get_users(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get all Linear users.
        
        Args:
            active_only: Whether to return only active users
            
        Returns:
            List of users
            
        Raises:
            LinearAPIError: If the API request fails
        """
        # Define the GraphQL query
        query = """
        query GetUsers($filter: UserFilter) {
          users(filter: $filter) {
            nodes {
              id
              name
              email
              displayName
              avatarUrl
              active
              admin
              lastSeen
              createdAt
              updatedAt
              teams {
                nodes {
                  id
                  name
                }
              }
            }
          }
        }
        """
        
        variables = {}
        if active_only:
            variables["filter"] = {"active": {"eq": True}}
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("users", {}).get("nodes"):
                return []
            
            return result["users"]["nodes"]
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear users: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear users: {e}")
            raise LinearAPIError(f"Unexpected error getting users: {e}")

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get a Linear user by ID.
        
        Args:
            user_id: ID of the user to retrieve
            
        Returns:
            User data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the user is not found
        """
        # Define the GraphQL query
        query = """
        query GetUser($id: String!) {
          user(id: $id) {
            id
            name
            email
            displayName
            avatarUrl
            active
            admin
            lastSeen
            createdAt
            updatedAt
            teams {
              nodes {
                id
                name
                key
              }
            }
            assignedIssues {
              totalCount
            }
            createdIssues {
              totalCount
            }
          }
        }
        """
        
        variables = {
            "id": user_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("user"):
                raise NotFoundError(f"User not found: {user_id}")
            
            return result["user"]
        
        except NotFoundError:
            logger.error(f"User not found: {user_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear user: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear user: {e}")
            raise LinearAPIError(f"Unexpected error getting user: {e}")

    async def update_user(self, user_id: str, input_data: UserUpdateInput) -> Dict[str, Any]:
        """
        Update a Linear user.
        
        Args:
            user_id: ID of the user to update
            input_data: User update input
            
        Returns:
            Updated user data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the user is not found
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation UpdateUser($id: String!, $input: UserUpdateInput!) {
          userUpdate(id: $id, input: $input) {
            success
            user {
              id
              name
              email
              displayName
              avatarUrl
              active
              admin
              lastSeen
              createdAt
              updatedAt
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        variables = {
            "id": user_id,
            "input": {
                "name": input_data.name,
                "displayName": input_data.display_name,
                "avatarUrl": input_data.avatar_url,
                "statusText": input_data.status,
                "timezone": input_data.timezone,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("userUpdate", {}).get("success"):
                raise LinearAPIError("Failed to update user")
            
            return result["userUpdate"]["user"]
        
        except NotFoundError:
            logger.error(f"User not found: {user_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error updating Linear user: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error updating Linear user: {e}")
            raise LinearAPIError(f"Unexpected error updating user: {e}")

    async def get_current_user(self) -> Dict[str, Any]:
        """
        Get the currently authenticated user.
        
        Returns:
            Current user data
            
        Raises:
            LinearAPIError: If the API request fails
            UnauthorizedError: If not authenticated
        """
        # Define the GraphQL query
        query = """
        query {
          viewer {
            id
            name
            email
            displayName
            avatarUrl
            active
            admin
            lastSeen
            createdAt
            updatedAt
            teams {
              nodes {
                id
                name
                key
              }
            }
            assignedIssues {
              totalCount
            }
            createdIssues {
              totalCount
            }
          }
        }
        """
        
        try:
            # Execute the query
            result = await self.client.execute_query(query)
            
            if not result.get("viewer"):
                raise LinearAPIError("Failed to get current user")
            
            return result["viewer"]
        
        except LinearAPIError as e:
            logger.error(f"Error getting current user: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting current user: {e}")
            raise LinearAPIError(f"Unexpected error getting current user: {e}")

    async def get_user_assignable_teams(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get teams that a user can be assigned to.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of assignable teams
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the user is not found
        """
        # Define the GraphQL query
        query = """
        query GetUserAssignableTeams($id: String!) {
          user(id: $id) {
            assignableTeams {
              nodes {
                id
                name
                key
                description
              }
            }
          }
        }
        """
        
        variables = {
            "id": user_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("user"):
                raise NotFoundError(f"User not found: {user_id}")
            
            return result["user"]["assignableTeams"]["nodes"]
        
        except NotFoundError:
            logger.error(f"User not found: {user_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting user assignable teams: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting user assignable teams: {e}")
            raise LinearAPIError(f"Unexpected error getting user assignable teams: {e}")

    async def get_user_assigned_issues(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get issues assigned to a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of issues to return
            
        Returns:
            List of assigned issues
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the user is not found
        """
        # Define the GraphQL query
        query = """
        query GetUserAssignedIssues($id: String!, $first: Int) {
          user(id: $id) {
            assignedIssues(first: $first) {
              nodes {
                id
                title
                identifier
                url
                state {
                  name
                  type
                }
                team {
                  id
                  name
                }
                project {
                  id
                  name
                }
                priority
                createdAt
                updatedAt
              }
            }
          }
        }
        """
        
        variables = {
            "id": user_id,
            "first": limit,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("user"):
                raise NotFoundError(f"User not found: {user_id}")
            
            return result["user"]["assignedIssues"]["nodes"]
        
        except NotFoundError:
            logger.error(f"User not found: {user_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting user assigned issues: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting user assigned issues: {e}")
            raise LinearAPIError(f"Unexpected error getting user assigned issues: {e}")

    async def find_user_by_email(self, email: str) -> Dict[str, Any]:
        """
        Find a user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the user is not found
        """
        # Define the GraphQL query
        query = """
        query FindUserByEmail($email: String!) {
          users(filter: {email: {eq: $email}}) {
            nodes {
              id
              name
              email
              displayName
              avatarUrl
              active
              admin
              lastSeen
              createdAt
              updatedAt
            }
          }
        }
        """
        
        variables = {
            "email": email,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            users = result.get("users", {}).get("nodes", [])
            if not users:
                raise NotFoundError(f"User not found with email: {email}")
            
            return users[0]
        
        except NotFoundError:
            logger.error(f"User not found with email: {email}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error finding user by email: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error finding user by email: {e}")
            raise LinearAPIError(f"Unexpected error finding user by email: {e}")

    async def get_user_active_teams(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get teams that a user is actively part of.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of active teams
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the user is not found
        """
        # Define the GraphQL query
        query = """
        query GetUserActiveTeams($id: String!) {
          user(id: $id) {
            teams {
              nodes {
                id
                name
                key
                description
                icon
                color
              }
            }
          }
        }
        """
        
        variables = {
            "id": user_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("user"):
                raise NotFoundError(f"User not found: {user_id}")
            
            return result["user"]["teams"]["nodes"]
        
        except NotFoundError:
            logger.error(f"User not found: {user_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting user active teams: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting user active teams: {e}")
            raise LinearAPIError(f"Unexpected error getting user active teams: {e}")
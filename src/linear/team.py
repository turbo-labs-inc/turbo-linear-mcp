"""
Linear team resource module.

This module provides functionality for interacting with Linear teams.
"""

from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from src.linear.client import LinearClient
from src.utils.errors import LinearAPIError, NotFoundError, ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TeamCreateInput(BaseModel):
    """Input for creating a Linear team."""

    name: str
    key: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    private: Optional[bool] = None


class TeamUpdateInput(BaseModel):
    """Input for updating a Linear team."""

    name: Optional[str] = None
    key: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    private: Optional[bool] = None


class LinearTeamClient:
    """
    Client for interacting with Linear teams.
    
    This class provides methods for creating, updating, and querying Linear teams.
    """

    def __init__(self, linear_client: LinearClient):
        """
        Initialize the Linear team client.
        
        Args:
            linear_client: Linear API client
        """
        self.client = linear_client
        logger.info("Linear team client initialized")

    async def create_team(self, input_data: TeamCreateInput) -> Dict[str, Any]:
        """
        Create a new Linear team.
        
        Args:
            input_data: Team creation input
            
        Returns:
            Created team data
            
        Raises:
            LinearAPIError: If the API request fails
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation CreateTeam($input: TeamCreateInput!) {
          teamCreate(input: $input) {
            success
            team {
              id
              name
              key
              description
              icon
              color
              private
              createdAt
              updatedAt
              members {
                nodes {
                  id
                  name
                }
              }
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        variables = {
            "input": {
                "name": input_data.name,
                "key": input_data.key,
                "description": input_data.description,
                "icon": input_data.icon,
                "color": input_data.color,
                "private": input_data.private,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("teamCreate", {}).get("success"):
                raise LinearAPIError("Failed to create team")
            
            return result["teamCreate"]["team"]
        
        except LinearAPIError as e:
            logger.error(f"Error creating Linear team: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error creating Linear team: {e}")
            raise LinearAPIError(f"Unexpected error creating team: {e}")

    async def update_team(self, team_id: str, input_data: TeamUpdateInput) -> Dict[str, Any]:
        """
        Update an existing Linear team.
        
        Args:
            team_id: ID of the team to update
            input_data: Team update input
            
        Returns:
            Updated team data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the team is not found
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation UpdateTeam($id: String!, $input: TeamUpdateInput!) {
          teamUpdate(id: $id, input: $input) {
            success
            team {
              id
              name
              key
              description
              icon
              color
              private
              createdAt
              updatedAt
              members {
                nodes {
                  id
                  name
                }
              }
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        variables = {
            "id": team_id,
            "input": {
                "name": input_data.name,
                "key": input_data.key,
                "description": input_data.description,
                "icon": input_data.icon,
                "color": input_data.color,
                "private": input_data.private,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("teamUpdate", {}).get("success"):
                raise LinearAPIError("Failed to update team")
            
            return result["teamUpdate"]["team"]
        
        except NotFoundError:
            logger.error(f"Team not found: {team_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error updating Linear team: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error updating Linear team: {e}")
            raise LinearAPIError(f"Unexpected error updating team: {e}")

    async def get_team(self, team_id: str) -> Dict[str, Any]:
        """
        Get a Linear team by ID.
        
        Args:
            team_id: ID of the team to retrieve
            
        Returns:
            Team data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the team is not found
        """
        # Define the GraphQL query
        query = """
        query GetTeam($id: String!) {
          team(id: $id) {
            id
            name
            key
            description
            icon
            color
            private
            createdAt
            updatedAt
            members {
              nodes {
                id
                name
                email
                displayName
                active
                role
              }
            }
            states {
              nodes {
                id
                name
                color
                type
                position
              }
            }
            projects {
              nodes {
                id
                name
                state
              }
            }
            labels {
              nodes {
                id
                name
                color
              }
            }
            cycles {
              nodes {
                id
                name
                startsAt
                endsAt
                progress
              }
            }
          }
        }
        """
        
        variables = {
            "id": team_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("team"):
                raise NotFoundError(f"Team not found: {team_id}")
            
            return result["team"]
        
        except NotFoundError:
            logger.error(f"Team not found: {team_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear team: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear team: {e}")
            raise LinearAPIError(f"Unexpected error getting team: {e}")

    async def get_teams(self) -> List[Dict[str, Any]]:
        """
        Get all Linear teams.
        
        Returns:
            List of teams
            
        Raises:
            LinearAPIError: If the API request fails
        """
        # Define the GraphQL query
        query = """
        query GetTeams {
          teams {
            nodes {
              id
              name
              key
              description
              icon
              color
              private
              createdAt
              updatedAt
              members {
                totalCount
              }
              issues {
                totalCount
              }
              projects {
                totalCount
              }
            }
          }
        }
        """
        
        try:
            # Execute the query
            result = await self.client.execute_query(query)
            
            if not result.get("teams", {}).get("nodes"):
                return []
            
            return result["teams"]["nodes"]
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear teams: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear teams: {e}")
            raise LinearAPIError(f"Unexpected error getting teams: {e}")

    async def get_team_members(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get members of a Linear team.
        
        Args:
            team_id: ID of the team
            
        Returns:
            List of team members
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the team is not found
        """
        # Define the GraphQL query
        query = """
        query GetTeamMembers($id: String!) {
          team(id: $id) {
            members {
              nodes {
                id
                name
                email
                displayName
                active
                role
                createdAt
                updatedAt
              }
            }
          }
        }
        """
        
        variables = {
            "id": team_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("team"):
                raise NotFoundError(f"Team not found: {team_id}")
            
            return result["team"]["members"]["nodes"]
        
        except NotFoundError:
            logger.error(f"Team not found: {team_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting team members: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting team members: {e}")
            raise LinearAPIError(f"Unexpected error getting team members: {e}")

    async def add_team_member(self, team_id: str, user_id: str) -> bool:
        """
        Add a user to a team.
        
        Args:
            team_id: ID of the team
            user_id: ID of the user to add
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the team or user is not found
        """
        # Define the GraphQL mutation
        mutation = """
        mutation AddTeamMember($input: TeamMembershipCreateInput!) {
          teamMembershipCreate(input: $input) {
            success
            teamMembership {
              id
              user {
                id
                name
              }
              team {
                id
                name
              }
            }
          }
        }
        """
        
        variables = {
            "input": {
                "teamId": team_id,
                "userId": user_id,
            }
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("teamMembershipCreate", {}).get("success", False)
        
        except NotFoundError:
            logger.error(f"Team or user not found: {team_id}, {user_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error adding team member: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error adding team member: {e}")
            raise LinearAPIError(f"Unexpected error adding team member: {e}")

    async def remove_team_member(self, team_id: str, user_id: str) -> bool:
        """
        Remove a user from a team.
        
        Args:
            team_id: ID of the team
            user_id: ID of the user to remove
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the team membership is not found
        """
        # First, get the team membership ID
        query = """
        query GetTeamMembership($teamId: String!, $userId: String!) {
          teamMemberships(
            filter: {team: {id: {eq: $teamId}}, user: {id: {eq: $userId}}}
          ) {
            nodes {
              id
            }
          }
        }
        """
        
        variables = {
            "teamId": team_id,
            "userId": user_id,
        }
        
        try:
            # Get team membership ID
            result = await self.client.execute_query(query, variables)
            
            memberships = result.get("teamMemberships", {}).get("nodes", [])
            if not memberships:
                raise NotFoundError(f"Team membership not found for team {team_id} and user {user_id}")
            
            membership_id = memberships[0]["id"]
            
            # Define the GraphQL mutation for deletion
            mutation = """
            mutation RemoveTeamMember($id: String!) {
              teamMembershipDelete(id: $id) {
                success
              }
            }
            """
            
            delete_variables = {
                "id": membership_id,
            }
            
            # Execute the mutation
            delete_result = await self.client.execute_query(mutation, delete_variables)
            
            return delete_result.get("teamMembershipDelete", {}).get("success", False)
        
        except NotFoundError:
            logger.error(f"Team membership not found: {team_id}, {user_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error removing team member: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error removing team member: {e}")
            raise LinearAPIError(f"Unexpected error removing team member: {e}")

    async def get_team_by_key(self, key: str) -> Dict[str, Any]:
        """
        Get a team by its key.
        
        Args:
            key: Team key
            
        Returns:
            Team data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the team is not found
        """
        # Define the GraphQL query
        query = """
        query GetTeamByKey($key: String!) {
          teams(filter: {key: {eq: $key}}) {
            nodes {
              id
              name
              key
              description
              icon
              color
              private
              createdAt
              updatedAt
            }
          }
        }
        """
        
        variables = {
            "key": key,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            teams = result.get("teams", {}).get("nodes", [])
            if not teams:
                raise NotFoundError(f"Team not found with key: {key}")
            
            return teams[0]
        
        except NotFoundError:
            logger.error(f"Team not found with key: {key}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting team by key: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting team by key: {e}")
            raise LinearAPIError(f"Unexpected error getting team by key: {e}")

    async def get_team_workflow_states(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get workflow states for a team.
        
        Args:
            team_id: ID of the team
            
        Returns:
            List of workflow states
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the team is not found
        """
        # Define the GraphQL query
        query = """
        query GetTeamWorkflowStates($id: String!) {
          team(id: $id) {
            states {
              nodes {
                id
                name
                description
                color
                type
                position
              }
            }
          }
        }
        """
        
        variables = {
            "id": team_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("team"):
                raise NotFoundError(f"Team not found: {team_id}")
            
            return result["team"]["states"]["nodes"]
        
        except NotFoundError:
            logger.error(f"Team not found: {team_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting team workflow states: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting team workflow states: {e}")
            raise LinearAPIError(f"Unexpected error getting team workflow states: {e}")

    async def get_team_labels(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get labels for a team.
        
        Args:
            team_id: ID of the team
            
        Returns:
            List of labels
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the team is not found
        """
        # Define the GraphQL query
        query = """
        query GetTeamLabels($id: String!) {
          team(id: $id) {
            labels {
              nodes {
                id
                name
                description
                color
                createdAt
                updatedAt
              }
            }
          }
        }
        """
        
        variables = {
            "id": team_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("team"):
                raise NotFoundError(f"Team not found: {team_id}")
            
            return result["team"]["labels"]["nodes"]
        
        except NotFoundError:
            logger.error(f"Team not found: {team_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting team labels: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting team labels: {e}")
            raise LinearAPIError(f"Unexpected error getting team labels: {e}")
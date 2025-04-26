"""
Linear project resource module.

This module provides functionality for interacting with Linear projects.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from src.linear.client import LinearClient
from src.utils.errors import LinearAPIError, NotFoundError, ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ProjectState(str, Enum):
    """Linear project states."""

    PLANNED = "planned"
    STARTED = "started"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELED = "canceled"


class ProjectCreateInput(BaseModel):
    """Input for creating a Linear project."""

    name: str
    description: Optional[str] = None
    team_id: str
    state: Optional[ProjectState] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class ProjectUpdateInput(BaseModel):
    """Input for updating a Linear project."""

    name: Optional[str] = None
    description: Optional[str] = None
    team_id: Optional[str] = None
    state: Optional[ProjectState] = None
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class LinearProjectClient:
    """
    Client for interacting with Linear projects.
    
    This class provides methods for creating, updating, and querying Linear projects.
    """

    def __init__(self, linear_client: LinearClient):
        """
        Initialize the Linear project client.
        
        Args:
            linear_client: Linear API client
        """
        self.client = linear_client
        logger.info("Linear project client initialized")

    async def create_project(self, input_data: ProjectCreateInput) -> Dict[str, Any]:
        """
        Create a new Linear project.
        
        Args:
            input_data: Project creation input
            
        Returns:
            Created project data
            
        Raises:
            LinearAPIError: If the API request fails
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation CreateProject($input: ProjectCreateInput!) {
          projectCreate(input: $input) {
            success
            project {
              id
              name
              description
              url
              state
              icon
              color
              startDate
              targetDate
              completedAt
              createdAt
              updatedAt
              team {
                id
                name
              }
              members {
                nodes {
                  id
                  name
                }
              }
              issues {
                totalCount
              }
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        variables = {
            "input": {
                "name": input_data.name,
                "description": input_data.description,
                "teamId": input_data.team_id,
                "state": input_data.state.value if input_data.state else None,
                "startDate": input_data.start_date.isoformat() if input_data.start_date else None,
                "targetDate": input_data.target_date.isoformat() if input_data.target_date else None,
                "icon": input_data.icon,
                "color": input_data.color,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("projectCreate", {}).get("success"):
                raise LinearAPIError("Failed to create project")
            
            return result["projectCreate"]["project"]
        
        except LinearAPIError as e:
            logger.error(f"Error creating Linear project: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error creating Linear project: {e}")
            raise LinearAPIError(f"Unexpected error creating project: {e}")

    async def update_project(self, project_id: str, input_data: ProjectUpdateInput) -> Dict[str, Any]:
        """
        Update an existing Linear project.
        
        Args:
            project_id: ID of the project to update
            input_data: Project update input
            
        Returns:
            Updated project data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the project is not found
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation UpdateProject($id: String!, $input: ProjectUpdateInput!) {
          projectUpdate(id: $id, input: $input) {
            success
            project {
              id
              name
              description
              url
              state
              icon
              color
              startDate
              targetDate
              completedAt
              createdAt
              updatedAt
              team {
                id
                name
              }
              members {
                nodes {
                  id
                  name
                }
              }
              issues {
                totalCount
              }
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        variables = {
            "id": project_id,
            "input": {
                "name": input_data.name,
                "description": input_data.description,
                "teamId": input_data.team_id,
                "state": input_data.state.value if input_data.state else None,
                "startDate": input_data.start_date.isoformat() if input_data.start_date else None,
                "targetDate": input_data.target_date.isoformat() if input_data.target_date else None,
                "icon": input_data.icon,
                "color": input_data.color,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("projectUpdate", {}).get("success"):
                raise LinearAPIError("Failed to update project")
            
            return result["projectUpdate"]["project"]
        
        except NotFoundError:
            logger.error(f"Project not found: {project_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error updating Linear project: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error updating Linear project: {e}")
            raise LinearAPIError(f"Unexpected error updating project: {e}")

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get a Linear project by ID.
        
        Args:
            project_id: ID of the project to retrieve
            
        Returns:
            Project data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the project is not found
        """
        # Define the GraphQL query
        query = """
        query GetProject($id: String!) {
          project(id: $id) {
            id
            name
            description
            url
            state
            icon
            color
            startDate
            targetDate
            completedAt
            createdAt
            updatedAt
            team {
              id
              name
            }
            members {
              nodes {
                id
                name
              }
            }
            issues {
              totalCount
              nodes {
                id
                title
                state {
                  name
                  type
                }
              }
            }
          }
        }
        """
        
        variables = {
            "id": project_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("project"):
                raise NotFoundError(f"Project not found: {project_id}")
            
            return result["project"]
        
        except NotFoundError:
            logger.error(f"Project not found: {project_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear project: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear project: {e}")
            raise LinearAPIError(f"Unexpected error getting project: {e}")

    async def get_projects(
        self, 
        team_id: Optional[str] = None,
        state: Optional[ProjectState] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get Linear projects with optional filtering.
        
        Args:
            team_id: Optional team ID to filter by
            state: Optional project state to filter by
            limit: Maximum number of projects to return
            offset: Offset for pagination
            
        Returns:
            List of projects
            
        Raises:
            LinearAPIError: If the API request fails
        """
        # Define the GraphQL query
        query = """
        query GetProjects($filter: ProjectFilter, $first: Int, $after: String) {
          projects(filter: $filter, first: $first, after: $after, orderBy: { createdAt: DESC }) {
            nodes {
              id
              name
              description
              url
              state
              icon
              color
              startDate
              targetDate
              completedAt
              createdAt
              updatedAt
              team {
                id
                name
              }
              members {
                nodes {
                  id
                  name
                }
              }
              issues {
                totalCount
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        # Build filter
        filter_vars = {}
        if team_id:
            filter_vars["team"] = {"id": {"eq": team_id}}
        if state:
            filter_vars["state"] = {"eq": state.value}
        
        variables = {
            "filter": filter_vars,
            "first": limit,
        }
        
        if offset > 0:
            # Linear uses cursor-based pagination, so we need to get the cursor for the offset
            variables["after"] = f"offset:{offset}"
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("projects", {}).get("nodes"):
                return []
            
            return result["projects"]["nodes"]
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear projects: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear projects: {e}")
            raise LinearAPIError(f"Unexpected error getting projects: {e}")

    async def delete_project(self, project_id: str) -> bool:
        """
        Delete a Linear project.
        
        Args:
            project_id: ID of the project to delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the project is not found
        """
        # Define the GraphQL mutation
        mutation = """
        mutation DeleteProject($id: String!) {
          projectDelete(id: $id) {
            success
          }
        }
        """
        
        variables = {
            "id": project_id,
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("projectDelete", {}).get("success", False)
        
        except NotFoundError:
            logger.error(f"Project not found: {project_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error deleting Linear project: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error deleting Linear project: {e}")
            raise LinearAPIError(f"Unexpected error deleting project: {e}")

    async def add_issue_to_project(self, project_id: str, issue_id: str) -> bool:
        """
        Add an issue to a project.
        
        Args:
            project_id: ID of the project
            issue_id: ID of the issue to add
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the project or issue is not found
        """
        # Define the GraphQL mutation
        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
          }
        }
        """
        
        variables = {
            "id": issue_id,
            "input": {
                "projectId": project_id,
            }
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("issueUpdate", {}).get("success", False)
        
        except NotFoundError:
            logger.error(f"Project or issue not found: {project_id}, {issue_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error adding issue to project: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error adding issue to project: {e}")
            raise LinearAPIError(f"Unexpected error adding issue to project: {e}")

    async def remove_issue_from_project(self, issue_id: str) -> bool:
        """
        Remove an issue from its project.
        
        Args:
            issue_id: ID of the issue to remove from project
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue is not found
        """
        # Define the GraphQL mutation
        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
          }
        }
        """
        
        variables = {
            "id": issue_id,
            "input": {
                "projectId": None,
            }
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("issueUpdate", {}).get("success", False)
        
        except NotFoundError:
            logger.error(f"Issue not found: {issue_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error removing issue from project: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error removing issue from project: {e}")
            raise LinearAPIError(f"Unexpected error removing issue from project: {e}")

    async def get_project_milestones(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get milestones for a Linear project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            List of milestones
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the project is not found
        """
        # Define the GraphQL query
        query = """
        query GetProjectMilestones($id: String!) {
          project(id: $id) {
            milestones {
              nodes {
                id
                name
                description
                targetDate
                state
                createdAt
                updatedAt
              }
            }
          }
        }
        """
        
        variables = {
            "id": project_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("project"):
                raise NotFoundError(f"Project not found: {project_id}")
            
            return result["project"]["milestones"]["nodes"]
        
        except NotFoundError:
            logger.error(f"Project not found: {project_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting project milestones: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting project milestones: {e}")
            raise LinearAPIError(f"Unexpected error getting project milestones: {e}")
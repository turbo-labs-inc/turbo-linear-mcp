"""
Linear label resource module.

This module provides functionality for interacting with Linear labels and custom fields.
"""

from typing import Any, Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from src.linear.client import LinearClient
from src.utils.errors import LinearAPIError, NotFoundError, ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LabelCreateInput(BaseModel):
    """Input for creating a Linear label."""

    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    team_id: Optional[str] = None
    parent_id: Optional[str] = None


class LabelUpdateInput(BaseModel):
    """Input for updating a Linear label."""

    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    team_id: Optional[str] = None
    parent_id: Optional[str] = None


class CustomFieldCreateInput(BaseModel):
    """Input for creating a Linear custom field."""

    name: str
    description: Optional[str] = None
    team_id: str
    type: str  # text, number, date, single_select, multi_select, link, checkbox
    options: Optional[List[Dict[str, str]]] = None  # For select types: [{"label": "Option 1", "value": "option_1"}]
    required: Optional[bool] = None


class CustomFieldUpdateInput(BaseModel):
    """Input for updating a Linear custom field."""

    name: Optional[str] = None
    description: Optional[str] = None
    options: Optional[List[Dict[str, str]]] = None
    required: Optional[bool] = None


class LinearLabelClient:
    """
    Client for interacting with Linear labels.
    
    This class provides methods for creating, updating, and querying Linear labels.
    """

    def __init__(self, linear_client: LinearClient):
        """
        Initialize the Linear label client.
        
        Args:
            linear_client: Linear API client
        """
        self.client = linear_client
        logger.info("Linear label client initialized")

    async def create_label(self, input_data: LabelCreateInput) -> Dict[str, Any]:
        """
        Create a new Linear label.
        
        Args:
            input_data: Label creation input
            
        Returns:
            Created label data
            
        Raises:
            LinearAPIError: If the API request fails
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation CreateLabel($input: IssueLabelCreateInput!) {
          issueLabelCreate(input: $input) {
            success
            issueLabel {
              id
              name
              description
              color
              createdAt
              updatedAt
              team {
                id
                name
              }
              parent {
                id
                name
              }
              children {
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
                "description": input_data.description,
                "color": input_data.color,
                "teamId": input_data.team_id,
                "parentId": input_data.parent_id,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("issueLabelCreate", {}).get("success"):
                raise LinearAPIError("Failed to create label")
            
            return result["issueLabelCreate"]["issueLabel"]
        
        except LinearAPIError as e:
            logger.error(f"Error creating Linear label: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error creating Linear label: {e}")
            raise LinearAPIError(f"Unexpected error creating label: {e}")

    async def update_label(self, label_id: str, input_data: LabelUpdateInput) -> Dict[str, Any]:
        """
        Update an existing Linear label.
        
        Args:
            label_id: ID of the label to update
            input_data: Label update input
            
        Returns:
            Updated label data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the label is not found
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation UpdateLabel($id: String!, $input: IssueLabelUpdateInput!) {
          issueLabelUpdate(id: $id, input: $input) {
            success
            issueLabel {
              id
              name
              description
              color
              createdAt
              updatedAt
              team {
                id
                name
              }
              parent {
                id
                name
              }
              children {
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
            "id": label_id,
            "input": {
                "name": input_data.name,
                "description": input_data.description,
                "color": input_data.color,
                "teamId": input_data.team_id,
                "parentId": input_data.parent_id,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("issueLabelUpdate", {}).get("success"):
                raise LinearAPIError("Failed to update label")
            
            return result["issueLabelUpdate"]["issueLabel"]
        
        except NotFoundError:
            logger.error(f"Label not found: {label_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error updating Linear label: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error updating Linear label: {e}")
            raise LinearAPIError(f"Unexpected error updating label: {e}")

    async def get_label(self, label_id: str) -> Dict[str, Any]:
        """
        Get a Linear label by ID.
        
        Args:
            label_id: ID of the label to retrieve
            
        Returns:
            Label data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the label is not found
        """
        # Define the GraphQL query
        query = """
        query GetLabel($id: String!) {
          issueLabel(id: $id) {
            id
            name
            description
            color
            createdAt
            updatedAt
            team {
              id
              name
            }
            parent {
              id
              name
            }
            children {
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
        """
        
        variables = {
            "id": label_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("issueLabel"):
                raise NotFoundError(f"Label not found: {label_id}")
            
            return result["issueLabel"]
        
        except NotFoundError:
            logger.error(f"Label not found: {label_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear label: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear label: {e}")
            raise LinearAPIError(f"Unexpected error getting label: {e}")

    async def get_labels(
        self, team_id: Optional[str] = None, parent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get Linear labels with optional filtering.
        
        Args:
            team_id: Optional team ID to filter by
            parent_id: Optional parent label ID to filter by
            
        Returns:
            List of labels
            
        Raises:
            LinearAPIError: If the API request fails
        """
        # Define the GraphQL query
        query = """
        query GetLabels($filter: IssueLabelFilter) {
          issueLabels(filter: $filter) {
            nodes {
              id
              name
              description
              color
              createdAt
              updatedAt
              team {
                id
                name
              }
              parent {
                id
                name
              }
              children {
                totalCount
              }
            }
          }
        }
        """
        
        # Build filter
        filter_vars = {}
        if team_id:
            filter_vars["team"] = {"id": {"eq": team_id}}
        if parent_id:
            filter_vars["parent"] = {"id": {"eq": parent_id}}
        
        variables = {
            "filter": filter_vars,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("issueLabels", {}).get("nodes"):
                return []
            
            return result["issueLabels"]["nodes"]
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear labels: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear labels: {e}")
            raise LinearAPIError(f"Unexpected error getting labels: {e}")

    async def delete_label(self, label_id: str) -> bool:
        """
        Delete a Linear label.
        
        Args:
            label_id: ID of the label to delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the label is not found
        """
        # Define the GraphQL mutation
        mutation = """
        mutation DeleteLabel($id: String!) {
          issueLabelDelete(id: $id) {
            success
          }
        }
        """
        
        variables = {
            "id": label_id,
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("issueLabelDelete", {}).get("success", False)
        
        except NotFoundError:
            logger.error(f"Label not found: {label_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error deleting Linear label: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error deleting Linear label: {e}")
            raise LinearAPIError(f"Unexpected error deleting label: {e}")

    async def create_custom_field(self, input_data: CustomFieldCreateInput) -> Dict[str, Any]:
        """
        Create a new Linear custom field.
        
        Args:
            input_data: Custom field creation input
            
        Returns:
            Created custom field data
            
        Raises:
            LinearAPIError: If the API request fails
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation CreateCustomField($input: CustomFieldCreateInput!) {
          customFieldCreate(input: $input) {
            success
            customField {
              id
              name
              description
              type
              createdAt
              updatedAt
              team {
                id
                name
              }
              settings
              required
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        settings = {}
        if input_data.options and input_data.type in ["single_select", "multi_select"]:
            settings["options"] = input_data.options
        
        variables = {
            "input": {
                "name": input_data.name,
                "description": input_data.description,
                "teamId": input_data.team_id,
                "type": input_data.type,
                "settings": settings,
                "required": input_data.required,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("customFieldCreate", {}).get("success"):
                raise LinearAPIError("Failed to create custom field")
            
            return result["customFieldCreate"]["customField"]
        
        except LinearAPIError as e:
            logger.error(f"Error creating Linear custom field: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error creating Linear custom field: {e}")
            raise LinearAPIError(f"Unexpected error creating custom field: {e}")

    async def update_custom_field(
        self, field_id: str, input_data: CustomFieldUpdateInput
    ) -> Dict[str, Any]:
        """
        Update an existing Linear custom field.
        
        Args:
            field_id: ID of the custom field to update
            input_data: Custom field update input
            
        Returns:
            Updated custom field data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the custom field is not found
            ValidationError: If the input data is invalid
        """
        # Define the GraphQL mutation
        mutation = """
        mutation UpdateCustomField($id: String!, $input: CustomFieldUpdateInput!) {
          customFieldUpdate(id: $id, input: $input) {
            success
            customField {
              id
              name
              description
              type
              createdAt
              updatedAt
              team {
                id
                name
              }
              settings
              required
            }
          }
        }
        """
        
        # Convert input data to GraphQL format
        settings = {}
        if input_data.options:
            settings["options"] = input_data.options
        
        variables = {
            "id": field_id,
            "input": {
                "name": input_data.name,
                "description": input_data.description,
                "settings": settings if settings else None,
                "required": input_data.required,
            }
        }
        
        # Remove None values
        variables["input"] = {k: v for k, v in variables["input"].items() if v is not None}
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            if not result.get("customFieldUpdate", {}).get("success"):
                raise LinearAPIError("Failed to update custom field")
            
            return result["customFieldUpdate"]["customField"]
        
        except NotFoundError:
            logger.error(f"Custom field not found: {field_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error updating Linear custom field: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error updating Linear custom field: {e}")
            raise LinearAPIError(f"Unexpected error updating custom field: {e}")

    async def get_custom_field(self, field_id: str) -> Dict[str, Any]:
        """
        Get a Linear custom field by ID.
        
        Args:
            field_id: ID of the custom field to retrieve
            
        Returns:
            Custom field data
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the custom field is not found
        """
        # Define the GraphQL query
        query = """
        query GetCustomField($id: String!) {
          customField(id: $id) {
            id
            name
            description
            type
            createdAt
            updatedAt
            team {
              id
              name
            }
            settings
            required
          }
        }
        """
        
        variables = {
            "id": field_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            if not result.get("customField"):
                raise NotFoundError(f"Custom field not found: {field_id}")
            
            return result["customField"]
        
        except NotFoundError:
            logger.error(f"Custom field not found: {field_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting Linear custom field: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting Linear custom field: {e}")
            raise LinearAPIError(f"Unexpected error getting custom field: {e}")

    async def get_team_custom_fields(self, team_id: str) -> List[Dict[str, Any]]:
        """
        Get custom fields for a team.
        
        Args:
            team_id: ID of the team
            
        Returns:
            List of custom fields
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the team is not found
        """
        # Define the GraphQL query
        query = """
        query GetTeamCustomFields($teamId: String!) {
          customFields(filter: {team: {id: {eq: $teamId}}}) {
            nodes {
              id
              name
              description
              type
              createdAt
              updatedAt
              team {
                id
                name
              }
              settings
              required
            }
          }
        }
        """
        
        variables = {
            "teamId": team_id,
        }
        
        try:
            # Execute the query
            result = await self.client.execute_query(query, variables)
            
            return result.get("customFields", {}).get("nodes", [])
        
        except LinearAPIError as e:
            logger.error(f"Error getting team custom fields: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting team custom fields: {e}")
            raise LinearAPIError(f"Unexpected error getting team custom fields: {e}")

    async def delete_custom_field(self, field_id: str) -> bool:
        """
        Delete a Linear custom field.
        
        Args:
            field_id: ID of the custom field to delete
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the custom field is not found
        """
        # Define the GraphQL mutation
        mutation = """
        mutation DeleteCustomField($id: String!) {
          customFieldDelete(id: $id) {
            success
          }
        }
        """
        
        variables = {
            "id": field_id,
        }
        
        try:
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("customFieldDelete", {}).get("success", False)
        
        except NotFoundError:
            logger.error(f"Custom field not found: {field_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error deleting Linear custom field: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error deleting Linear custom field: {e}")
            raise LinearAPIError(f"Unexpected error deleting custom field: {e}")

    async def get_issue_labels(self, issue_id: str) -> List[Dict[str, Any]]:
        """
        Get labels for an issue.
        
        Args:
            issue_id: ID of the issue
            
        Returns:
            List of labels
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue is not found
        """
        # Define the GraphQL query
        query = """
        query GetIssueLabels($id: String!) {
          issue(id: $id) {
            labels {
              nodes {
                id
                name
                description
                color
                createdAt
                updatedAt
                team {
                  id
                  name
                }
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
            
            return result["issue"]["labels"]["nodes"]
        
        except NotFoundError:
            logger.error(f"Issue not found: {issue_id}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error getting issue labels: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error getting issue labels: {e}")
            raise LinearAPIError(f"Unexpected error getting issue labels: {e}")

    async def add_label_to_issue(self, issue_id: str, label_id: str) -> bool:
        """
        Add a label to an issue.
        
        Args:
            issue_id: ID of the issue
            label_id: ID of the label to add
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue or label is not found
        """
        # First get current labels
        try:
            issue_labels = await self.get_issue_labels(issue_id)
            label_ids = [label["id"] for label in issue_labels]
            
            # Add new label if not already present
            if label_id not in label_ids:
                label_ids.append(label_id)
            
            # Update issue with new labels
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
                    "labelIds": label_ids,
                }
            }
            
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("issueUpdate", {}).get("success", False)
        
        except NotFoundError as e:
            logger.error(f"Error adding label to issue: {e}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error adding label to issue: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error adding label to issue: {e}")
            raise LinearAPIError(f"Unexpected error adding label to issue: {e}")

    async def remove_label_from_issue(self, issue_id: str, label_id: str) -> bool:
        """
        Remove a label from an issue.
        
        Args:
            issue_id: ID of the issue
            label_id: ID of the label to remove
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            LinearAPIError: If the API request fails
            NotFoundError: If the issue or label is not found
        """
        # First get current labels
        try:
            issue_labels = await self.get_issue_labels(issue_id)
            label_ids = [label["id"] for label in issue_labels if label["id"] != label_id]
            
            # Update issue with new labels
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
                    "labelIds": label_ids,
                }
            }
            
            # Execute the mutation
            result = await self.client.execute_query(mutation, variables)
            
            return result.get("issueUpdate", {}).get("success", False)
        
        except NotFoundError as e:
            logger.error(f"Error removing label from issue: {e}")
            raise
        
        except LinearAPIError as e:
            logger.error(f"Error removing label from issue: {e}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error removing label from issue: {e}")
            raise LinearAPIError(f"Unexpected error removing label from issue: {e}")
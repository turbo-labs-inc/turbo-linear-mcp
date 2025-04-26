"""
Search query builder for Linear resources.

This module provides functionality for building search queries for Linear resources.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, validator

from src.utils.errors import ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ResourceType(str, Enum):
    """Types of Linear resources that can be searched."""

    ISSUE = "issue"
    PROJECT = "project"
    TEAM = "team"
    USER = "user"
    COMMENT = "comment"
    LABEL = "label"
    CYCLE = "cycle"
    WORKFLOW_STATE = "workflowState"


class Operator(str, Enum):
    """Operators for search conditions."""

    EQUALS = "eq"
    NOT_EQUALS = "neq"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUALS = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUALS = "lte"
    IN = "in"
    NOT_IN = "not_in"
    IS = "is"
    IS_NOT = "is_not"


class Condition(BaseModel):
    """Model for a search condition."""

    field: str
    operator: Operator
    value: Any
    
    @validator("value")
    def validate_value(cls, v: Any, values: Dict[str, Any]) -> Any:
        """Validate that the value is appropriate for the operator."""
        operator = values.get("operator")
        
        if operator in (Operator.IN, Operator.NOT_IN) and not isinstance(v, list):
            raise ValueError(f"Value for {operator} operator must be a list")
        
        return v


class SortDirection(str, Enum):
    """Sort directions for search results."""

    ASC = "asc"
    DESC = "desc"


class SortOption(BaseModel):
    """Model for a sort option."""

    field: str
    direction: SortDirection = SortDirection.ASC


class SearchQuery(BaseModel):
    """Model for a search query."""

    conditions: List[Condition] = Field(default_factory=list)
    resource_types: List[ResourceType] = Field(default_factory=list)
    sort: Optional[SortOption] = None
    limit: int = 50
    offset: int = 0
    
    @validator("resource_types")
    def validate_resource_types(cls, v: List[ResourceType]) -> List[ResourceType]:
        """Validate that at least one resource type is specified."""
        if not v:
            raise ValueError("At least one resource type must be specified")
        return v
    
    @validator("limit")
    def validate_limit(cls, v: int) -> int:
        """Validate that the limit is within a reasonable range."""
        if v < 1:
            raise ValueError("Limit must be at least 1")
        if v > 100:
            raise ValueError("Limit cannot exceed 100")
        return v
    
    @validator("offset")
    def validate_offset(cls, v: int) -> int:
        """Validate that the offset is non-negative."""
        if v < 0:
            raise ValueError("Offset cannot be negative")
        return v


class QueryBuilder:
    """
    Builder for Linear search queries.
    
    This class provides utilities for building search queries for Linear resources.
    """

    def __init__(self):
        """Initialize the query builder."""
        # Field mappings for different resource types
        self.field_mappings = {
            ResourceType.ISSUE: {
                "title": "title",
                "description": "description",
                "identifier": "identifier",
                "priority": "priority",
                "estimate": "estimate",
                "state": "state.name",
                "team": "team.name",
                "project": "project.name",
                "assignee": "assignee.name",
                "creator": "creator.name",
                "created_at": "createdAt",
                "updated_at": "updatedAt",
                "due_date": "dueDate",
                "completed_at": "completedAt",
                "label": "labels.nodes.name",
                "parent": "parent.title",
            },
            ResourceType.PROJECT: {
                "name": "name",
                "description": "description",
                "state": "state",
                "team": "team.name",
                "created_at": "createdAt",
                "updated_at": "updatedAt",
                "start_date": "startDate",
                "target_date": "targetDate",
                "completed_at": "completedAt",
            },
            ResourceType.TEAM: {
                "name": "name",
                "key": "key",
                "description": "description",
                "created_at": "createdAt",
                "updated_at": "updatedAt",
            },
            ResourceType.USER: {
                "name": "name",
                "email": "email",
                "display_name": "displayName",
                "active": "active",
                "created_at": "createdAt",
                "updated_at": "updatedAt",
                "last_seen": "lastSeen",
            },
            ResourceType.COMMENT: {
                "body": "body",
                "issue": "issue.title",
                "user": "user.name",
                "created_at": "createdAt",
                "updated_at": "updatedAt",
            },
            ResourceType.LABEL: {
                "name": "name",
                "description": "description",
                "team": "team.name",
                "created_at": "createdAt",
                "updated_at": "updatedAt",
            },
            ResourceType.CYCLE: {
                "name": "name",
                "description": "description",
                "team": "team.name",
                "created_at": "createdAt",
                "updated_at": "updatedAt",
                "starts_at": "startsAt",
                "ends_at": "endsAt",
            },
            ResourceType.WORKFLOW_STATE: {
                "name": "name",
                "description": "description",
                "team": "team.name",
                "type": "type",
                "created_at": "createdAt",
                "updated_at": "updatedAt",
            },
        }
        
        logger.info("Query builder initialized")

    def build_graphql_filter(
        self, resource_type: ResourceType, conditions: List[Condition]
    ) -> Dict[str, Any]:
        """
        Build a GraphQL filter for a resource type.
        
        Args:
            resource_type: Type of resource to filter
            conditions: List of conditions to apply
            
        Returns:
            GraphQL filter dictionary
            
        Raises:
            ValidationError: If a field is not supported for the resource type
        """
        filter_dict = {}
        
        for condition in conditions:
            # Map the field to the appropriate GraphQL field
            field_mapping = self.field_mappings.get(resource_type, {})
            if condition.field not in field_mapping:
                raise ValidationError(
                    f"Field '{condition.field}' is not supported for resource type '{resource_type}'"
                )
            
            graphql_field = field_mapping[condition.field]
            
            # Handle nested fields
            if "." in graphql_field:
                parts = graphql_field.split(".")
                current_dict = filter_dict
                
                for i, part in enumerate(parts[:-1]):
                    if part not in current_dict:
                        current_dict[part] = {}
                    
                    # Special case for nodes in connections
                    if part == "nodes":
                        current_dict = current_dict[part]
                        if "some" not in current_dict:
                            current_dict["some"] = {}
                        current_dict = current_dict["some"]
                    else:
                        current_dict = current_dict[part]
                
                # Set the condition value
                field_name = parts[-1]
                if field_name not in current_dict:
                    current_dict[field_name] = {}
                
                current_dict[field_name] = self._build_condition_value(condition)
            else:
                # Direct field
                if graphql_field not in filter_dict:
                    filter_dict[graphql_field] = {}
                
                filter_dict[graphql_field] = self._build_condition_value(condition)
        
        return filter_dict

    def _build_condition_value(self, condition: Condition) -> Dict[str, Any]:
        """
        Build a condition value for a GraphQL filter.
        
        Args:
            condition: Condition to convert
            
        Returns:
            GraphQL condition dictionary
            
        Raises:
            ValidationError: If the operator is not supported
        """
        value = condition.value
        
        # Handle date values
        if isinstance(value, datetime):
            value = value.isoformat()
        
        # Map operator to GraphQL filter
        if condition.operator == Operator.EQUALS:
            return {"eq": value}
        elif condition.operator == Operator.NOT_EQUALS:
            return {"neq": value}
        elif condition.operator == Operator.CONTAINS:
            return {"contains": value}
        elif condition.operator == Operator.NOT_CONTAINS:
            return {"notContains": value}
        elif condition.operator == Operator.STARTS_WITH:
            return {"startsWith": value}
        elif condition.operator == Operator.ENDS_WITH:
            return {"endsWith": value}
        elif condition.operator == Operator.GREATER_THAN:
            return {"gt": value}
        elif condition.operator == Operator.GREATER_THAN_OR_EQUALS:
            return {"gte": value}
        elif condition.operator == Operator.LESS_THAN:
            return {"lt": value}
        elif condition.operator == Operator.LESS_THAN_OR_EQUALS:
            return {"lte": value}
        elif condition.operator == Operator.IN:
            return {"in": value}
        elif condition.operator == Operator.NOT_IN:
            return {"nin": value}
        elif condition.operator == Operator.IS:
            return {"eq": value}
        elif condition.operator == Operator.IS_NOT:
            return {"neq": value}
        else:
            raise ValidationError(f"Unsupported operator: {condition.operator}")

    def parse_query_string(self, query_string: str) -> SearchQuery:
        """
        Parse a query string into a search query.
        
        Args:
            query_string: Query string to parse
            
        Returns:
            Parsed search query
            
        Raises:
            ValidationError: If the query string is invalid
        """
        # Extract resource types
        resource_types = []
        type_match = re.search(r"type:([\w,]+)", query_string)
        if type_match:
            type_str = type_match.group(1)
            for type_name in type_str.split(","):
                try:
                    resource_types.append(ResourceType(type_name.strip().lower()))
                except ValueError:
                    raise ValidationError(f"Invalid resource type: {type_name}")
            
            # Remove the type: clause from the query
            query_string = re.sub(r"type:[\w,]+", "", query_string)
        else:
            # Default to all resource types
            resource_types = [
                ResourceType.ISSUE,
                ResourceType.PROJECT,
                ResourceType.TEAM,
                ResourceType.USER,
                ResourceType.COMMENT,
                ResourceType.LABEL,
                ResourceType.CYCLE,
                ResourceType.WORKFLOW_STATE,
            ]
        
        # Extract limit
        limit = 50
        limit_match = re.search(r"limit:(\d+)", query_string)
        if limit_match:
            limit = int(limit_match.group(1))
            
            # Remove the limit: clause from the query
            query_string = re.sub(r"limit:\d+", "", query_string)
        
        # Extract sort
        sort = None
        sort_match = re.search(r"sort:([a-zA-Z_]+)(?::(asc|desc))?", query_string)
        if sort_match:
            sort_field = sort_match.group(1)
            sort_direction = sort_match.group(2) or "asc"
            
            sort = SortOption(
                field=sort_field,
                direction=SortDirection(sort_direction),
            )
            
            # Remove the sort: clause from the query
            query_string = re.sub(r"sort:[a-zA-Z_]+(?::(asc|desc))?", "", query_string)
        
        # Extract field-specific conditions
        conditions = []
        field_matches = re.finditer(r"(\w+):([\w\s\-\.]+)", query_string)
        for match in field_matches:
            field = match.group(1)
            value = match.group(2).strip()
            
            # Determine operator based on value
            operator = Operator.EQUALS
            condition_value = value
            
            # Check for operator prefixes
            if value.startswith(">"):
                operator = Operator.GREATER_THAN
                condition_value = value[1:].strip()
            elif value.startswith(">="):
                operator = Operator.GREATER_THAN_OR_EQUALS
                condition_value = value[2:].strip()
            elif value.startswith("<"):
                operator = Operator.LESS_THAN
                condition_value = value[1:].strip()
            elif value.startswith("<="):
                operator = Operator.LESS_THAN_OR_EQUALS
                condition_value = value[2:].strip()
            elif value.startswith("!"):
                operator = Operator.NOT_EQUALS
                condition_value = value[1:].strip()
            
            conditions.append(
                Condition(
                    field=field,
                    operator=operator,
                    value=condition_value,
                )
            )
            
            # Remove the field: clause from the query
            query_string = re.sub(f"{field}:{re.escape(value)}", "", query_string)
        
        # Any remaining text is a general search
        text_search = query_string.strip()
        if text_search:
            # Generate multiple conditions for text search across common fields
            # These will be combined with OR in the search engine
            # For now, just add a single condition on title or name
            # Actual implementation would handle this more comprehensively
            conditions.append(
                Condition(
                    field="title" if ResourceType.ISSUE in resource_types else "name",
                    operator=Operator.CONTAINS,
                    value=text_search,
                )
            )
        
        return SearchQuery(
            conditions=conditions,
            resource_types=resource_types,
            sort=sort,
            limit=limit,
        )

    def build_graphql_query(
        self, resource_type: ResourceType, filter_dict: Dict[str, Any], query: SearchQuery
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build a GraphQL query for a resource type.
        
        Args:
            resource_type: Type of resource to query
            filter_dict: GraphQL filter dictionary
            query: Search query parameters
            
        Returns:
            Tuple of (query_string, variables)
        """
        # Define the fields to retrieve for each resource type
        fields = {
            ResourceType.ISSUE: """
                id
                title
                description
                identifier
                url
                priority
                estimate
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
                createdAt
                updatedAt
                dueDate
                completedAt
            """,
            ResourceType.PROJECT: """
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
                  key
                }
            """,
            ResourceType.TEAM: """
                id
                name
                key
                description
                icon
                color
                createdAt
                updatedAt
            """,
            ResourceType.USER: """
                id
                name
                email
                displayName
                avatarUrl
                active
                createdAt
                updatedAt
                lastSeen
            """,
            ResourceType.COMMENT: """
                id
                body
                url
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
                createdAt
                updatedAt
            """,
            ResourceType.LABEL: """
                id
                name
                description
                color
                createdAt
                updatedAt
                team {
                  id
                  name
                  key
                }
            """,
            ResourceType.CYCLE: """
                id
                name
                description
                number
                startsAt
                endsAt
                progress
                createdAt
                updatedAt
                team {
                  id
                  name
                  key
                }
            """,
            ResourceType.WORKFLOW_STATE: """
                id
                name
                description
                color
                type
                position
                createdAt
                updatedAt
                team {
                  id
                  name
                  key
                }
            """,
        }
        
        # Map resource type to GraphQL query name
        query_name = {
            ResourceType.ISSUE: "issues",
            ResourceType.PROJECT: "projects",
            ResourceType.TEAM: "teams",
            ResourceType.USER: "users",
            ResourceType.COMMENT: "comments",
            ResourceType.LABEL: "issueLabels",
            ResourceType.CYCLE: "cycles",
            ResourceType.WORKFLOW_STATE: "workflowStates",
        }[resource_type]
        
        # Build sort input
        sort_input = ""
        if query.sort:
            # Map field to GraphQL field
            field_mapping = self.field_mappings.get(resource_type, {})
            if query.sort.field in field_mapping:
                sort_field = field_mapping[query.sort.field]
                sort_direction = query.sort.direction.value
                sort_input = f", orderBy: {{ {sort_field}: {sort_direction} }}"
            else:
                logger.warning(
                    f"Sort field '{query.sort.field}' not supported for resource type '{resource_type}'"
                )
        
        # Build pagination input
        pagination_input = f", first: {query.limit}"
        if query.offset > 0:
            pagination_input += f", after: \"offset:{query.offset}\""
        
        # Build the query
        query_string = f"""
        query Search($filter: {resource_type.value.capitalize()}Filter) {{
          {query_name}(filter: $filter{sort_input}{pagination_input}) {{
            nodes {{
              {fields[resource_type]}
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
            totalCount
          }}
        }}
        """
        
        variables = {
            "filter": filter_dict,
        }
        
        return query_string, variables
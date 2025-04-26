"""
Search query validation.

This module provides functionality for validating search queries
to ensure they are properly formatted and within allowed limits.
"""

import re
from typing import Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, validator

from src.search.query import FilterOperator, ResourceType, SearchCondition, SearchQuery
from src.utils.errors import ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationRule(BaseModel):
    """Model for a validation rule."""
    
    field: str
    allowed_operators: Optional[List[FilterOperator]] = None
    allowed_values: Optional[List[str]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    pattern: Optional[str] = None
    required: bool = False
    error_message: Optional[str] = None


class ResourceTypeRules(BaseModel):
    """Rules for a specific resource type."""
    
    allowed_fields: List[str]
    field_rules: Dict[str, ValidationRule] = Field(default_factory=dict)


class QueryValidator(BaseModel):
    """
    Validator for search queries.
    
    This class provides validation for search queries to ensure
    they are properly formatted and within allowed limits.
    """
    
    # Maximum query parameters
    max_query_length: int = 1000
    max_conditions: int = 10
    max_resource_types: int = 5
    
    # Common rules applied to all resource types
    common_rules: Dict[str, ValidationRule] = Field(default_factory=dict)
    
    # Resource type specific rules
    resource_type_rules: Dict[ResourceType, ResourceTypeRules] = Field(default_factory=dict)
    
    # Banned patterns in query text
    banned_patterns: List[str] = []
    
    # Banned terms in query text
    banned_terms: List[str] = []
    
    class Config:
        """Pydantic configuration."""
        
        arbitrary_types_allowed = True
    
    def __init__(self, **data):
        """Initialize with default rules if not provided."""
        super().__init__(**data)
        
        # Set up default rules if none provided
        if not self.common_rules:
            self._set_default_common_rules()
        
        if not self.resource_type_rules:
            self._set_default_resource_type_rules()
        
        logger.info("Query validator initialized")
    
    def _set_default_common_rules(self):
        """Set default common validation rules."""
        self.common_rules = {
            "title": ValidationRule(
                field="title",
                allowed_operators=[
                    FilterOperator.EQUALS,
                    FilterOperator.CONTAINS,
                    FilterOperator.STARTS_WITH,
                ],
                pattern=r"^[a-zA-Z0-9\s\-_\.,;:!?'\(\)]{1,100}$",
                error_message="Title must be 1-100 characters and contain only alphanumeric and common punctuation",
            ),
            "description": ValidationRule(
                field="description",
                allowed_operators=[
                    FilterOperator.CONTAINS,
                ],
                error_message="Description only supports the 'contains' operator",
            ),
            "created_at": ValidationRule(
                field="created_at",
                allowed_operators=[
                    FilterOperator.EQUALS,
                    FilterOperator.GREATER_THAN,
                    FilterOperator.LESS_THAN,
                    FilterOperator.GREATER_THAN_OR_EQUALS,
                    FilterOperator.LESS_THAN_OR_EQUALS,
                ],
                pattern=r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$",
                error_message="Date format must be YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ",
            ),
            "updated_at": ValidationRule(
                field="updated_at",
                allowed_operators=[
                    FilterOperator.EQUALS,
                    FilterOperator.GREATER_THAN,
                    FilterOperator.LESS_THAN,
                    FilterOperator.GREATER_THAN_OR_EQUALS,
                    FilterOperator.LESS_THAN_OR_EQUALS,
                ],
                pattern=r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$",
                error_message="Date format must be YYYY-MM-DD or YYYY-MM-DDThh:mm:ssZ",
            ),
        }
    
    def _set_default_resource_type_rules(self):
        """Set default resource type specific validation rules."""
        # Issue-specific rules
        self.resource_type_rules[ResourceType.ISSUE] = ResourceTypeRules(
            allowed_fields=[
                "title", "description", "created_at", "updated_at",
                "state", "priority", "estimate", "assignee", "team",
                "project", "labels", "identifier",
            ],
            field_rules={
                "priority": ValidationRule(
                    field="priority",
                    allowed_operators=[
                        FilterOperator.EQUALS,
                        FilterOperator.GREATER_THAN,
                        FilterOperator.LESS_THAN,
                    ],
                    allowed_values=["0", "1", "2", "3", "4"],
                    error_message="Priority must be 0-4 (0=no priority, 1=urgent, 2=high, 3=medium, 4=low)",
                ),
                "estimate": ValidationRule(
                    field="estimate",
                    allowed_operators=[
                        FilterOperator.EQUALS,
                        FilterOperator.GREATER_THAN,
                        FilterOperator.LESS_THAN,
                    ],
                    min_value=0,
                    max_value=100,
                    error_message="Estimate must be a number between 0 and 100",
                ),
                "state": ValidationRule(
                    field="state",
                    allowed_operators=[FilterOperator.EQUALS],
                    error_message="State only supports the 'equals' operator",
                ),
                "assignee": ValidationRule(
                    field="assignee",
                    allowed_operators=[FilterOperator.EQUALS],
                    error_message="Assignee only supports the 'equals' operator",
                ),
                "team": ValidationRule(
                    field="team",
                    allowed_operators=[FilterOperator.EQUALS],
                    error_message="Team only supports the 'equals' operator",
                ),
                "project": ValidationRule(
                    field="project",
                    allowed_operators=[FilterOperator.EQUALS],
                    error_message="Project only supports the 'equals' operator",
                ),
                "labels": ValidationRule(
                    field="labels",
                    allowed_operators=[FilterOperator.EQUALS, FilterOperator.CONTAINS],
                    error_message="Labels support 'equals' and 'contains' operators",
                ),
                "identifier": ValidationRule(
                    field="identifier",
                    allowed_operators=[
                        FilterOperator.EQUALS,
                        FilterOperator.STARTS_WITH,
                    ],
                    pattern=r"^[A-Z]{1,10}-\d{1,10}$",
                    error_message="Identifier must be in format PROJ-123",
                ),
            },
        )
        
        # Project-specific rules
        self.resource_type_rules[ResourceType.PROJECT] = ResourceTypeRules(
            allowed_fields=[
                "title", "description", "created_at", "updated_at",
                "state", "team", "start_date", "target_date",
            ],
            field_rules={
                "state": ValidationRule(
                    field="state",
                    allowed_operators=[FilterOperator.EQUALS],
                    error_message="State only supports the 'equals' operator",
                ),
                "team": ValidationRule(
                    field="team",
                    allowed_operators=[FilterOperator.EQUALS],
                    error_message="Team only supports the 'equals' operator",
                ),
                "start_date": ValidationRule(
                    field="start_date",
                    allowed_operators=[
                        FilterOperator.EQUALS,
                        FilterOperator.GREATER_THAN,
                        FilterOperator.LESS_THAN,
                    ],
                    pattern=r"^\d{4}-\d{2}-\d{2}$",
                    error_message="Start date must be in format YYYY-MM-DD",
                ),
                "target_date": ValidationRule(
                    field="target_date",
                    allowed_operators=[
                        FilterOperator.EQUALS,
                        FilterOperator.GREATER_THAN,
                        FilterOperator.LESS_THAN,
                    ],
                    pattern=r"^\d{4}-\d{2}-\d{2}$",
                    error_message="Target date must be in format YYYY-MM-DD",
                ),
            },
        )
        
        # Team-specific rules
        self.resource_type_rules[ResourceType.TEAM] = ResourceTypeRules(
            allowed_fields=[
                "title", "description", "created_at", "updated_at",
                "key",
            ],
            field_rules={
                "key": ValidationRule(
                    field="key",
                    allowed_operators=[
                        FilterOperator.EQUALS,
                        FilterOperator.STARTS_WITH,
                    ],
                    pattern=r"^[A-Z]{1,10}$",
                    error_message="Team key must be 1-10 uppercase letters",
                ),
            },
        )
        
        # User-specific rules
        self.resource_type_rules[ResourceType.USER] = ResourceTypeRules(
            allowed_fields=[
                "title", "created_at", "updated_at",
                "email", "display_name", "active",
            ],
            field_rules={
                "email": ValidationRule(
                    field="email",
                    allowed_operators=[
                        FilterOperator.EQUALS,
                        FilterOperator.CONTAINS,
                    ],
                    pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                    error_message="Email must be a valid email address",
                ),
                "display_name": ValidationRule(
                    field="display_name",
                    allowed_operators=[
                        FilterOperator.EQUALS,
                        FilterOperator.CONTAINS,
                    ],
                    error_message="Display name supports 'equals' and 'contains' operators",
                ),
                "active": ValidationRule(
                    field="active",
                    allowed_operators=[FilterOperator.EQUALS],
                    allowed_values=["true", "false"],
                    error_message="Active must be 'true' or 'false'",
                ),
            },
        )
    
    def validate_query_text(self, query_text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate the query text string.
        
        Args:
            query_text: Query text to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query_text:
            return True, None
        
        # Check query length
        if len(query_text) > self.max_query_length:
            return False, f"Query text exceeds maximum length of {self.max_query_length} characters"
        
        # Check for banned patterns
        for pattern in self.banned_patterns:
            if re.search(pattern, query_text, re.IGNORECASE):
                return False, f"Query contains disallowed pattern: {pattern}"
        
        # Check for banned terms
        for term in self.banned_terms:
            if term.lower() in query_text.lower():
                return False, f"Query contains disallowed term: {term}"
        
        return True, None
    
    def validate_condition(
        self, condition: SearchCondition, resource_types: List[ResourceType]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a search condition.
        
        Args:
            condition: Search condition to validate
            resource_types: Resource types the condition is applied to
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if field exists in common rules
        if condition.field in self.common_rules:
            rule = self.common_rules[condition.field]
            return self._validate_condition_against_rule(condition, rule)
        
        # Check if field exists in any of the resource type rules
        valid_field = False
        for resource_type in resource_types:
            if resource_type not in self.resource_type_rules:
                continue
            
            resource_rules = self.resource_type_rules[resource_type]
            
            if condition.field in resource_rules.allowed_fields:
                valid_field = True
                
                # If there's a specific rule for this field, validate against it
                if condition.field in resource_rules.field_rules:
                    rule = resource_rules.field_rules[condition.field]
                    is_valid, error = self._validate_condition_against_rule(condition, rule)
                    if not is_valid:
                        return False, error
        
        if not valid_field:
            # Find valid fields for error message
            valid_fields = set(self.common_rules.keys())
            for resource_type in resource_types:
                if resource_type in self.resource_type_rules:
                    valid_fields.update(self.resource_type_rules[resource_type].allowed_fields)
            
            return False, f"Field '{condition.field}' is not valid for the selected resource types. Valid fields: {', '.join(sorted(valid_fields))}"
        
        return True, None
    
    def _validate_condition_against_rule(
        self, condition: SearchCondition, rule: ValidationRule
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a condition against a specific rule.
        
        Args:
            condition: Search condition to validate
            rule: Validation rule to apply
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check operator
        if rule.allowed_operators and condition.operator not in rule.allowed_operators:
            allowed_ops = [op.value for op in rule.allowed_operators]
            return False, rule.error_message or f"Field '{rule.field}' does not support operator '{condition.operator.value}'. Allowed operators: {', '.join(allowed_ops)}"
        
        # Check against allowed values
        if rule.allowed_values and str(condition.value) not in rule.allowed_values:
            return False, rule.error_message or f"Field '{rule.field}' with operator '{condition.operator.value}' does not allow value '{condition.value}'. Allowed values: {', '.join(rule.allowed_values)}"
        
        # Check numeric range
        if rule.min_value is not None or rule.max_value is not None:
            try:
                num_value = float(condition.value)
                if rule.min_value is not None and num_value < rule.min_value:
                    return False, rule.error_message or f"Value for '{rule.field}' must be at least {rule.min_value}"
                if rule.max_value is not None and num_value > rule.max_value:
                    return False, rule.error_message or f"Value for '{rule.field}' must be at most {rule.max_value}"
            except (ValueError, TypeError):
                return False, rule.error_message or f"Value for '{rule.field}' must be a number"
        
        # Check pattern
        if rule.pattern and isinstance(condition.value, str):
            if not re.match(rule.pattern, condition.value):
                return False, rule.error_message or f"Value for '{rule.field}' does not match required format"
        
        return True, None
    
    def validate_query(self, query: SearchQuery) -> Tuple[bool, List[str]]:
        """
        Validate a search query.
        
        Args:
            query: Search query to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate query text
        is_valid, error = self.validate_query_text(query.text)
        if not is_valid:
            errors.append(error)
        
        # Check resource type count
        if len(query.resource_types) > self.max_resource_types:
            errors.append(f"Query exceeds maximum of {self.max_resource_types} resource types")
        
        # Check condition count
        if len(query.conditions) > self.max_conditions:
            errors.append(f"Query exceeds maximum of {self.max_conditions} conditions")
        
        # Validate each condition
        for condition in query.conditions:
            is_valid, error = self.validate_condition(condition, query.resource_types)
            if not is_valid:
                errors.append(error)
        
        return len(errors) == 0, errors
    
    def validate_and_raise(self, query: SearchQuery) -> None:
        """
        Validate a query and raise an exception if invalid.
        
        Args:
            query: Search query to validate
            
        Raises:
            ValidationError: If the query is invalid
        """
        is_valid, errors = self.validate_query(query)
        if not is_valid:
            raise ValidationError(
                message="Invalid search query",
                details={"errors": errors}
            )
    
    def get_allowed_fields(self, resource_type: ResourceType) -> List[Dict[str, str]]:
        """
        Get allowed fields for a resource type.
        
        Args:
            resource_type: Resource type to get fields for
            
        Returns:
            List of field information dictionaries
        """
        fields = []
        
        # Add common fields
        for field, rule in self.common_rules.items():
            fields.append({
                "name": field,
                "operators": [op.value for op in (rule.allowed_operators or list(FilterOperator))],
                "description": rule.error_message or "",
            })
        
        # Add resource-specific fields
        if resource_type in self.resource_type_rules:
            resource_rules = self.resource_type_rules[resource_type]
            
            for field in resource_rules.allowed_fields:
                # Skip fields already added from common rules
                if any(f["name"] == field for f in fields):
                    continue
                
                # Get operators from specific rule or default to all
                operators = list(FilterOperator)
                description = ""
                
                if field in resource_rules.field_rules:
                    rule = resource_rules.field_rules[field]
                    if rule.allowed_operators:
                        operators = rule.allowed_operators
                    description = rule.error_message or ""
                
                fields.append({
                    "name": field,
                    "operators": [op.value for op in operators],
                    "description": description,
                })
        
        return fields
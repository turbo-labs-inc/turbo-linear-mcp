"""
Complex filter combinations for search queries.

This module provides functionality for creating and validating complex
filter combinations, including logical operators (AND, OR, NOT) and
grouping of conditions.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union, Any

from pydantic import BaseModel, Field, root_validator, validator

from src.search.query import FilterOperator, ResourceType, SearchCondition
from src.utils.errors import ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class LogicalOperator(str, Enum):
    """Logical operators for combining conditions."""
    
    AND = "and"
    OR = "or"
    NOT = "not"


class FilterNode(BaseModel):
    """Base class for all filter nodes."""
    
    def to_graphql(self) -> Dict[str, Any]:
        """
        Convert the filter node to a GraphQL filter.
        
        Must be implemented by subclasses.
        
        Returns:
            GraphQL filter dictionary
        """
        raise NotImplementedError("Subclasses must implement to_graphql")
    
    def to_string(self) -> str:
        """
        Convert the filter node to a human-readable string.
        
        Must be implemented by subclasses.
        
        Returns:
            Human-readable string representation
        """
        raise NotImplementedError("Subclasses must implement to_string")


class ConditionNode(FilterNode):
    """A node representing a single search condition."""
    
    condition: SearchCondition
    
    def to_graphql(self) -> Dict[str, Any]:
        """
        Convert the condition to a GraphQL filter.
        
        Returns:
            GraphQL filter dictionary
        """
        field = self.condition.field
        operator = self.condition.operator
        value = self.condition.value
        
        # Handle special operators that need transformation
        if operator == FilterOperator.CONTAINS:
            return {field: {"contains": value}}
        elif operator == FilterOperator.STARTS_WITH:
            return {field: {"startsWith": value}}
        elif operator == FilterOperator.ENDS_WITH:
            return {field: {"endsWith": value}}
        elif operator == FilterOperator.EQUALS:
            return {field: {"eq": value}}
        elif operator == FilterOperator.NOT_EQUALS:
            return {field: {"neq": value}}
        elif operator == FilterOperator.GREATER_THAN:
            return {field: {"gt": value}}
        elif operator == FilterOperator.LESS_THAN:
            return {field: {"lt": value}}
        elif operator == FilterOperator.GREATER_THAN_OR_EQUALS:
            return {field: {"gte": value}}
        elif operator == FilterOperator.LESS_THAN_OR_EQUALS:
            return {field: {"lte": value}}
        elif operator == FilterOperator.IN:
            # Split comma-separated values
            values = [v.strip() for v in value.split(",")] if isinstance(value, str) else value
            return {field: {"in": values}}
        elif operator == FilterOperator.NOT_IN:
            # Split comma-separated values
            values = [v.strip() for v in value.split(",")] if isinstance(value, str) else value
            return {field: {"nin": values}}
        elif operator == FilterOperator.IS_NULL:
            return {field: {"null": True if value in [True, "true", 1, "1"] else False}}
        else:
            # Default to equality
            return {field: {"eq": value}}
    
    def to_string(self) -> str:
        """
        Convert the condition to a human-readable string.
        
        Returns:
            Human-readable string representation
        """
        field = self.condition.field
        operator = self.condition.operator
        value = self.condition.value
        
        # Format value based on type
        if isinstance(value, str):
            # Add quotes for strings
            formatted_value = f'"{value}"'
        elif value is None:
            formatted_value = "null"
        elif isinstance(value, bool):
            formatted_value = str(value).lower()
        else:
            formatted_value = str(value)
        
        # Map operators to human-readable format
        operator_map = {
            FilterOperator.CONTAINS: "contains",
            FilterOperator.STARTS_WITH: "starts with",
            FilterOperator.ENDS_WITH: "ends with",
            FilterOperator.EQUALS: "=",
            FilterOperator.NOT_EQUALS: "≠",
            FilterOperator.GREATER_THAN: ">",
            FilterOperator.LESS_THAN: "<",
            FilterOperator.GREATER_THAN_OR_EQUALS: "≥",
            FilterOperator.LESS_THAN_OR_EQUALS: "≤",
            FilterOperator.IN: "in",
            FilterOperator.NOT_IN: "not in",
            FilterOperator.IS_NULL: "is null" if value else "is not null",
        }
        
        # Get operator string
        operator_str = operator_map.get(operator, str(operator))
        
        # For IS_NULL, we don't need to show the value
        if operator == FilterOperator.IS_NULL:
            return f"{field} {operator_str}"
        
        return f"{field} {operator_str} {formatted_value}"


class LogicalNode(FilterNode):
    """A node representing a logical operation on other nodes."""
    
    operator: LogicalOperator
    children: List[FilterNode]
    
    @validator("children")
    def validate_children(cls, children, values):
        """Validate that there are enough children for the operator."""
        operator = values.get("operator")
        
        if not operator:
            return children
        
        if operator == LogicalOperator.NOT and len(children) != 1:
            raise ValueError("NOT operator must have exactly one child")
        
        if operator in [LogicalOperator.AND, LogicalOperator.OR] and len(children) < 2:
            raise ValueError(f"{operator.value.upper()} operator must have at least two children")
        
        return children
    
    def to_graphql(self) -> Dict[str, Any]:
        """
        Convert the logical operation to a GraphQL filter.
        
        Returns:
            GraphQL filter dictionary
        """
        if self.operator == LogicalOperator.AND:
            return {"and": [child.to_graphql() for child in self.children]}
        elif self.operator == LogicalOperator.OR:
            return {"or": [child.to_graphql() for child in self.children]}
        elif self.operator == LogicalOperator.NOT:
            # NOT only has one child
            return {"not": self.children[0].to_graphql()}
        else:
            raise ValueError(f"Unknown logical operator: {self.operator}")
    
    def to_string(self) -> str:
        """
        Convert the logical operation to a human-readable string.
        
        Returns:
            Human-readable string representation
        """
        if self.operator == LogicalOperator.NOT:
            # NOT only has one child
            child_str = self.children[0].to_string()
            return f"NOT ({child_str})"
        
        # Join children with the operator
        operator_str = f" {self.operator.value.upper()} "
        child_strings = [child.to_string() for child in self.children]
        
        # Add parentheses around each child if it's a logical node
        for i, child in enumerate(self.children):
            if isinstance(child, LogicalNode):
                child_strings[i] = f"({child_strings[i]})"
        
        return operator_str.join(child_strings)


class FilterGroup(BaseModel):
    """A group of filter nodes, combined with a logical operator."""
    
    root: FilterNode
    
    @classmethod
    def from_conditions(cls, conditions: List[SearchCondition], operator: LogicalOperator = LogicalOperator.AND) -> "FilterGroup":
        """
        Create a filter group from a list of search conditions.
        
        Args:
            conditions: List of search conditions
            operator: Logical operator to combine conditions with
            
        Returns:
            Filter group
        """
        if not conditions:
            raise ValueError("Cannot create filter group with no conditions")
        
        if len(conditions) == 1:
            # Single condition, no need for a logical node
            return cls(root=ConditionNode(condition=conditions[0]))
        
        # Multiple conditions, create a logical node
        condition_nodes = [ConditionNode(condition=condition) for condition in conditions]
        return cls(root=LogicalNode(operator=operator, children=condition_nodes))
    
    def to_graphql(self) -> Dict[str, Any]:
        """
        Convert the filter group to a GraphQL filter.
        
        Returns:
            GraphQL filter dictionary
        """
        return self.root.to_graphql()
    
    def to_string(self) -> str:
        """
        Convert the filter group to a human-readable string.
        
        Returns:
            Human-readable string representation
        """
        return self.root.to_string()
    
    def and_with(self, other: Union["FilterGroup", SearchCondition]) -> "FilterGroup":
        """
        Combine this filter group with another using AND.
        
        Args:
            other: Filter group or search condition to combine with
            
        Returns:
            New filter group
        """
        if isinstance(other, SearchCondition):
            other_node = ConditionNode(condition=other)
        elif isinstance(other, FilterGroup):
            other_node = other.root
        else:
            raise TypeError("other must be a FilterGroup or SearchCondition")
        
        # If this group's root is already an AND, add the other node to it
        if isinstance(self.root, LogicalNode) and self.root.operator == LogicalOperator.AND:
            new_children = self.root.children + [other_node]
            return FilterGroup(root=LogicalNode(operator=LogicalOperator.AND, children=new_children))
        
        # Otherwise, create a new AND node
        return FilterGroup(root=LogicalNode(operator=LogicalOperator.AND, children=[self.root, other_node]))
    
    def or_with(self, other: Union["FilterGroup", SearchCondition]) -> "FilterGroup":
        """
        Combine this filter group with another using OR.
        
        Args:
            other: Filter group or search condition to combine with
            
        Returns:
            New filter group
        """
        if isinstance(other, SearchCondition):
            other_node = ConditionNode(condition=other)
        elif isinstance(other, FilterGroup):
            other_node = other.root
        else:
            raise TypeError("other must be a FilterGroup or SearchCondition")
        
        # If this group's root is already an OR, add the other node to it
        if isinstance(self.root, LogicalNode) and self.root.operator == LogicalOperator.OR:
            new_children = self.root.children + [other_node]
            return FilterGroup(root=LogicalNode(operator=LogicalOperator.OR, children=new_children))
        
        # Otherwise, create a new OR node
        return FilterGroup(root=LogicalNode(operator=LogicalOperator.OR, children=[self.root, other_node]))
    
    def not_filter(self) -> "FilterGroup":
        """
        Negate this filter group.
        
        Returns:
            New filter group with NOT applied
        """
        return FilterGroup(root=LogicalNode(operator=LogicalOperator.NOT, children=[self.root]))


class FilterBuilder:
    """Builder for creating complex filter combinations."""
    
    @staticmethod
    def condition(field: str, operator: FilterOperator, value: Any) -> FilterGroup:
        """
        Create a filter group with a single condition.
        
        Args:
            field: Field to filter on
            operator: Filter operator
            value: Filter value
            
        Returns:
            Filter group
        """
        condition = SearchCondition(field=field, operator=operator, value=value)
        return FilterGroup(root=ConditionNode(condition=condition))
    
    @staticmethod
    def and_filters(*filters: Union[FilterGroup, SearchCondition]) -> FilterGroup:
        """
        Combine multiple filters with AND.
        
        Args:
            *filters: Filters to combine
            
        Returns:
            Filter group
        """
        if not filters:
            raise ValueError("Cannot create AND filter with no children")
        
        # Convert all to FilterNodes
        nodes = []
        for f in filters:
            if isinstance(f, SearchCondition):
                nodes.append(ConditionNode(condition=f))
            elif isinstance(f, FilterGroup):
                nodes.append(f.root)
            else:
                raise TypeError("Filters must be FilterGroups or SearchConditions")
        
        return FilterGroup(root=LogicalNode(operator=LogicalOperator.AND, children=nodes))
    
    @staticmethod
    def or_filters(*filters: Union[FilterGroup, SearchCondition]) -> FilterGroup:
        """
        Combine multiple filters with OR.
        
        Args:
            *filters: Filters to combine
            
        Returns:
            Filter group
        """
        if not filters:
            raise ValueError("Cannot create OR filter with no children")
        
        # Convert all to FilterNodes
        nodes = []
        for f in filters:
            if isinstance(f, SearchCondition):
                nodes.append(ConditionNode(condition=f))
            elif isinstance(f, FilterGroup):
                nodes.append(f.root)
            else:
                raise TypeError("Filters must be FilterGroups or SearchConditions")
        
        return FilterGroup(root=LogicalNode(operator=LogicalOperator.OR, children=nodes))
    
    @staticmethod
    def not_filter(filter_obj: Union[FilterGroup, SearchCondition]) -> FilterGroup:
        """
        Negate a filter.
        
        Args:
            filter_obj: Filter to negate
            
        Returns:
            Filter group
        """
        if isinstance(filter_obj, SearchCondition):
            node = ConditionNode(condition=filter_obj)
        elif isinstance(filter_obj, FilterGroup):
            node = filter_obj.root
        else:
            raise TypeError("Filter must be a FilterGroup or SearchCondition")
        
        return FilterGroup(root=LogicalNode(operator=LogicalOperator.NOT, children=[node]))
    
    @staticmethod
    def parse_query_string(query_string: str) -> FilterGroup:
        """
        Parse a query string into a filter group.
        
        This is a simple implementation that supports basic AND/OR combinations.
        For more complex queries, a proper query parser would be needed.
        
        Args:
            query_string: Query string to parse
            
        Returns:
            Filter group
        
        Example:
            "title:issue AND state:open OR state:in_progress"
            "(priority:1 OR priority:2) AND state:open"
        """
        # TODO: Implement a more robust query parser
        # For now, we'll just use the existing parser in the query builder
        raise NotImplementedError("Complex query string parsing is not yet implemented")
    
    @staticmethod
    def from_dict(filter_dict: Dict[str, Any]) -> FilterGroup:
        """
        Create a filter group from a dictionary representation.
        
        Args:
            filter_dict: Dictionary representation of a filter
            
        Returns:
            Filter group
        
        Example:
            {
                "and": [
                    {"field": "title", "operator": "contains", "value": "issue"},
                    {"field": "state", "operator": "equals", "value": "open"}
                ]
            }
        """
        # Check if it's a simple condition
        if "field" in filter_dict and "operator" in filter_dict and "value" in filter_dict:
            condition = SearchCondition(
                field=filter_dict["field"],
                operator=FilterOperator(filter_dict["operator"]),
                value=filter_dict["value"],
            )
            return FilterGroup(root=ConditionNode(condition=condition))
        
        # Check for logical operators
        for op in ["and", "or", "not"]:
            if op in filter_dict:
                if op == "not":
                    # NOT only has one child
                    child = FilterBuilder.from_dict(filter_dict[op])
                    return FilterGroup(
                        root=LogicalNode(
                            operator=LogicalOperator.NOT,
                            children=[child.root],
                        )
                    )
                else:
                    # AND/OR have multiple children
                    children = [
                        FilterBuilder.from_dict(child).root
                        for child in filter_dict[op]
                    ]
                    return FilterGroup(
                        root=LogicalNode(
                            operator=LogicalOperator(op),
                            children=children,
                        )
                    )
        
        raise ValueError(f"Invalid filter dictionary: {filter_dict}")
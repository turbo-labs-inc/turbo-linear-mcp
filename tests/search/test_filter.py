"""
Tests for the complex filter combinations.
"""

import unittest

from src.search.filter import (
    ConditionNode,
    FilterBuilder,
    FilterGroup,
    LogicalNode,
    LogicalOperator,
)
from src.search.query import FilterOperator, SearchCondition


class TestFilterNodes(unittest.TestCase):
    """Tests for filter nodes."""

    def test_condition_node(self):
        """Test condition node conversion."""
        # Test simple equality condition
        condition = SearchCondition(
            field="title",
            operator=FilterOperator.EQUALS,
            value="test",
        )
        node = ConditionNode(condition=condition)
        
        # Test GraphQL conversion
        graphql = node.to_graphql()
        self.assertEqual(graphql, {"title": {"eq": "test"}})
        
        # Test string conversion
        string = node.to_string()
        self.assertEqual(string, 'title = "test"')
        
        # Test with different operators
        condition = SearchCondition(
            field="priority",
            operator=FilterOperator.GREATER_THAN,
            value=1,
        )
        node = ConditionNode(condition=condition)
        
        graphql = node.to_graphql()
        self.assertEqual(graphql, {"priority": {"gt": 1}})
        
        string = node.to_string()
        self.assertEqual(string, "priority > 1")
        
        # Test IN operator with comma-separated string
        condition = SearchCondition(
            field="state",
            operator=FilterOperator.IN,
            value="open,in_progress,review",
        )
        node = ConditionNode(condition=condition)
        
        graphql = node.to_graphql()
        self.assertEqual(graphql, {"state": {"in": ["open", "in_progress", "review"]}})
        
        string = node.to_string()
        self.assertEqual(string, 'state in "open,in_progress,review"')
        
        # Test IS_NULL operator
        condition = SearchCondition(
            field="assignee",
            operator=FilterOperator.IS_NULL,
            value=True,
        )
        node = ConditionNode(condition=condition)
        
        graphql = node.to_graphql()
        self.assertEqual(graphql, {"assignee": {"null": True}})
        
        string = node.to_string()
        self.assertEqual(string, "assignee is null")

    def test_logical_node(self):
        """Test logical node conversion."""
        # Create condition nodes
        condition1 = SearchCondition(
            field="title",
            operator=FilterOperator.CONTAINS,
            value="test",
        )
        node1 = ConditionNode(condition=condition1)
        
        condition2 = SearchCondition(
            field="state",
            operator=FilterOperator.EQUALS,
            value="open",
        )
        node2 = ConditionNode(condition=condition2)
        
        # Test AND operator
        and_node = LogicalNode(
            operator=LogicalOperator.AND,
            children=[node1, node2],
        )
        
        graphql = and_node.to_graphql()
        self.assertEqual(graphql, {
            "and": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
            ]
        })
        
        string = and_node.to_string()
        self.assertEqual(string, 'title contains "test" AND state = "open"')
        
        # Test OR operator
        or_node = LogicalNode(
            operator=LogicalOperator.OR,
            children=[node1, node2],
        )
        
        graphql = or_node.to_graphql()
        self.assertEqual(graphql, {
            "or": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
            ]
        })
        
        string = or_node.to_string()
        self.assertEqual(string, 'title contains "test" OR state = "open"')
        
        # Test NOT operator
        not_node = LogicalNode(
            operator=LogicalOperator.NOT,
            children=[node1],
        )
        
        graphql = not_node.to_graphql()
        self.assertEqual(graphql, {"not": {"title": {"contains": "test"}}})
        
        string = not_node.to_string()
        self.assertEqual(string, 'NOT (title contains "test")')
        
        # Test nested logical nodes
        nested_node = LogicalNode(
            operator=LogicalOperator.AND,
            children=[
                node1,
                LogicalNode(
                    operator=LogicalOperator.OR,
                    children=[node2, node2],  # Using the same node twice for simplicity
                ),
            ],
        )
        
        graphql = nested_node.to_graphql()
        self.assertEqual(graphql, {
            "and": [
                {"title": {"contains": "test"}},
                {"or": [
                    {"state": {"eq": "open"}},
                    {"state": {"eq": "open"}},
                ]},
            ]
        })
        
        string = nested_node.to_string()
        self.assertEqual(string, 'title contains "test" AND (state = "open" OR state = "open")')

    def test_filter_group(self):
        """Test filter group creation and conversion."""
        # Create from conditions
        conditions = [
            SearchCondition(
                field="title",
                operator=FilterOperator.CONTAINS,
                value="test",
            ),
            SearchCondition(
                field="state",
                operator=FilterOperator.EQUALS,
                value="open",
            ),
        ]
        
        group = FilterGroup.from_conditions(conditions)
        
        # Check root node
        self.assertIsInstance(group.root, LogicalNode)
        self.assertEqual(group.root.operator, LogicalOperator.AND)
        self.assertEqual(len(group.root.children), 2)
        
        # Test to_graphql
        graphql = group.to_graphql()
        self.assertEqual(graphql, {
            "and": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
            ]
        })
        
        # Test to_string
        string = group.to_string()
        self.assertEqual(string, 'title contains "test" AND state = "open"')
        
        # Test from single condition
        group = FilterGroup.from_conditions([conditions[0]])
        self.assertIsInstance(group.root, ConditionNode)
        
        # Test using OR operator
        group = FilterGroup.from_conditions(conditions, LogicalOperator.OR)
        self.assertEqual(group.root.operator, LogicalOperator.OR)


class TestFilterGroupOperations(unittest.TestCase):
    """Tests for filter group operations."""

    def setUp(self):
        """Set up test fixtures."""
        self.condition1 = SearchCondition(
            field="title",
            operator=FilterOperator.CONTAINS,
            value="test",
        )
        self.condition2 = SearchCondition(
            field="state",
            operator=FilterOperator.EQUALS,
            value="open",
        )
        self.condition3 = SearchCondition(
            field="priority",
            operator=FilterOperator.GREATER_THAN,
            value=1,
        )
        
        self.group1 = FilterGroup.from_conditions([self.condition1])
        self.group2 = FilterGroup.from_conditions([self.condition2])

    def test_and_with(self):
        """Test AND operation."""
        # Test with condition
        combined = self.group1.and_with(self.condition2)
        
        # Check result
        self.assertIsInstance(combined.root, LogicalNode)
        self.assertEqual(combined.root.operator, LogicalOperator.AND)
        self.assertEqual(len(combined.root.children), 2)
        
        # Test with filter group
        combined = self.group1.and_with(self.group2)
        
        # Check result
        self.assertIsInstance(combined.root, LogicalNode)
        self.assertEqual(combined.root.operator, LogicalOperator.AND)
        self.assertEqual(len(combined.root.children), 2)
        
        # Test chaining with another condition
        combined = self.group1.and_with(self.condition2).and_with(self.condition3)
        
        # Check result
        self.assertIsInstance(combined.root, LogicalNode)
        self.assertEqual(combined.root.operator, LogicalOperator.AND)
        self.assertEqual(len(combined.root.children), 3)
        
        # Convert to GraphQL and check
        graphql = combined.to_graphql()
        self.assertEqual(graphql, {
            "and": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
                {"priority": {"gt": 1}},
            ]
        })

    def test_or_with(self):
        """Test OR operation."""
        # Test with condition
        combined = self.group1.or_with(self.condition2)
        
        # Check result
        self.assertIsInstance(combined.root, LogicalNode)
        self.assertEqual(combined.root.operator, LogicalOperator.OR)
        self.assertEqual(len(combined.root.children), 2)
        
        # Test with filter group
        combined = self.group1.or_with(self.group2)
        
        # Check result
        self.assertIsInstance(combined.root, LogicalNode)
        self.assertEqual(combined.root.operator, LogicalOperator.OR)
        self.assertEqual(len(combined.root.children), 2)
        
        # Test chaining with another condition
        combined = self.group1.or_with(self.condition2).or_with(self.condition3)
        
        # Check result
        self.assertIsInstance(combined.root, LogicalNode)
        self.assertEqual(combined.root.operator, LogicalOperator.OR)
        self.assertEqual(len(combined.root.children), 3)
        
        # Convert to GraphQL and check
        graphql = combined.to_graphql()
        self.assertEqual(graphql, {
            "or": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
                {"priority": {"gt": 1}},
            ]
        })

    def test_not_filter(self):
        """Test NOT operation."""
        # Test with simple condition
        negated = self.group1.not_filter()
        
        # Check result
        self.assertIsInstance(negated.root, LogicalNode)
        self.assertEqual(negated.root.operator, LogicalOperator.NOT)
        self.assertEqual(len(negated.root.children), 1)
        
        # Test with combined conditions
        combined = self.group1.and_with(self.condition2)
        negated = combined.not_filter()
        
        # Check result
        self.assertIsInstance(negated.root, LogicalNode)
        self.assertEqual(negated.root.operator, LogicalOperator.NOT)
        self.assertEqual(len(negated.root.children), 1)
        
        # Convert to GraphQL and check
        graphql = negated.to_graphql()
        self.assertEqual(graphql, {
            "not": {
                "and": [
                    {"title": {"contains": "test"}},
                    {"state": {"eq": "open"}},
                ]
            }
        })
        
        # Convert to string and check
        string = negated.to_string()
        self.assertEqual(string, 'NOT (title contains "test" AND state = "open")')

    def test_mixed_operations(self):
        """Test mixed operations."""
        # Create (condition1 AND condition2) OR condition3
        combined = self.group1.and_with(self.condition2).or_with(self.condition3)
        
        # Check GraphQL
        graphql = combined.to_graphql()
        expected = {
            "or": [
                {
                    "and": [
                        {"title": {"contains": "test"}},
                        {"state": {"eq": "open"}},
                    ]
                },
                {"priority": {"gt": 1}},
            ]
        }
        self.assertEqual(graphql, expected)
        
        # Create condition1 AND (condition2 OR condition3)
        group2_or_3 = FilterGroup.from_conditions(
            [self.condition2, self.condition3],
            LogicalOperator.OR,
        )
        combined = self.group1.and_with(group2_or_3)
        
        # Check GraphQL
        graphql = combined.to_graphql()
        expected = {
            "and": [
                {"title": {"contains": "test"}},
                {
                    "or": [
                        {"state": {"eq": "open"}},
                        {"priority": {"gt": 1}},
                    ]
                },
            ]
        }
        self.assertEqual(graphql, expected)
        
        # Check string representation
        string = combined.to_string()
        self.assertEqual(string, 'title contains "test" AND (state = "open" OR priority > 1)')


class TestFilterBuilder(unittest.TestCase):
    """Tests for the filter builder."""

    def test_condition(self):
        """Test creating a condition."""
        # Create a simple condition
        filter_group = FilterBuilder.condition("title", FilterOperator.CONTAINS, "test")
        
        # Check result
        self.assertIsInstance(filter_group, FilterGroup)
        self.assertIsInstance(filter_group.root, ConditionNode)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {"title": {"contains": "test"}})

    def test_and_filters(self):
        """Test AND combination."""
        # Create conditions
        condition1 = SearchCondition(
            field="title",
            operator=FilterOperator.CONTAINS,
            value="test",
        )
        condition2 = SearchCondition(
            field="state",
            operator=FilterOperator.EQUALS,
            value="open",
        )
        
        # Combine with AND
        filter_group = FilterBuilder.and_filters(condition1, condition2)
        
        # Check result
        self.assertIsInstance(filter_group, FilterGroup)
        self.assertIsInstance(filter_group.root, LogicalNode)
        self.assertEqual(filter_group.root.operator, LogicalOperator.AND)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {
            "and": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
            ]
        })
        
        # Test with filter groups
        group1 = FilterBuilder.condition("title", FilterOperator.CONTAINS, "test")
        group2 = FilterBuilder.condition("state", FilterOperator.EQUALS, "open")
        
        filter_group = FilterBuilder.and_filters(group1, group2)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {
            "and": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
            ]
        })

    def test_or_filters(self):
        """Test OR combination."""
        # Create conditions
        condition1 = SearchCondition(
            field="title",
            operator=FilterOperator.CONTAINS,
            value="test",
        )
        condition2 = SearchCondition(
            field="state",
            operator=FilterOperator.EQUALS,
            value="open",
        )
        
        # Combine with OR
        filter_group = FilterBuilder.or_filters(condition1, condition2)
        
        # Check result
        self.assertIsInstance(filter_group, FilterGroup)
        self.assertIsInstance(filter_group.root, LogicalNode)
        self.assertEqual(filter_group.root.operator, LogicalOperator.OR)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {
            "or": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
            ]
        })
        
        # Test with filter groups
        group1 = FilterBuilder.condition("title", FilterOperator.CONTAINS, "test")
        group2 = FilterBuilder.condition("state", FilterOperator.EQUALS, "open")
        
        filter_group = FilterBuilder.or_filters(group1, group2)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {
            "or": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
            ]
        })

    def test_not_filter(self):
        """Test NOT operation."""
        # Create a condition
        condition = SearchCondition(
            field="title",
            operator=FilterOperator.CONTAINS,
            value="test",
        )
        
        # Negate it
        filter_group = FilterBuilder.not_filter(condition)
        
        # Check result
        self.assertIsInstance(filter_group, FilterGroup)
        self.assertIsInstance(filter_group.root, LogicalNode)
        self.assertEqual(filter_group.root.operator, LogicalOperator.NOT)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {
            "not": {"title": {"contains": "test"}}
        })
        
        # Test with filter group
        group = FilterBuilder.condition("title", FilterOperator.CONTAINS, "test")
        filter_group = FilterBuilder.not_filter(group)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {
            "not": {"title": {"contains": "test"}}
        })

    def test_from_dict(self):
        """Test creating filters from dictionary."""
        # Test simple condition
        filter_dict = {
            "field": "title",
            "operator": "contains",
            "value": "test",
        }
        
        filter_group = FilterBuilder.from_dict(filter_dict)
        
        # Check result
        self.assertIsInstance(filter_group, FilterGroup)
        self.assertIsInstance(filter_group.root, ConditionNode)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {"title": {"contains": "test"}})
        
        # Test AND combination
        filter_dict = {
            "and": [
                {
                    "field": "title",
                    "operator": "contains",
                    "value": "test",
                },
                {
                    "field": "state",
                    "operator": "equals",
                    "value": "open",
                },
            ]
        }
        
        filter_group = FilterBuilder.from_dict(filter_dict)
        
        # Check result
        self.assertIsInstance(filter_group, FilterGroup)
        self.assertIsInstance(filter_group.root, LogicalNode)
        self.assertEqual(filter_group.root.operator, LogicalOperator.AND)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {
            "and": [
                {"title": {"contains": "test"}},
                {"state": {"eq": "open"}},
            ]
        })
        
        # Test nested structure
        filter_dict = {
            "and": [
                {
                    "field": "title",
                    "operator": "contains",
                    "value": "test",
                },
                {
                    "or": [
                        {
                            "field": "state",
                            "operator": "equals",
                            "value": "open",
                        },
                        {
                            "field": "state",
                            "operator": "equals",
                            "value": "in_progress",
                        },
                    ]
                },
            ]
        }
        
        filter_group = FilterBuilder.from_dict(filter_dict)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        expected = {
            "and": [
                {"title": {"contains": "test"}},
                {
                    "or": [
                        {"state": {"eq": "open"}},
                        {"state": {"eq": "in_progress"}},
                    ]
                },
            ]
        }
        self.assertEqual(graphql, expected)
        
        # Test NOT operator
        filter_dict = {
            "not": {
                "field": "title",
                "operator": "contains",
                "value": "test",
            }
        }
        
        filter_group = FilterBuilder.from_dict(filter_dict)
        
        # Check GraphQL
        graphql = filter_group.to_graphql()
        self.assertEqual(graphql, {
            "not": {"title": {"contains": "test"}}
        })
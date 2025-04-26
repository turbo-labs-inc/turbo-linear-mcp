"""
Tests for the search query validation.
"""

import unittest

from src.search.query import FilterOperator, ResourceType, SearchCondition, SearchQuery
from src.search.validation import QueryValidator, ValidationRule
from src.utils.errors import ValidationError


class TestQueryValidator(unittest.TestCase):
    """Tests for the search query validator."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = QueryValidator()
        
        # Create a valid query for testing
        self.valid_query = SearchQuery(
            text="test query",
            resource_types=[ResourceType.ISSUE, ResourceType.PROJECT],
            conditions=[
                SearchCondition(
                    field="title",
                    operator=FilterOperator.CONTAINS,
                    value="test",
                ),
                SearchCondition(
                    field="created_at",
                    operator=FilterOperator.GREATER_THAN,
                    value="2023-01-01",
                ),
            ],
        )

    def test_validate_query_text(self):
        """Test validation of query text."""
        # Test valid query text
        is_valid, error = self.validator.validate_query_text("test query")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test empty query text (valid)
        is_valid, error = self.validator.validate_query_text("")
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test query text that's too long
        long_text = "a" * (self.validator.max_query_length + 1)
        is_valid, error = self.validator.validate_query_text(long_text)
        self.assertFalse(is_valid)
        self.assertIn("exceeds maximum length", error)
        
        # Test query with banned terms
        self.validator.banned_terms = ["forbidden"]
        is_valid, error = self.validator.validate_query_text("This contains a forbidden term")
        self.assertFalse(is_valid)
        self.assertIn("disallowed term", error)
        
        # Test query with banned patterns
        self.validator.banned_patterns = [r"\bsql\b"]
        is_valid, error = self.validator.validate_query_text("This contains an sql injection")
        self.assertFalse(is_valid)
        self.assertIn("disallowed pattern", error)

    def test_validate_condition(self):
        """Test validation of search conditions."""
        # Test valid title condition
        condition = SearchCondition(
            field="title",
            operator=FilterOperator.CONTAINS,
            value="test",
        )
        is_valid, error = self.validator.validate_condition(
            condition, [ResourceType.ISSUE]
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Test invalid operator for title
        condition = SearchCondition(
            field="title",
            operator=FilterOperator.IN,  # Not allowed for title
            value="test",
        )
        is_valid, error = self.validator.validate_condition(
            condition, [ResourceType.ISSUE]
        )
        self.assertFalse(is_valid)
        self.assertIn("does not support operator", error)
        
        # Test invalid field
        condition = SearchCondition(
            field="nonexistent_field",
            operator=FilterOperator.EQUALS,
            value="test",
        )
        is_valid, error = self.validator.validate_condition(
            condition, [ResourceType.ISSUE]
        )
        self.assertFalse(is_valid)
        self.assertIn("not valid for the selected resource types", error)
        
        # Test field valid for one resource type but not another
        condition = SearchCondition(
            field="priority",  # Only valid for ISSUE
            operator=FilterOperator.EQUALS,
            value="1",
        )
        is_valid, error = self.validator.validate_condition(
            condition, [ResourceType.ISSUE]
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        is_valid, error = self.validator.validate_condition(
            condition, [ResourceType.USER]
        )
        self.assertFalse(is_valid)
        self.assertIn("not valid for the selected resource types", error)
        
        # Test valid for mixed resource types
        condition = SearchCondition(
            field="title",  # Valid for all resource types
            operator=FilterOperator.CONTAINS,
            value="test",
        )
        is_valid, error = self.validator.validate_condition(
            condition, [ResourceType.ISSUE, ResourceType.PROJECT, ResourceType.USER]
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)

    def test_validate_against_rule(self):
        """Test validation against specific rules."""
        # Test allowed values rule
        rule = ValidationRule(
            field="priority",
            allowed_operators=[FilterOperator.EQUALS],
            allowed_values=["0", "1", "2", "3", "4"],
        )
        
        condition = SearchCondition(
            field="priority",
            operator=FilterOperator.EQUALS,
            value="1",
        )
        is_valid, error = self.validator._validate_condition_against_rule(condition, rule)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        condition = SearchCondition(
            field="priority",
            operator=FilterOperator.EQUALS,
            value="5",  # Not in allowed values
        )
        is_valid, error = self.validator._validate_condition_against_rule(condition, rule)
        self.assertFalse(is_valid)
        self.assertIn("does not allow value", error)
        
        # Test min/max value rule
        rule = ValidationRule(
            field="estimate",
            allowed_operators=[FilterOperator.EQUALS],
            min_value=0,
            max_value=100,
        )
        
        condition = SearchCondition(
            field="estimate",
            operator=FilterOperator.EQUALS,
            value="50",
        )
        is_valid, error = self.validator._validate_condition_against_rule(condition, rule)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        condition = SearchCondition(
            field="estimate",
            operator=FilterOperator.EQUALS,
            value="150",  # Above max
        )
        is_valid, error = self.validator._validate_condition_against_rule(condition, rule)
        self.assertFalse(is_valid)
        self.assertIn("must be at most", error)
        
        condition = SearchCondition(
            field="estimate",
            operator=FilterOperator.EQUALS,
            value="-10",  # Below min
        )
        is_valid, error = self.validator._validate_condition_against_rule(condition, rule)
        self.assertFalse(is_valid)
        self.assertIn("must be at least", error)
        
        # Test pattern rule
        rule = ValidationRule(
            field="identifier",
            allowed_operators=[FilterOperator.EQUALS],
            pattern=r"^[A-Z]{1,10}-\d{1,10}$",
        )
        
        condition = SearchCondition(
            field="identifier",
            operator=FilterOperator.EQUALS,
            value="PROJ-123",
        )
        is_valid, error = self.validator._validate_condition_against_rule(condition, rule)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        condition = SearchCondition(
            field="identifier",
            operator=FilterOperator.EQUALS,
            value="invalid-format",
        )
        is_valid, error = self.validator._validate_condition_against_rule(condition, rule)
        self.assertFalse(is_valid)
        self.assertIn("does not match required format", error)

    def test_validate_query(self):
        """Test validation of a complete query."""
        # Test valid query
        is_valid, errors = self.validator.validate_query(self.valid_query)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Test query with too many resource types
        max_resource_types = self.validator.max_resource_types
        query = SearchQuery(
            text="test query",
            resource_types=[ResourceType.ISSUE] * (max_resource_types + 1),
        )
        is_valid, errors = self.validator.validate_query(query)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("maximum of", errors[0])
        
        # Test query with too many conditions
        max_conditions = self.validator.max_conditions
        conditions = [
            SearchCondition(
                field="title",
                operator=FilterOperator.CONTAINS,
                value="test",
            )
        ] * (max_conditions + 1)
        
        query = SearchQuery(
            text="test query",
            resource_types=[ResourceType.ISSUE],
            conditions=conditions,
        )
        is_valid, errors = self.validator.validate_query(query)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("maximum of", errors[0])
        
        # Test query with multiple errors
        query = SearchQuery(
            text="a" * (self.validator.max_query_length + 1),  # Too long
            resource_types=[ResourceType.ISSUE] * (max_resource_types + 1),  # Too many
            conditions=[
                SearchCondition(
                    field="invalid_field",  # Invalid field
                    operator=FilterOperator.EQUALS,
                    value="test",
                ),
            ],
        )
        is_valid, errors = self.validator.validate_query(query)
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 3)  # Three errors

    def test_validate_and_raise(self):
        """Test validation with exception raising."""
        # Test valid query (should not raise)
        try:
            self.validator.validate_and_raise(self.valid_query)
        except ValidationError:
            self.fail("validate_and_raise() raised ValidationError unexpectedly!")
        
        # Test invalid query (should raise)
        query = SearchQuery(
            text="test query",
            resource_types=[ResourceType.ISSUE],
            conditions=[
                SearchCondition(
                    field="invalid_field",
                    operator=FilterOperator.EQUALS,
                    value="test",
                ),
            ],
        )
        with self.assertRaises(ValidationError) as context:
            self.validator.validate_and_raise(query)
        
        # Check that error details are included
        self.assertIn("errors", context.exception.details)
        self.assertIsInstance(context.exception.details["errors"], list)
        self.assertGreater(len(context.exception.details["errors"]), 0)

    def test_get_allowed_fields(self):
        """Test getting allowed fields for a resource type."""
        # Test for ISSUE resource type
        fields = self.validator.get_allowed_fields(ResourceType.ISSUE)
        
        # Check that result is a list of dictionaries
        self.assertIsInstance(fields, list)
        self.assertTrue(all(isinstance(f, dict) for f in fields))
        
        # Check that each field has the required keys
        for field in fields:
            self.assertIn("name", field)
            self.assertIn("operators", field)
            self.assertIn("description", field)
        
        # Check that common fields are included
        self.assertTrue(any(f["name"] == "title" for f in fields))
        self.assertTrue(any(f["name"] == "description" for f in fields))
        
        # Check that issue-specific fields are included
        self.assertTrue(any(f["name"] == "priority" for f in fields))
        self.assertTrue(any(f["name"] == "estimate" for f in fields))
        
        # Test for USER resource type
        fields = self.validator.get_allowed_fields(ResourceType.USER)
        
        # Check that user-specific fields are included
        self.assertTrue(any(f["name"] == "email" for f in fields))
        self.assertTrue(any(f["name"] == "active" for f in fields))
        
        # Check that issue-specific fields are not included
        self.assertFalse(any(f["name"] == "priority" for f in fields))
        self.assertFalse(any(f["name"] == "estimate" for f in fields))
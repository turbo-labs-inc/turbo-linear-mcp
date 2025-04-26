"""
Feature list validation module.

This module provides functionality for validating feature lists.
"""

from typing import Dict, List, Optional, Set, Union

from pydantic import BaseModel, Field

from src.features.parser import (
    Feature,
    FeatureFormat,
    FeatureList,
    FeatureParser,
    FeaturePriority,
    FeatureType,
)
from src.utils.errors import ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationRule(BaseModel):
    """Model for a validation rule."""

    name: str
    description: str
    severity: str  # "error", "warning", "info"


class ValidationIssue(BaseModel):
    """Model for a validation issue."""

    rule: ValidationRule
    message: str
    index: Optional[int] = None  # Feature index
    field: Optional[str] = None  # Field name


class ValidationResult(BaseModel):
    """Model for a validation result."""

    valid: bool
    errors: List[ValidationIssue] = Field(default_factory=list)
    warnings: List[ValidationIssue] = Field(default_factory=list)
    info: List[ValidationIssue] = Field(default_factory=list)


class FeatureListValidator:
    """
    Validator for feature lists.
    
    This class provides functionality for validating feature lists against
    various rules.
    """

    # Define validation rules
    MISSING_TITLE = ValidationRule(
        name="missing_title",
        description="Feature must have a title",
        severity="error",
    )
    
    TITLE_TOO_SHORT = ValidationRule(
        name="title_too_short",
        description="Feature title is too short",
        severity="warning",
    )
    
    TITLE_TOO_LONG = ValidationRule(
        name="title_too_long",
        description="Feature title is too long",
        severity="warning",
    )
    
    MISSING_DESCRIPTION = ValidationRule(
        name="missing_description",
        description="Feature should have a description",
        severity="warning",
    )
    
    DESCRIPTION_TOO_SHORT = ValidationRule(
        name="description_too_short",
        description="Feature description is too short",
        severity="info",
    )
    
    DUPLICATED_FEATURE = ValidationRule(
        name="duplicated_feature",
        description="Feature title appears to be duplicated",
        severity="warning",
    )
    
    MISSING_PARENT = ValidationRule(
        name="missing_parent",
        description="Referenced parent feature not found in list",
        severity="error",
    )
    
    NO_FEATURES = ValidationRule(
        name="no_features",
        description="Feature list contains no features",
        severity="error",
    )
    
    EMPTY_FEATURE_LIST = ValidationRule(
        name="empty_feature_list",
        description="Feature list is empty",
        severity="error",
    )
    
    CIRCULAR_REFERENCE = ValidationRule(
        name="circular_reference",
        description="Feature has a circular parent reference",
        severity="error",
    )

    def __init__(
        self,
        min_title_length: int = 3,
        max_title_length: int = 100,
        min_description_length: int = 10,
    ):
        """
        Initialize the feature list validator.
        
        Args:
            min_title_length: Minimum title length
            max_title_length: Maximum title length
            min_description_length: Minimum description length
        """
        self.min_title_length = min_title_length
        self.max_title_length = max_title_length
        self.min_description_length = min_description_length
        logger.info("Feature list validator initialized")

    def validate_text(
        self, text: str, format: Optional[FeatureFormat] = None
    ) -> ValidationResult:
        """
        Validate a feature list from text.
        
        Args:
            text: Feature list text
            format: Optional format to use
            
        Returns:
            Validation result
        """
        if not text.strip():
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationIssue(
                        rule=self.EMPTY_FEATURE_LIST,
                        message="Feature list is empty",
                    )
                ],
            )
        
        try:
            feature_list = FeatureParser.parse(text, format)
            return self.validate_feature_list(feature_list)
        except ValidationError as e:
            return ValidationResult(
                valid=False,
                errors=[
                    ValidationIssue(
                        rule=self.EMPTY_FEATURE_LIST,
                        message=f"Failed to parse feature list: {e}",
                    )
                ],
            )

    def validate_feature_list(self, feature_list: FeatureList) -> ValidationResult:
        """
        Validate a feature list.
        
        Args:
            feature_list: Feature list to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        info = []
        
        # Check if feature list is empty
        if not feature_list.features:
            errors.append(
                ValidationIssue(
                    rule=self.NO_FEATURES,
                    message="Feature list contains no features",
                )
            )
            return ValidationResult(valid=False, errors=errors)
        
        # Check for duplicated titles
        title_counts = {}
        for i, feature in enumerate(feature_list.features):
            if feature.title in title_counts:
                title_counts[feature.title].append(i)
            else:
                title_counts[feature.title] = [i]
        
        for title, indices in title_counts.items():
            if len(indices) > 1:
                for i in indices[1:]:  # Skip first occurrence
                    warnings.append(
                        ValidationIssue(
                            rule=self.DUPLICATED_FEATURE,
                            message=f"Feature title '{title}' is duplicated",
                            index=i,
                            field="title",
                        )
                    )
        
        # Validate each feature
        for i, feature in enumerate(feature_list.features):
            # Check title
            if not feature.title:
                errors.append(
                    ValidationIssue(
                        rule=self.MISSING_TITLE,
                        message="Feature must have a title",
                        index=i,
                        field="title",
                    )
                )
            elif len(feature.title) < self.min_title_length:
                warnings.append(
                    ValidationIssue(
                        rule=self.TITLE_TOO_SHORT,
                        message=f"Feature title is too short (min {self.min_title_length} characters)",
                        index=i,
                        field="title",
                    )
                )
            elif len(feature.title) > self.max_title_length:
                warnings.append(
                    ValidationIssue(
                        rule=self.TITLE_TOO_LONG,
                        message=f"Feature title is too long (max {self.max_title_length} characters)",
                        index=i,
                        field="title",
                    )
                )
            
            # Check description
            if not feature.description:
                warnings.append(
                    ValidationIssue(
                        rule=self.MISSING_DESCRIPTION,
                        message="Feature should have a description",
                        index=i,
                        field="description",
                    )
                )
            elif (
                feature.description
                and len(feature.description) < self.min_description_length
            ):
                info.append(
                    ValidationIssue(
                        rule=self.DESCRIPTION_TOO_SHORT,
                        message=f"Feature description is quite short (min {self.min_description_length} characters recommended)",
                        index=i,
                        field="description",
                    )
                )
            
            # Check parent references
            if feature.metadata.parent:
                parent_found = False
                for other_feature in feature_list.features:
                    if other_feature.title == feature.metadata.parent:
                        parent_found = True
                        break
                
                if not parent_found:
                    errors.append(
                        ValidationIssue(
                            rule=self.MISSING_PARENT,
                            message=f"Referenced parent feature '{feature.metadata.parent}' not found in list",
                            index=i,
                            field="parent",
                        )
                    )
        
        # Check for circular references
        for i, feature in enumerate(feature_list.features):
            if feature.metadata.parent:
                visited = set([feature.title])
                current = feature.metadata.parent
                
                while current:
                    if current in visited:
                        errors.append(
                            ValidationIssue(
                                rule=self.CIRCULAR_REFERENCE,
                                message=f"Circular parent reference detected for feature '{feature.title}'",
                                index=i,
                                field="parent",
                            )
                        )
                        break
                    
                    visited.add(current)
                    
                    # Find parent feature
                    parent_feature = None
                    for f in feature_list.features:
                        if f.title == current:
                            parent_feature = f
                            break
                    
                    if not parent_feature or not parent_feature.metadata.parent:
                        break
                    
                    current = parent_feature.metadata.parent
        
        # Result is valid if there are no errors
        valid = len(errors) == 0
        
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            info=info,
        )

    def validate_feature(self, feature: Feature) -> ValidationResult:
        """
        Validate a single feature.
        
        Args:
            feature: Feature to validate
            
        Returns:
            Validation result
        """
        errors = []
        warnings = []
        info = []
        
        # Check title
        if not feature.title:
            errors.append(
                ValidationIssue(
                    rule=self.MISSING_TITLE,
                    message="Feature must have a title",
                    field="title",
                )
            )
        elif len(feature.title) < self.min_title_length:
            warnings.append(
                ValidationIssue(
                    rule=self.TITLE_TOO_SHORT,
                    message=f"Feature title is too short (min {self.min_title_length} characters)",
                    field="title",
                )
            )
        elif len(feature.title) > self.max_title_length:
            warnings.append(
                ValidationIssue(
                    rule=self.TITLE_TOO_LONG,
                    message=f"Feature title is too long (max {self.max_title_length} characters)",
                    field="title",
                )
            )
        
        # Check description
        if not feature.description:
            warnings.append(
                ValidationIssue(
                    rule=self.MISSING_DESCRIPTION,
                    message="Feature should have a description",
                    field="description",
                )
            )
        elif (
            feature.description
            and len(feature.description) < self.min_description_length
        ):
            info.append(
                ValidationIssue(
                    rule=self.DESCRIPTION_TOO_SHORT,
                    message=f"Feature description is quite short (min {self.min_description_length} characters recommended)",
                    field="description",
                )
            )
        
        # Result is valid if there are no errors
        valid = len(errors) == 0
        
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            info=info,
        )
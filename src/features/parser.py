"""
Feature list parser module.

This module provides functionality for parsing feature lists in various formats.
"""

import json
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field, validator

from src.utils.errors import ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class FeatureFormat(str, Enum):
    """Supported feature list formats."""

    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"


class FeatureType(str, Enum):
    """Types of features."""

    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    TASK = "task"
    STORY = "story"
    EPIC = "epic"


class FeaturePriority(str, Enum):
    """Priority levels for features."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class FeatureMetadata(BaseModel):
    """Metadata for a feature."""

    type: Optional[FeatureType] = None
    priority: Optional[FeaturePriority] = None
    estimate: Optional[float] = None
    labels: Optional[List[str]] = None
    assignee: Optional[str] = None
    milestone: Optional[str] = None
    parent: Optional[str] = None
    related: Optional[List[str]] = None


class Feature(BaseModel):
    """Model for a parsed feature."""

    title: str
    description: Optional[str] = None
    metadata: FeatureMetadata = Field(default_factory=FeatureMetadata)


class FeatureList(BaseModel):
    """Model for a parsed feature list."""

    features: List[Feature]
    format: FeatureFormat
    team: Optional[str] = None
    project: Optional[str] = None
    global_labels: Optional[List[str]] = None


class TextParser:
    """
    Parser for plain text feature lists.
    
    This parser understands simple text formats with features on their own lines,
    optionally followed by indented or prefixed descriptions and metadata.
    """

    @staticmethod
    def parse(text: str) -> FeatureList:
        """
        Parse a plain text feature list.
        
        Args:
            text: The text to parse
            
        Returns:
            Parsed feature list
        """
        lines = text.strip().split("\n")
        features = []
        current_feature = None
        description_lines = []
        
        # Extract global metadata
        team = None
        project = None
        global_labels = None
        
        for i, line in enumerate(lines):
            # Skip empty lines
            if not line.strip():
                continue
            
            # Check for global metadata
            if i < 5:  # Only check at the beginning
                team_match = re.match(r"^team:?\s*(.+)$", line, re.IGNORECASE)
                if team_match:
                    team = team_match.group(1).strip()
                    continue
                
                project_match = re.match(r"^project:?\s*(.+)$", line, re.IGNORECASE)
                if project_match:
                    project = project_match.group(1).strip()
                    continue
                
                labels_match = re.match(r"^labels:?\s*(.+)$", line, re.IGNORECASE)
                if labels_match:
                    global_labels = [
                        l.strip() for l in labels_match.group(1).split(",")
                    ]
                    continue
            
            # Check if line starts a new feature
            if not line.startswith(" ") and not line.startswith("\t"):
                # Save previous feature if it exists
                if current_feature:
                    if description_lines:
                        current_feature.description = "\n".join(description_lines)
                    features.append(current_feature)
                
                # Start new feature
                title = line.strip()
                priority = None
                feature_type = None
                
                # Check for embedded metadata in title
                metadata_match = re.search(r"\[(.*?)\]", title)
                if metadata_match:
                    metadata_str = metadata_match.group(1)
                    title = title.replace(f"[{metadata_str}]", "").strip()
                    
                    # Parse priority
                    if "high" in metadata_str.lower():
                        priority = FeaturePriority.HIGH
                    elif "urgent" in metadata_str.lower():
                        priority = FeaturePriority.URGENT
                    elif "low" in metadata_str.lower():
                        priority = FeaturePriority.LOW
                    else:
                        priority = FeaturePriority.MEDIUM
                    
                    # Parse type
                    if "bug" in metadata_str.lower():
                        feature_type = FeatureType.BUG
                    elif "improvement" in metadata_str.lower():
                        feature_type = FeatureType.IMPROVEMENT
                    elif "task" in metadata_str.lower():
                        feature_type = FeatureType.TASK
                    elif "story" in metadata_str.lower():
                        feature_type = FeatureType.STORY
                    elif "epic" in metadata_str.lower():
                        feature_type = FeatureType.EPIC
                    else:
                        feature_type = FeatureType.FEATURE
                
                # Create feature with metadata
                metadata = FeatureMetadata(
                    type=feature_type,
                    priority=priority,
                )
                
                current_feature = Feature(
                    title=title,
                    metadata=metadata,
                )
                description_lines = []
            else:
                # This is a description line for the current feature
                if current_feature:
                    # Extract metadata from description
                    line_stripped = line.strip()
                    
                    # Check for metadata lines
                    priority_match = re.match(r"^priority:?\s*(.+)$", line_stripped, re.IGNORECASE)
                    if priority_match:
                        priority_value = priority_match.group(1).strip().lower()
                        if "high" in priority_value:
                            current_feature.metadata.priority = FeaturePriority.HIGH
                        elif "urgent" in priority_value or "critical" in priority_value:
                            current_feature.metadata.priority = FeaturePriority.URGENT
                        elif "low" in priority_value:
                            current_feature.metadata.priority = FeaturePriority.LOW
                        else:
                            current_feature.metadata.priority = FeaturePriority.MEDIUM
                        continue
                    
                    type_match = re.match(r"^type:?\s*(.+)$", line_stripped, re.IGNORECASE)
                    if type_match:
                        type_value = type_match.group(1).strip().lower()
                        if "bug" in type_value:
                            current_feature.metadata.type = FeatureType.BUG
                        elif "improve" in type_value:
                            current_feature.metadata.type = FeatureType.IMPROVEMENT
                        elif "task" in type_value:
                            current_feature.metadata.type = FeatureType.TASK
                        elif "story" in type_value:
                            current_feature.metadata.type = FeatureType.STORY
                        elif "epic" in type_value:
                            current_feature.metadata.type = FeatureType.EPIC
                        else:
                            current_feature.metadata.type = FeatureType.FEATURE
                        continue
                    
                    labels_match = re.match(r"^labels?:?\s*(.+)$", line_stripped, re.IGNORECASE)
                    if labels_match:
                        labels = [
                            l.strip() for l in labels_match.group(1).split(",")
                        ]
                        current_feature.metadata.labels = labels
                        continue
                    
                    estimate_match = re.match(r"^estimate:?\s*(\d+\.?\d*)$", line_stripped, re.IGNORECASE)
                    if estimate_match:
                        try:
                            current_feature.metadata.estimate = float(estimate_match.group(1))
                        except ValueError:
                            pass
                        continue
                    
                    assignee_match = re.match(r"^assign(?:ee)?:?\s*(.+)$", line_stripped, re.IGNORECASE)
                    if assignee_match:
                        current_feature.metadata.assignee = assignee_match.group(1).strip()
                        continue
                    
                    # If not a metadata line, add to description
                    description_lines.append(line_stripped)
        
        # Save the last feature
        if current_feature:
            if description_lines:
                current_feature.description = "\n".join(description_lines)
            features.append(current_feature)
        
        return FeatureList(
            features=features,
            format=FeatureFormat.TEXT,
            team=team,
            project=project,
            global_labels=global_labels,
        )


class MarkdownParser:
    """
    Parser for Markdown feature lists.
    
    This parser understands Markdown formats with features as headings,
    followed by descriptions and metadata in various formats.
    """

    @staticmethod
    def parse(markdown: str) -> FeatureList:
        """
        Parse a Markdown feature list.
        
        Args:
            markdown: The Markdown text to parse
            
        Returns:
            Parsed feature list
        """
        lines = markdown.strip().split("\n")
        features = []
        current_feature = None
        description_lines = []
        
        # Extract global metadata from YAML frontmatter or initial lines
        team = None
        project = None
        global_labels = None
        
        # Check for YAML frontmatter
        frontmatter = {}
        if lines and lines[0].strip() == "---":
            frontmatter_end = -1
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    frontmatter_end = i
                    break
            
            if frontmatter_end > 0:
                # Extract frontmatter
                frontmatter_lines = lines[1:frontmatter_end]
                for line in frontmatter_lines:
                    if not line.strip():
                        continue
                    
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key == "team":
                            team = value
                        elif key == "project":
                            project = value
                        elif key == "labels":
                            global_labels = [
                                l.strip() for l in value.split(",")
                            ]
                
                # Remove frontmatter from lines
                lines = lines[frontmatter_end + 1:]
        
        # Process remaining lines
        in_code_block = False
        for line in lines:
            # Handle code blocks
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                if current_feature:
                    description_lines.append(line)
                continue
            
            # If in code block, just add to description
            if in_code_block:
                if current_feature:
                    description_lines.append(line)
                continue
            
            # Check for global metadata if not set by frontmatter
            if not team and not project and not global_labels:
                team_match = re.match(r"^##?\s*team:?\s*(.+)$", line, re.IGNORECASE)
                if team_match:
                    team = team_match.group(1).strip()
                    continue
                
                project_match = re.match(r"^##?\s*project:?\s*(.+)$", line, re.IGNORECASE)
                if project_match:
                    project = project_match.group(1).strip()
                    continue
                
                labels_match = re.match(r"^##?\s*labels:?\s*(.+)$", line, re.IGNORECASE)
                if labels_match:
                    global_labels = [
                        l.strip() for l in labels_match.group(1).split(",")
                    ]
                    continue
            
            # Check for heading (potential feature)
            heading_match = re.match(r"^(#+)\s+(.+)$", line)
            if heading_match:
                # Save previous feature if it exists
                if current_feature:
                    if description_lines:
                        current_feature.description = "\n".join(description_lines)
                    features.append(current_feature)
                
                # Parse new feature
                heading_level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # Skip headings that are likely section titles
                if heading_level <= 2 and (
                    title.lower() in ["features", "requirements", "overview", "introduction"]
                ):
                    current_feature = None
                    description_lines = []
                    continue
                
                priority = None
                feature_type = None
                
                # Check for embedded metadata in title
                metadata_match = re.search(r"\[(.*?)\]", title)
                if metadata_match:
                    metadata_str = metadata_match.group(1)
                    title = title.replace(f"[{metadata_str}]", "").strip()
                    
                    # Parse priority
                    if "high" in metadata_str.lower():
                        priority = FeaturePriority.HIGH
                    elif "urgent" in metadata_str.lower():
                        priority = FeaturePriority.URGENT
                    elif "low" in metadata_str.lower():
                        priority = FeaturePriority.LOW
                    else:
                        priority = FeaturePriority.MEDIUM
                    
                    # Parse type
                    if "bug" in metadata_str.lower():
                        feature_type = FeatureType.BUG
                    elif "improvement" in metadata_str.lower():
                        feature_type = FeatureType.IMPROVEMENT
                    elif "task" in metadata_str.lower():
                        feature_type = FeatureType.TASK
                    elif "story" in metadata_str.lower():
                        feature_type = FeatureType.STORY
                    elif "epic" in metadata_str.lower():
                        feature_type = FeatureType.EPIC
                    else:
                        feature_type = FeatureType.FEATURE
                
                # Create feature with metadata
                metadata = FeatureMetadata(
                    type=feature_type,
                    priority=priority,
                )
                
                current_feature = Feature(
                    title=title,
                    metadata=metadata,
                )
                description_lines = []
            elif line.strip().startswith("- ") and not current_feature:
                # List item as a feature
                title = line.strip()[2:].strip()
                
                # Check for embedded metadata in title
                priority = None
                feature_type = None
                
                metadata_match = re.search(r"\[(.*?)\]", title)
                if metadata_match:
                    metadata_str = metadata_match.group(1)
                    title = title.replace(f"[{metadata_str}]", "").strip()
                    
                    # Parse priority
                    if "high" in metadata_str.lower():
                        priority = FeaturePriority.HIGH
                    elif "urgent" in metadata_str.lower():
                        priority = FeaturePriority.URGENT
                    elif "low" in metadata_str.lower():
                        priority = FeaturePriority.LOW
                    else:
                        priority = FeaturePriority.MEDIUM
                    
                    # Parse type
                    if "bug" in metadata_str.lower():
                        feature_type = FeatureType.BUG
                    elif "improvement" in metadata_str.lower():
                        feature_type = FeatureType.IMPROVEMENT
                    elif "task" in metadata_str.lower():
                        feature_type = FeatureType.TASK
                    elif "story" in metadata_str.lower():
                        feature_type = FeatureType.STORY
                    elif "epic" in metadata_str.lower():
                        feature_type = FeatureType.EPIC
                    else:
                        feature_type = FeatureType.FEATURE
                
                # Save previous feature if it exists
                if current_feature:
                    if description_lines:
                        current_feature.description = "\n".join(description_lines)
                    features.append(current_feature)
                
                # Create feature with metadata
                metadata = FeatureMetadata(
                    type=feature_type,
                    priority=priority,
                )
                
                current_feature = Feature(
                    title=title,
                    metadata=metadata,
                )
                description_lines = []
            elif current_feature:
                # Check for metadata lines in description
                metadata_line = False
                line_stripped = line.strip()
                
                # Check for metadata as list items
                if line_stripped.startswith("- "):
                    item_text = line_stripped[2:].strip()
                    
                    # Priority
                    priority_match = re.match(r"^priority:?\s*(.+)$", item_text, re.IGNORECASE)
                    if priority_match:
                        priority_value = priority_match.group(1).strip().lower()
                        if "high" in priority_value:
                            current_feature.metadata.priority = FeaturePriority.HIGH
                        elif "urgent" in priority_value or "critical" in priority_value:
                            current_feature.metadata.priority = FeaturePriority.URGENT
                        elif "low" in priority_value:
                            current_feature.metadata.priority = FeaturePriority.LOW
                        else:
                            current_feature.metadata.priority = FeaturePriority.MEDIUM
                        metadata_line = True
                    
                    # Type
                    type_match = re.match(r"^type:?\s*(.+)$", item_text, re.IGNORECASE)
                    if type_match:
                        type_value = type_match.group(1).strip().lower()
                        if "bug" in type_value:
                            current_feature.metadata.type = FeatureType.BUG
                        elif "improve" in type_value:
                            current_feature.metadata.type = FeatureType.IMPROVEMENT
                        elif "task" in type_value:
                            current_feature.metadata.type = FeatureType.TASK
                        elif "story" in type_value:
                            current_feature.metadata.type = FeatureType.STORY
                        elif "epic" in type_value:
                            current_feature.metadata.type = FeatureType.EPIC
                        else:
                            current_feature.metadata.type = FeatureType.FEATURE
                        metadata_line = True
                    
                    # Labels
                    labels_match = re.match(r"^labels?:?\s*(.+)$", item_text, re.IGNORECASE)
                    if labels_match:
                        labels = [
                            l.strip() for l in labels_match.group(1).split(",")
                        ]
                        current_feature.metadata.labels = labels
                        metadata_line = True
                    
                    # Estimate
                    estimate_match = re.match(r"^estimate:?\s*(\d+\.?\d*)$", item_text, re.IGNORECASE)
                    if estimate_match:
                        try:
                            current_feature.metadata.estimate = float(estimate_match.group(1))
                        except ValueError:
                            pass
                        metadata_line = True
                    
                    # Assignee
                    assignee_match = re.match(r"^assign(?:ee)?:?\s*(.+)$", item_text, re.IGNORECASE)
                    if assignee_match:
                        current_feature.metadata.assignee = assignee_match.group(1).strip()
                        metadata_line = True
                
                # If not a metadata line, add to description
                if not metadata_line:
                    description_lines.append(line)
        
        # Save the last feature
        if current_feature:
            if description_lines:
                current_feature.description = "\n".join(description_lines)
            features.append(current_feature)
        
        return FeatureList(
            features=features,
            format=FeatureFormat.MARKDOWN,
            team=team,
            project=project,
            global_labels=global_labels,
        )


class JsonParser:
    """
    Parser for JSON feature lists.
    
    This parser understands JSON objects with a features array and optional
    global metadata.
    """

    @staticmethod
    def parse(json_text: str) -> FeatureList:
        """
        Parse a JSON feature list.
        
        Args:
            json_text: The JSON text to parse
            
        Returns:
            Parsed feature list
            
        Raises:
            ValidationError: If the JSON is invalid
        """
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON: {e}")
        
        # Validate structure
        if not isinstance(data, dict):
            raise ValidationError("JSON must be an object")
        
        if "features" not in data:
            raise ValidationError("JSON must contain a 'features' array")
        
        if not isinstance(data["features"], list):
            raise ValidationError("'features' must be an array")
        
        # Extract features
        features = []
        for item in data["features"]:
            if not isinstance(item, dict):
                logger.warning("Skipping non-object feature item")
                continue
            
            if "title" not in item:
                logger.warning("Skipping feature without title")
                continue
            
            # Extract metadata
            metadata = FeatureMetadata()
            
            if "type" in item:
                try:
                    metadata.type = FeatureType(item["type"])
                except ValueError:
                    # Default to feature if type is invalid
                    metadata.type = FeatureType.FEATURE
            
            if "priority" in item:
                try:
                    metadata.priority = FeaturePriority(item["priority"])
                except ValueError:
                    # Default to medium if priority is invalid
                    metadata.priority = FeaturePriority.MEDIUM
            
            if "estimate" in item:
                try:
                    metadata.estimate = float(item["estimate"])
                except (ValueError, TypeError):
                    pass
            
            if "labels" in item and isinstance(item["labels"], list):
                metadata.labels = [str(label) for label in item["labels"]]
            
            if "assignee" in item:
                metadata.assignee = str(item["assignee"])
            
            if "milestone" in item:
                metadata.milestone = str(item["milestone"])
            
            if "parent" in item:
                metadata.parent = str(item["parent"])
            
            if "related" in item and isinstance(item["related"], list):
                metadata.related = [str(rel) for rel in item["related"]]
            
            # Create feature
            feature = Feature(
                title=str(item["title"]),
                description=str(item.get("description", "")),
                metadata=metadata,
            )
            
            features.append(feature)
        
        # Extract global metadata
        team = data.get("team")
        project = data.get("project")
        global_labels = data.get("labels")
        
        return FeatureList(
            features=features,
            format=FeatureFormat.JSON,
            team=team,
            project=project,
            global_labels=global_labels,
        )


class FeatureParser:
    """
    Parser for feature lists.
    
    This class provides methods for detecting and parsing feature lists in various formats.
    """

    @staticmethod
    def detect_format(text: str) -> FeatureFormat:
        """
        Detect the format of a feature list.
        
        Args:
            text: The text to analyze
            
        Returns:
            Detected format
        """
        # Check if JSON
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                json.loads(text)
                return FeatureFormat.JSON
            except json.JSONDecodeError:
                pass
        
        # Check if Markdown
        if "# " in text or "## " in text or "### " in text:
            return FeatureFormat.MARKDOWN
        
        # Check for Markdown frontmatter
        if text.startswith("---") and "---" in text[3:]:
            return FeatureFormat.MARKDOWN
        
        # Default to plain text
        return FeatureFormat.TEXT

    @staticmethod
    def parse(text: str, format: Optional[FeatureFormat] = None) -> FeatureList:
        """
        Parse a feature list.
        
        Args:
            text: The text to parse
            format: Optional format override
            
        Returns:
            Parsed feature list
            
        Raises:
            ValidationError: If the text cannot be parsed
        """
        # Detect format if not specified
        if format is None:
            format = FeatureParser.detect_format(text)
        
        # Parse based on format
        try:
            if format == FeatureFormat.TEXT:
                return TextParser.parse(text)
            elif format == FeatureFormat.MARKDOWN:
                return MarkdownParser.parse(text)
            elif format == FeatureFormat.JSON:
                return JsonParser.parse(text)
            else:
                raise ValidationError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error(f"Error parsing feature list: {e}")
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(f"Failed to parse feature list: {e}")

    @staticmethod
    def normalize_feature_list(feature_list: FeatureList) -> FeatureList:
        """
        Normalize a feature list by applying global metadata to features.
        
        Args:
            feature_list: Feature list to normalize
            
        Returns:
            Normalized feature list
        """
        normalized_features = []
        
        for feature in feature_list.features:
            # Create a copy of the feature
            normalized_feature = Feature(
                title=feature.title,
                description=feature.description,
                metadata=FeatureMetadata(
                    type=feature.metadata.type,
                    priority=feature.metadata.priority,
                    estimate=feature.metadata.estimate,
                    assignee=feature.metadata.assignee,
                    milestone=feature.metadata.milestone,
                    parent=feature.metadata.parent,
                    related=feature.metadata.related,
                )
            )
            
            # Apply global labels if feature doesn't have labels
            if feature_list.global_labels and not normalized_feature.metadata.labels:
                normalized_feature.metadata.labels = feature_list.global_labels
            elif feature_list.global_labels and normalized_feature.metadata.labels:
                # Merge global and feature-specific labels
                normalized_feature.metadata.labels = list(
                    set(normalized_feature.metadata.labels + feature_list.global_labels)
                )
            
            # Apply defaults for missing metadata
            if normalized_feature.metadata.type is None:
                normalized_feature.metadata.type = FeatureType.FEATURE
            
            if normalized_feature.metadata.priority is None:
                normalized_feature.metadata.priority = FeaturePriority.MEDIUM
            
            normalized_features.append(normalized_feature)
        
        return FeatureList(
            features=normalized_features,
            format=feature_list.format,
            team=feature_list.team,
            project=feature_list.project,
            global_labels=feature_list.global_labels,
        )
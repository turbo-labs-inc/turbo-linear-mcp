"""
Feature list processor module.

This module provides functionality for processing feature lists and converting them
to Linear issues.
"""

import asyncio
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from src.features.parser import (
    Feature,
    FeatureFormat,
    FeatureList,
    FeatureParser,
    FeaturePriority,
    FeatureType,
)
from src.linear.client import LinearClient
from src.linear.issue import IssueCreateInput, LinearIssueClient
from src.linear.label import LinearLabelClient
from src.linear.project import LinearProjectClient
from src.linear.team import LinearTeamClient
from src.utils.errors import LinearAPIError, NotFoundError, ValidationError
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ProcessorOptions(BaseModel):
    """Options for feature list processing."""

    team_id: Optional[str] = None
    team_key: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    create_labels: bool = True
    create_parent_issues: bool = True
    use_feature_type_labels: bool = True
    default_estimate_scale: float = 1.0


class ProcessingResult(BaseModel):
    """Result of feature list processing."""

    issues_created: List[Dict[str, Any]]
    issues_failed: List[Dict[str, str]]
    team_id: Optional[str] = None
    project_id: Optional[str] = None
    labels_created: List[str] = Field(default_factory=list)


class FeatureListProcessor:
    """
    Processor for feature lists.
    
    This class provides functionality for processing feature lists and converting
    them to Linear issues.
    """

    def __init__(
        self,
        linear_client: LinearClient,
        options: Optional[ProcessorOptions] = None,
    ):
        """
        Initialize the feature list processor.
        
        Args:
            linear_client: Linear API client
            options: Processing options
        """
        self.linear_client = linear_client
        self.options = options or ProcessorOptions()
        
        # Initialize Linear resource clients
        self.issue_client = LinearIssueClient(linear_client)
        self.team_client = LinearTeamClient(linear_client)
        self.project_client = LinearProjectClient(linear_client)
        self.label_client = LinearLabelClient(linear_client)
        
        logger.info("Feature list processor initialized")

    async def process_text(
        self, text: str, format: Optional[FeatureFormat] = None
    ) -> ProcessingResult:
        """
        Process a feature list text.
        
        Args:
            text: Feature list text
            format: Optional format override
            
        Returns:
            Processing result
            
        Raises:
            ValidationError: If the text cannot be parsed
            LinearAPIError: If there is an error communicating with Linear
        """
        # Parse the feature list
        feature_list = FeatureParser.parse(text, format)
        
        # Normalize the feature list
        feature_list = FeatureParser.normalize_feature_list(feature_list)
        
        # Process the feature list
        return await self.process_feature_list(feature_list)

    async def process_feature_list(self, feature_list: FeatureList) -> ProcessingResult:
        """
        Process a feature list.
        
        Args:
            feature_list: Feature list to process
            
        Returns:
            Processing result
            
        Raises:
            LinearAPIError: If there is an error communicating with Linear
        """
        # Resolve team ID
        team_id = await self._resolve_team_id(feature_list.team)
        
        # Resolve project ID
        project_id = await self._resolve_project_id(feature_list.project, team_id)
        
        # Process features
        issues_created = []
        issues_failed = []
        labels_created = []
        
        # First, process parent features
        parent_map = {}  # Map of feature title to issue ID
        if self.options.create_parent_issues:
            for feature in feature_list.features:
                if feature.metadata.parent is None:
                    continue
                
                # Check if we already processed this parent
                if feature.metadata.parent in parent_map:
                    continue
                
                # Try to find the parent feature in the list
                parent_feature = None
                for f in feature_list.features:
                    if f.title == feature.metadata.parent:
                        parent_feature = f
                        break
                
                if parent_feature:
                    # Create parent issue
                    try:
                        parent_issue = await self._create_issue_from_feature(
                            parent_feature, team_id, project_id
                        )
                        parent_map[parent_feature.title] = parent_issue["id"]
                        issues_created.append(parent_issue)
                    except Exception as e:
                        logger.error(f"Failed to create parent issue: {e}")
                        issues_failed.append({
                            "title": parent_feature.title,
                            "error": str(e),
                        })
        
        # Process all features
        for feature in feature_list.features:
            # Skip if already processed as a parent
            if feature.title in parent_map:
                continue
            
            try:
                # Resolve parent ID
                parent_id = None
                if feature.metadata.parent and feature.metadata.parent in parent_map:
                    parent_id = parent_map[feature.metadata.parent]
                
                # Create or update labels
                if feature.metadata.labels and self.options.create_labels:
                    for label_name in feature.metadata.labels:
                        # Check if label exists
                        try:
                            label_exists = False
                            team_labels = await self.label_client.get_labels(team_id=team_id)
                            for label in team_labels:
                                if label["name"].lower() == label_name.lower():
                                    label_exists = True
                                    break
                            
                            if not label_exists:
                                await self.label_client.create_label({
                                    "name": label_name,
                                    "team_id": team_id,
                                })
                                labels_created.append(label_name)
                        except Exception as e:
                            logger.warning(f"Failed to create label '{label_name}': {e}")
                
                # Create feature type label if enabled
                if (
                    self.options.use_feature_type_labels
                    and feature.metadata.type
                    and self.options.create_labels
                ):
                    feature_type_label = feature.metadata.type.value
                    try:
                        label_exists = False
                        team_labels = await self.label_client.get_labels(team_id=team_id)
                        for label in team_labels:
                            if label["name"].lower() == feature_type_label.lower():
                                label_exists = True
                                break
                        
                        if not label_exists:
                            await self.label_client.create_label({
                                "name": feature_type_label,
                                "team_id": team_id,
                            })
                            labels_created.append(feature_type_label)
                            
                            # Add to feature's labels
                            if feature.metadata.labels:
                                feature.metadata.labels.append(feature_type_label)
                            else:
                                feature.metadata.labels = [feature_type_label]
                    except Exception as e:
                        logger.warning(f"Failed to create type label '{feature_type_label}': {e}")
                
                # Create issue
                issue = await self._create_issue_from_feature(
                    feature,
                    team_id,
                    project_id,
                    parent_id=parent_id,
                )
                
                issues_created.append(issue)
                
                # Add to parent map in case it's referenced by other features
                parent_map[feature.title] = issue["id"]
            
            except Exception as e:
                logger.error(f"Failed to create issue for feature '{feature.title}': {e}")
                issues_failed.append({
                    "title": feature.title,
                    "error": str(e),
                })
        
        return ProcessingResult(
            issues_created=issues_created,
            issues_failed=issues_failed,
            team_id=team_id,
            project_id=project_id,
            labels_created=labels_created,
        )

    async def _resolve_team_id(self, team_name: Optional[str] = None) -> str:
        """
        Resolve a team ID from a name, key, or options.
        
        Args:
            team_name: Optional team name or key
            
        Returns:
            Team ID
            
        Raises:
            ValidationError: If team cannot be resolved
            LinearAPIError: If there is an error communicating with Linear
        """
        # Use ID from options if provided
        if self.options.team_id:
            return self.options.team_id
        
        # Use key from options if provided
        if self.options.team_key:
            try:
                team = await self.team_client.get_team_by_key(self.options.team_key)
                return team["id"]
            except NotFoundError:
                logger.warning(f"Team with key '{self.options.team_key}' not found")
        
        # Use name from feature list if provided
        if team_name:
            # Check if team_name is a key
            try:
                team = await self.team_client.get_team_by_key(team_name)
                return team["id"]
            except NotFoundError:
                pass
            
            # Otherwise search for team by name
            try:
                teams = await self.team_client.get_teams()
                for team in teams:
                    if team["name"].lower() == team_name.lower():
                        return team["id"]
            except Exception as e:
                logger.error(f"Error searching for team by name: {e}")
        
        # Fallback to first available team
        try:
            teams = await self.team_client.get_teams()
            if teams:
                return teams[0]["id"]
        except Exception as e:
            logger.error(f"Error getting teams: {e}")
        
        raise ValidationError("Unable to resolve team ID")

    async def _resolve_project_id(
        self, project_name: Optional[str] = None, team_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Resolve a project ID from a name or options.
        
        Args:
            project_name: Optional project name
            team_id: Optional team ID to filter projects
            
        Returns:
            Project ID, or None if no project should be used
            
        Raises:
            LinearAPIError: If there is an error communicating with Linear
        """
        # Use ID from options if provided
        if self.options.project_id:
            return self.options.project_id
        
        # Use name from options if provided
        if self.options.project_name:
            try:
                projects = await self.project_client.get_projects(team_id=team_id)
                for project in projects:
                    if project["name"].lower() == self.options.project_name.lower():
                        return project["id"]
            except Exception as e:
                logger.error(f"Error searching for project by name from options: {e}")
        
        # Use name from feature list if provided
        if project_name:
            try:
                projects = await self.project_client.get_projects(team_id=team_id)
                for project in projects:
                    if project["name"].lower() == project_name.lower():
                        return project["id"]
            except Exception as e:
                logger.error(f"Error searching for project by name from feature list: {e}")
        
        # No project ID could be resolved, which is fine
        return None

    async def _create_issue_from_feature(
        self,
        feature: Feature,
        team_id: str,
        project_id: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a Linear issue from a feature.
        
        Args:
            feature: Feature to convert
            team_id: Team ID
            project_id: Optional project ID
            parent_id: Optional parent issue ID
            
        Returns:
            Created issue data
            
        Raises:
            LinearAPIError: If there is an error communicating with Linear
        """
        # Map feature priority to Linear priority
        priority_map = {
            FeaturePriority.LOW: 0,
            FeaturePriority.MEDIUM: 1,
            FeaturePriority.HIGH: 2,
            FeaturePriority.URGENT: 3,
        }
        
        priority = None
        if feature.metadata.priority:
            priority = priority_map.get(feature.metadata.priority)
        
        # Prepare issue input
        input_data = IssueCreateInput(
            title=feature.title,
            description=feature.description,
            team_id=team_id,
            project_id=project_id,
            parent_id=parent_id,
            priority=priority,
        )
        
        # Set estimate if available
        if feature.metadata.estimate is not None:
            # Apply scale factor
            input_data.estimate = feature.metadata.estimate * self.options.default_estimate_scale
        
        # Create the issue
        issue = await self.issue_client.create_issue(input_data)
        
        # Add labels if available
        if feature.metadata.labels:
            # First, get the label IDs
            label_ids = []
            team_labels = await self.label_client.get_labels(team_id=team_id)
            
            for label_name in feature.metadata.labels:
                for label in team_labels:
                    if label["name"].lower() == label_name.lower():
                        label_ids.append(label["id"])
                        break
            
            # Update issue with labels
            if label_ids:
                # Get existing labels to avoid duplicates
                existing_labels = await self.label_client.get_issue_labels(issue["id"])
                existing_label_ids = [label["id"] for label in existing_labels]
                
                # Combine existing and new labels
                all_label_ids = list(set(existing_label_ids + label_ids))
                
                # Update issue
                update_input = {
                    "labelIds": all_label_ids,
                }
                
                await self.issue_client.update_issue(issue["id"], update_input)
        
        return issue

    async def batch_process_text(
        self, texts: List[str], formats: Optional[List[FeatureFormat]] = None
    ) -> List[ProcessingResult]:
        """
        Process multiple feature list texts.
        
        Args:
            texts: List of feature list texts
            formats: Optional list of format overrides
            
        Returns:
            List of processing results
        """
        if formats is None:
            formats = [None] * len(texts)
        
        results = []
        for text, format in zip(texts, formats):
            try:
                result = await self.process_text(text, format)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process feature list: {e}")
                results.append(
                    ProcessingResult(
                        issues_created=[],
                        issues_failed=[{"title": "Feature list parsing", "error": str(e)}],
                    )
                )
        
        return results
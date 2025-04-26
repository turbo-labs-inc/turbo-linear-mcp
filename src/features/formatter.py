"""
Feature list response formatter module.

This module provides functionality for formatting response data from feature list processing.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.features.processor import ProcessingResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


class IssueResponse(BaseModel):
    """Model for a created issue response."""

    id: str
    title: str
    url: str
    identifier: Optional[str] = None
    state: Optional[str] = None
    priority: Optional[int] = None
    labels: List[str] = Field(default_factory=list)
    project: Optional[str] = None
    team: Optional[str] = None


class FailedIssueResponse(BaseModel):
    """Model for a failed issue response."""

    title: str
    error: str


class ConversionResponse(BaseModel):
    """Model for a feature list conversion response."""

    successful: List[IssueResponse]
    failed: List[FailedIssueResponse]
    total_count: int
    success_count: int
    failure_count: int
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    labels_created: List[str] = Field(default_factory=list)


class FeatureListFormatter:
    """
    Formatter for feature list processing results.
    
    This class provides functionality for formatting processing results into
    response data for API clients.
    """

    @staticmethod
    def format_result(result: ProcessingResult) -> ConversionResponse:
        """
        Format a processing result.
        
        Args:
            result: Processing result to format
            
        Returns:
            Formatted response
        """
        successful = []
        for issue in result.issues_created:
            labels = []
            if "labels" in issue and "nodes" in issue["labels"]:
                labels = [label["name"] for label in issue["labels"]["nodes"]]
            
            team_name = None
            if "team" in issue and issue["team"]:
                team_name = issue["team"].get("name")
            
            project_name = None
            if "project" in issue and issue["project"]:
                project_name = issue["project"].get("name")
            
            state_name = None
            if "state" in issue and issue["state"]:
                state_name = issue["state"].get("name")
            
            successful.append(
                IssueResponse(
                    id=issue["id"],
                    title=issue["title"],
                    url=issue["url"],
                    identifier=issue.get("identifier"),
                    state=state_name,
                    priority=issue.get("priority"),
                    labels=labels,
                    project=project_name,
                    team=team_name,
                )
            )
        
        failed = [
            FailedIssueResponse(
                title=issue["title"],
                error=issue["error"],
            )
            for issue in result.issues_failed
        ]
        
        return ConversionResponse(
            successful=successful,
            failed=failed,
            total_count=len(successful) + len(failed),
            success_count=len(successful),
            failure_count=len(failed),
            team_id=result.team_id,
            project_id=result.project_id,
            labels_created=result.labels_created,
        )

    @staticmethod
    def format_batch_results(results: List[ProcessingResult]) -> List[ConversionResponse]:
        """
        Format multiple processing results.
        
        Args:
            results: List of processing results to format
            
        Returns:
            List of formatted responses
        """
        return [FeatureListFormatter.format_result(result) for result in results]

    @staticmethod
    def create_summary(response: ConversionResponse) -> str:
        """
        Create a text summary of a conversion response.
        
        Args:
            response: Conversion response to summarize
            
        Returns:
            Text summary
        """
        summary = []
        
        # Add header
        summary.append(f"# Feature List Conversion Summary")
        summary.append("")
        
        # Add overall counts
        summary.append(f"Processed {response.total_count} features")
        summary.append(f"* {response.success_count} features successfully converted to issues")
        summary.append(f"* {response.failure_count} features failed to convert")
        summary.append("")
        
        # Add team and project info
        if response.team_name:
            summary.append(f"Team: {response.team_name}")
        elif response.team_id:
            summary.append(f"Team ID: {response.team_id}")
        
        if response.project_name:
            summary.append(f"Project: {response.project_name}")
        elif response.project_id:
            summary.append(f"Project ID: {response.project_id}")
        
        if response.labels_created:
            summary.append("")
            summary.append(f"Created {len(response.labels_created)} new labels:")
            for label in response.labels_created:
                summary.append(f"* {label}")
        
        # Add successful issues
        if response.successful:
            summary.append("")
            summary.append("## Successfully Created Issues")
            summary.append("")
            
            for issue in response.successful:
                summary.append(f"* [{issue.title}]({issue.url})")
                details = []
                
                if issue.identifier:
                    details.append(f"ID: {issue.identifier}")
                
                if issue.state:
                    details.append(f"State: {issue.state}")
                
                if issue.labels:
                    details.append(f"Labels: {', '.join(issue.labels)}")
                
                if details:
                    summary.append(f"  * {' | '.join(details)}")
        
        # Add failed issues
        if response.failed:
            summary.append("")
            summary.append("## Failed Issues")
            summary.append("")
            
            for issue in response.failed:
                summary.append(f"* {issue.title}")
                summary.append(f"  * Error: {issue.error}")
        
        return "\n".join(summary)

    @staticmethod
    def create_html_summary(response: ConversionResponse) -> str:
        """
        Create an HTML summary of a conversion response.
        
        Args:
            response: Conversion response to summarize
            
        Returns:
            HTML summary
        """
        html = []
        
        # Add header
        html.append("<h1>Feature List Conversion Summary</h1>")
        
        # Add overall counts
        html.append(f"<p>Processed {response.total_count} features</p>")
        html.append("<ul>")
        html.append(f"<li>{response.success_count} features successfully converted to issues</li>")
        html.append(f"<li>{response.failure_count} features failed to convert</li>")
        html.append("</ul>")
        
        # Add team and project info
        html.append("<p>")
        if response.team_name:
            html.append(f"Team: {response.team_name}<br>")
        elif response.team_id:
            html.append(f"Team ID: {response.team_id}<br>")
        
        if response.project_name:
            html.append(f"Project: {response.project_name}<br>")
        elif response.project_id:
            html.append(f"Project ID: {response.project_id}<br>")
        html.append("</p>")
        
        if response.labels_created:
            html.append(f"<p>Created {len(response.labels_created)} new labels:</p>")
            html.append("<ul>")
            for label in response.labels_created:
                html.append(f"<li>{label}</li>")
            html.append("</ul>")
        
        # Add successful issues
        if response.successful:
            html.append("<h2>Successfully Created Issues</h2>")
            html.append("<ul>")
            
            for issue in response.successful:
                html.append(f'<li><a href="{issue.url}">{issue.title}</a>')
                details = []
                
                if issue.identifier:
                    details.append(f"ID: {issue.identifier}")
                
                if issue.state:
                    details.append(f"State: {issue.state}")
                
                if issue.labels:
                    details.append(f"Labels: {', '.join(issue.labels)}")
                
                if details:
                    html.append(f" ({' | '.join(details)})")
                
                html.append("</li>")
            
            html.append("</ul>")
        
        # Add failed issues
        if response.failed:
            html.append("<h2>Failed Issues</h2>")
            html.append("<ul>")
            
            for issue in response.failed:
                html.append(f"<li><strong>{issue.title}</strong>")
                html.append(f" - Error: {issue.error}")
                html.append("</li>")
            
            html.append("</ul>")
        
        return "".join(html)
"""
Configuration management for GitLab Secrets Manager.

This module handles loading and validating configuration settings from environment
variables or a .env file. It provides a Config class that reads GitLab API credentials
and project information needed to interact with the GitLab API.

Example:
    config = Config()
    config.validate()  # Raises ValueError if required settings are missing
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# This allows users to store their credentials in a .env file instead of setting
# environment variables manually
load_dotenv()


class Config:
    """
    Configuration class for GitLab API settings.
    
    This class manages all configuration required to connect to the GitLab API.
    It reads configuration from environment variables or a .env file and provides
    validation to ensure all required settings are present.
    
    Attributes:
        gitlab_url (str): The base URL of the GitLab instance (default: https://gitlab.com)
        gitlab_token (str): Personal access token for GitLab API authentication
        project_id (str): The GitLab project ID to manage variables for
    
    Example:
        >>> config = Config()
        >>> config.gitlab_url
        'https://gitlab.com'
        >>> config.validate()  # Raises ValueError if token or project_id is missing
    """
    
    def __init__(self):
        """
        Initialize the Config object by reading environment variables.
        
        Reads configuration from environment variables with fallback defaults:
        - GITLAB_URL: defaults to 'https://gitlab.com' (public GitLab)
        - GITLAB_TOKEN: required for API authentication (no default)
        - GITLAB_PROJECT_ID: required to identify the project (no default)
        """
        # Base URL of the GitLab instance (supports self-hosted GitLab)
        self.gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
        
        # Personal access token for authenticating API requests
        # Get this from: Settings > Access Tokens in GitLab
        self.gitlab_token = os.getenv('GITLAB_TOKEN', '')
        
        # Project ID where CI/CD variables will be managed
        # Find this in the project's Settings > General section
        self.project_id = os.getenv('GITLAB_PROJECT_ID', '')
    
    def validate(self) -> bool:
        """
        Validate that required configuration is present.
        
        Checks that both the GitLab token and project ID are set. These are
        essential for making API requests to GitLab.
        
        Returns:
            bool: True if validation passes
            
        Raises:
            ValueError: If GITLAB_TOKEN is not set
            ValueError: If GITLAB_PROJECT_ID is not set
            
        Example:
            >>> config = Config()
            >>> config.validate()  # Raises ValueError if missing required fields
            True
        """
        # Ensure the authentication token is provided
        if not self.gitlab_token:
            raise ValueError("GITLAB_TOKEN environment variable is required")
        
        # Ensure the project ID is provided so we know which project to manage
        if not self.project_id:
            raise ValueError("GITLAB_PROJECT_ID environment variable is required")
        
        return True


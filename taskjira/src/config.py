"""config.py

Defines a pydantic-settings class that holds the connection data needed for connection to JIRA"""

from typing import Optional

from pydantic import AnyUrl, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TaskJiraSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class PassPyConfig(TaskJiraSettings):
    GPG_BIN: str = "gpg"


class JiraConfig(TaskJiraSettings):
    USERNAME: EmailStr
    JIRA_HOST: AnyUrl
    API_PASS_KEY: str
    JIRA_USER: Optional[str] = None


class TaskWarriorConfig(TaskJiraSettings):
    TASKRC_FILEPATH: str = "~/.taskrc"


class IntergratorConfig(TaskJiraSettings):
    PROJECT_ABBREVIATION: str

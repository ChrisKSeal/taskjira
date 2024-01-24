"""dataclasses.py

Dataclasses to hold the JIRA issues, Epics and Sprints ready for ingestion into Taskwarrior and vice-versa"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class TJIssue:
    """Dataclass to hold an individual Epic from Jira

    comments follow a (user, comment) structure
    links follow a (depends|is dependant on, key) structure
    """

    key: str
    summary: str
    state: str
    priority: str = "Minor"
    description: Optional[str] = None
    comments: Optional[List[Tuple[str, str]]] = None
    links: Optional[List[Tuple[str, str]]] = None


@dataclass
class TJSprint:
    """Dataclass to hold a Sprint from Jira"""

    name: str
    state: str
    start_date: datetime
    end_date: datetime

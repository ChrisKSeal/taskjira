"""dataclasses.py

Dataclasses to hold the JIRA issues, Epics and Sprints ready for ingestion into Taskwarrior and vice-versa"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


@dataclass
class TJIssue:
    """Dataclass to hold an individual Issue from Jira

    comments follow a (user, comment) structure
    links follow a (inward|outward, depends|is dependant on, key) structure
    """

    key: str
    summary: str
    state: str
    priority: str
    description: Optional[str] = None
    comments: Optional[List[Tuple[str, str]]] = None
    links: Optional[List[Tuple[str, str, str]]] = None
    project: Optional[str] = None
    tags: Optional[List[str]] = None
    labels: Optional[List[str]] = None


@dataclass
class TJSprint:
    """Dataclass to hold a Sprint from Jira"""

    name: str
    state: str
    start_date: datetime
    end_date: datetime


@dataclass
class TWTask:
    """Dataclass to hold a task from TaskWarrior"""

    name: str
    state: str
    priority: str
    details: Optional[str] = None
    project: Optional[str] = None
    uuid: Optional[str] = None
    depends: Optional[List[str]] = None
    comments: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    due: Optional[datetime] = None
    sprints: Optional[List[str]] = None
    end: Optional[datetime] = None

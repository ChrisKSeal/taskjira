"""taskwarrior.py

Scripts to manage the integration with taskwarrior
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dateutil import parser
from src.config import TaskWarriorConfig
from src.dataclasses import TWTask
from taskw import TaskWarrior

COMMENT_REGEX = r"[a-zA-Z\s]+:-"


class TJTaskWarrior:
    """TJTaskWarrior

    A class to mediate interactions with TaskWarrior
    """

    def __init__(
        self,
        tw_config: TaskWarriorConfig,
    ) -> None:
        """Initialisation script

        Args:
            tw_config (TaskWarriorConfig): A config class containing the location of the
                taskrc file.
        """
        self.taskwarrior = TaskWarrior(config_filename=tw_config.TASKRC_FILEPATH)

    @staticmethod
    def __process_task(
        task: Dict[str, str | List[str] | List[Dict[str, str]]],
        completed: bool = False,
    ) -> Dict[str, Optional[str | datetime | List[str] | List[Dict[str, str]]]]:
        name = task["description"]
        try:
            due = parser.parse(task["due"])
        except KeyError:
            due = None
        state = task["status"]
        try:
            priority = task["priority"] or "M"
        except KeyError:
            priority = "M"
        try:
            project = task["project"] or None
        except KeyError:
            project = None
        uuid = task["uuid"]
        try:
            details = task["details"] or None
        except KeyError:
            details = None
        try:
            raw_comments = task["annotations"] or None
        except KeyError:
            raw_comments = None
        try:
            depends = task["depends"] or None
        except KeyError:
            depends = None
        try:
            tags = task["tags"] or None
        except KeyError:
            tags = None
        try:
            end = parser.parse(task["end"]) if completed else None
        except KeyError:
            end = None
        try:
            sprints = task["sprints"] or None
        except KeyError:
            sprints = None
        return {
            "name": name,
            "due": due,
            "state": state,
            "priority": priority,
            "project": project,
            "uuid": uuid,
            "details": details,
            "raw_comments": raw_comments,
            "depends": depends,
            "tags": tags,
            "end": end,
            "sprints": sprints,
        }

    @staticmethod
    def __parse_comments(comments: List[Dict[str, str]]) -> Optional[List[Tuple[str, str]]]:
        return_list = []
        for comment in comments:
            comment_string = comment["description"]
            if re.match(COMMENT_REGEX, comment_string):
                comment_tuple = (
                    comment_string.split(":-")[0].strip(),
                    comment_string.split(":-")[1].strip(),
                )
                return_list.append(comment_tuple)
        return return_list or None

    def __get_tasks(self, active: bool = True) -> List[TWTask]:
        """Retrieve the tasks from taskwarrior

        Returns:
            List[TWTask]: A list of tasks converted to TWTask dataclasses
        """
        tasks = self.taskwarrior.load_tasks()
        return_list = []
        task_list = tasks["pending"] if active else tasks["completed"]
        for task in task_list:
            raw_task = TJTaskWarrior.__process_task(task)
            if "raw_comments" in raw_task.keys() and raw_task["raw_comments"]:
                comments = TJTaskWarrior.__parse_comments(raw_task["raw_comments"])
            return_list.append(
                TWTask(
                    name=raw_task["name"],
                    state=raw_task["state"],
                    priority=raw_task["priority"],
                    details=raw_task["details"],
                    uuid=raw_task["uuid"],
                    tags=raw_task["tags"],
                    comments=comments or None,
                    depends=raw_task["depends"],
                    due=raw_task["due"],
                    end=raw_task["end"],
                    sprints=raw_task["sprints"],
                )
            )
        return return_list

    def get_active_tasks(self):
        return self.__get_tasks()

    def get_completed_tasks(self):
        return self.__get_tasks(active=False)

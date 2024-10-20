"""integrations.py

Scripts to migrate to and from JIRA and TaskWarrior"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytz
from dateutil import parser
from jira import Issue, Priority
from src.config import IntergratorConfig
from src.dataclasses import TWTask
from src.jira import TJJira
from src.taskwarrior import TJTaskWarrior


class Integrator:
    def __init__(
        self,
        integrator_config: IntergratorConfig,
        jira_inst: TJJira,
        tw_inst: TJTaskWarrior,
    ) -> None:
        self.JIRA_KEY_REGEX = f"{integrator_config.PROJECT_ABBREVIATION}-[0-9]+"
        self.jira = jira_inst
        self.taskwarrior = tw_inst
        self.jql_search = (
            f'project = "{integrator_config.PROJECT_ABBREVIATION}" '
            f'and assignee = "{self.jira.current_user}" '
            "and status != resolved "
            "and status != done "
            "and status != closed"
        )
        self.jql_sprint = f'assignee = "{self.jira.current_user}" ' "and sprint != NULL " "and sprint in openSprints()"
        self.jql_epic = (
            f'project = "{integrator_config.PROJECT_ABBREVIATION}" '
            'and issuetype = "Epic" '
            "and status != resolved "
            "and status != done "
            "and status != closed"
        )
        self.project = integrator_config.PROJECT_ABBREVIATION

    def get_keys_by_type(
        self,
        issues: Dict[str, Issue],
        issue_type: str,
    ) -> List[str]:
        return [key for key, issue in issues.items() if str(issue.get_field("issuetype") == issue_type)]

    def build_parent_tree(
        self,
        issues: Dict[str, Issue],
    ) -> Dict[str, Optional[str]]:
        return_dict = {}
        for key, issue in issues.items():
            try:
                parent = issue.get_field("parent").key
            except AttributeError:
                parent = None
            return_dict[key] = parent
        return return_dict

    def build_dependency_tree(
        self,
        issues: Dict[str, Issue],
    ) -> Dict[str, Optional[List[str]]]:
        return_dict: Dict[str, Optional[List[str]]] = {}
        for key, issue in issues.items():
            try:
                links = issue.fields.issuelinks or None
            except AttributeError:
                return_dict[key] = None
                continue
            if links:
                link_list = []
                for link in links:
                    try:
                        link_list.append(link.outwardIssue.key)
                    except AttributeError:
                        continue
                deps = link_list or None
                return_dict[key] = deps
            else:
                return_dict[key] = None
        return return_dict

    def build_project_tree(
        self,
        issues: Dict[str, Issue],
    ) -> Dict[str, Optional[str]]:
        parents = self.build_parent_tree(issues)
        dependencies = self.build_dependency_tree(issues)
        for key, values in dependencies.items():
            if values:
                for value in values:
                    parents[value] = f"{parents[value]}.{key}"
        for key, value in parents.items():
            parents[key] = f"IDS.{value}" if value else "IDS"
        return parents

    def process_comments(
        self,
        issues: Dict[str, Issue],
    ) -> Dict[str, Optional[List[str]]]:
        return_dict: Dict[str, Optional[List[str]]] = {}
        for key, issue in issues.items():
            try:
                comments = issue.fields.comment.comments or None
            except AttributeError:
                comments = None
            if comments:
                return_dict[key] = [f"{comment.author.displayName} - {comment.body}" for comment in comments]
            else:
                return_dict[key] = None
        return return_dict

    def process_tags(
        self,
        issues: Dict[str, Issue],
    ) -> Dict[str, List[str]]:
        return_dict: Dict[str, List[str]] = {}
        priorities = self.build_priority_from_parents_and_dependencies(issues)
        for key, issue in issues.items():
            tags = ["IDS", "JIRA"]
            if issue.fields.customfield_10020:
                tags.extend("currentsprint" for sprint in issue.fields.customfield_10020 if sprint.state == "active")
            if issue.fields.labels:
                tags.extend(iter(issue.fields.labels))
            if priorities[key] == 5:
                tags.append("blocker")
            return_dict[key] = sorted(list(set(tags)))
        return return_dict

    def build_priority_from_parents_and_dependencies(
        self,
        issues: Dict[str, Issue],
    ) -> Dict[str, int]:
        return_dict: Dict[str, int] = {}
        parents = self.build_parent_tree(issues)
        dependencies = self.build_dependency_tree(issues)
        rev_deps = self.__reverse_dependencies(dependencies)
        for key, issue in issues.items():
            issue_priority = -1
            if parents[key]:
                issue_priority = max(
                    self.__get_numeric_value_for_priority(issues[parents[key]].fields.priority),
                    self.__get_numeric_value_for_priority(issue.fields.priority),
                )
            else:
                issue_priority = self.__get_numeric_value_for_priority(issue.fields.priority)
            if key in rev_deps:
                dependencies_priority = [self.__get_numeric_value_for_priority(issue.fields.priority)]
                for dep in rev_deps[key]:
                    dependencies_priority.append(self.__get_numeric_value_for_priority(issues[dep].fields.priority))
                    if parents[dep]:
                        dependencies_priority.append(
                            self.__get_numeric_value_for_priority(issues[parents[dep]].fields.priority)
                        )
                if parents[key]:
                    dependencies_priority.append(
                        self.__get_numeric_value_for_priority(issues[parents[key]].fields.priority)
                    )
                issue_priority = max(dependencies_priority)
            return_dict[key] = issue_priority
        return return_dict

    def __reverse_dependencies(
        self,
        dependencies: Dict[str, Optional[List[str]]],
    ) -> Dict[str, List[str]]:
        return_dict: Dict[str, List[str]] = {}
        for key, dependency in dependencies.items():
            if dependency:
                for dep in dependency:
                    try:
                        val = return_dict[dep]
                        val.append(key)
                    except KeyError:
                        return_dict[dep] = [key]
        return return_dict

    def __get_numeric_value_for_priority(self, priority: Priority) -> int:
        priority_dict = {
            "blocker": 5,
            "critical": 4,
            "major": 3,
            "minor": 2,
            "release": 1,
            "trivial": 0,
            "unscheduled": 0,
        }
        return 0 if str(priority).lower() not in priority_dict else priority_dict[str(priority).lower()]

    def __get_str_from_priority(self, priority: int) -> str:
        if priority < 2:
            return "L"
        elif priority > 2:
            return "H"
        return "M"

    def process_sprints(self, issues: Dict[str, Issue]) -> Dict[str, Optional[List[str]]]:
        return_dict: Dict[str, Optional[List[str]]] = {
            key: [field.name for field in issue.fields.customfield_10020] if issue.fields.customfield_10020 else None
            for key, issue in issues.items()
        }
        return return_dict

    def process_due_dates(self, issues: Dict[str, Issue]) -> Dict[str, Optional[datetime]]:
        nztime = pytz.timezone("Pacific/Auckland")
        return_dict: Dict[str, Optional[datetime]] = {}
        for key, issue in issues.items():
            duedate = []
            if issue.fields.duedate:
                duedate.append(parser.isoparse(issue.fields.duedate).astimezone(nztime))
            if issue.fields.customfield_10020:
                duedate.extend(
                    parser.parse(sprint.endDate).astimezone(nztime)
                    for sprint in issue.fields.customfield_10020
                    if sprint.state == "active"
                )
            if duedate:
                duedate = min(duedate)
                return_dict[key] = duedate
            else:
                return_dict[key] = None
        return return_dict

    def pull_from_jira(
        self,
        jql_search_string: Optional[str] = None,
        jql_epics_string: Optional[str] = None,
        max_results: int = 500,
    ) -> Dict[str, TWTask]:
        if not jql_search_string:
            jql_search_string = self.jql_search
        if not jql_epics_string:
            jql_epics_string = self.jql_epic
        jira_issues = self.jira.jira.search_issues(
            jql_search_string,
            maxResults=max_results,
        )
        epics = self.jira.jira.search_issues(jql_epics_string, maxResults=max_results)
        issues = {issue.key: issue for issue in jira_issues}
        for epic in epics:
            if epic.key not in issues:
                issues[epic.key] = epic
        dependencies = self.build_dependency_tree(issues)
        projects = self.build_project_tree(issues)
        comments = self.process_comments(issues)
        priorities = self.build_priority_from_parents_and_dependencies(issues)
        tags = self.process_tags(issues)
        sprints = self.process_sprints(issues)
        due_dates = self.process_due_dates(issues)
        return {
            key: TWTask(
                key=key,
                name=f"{key} - {issue.fields.summary}",
                state="pending",
                priority=self.__get_str_from_priority(priorities[key]),
                details=issue.fields.description,
                depends=dependencies[key],
                project=projects[key],
                tags=tags[key],
                comments=comments[key],
                due=due_dates[key],
                sprints=sprints[key],
                uuid=str(uuid4()),
            )
            for key, issue in issues.items()
            if str(issue.fields.issuetype) != "Epic"
        }

    def check_for_existing_task(
        self,
        task_dict: Dict[str, TWTask],
    ) -> Dict[str, List[str]]:
        existing_tasks = self.taskwarrior.taskwarrior.load_tasks()
        tasks_in_tw: Dict[str, Dict] = {}
        for task in existing_tasks["pending"]:
            try:
                key = task["jirakey"]
            except KeyError:
                continue
            if key:
                tasks_in_tw[key] = task
        for task in existing_tasks["completed"]:
            try:
                key = task["jirakey"]
            except KeyError:
                continue
            if key:
                tasks_in_tw[key] = task
        return_dict: Dict[str, List[str]] = {}
        for key, task in task_dict.items():
            if key in tasks_in_tw:
                task.uuid = tasks_in_tw[key]["uuid"]
        for key, task in task_dict.items():
            comp_list = []
            if key in tasks_in_tw:
                old_task = tasks_in_tw[key]
                if "depends" in old_task:
                    old_task["depends"] = [
                        self.__get_twtask_key_by_uuid(task_uuid, task_dict) for task_uuid in old_task["depends]"]
                    ]
                    print(old_task)
                new_task = self.parse_twtask_to_dict(key, task_dict)
                if old_task["description"] != new_task["description"]:
                    comp_list.append("description")
                if old_task["project"] != new_task["project"]:
                    comp_list.append("project")
                if old_task["tags"] != new_task["tags"]:
                    comp_list.append("tags")
                if old_task["priority"] != new_task["priority"]:
                    comp_list.append("priority")
                if (
                    "sprints" in old_task.keys()
                    and "sprintss" in new_task.keys()
                    and old_task["sprints"] != new_task["sprints"]
                ):
                    comp_list.append("sprints")
                if "due" in old_task.keys() and "due" in new_task.keys() and old_task["due"] != new_task["due"]:
                    print(old_task["due"], new_task["due"])
                    comp_list.append("due")
                if (
                    "details" in old_task.keys()
                    and "details" in new_task.keys()
                    and old_task["details"] != new_task["details"]
                ):
                    comp_list.append("details")
                if (
                    "depends" in old_task.keys()
                    and "depends" in new_task.keys()
                    and old_task["depends"] != new_task["depends"]
                ) or ("depends" in new_task.keys() and "depends" not in old_task.keys()):
                    comp_list.append("depends")
            else:
                comp_list.append("all")
            return_dict[key] = comp_list
        return return_dict

    def __get_twtask_uuid_by_key(self, key: str, task_dict: Dict[str, TWTask]) -> str:
        return task_dict[key].uuid

    def __get_twtask_key_by_uuid(self, uuid: str, task_dict: Dict[str, TWTask]) -> Optional[str]:
        return next((key for key, task in task_dict.items() if task.uuid == uuid), None)

    def parse_twtask_to_dict(self, key: str, task_dict: Dict[str, TWTask]) -> Dict[str, Any]:
        twtask = task_dict[key]
        return_dict = {
            "jirakey": twtask.key,
            "description": twtask.name,
            "tags": twtask.tags,
            "project": twtask.project,
            "uuid": twtask.uuid,
            "priority": twtask.priority,
        }
        if twtask.due:
            return_dict["due"] = twtask.due.strftime("%Y%m%dT%H%M%SZ")
        if twtask.sprints:
            return_dict["sprints"] = ",".join(twtask.sprints)
            return_dict["numsprints"] = len(twtask.sprints)
        if twtask.depends:
            return_dict["depends"] = list(twtask.depends)
        if twtask.details:
            return_dict["details"] = twtask.details
        return return_dict

    # def create_task_from_dictionary(self,
    #                                task_dict: Dict[str, Any]) -> Dict[str, Any]:
    #    description = task_dict['description']
    #    tags = task_dict['tags']
    #    uuid = task_dict['uuid']
    #    project=task_dict['project']

    def push_to_taskwarrior(self, task_dict: Dict[str, TWTask]) -> None:
        existing_tasks = self.taskwarrior.taskwarrior.load_tasks()
        existing_tasks = self.check_for_existing_task(task_dict)
        for key, task in task_dict.items():
            tw_entry = self.parse_twtask_to_dict(key, task_dict)
            if task.depends:
                tw_entry["depends"] = [
                    self.__get_twtask_uuid_by_key(task_key, task_dict) for task_key in tw_entry["depends"]
                ]
            if "all" in existing_tasks[key]:
                print(f"Adding task: {key}")
                depends = None
                if task.depends:
                    depends = tw_entry.pop("depends")
                _ = self.taskwarrior.taskwarrior.task_add(**tw_entry)
                if depends:
                    tw_entry["depends"] = depends
            elif existing_tasks[key]:
                print(f"Updating task: {key} with {existing_tasks[key]}")
                depends = None
                if task.depends:
                    existing_tasks[key].remove("depends")
                    depends = True
                if existing_tasks[key]:
                    _, tw_task = self.taskwarrior.taskwarrior.get_task(uuid=task.uuid)
                    for field in existing_tasks[key]:
                        tw_task[field] = tw_entry[field]
                    self.taskwarrior.taskwarrior.task_update(tw_task)
                if depends:
                    existing_tasks[key].append("depends")
        for key, task in task_dict.items():
            # Need to do this in two parts to ensure that the tasks exist before
            # setting dependencies.
            if ("all" in existing_tasks[key] and task.depends) or "depends" in existing_tasks[key]:
                tw_entry = self.parse_twtask_to_dict(key, task_dict)
                print(f"Sorting Dependencies for task: {key}")
                _, tw_task = self.taskwarrior.taskwarrior.get_task(uuid=task.uuid)
                tw_entry["depends"] = [
                    self.__get_twtask_uuid_by_key(task_key, task_dict) for task_key in tw_entry["depends"]
                ]
                tw_task["depends"] = ",".join(tw_entry["depends"])
                self.taskwarrior.taskwarrior.task_update(tw_task)

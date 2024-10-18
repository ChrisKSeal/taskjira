"""jira.py

Scripts to connect to JIRA and access"""

import contextlib
import pprint
from typing import Any, Dict, List, Optional, Tuple

from jira import JIRA, Issue
from jira.client import ResultList
from passpy import Store

# from taskjira.src.config import JiraConfig
# from taskjira.src.utils import get_password_from_store


def get_password_from_store(
    store: Store,
    pass_key: str,
) -> Optional[str]:
    """Retrieve a key from a password store."""
    with contextlib.suppress(FileNotFoundError):
        return password.rstrip("\n") if (password := store.get_key(pass_key)) else None
    return None


class MyJiraCore:
    """JiraCore

    A class to mediate interactions with JIRA
    """

    def __init__(
        self,
        username: str,
        host: str,
        store: Store,
    ) -> None:
        """Initialisation script

        Args:
            jira_config (JiraConfig): A config class containing the connection details to JIRA
        """
        if password := get_password_from_store(store=store, pass_key="JIRA/API"):
            print("Establishing connection to JIRA")
            self.jira = JIRA(
                server=host,
                basic_auth=(
                    username,
                    password,
                ),
            )
            self.current_user = "c.seal@auckland.ac.nz"
            print("Connection established")
        else:
            raise ValueError("Unable to retrieve the API Key from the password store")

    def get_issues(
        self,
        jql_search: str,
    ) -> Dict[str, Any] | ResultList[Issue] | List[Any]:
        """script to run a JQL search query on the JIRA instance

        Args:
            jql_search (str): A string representation of the JQL query

        Example:
            For a JQL query returning all active issues associated with a particular user,
            where the query is::
                assignee = "Chris Seal" and status != closed
                            and status != resolved and status != Done

        then the request would be::
            TJJira.__get_issues('assignee = "Chris Seal" and status != closed
                                 and status != resolved and status != Done')
        """
        issues = self.jira.search_issues(jql_search)
        if isinstance(issues, dict):
            return issues
        issues = self.__get_all_parents(issues)  # type:ignore
        return self.__get_all_subtasks(issues)

    def __get_all_parents(self, issues: ResultList[Issue] | List[Any]) -> List[Any]:
        """Make sure we have all the parent issues on the off chance that there are
        some not assigned to the current user

        Args:
            issues (ResultList[Issues]): The current list of issues that we have a full copy of

        Returns:
            A ResultList of issues with their parents added
        """
        return_list = issues.copy()
        issue_keys = {issue.key for issue in issues}
        if missing_parents := {
            issue.fields.parent.key
            for issue in issues
            if "parent" in dir(issue.fields)
            and issue.fields.parent.key not in issue_keys
        }:
            for parent in missing_parents:
                return_list.append(self.jira.issue(parent))
            return_list = self.__get_all_parents(return_list)
        return return_list

    def __get_all_subtasks(
        self, issues: ResultList[Issue] | List[Any]
    ) -> ResultList[Issue] | List[Any]:
        """Make sure we have all the sub-tasks of an issue on the off chance that there are
        some not assigned to the current user

         Args:
            issues (ResultList[Issues]): The current list of issues that we have a full copy of

        Returns:
            A ResultList of issues with their parents added
        """
        return_list = issues.copy()
        issue_keys = {issue.key for issue in issues}
        sub_task_keys = []
        for issue in issues:
            if issue.fields.subtasks:
                sub_task_keys.extend([subtask.key for subtask in issue.fields.subtasks])
        sub_task_keys = list(set(sub_task_keys))
        if missing_issues := {
            sub_task_key
            for sub_task_key in sub_task_keys
            if sub_task_key not in issue_keys
        }:
            for missing_issue in missing_issues:
                return_list.append(self.jira.issue(missing_issue))
            return_list = self.__get_all_subtasks(return_list)
        return return_list

    @staticmethod
    def __get_issue_from_list_by_key(issues: List[Issue], key: str) -> Optional[Issue]:
        """return the Issue from a list of Issues that has the unique key defined

        Args:
          issues (List[Issue]): The list containing the issues to be searched
          key (str): The unique key associated with the desired Issue

        Returns:
          The Issue that matches the key or None if the issue can't be found
        """
        return next((issue for issue in issues if issue.key == key), None)

    @staticmethod
    def __compactify_heirarchy(heirarchy: Dict[Issue, Any]) -> Dict[Issue, Any]:
        """Read through the dictionary and move any issues that are children to
        their parents
        """
        heirarchy = MyJiraCore.__reassign_children_of_epics_if_other_child(
            heirarchy, heirarchy
        )
        return heirarchy

    @staticmethod
    def __move_child_to_new_dict(
        issue_map: Dict[Issue, Any], hierarchy: Dict[Issue, Any]
    ) -> Dict[Issue, Any]:
        """Function to call recursively on children to build tidied structure"""
        pprint.pp(hierarchy)
        if isinstance(hierarchy, list):
            if not hierarchy:
                return hierarchy
            else:
                return {
                    issue: (
                        [
                            MyJiraCore.__move_child_to_new_dict(
                                issue_map, issue_map[issue]
                            )
                        ]
                    )
                    for issue in hierarchy
                }

        return {
            key: (
                [
                    MyJiraCore.__move_child_to_new_dict(issue_map, issue_map[issue])
                    for issue in value
                ]
                if value
                else None
            )
            for key, value in hierarchy.items()
        }

    @staticmethod
    def __reassign_children_of_epics_if_other_child(
        heirarchy: Dict[Issue, Any], is_child: List[Issue]
    ) -> Dict[Issue, Any]:
        """Look at all issues that are children, identify where there are duplicates and find who thier parents are.
        If one of the parents is a Story or a Task and the other is an Epic, remove the child from the Epic
        """
        # Check for duplicates
        seen = set()
        duplicates = [child for child in is_child if child in seen or seen.add(child)]
        parents_to_prune = []
        for duplicate in duplicates:
            direct_parent = None
            for issue, values in heirarchy.items():
                if duplicate in values:
                    if direct_parent:
                        if (
                            (
                                direct_parent.fields.issuetype == "Epic"
                                and issue.fields.issuetype
                                in ["Story", "Task", "Sub-task"]
                            )
                            or (
                                direct_parent.fields.issuetype == "Story"
                                and issue.fields.issuetype in ["Task", "Sub-task"]
                            )
                            or (
                                direct_parent.fields.issuetype == "Task"
                                and issue.fields.issuetyp == "Sub-task"
                            )
                        ):
                            parents_to_prune.append((direct_parent, duplicate))
                            direct_parent = issue
                        else:
                            parents_to_prune.append((issue, duplicate))
                    else:
                        direct_parent = issue
        for parent in parents_to_prune:
            heirarchy[parent[0]].remove(parent[1])
        heirarchy = MyJiraCore.__move_child_to_new_dict(heirarchy, heirarchy)
        return heirarchy

    def build_parent_child_heirarchy(
        self, issues: List[Any]
    ) -> Dict[Issue, Optional[List[Issue]]]:
        """Arrange the Issues into a parent/child heirarchy using the parent, subtasks and isseueLinks fields, where
        the inwardIssue for a Depend type is the child of the Issue holding that link.

        Args:
          issues (List[Any]): The list of issues to arrange

        Returns:
          A dictionary of Issues with their children or None if they have no children.
        """
        heirarchy = {issue: [] for issue in issues}
        for issue in issues:
            if "parent" in dir(issue.fields):
                parent = MyJiraCore.__get_issue_from_list_by_key(
                    issues, issue.fields.parent.key
                ) or self.jira.get_issue(issue.fields.parent.key)
                heirarchy[parent].append(issue)
            if issue.fields.subtasks:
                for subtask in issue.fields.subtasks:
                    subtask_issue = MyJiraCore.__get_issue_from_list_by_key(
                        issues, subtask.key
                    ) or self.jira.get_issue(subtask.key)
                    heirarchy[issue].append(subtask_issue)
            if issue.fields.issuelinks:
                for link in issue.fields.issuelinks:
                    if link.type.name == "Depend" and "outwardIssue" in dir(link):
                        child = MyJiraCore.__get_issue_from_list_by_key(
                            issues, link.outwardIssue.key
                        ) or self.jira.issue(link.outwardIssue.key)
                        heirarchy[issue].append(child)
        for key, value in heirarchy.items():
            heirarchy[key] = list(set(value))
        heirarchy = MyJiraCore.__compactify_heirarchy(heirarchy)
        pprint.pp(heirarchy)
        return heirarchy

"""jira.py

Scripts to connect to JIRA and access """

from typing import List, Tuple

from passpy import Store

from jira import JIRA, Issue
from jira.client import ResultList
from jira.resources import Comment, IssueLink
from src.config import JiraConfig
from src.dataclasses import TJIssue
from src.utils import get_password_from_store


class TJJira:
    """TJJira

    A class to mediate interactions with JIRA
    """

    def __init__(
        self,
        jira_config: JiraConfig,
        store: Store,
    ) -> None:
        """Initialisation script

        Args:
            jira_config (JiraConfig): A config class containing the connection details to JIRA
        """
        if password := get_password_from_store(
            store=store, pass_key=jira_config.API_PASS_KEY
        ):
            print("Establishing connection to JIRA")
            self.jira = JIRA(
                server=str(jira_config.JIRA_HOST),
                basic_auth=(
                    str(jira_config.USERNAME),
                    password,
                ),
            )
            self.current_user = jira_config.JIRA_USER or jira_config.USERNAME
            print("Connection established")
        else:
            raise ValueError("Unable to retrieve the API Key from the password store")

    def __get_issues(
        self,
        jql_search: str,
    ) -> ResultList[Issue]:
        """script to run a JQL search query on the JIRA instance

        Args:
            jql_search (str): A string representation of the JQL querr

        Example:
            For a JQL query returning all active issues associated with a particular user, where the
            query is::
                assignee = "Chris Seal" and status != closed and status != resolved and status != Done

        then the request would be::
            TJJira.__get_issues('assignee = "Chris Seal" and status != closed and status != resolved and status != Done')
        """
        return self.jira.search_issues(jql_search)

    def get_active_issues(self) -> ResultList[Issue]:
        """Wrapper around the __get_issues function to get active issues for the user"""
        sql_string = (
            f'assignee = "{self.current_user}" '
            #"and issuetype != Epic "
            #"and issuetype != Story "
            "and status != closed "
            "and status != resolved "
            "and status != Done"
        )
        return self.__get_issues(sql_string)

    def get_active_epics(self) -> ResultList[Issue]:
        "Wrapper around the __get_issues function to get the active Epics for the user"
        sql_string = (
            'project = "IDS" '
            "and issuetype = Epic "
            "and status != closed "
            "and status != resolved "
            "and status != Done"
        )
        return self.__get_issues(sql_string)

    def get_active_stories(self) -> ResultList[Issue]:
        "Wrapper around the __get_issues function to get the active Epics for the user"
        sql_string = (
            f'assignee = "{self.current_user}" '
            "and issuetype = Story "
            "and status != closed "
            "and status != resolved "
            "and status != Done"
        )
        return self.__get_issues(sql_string)

    def get_current_sprint(self) -> ResultList[Issue]:
        """Wrapper around the __get_issues function to get the currently active sprint"""
        sql_string = (
            f'assignee = "{self.current_user}" '
            "and sprint != NULL "
            "and sprint in openSprints()"
        )
        return self.__get_issues(sql_string)

    def get_issue_by_key(
        self,
        key: str,
    ) -> Issue:
        return self.jira.issue(key)

    @staticmethod
    def __process_comments(comments: List[Comment]) -> List[Tuple[str, str]]:
        return [(comment.author.displayName, comment.body) for comment in comments]

    def create_issue_dataclasses(
        self,
        issues: ResultList[Issue],
    ) -> List[TJIssue]:
        """Creates a list of TJIssue dataclasses that hold the active epics

        Returns:
            List[TJIssue]: list of epics as dataclasses
        """
        return_list = []
        if isinstance(issues, Issue):
            issues = [issues]
        for issue in issues:
            key = issue.key
            summary = f"{key} - {issue.fields.summary}"
            state = issue.fields.status
            priority = issue.fields.priority
            description = issue.fields.description
            comments = None
            links = None
            parent = None
            labels = None
            if issue.fields.comment.comments:
                comments = TJJira.__process_comments(issue.fields.comment.comments)
            if issue.fields.issuelinks:
                links = TJJira.__process_linked_issues(issue.fields.issuelinks)
            if issue.fields.labels:
                labels = list(issue.fields.labels)
            try:
                parent = issue.fields.parent.key
            except AttributeError:
                parent = None
            return_list.append(
                TJIssue(
                    key=key,
                    summary=summary,
                    state=str(state),
                    priority=str(priority),
                    description=description,
                    comments=comments,
                    links=links,
                    parent=parent,
                    issuetype=str(issue.fields.issuetype),
                    labels=labels,
                )
            )
        return return_list

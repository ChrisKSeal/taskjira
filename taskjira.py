"""taskjira.py

Run script to synchronise JIRA and taskwarrior"""

from passpy import Store

from src.config import JiraConfig, PassPyConfig
from src.jira import TJJira

jira_config = JiraConfig()
passpy_config = PassPyConfig()

store = Store(gpg_bin=passpy_config.GPG_BIN)

taskjira = TJJira(jira_config, store)

"""print(taskjira.jira.boards(name="Core MyTardis"))
print(taskjira.jira.sprints(50))
print(taskjira.jira.sprint(2747))
print(dir(taskjira.jira.sprint(2747)))"""

# active_issues = taskjira.get_active_issues()
active_epics = taskjira.create_issue_dataclasses(taskjira.get_active_epics())
active_stories = taskjira.create_issue_dataclasses(taskjira.get_active_stories())
active_tasks = taskjira.create_issue_dataclasses(taskjira.get_active_issues())

print(active_epics)
print(active_stories)
print(active_tasks)

"""for issue in active_issues:
    print(issue)
    print(issue.fields.issuetype)
    print(issue.fields.assignee)
    print(issue.fields.summary)
    print(issue.fields.description)
    print(issue.fields.issuelinks)
    if issue.fields.issuelinks:
        for link in issue.fields.issuelinks:
            print(link.raw)
    if issue.fields.comment.comments:
        for comment in issue.fields.comment.comments:
            print("Comment:", comment.body)
    if issue.fields.customfield_10020:
        for sprint_field in issue.fields.customfield_10020:
            print(sprint_field.name)
            print(sprint_field.startDate)
            print(sprint_field.endDate)
            print(sprint_field.state)
            print(sprint_field.completeDate)
    print(issue.fields.parent)
    print(issue.fields.status)"""

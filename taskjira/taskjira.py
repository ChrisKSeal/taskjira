"""taskjira.py

Run script to synchronise JIRA and taskwarrior"""

from passpy import Store

# from src.config import (IntergratorConfig, JiraConfig, PassPyConfig,
#                       TaskWarriorConfig)
# from src.integrations import Integrator
from src.jira import MyJiraCore
# from src.taskwarrior import TJTaskWarrior

# jira_config = JiraConfig()
# passpy_config = PassPyConfig()
# taskwarrior_config = TaskWarriorConfig()
# integrator_config = IntergratorConfig()
import pprint

store = Store(gpg_bin="/opt/homebrew/bin/gpg")

jira = MyJiraCore("c.seal@auckland.ac.nz", "https://aucklanduni.atlassian.net", store)
# taskjira_tw = TJTaskWarrior(taskwarrior_config)
# integrator = Integrator(
#    integrator_config,
#    taskjira_jira,
#    taskjira_tw,
# )


jql = '(assignee = currentUser() or assignee = "Unassigned") and status != closed and status != resolved and status != Done'
issue_list = jira.get_issues(jql)
heirarchy = jira.build_parent_child_heirarchy(issue_list)

# = integrator.pull_from_jira()
# integrator.push_to_taskwarrior(task_list)

"""print(taskjira.jira.boards(name="Core MyTardis"))
print(taskjira.jira.sprints(50))
print(taskjira.jira.sprint(2747))
print(dir(taskjira.jira.sprint(2747)))"""

"""# active_issues = taskjira.get_active_issues()
active_epics = taskjira_j.create_issue_dataclasses(taskjira_j.get_active_epics())
active_stories = taskjira_j.create_issue_dataclasses(taskjira_j.get_active_stories())
active_tasks = taskjira_j.create_issue_dataclasses(taskjira_j.get_active_issues())

print(active_epics)
print(active_stories)
print(active_tasks)

print(taskjira_j.create_issue_dataclasses(taskjira_j.get_current_sprint()))


print(taskjira_tw.get_active_tasks())"""

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

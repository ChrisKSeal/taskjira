"""integrations.py

Scripts to migrate to and from JIRA and TaskWarrior"""

import re

from src.config import IntergratorConfig
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

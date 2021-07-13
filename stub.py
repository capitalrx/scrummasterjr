import os
from scrummasterjr.jira import Jira
import logging

if __name__ == '__main__':

    logging.basicConfig(
        level=os.getenv('LOG_LEVEL', 'INFO')
    )

    jira_host = os.environ["JIRA_HOST"]
    jira_user = os.environ["JIRA_USER"]
    jira_token = os.environ["JIRA_TOKEN"]
    jira = Jira(jira_host, jira_user, jira_token)

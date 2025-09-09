import os, sys
from scrummasterjr.jira import Jira
from scrummasterjr.error import ScrumMasterJrError
import logging, re

if __name__ == '__main__':

    logging.basicConfig(
        level=os.getenv('LOG_LEVEL', 'INFO')
    )

    jira_host = os.environ["JIRA_HOST"]
    jira_user = os.environ["JIRA_USER"]
    jira_token = os.environ["JIRA_TOKEN"]
    jira = Jira(jira_host, jira_user, jira_token)

    teams = {
        "Emu": 30,
        "Fire Ferrets": 42,
        "Godzilla": 189,
        "Jedi": 157,
        "Whiskey": 126,
        "Paradise": 48,
        "Snacks": 27,
        "Unicorn": 89,
        "Atlantis": 92,
        "Yeet": 119,
        "Zeppelin": 883,
        "Merlin": 165,
        "Keto-memes": 162,
        "Command Z": 179,
        "Rambo": 182,
        "Data Matrix": 116,
        "Turing": 114,
        "HODL": 46,
        "Queso": 322,
        "Vigilante": 784,
        "Platform": 388,
        "Rosetta": 586,
        "T3quila": 620
    }

    f = open('all_sprint_data.txt', 'a')

    for team in teams.keys():
        print(f"Team = {team}")

        if len(sys.argv) > 1:
            sprint = jira.getMatchingSprintInBoard(teams[team], f"{sys.argv[1]}")
            try:
                data = jira.generateAllSprintReportData(sprint['id'])
                f.write(f"{team},{sprint['name']},{data['sprint_start']},{data['sprint_end']},{data['issue_metrics']['points']['committed']},{data['issue_metrics']['points']['completed']},{data['issue_metrics']['points']['planned_completed']},{data['issue_metrics']['points']['unplanned_completed']},{data['issue_metrics']['points']['feature_completed']},{data['issue_metrics']['points']['optimization_completed']},{data['issue_metrics']['points']['not_completed']},{data['issue_metrics']['points']['removed']},{data['issue_metrics']['items']['committed']},{data['issue_metrics']['items']['completed']},{data['issue_metrics']['items']['planned_completed']},{data['issue_metrics']['items']['unplanned_completed']},{data['issue_metrics']['items']['stories_completed']},{data['issue_metrics']['items']['unplanned_stories_completed']},{data['issue_metrics']['items']['bugs_completed']},{data['issue_metrics']['items']['unplanned_bugs_completed']},{data['issue_metrics']['items']['not_completed']},{data['issue_metrics']['items']['removed']},{data['issue_metrics']['items']['added']},{data['issue_metrics']['meta']['predictability']},{data['issue_metrics']['meta']['predictability_of_commitments']},{data['average_velocity']},{data['average_predictability']},{data['average_predictability_of_commitments']},,,,{data['issue_metrics']['points']['design_committed']},{data['issue_metrics']['points']['design_completed']},{data['issue_metrics']['points']['prod_support']}\n")
            except:
                continue

        else :
            sprints = jira.getSprintsInBoard(teams[team])
            for sprint in sprints:
                print(f"    Sprint = {sprint['name']}")
                if(re.search(team_letter, sprint['name'])):
                    try:
                        data = jira.generateAllSprintReportData(sprint['id'])
                        f.write(f"{team},{sprint['name']},{data['sprint_start']},{data['sprint_end']},{data['issue_metrics']['points']['committed']},{data['issue_metrics']['points']['completed']},{data['issue_metrics']['points']['planned_completed']},{data['issue_metrics']['points']['unplanned_completed']},{data['issue_metrics']['points']['feature_completed']},{data['issue_metrics']['points']['optimization_completed']},{data['issue_metrics']['points']['not_completed']},{data['issue_metrics']['points']['removed']},{data['issue_metrics']['items']['committed']},{data['issue_metrics']['items']['completed']},{data['issue_metrics']['items']['planned_completed']},{data['issue_metrics']['items']['unplanned_completed']},{data['issue_metrics']['items']['stories_completed']},{data['issue_metrics']['items']['unplanned_stories_completed']},{data['issue_metrics']['items']['bugs_completed']},{data['issue_metrics']['items']['unplanned_bugs_completed']},{data['issue_metrics']['items']['not_completed']},{data['issue_metrics']['items']['removed']},{data['issue_metrics']['items']['added']},{data['issue_metrics']['meta']['predictability']},{data['issue_metrics']['meta']['predictability_of_commitments']},{data['average_velocity']},{data['average_predictability']},{data['average_predictability_of_commitments']},,,,{data['issue_metrics']['points']['design_committed']},{data['issue_metrics']['points']['design_completed']},{data['issue_metrics']['points']['prod_support']}\n")
                    except:
                        continue


    f.close()

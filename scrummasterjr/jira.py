from requests.auth import HTTPBasicAuth
import requests
import logging
import re
import json
from datetime import datetime
from scrummasterjr.notionpage import NotionPage
from scrummasterjr.confluencepage import ConfluencePage
from scrummasterjr.error import ScrumMasterJrError

class Jira:
    __auth = None
    __token = None
    __url = None
    __greenhopper_url = None
    __agile_url = None
    __prefix = ''

    __regex = {}
    __descriptions = {}

    def __makeRequest(self, verb, url, params=None):
        """Wrapper for a simple HTTP request

            Args:
                verb: string - HTTP verb as string (ie. 'GET' or 'POST')
                url: string - URL to make HTTP requests against
                params: dictionary - Any request parameters to pass along (defaults to None)

            Returns:
                dictionary - A JSON represenatation of the response text, or False in the case of an error
        """
        response = requests.request(verb, url, headers={ 'Accept': 'application/json' }, auth=self.__auth, params=params)
        if response.status_code == 200:
            return(json.loads(response.text))
        else:
            logging.error(response.text)
            return(False)

    def __init__(self, host, user, token, prefix=False):
        self.__host = host
        self.__auth = HTTPBasicAuth(user, token)
        self.__prefix = f'{prefix} ' if prefix else ''

        self.__url = f"https://{self.__host}/rest/api/latest/"
        self.__agile_url = f"https://{self.__host}/rest/agile/latest/"
        self.__greenhopper_url = f"https://{self.__host}/rest/greenhopper/latest/"
        self.summary = {}

    def testConnection(self):
        """Tests the connection to Jira by getting user data"""
        url = f"{self.__url}/myself"

        response = self.__makeRequest('GET', url)

        return response

    def calculateSprintMetrics(self, sprint_report):
        """Given the data from a Jira sprint report, calculates sprint metrics

        Args:
            sprint_report: dictionary - the data from a Jira sprint reports

        Returns:
            dictionary - calculated metrics
        """
        points = {
            "committed": 0,
            "completed": 0,
            "planned_completed": 0,
            "unplanned_completed": 0,
            "feature_completed": 0,
            "optimization_completed": 0,
            "not_completed": 0,
            "removed": 0,
            "prod_support": 0,
            "design_committed": 0,
            "design_completed": 0,
            "added": 0,
            "bugs": 0,
            "by_label": {'committed': {}, 'completed': {}, 'added': {}, 'unplanned_completed': {}}
        }

        items = {
            "committed": 0,
            "completed": 0,
            "planned_completed": 0,
            "unplanned_completed": 0,
            "stories_completed": 0,
            "unplanned_stories_completed": 0,
            "bugs_completed": 0,
            "unplanned_bugs_completed": 0,
            "not_completed": 0,
            "removed": 0, 
            "design_committed": 0,
            "design_completed": 0,
            "prod_support": 0
        }

        issue_keys = {
            "committed": [],
            "completed": [],
            "incomplete": [],
            "removed": [],
            "prod_support": []
        }

        feature_work = ["Story", "Design", "Spike"]
        optimization = ["Optimization"]
        bug = ["Bug", "User Bug"]
        design = ["Design", "Design Spike"]
        ignore = ["Task", "Epic", "Retro Action Item", "Requirement", "Request", "Idea", "Test"]

        puntedKeys = [d["key"] for d in sprint_report["contents"]["puntedIssues"]]

        # Completed Work
        for completed in sprint_report["contents"]["completedIssues"]:

            # Short-circuit for things we don't track
            if completed["typeName"] in ignore:
                continue

            unplanned = False
            if completed["key"] in sprint_report["contents"]["issueKeysAddedDuringSprint"].keys():
                unplanned = True

            issue_keys["completed"].append(completed["key"])

            try:
                issue_points_original = round(completed["estimateStatistic"]["statFieldValue"]["value"])
            except:
                issue_points_original = 0

            try:
                issue_points = round(completed["currentEstimateStatistic"]["statFieldValue"]["value"])
            except:
                issue_points = 0

            points["completed"] += issue_points
            items["completed"] += 1

            for label in completed["labels"]:
                points["by_label"]['completed'][label] = points["by_label"]['completed'].get(label, 0) + issue_points
                
            if unplanned:
                points["unplanned_completed"] += issue_points
                items["unplanned_completed"] += 1
                points["added"] += issue_points
                for label in completed["labels"]:
                    points["by_label"]['added'][label] = points["by_label"]['added'].get(label, 0) + issue_points
                    points["by_label"]['unplanned_completed'][label] = points["by_label"]['unplanned_completed'].get(label, 0) + issue_points

            else:
                issue_keys["committed"].append(completed["key"])
                points["committed"] += issue_points_original
                items["committed"] += 1
                points["planned_completed"] += issue_points
                items["planned_completed"] += 1
                if issue_points_original < issue_points:
                    points["planned_completed"] += issue_points-issue_points_original
                for label in completed["labels"]:
                    points["by_label"]['committed'][label] = points["by_label"]['committed'].get(label, 0) + issue_points
                    
            # Story
            if completed["typeName"] == "Story":
                items["stories_completed"] += 1
                if unplanned:
                    items["unplanned_stories_completed"] += 1

            # Story / Design / Spike (Feature Work)
            if completed["typeName"] in feature_work:
                points["feature_completed"] += issue_points

            # Optimization
            if completed["typeName"] in optimization:
                points["optimization_completed"] += issue_points

            # Bugs
            if completed["typeName"] in bug:
                items["bugs_completed"] += 1
                points["bugs"] += issue_points
                if unplanned:
                    items["unplanned_bugs_completed"] += 1

            # Design
            if completed["typeName"] in design:
                items["design_completed"] += 1
                points["design_completed"] += issue_points
                if not unplanned:
                    items["design_committed"] += 1
                    points["design_committed"] += issue_points

            # Prod Support
            if "prod_support" in completed["labels"]:
                points["prod_support"] += issue_points
                items["prod_support"] += 1
                issue_keys["prod_support"].append(completed["key"])
                
        # Incomplete Work
        for incomplete in sprint_report["contents"]["issuesNotCompletedInCurrentSprint"]:

            # Short-circuit for things we don't track
            if incomplete["typeName"] in ignore:
                continue

            unplanned = False
            if incomplete["key"] in sprint_report["contents"]["issueKeysAddedDuringSprint"].keys():
                unplanned = True
            
            issue_keys["incomplete"].append(incomplete["key"])

            try:
                issue_points = round(incomplete["currentEstimateStatistic"]["statFieldValue"]["value"])
            except:
                issue_points = 0

            try:
                issue_points_original = round(incomplete["estimateStatistic"]["statFieldValue"]["value"])
            except:
                issue_points_original = 0

            points["not_completed"] += issue_points
            items["not_completed"] += 1

            if not unplanned:
                issue_keys["committed"].append(incomplete["key"])
                points["committed"] += issue_points_original
                items["committed"] += 1

                for label in incomplete["labels"]:
                    points["by_label"]['committed'][label] = points["by_label"]['committed'].get(label, 0) + issue_points
                    
                if incomplete["typeName"] in design:
                    items["design_committed"] += 1
                    points["design_committed"] += issue_points_original
            else:
                points["added"] += issue_points
                for label in incomplete["labels"]:
                    points["by_label"]['added'][label] = points["by_label"]['added'].get(label, 0) + issue_points

        # Removed Work
        for removed in sprint_report["contents"]["puntedIssues"]:

            # Short-circuit for things we don't track
            if removed["typeName"] in ignore:
                continue

             # Short-circuit for issues that were added and then removed
            unplanned = False
            if removed["key"] in sprint_report["contents"]["issueKeysAddedDuringSprint"].keys():
                unplanned = True
                if removed["key"] in puntedKeys:
                    continue

            issue_keys["removed"].append(removed["key"])

            try:
                issue_points = round(removed["currentEstimateStatistic"]["statFieldValue"]["value"])
            except:
                issue_points = 0

            try:
                issue_points_original = round(removed["estimateStatistic"]["statFieldValue"]["value"])
            except:
                issue_points_original = 0

            if not unplanned:
                points["committed"] += issue_points_original
                items["committed"] += 1
                issue_keys["committed"].append(removed["key"])
                
            points["removed"] += issue_points
            items["removed"] += 1

        meta = {
            "predictability": 0,
            "predictability_of_commitments": 0
        }

        #Added Work
        issue_keys["added"] = list(set(sprint_report["contents"]["issueKeysAddedDuringSprint"].keys()) - set(puntedKeys))
        items["added"] = len(issue_keys["added"])

        if points['committed'] != 0:
            meta['predictability'] = round(points['completed']/points['committed']*100)
            meta['predictability_of_commitments'] = round(points['planned_completed']/points['committed']*100)
        else:
            # If a sprint has no points committed, we say the predictability is 0
            logging.warning('This sprint had no commitments, predictability is 0')

        return {
            "points" : points,
            "items" : items,
            "issue_keys": issue_keys,
            "meta": meta
        }

    def getSprint(self, sprint_id):
        """Utility funtion to get sprint data from Jira

        Args:
            sprint_id: string - the id of a Jira sprint

        Returns:
            dictionary - A JSON encoded represenatation of the Jira sprint object
        """
        # Get Jira Sprint Object (including Board reference) from Sprint ID
        sprint = self.__makeRequest('GET', f"{self.__agile_url}sprint/{sprint_id}")
        if not sprint:
            raise ScrumMasterJrError(f"I could not find sprint with id {sprint_id}. Please check your arguments again. Are you using the right command for your jira instance? Ask me for `help` for more information")

        return sprint

    def getBoard(self, board_id):
        """Utility funtion to get board data from Jira

        Args:
            board_id: string - the id of a Jira board

        Returns:
            dictionary - A JSON encoded represenatation of Jira board object
        """
        board = self.__makeRequest('GET', f"{self.__agile_url}board/{board_id}")
        if not board:
            raise ScrumMasterJrError(f"Could not find boad with id {board_id}. Please check your arguments again. Are you using the right command for your jira instance? Ask me for `help` for more information")

        return board

    def getSprintReport(self, sprint_id, board_id):
        """Utility funtion to get sprint report data from Jira

        Args:
            sprint_id: string - the id of a Jira sprint
            board_id: string - the id of a Jira board

        Returns:
            dictionary - A JSON encoded represenatation of a Jira Sprint Report for the given sprint and board
        """
        sprint_report = self.__makeRequest('GET',f"{self.__greenhopper_url}rapid/charts/sprintreport?rapidViewId={board_id}&sprintId={sprint_id}")
        if not sprint_report:
            raise ScrumMasterJrError(f"Could not find report for sprint {sprint_id} on board {board_id}. Please check your arguments again. Are you using the right command for your jira instance? Ask me for `help` for more information")

        return sprint_report

    def getSprintMetricsCommand(self, message):
        """User-friendly wrapper for getting the metrics for a given sprint

        Args:
            message: string - the message from the user that initiated this command

        Returns:
            dictionary - A slack message response
        """
        try:
            sprintid = re.search('sprint metrics ([0-9]+)', message).group(1)
        except :
            logging.error(f"Did not find a sprint number in: '{message}'")
            return {'text': "Sorry, I don't see a valid sprint number there"}

        sprint = self.getSprint(sprintid)
        sprint_report = self.getSprintReport(sprintid, sprint['originBoardId'])
        metrics = self.calculateSprintMetrics(sprint_report)

        metrics_text = json.dumps(metrics, sort_keys=True, indent=4, separators=(",", ": "))

        return {'text': f"```{metrics_text}```"}

    def getJiraSprintReportData(self, sprint_report):
        """Utility funtion to parse general sprint information from a Jira sprint report

        Args:
            sprint_report: string - raw data from a Jira Sprint Report

        Returns:
            dictionary - relevant information parsed from the report
        """
        report = {}

        try:
            report['sprint_number'] = re.search(r'(?i)(S|Sprint |\d*\.)(?P<number>\d+)', sprint_report["sprint"]["name"]).group('number')
        except AttributeError:
            report['sprint_number'] = 'XXX'
            
        try:
            report['sprint_start'] = sprint_report['sprint']['startDate']
            report['sprint_end'] = sprint_report['sprint']['endDate']
        except KeyError:
            # Every sprint doesn't have a start / end date
            logging.warning('This sprint does not have start and/or end dates')

        try:
            report['sprint_goals'] = sprint_report['sprint']['goal'].split("\n")
        except (AttributeError, KeyError):
            pass
            #raise ScrumMasterJrError(f"I couldn't find or parse sprint goal for one of your sprints. Please check your arguments again, but this might not be your fault so I've let my overlords know. Are you using the right command for your jira instance? Ask me for `help` for more information", f"Unable to find or parse sprint goal\n {sprint_report}")

        return report

    def generateAllSprintReportData(self, sprint_id):
        """Congomerates all the data from different Jira reports into one holistic Sprint Report data-set

        Args:
            sprint_id: string - the id of a Jira sprint

        Returns:
            dictionary - the information necessary for creating an AgileOps Sprint Report
        """
        report = {}

        sprint = self.getSprint(sprint_id)
        sprint_report = self.getSprintReport(sprint_id, sprint['originBoardId'])
        report = self.getJiraSprintReportData(sprint_report)
        report['issue_metrics'] = self.calculateSprintMetrics(sprint_report)
        board = self.getBoard(sprint['originBoardId'])
        report['project_name'] = board['location']['projectName']
        report['project_key'] = board['location']['projectKey']
        report['average_velocity'] = self.getAverageVelocity(sprint['originBoardId'], sprint_id)

        [report['average_predictability'], report['average_predictability_of_commitments'], report['average_prod_support'], report['average_design'], report['average_unplanned_completed']] = self.getAveragePredictabilities(sprint['originBoardId'], sprint_id)

        return report

    def updateNotionPage(self, notion_url, sprint_report_data, next_sprint_report_data=False):
        """Updates the notion page at the url with the sprint report data using a search / replace mechanism

        Args:
            notion_url: string - the URL to a notion page
            sprint_report_data: dictionary - AgileOps Sprint Report Data
            next_sprint_report_data: dictionary - AgileOps Sprint Report Data for the subsequent sprint (defaults to False if there is no next sprint)

        Returns:
            A BaseException if there was a problem
            boolean - False if everything ran smoothly
        """
        search_replace_dict = self.generateNotionReplacementDictionary(sprint_report_data)

        if next_sprint_report_data:
            search_replace_dict.update(self.generateNextSprintNotionReplacementDictionary(next_sprint_report_data))

        try:
            page = ConfluencePage(notion_url)
            logging.info(f"Notion Page: {page}")
            page.searchAndReplace(search_replace_dict)
        except BaseException as e:
            return e

        return False

    def getAverageVelocity(self, board_id, sprint_id = None):
        """"Gets the 3 sprint average velocity for a board as of a specific sprint

        Args:
            board_id: string - the id of a Jira board
            sprint_id: string - the id of a Jira sprint (defaults to None, in which case it assumes the most recently completely sprint)

        Returns:
            integer - The 3 sprint average velocity for the board_id as of the sprint_id provided
        """
        velocity_report = self.__makeRequest('GET',f"{self.__greenhopper_url}rapid/charts/velocity?rapidViewId={board_id}")

        if velocity_report == False:
            raise ScrumMasterJrError(f"I wasn't able to get the velocity report for board {board_id}. Please check your arguments again. Are you using the right command for your jira instance? Ask me for `help` for more information")

        total = 0
        sprints = 0
        found_sprint = True if sprint_id == None else False

        sprint_id = f"{sprint_id}"

        for sprint in sorted(velocity_report['velocityStatEntries'], reverse=True):
            if sprints >= 3:
                # We only care about the last three sprints
                break;

            if found_sprint == True or sprint_id == sprint:
                found_sprint = True
                total = total +  velocity_report['velocityStatEntries'][sprint]['completed']['value']
                sprints = sprints + 1

        return round(total/sprints) if sprints > 0 else total

    def generateGoogleFormURL(self, sprint_report_data):
        """Generates a URL that will pre-populate a specific AgileOps Google Form where teams submit their sprint metrics

        Args:
            sprint_report_data: dictionary - AgileOps Sprint Report Data

        Returns:
            string - A URL to a google form with relevant information pre-populate via query parameters
        """
        url = 'https://docs.google.com/forms/d/e/1FAIpQLSdF__V1ZMfl6H5q3xIQhSkeZMeCNkOHUdTBFdYA1HBavH31hA/formResponse?'

        google_entry_translations = {
        "issue_metrics": {
            "items": {
                "bugs_completed": 'entry.448087930',
                "committed": 'entry.2095001800',
                "completed": 'entry.1399119358',
                "not_completed": 'entry.128659456',
                "planned_completed": 'entry.954885633',
                "removed": 'entry.1137054034',
                "stories_completed": 'entry.1980453543',
                "unplanned_bugs_completed": 'entry.1252702382',
                "unplanned_completed": 'entry.485777497',
                "unplanned_stories_completed": 'entry.370334542'
            },
            "points": {
                "committed": 'entry.1427603868',
                "completed": 'entry.1486076673',
                "feature_completed": 'entry.254612996',
                "not_completed": 'entry.611444996',
                "optimization_completed": 'entry.2092919144',
                "planned_completed": 'entry.493624591',
                "removed": 'entry.976792423',
                "unplanned_completed": 'entry.1333444050'
            }
        },
        #TODO: We're assuming that the project name IS the team name, which isn't always the case
        "project_key": "entry.1082637073",
        "sprint_number": "entry.1975251686"
        }

        try:
            for entry in ["project_key", "sprint_number"]:
                url += f"{google_entry_translations[entry]}={sprint_report_data[entry]}&"

            for metric_type in sprint_report_data['issue_metrics'].keys():
                if metric_type in ["meta", "issue_keys"]:
                    continue
                for item in sprint_report_data['issue_metrics'][metric_type].keys():
                    url += f"{google_entry_translations['issue_metrics'][metric_type][item]}={sprint_report_data['issue_metrics'][metric_type][item]}&"
        except (KeyError):
            raise ScrumMasterJrError("I wasn't able to generate a Google Form URl for some reason. This probably isn't your fault, I've let my overlords know.", "Unable to generate Google Form URL, expected keys missing")

        url += "submit=Submit"

        return url

    def generateNextSprintNotionReplacementDictionary(self, sprint_report_data):
        """
        Generates a dictionary who's keys are special tags placed in notion docs like `[sprint-number]` and values are the relevant data.

        This function assumes that the data being passed in is for the 'next sprint' and acts accordingly

        Args:
            sprint_report_data: dictionary - AgileOps Sprint Report data

        Returns:
            dictionary - key / value pairs that will facilitate a search and replace in a notion document to populate it with relevant data
        """
        notion_dictionary = {}

        try:
            start_date = datetime.strptime(sprint_report_data['sprint_start'].split('T')[0], '%d/%b/%y %I:%M %p')
            notion_dictionary['[next-sprint-start]'] = datetime.strftime(start_date, '%m/%d/%Y')
        except ValueError:
            pass

        try:
            end_date = datetime.strptime(sprint_report_data['sprint_end'].split('T')[0], '%d/%b/%y %I:%M %p')
            notion_dictionary['[next-sprint-end]'] = datetime.strftime(end_date, '%m/%d/%Y')
        except ValueError:
            pass

        try:
            notion_dictionary['[next-sprint-number]'] = sprint_report_data['sprint_number']

            notion_dictionary['[next-sprint-goal]'] = "\n".join(sprint_report_data['sprint_goals'])

            notion_dictionary['[next-points-committed]'] = str(sprint_report_data['issue_metrics']['points']['committed'])
            notion_dictionary['[next-items-committed]'] = str(sprint_report_data['issue_metrics']['items']['committed'])

            notion_dictionary['[next-original-committed-link]'] =f"[{sprint_report_data['issue_metrics']['items']['committed']} Committed Issues]({self.generateJiraIssueLink(sprint_report_data['issue_metrics']['issue_keys']['committed'])})"

        except KeyError:
            pass
            #raise ScrumMasterJrError("I wasn't able to update your Notion Doc for some reason. This probably isn't your fault, I've let my overlords know.", "Unable to generate a *Next Sprint* Notion Replacement Dictionary, keys not found")

        return notion_dictionary

    def generateNotionReplacementDictionary(self, sprint_report_data):
        """
        Generates a dictionary who's keys are special tags placed in notion docs like `[sprint-number]` and values are the relevant data.

        This function assumes that the data being passed in is for the 'current sprint' and acts accordingly

        Args:
            sprint_report_data: dictionary - AgileOps Sprint Report data

        Returns:
            dictionary - key / value pairs that will facilitate a search and replace in a notion document to populate it with relevant data
        """
        notion_dictionary = {}

        try:
            start_date = datetime.strptime(sprint_report_data['sprint_start'].split('T')[0], '%d/%b/%y %I:%M %p')
            end_date = datetime.strptime(sprint_report_data['sprint_end'].split('T')[0], '%d/%b/%y %I:%M %p')
            notion_dictionary['[sprint-start]'] = datetime.strftime(start_date, '%m/%d/%Y')
            notion_dictionary['[sprint-end]'] = datetime.strftime(end_date, '%m/%d/%Y')

        except ValueError:
            pass

        try:

            notion_dictionary['[team-name]'] = sprint_report_data['project_name']
            notion_dictionary['[sprint-number]'] = sprint_report_data['sprint_number']
            
            notion_dictionary['[sprint-goal]'] = "\n".join(sprint_report_data['sprint_goals'])
            notion_dictionary['[points-committed]'] = str(sprint_report_data['issue_metrics']['points']['committed'])
            notion_dictionary['[points-completed]'] = str(sprint_report_data['issue_metrics']['points']['completed'])

            notion_dictionary['[items-committed]'] = str(sprint_report_data['issue_metrics']['items']['committed'])
            notion_dictionary['[items-completed]'] = str(sprint_report_data['issue_metrics']['items']['completed'])
            notion_dictionary['[items-added]'] = str(sprint_report_data['issue_metrics']['items']['added'])
            notion_dictionary['[bugs-completed]'] = str(sprint_report_data['issue_metrics']['items']['bugs_completed'])

            notion_dictionary['[predictability]'] = str(sprint_report_data['issue_metrics']['meta']['predictability']) + "%"
            notion_dictionary['[predictability-commitments]'] = str(sprint_report_data['issue_metrics']['meta']['predictability_of_commitments']) + "%"
            notion_dictionary['[average-velocity]'] = str(sprint_report_data['average_velocity'])

            notion_dictionary['[original-committed-link]'] =f"<a href=\"{self.generateJiraIssueLink(sprint_report_data['issue_metrics']['issue_keys']['committed'])}\">{sprint_report_data['issue_metrics']['items']['committed']} Originally Committed Issues</a>"

            notion_dictionary['[completed-issues-link]'] = f"<a href=\"{self.generateJiraIssueLink(sprint_report_data['issue_metrics']['issue_keys']['completed'])}\">{sprint_report_data['issue_metrics']['items']['completed']} Completed Issues</a>"

            notion_dictionary['[items-not-completed-link]'] = f"<a href=\"{self.generateJiraIssueLink(sprint_report_data['issue_metrics']['issue_keys']['incomplete'])}\">{sprint_report_data['issue_metrics']['items']['not_completed']} Incomplete Issues</a>"

            notion_dictionary['[items-removed-link]'] = f"<a href=\"{self.generateJiraIssueLink(sprint_report_data['issue_metrics']['issue_keys']['removed'])}\">{sprint_report_data['issue_metrics']['items']['removed']} Removed Issues</a>"

            notion_dictionary['[items-added-link]'] = f"<a href=\"{self.generateJiraIssueLink(sprint_report_data['issue_metrics']['issue_keys']['added'])}\">{sprint_report_data['issue_metrics']['items']['added']} Added Issues</a>"

            notion_dictionary['[average-predictability]'] = f"{sprint_report_data['average_predictability']}%"
            notion_dictionary['[average-commitment-predictability]'] = f"{sprint_report_data['average_predictability_of_commitments']}%"

            notion_dictionary['[design-committed]'] = str(sprint_report_data['issue_metrics']['items']['design_committed'])
            notion_dictionary['[design-completed]'] = str(sprint_report_data['issue_metrics']['items']['design_completed'])
            notion_dictionary['[average-design]'] = f"{round(sprint_report_data['average_design']/sprint_report_data['average_velocity']*100)}%"
            notion_dictionary['[average-design-points]'] = str(sprint_report_data['average_design'])
            notion_dictionary['[design-points-committed]'] = str(sprint_report_data['issue_metrics']['points']['design_committed'])
            notion_dictionary['[design-points-completed]'] = str(sprint_report_data['issue_metrics']['points']['design_completed'])

            notion_dictionary['[items-planned-completed]'] = str(sprint_report_data['issue_metrics']['items']['planned_completed'])
            notion_dictionary['[items-not-completed]'] = str(sprint_report_data['issue_metrics']['items']['not_completed'])

            notion_dictionary['[items-prod-support]'] = str(sprint_report_data['issue_metrics']['items']['prod_support'])
            notion_dictionary['[points-prod-support]'] = str(sprint_report_data['issue_metrics']['points']['prod_support'])
            notion_dictionary['[average-prod-support]'] = f"{round(sprint_report_data['average_prod_support']/sprint_report_data['average_velocity']*100)}%"
            notion_dictionary['[average-prod-support-points]'] = str(sprint_report_data['average_prod_support'])

            notion_dictionary['[average-unplanned-completed]'] = f"{round(sprint_report_data['average_unplanned_completed']/sprint_report_data['average_velocity']*100)}%"
            notion_dictionary['[average-unplanned-completed-points]'] = str(sprint_report_data['average_unplanned_completed'])

            dev_points = sprint_report_data['issue_metrics']['points']['completed'] - sprint_report_data['issue_metrics']['points']['design_completed']
            notion_dictionary['[dev-points]'] = str(dev_points)

            # These expect to be called with some additional summary context from a Conluence / Notion doc and will bail if we don't have that
            notion_dictionary['[dev-count]'] = str(self.summary['dev_count'])
            notion_dictionary['[designer-count]'] = str(self.summary['designer_count'])

            notion_dictionary['[points-per-dev]'] = str(round(dev_points / self.summary['dev_count'])) if self.summary['dev_count'] else "N/A"
            notion_dictionary['[points-per-designer]'] = str(round(sprint_report_data['issue_metrics']['points']['design_completed'] / self.summary['designer_count'])) if self.summary['designer_count'] else "N/A"

        except KeyError:
            pass
            #raise ScrumMasterJrError("I wasn't able to update your Notion Doc for some reason. This probably isn't your fault, I've let my overlords know.", "Unable to generate a Notion Replacement Dictionary, keys not found")

        return notion_dictionary

    def generateJiraIssueLink(self, issues):
        """Generates a link to a collection of Jira issues

        Args:
            issues: list - Jira issue id's

        Returns:
            string - A Jira link that will display the passed in issues
        """
        link =  f"https://{self.__host}/issues/?jql=issueKey%20in%20("

        for issue in issues:
            link += f"{issue}%2C"

        link = re.sub(r'\%2C$', '', link) + ")"

        return link

    def getBoardsInProject(self, projectkey):
        link = ""
        try:
            link = f"{self.__agile_url}board?projectKeyOrId={projectkey.upper()}"
            results = self.__makeRequest('GET', link)
            if results:
                return results
        except AttributeError:
            pass

        return False

    def getSprintsInBoard(self, board_id):
        # We handle pagination by using `startAt`.
        # Because how sprints are returned (oldest first) we will reverse the list before return.
        link = f"{self.__agile_url}board/{board_id}/sprint"
        sprints = []
        startAt = 0
        while True:
            # Get list of sprints, if this is not the start, then start at `startAt`
            url = f'{link}?startAt={startAt}' if startAt > 0 else link
            results = self.__makeRequest('GET', url)
            logging.debug(f"Sprint Results: {results}")

            if results:
                sprints.extend(results['values'])
                startAt += len(results['values'])

            if (not results) or (results.get('isLast', True)):
                # break from while if results is false or `isLast` is True.
                break

        # if the 'sprints' array is empty it'll still return a falsy object
        # no need to explicitly return "false"
        sprints.reverse()
        logging.debug(f"Sprints: {sprints}")
        return sprints

    def getMatchingSprintInBoard(self, board_id, contains):
        all_sprints = self.getSprintsInBoard(board_id)

        for sprint in all_sprints:
            if re.search(contains, sprint['name']):
                return sprint

    def updateSummaryNotionDictionary(self):
        notion_dictionary = {}

        if 'board_id' in self.summary.keys():
            logging.info(f"We have a board: {self.summary['board_id']}")

            if 'current_sprint' in self.summary.keys():
                sprint = self.getMatchingSprintInBoard(self.summary['board_id'], f"{self.summary['current_sprint']}{self.summary['specific_sprint_name_match']}")
                if sprint:
                    logging.info(f"We have a sprint: {sprint}")
                    data = self.generateAllSprintReportData(sprint['id'])
                    dictionary = self.generateNotionReplacementDictionary(data)
                    notion_dictionary.update(dictionary)
                else:
                    logging.info("Couldn't find sprint, moving on")

            if 'next_sprint' in self.summary.keys():
                sprint = self.getMatchingSprintInBoard(self.summary['board_id'], f"{self.summary['next_sprint']}{self.summary['specific_sprint_name_match']}")
                if sprint:
                    data = self.generateAllSprintReportData(sprint['id'])
                    dictionary = self.generateNextSprintNotionReplacementDictionary(data)
                    notion_dictionary.update(dictionary)

        logging.info(f"Updating notion_dictionary\n{notion_dictionary}\nContext:\n{self.summary}")

        return notion_dictionary

    def setSummaryCurrentSprint (self, sprint):
        self.summary['current_sprint'] = sprint
        return self.updateSummaryNotionDictionary()

    def setSummaryNextSprint(self, next_sprint):
        self.summary['next_sprint'] = next_sprint
        return self.updateSummaryNotionDictionary()

    def setSummaryBoardID(self, board_id, specific_sprint_name_match = "", dev_count = 0, designer_count = 0):
        self.summary['board_id'] = board_id
        self.summary['specific_sprint_name_match'] = specific_sprint_name_match
        self.summary['dev_count'] = int(dev_count) if dev_count else 0
        self.summary['designer_count'] = int(designer_count) if designer_count else 0
        return self.updateSummaryNotionDictionary()

    def updateSummary(self, tag):
        logging.info(f"Found Summary Update Tag: {tag}")
        results = re.search('\[(?P<tag>[\w-]+) (?P<value>[\d\.]+)( (?P<arg>[\w\.]+))?( (?P<arg2>[\d\.]+))?( (?P<arg3>[\d\.]+))?\]', tag)
        if results:
            if results.group('tag') == 'sprint':
                return self.setSummaryCurrentSprint(results.group('value'))
            if results.group('tag') == 'next-sprint':
                return self.setSummaryNextSprint(results.group('value'))
            if results.group('tag') == 'board':
                return self.setSummaryBoardID(results.group('value'), results.group('arg'), results.group('arg2'), results.group('arg3'))
        return {}

    def updateNotionSummaryPage(self, notion_url):
        self.summary = {}
        self.summary['page'] = ConfluencePage(notion_url)

        stopping_block_patterns = ['\[sprint ', '\[next-sprint ', '\[board ']

        self.summary['page'].searchAndReplace({}, stopping_block_patterns, self.updateSummary)

    def getAveragePredictabilities(self, board_id, sprint_id):
        sprints = self.getSprintsInBoard(board_id)
        found = False
        found_sprints = 0
        completed = 0
        committed = 0
        planned_completed = 0
        prod_support = 0
        design = 0
        unplanned_completed = 0

        for sprint in sprints:
            if sprint['id'] == sprint_id:
                found = True
            if found and found_sprints < 3:
                sprint_report = self.getSprintReport(sprint['id'], board_id)
                report = self.getJiraSprintReportData(sprint_report)
                metrics = self.calculateSprintMetrics(sprint_report)
                completed += metrics['points']['completed']
                committed += metrics['points']['committed']
                planned_completed += metrics['points']['planned_completed']
                prod_support += metrics['points']['prod_support']
                design += metrics['points']['design_completed']
                unplanned_completed += metrics['points']['unplanned_completed']
                found_sprints += 1

        return (round(completed / committed*100) if committed else 0, 
                round(planned_completed / committed*100) if committed else 0, 
                round(prod_support / found_sprints) if found_sprints else 0, 
                round(design / found_sprints) if found_sprints else 0,
                round(unplanned_completed / found_sprints) if found_sprints else 0)


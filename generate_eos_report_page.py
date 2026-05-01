import os, logging, re, datetime

from atlassian import Confluence

if __name__ == '__main__':

    logging.basicConfig(
        level=os.getenv('LOG_LEVEL', 'INFO')
    )

    confluence = Confluence(
        url=f"https://{os.environ['JIRA_HOST']}",
        username=os.environ["JIRA_USER"],
        password=os.environ["JIRA_TOKEN"]
    )

    template_page_id = os.environ["TEMPLATE_PAGE_ID"]
    parent_page_id = os.environ["PARENT_PAGE_ID"]

    # Find the last EOS
    children = confluence.get_child_pages(parent_page_id)
    *_, last_child = children

    match = re.search(r'(\d+) Report - (\d+\/\d+) to (\d+\/\d+)', last_child['title'])
    if match: 
        now = datetime.datetime.now()
        previous_end = datetime.datetime.strptime(f"{match.group(3)}/{now.strftime('%y')}", "%m/%d/%y")

        # Assume that this is going to run on the Monday before the sprint ending on Wednesday
        if previous_end > now-datetime.timedelta(days=7):
            print(f"Previous EOS ended on {match.group(3)} and we need to wait until next week to cut a new one")
            exit(1)

        current_sprint_number = int(match.group(1))+1
        current_sprint_string = f"{now.strftime('%y')}.{current_sprint_number:02}"
        next_sprint = f"{now.strftime('%y')}.{current_sprint_number+1:02}"
        previous_sprint = f"{now.strftime('%y')}.{current_sprint_number-1:02}"
        
        start_date = (now-datetime.timedelta(days=12)).strftime('%m/%d')
        end_date = (now+datetime.timedelta(days=2)).strftime('%m/%d')

        source = confluence.get_page_by_id(template_page_id, expand='body.storage')
        newbody = source['body']['storage']['value']

        newbody = re.sub(r'\[sprint {sprint number}\]', f'[sprint {current_sprint_string}]', newbody)
        newbody = re.sub(r'\[next-sprint {sprint number}\]', f'[next-sprint {next_sprint}]', newbody)
        newbody = re.sub(r'\[previous-sprint {sprint number}\]', f'[previous-sprint {previous_sprint}]', newbody)

        dest = confluence.update_or_create(parent_page_id, f"[PENDING METRICS] End of Sprint {current_sprint_number} Report - {start_date} to {end_date}", newbody)
    else: 
        print("Last child in parent does not match EOS title formatting")
        exit(1)

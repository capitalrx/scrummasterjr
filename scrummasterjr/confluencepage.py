import os

from atlassian import Confluence

from datetime import datetime
import logging
import re
from collections import deque

from bs4 import BeautifulSoup

class ConfluencePage:

    def __init__(self, page_url):
        self.__client = Confluence(
            url=f"https://{os.environ['JIRA_HOST']}",
            username=os.environ["JIRA_USER"],
            password=os.environ["JIRA_TOKEN"]
        )
        self.page_id = re.search("(\d*)\/[^\/]*$", page_url).groups()[0]
        logging.info(f"Page URL: {page_url}\nPage ID: {self.page_id}")
        self.page = self.__client.get_page_by_id(self.page_id, expand='body.storage')
        self.contents = self.page['body']['storage']['value']
        self.queue = None

    def searchAndReplace(self, replacement_dictionary, stopping_block_patterns = [], dictionary_update_callback = None):
        soup = BeautifulSoup(self.contents, 'html.parser')
        self.queue = deque(soup.contents[0].contents)

        logging.info(f"Replacement Dictionary\n{replacement_dictionary}")

        total_items_committed = 0
        total_items_completed = 0
        total_items_planned_completed = 0
        total_commitment_predictability = 0

        checkSprintGoals = False
        if "[sprint-goal]" in replacement_dictionary:
            checkSprintGoals = True

        checkNextSprintGoals = False
        if "[next-sprint-goal]" in replacement_dictionary:
            checkNextSprintGoals = True

        while self.queue:
            block = self.queue.popleft()
            logging.info(f"Processing Block: {block}")

            try:
                self.queue.extendleft(block.contents[::-1])
                continue
            except AttributeError:
                logging.info("Block has no more children, end of the line")

            try:
                for pattern in stopping_block_patterns:
                    if re.match(pattern, block.string):
                        replacement_dictionary = dictionary_update_callback(block.string)

                        total_items_committed += int(replacement_dictionary['[items-committed]']) if '[items-committed]' in replacement_dictionary else 0
                        total_items_completed += int(replacement_dictionary['[items-completed]']) if '[items-completed]' in replacement_dictionary else 0
                        total_items_planned_completed += int(replacement_dictionary['[items-planned-completed]']) if '[items-planned-completed]' in replacement_dictionary else 0
                        total_commitment_predictability = f"{round(total_items_planned_completed / total_items_committed*100)}%" if total_items_committed > 0 else "N/A"

                        replacement_dictionary['[total-items-committed] items committed'] = str(total_items_committed)
                        replacement_dictionary['[total-items-completed]'] = str(total_items_completed)
                        replacement_dictionary['[total-items-planned-completed]'] = str(total_items_planned_completed)
                        replacement_dictionary['[total-commitment-predictability]'] = total_commitment_predictability

                        block.replace_with()
                        if "[next-sprint-goal]" in replacement_dictionary:
                            checkNextSprintGoals = True
                        if "[sprint-goal]" in replacement_dictionary:
                            checkSprintGoals = True
                        
                        logging.info(f"Replacement Dictionary\n{replacement_dictionary}")
                        continue


                if checkSprintGoals and "[sprint-goal]" in block.string:
                    parent = block.parent
                    logging.info(f"Parent: {parent}")
                    list = soup.new_tag('ac:task-list')
                    try:
                        for goal in replacement_dictionary['[sprint-goal]'].split("\n"):
                            list_item = soup.new_tag('ac:task')
                            p_item = soup.new_tag('ac:task-status')
                            p_item.string = "incomplete"
                            list_item.append(p_item)
                            p_item = soup.new_tag('ac:task-body')
                            p_item.string = goal
                            list_item.append(p_item)
                            list.append(list_item)
                        parent.replace_with(list)
                    except (KeyError):
                        pass
                    continue

                if checkNextSprintGoals and "[next-sprint-goal]" in block.string:
                    parent = block.parent
                    logging.info(f"Parent: {parent}")
                    list = soup.new_tag('ul')
                    try:
                        for goal in replacement_dictionary['[next-sprint-goal]'].split("\n"):
                            list_item = soup.new_tag('li')
                            p_item = soup.new_tag('p')
                            p_item.string = goal
                            list_item.append(p_item)
                            list.append(list_item)
                        parent.replace_with(list)
                    except (KeyError):
                        pass    
                    continue

                link_match = re.search('\[.*\-link\]', block.string)

                if link_match:
                    # This is a link, so replace the whole block
                    logging.info(f"REPLACING {block.string} -> LINK")
                    parent = block.parent
                    logging.info(f"Parent: {parent}")
                    link = soup.new_tag('p')
                    link.append(BeautifulSoup(replacement_dictionary[link_match[0]], 'html.parser').contents[0])
                    logging.info(link)
                    parent.replace_with(link)
                    continue

                new_title = block.string

                for search, replace in replacement_dictionary.items():
                    new_title = new_title.replace(search, replace)

                if block.string != new_title:
                    logging.info(f"REPLACING {block.string} -> {new_title}")
                    block.string.replace_with(new_title)

            except AttributeError:
                logging.info("Block has no title, moving on")

        logging.info(f"------------------------\nSoup:\n{soup}\n------------------------")

        if self.contents != soup:
            self.__client.update_page(self.page_id, self.page['title'], body=str(soup), representation="storage", always_update=True)

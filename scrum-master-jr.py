from slackeventsapi import SlackEventAdapter
import slack
import os
import re
import random
from flask import Flask, jsonify, request
import logging
logging.basicConfig(format='%(message)s')

from jira import Jira

app = Flask(__name__)

@app.route("/health")
def healthcheck():
    return "Up and Running!", 200


# Our app's Slack Event Adapter for receiving actions via the Events API
slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
slack_events_adapter = SlackEventAdapter(slack_signing_secret, "/slack/events", app)

# Create a SlackClient for your bot to use for Web API requests
slack_bot_token = os.environ["SLACK_BOT_TOKEN"]
slack_client = slack.WebClient(slack_bot_token)

# Set up for Jira Commands
jira_host = os.environ["JIRA_HOST"]
jira_user = os.environ["JIRA_USER"]
jira_token = os.environ["JIRA_TOKEN"]
jira = Jira(jira_host, jira_user, jira_token)

commandsets = [jira]

def say_hello(message):
    responses = ["Hello there!",
                 "It's a pleasure to meet you! My name is Scrum Master Jr.",
                 "Oh! Sorry, you startled me. I didn't see you there.",
                 "Hi!",
                 "Howdy!",
                 "Aloha!",
                 "Hola!",
                 "Bonjour!"
                ]

    return random.choice(responses)

@slack_events_adapter.on("app_mention")
def handle_mention(event_data):
    message = event_data["event"]
    response = "I'm sorry, I don't understand you. Try asking me for `help`"

    if message.get("subtype") is None:
        text = message.get("text")

        if re.search('h(ello|i)', text):
            response = say_hello(message)
        for set in commandsets:
            for regex in set.getCommandsRegex().keys():
                if re.search(regex, text):
                    response = set.getCommandsRegex[regex](message)

        slack_client.chat_postMessage(channel=message["channel"], text=response)

# Start the server on port 80
if __name__ == "__main__":
  app.run(host='0.0.0.0', port=80)

# Scrum Master Jr.
asdfasdfasdfasdfasdf
This is a Slack bot aimed at helping Scrum Masters and Self-Organizing teams. Currently it's focused on providing metrics and writing sprint reports, but expect more in the future! 

Configuration is done through environment variables set via Ahab.

|Environment Variable   |Value   |
|---|---|
|slack_bot_secret   |The bot token associated with the app's bot in Slack   |
|slack_signing_secret   |The signing secret associated with the app in Slack (used to confirm that incoming messages are actually from Slack)   |

The bot will listen to commands in any channel it has been invited to, provided that they are prefixed by an @mention. It will also respond to DM's, where they @mention is not required. 

### Built In Commands
`hello` - The bot will respond with some different greetings if you say `hello` or `hi`

`help` - The bot will respond with the list of commands that are currently enabled and brief description of each

## Jira
You can connect up to two Jira instances to be able to pull sprint metrics and return data that would be helpful in generating a sprint report

|Environment Variable   |Value   |
|---|---|
|jira_host   |The url of the default jira instance   |
|jira_token   |A token that has read access to the relevant projects in the default jira instance   |
|jira_user   |The username (email address) of the user associated with the above token   |
|cds_jira_host   |The url of a secondary jira instance (all commands prefixed with `cds`  |
|cds_jira_token   |A token that has read access to the relevant projects in the secondary jira instance   |
|cds_jira_user   |The username (email address) of the user associated with the above token   |

## Notion
You can connect a Notion account to enable writing data into reports. 

*Note: The Notion library being used is [notionpy](https://github.com/jamalex/notion-py) which uses unofficial and unsupported api's. Proper API access is on Notion's roadmap, and this should be used instead whenever ready.*

*Also Note: The cookie that contains the token does expired occasionally. This will cause errors when trying to access Notion, you can confirm this is the case by checking the logs. It's on the roadmap to provide a better error to users, and to send proactive notifications that the cookie needs to be updated.*

|Environment Variable   |Value   |
|---|---|
|notion_token   |The token included in a Notion cookie |

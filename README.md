# Discord DJ Link Fetcher Bot

## Overview
This Discord bot is designed to enhance the experience of music enthusiasts and community members within Discord servers. It fetches and provides quest and non-quest DJ links upon request, making it easier for users to find and enjoy DJ sets that suit their platform preferences.

## How It Works
The bot listens for specific commands or mentions in Discord channels. When a user requests quest or non-quest links for specific DJs, the bot processes this request by:

1. Parsing the user's message to extract DJ names.
2. Utilizing fuzzy matching to find the closest matches for the requested DJ names from a predefined list.
3. Fetching the corresponding links (quest or non-quest) based on the matched DJ names.
4. Responding to the user with the requested links directly in the Discord channel.

The bot leverages the `fuzzywuzzy` Python library to handle variations and potential misspellings in DJ names, ensuring that users receive accurate information even with imprecise requests.

## Setup Instructions

### Prerequisites
- Python 3.12 or later
- A Discord account and a Discord server where you have permissions to add bots

### Steps

1. **Clone the Repository**
   Begin by cloning this repository to your local machine.


2. **Create a Virtual Environment (Optional)**
It's recommended to create a virtual environment for Python projects to manage dependencies more effectively.


3. **Install Dependencies**
Install the required Python packages listed in `requirements.txt`.


4. **Discord Bot Token**
You need to create a Discord bot on the Discord Developer Portal and generate a bot token. Follow the instructions [here](https://discord.com/developers/docs/intro) to create a bot and get your token.

5. **Configure Environment Variables**
Create a `.env` file in the root directory of the project. Add the following line, replacing `<Your-Discord-Bot-Token>` with the token you obtained from the Discord Developer Portal.


6. **Run the Bot**
With the environment variable set, you can now run the bot using Python.


### Adding the Bot to Your Discord Server
To add the bot to your Discord server, navigate to the OAuth2 page in the Discord Developer Portal for your bot. Generate an invite link with the necessary permissions and follow the link to add your bot to your server.

## Contributions
Contributions are welcome! If you have suggestions for improvements or bug fixes, feel free to open an issue or submit a pull request.
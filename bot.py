import discord
import requests
import logging
from dotenv import load_dotenv
import os
from fuzzywuzzy import process

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# Load environment variables
load_dotenv()

# Discord client setup
intents = discord.Intents.default()
intents.messages = True  # Enables receiving messages
client = discord.Client(intents=intents)

# Function to retrieve and parse the JSON file
def get_dj_data():
    response = requests.get('https://github.com/PhillipDiCarlo/ClubLAAssets/blob/main/CLA_DJ_Links.json')
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Function to determine request type (Quest or Non-Quest)
def determine_request_type(message):
    quest_keywords = ['quest', 'quest friendly', 'quest compatible']
    non_quest_keywords = ['non quest', 'non-quest', 'no quest', 'non quest friendly', 'non-quest compatible']

    quest_match = process.extractOne(message, quest_keywords)
    non_quest_match = process.extractOne(message, non_quest_keywords)

    # Default to Quest if no clear type is found
    if non_quest_match[1] > quest_match[1]:
        return 'non-quest'
    else:
        return 'quest'  

def get_chatgpt_response(dj_data, user_message):
    # Format the data for ChatGPT
    prompt = (f"Please provide the exact DJ names from this message in CSV format, "
              f"maintaining the order in which they are mentioned: '{user_message}'. "
              f"Available DJs and VJs: {dj_data}")

    # API call to ChatGPT
    response = requests.post(
        'https://api.openai.com/v1/engines/chatgpt/completions',
        json={'prompt': prompt, 'max_tokens': 100},
        headers={'Authorization': f'Bearer {os.getenv("CHATGPT_API_KEY")}'}
    )

    if response.status_code == 200:
        return response.json()['choices'][0]['text']
    else:
        return None

def parse_csv_and_fetch_links(csv_response, request_type):
    dj_names = csv_response.strip().split(',')
    links = []
    for name in dj_names:
        name = name.strip()
        if name in dj_data:
            link_type = "Quest_Friendly" if request_type == 'quest' else "Non-Quest_Friendly"
            link = dj_data[name].get(link_type, "Link not found")
            links.append(f"{name} - {link}")
    return links

# Bot event handling
@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')
    global dj_data
    try:
        dj_data = get_dj_data()
        if dj_data is None:
            logging.error('Failed to fetch or parse DJ data')
    except Exception as e:
        logging.error(f'Error during data fetching: {e}')

@client.event
async def on_message(message):
    try:
        if client.user.mentioned_in(message) and message.mentions:
            message_content = message.content
            request_type = determine_request_type(message_content)

            csv_response = get_chatgpt_response(dj_data, message_content)
            if csv_response:
                links_response = parse_csv_and_fetch_links(csv_response, request_type)
                response_message = "\n".join(links_response)
                await message.channel.send(response_message)
            else:
                logging.warning('No response from ChatGPT or response parsing failed')
    except Exception as e:
        logging.error(f'Error handling message: {e}')

client.run(os.getenv('DISCORD_BOT_TOKEN'))

import discord
import requests
import logging
from dotenv import load_dotenv
import os
from fuzzywuzzy import process
from openai import OpenAI
import json
import re


# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


# Load environment variables
load_dotenv()

# Discord client setup
intents = discord.Intents.default()
intents.messages = True  # Enables receiving messages
discordClient = discord.Client(intents=intents)

# OpenAI Client Setup
openaiClient = OpenAI(
    api_key=os.environ.get("CHATGPT_API_KEY")
)

# Function to retrieve and parse the JSON file
def get_dj_data():
    response = requests.get('https://raw.githubusercontent.com/PhillipDiCarlo/ClubLAAssets/main/CLA_DJ_Links.json')
    if response.status_code == 200:
        global dj_vj_json
        dj_vj_json = response.json()  # Save the entire JSON
        # Extracting DJ and VJ names
        dj_names = [dj['DJ_Name'] for dj in dj_vj_json.get('DJs', [])]
        vj_names = [vj['VJ_Name'] for vj in dj_vj_json.get('VJs', [])]
        all_names = dj_names + vj_names  # Combine DJ and VJ names
        # Create CSV string
        dj_vj_csv = ','.join(all_names)
        # print("XYZ" + dj_vj_csv)

        return dj_vj_csv
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
    cleaned_text = re.sub(r"<@.*?>", "", user_message)
    
    completion = openaiClient.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are an automated program designed to return a list of names (in CSV format) based from the given list of DJ/VJ names. You will return only a match of the given names in the same order as mentioned."},
        {"role": "user", "content": f"Names requested {cleaned_text} from the list {dj_data}."} 
    ]
    )
    return completion.choices[0].message.content

def parse_csv_and_fetch_links(csv_response, request_type):
    dj_names = csv_response.strip().split(',')
    requestedLinks = []
    link_type = "Quest_Friendly" if request_type == 'quest' else "Non-Quest_Friendly"
    # for name in dj_names:
    #     name = name.strip()
    #     if name in dj_data:
    #         link_type = "Quest_Friendly" if request_type == 'quest' else "Non-Quest_Friendly"
    #          # TODO: exception raised here, im not using the right variable here. might need to be dj_vj_json
    #         link = dj_data[name].get(link_type, "Link not found")
    #         requestedLinks.append(f"{name} - {link}")
    # return requestedLinks

    # Loop through both DJs and VJs
    nameFound = False
    for name in dj_names:
        nameFound = False
        for category in ['DJs', 'VJs']:
            if nameFound == True:
                break
            for item in dj_vj_json.get(category, []):
                if item.get('DJ_Name') == name:
                    link = item.get(link_type)
                    requestedLinks.append(f"{name} - {link}")
                    nameFound = True
                    break
    return requestedLinks  # Return None if the DJ/VJ was not found


# Bot event handling
@discordClient.event
async def on_ready():
    logging.info(f'Logged in as {discordClient.user}')
    global dj_data
    try:
        dj_data = get_dj_data()
        if dj_data is None:
            logging.error('Failed to fetch or parse DJ data')
    except Exception as e:
        logging.error(f'Error during data fetching: {e}')

@discordClient.event
async def on_message(message):
    try:
        if discordClient.user.mentioned_in(message) and message.mentions:
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

discordClient.run(os.getenv('DISCORD_BOT_TOKEN'))

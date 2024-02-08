import discord
import requests
import logging
from dotenv import load_dotenv
import os
from fuzzywuzzy import process
# from openai import OpenAI
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

        return dj_vj_csv
    else:
        return None

# Function to determine request type (Quest or Non-Quest)
def determine_request_type(message):
    # quest_keywords = ['quest', 'quest friendly', 'quest compatible']
    non_quest_keywords = ['non quest', 'non-quest', 'no quest', 'non quest friendly', 'non-quest compatible']

    if any(keyword in message.lower() for keyword in non_quest_keywords):
        return "non-quest"
    return "quest"

def get_matched_response(dj_data, user_message):
    
    cleaned_text = re.sub(r"<@.*?>", "", user_message)
    pattern = r"(non[-\s]?quest\s+links?\s+for|quest\s+links?\s+for|non[-\s]?quest\s+links?|quest\s+links?|non[-\s]?quest\s+for|quest\s+for)"
    cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE).strip()

    requested_names = [name.strip() for name in cleaned_text.split(',')]
    dj_name_list = [name.strip() for name in dj_data.split(',')]

    finalMatchedNames = {}
    uniqueMatchedNames = set()  # Use a set to store unique matched DJ names

    for phrase in requested_names:
        # Split phrase into segments for matching
        # Here, we always split by 'and' or spaces to handle both clear and concatenated names
        segments = re.split(r"\s+and\s+|\s+", phrase)  # Split by 'and' or spaces
        for segment in segments:
            if segment:  # Ensure segment is not empty
                match = process.extractOne(segment, dj_name_list, score_cutoff=75)
                if match:
                    matchedName, score = match
                    logging.info(f"Requested: '{segment}', Matched: '{matchedName}', Score: {score}")
                    if matchedName not in uniqueMatchedNames:  # Check for uniqueness
                        uniqueMatchedNames.add(matchedName)  # Add to the set of unique names
                        finalMatchedNames[segment] = matchedName  # Maintain mapping

    return finalMatchedNames

def parse_csv_and_fetch_links(matched_names, request_type):
    requestedLinks = []
    link_type = "Quest_Friendly" if request_type == 'quest' else "Non-Quest_Friendly"

    # Loop through matched_names values
    for original_name, matched_name in matched_names.items():
        nameFound = False
        for category in ['DJs', 'VJs']:
            if nameFound:
                break
            for item in dj_vj_json.get(category, []):
                if item.get('DJ_Name') == matched_name:  # Use matched_name
                    link = item.get(link_type)
                    requestedLinks.append(f"{matched_name} - {link}")
                    nameFound = True
                    break
    
    # Check if no names were found and handle accordingly
    if not requestedLinks:
        return ["No links found for the requested names."]
    
    return requestedLinks


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

            csv_response = get_matched_response(dj_data, message_content)
            if csv_response:
                links_response = parse_csv_and_fetch_links(csv_response, request_type)
                response_message = "\n".join(links_response)
                await message.channel.send(response_message)
            else:
                logging.warning('No response from ChatGPT or response parsing failed')
    except Exception as e:
        logging.error(f'Error handling message: {e}')

discordClient.run(os.getenv('DISCORD_BOT_TOKEN'))

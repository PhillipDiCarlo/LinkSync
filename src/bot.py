import discord
import logging
import os
import psycopg2
from dotenv import load_dotenv
from discord import app_commands

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
SUBSCRIPTION_LINK = "https://your_subscription_link_here"  # Replace with your actual link

# Setup logging with dynamic level
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the Discord bot with intents
intents = discord.Intents.default()
intents.members = True  # Enable the members intent if needed for member-related events

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.last_startup_time = None

    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

# Function to check if the user has an active subscription
def check_user_subscription(discord_id):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    query = "SELECT active_subscription FROM users WHERE discord_id = %s"
    cursor.execute(query, (str(discord_id),))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None and result[0]

# Function to retrieve DJ links from the database using trigram similarity
def get_dj_links_from_db(dj_name, is_quest):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    link_type = "quest_link" if is_quest else "non_quest_link"
    
    query = f"""
    SELECT dj_name, {link_type}
    FROM links
    WHERE SIMILARITY(dj_name, %s) > 0.4
    ORDER BY SIMILARITY(dj_name, %s) DESC
    LIMIT 1;
    """
    
    cursor.execute(query, (dj_name, dj_name))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

# Slash command to get DJ links with inline options
@bot.tree.command(name="get_dj_links", description="Retrieve DJ links based on your preferences.")
@app_commands.describe(
    quest="Do you want Quest links? Select True or False.",
    slot_count="How many DJ slots would you like? (Default: 4)",
    dj_names="Enter DJ names separated by commas."
)
async def get_dj_links(
    interaction: discord.Interaction, 
    quest: bool, 
    slot_count: int = 4, 
    dj_names: str = ""
):
    if not check_user_subscription(interaction.user.id):
        await interaction.response.send_message(
            f"You do not have an active subscription. Please [click here]({SUBSCRIPTION_LINK}) to subscribe.",
            ephemeral=True
        )
        return

    # Split the DJ names from the input
    dj_names_list = [name.strip() for name in dj_names.split(',')][:slot_count]

    # Prepare response
    links_response = [f"Quest Compatible = {quest}"]
    
    # Fetch DJ Links from the Database
    for dj_name in dj_names_list:
        result = get_dj_links_from_db(dj_name, quest)
        if result:
            dj_name, link = result
            links_response.append(f"**{dj_name}** - {link if link else 'No link available'}")
        else:
            links_response.append(f"No match found for **{dj_name}**.")
    
    await interaction.response.send_message("\n".join(links_response), ephemeral=True)

# Event handling
@bot.event
async def on_ready():
    bot.last_startup_time = discord.utils.utcnow()
    logging.info(f'Bot is ready. Logged in as {bot.user}')
    logging.info(f"Bot started at {bot.last_startup_time}")

# Run the bot
bot.run(DISCORD_BOT_TOKEN)

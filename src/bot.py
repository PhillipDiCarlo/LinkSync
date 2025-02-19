import discord
import logging
import os
import psycopg2
from dotenv import load_dotenv
from discord import app_commands
import asyncio
from discord.ui import View, Button

# Load environment variables
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL_DJ')
SUBSCRIPTION_LINK = "https://esattotech.com/pricing/"
HOME_DISCORD_SERVER = os.getenv('HOME_DISCORD_SERVER')

# Setup logging with dynamic level
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'), format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the Discord bot with intents
intents = discord.Intents.default()

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
    dj_names="Enter DJ names separated by commas."
)
async def get_dj_links(
    interaction: discord.Interaction, 
    quest: bool, 
    dj_names: str = ""
):
    # Check if the user is in your specific Discord server
    if interaction.guild_id != HOME_DISCORD_SERVER:
        # If not in the specific server, check the user's subscription
        if not check_user_subscription(interaction.user.id):
            await interaction.response.send_message(
                f"You do not have an active subscription. Please [click here]({SUBSCRIPTION_LINK}) to subscribe.",
                ephemeral=True
            )
            return

    # Split the DJ names from the input
    dj_names_list = [name.strip() for name in dj_names.split(',')]

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
    
    await interaction.response.send_message("\n".join(links_response))

# Slash command to add a DJ link for review
@bot.tree.command(name="add_link", description="Submit a DJ link for review.")
@app_commands.describe(
    dj_name="Enter the DJ's name",
    dj_link="Enter the DJ link"
)
async def add_link(interaction: discord.Interaction, dj_name: str, dj_link: str):
    submitter_id = interaction.user.id

    # Respond with a defer message first
    await interaction.response.defer(ephemeral=True)

    # Check if the DJ exists in the 'links' or 'requests' table
    def search_existing_dj(dj_name):
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Search only the links table using similarity matching
        query = """
        SELECT dj_name, quest_link FROM links 
        WHERE SIMILARITY(LOWER(dj_name), LOWER(%s)) > 0.4
        LIMIT 1;
        """
        cursor.execute(query, (dj_name,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row
    
    # Search for the DJ
    existing_dj = search_existing_dj(dj_name)

    # If a match is found, ask the user to confirm with buttons
    if existing_dj:
        existing_dj_name, existing_dj_link = existing_dj

        # Define the buttons for Yes/No
        class ConfirmView(View):
            def __init__(self):
                super().__init__()
                self.value = None

            @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
            async def yes_button(self, interaction: discord.Interaction, button: Button):
                self.value = "yes"
                self.stop()

            @discord.ui.button(label="No", style=discord.ButtonStyle.red)
            async def no_button(self, interaction: discord.Interaction, button: Button):
                self.value = "no"
                self.stop()

        view = ConfirmView()

        # Send the message with the buttons and wait for the user's interaction
        await interaction.followup.send(
            f"Is this the DJ you're referring to?\n**DJ Name**: {existing_dj_name}\n**Quest Link**: {existing_dj_link}",
            view=view,
            ephemeral=True
        )

        # Wait for the user's response
        await view.wait()

        # Handle the user's button response
        if view.value == "yes":
            await interaction.followup.send("Submission canceled. The DJ already exists.", ephemeral=True)
            return
        else:
            await interaction.followup.send("Proceeding with your submission.", ephemeral=True)

    # Insert into the requests table since user confirmed it's not the same DJ
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    insert_query = """
    INSERT INTO requests (dj_name, dj_link, submitter_id, review_status)
    VALUES (%s, %s, %s, 'Pending')
    """
    cursor.execute(insert_query, (dj_name, dj_link, submitter_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    await interaction.followup.send("Your DJ link has been submitted for review.", ephemeral=True)

# Event handling
@bot.event
async def on_ready():
    bot.last_startup_time = discord.utils.utcnow()
    logging.info(f'Bot is ready. Logged in as {bot.user}')
    logging.info(f"Bot started at {bot.last_startup_time}")

# Run the bot
bot.run(DISCORD_BOT_TOKEN)

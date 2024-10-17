import json
import psycopg2
import os
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
database_url = os.getenv("DATABASE_URL")

# Load JSON data
with open('CLA_DJ_Links.json') as file:
    data = json.load(file)

# Connect to the PostgreSQL database using DATABASE_URL
conn = psycopg2.connect(database_url)
cursor = conn.cursor()

# SQL query to insert data into the links table
insert_query = """
INSERT INTO links (dj_name, non_quest_link, quest_link) VALUES (%s, %s, %s)
ON CONFLICT (dj_name) DO NOTHING;
"""

# Collect unique names from DJs
unique_entries = {}
for dj in data.get("DJs", []):
    dj_name = dj.get("DJ_Name")
    non_quest_link = dj.get("Non-Quest_Friendly", None)
    quest_link = dj.get("Quest_Friendly", None)
    unique_entries[dj_name] = (non_quest_link, quest_link)

# Add unique VJs, only if they don't exist in DJs
for vj in data.get("VJs", []):
    vj_name = vj.get("VJ_Name")
    if vj_name not in unique_entries:
        non_quest_link = vj.get("Non-Quest_Friendly", None)
        quest_link = vj.get("Quest_Friendly", None)
        unique_entries[vj_name] = (non_quest_link, quest_link)

# Insert all unique entries into the database
for name, links in unique_entries.items():
    non_quest_link, quest_link = links
    cursor.execute(insert_query, (name, non_quest_link, quest_link))

# Commit the transaction and close the connection
conn.commit()
cursor.close()
conn.close()

print("Data inserted successfully into the links table.")

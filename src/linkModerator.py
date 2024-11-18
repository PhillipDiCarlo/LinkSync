import os
import tkinter as tk
import psycopg2
from tkinter import messagebox
import sys
from dotenv import load_dotenv

def resource_path(relative_path):
    """ Get absolute path to resource, works for PyInstaller and development """
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_path = os.path.dirname(sys.executable)
    else:
        # Running in a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)



# Load environment variables from .env file
dotenv_path = resource_path('.env')
load_dotenv(dotenv_path=dotenv_path)

# Debugging: Check if the .env file was loaded
if not os.path.exists(dotenv_path):
    messagebox.showerror("Error", f".env file not found at {dotenv_path}")
    sys.exit(1)

# Database connection setup
DATABASE_URL = os.getenv('DATABASE_URL_DJ')
if not DATABASE_URL:
    messagebox.showerror("Error", "DATABASE_URL_DJ is not set. Please check your .env file.")
    sys.exit(1)
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Function to convert links to their Quest and Non-Quest compatible versions
def convert_links(quest_link):
    non_quest_link = quest_link  # Default case, they are the same

    if quest_link.startswith("https://stream.vrcdn.live/live/"):
        # Convert Quest link to Non-Quest link by removing '.live.ts'
        username = quest_link.replace("https://stream.vrcdn.live/live/", "").replace(".live.ts", "")
        non_quest_link = f"rtspt://stream.vrcdn.live/live/{username}"

    if quest_link.startswith("rtspt://stream.vrcdn.live/live/"):
        # Convert Non-Quest link to Quest link by adding '.live.ts'
        username = quest_link.replace("rtspt://stream.vrcdn.live/live/", "")
        quest_link = f"https://stream.vrcdn.live/live/{username}.live.ts"

    return quest_link, non_quest_link

# Function to fetch the next request in FIFO order
def fetch_next_request():
    cursor.execute("SELECT id, dj_name, dj_link FROM requests ORDER BY id LIMIT 1")
    return cursor.fetchone()

# Function to fetch similar DJs from the database
def fetch_similar_djs(dj_name):
    cursor.execute("""
    SELECT dj_name, quest_link, non_quest_link FROM links
    WHERE SIMILARITY(dj_name, %s) > 0.4
    LIMIT 1
    """, (dj_name,))
    return cursor.fetchone()

# Function to enable or disable buttons based on whether there are requests
def update_button_states():
    if request_data:
        accept_button.config(state=tk.NORMAL)
        deny_button.config(state=tk.NORMAL)
    else:
        accept_button.config(state=tk.DISABLED)
        deny_button.config(state=tk.DISABLED)

# Function to accept the request
def accept_request():
    dj_name = dj_name_entry.get()
    quest_link = quest_link_entry.get()
    non_quest_link = non_quest_link_entry.get()
    request_id = request_data[0]

    cursor.execute("""
    INSERT INTO links (dj_name, quest_link, non_quest_link)
    VALUES (%s, %s, %s)
    """, (dj_name, quest_link, non_quest_link))

    cursor.execute("DELETE FROM requests WHERE id = %s", (request_id,))
    conn.commit()

    messagebox.showinfo("Success", "DJ accepted and added to the database.")
    load_next_request()

# Function to deny the request
def deny_request():
    request_id = request_data[0]
    cursor.execute("DELETE FROM requests WHERE id = %s", (request_id,))
    conn.commit()

    messagebox.showinfo("Denied", "DJ request denied and removed from the list.")
    load_next_request()

# Function to load the next request and populate the form
def load_next_request():
    global request_data
    request_data = fetch_next_request()

    if not request_data:
        dj_name_entry.delete(0, tk.END)
        quest_link_entry.delete(0, tk.END)
        non_quest_link_entry.delete(0, tk.END)
        similar_dj_name.set("No more DJ requests to review.")
        similar_quest_link.set("")
        similar_non_quest_link.set("")
        update_button_states()  # Disable buttons
        return

    dj_name_entry.delete(0, tk.END)
    dj_name_entry.insert(0, request_data[1])

    dj_link = request_data[2]
    quest_link, non_quest_link = convert_links(dj_link)

    quest_link_entry.delete(0, tk.END)
    quest_link_entry.insert(0, quest_link)

    non_quest_link_entry.delete(0, tk.END)
    non_quest_link_entry.insert(0, non_quest_link)

    # Fetch and display similar DJs
    similar_dj = fetch_similar_djs(request_data[1])
    if similar_dj:
        similar_dj_name.set(f"Similar DJ: {similar_dj[0]}")
        similar_quest_link.set(f"Quest Link: {similar_dj[1]}")
        similar_non_quest_link.set(f"Non-Quest Link: {similar_dj[2]}")
    else:
        similar_dj_name.set("No similar DJs found")
        similar_quest_link.set("")
        similar_non_quest_link.set("")

    update_button_states()  # Enable buttons

# Function to refresh and check for new requests
def refresh_requests():
    load_next_request()
    if request_data:
        messagebox.showinfo("Refreshed", "New DJ requests found!")
    else:
        messagebox.showinfo("No Requests", "No new DJ requests.")

# Set up the GUI
root = tk.Tk()
root.title("DJ Request Reviewer")

default_width = 400
default_height = 250
root.geometry(f"{default_width}x{default_height}")

# Similar DJ Info
similar_dj_name = tk.StringVar()

tk.Label(root, textvariable=similar_dj_name).grid(row=0, column=0, columnspan=2)

# Label for Similar DJ Quest Link
tk.Label(root, text="Quest Link").grid(row=1, column=0)
quest_link_entry_similar = tk.Entry(root, width=40)
quest_link_entry_similar.grid(row=1, column=1)
quest_link_entry_similar.config(state=tk.DISABLED)  # Make it read-only

# Label for Similar DJ Non-Quest Link
tk.Label(root, text="Non-Quest Link").grid(row=2, column=0)
non_quest_link_entry_similar = tk.Entry(root, width=40)
non_quest_link_entry_similar.grid(row=2, column=1)
non_quest_link_entry_similar.config(state=tk.DISABLED)  # Make it read-only

# Spacer between the sections
tk.Label(root, text="").grid(row=3, column=0, columnspan=2)  # Empty label as a spacer

# Editable fields for the requested DJ with increased width
tk.Label(root, text="DJ Name").grid(row=4, column=0)
dj_name_entry = tk.Entry(root, width=40)
dj_name_entry.grid(row=4, column=1)

tk.Label(root, text="Quest Link").grid(row=5, column=0)
quest_link_entry = tk.Entry(root, width=40)
quest_link_entry.grid(row=5, column=1)

tk.Label(root, text="Non-Quest Link").grid(row=6, column=0)
non_quest_link_entry = tk.Entry(root, width=40)
non_quest_link_entry.grid(row=6, column=1)

# Accept and Deny buttons (initially disabled if no requests)
accept_button = tk.Button(root, text="Accept", command=accept_request)
accept_button.grid(row=7, column=0)

deny_button = tk.Button(root, text="Deny", command=deny_request)
deny_button.grid(row=8, column=0)

# Refresh button to check for new requests
refresh_button = tk.Button(root, text="Refresh", command=refresh_requests)
refresh_button.grid(row=7, column=1)

# Function to load the next request and populate the form
def load_next_request():
    global request_data
    request_data = fetch_next_request()

    if not request_data:
        dj_name_entry.delete(0, tk.END)
        quest_link_entry.delete(0, tk.END)
        non_quest_link_entry.delete(0, tk.END)
        quest_link_entry_similar.config(state=tk.NORMAL)
        quest_link_entry_similar.delete(0, tk.END)
        quest_link_entry_similar.config(state=tk.DISABLED)
        non_quest_link_entry_similar.config(state=tk.NORMAL)
        non_quest_link_entry_similar.delete(0, tk.END)
        non_quest_link_entry_similar.config(state=tk.DISABLED)
        similar_dj_name.set("No more DJ requests to review.")
        update_button_states()  # Disable buttons
        return

    dj_name_entry.delete(0, tk.END)
    dj_name_entry.insert(0, request_data[1])

    dj_link = request_data[2]
    quest_link, non_quest_link = convert_links(dj_link)

    quest_link_entry.delete(0, tk.END)
    quest_link_entry.insert(0, quest_link)

    non_quest_link_entry.delete(0, tk.END)
    non_quest_link_entry.insert(0, non_quest_link)

    # Fetch and display similar DJs
    similar_dj = fetch_similar_djs(request_data[1])
    if similar_dj:
        similar_dj_name.set(f"Similar DJ: {similar_dj[0]}")
        quest_link_entry_similar.config(state=tk.NORMAL)
        quest_link_entry_similar.delete(0, tk.END)
        quest_link_entry_similar.insert(0, similar_dj[1])
        quest_link_entry_similar.config(state=tk.DISABLED)

        non_quest_link_entry_similar.config(state=tk.NORMAL)
        non_quest_link_entry_similar.delete(0, tk.END)
        non_quest_link_entry_similar.insert(0, similar_dj[2])
        non_quest_link_entry_similar.config(state=tk.DISABLED)
    else:
        similar_dj_name.set("No similar DJs found")
        quest_link_entry_similar.config(state=tk.NORMAL)
        quest_link_entry_similar.delete(0, tk.END)
        quest_link_entry_similar.config(state=tk.DISABLED)

        non_quest_link_entry_similar.config(state=tk.NORMAL)
        non_quest_link_entry_similar.delete(0, tk.END)
        non_quest_link_entry_similar.config(state=tk.DISABLED)

    update_button_states()  # Enable buttons

# Load the first request
load_next_request()

root.mainloop()
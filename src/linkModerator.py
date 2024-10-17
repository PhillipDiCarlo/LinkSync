import os
import tkinter as tk
import psycopg2
from tkinter import messagebox

# Database connection setup
DATABASE_URL = os.getenv('DATABASE_URL_DJ')
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


    # Both twitch.tv and youtube.com are valid for both Quest and Non-Quest
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

# Function to accept the request
def accept_request():
    dj_name = dj_name_entry.get()
    quest_link = quest_link_entry.get()
    non_quest_link = non_quest_link_entry.get()
    request_id = request_data[0]

    # Insert into links table
    cursor.execute("""
    INSERT INTO links (dj_name, quest_link, non_quest_link)
    VALUES (%s, %s, %s)
    """, (dj_name, quest_link, non_quest_link))

    # Remove from requests table
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
        messagebox.showinfo("No Requests", "No more DJ requests to review.")
        root.quit()  # Exit the application if there are no more requests
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

# Set up the GUI
root = tk.Tk()
root.title("DJ Request Reviewer")

# Define the new size (twice the width, 1.5 times the height)
default_width = 400  # Example default width
default_height = 300  # Example default height

# new_width = default_width * 2  # Twice the width
# new_height = int(default_height * 1.5)  # 1.5 times the height

# Set the window size
root.geometry(f"{default_width}x{default_height}")

# Similar DJ Info
similar_dj_name = tk.StringVar()
similar_quest_link = tk.StringVar()
similar_non_quest_link = tk.StringVar()

tk.Label(root, textvariable=similar_dj_name).grid(row=0, column=0, columnspan=2)
tk.Label(root, textvariable=similar_quest_link).grid(row=1, column=0, columnspan=2)
tk.Label(root, textvariable=similar_non_quest_link).grid(row=2, column=0, columnspan=2)

# Editable fields for the requested DJ with increased width
tk.Label(root, text="DJ Name").grid(row=3, column=0)
dj_name_entry = tk.Entry(root, width=40)  # Increased width
dj_name_entry.grid(row=3, column=1)

tk.Label(root, text="Quest Link").grid(row=4, column=0)
quest_link_entry = tk.Entry(root, width=40)  # Increased width
quest_link_entry.grid(row=4, column=1)

tk.Label(root, text="Non-Quest Link").grid(row=5, column=0)
non_quest_link_entry = tk.Entry(root, width=40)  # Increased width
non_quest_link_entry.grid(row=5, column=1)

# Accept and Deny buttons
accept_button = tk.Button(root, text="Accept", command=accept_request)
accept_button.grid(row=6, column=0)

deny_button = tk.Button(root, text="Deny", command=deny_request)
deny_button.grid(row=7, column=0)

# Load the first request
load_next_request()

root.mainloop()
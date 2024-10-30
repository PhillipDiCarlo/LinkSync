```markdown
# Discord DJ Link Retrieval Bot

## Overview
The Discord DJ Link Retrieval Bot is designed to make finding DJ music links seamless within a Discord server. By automatically fetching Quest and Non-Quest compatible links on demand, the bot saves users from having to search manually. The bot's smart search system utilizes similarity matching to help account for misspellings, ensuring users can find the DJ links they need with minimal effort. With a continually expanding database of DJs, this bot is a perfect tool for communities that want quick, easy access to DJ content.

## Key Features
- **Quest and Non-Quest Compatibility**: Automatically retrieves Quest-compatible and Non-Quest-compatible DJ links based on user preference.
- **Similarity Matching**: Supports variation in name spelling, so users can still get accurate results even with minor typos.
- **Expandable DJ Database**: The database is regularly updated with new DJ links, making it an ever-growing resource.
- **Add Link Feature for DJs**: Users can submit DJ link requests directly through the bot for review, helping build a comprehensive link database.
- **Server-Specific Access**: Restricts certain commands based on user subscriptions and server membership, allowing for fine-tuned access control.
- **Admin Moderation**: Provides tools for moderators to approve or deny DJ link requests, with an easy-to-use review interface.

## How It Works
The bot listens for specific commands within Discord and provides easy access to DJ links:

1. **Get DJ Links**:
   - Users can request DJ links with a specific command, choosing Quest or Non-Quest options.
   - The bot searches the database using similarity matching for each requested DJ, ensuring accurate retrieval even with slight name variations.
   - Results are delivered with links directly in the channel or as a private message, depending on access and permissions.

2. **Submit a DJ Link**:
   - Users who notice a missing DJ can submit a link request through the bot.
   - Requests go to a moderation queue where admins can review, approve, or deny the addition to the main database.

## Setup Instructions

### Prerequisites
- Python 3.12 or later
- A Discord account and a Discord server where you have permissions to add bots
- PostgreSQL database (for link storage)

### Steps

1. **Install Dependencies**
   Install the required Python packages listed in `requirements.txt`.

   ```bash
   pip install -r requirements.txt
   ```

2. **Discord Bot Token**
   Create a Discord bot on the Discord Developer Portal and generate a bot token. Follow the instructions [here](https://discord.com/developers/docs/intro) to create a bot and get your token.

3. **Configure Environment Variables**
   Set up a `.env` file in the root directory with the following variables:

   ```env
   DISCORD_BOT_TOKEN=<Your-Discord-Bot-Token>
   DATABASE_URL_DJ=<Your-Database-URL>
   ```

4. **Run the Bot**
   Run the bot using Python:

   ```bash
   python bot.py
   ```

### Adding the Bot to Your Discord Server
To add the bot to your Discord server, navigate to the OAuth2 page in the Discord Developer Portal, generate an invite link with the necessary permissions, and add the bot to your server.

## Contributions
Contributions are welcome! If you have suggestions for improvements, new features, or bug fixes, feel free to open an issue or submit a pull request.
```

"""
DJ Link Bot (Discord Slash Commands)

- /get_dj_links (premium-gated via Discord App Subscriptions entitlements, unless guild is whitelisted)
- /add_link (free; submits to requests table for later review)

Environment variables required:
- DISCORD_BOT_TOKEN
- DATABASE_URL_DJ
- DISCORD_APP_ID           (your Discord Application / Client ID)
- PREMIUM_SKU_ID           (your monthly per-user subscription SKU ID)

Optional:
- WHITELISTED_SERVERS      (comma-separated guild IDs that bypass premium gating)
- LOG_LEVEL                (INFO, DEBUG, etc.)
- PREMIUM_UPSELL_URL       (a URL you want to show for "subscribe here" - can be your app directory listing)
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Any, Dict

import aiohttp
import discord
import psycopg2
from discord import app_commands
from discord.ui import View, Button
from dotenv import load_dotenv


# -----------------------------------------------------------------------------
# Config / Logging
# -----------------------------------------------------------------------------

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL_DJ", "").strip()

# Discord Premium Apps / App Subscriptions (Option A)
DISCORD_APP_ID = os.getenv("DISCORD_APP_ID", "").strip()      # Application (Client) ID
PREMIUM_SKU_ID = os.getenv("PREMIUM_SKU_ID", "").strip()      # Monthly per-user subscription SKU ID

# Where to send users to subscribe (use your Discord App Directory listing or store URL)
PREMIUM_UPSELL_URL = os.getenv("PREMIUM_UPSELL_URL", "").strip()  # optional; if blank, we just explain

WHITELISTED_SERVERS_RAW = os.getenv("WHITELISTED_SERVERS", "").strip()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

WHITELISTED_SERVERS_LIST: List[int] = []
if WHITELISTED_SERVERS_RAW:
    try:
        WHITELISTED_SERVERS_LIST = [int(sid.strip()) for sid in WHITELISTED_SERVERS_RAW.split(",") if sid.strip()]
    except ValueError:
        logging.warning("WHITELISTED_SERVERS contains non-integer values; ignoring.")


def require_env() -> None:
    missing = []
    if not DISCORD_BOT_TOKEN:
        missing.append("DISCORD_BOT_TOKEN")
    if not DATABASE_URL:
        missing.append("DATABASE_URL_DJ")
    if not DISCORD_APP_ID:
        missing.append("DISCORD_APP_ID")
    if not PREMIUM_SKU_ID:
        missing.append("PREMIUM_SKU_ID")

    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


# -----------------------------------------------------------------------------
# Database helpers
# -----------------------------------------------------------------------------

def db_connect():
    # psycopg2 is sync; that’s fine for small bots. If this grows, move DB ops to an executor/pool.
    return psycopg2.connect(DATABASE_URL)


def get_dj_links_from_db(dj_name: str, is_quest: bool) -> Optional[Tuple[str, Optional[str]]]:
    """
    Retrieves best match DJ link using pg_trgm similarity.
    Expects table `links(dj_name, quest_link, non_quest_link)` and pg_trgm installed.
    """
    link_type = "quest_link" if is_quest else "non_quest_link"

    query = f"""
    SELECT dj_name, {link_type}
    FROM links
    WHERE SIMILARITY(dj_name, %s) > 0.4
    ORDER BY SIMILARITY(dj_name, %s) DESC
    LIMIT 1;
    """

    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (dj_name, dj_name))
            row = cur.fetchone()
            return row  # (dj_name, link)
    finally:
        conn.close()


def search_existing_dj_in_links(dj_name: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Finds an existing DJ in `links` using similarity match (lowercased).
    Returns (existing_dj_name, existing_quest_link).
    """
    query = """
    SELECT dj_name, quest_link
    FROM links
    WHERE SIMILARITY(LOWER(dj_name), LOWER(%s)) > 0.4
    LIMIT 1;
    """

    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(query, (dj_name,))
            return cur.fetchone()
    finally:
        conn.close()


def insert_request(dj_name: str, dj_link: str, submitter_id: int) -> None:
    """
    Inserts a row into `requests(dj_name, dj_link, submitter_id, review_status)`.
    """
    insert_query = """
    INSERT INTO requests (dj_name, dj_link, submitter_id, review_status)
    VALUES (%s, %s, %s, 'Pending')
    """

    conn = db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(insert_query, (dj_name, dj_link, str(submitter_id)))
        conn.commit()
    finally:
        conn.close()


# -----------------------------------------------------------------------------
# Discord Entitlements (Premium Apps / App Subscriptions)
# -----------------------------------------------------------------------------

_PREMIUM_CACHE: Dict[int, Tuple[bool, float]] = {}  # user_id -> (is_premium, expires_epoch)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_entitlement_active(ent: dict) -> bool:
    """
    Defensive check for entitlement activity.
    Active if:
      - not deleted
      - starts_at is None or <= now
      - ends_at is None or > now
    """
    if ent.get("deleted"):
        return False

    now = _utc_now()

    starts_at = ent.get("starts_at")
    if starts_at:
        s = datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
        if s > now:
            return False

    ends_at = ent.get("ends_at")
    if ends_at:
        e = datetime.fromisoformat(ends_at.replace("Z", "+00:00"))
        if e <= now:
            return False

    return True


async def has_premium_entitlement(user_id: int) -> bool:
    """
    Authoritative entitlement check via REST:
      GET /applications/{application_id}/entitlements
        ?user_id=...
        &sku_ids=...
        &exclude_deleted=true
        &exclude_ended=true
        &limit=100

    Uses a small TTL cache to reduce API calls.
    """
    if not DISCORD_APP_ID or not PREMIUM_SKU_ID:
        logging.error("Missing DISCORD_APP_ID or PREMIUM_SKU_ID env var.")
        return False

    now_epoch = time.time()
    # cached = _PREMIUM_CACHE.get(user_id)
    # if cached and cached[1] > now_epoch:
    #     return cached[0]

    url = f"https://discord.com/api/v10/applications/{DISCORD_APP_ID}/entitlements"
    params = {
        "user_id": str(user_id),
        "sku_ids": str(PREMIUM_SKU_ID),
        "exclude_deleted": "true",
        "exclude_ended": "true",
        "limit": "100",
    }
    headers = {"Authorization": f"Bot {DISCORD_BOT_TOKEN}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logging.error(f"Entitlements API error {resp.status}: {body}")
                    _PREMIUM_CACHE[user_id] = (False, now_epoch + 30)  # short negative cache
                    return False

                entitlements = await resp.json()

        active = any(
            (str(ent.get("sku_id")) == str(PREMIUM_SKU_ID)) and _is_entitlement_active(ent)
            for ent in entitlements
        )

        _PREMIUM_CACHE[user_id] = (active, now_epoch + (120 if active else 30))
        return active

    except Exception:
        logging.exception("Failed to check entitlements.")
        _PREMIUM_CACHE[user_id] = (False, now_epoch + 30)
        return False


async def ensure_premium_or_upsell(interaction: discord.Interaction) -> bool:
    """
    Returns True if premium should be granted, otherwise sends an ephemeral upsell and returns False.

    Premium is granted if:
      - interaction.guild_id is whitelisted OR
      - user has a premium entitlement for PREMIUM_SKU_ID
    """
    guild_id = interaction.guild_id
    if guild_id in WHITELISTED_SERVERS_LIST:
        return True

    ok = await has_premium_entitlement(interaction.user.id)
    if ok:
        return True

    # Upsell message
    if PREMIUM_UPSELL_URL:
        msg = (
            "This is a **premium** command.\n"
            f"Subscribe to unlock it: {PREMIUM_UPSELL_URL}\n\n"
            "Once you subscribe in Discord, access is applied automatically."
        )
    else:
        msg = (
            "This is a **premium** command.\n"
            "Subscribe to unlock it in Discord (App Subscriptions). "
            "Once you subscribe, access is applied automatically."
        )

    # If we haven’t responded yet, use response; otherwise use followup
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)
    return False


# -----------------------------------------------------------------------------
# Discord Bot Setup
# -----------------------------------------------------------------------------

intents = discord.Intents.default()


class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.last_startup_time: Optional[datetime] = None

    async def setup_hook(self):
        await self.tree.sync()


bot = MyBot()


# -----------------------------------------------------------------------------
# UI Views
# -----------------------------------------------------------------------------

class ConfirmView(View):
    """
    Simple yes/no confirmation view.
    """
    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.value: Optional[str] = None

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, button: Button):
        self.value = "yes"
        self.stop()

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction: discord.Interaction, button: Button):
        self.value = "no"
        self.stop()


# -----------------------------------------------------------------------------
# Commands
# -----------------------------------------------------------------------------

@bot.tree.command(name="get_dj_links", description="Retrieve DJ links based on your preferences.")
@app_commands.describe(
    quest="Do you want Quest links? Select True or False.",
    dj_names="Enter DJ names separated by commas.",
)
async def get_dj_links(interaction: discord.Interaction, quest: bool, dj_names: str = ""):
    # Premium gate (per-user entitlements), unless server is whitelisted
    if not await ensure_premium_or_upsell(interaction):
        return

    # Split DJ names
    dj_names_list = [name.strip() for name in dj_names.split(",") if name.strip()]
    if not dj_names_list:
        await interaction.response.send_message(
            "Please provide at least one DJ name (comma-separated). Example: `DJ1, DJ2`",
            ephemeral=True,
        )
        return

    links_response = [f"Quest Compatible = {quest}"]

    for dj_name in dj_names_list:
        result = get_dj_links_from_db(dj_name, quest)
        if result:
            found_dj_name, link = result
            links_response.append(f"**{found_dj_name}** - {link if link else 'No link available'}")
        else:
            links_response.append(f"No match found for **{dj_name}**.")

    await interaction.response.send_message("\n".join(links_response))


@bot.tree.command(name="add_link", description="Submit a DJ link for review.")
@app_commands.describe(
    dj_name="Enter the DJ's name",
    dj_link="Enter the DJ link",
)
async def add_link(interaction: discord.Interaction, dj_name: str, dj_link: str):
    submitter_id = interaction.user.id

    # Defer early (ephemeral) since we may do multiple DB operations + wait for a view
    await interaction.response.defer(ephemeral=True)

    # Check if a similar DJ exists in links table
    existing_dj = search_existing_dj_in_links(dj_name)

    if existing_dj:
        existing_dj_name, existing_dj_link = existing_dj
        view = ConfirmView()

        await interaction.followup.send(
            f"Is this the DJ you're referring to?\n"
            f"**DJ Name**: {existing_dj_name}\n"
            f"**Quest Link**: {existing_dj_link}",
            view=view,
            ephemeral=True,
        )

        await view.wait()

        if view.value == "yes":
            await interaction.followup.send(
                "Submission canceled. That DJ already exists in the database.",
                ephemeral=True,
            )
            return

        # If no / timeout, continue
        await interaction.followup.send("Proceeding with your submission.", ephemeral=True)

    # Insert into requests table
    insert_request(dj_name=dj_name, dj_link=dj_link, submitter_id=submitter_id)
    await interaction.followup.send("Your DJ link has been submitted for review.", ephemeral=True)


# -----------------------------------------------------------------------------
# Events
# -----------------------------------------------------------------------------

@bot.event
async def on_ready():
    bot.last_startup_time = discord.utils.utcnow()
    logging.info(f"Bot is ready. Logged in as {bot.user}")
    logging.info(f"Bot started at {bot.last_startup_time}")
    if WHITELISTED_SERVERS_LIST:
        logging.info(f"Whitelisted servers: {', '.join(map(str, WHITELISTED_SERVERS_LIST))}")
    else:
        logging.info("No servers are whitelisted.")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    require_env()
    bot.run(DISCORD_BOT_TOKEN)

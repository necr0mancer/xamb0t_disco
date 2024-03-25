import discord
from discord.ext import commands
import asyncio
import datetime
import sqlite3
#sqlite4 ?
import os
from typing import Final
from dotenv import load_dotenv

# Discord bot token
load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')

# Intents
#intents = discord.Intents.default()
intents = discord.Intents.all()
intents.messages = True
intents.members = True

# Initialize bot with intents
bot = commands.Bot(command_prefix='!', intents=intents)

# SQLite database connection
conn = sqlite3.connect('activity_tracker.db')
c = conn.cursor()

# Create db table to store user activity
c.execute('''CREATE TABLE IF NOT EXISTS user_activity (
             user_id TEXT PRIMARY KEY,
             message_count INTEGER
             )''')
# create db table to store message ids to prevent duplicate counting
c.execute('''CREATE TABLE IF NOT EXISTS counted_messages (
             message_id TEXT PRIMARY KEY,
             timestamp TIMESTAMP
             )''')
conn.commit()

# Define the channel where you want to track message counts
#CHANNEL_ID = 1234567890

# Define role thresholds
role_thresholds = {
    "Common": 1,
    "Rare": 25,
    "Majestic": 70,
    "Legendary": 150,
    "Marvel": 500,
    "Fabled": 1500,
    # Add or adjust roles and thresholds as needed
}

# Function to update user roles based on message count
async def update_roles():
    # guild = bot.get_guild(GUILD_ID)  # Replace GUILD_ID with your guild's ID
    guild = bot.get_guild(1040160227389091872)
    for member in guild.members:
        # Get message count from the database
        c.execute("SELECT message_count FROM user_activity WHERE user_id=?", (str(member.id),))
        result = c.fetchone()
        if result:
            message_count = result[0]
        else:
            message_count = 0
        # Update message count for the current month
        message_count_current_month = 0
        for channel in guild.text_channels:
            async for message in channel.history(limit=None, after=datetime.datetime.utcnow() - datetime.timedelta(days=30)):
            # async for message in channel.history(limit=None, after=datetime.datetime.utcnow() - datetime.timedelta(days=1)).flatten():
                # if message.author == member:
                if message.author == member and str(message.id) not in get_counted_message_ids():
                    message_count_current_month += 1
                    # add counted message id
                    add_counted_message_id(str(message.id))
        message_count += message_count_current_month
        # Update message count in the database
        c.execute("REPLACE INTO user_activity (user_id, message_count) VALUES (?, ?)", (str(member.id), message_count))
        conn.commit()
        # Update roles based on message count
        for role, threshold in role_thresholds.items():
            if message_count >= threshold:
                role_obj = discord.utils.get(guild.roles, name=role)
                await member.add_roles(role_obj)
            else:
                role_obj = discord.utils.get(guild.roles, name=role)
                await member.remove_roles(role_obj)

# function to get IDs of counted messages from db
def get_counted_message_ids():
    c.execute("SELECT message_id FROM counted_messages")
    return [row[0] for row in c.fetchall()]

# function to add counted message ID to db
def add_counted_message_id(message_id):
    c.execute("INSERT INTO counted_messages (message_id, timestamp) VALUES (?, ?)", (message_id, datetime.datetime.utcnow()))
    conn.commit()

# function to delete outdated message IDs from db
def delete_outdated_message_ids():
    thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
    c.execute("DELETE FROM counted_messages WHERE timestamp < ?", (thirty_days_ago,))
    conn.commit()

# event listener for when the bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    # Start a background task to update roles periodically
    bot.loop.create_task(update_roles_loop())
    # start background task to clean up outdates messages IDs 
    bot.loop.create_task(delete_outdated_message_ids_loop())

# Background task to periodically update roles
async def update_roles_loop():
    while True:
        await update_roles()
        # await asyncio.sleep(3600)  # Update every hour (adjust as needed)
        await asyncio.sleep(300) # update every $x seconds

# background task to clean up outdates message IDs from db
async def delete_outdated_message_ids_loop():
    while True:
        delete_outdated_message_ids()
        await asyncio.sleep(86400) # cleanup every day

# Run the bot
bot.run(TOKEN)


import discord
import sqlite3
from discord.ext import commands

def setup_database() -> sqlite3.Connection:
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS music_roles (guild_id INTEGER PRIMARY KEY, role_id INTEGER)")
    conn.commit()
    return conn

db_conn = setup_database()
db_cursor = db_conn.cursor()

def get_music_role(bot: commands.Bot, guild_id: int) -> discord.Role:
    db_cursor.execute("SELECT role_id FROM music_roles WHERE guild_id = ?", (guild_id,))
    guild = bot.get_guild(guild_id)
    role_id = db_cursor.fetchone()
    if role_id is None:
        return None
    return discord.utils.get(guild.roles, id=role_id[0])

def set_music_role(bot: commands.Bot, guild: discord.Guild, role: discord.Role):
    db_cursor.execute("INSERT OR REPLACE INTO music_roles (guild_id, role_id) VALUES (?, ?)", (guild.id, role.id))
    db_conn.commit()
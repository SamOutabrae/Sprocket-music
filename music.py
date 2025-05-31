import discord
from discord.ext import commands

from .musiccontrol import Music

# Specify the intents for this module
def get_intents() -> discord.Intents:
    intents = discord.Intents.default()
    return intents

# Returns a list of cogs for this module
def get_cogs(client: commands.Bot, directory: str) -> list:
    return [Music(client)]
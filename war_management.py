import discord
from discord.ext import commands
from discord import app_commands, Interaction
from database_setup import conn, cursor


class WarManagement(commands.cog):
    def __init__(self, bot):
        self.bot = bot  # Store bot instance

    # WarCounters
    @app_commands.command(name="warcounter", description="Show a Team War counter, with punch ups and punch downs statistics")
    async def warcounter(self, Interaction:Interaction, Message: str):
        print("Hello")
    
    @app_commands.command(name="customwarcounter", description="Show possible counter for a custom team *Won't be accurate and baised on community inputs*")
    async def customwarcounter(self, Interation:Interaction):
        print("Hello")

    @app_commands.command(name="addcommunitywarcounter", description="Players can add new warcounters, which players can upvote and if it was a punch up or punch down to bring statistics")
    async def addcommunitywarcounter(self, Interaction:Interaction):
        print("Hello")

    # War Defence
    @app_commands.command(name="showwarseasonalbuff", description="Shows the current war seasonal buff with suggested war defencse teams")
    async def showwarseasonalbuff(self, Interaction:Interaction):
        print("Hello")
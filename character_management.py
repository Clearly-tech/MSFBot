from discord.ext import commands
import discord
from discord.ui import Select, Button, View
from discord import app_commands, Interaction
from getData import getdata
import asyncio
from database_setup import db_setup
from typing import Optional

class CharManage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _execute_query(self, query: str, params: tuple = ()) -> list:
        """Async query execution function"""
        cursor = db_setup.conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    async def _execute_commit(self, query: str, params: tuple = ()) -> None:
        """Executes a commit operation like INSERT/UPDATE"""
        cursor = db_setup.conn.cursor()
        cursor.execute(query, params)
        db_setup.conn.commit()

    @app_commands.command(name="add_player", description="Add a player to the database. Game Alliance ID required.")
    async def add_player(self, interaction: Interaction, player_name: str, player_game_id: str):
        player_discord_id = str(interaction.user.id)
        await self._execute_commit(
            'INSERT INTO players (player_name, player_discord_id, player_game_id) VALUES (?, ?, ?)',
            (player_name, player_discord_id, player_game_id)
        )
        player_id = db_setup.cursor.lastrowid
        await interaction.response.send_message(f"Player {player_name} added with Game ID {player_game_id}.")
        getdata.add_player_roster(player_id, player_game_id, False)

    @app_commands.command(name="get_roster", description="Retrieve player's character roster.")
    async def get_roster(self, interaction: Interaction, player_name: str):
        """Command to fetch and display the roster of a given player."""
        player_name = player_name.strip()
        cursor = db_setup.conn.cursor()

        # Look up the player by name
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        result = cursor.fetchone()

        if result:
            player_id = result[0]
            cursor.execute('SELECT name, level, power, iso_class FROM characters WHERE player_id = ?', (player_id,))
            characters = cursor.fetchall()
            current_page = 0
            characters_per_page = 5
            total_pages = (len(characters) + characters_per_page - 1) // characters_per_page

            def create_embed(page):
                embed = discord.Embed(
                    title=f"{player_name}'s Roster - Page {page + 1}/{total_pages}", 
                    color=discord.Color.blue()
                )
                start = page * characters_per_page
                for character in characters[start:start + characters_per_page]:
                    embed.add_field(
                        name=character[0], 
                        value=f"Level: {character[1]}, Power: {character[2]}, ISO Class: {character[3]}"
                    )
                return embed

            message = await interaction.response.send_message(embed=create_embed(current_page), ephemeral=True)
            await message.add_reaction("◀️")
            await message.add_reaction("▶️")

            def check(reaction, user):
                return (
                    user == interaction.user 
                    and str(reaction.emoji) in ["◀️", "▶️"] 
                    and reaction.message.id == message.id
                )

            while True:
                try:
                    reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    if str(reaction.emoji) == "▶️" and current_page < total_pages - 1:
                        current_page += 1
                        await message.edit(embed=create_embed(current_page))
                    elif str(reaction.emoji) == "◀️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=create_embed(current_page))
                    await message.remove_reaction(reaction, interaction.user)
                except asyncio.TimeoutError:
                    await message.clear_reactions()
                    break
        else:
            await interaction.response.send_message(f"No roster found for {player_name}.")

    @app_commands.command(name="find_character", description="Search for characters based on filters.")
    async def find_character(self, interaction: Interaction):
        bot = self.bot
        cursor = db_setup.conn.cursor()
        cursor.execute("SELECT DISTINCT name FROM characters")
        characters = sorted([row[0] for row in cursor.fetchall()])

        characters_per_page = 10
        current_page = 0
        max_page = (len(characters) - 1) // characters_per_page

        def create_character_embed(page):
            embed = discord.Embed(title="Select a Character", color=discord.Color.blue())
            start = page * characters_per_page
            for i, char in enumerate(characters[start:start + characters_per_page], start=1):
                embed.add_field(name=f"{i}. {char}", value="\u200b", inline=False)
            embed.set_footer(text=f"Page {page + 1} of {max_page + 1}")
            return embed

        def create_dropdown_options(page):
            start = page * characters_per_page
            return [discord.SelectOption(label=char, value=char) for char in characters[start:start + characters_per_page]]

        selection_msg = await interaction.response.send_message(embed=create_character_embed(current_page), ephemeral=True)
        dropdown = Select(placeholder="Choose a character", options=create_dropdown_options(current_page))

        skip_button = Button(label="Skip Character Selection", style=discord.ButtonStyle.secondary)

        dropdown_view = View()
        dropdown_view.add_item(dropdown)
        dropdown_view.add_item(skip_button)
        dropdown_msg = await interaction.followup.send("Select a character or skip:", view=dropdown_view, ephemeral=True)

        await selection_msg.add_reaction("⬅️")
        await selection_msg.add_reaction("➡️")

        async def select_callback(interaction):
            selected_character = dropdown.values[0]
            await dropdown_msg.delete()
            dropdown_view.stop()
            await self.run_filter_prompt(interaction, selected_character)

        async def skip_callback(interaction):
            await dropdown_msg.delete()
            dropdown_view.stop()
            await self.run_filter_prompt(interaction, None)  # Pass None to skip character filter

        dropdown.callback = select_callback
        skip_button.callback = skip_callback

        while True:
            try:
                reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=lambda r, u: u == interaction.user and str(r.emoji) in ["⬅️", "➡️"])
                if str(reaction.emoji) == "➡️" and current_page < max_page:
                    current_page += 1
                elif str(reaction.emoji) == "⬅️" and current_page > 0:
                    current_page -= 1
                await selection_msg.edit(embed=create_character_embed(current_page))
                dropdown.options = create_dropdown_options(current_page)
                await dropdown_msg.edit(view=dropdown_view)
                await selection_msg.remove_reaction(reaction.emoji, interaction.user)
            except asyncio.TimeoutError:
                await selection_msg.clear_reactions()
                break

async def setup(bot):
    await bot.add_cog(CharManage(bot))

from discord.ext import commands
import discord
from discord import app_commands, Interaction, SelectOption
from discord.ui import Select, Button, View
from database_setup import db_setup
from DiscordLoader import DiscordLoader
from collections import defaultdict
import asyncio

class InterHelpers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Store bot instance

    @app_commands.command(name="link_discord", description="Link your current Discord account to a player")
    async def link_discord(self, interaction: Interaction):
        """Starts an interactive, paginated wizard for player selection to link a Discord account."""

        # Check if the user's Discord account is already linked
        db_setup.cursor.execute('SELECT player_name FROM players WHERE player_discord_id = ?', (interaction.user.id,))
        result = db_setup.cursor.fetchone()

        if result:
            player_name = result[0]
            embed = discord.Embed(
                title="Already Linked",
                description="Your Discord account is already linked to a player.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Player Name", value=player_name, inline=True)
            embed.add_field(name="Discord Name", value=interaction.user.name, inline=True)
            embed.set_footer(text="Use /unlink_discord to unlink if needed.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Retrieve unlinked players from the database
        db_setup.cursor.execute("SELECT player_id, player_name FROM players WHERE player_discord_id IS NULL")
        players = db_setup.cursor.fetchall()

        if not players:
            embed = discord.Embed(
                title="No Players Available",
                description="No players are available for linking. Ask your alliance leader to use `/update_alliance`.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Pagination setup
        players_per_page = 5
        current_page = 0
        max_page = (len(players) - 1) // players_per_page

        # Helper functions for creating embed and dropdown
        def create_player_embed(page):
            embed = discord.Embed(
                title="Link Your Discord Account to a Player",
                color=discord.Color.blue()
            )
            start = page * players_per_page
            for i, (player_id, player_name) in enumerate(players[start:start + players_per_page], start=1):
                embed.add_field(name=f"{i}. {player_name}", value=f"ID: {player_id}", inline=False)
            embed.set_footer(text=f"Page {page + 1} of {max_page + 1}")
            return embed

        def create_dropdown_options(page):
            start = page * players_per_page
            return [SelectOption(label=player_name, description=f"Player ID: {player_id}", value=str(player_id))
                    for player_id, player_name in players[start:start + players_per_page]]

        # Send the initial embed and dropdown
        embed = create_player_embed(current_page)
        view = View()

        dropdown = Select(placeholder="Choose a player to link", options=create_dropdown_options(current_page))
        view.add_item(dropdown)

        message = await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # Define dropdown callback
        async def select_callback(inner_interaction: Interaction):
            selected_player_id = int(dropdown.values[0])
            db_setup.cursor.execute(
                'UPDATE players SET player_discord_id = ? WHERE player_id = ?',
                (interaction.user.id, selected_player_id)
            )
            db_setup.conn.commit()

            db_setup.cursor.execute('SELECT player_name FROM players WHERE player_id = ?', (selected_player_id,))
            player_name = db_setup.cursor.fetchone()[0]

            embed = discord.Embed(
                title="Link Successful",
                description=f"Your Discord account has been successfully linked to **{player_name}**.",
                color=discord.Color.green()
            )
            embed.add_field(name="Player Name", value=player_name, inline=True)
            embed.add_field(name="Discord Name", value=interaction.user.name, inline=True)
            embed.set_footer(text="Use /unlink_discord to unlink if needed.")
            await inner_interaction.response.edit_message(embed=embed, view=None)

        dropdown.callback = select_callback

    @app_commands.command(name="unlink_discord", description="Unlink your Discord account from a player")
    async def unlink_discord(self, interaction: Interaction):
        """Unlinks the user's Discord account from a player."""

        # Check if the user's Discord account is linked to any player
        db_setup.cursor.execute('SELECT player_id, player_name FROM players WHERE player_discord_id = ?', (interaction.user.id,))
        result = db_setup.cursor.fetchone()

        if result:
            player_id, player_name = result
            db_setup.cursor.execute('UPDATE players SET player_discord_id = NULL WHERE player_id = ?', (player_id,))
            db_setup.conn.commit()

            embed = discord.Embed(
                title="Unlink Successful",
                description=f"Your Discord account has been successfully unlinked from **{player_name}**.",
                color=discord.Color.green()
            )
            embed.add_field(name="Player Name", value=player_name, inline=True)
            embed.set_footer(text="You can relink with `/link_discord`.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="Unlink Failed",
                description="No linked player account was found for your Discord ID.",
                color=discord.Color.red()
            )
            embed.set_footer(text="You can link an account using `/link_discord`.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="get_self", description="Retrieve your linked player roster")
    async def get_self(self, interaction: Interaction):
        """Fetches and displays the roster of the user linked to their Discord account."""

        loader = DiscordLoader(interaction.channel)
        await loader.initialize_loader("Checking user link...")

        db_setup.cursor.execute('SELECT player_id FROM players WHERE player_discord_id = ?', (interaction.user.id,))
        result = db_setup.cursor.fetchone()

        if result:
            player_id = result[0]
            db_setup.cursor.execute('SELECT name, level, power FROM characters WHERE player_id = ?', (player_id,))
            characters = db_setup.cursor.fetchall()

            if not characters:
                await loader.finish_loader("No characters found in your roster.")
                return

            current_page = 0
            characters_per_page = 5
            total_pages = (len(characters) + characters_per_page - 1) // characters_per_page

            def create_embed(page):
                embed = discord.Embed(title=f"Your Roster - Page {page + 1}/{total_pages}", color=discord.Color.blue())
                start = page * characters_per_page
                for character in characters[start:start + characters_per_page]:
                    embed.add_field(name=character[0], value=f"Level: {character[1]}, Power: {character[2]}")
                return embed

            message = await interaction.response.send_message(embed=create_embed(current_page), ephemeral=True)

            def check(reaction, user):
                return user == interaction.user and str(reaction.emoji) in ["◀️", "▶️"]

            await message.add_reaction("◀️")
            await message.add_reaction("▶️")

            while True:
                try:
                    reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    if str(reaction.emoji) == "▶️" and current_page < total_pages - 1:
                        current_page += 1
                        await message.edit(embed=create_embed(current_page))
                    elif str(reaction.emoji) == "◀️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=create_embed(current_page))
                    await message.remove_reaction(reaction.emoji, interaction.user)
                except asyncio.TimeoutError:
                    await message.clear_reactions()
                    break
        else:
            await loader.finish_loader("No linked player found. Use `/link_discord` to link.")

async def setup(bot):
    await bot.add_cog(InterHelpers(bot))

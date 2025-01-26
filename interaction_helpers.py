import discord
from discord.ext import commands
from discord import SelectOption
from discord.ui import Select, View
from database_setup import conn, cursor
from DiscordLoader import DiscordLoader
import asyncio

class InteractionHelpers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="link_discord")
    async def link_discord(self, ctx):
        """Starts an interactive, paginated wizard for player selection to link a Discord account."""
        # Check if the user's Discord account is already linked
        cursor.execute('SELECT player_id, player_name FROM players WHERE player_discord_id = ?', (ctx.author.id,))
        result = cursor.fetchone()

        if result:
            player_id, player_name = result
            embed = discord.Embed(
                title="Link Successful",
                description="Your account is already linked.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Player Name", value=player_name, inline=True)
            embed.add_field(name="Discord Name", value=ctx.author.name, inline=True)
            embed.set_footer(text="Use /unlink_discord to unlink if needed.")
            await ctx.send(embed=embed)
            return

        # Retrieve unlinked players from the database
        cursor.execute("SELECT player_id, player_name FROM players WHERE player_discord_id IS NULL")
        players = cursor.fetchall()

        if not players:
            embed = discord.Embed(
                title="No players available for linking.",
                description="Try again later after the alliance leader uses '/update_alliance'.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        # Pagination variables
        players_per_page = 5
        current_page = 0
        max_page = (len(players) - 1) // players_per_page

        def create_player_embed(page):
            embed = discord.Embed(title="Link Your Discord Account to a Player", color=discord.Color.blue())
            start = page * players_per_page
            for i, (player_id, player_name) in enumerate(players[start:start + players_per_page], start=1):
                embed.add_field(name=f"{i}. {player_name}", value=f"ID: {player_id}", inline=False)
            embed.set_footer(text=f"Page {page + 1} of {max_page + 1}")
            return embed

        def create_dropdown_options(page):
            start = page * players_per_page
            return [SelectOption(label=player_name, description=f"Player ID: {player_id}", value=str(player_id))
                    for player_id, player_name in players[start:start + players_per_page]]

        selection_msg = await ctx.send(embed=create_player_embed(current_page))
        dropdown = Select(placeholder="Choose a player to link", options=create_dropdown_options(current_page))
        dropdown_view = View()
        dropdown_view.add_item(dropdown)
        dropdown_msg = await ctx.send("Select a player from the dropdown below:", view=dropdown_view)

        await selection_msg.add_reaction("⬅️")
        await selection_msg.add_reaction("➡️")

        async def select_callback(interaction):
            selected_player_id = int(dropdown.values[0])
            cursor.execute('UPDATE players SET player_discord_id = ? WHERE player_id = ?', (ctx.author.id, selected_player_id))
            conn.commit()
            cursor.execute('SELECT player_name FROM players WHERE player_discord_id = ?', (ctx.author.id,))
            player_name = cursor.fetchone()[0]

            await dropdown_msg.delete()
            dropdown_view.stop()
            embed = discord.Embed(
                title="Link Successful",
                description=f"Your Discord account has been successfully linked to **{player_name}**.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Player Name", value=player_name, inline=True)
            embed.add_field(name="Discord Name", value=ctx.author.name, inline=True)
            embed.set_footer(text="Use /unlink_discord to unlink if needed.")
            await ctx.send(embed=embed)

        dropdown.callback = select_callback

        while True:
            try:
                reaction, _ = await self.bot.wait_for("reaction_add", timeout=60.0, 
                    check=lambda r, u: u == ctx.author and str(r.emoji) in ["⬅️", "➡️"])
                if str(reaction.emoji) == "➡️" and current_page < max_page:
                    current_page += 1
                elif str(reaction.emoji) == "⬅️" and current_page > 0:
                    current_page -= 1
                await selection_msg.edit(embed=create_player_embed(current_page))
                dropdown.options = create_dropdown_options(current_page)
                await dropdown_msg.edit(view=dropdown_view)
                await selection_msg.remove_reaction(reaction.emoji, ctx.author)
            except asyncio.TimeoutError:
                await selection_msg.clear_reactions()
                break

    @commands.command(name="unlink_discord")
    async def unlink_discord(self, ctx):
        cursor.execute('SELECT player_id, player_name FROM players WHERE player_discord_id = ?', (ctx.author.id,))
        result = cursor.fetchone()

        if result:
            player_id, player_name = result
            cursor.execute('UPDATE players SET player_discord_id = NULL WHERE player_id = ?', (player_id,))
            conn.commit()
            embed = discord.Embed(
                title="Unlink Successful",
                description=f"Your Discord account has been successfully unlinked from **{player_name}**.",
                color=discord.Color.green()
            )
            embed.add_field(name="Player Name", value=player_name, inline=True)
            embed.add_field(name="Player ID", value=player_id, inline=True)
            embed.set_footer(text="Use /link_discord to link again if needed.")
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Unlink Failed",
                description="No linked player account was found for your Discord ID.",
                color=discord.Color.red()
            )
            embed.add_field(name="Note", value="You can link an account using `/link_discord`.", inline=False)
            await ctx.send(embed=embed)

    @commands.command(name="get_self")
    async def get_self(self, ctx):
        loader = DiscordLoader(ctx.channel)
        await loader.initialize_loader("Checking for user")

        cursor.execute('SELECT player_id FROM players WHERE player_discord_id = ?', (ctx.author.id,))
        result = cursor.fetchone()

        if result:
            player_id = result[0]
            cursor.execute('SELECT name, level, power FROM characters WHERE player_id = ?', (player_id,))
            characters = cursor.fetchall()

            current_page = 0
            characters_per_page = 5
            total_pages = (len(characters) + characters_per_page - 1) // characters_per_page

            def create_embed(page):
                embed = discord.Embed(title=f"Your Roster - Page {page + 1}/{total_pages}", color=discord.Color.blue())
                start = page * characters_per_page
                for character in characters[start:start + characters_per_page]:
                    embed.add_field(name=character[0], value=f"Level: {character[1]}, Power: {character[2]}")
                return embed

            message = await ctx.send(embed=create_embed(current_page))
            await message.add_reaction("◀️")
            await message.add_reaction("▶️")
            await loader.finish_loader("User Found!\nIf this is incorrect, try `/unlink_discord` and `/link_discord` again.")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == message.id

            while True:
                try:
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                    if str(reaction.emoji) == "▶️" and current_page < total_pages - 1:
                        current_page += 1
                        await message.edit(embed=create_embed(current_page))
                    elif str(reaction.emoji) == "◀️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=create_embed(current_page))
                    await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    await message.clear_reactions()
                    break
        else:
            await loader.finish_loader("User Not Found.\nYou do not have an account set up. Try `/link_discord`.")



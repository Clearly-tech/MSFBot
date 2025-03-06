from discord.ext import commands
from discord import Interaction, SelectOption, app_commands
from discord.ui import Select, Button, View
import discord
import json
import time
import asyncio
from config import Debug_A, Debug_B
from bs4 import BeautifulSoup
from database_setup import conn, cursor
from selenium_setup import driver, cookies

class CharacterManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def add_character(player_id, character_data):
        try:
            cursor.execute(
                '''
                INSERT INTO characters (player_id, name, level, power, gear_tier, iso_class, abilities, stars_red, normal_stars, diamonds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    player_id,
                    character_data["Name"],
                    character_data["Level"],
                    character_data["Power"],
                    character_data["Gear Tier"],
                    character_data["ISO Class"],
                    json.dumps(character_data["Abilities"]),
                    character_data["Stars (Red)"],
                    character_data["Normal Stars"],
                    character_data["Diamonds"]
                )
            )
            conn.commit()
        except Exception as e:
            print(f"Error inserting character: {e}")
            print(f"Character data: {character_data}")

    @staticmethod
    def parse_character_block(char_block):
        try:
            # Extract name
            name_tag = char_block.find('h4')
            name = name_tag.get_text(strip=True) if name_tag else "Unknown"

            # Extract toon stats
            toon_stats = char_block.find('div', id='toon-stats')
            level = int(
                (toon_stats.find('div', style=lambda x: 'font-size: 12px;' in x).get_text(strip=True).replace("LVL", ""))
                if toon_stats else 0
            )
            power = int(
                (toon_stats.find('div', style=lambda x: 'font-size: 18px;' in x).get_text(strip=True).replace(",", ""))
                if toon_stats else 0
            )

            # Extract gear tier
            gear_tier_ring = char_block.find('div', class_='gear-tier-ring')
            gear_tier = int(
                ((gear_tier_ring.find('svg') or {}).get('class', [""])[0][1:] or "0")
            ) if gear_tier_ring else 0

            # Extract ISO class
            iso_class = "Unknown"
            iso_wrapper = char_block.find('div', class_='iso-wrapper')
            if iso_wrapper:
                for trait in ['restoration', 'assassin', 'skirmish', 'fortify', 'gambler']:
                    for tier in ['purple', 'blue', 'green']:
                        if iso_wrapper.find('div', class_=f'iso-{trait}-{tier}'):
                            iso_class = f'iso-{trait}-{tier}'
                            break
                    if iso_class != "Unknown":
                        break

            # Extract ability levels
            ability_levels = []
            ability_wrapper = char_block.find('div', class_='ability-level-wrapper')
            if ability_wrapper:
                ability_levels = [
                    (div.get('title') or div['class'][-1])
                    for div in ability_wrapper.find_all('div', class_='ability-level')
                ]

            # Extract stars and diamonds
            diamonds_container = char_block.find('div', class_='diamonds-container')
            diamonds = len(
                diamonds_container.find_all('div', class_='equipped-diamond diamond-filled')
            ) if diamonds_container else 0
            red_star_count = normal_star_count = diamonds if diamonds <= 3 else 7

            return {
                "Name": name,
                "Level": level,
                "Power": power,
                "Gear Tier": gear_tier,
                "ISO Class": iso_class,
                "Abilities": ability_levels,
                "Stars (Red)": red_star_count,
                "Normal Stars": normal_star_count,
                "Diamonds": diamonds
            }
        except Exception as e:
            print(f"Error parsing character block: {char_block}")
            print(f"Error details: {e}")
            return None

    @staticmethod
    def add_player_roster(player_id, player_game_id, is_self):
        url = f"https://marvelstrikeforce.com/en/{'player/characters' if is_self else f'member/{player_game_id}/characters'}"
        driver.get(url)

        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        character_blocks = soup.find_all('li', class_='character')

        for char_block in character_blocks:
            if Debug_A:
                print(f"Parsing character block: {char_block}")
            character_data = CharacterManagement.parse_character_block(char_block)
            if Debug_A:
                print(f"Parsed character data: {character_data}")
            CharacterManagement.add_character(player_id, character_data)

    @app_commands.command(name="add_player", description="Add a player to the database. Requires Game Alliance ID.")
    async def add_player(self, interaction: Interaction, player_name: str, player_game_id: str):
        player_discord_id = str(interaction.user.id)
        cursor.execute(
            'INSERT INTO players (player_name, player_discord_id, player_game_id) VALUES (?, ?, ?)',
            (player_name, player_discord_id, player_game_id)
        )
        conn.commit()
        player_id = cursor.lastrowid
        await interaction.response.send_message(f"Player {player_name} added with Game ID {player_game_id}.")
        CharacterManagement.add_player_roster(player_id, player_game_id, False)

    @app_commands.command(name="get_roster", description="Retrieve and paginate a player's roster.")
    async def get_roster(self, interaction: Interaction, player_name: str):
        cursor.execute('SELECT player_id FROM players WHERE player_name = ?', (player_name,))
        result = cursor.fetchone()

        if not result:
            await interaction.response.send_message(f"No roster found for {player_name}.")
            return

        player_id = result[0]
        cursor.execute('SELECT name, level, power, iso_class FROM characters WHERE player_id = ?', (player_id,))
        characters = cursor.fetchall()

        characters_per_page = 5
        total_pages = (len(characters) + characters_per_page - 1) // characters_per_page

        def create_embed(page):
            embed = discord.Embed(title=f"{player_name}'s Roster", color=discord.Color.blue())
            start = page * characters_per_page
            for char in characters[start:start + characters_per_page]:
                embed.add_field(name=char[0], value=f"Level: {char[1]}, Power: {char[2]}, ISO Class: {char[3]}")
            embed.set_footer(text=f"Page {page + 1}/{total_pages}")
            return embed

        current_page = 0
        message = await interaction.response.send_message(embed=create_embed(current_page))
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        def check(reaction, user):
            return user == interaction.user and str(reaction.emoji) in ["◀️", "▶️"]

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

    @app_commands.command(name="find_character", description="Find and select a character.")
    async def find_character(self, interaction: Interaction):
        """Starts an interactive, paginated wizard for character selection with skip options."""
        bot = interaction.client  # Access the bot instance via the Interaction object
        # Retrieve and sort characters from the database
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
            return [SelectOption(label=char, value=char) for char in characters[start:start + characters_per_page]]

        selection_msg = await interaction.response.send_message(embed=create_character_embed(current_page))
        dropdown = Select(placeholder="Choose a character", options=create_dropdown_options(current_page))

        skip_button = Button(label="Skip Character Selection", style=discord.ButtonStyle.secondary)

        # Initialize the view and add components
        dropdown_view = View()
        dropdown_view.add_item(dropdown)
        dropdown_view.add_item(skip_button)
        dropdown_msg = await interaction.followup.send("Select a character from the dropdown below, or skip:", view=dropdown_view)

        async def select_callback(interaction):
            selected_character = dropdown.values[0]
            await dropdown_msg.delete()
            dropdown_view.stop()  # Stop the view after selection
            await self.run_filter_prompt(interaction, selected_character)

        async def skip_callback(interaction):
            await dropdown_msg.delete()
            dropdown_view.stop()  # Stop the view if skipped
            await self.run_filter_prompt(interaction, None)  # Pass None to skip character filter

        dropdown.callback = select_callback
        skip_button.callback = skip_callback

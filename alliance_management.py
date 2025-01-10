from discord.ext import commands
from discord import app_commands, Interaction
from database_setup import db_setup
from selenium_setup import SeleniumSetup as selenium_setup, driver, cookies
from getData import getdata
from DiscordLoader import DiscordLoader
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class AllianceManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Store bot instance

    # Helper function to fetch alliance members
    async def fetch_alliance_members(self):
        try:
            driver.get("https://marvelstrikeforce.com/en/alliance/members")

            for cookie in cookies:
                driver.add_cookie(cookie)

            driver.refresh()

            # Wait dynamically for the content to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "tr"))
            )

            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            member_data = []
            rows = soup.select("tr")

            for row in rows:
                name_tag = row.select_one(".member-card-info .name span")
                name = name_tag.text.strip() if name_tag else "Unknown"
                is_self = row.find("span", class_="ability-lime")
                
                link_tag = row.select_one("a.button.blue-primary.small.rsl")
                if link_tag:
                    href = link_tag.get("href")
                    if href:
                        if is_self and "/en/player/" in href:
                            member_id = href.split("/en/player/")[1].split("/info")[0]
                        elif "/en/member/" in href:
                            member_id = href.split("/en/member/")[1].split("/info")[0]
                        else:
                            continue
                        member_data.append((name, member_id, bool(is_self)))

            return member_data

        except Exception as e:
            print(f"Error fetching alliance members: {e}")
            return []

    @app_commands.command(name="alliance_cleanup", description="Clean old players")
    async def alliance_cleanup(self, interaction: Interaction):
        try:
            db_setup.cursor.execute('SELECT player_id, player_name FROM players')
            all_players = db_setup.cursor.fetchall()
            removed_players = []

            for player_id, player_name in all_players:
                db_setup.cursor.execute('SELECT COUNT(*) FROM characters WHERE player_id = ?', (player_id,))
                if db_setup.cursor.fetchone()[0] == 0:
                    with db_setup.conn:
                        db_setup.cursor.execute('DELETE FROM players WHERE player_id = ?', (player_id,))
                    removed_players.append(player_name)

            await interaction.response.send_message(
                "Players removed due to no characters: " + ", ".join(removed_players)
            )
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}")

    @app_commands.command(name="setup", description="Setup Alliance")
    async def setup(self, interaction: Interaction):
        await interaction.response.send_message("Function doesn't work right now")

    @app_commands.command(name="update_alliance", description="Update Rosters")
    async def update_alliance(self, interaction: Interaction):
        try:
            loader = DiscordLoader(interaction.channel)
            await loader.initialize_loader("Updating Alliance")

            # Fetch alliance members
            members = await self.fetch_alliance_members()

            # Collect player_game_id for all members
            member_ids = {member[1] for member in members}
            total_members = len(members)

            # Get existing players from the database
            db_setup.cursor.execute('SELECT player_id, player_game_id FROM players')
            existing_players = db_setup.cursor.fetchall()

            # Find players to delete
            players_to_delete = [player for player in existing_players if player[1] not in member_ids]
            for player_id, _ in players_to_delete:
                with db_setup.conn:
                    db_setup.cursor.execute('DELETE FROM players WHERE player_id = ?', (player_id,))

            # Process members
            for index, (member_name, member_id, is_self) in enumerate(members, start=1):
                db_setup.cursor.execute('SELECT player_id FROM players WHERE player_game_id = ?', (member_id,))
                result = db_setup.cursor.fetchone()

                if result:
                    player_id = result[0]
                    # Player exists, so delete their existing character data
                    with db_setup.conn:
                        db_setup.cursor.execute('DELETE FROM characters WHERE player_id = ?', (player_id,))
                else:
                    # Player does not exist, so insert them into the players table
                    with db_setup.conn:
                        db_setup.cursor.execute(
                            'INSERT INTO players (player_name, player_game_id) VALUES (?, ?)', 
                            (member_name, member_id)
                        )
                        player_id = db_setup.cursor.lastrowid

                # Add character data
                getdata.add_player_roster(player_id, member_id, is_self)

                # Update progress
                await loader.update_loader(f"Uploading player: {member_name}", index, total_members)

            # Perform cleanup after update
            await self.alliance_cleanup(interaction)

            await loader.finish_loader("Update Complete!")
            await interaction.response.send_message("Alliance updated successfully!")

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(AllianceManager(bot))

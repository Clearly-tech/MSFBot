import discord
from discord.ext import commands
from database_setup import cursor, conn
from selenium_setup import driver, cookies
from character_management import CharacterManagement
from DiscordLoader import DiscordLoader
from bs4 import BeautifulSoup
from config import Debug_B
from war_schedule import WarScheduler
import time
import asyncio

class AllianceManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if Debug_B:
            print("AllianceManagement cog initialized.")

    @commands.command(name="alliance_cleanup")
    async def alliance_cleanup(self, ctx):
        cursor.execute('SELECT player_id, player_name FROM players')
        all_players = cursor.fetchall()
        removed_players = []

        for player_id, player_name in all_players:
            cursor.execute('SELECT COUNT(*) FROM characters WHERE player_id = ?', (player_id,))
            if cursor.fetchone()[0] == 0:
                cursor.execute('DELETE FROM players WHERE player_id = ?', (player_id,))
                removed_players.append(player_name)

        conn.commit()
        await ctx.send("Players removed due to no characters: " + ", ".join(removed_players))

    @commands.command(name="update_alliance")
    async def update_alliance(self, ctx, alliance_url=None, alliance_id=None, issetup=None):
        if not alliance_url:
            alliance_url = "https://marvelstrikeforce.com/en/alliance/members"

        # Fetch alliance_id if not provided
        if not alliance_id:
            cursor.execute('SELECT alliance_id FROM alliance WHERE url = ?', (alliance_url,))
            result = cursor.fetchone()
            if result:
                alliance_id = result[0]
            else:
                await ctx.send("Alliance ID not found. Please make sure the alliance is set up first.")
                return

        await ctx.send("This will update the alliance members' roster list.\n**This will not include alliance members who are not sharing their roster.**")
        loader = DiscordLoader(ctx.channel)
        await loader.initialize_loader("Updating Alliance")

        if not issetup:
            await self.fetch_alliance_details(alliance_url)

        try:
            # Fetch members from the provided alliance URL
            members = await self.fetch_alliance_members(alliance_url)
            member_ids = {member[1] for member in members}
            total_members = len(members)

            # Fetch existing players from the database
            cursor.execute('SELECT player_id, player_game_id FROM players')
            existing_players = cursor.fetchall()

            # Identify players to delete
            players_to_delete = [player for player in existing_players if player[1] not in member_ids]
            for player_id, _ in players_to_delete:
                cursor.execute('DELETE FROM players WHERE player_id = ?', (player_id,))

            # Process and update each member
            for index, (member_name, member_id, is_self) in enumerate(members, start=1):
                cursor.execute('SELECT player_id FROM players WHERE player_game_id = ?', (member_id,))
                result = cursor.fetchone()

                if result:
                    # Player exists, clear their characters
                    player_id = result[0]
                    cursor.execute('DELETE FROM characters WHERE player_id = ?', (player_id,))
                else:
                    # New player, insert into database
                    cursor.execute(
                        'INSERT INTO players (player_name, player_game_id, alliance_id) VALUES (?, ?, ?)',
                        (member_name, member_id, alliance_id)
                    )
                    player_id = cursor.lastrowid

                # Update roster for the player
                CharacterManagement.add_player_roster(player_id, member_id, is_self)

                # Update progress in the loader
                await loader.update_loader(f"Uploading player: {member_name}", index, total_members)

            # Finalize loader
            await self.alliance_cleanup(ctx)
            await loader.finish_loader("Update Complete!")

        except Exception as e:
            await loader.finish_loader("Update Failed.")
            await ctx.send(f"An error occurred during the update: {str(e)}")

    @commands.command(name="setup")
    async def setup(self, ctx):
        if Debug_B:
            print("Setup command initiated.")
        await ctx.send("Welcome to the Alliance Setup Wizard!\nPlease provide the alliance link or use https://marvelstrikeforce.com/en/alliance/members to use the default if you are in the alliance.")

        def check(message):
            if Debug_B:
                print(f"User Sent: {message.content}")
            return message.author == ctx.author and message.channel == ctx.channel

        def check_reactions(reaction, user):
            if Debug_B:
                print(f"{user} Reacted: {reaction.emoji}")
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"]

        try:
            if Debug_B:
                print("Waiting for user response...")
            user_input = await self.bot.wait_for("message", check=check, timeout=60)
            alliance_url = user_input.content.strip()
            if Debug_B:
                print(f"User provided alliance URL: {alliance_url}")

            if not alliance_url:
                alliance_url = "https://marvelstrikeforce.com/en/alliance/members"
                if Debug_B:
                    print(f"Default URL used: {alliance_url}")

            alliance = await self.fetch_alliance_details(alliance_url)

            response = await ctx.send(f"Do you wish the bot to notify you on war times?\nThis alliance is currently on: {alliance['zone']}")
            await response.add_reaction("✅")
            await response.add_reaction("❌")

            try:
                if Debug_B:
                    print("Waiting for reaction from user...")
                reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check_reactions)
                if Debug_B:
                    print(f"User reacted with: {reaction.emoji}")

                if str(reaction.emoji) == "✅":
                    await ctx.send("Which channel do you want to be notified in?")
                    user_input2 = await self.bot.wait_for("message", check=check, timeout=60)
                    channel_id = user_input2.content.strip()
                        
                    if Debug_B:
                        print(f"Notification channel ID provided: {channel_id}")

                    await ctx.send("Set a message for the Reminder.")
                    user_input3 = await self.bot.wait_for("message", check=check, timeout=60)
                    if Debug_B:
                        print(f"Reminder message set to: {user_input3.content}")

                    channel = self.bot.get_channel(int(channel_id))
                    if channel is None:
                        if Debug_B:
                            print(f"Channel {channel_id} not found in cache. Fetching from Discord API.")
                        try:
                            channel = await self.bot.fetch_channel(int(channel_id))
                        except discord.DiscordException as e:
                            await ctx.send(f"Error accessing channel: {e}")
                            if Debug_B:
                                print(f"Error fetching channel: {e}")
                            return
                    war_scheduler = WarScheduler(self.bot)
                    await war_scheduler.add_zone_reminder(alliance['zone'], int(channel_id), message=user_input3.content)


                    if Debug_B:
                        print("Adding schedule to the database.")
                    cursor.execute('SELECT alliance_id FROM alliance WHERE name = ?', (alliance['name'],))
                    alliance_id = cursor.fetchone()[0]
                    if Debug_B:
                        print(f"Alliance ID fetched: {alliance_id}")

                    if alliance_id:
                        cursor.execute(
                            '''
                            UPDATE alliance_discord_settings
                            SET current_war_enemy = ?, War_channel = ?, bot_controls_channel_alliance = ?, bot_controls_channel_members = ?
                            WHERE alliance_id = ?
                            ''', ('', channel.id, '', '', alliance_id)
                        )
                    else:
                        cursor.execute(
                            '''
                            INSERT INTO alliance_discord_settings (current_war_enemy, War_channel, bot_controls_channel_alliance, bot_controls_channel_members, alliance_id)
                            VALUES (?, ?, ?, ?, ?)
                            ''', ('', channel.id, '', '', alliance_id)
                        )
                    conn.commit()
                    if Debug_B:
                        print("Database updated successfully.")
                    await ctx.send("Schedule Added!")

                elif str(reaction.emoji) == "❌":
                    await ctx.send("You said No!")
                    if Debug_B:
                        print("User declined schedule setup.")
            except asyncio.TimeoutError:
                await ctx.send("You didn't respond in time!")
                if Debug_B:
                    print("Reaction timeout occurred.")

            await ctx.send(
                f"Alliance '{alliance['name']}' has been successfully set up!\n"
                f"Details:\n"
                f" - URL: {alliance_url}\n"
                f" - Level: {alliance['level']}\n"
                f" - Total Power: {alliance['power']}\n"
                f" - Members: {alliance['players']}\n"
            )
            if Debug_B:
                print(f"Alliance setup completed: {alliance}")
            await self.update_alliance(ctx, alliance_url, issetup=True)

        except Exception as e:
            await ctx.send(f"Setup failed: {str(e)}")
            if Debug_B:
                print(f"Setup failed with exception: {e}")
        await ctx.send("Setup Finished")

    async def fetch_alliance_details(self, url):
        if Debug_B:
            print(f"Fetching alliance details for URL: {url}")

        driver.get(url)
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(5)

        html_content = driver.page_source
        if Debug_B:
            print(f"HTML content fetched with length: {len(html_content)}")

        soup = BeautifulSoup(html_content, 'html.parser')

        alliance_name_tag = soup.find('h2', {'data-v-d0267c96': ''})
        alliance_name = (
            alliance_name_tag.find('span').text if alliance_name_tag and alliance_name_tag.find('span') else "Unknown"
        )
        if Debug_B:
            print(f"Extracted alliance name: {alliance_name}")

        level_tag = soup.find('div', class_='alliance-level')
        alliance_level = (
            int(level_tag.text.split(":")[1].strip()) if level_tag and ":" in level_tag.text else 0
        )
        if Debug_B:
            print(f"Extracted alliance level: {alliance_level}")

        total_power_tag = soup.find('div', class_='filter-title', string='total power')
        total_power_value = (
            total_power_tag.find_next_sibling('div').text if total_power_tag and total_power_tag.find_next_sibling('div') else "0"
        )
        if Debug_B:
            print(f"Extracted total power: {total_power_value}")

        members_tag = soup.find('div', class_='members')
        num_players = (
            members_tag.find_all('span')[-1].text if members_tag and members_tag.find_all('span') else "0/0"
        )
        if Debug_B:
            print(f"Extracted number of players: {num_players}")

        war_time_tag = soup.find('div', class_='filter-title', string='War Time')
        zone_number = (
            war_time_tag.find_next_sibling('div').text if war_time_tag and war_time_tag.find_next_sibling('div') else "Unknown"
        )
        if Debug_B:
            print(f"Extracted zone number: {zone_number}")

        cursor.execute('SELECT zone_id FROM zone_times WHERE zone_name = ?', (zone_number,))
        zone = cursor.fetchone()
        zone_id = zone[0] if zone else None

        cursor.execute('SELECT COUNT(*) FROM alliance WHERE url = ?', (url,))
        exists = cursor.fetchone()[0]

        if exists:
            if Debug_B:
                print("Alliance exists, updating record.")
            cursor.execute(
                '''
                UPDATE alliance
                SET name = ?, level = ?, power = ?, num_players = ?, zone_id = ?
                WHERE url = ?
                ''', (alliance_name, alliance_level, total_power_value, num_players, zone_id, url)
            )
        else:
            if Debug_B:
                print("Alliance does not exist, inserting new record.")
            cursor.execute(
                '''
                INSERT INTO alliance (url, name, level, power, num_players, zone_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (url, alliance_name, alliance_level, total_power_value, num_players, zone_id)
            )
        conn.commit()

        return {
            "name": alliance_name,
            "level": alliance_level,
            "power": total_power_value,
            "players": num_players,
            "zone": zone_number
        }
    
    async def fetch_alliance_members(self, alliance_url):
        driver.get(alliance_url)
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()
        time.sleep(5)

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        member_data = []
        rows = soup.select("tr")

        for row in rows:
            name_tag = row.select_one(".member-card-info .name span span")
            name = name_tag.text.strip() if name_tag else "Unknown"

            is_self = row.select_one(".member-card-info .name span.ability-lime") is not None

            link_tag = row.select_one("a.button.blue-primary.small.rsl")
            if link_tag:
                href = link_tag.get("href")
                if href:
                    if is_self:
                        if "/en/player/info" in href:
                            member_id = "self"
                        else:
                            continue
                    elif "/en/member/" in href:
                        member_id = href.split("/en/member/")[1].split("/info")[0]
                    else:
                        continue

                    member_data.append((name, member_id, is_self))

        return member_data


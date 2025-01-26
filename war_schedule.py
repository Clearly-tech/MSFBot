import discord
from discord.ext import commands
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
import sqlite3
from database_setup import cursor, conn

# Initialize the scheduler
scheduler = AsyncIOScheduler()

class WarScheduler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def parse_cron_expression(cron_expression):
        """
        Parse and validate a cron expression.

        Args:
            cron_expression (str): Cron expression to parse.
        
        Returns:
            tuple: (minute, hour, day_of_week).
        """
        try:
            cron_parts = cron_expression.split(" ")
            if len(cron_parts) != 5:
                raise ValueError("Invalid cron expression format.")
            minute, hour, _, _, day_of_week = cron_parts
            return minute, hour, day_of_week
        except Exception as e:
            raise ValueError(f"Error parsing cron expression: {e}")

    async def reload_jobs_from_db(self):
        """
        Reload all scheduled jobs from the database and add them to the scheduler.
        """
        cursor.execute('SELECT job_id, zone_id, channel_id, message, cron_expression, timezone FROM scheduled_jobs')
        jobs = cursor.fetchall()

        for job_id, zone_id, channel_id, message, cron_expression, timezone in jobs:
            try:
                minute, hour, day_of_week = self.parse_cron_expression(cron_expression)

                scheduler.add_job(
                    self.send_reminder_with_timestamp,
                    CronTrigger(
                        day_of_week=day_of_week,
                        hour=int(hour),
                        minute=int(minute),
                        timezone=timezone,
                    ),
                    args=[channel_id, int(hour), int(minute), message],
                    id=job_id,
                    replace_existing=True,
                )
            except Exception as e:
                print(f"Error reloading job {job_id}: {e}")

    async def save_job_to_db(self, job_id, zone_id, channel_id, message, cron_expression, timezone="America/New_York"):
        """
        Save a scheduled job to the database.
        """
        try:
            cursor.execute('''
                INSERT INTO scheduled_jobs (job_id, zone_id, channel_id, message, cron_expression, timezone)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (job_id, zone_id, channel_id, message, cron_expression, timezone))
            conn.commit()
        except sqlite3.Error as db_error:
            print(f"Database Error: {db_error}")
        except Exception as general_error:
            print(f"Error saving job to database: {general_error}")
          
    async def add_zone_reminder(self, zone_name, channel_id=None, *, message):
        """
        Add a recurring reminder for a specific zone.

        Args:
            zone_name (str): The name of the zone to fetch.
            channel_id (int, optional): The ID of the Discord channel to send reminders to.
            message (str): The reminder message.
        """
        try:
            # Query zone info from the database
            cursor.execute("SELECT zone_id ,time, days FROM zone_times WHERE zone_name = ?", (zone_name,))
            zone_data = cursor.fetchone()
            
            if not zone_data:
                if channel_id:
                    await self.bot.get_channel(channel_id).send(f"'{zone_name}' not found!")
                return

            zone_id, time_str, days_str = zone_data
            hour, minute = map(int, time.strptime(time_str, '%I:%M %p')[3:5])  # Parse time
            days = days_str.split(", ")  # Split days into a list

            # Default to current channel if channel_id is not provided
            if channel_id is None:
                raise ValueError("Channel ID must be specified for reminders.")

            for day in days:
                day_index = ["mon", "tues", "wed", "thurs", "fri", "sat", "sun"].index(day.lower()[:3])
                cron_expression = f"{minute} {hour} * * {day_index}"
                job = scheduler.add_job(
                    self.send_reminder_with_timestamp,
                    CronTrigger(day_of_week=day_index, hour=hour, minute=minute, timezone="America/New_York"),
                    args=[channel_id, hour, minute, message],
                )
                # Save the job to the database
                await self.save_job_to_db(job.id, zone_id, channel_id, message, cron_expression)

            # Confirmation message
            channel = self.bot.get_channel(channel_id)
            if channel:
                await channel.send(
                    f"Recurring reminder set for Zone {zone_id} at {time_str} ({', '.join(days)})."
                )
            else:
                print(f"Invalid channel ID: {channel_id}")

        except Exception as e:
            print(f"Error in add_zone_reminder: {e}")
            if channel_id:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    await channel.send("An error occurred while adding the reminder. Please try again.")

    async def send_reminder_with_timestamp(self, channel_id, hour, minute, message):
        """
        Sends a reminder message with exact and relative timestamps.

        Args:
            channel_id (int): The ID of the Discord channel to send the reminder to.
            hour (int): The hour of the reminder.
            minute (int): The minute of the reminder.
            message (str): The reminder message.
        """
        channel = self.bot.get_channel(channel_id)
        if channel:
            now = datetime.now(ZoneInfo("America/New_York"))
            next_reminder = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_reminder < now:
                next_reminder += timedelta(days=7)  # Handle weekly recurring reminders

            unix_timestamp = int(next_reminder.timestamp())
            timestamp_text = f"<t:{unix_timestamp}:F>"  # Full timestamp
            relative_time_text = f"<t:{unix_timestamp}:R>"  # Relative time

            await channel.send(
                f"@everyone Reminder: {message}\nExact Time: {timestamp_text}\nRelative Time: {relative_time_text}"
            )
        else:
            print(f"Could not find channel with ID: {channel_id}")


# Scheduler start logic to be handled in bot lifecycle
def setup_scheduler():
    if not scheduler.running:
        scheduler.start()

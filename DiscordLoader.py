import discord
from discord import Embed

class DiscordLoader:
    def __init__(self, channel):
        """
        Initialize the DiscordLoader with a specific channel.
        :param channel: The Discord channel where updates will be sent.
        """
        self.channel = channel
        self.message = None  # Store the message object to edit later

    async def initialize_loader(self, task_description: str):
        """
        Send an initial loading embed message to Discord.
        :param task_description: The initial task description to display.
        """
        embed = Embed(title="Task Progress", description=task_description, color=discord.Color.blue())
        embed.add_field(name="Status", value="Initializing...", inline=False)

        # Send the initial embed message
        self.message = await self.channel.send(embed=embed)

    async def update_loader(self, update_text: str, progress_count: int, max_count: int):
        """
        Update the loader with progress.
        :param update_text: Description text for the current task progress.
        :param progress_count: Current progress count.
        :param max_count: Maximum count for the task.
        """
        progress_bar = self._generate_progress_bar(progress_count, max_count)
        embed = self.message.embeds[0]
        
        # Update the "Status" field
        embed.set_field_at(0, name="Status", value=update_text, inline=False)

        # Check if a "Progress" field exists, and update it if it does
        field_names = [field.name for field in embed.fields]
        if "Progress" in field_names:
            # Update the existing progress field
            index = field_names.index("Progress")
            embed.set_field_at(index, name="Progress", value=progress_bar, inline=False)
        else:
            # Add the progress field if it doesn't exist
            embed.add_field(name="Progress", value=progress_bar, inline=False)

        # Update the existing message
        await self.message.edit(embed=embed)

    async def finish_loader(self, completion_text: str):
        """
        Finalize the loader with a completion message.
        :param completion_text: The final completion message to display.
        """
        embed = self.message.embeds[0]
        embed.set_field_at(0, name="Status", value=completion_text, inline=False)
        embed.color = discord.Color.green()  # Change color to green to indicate completion

        # Final update to the message
        await self.message.edit(embed=embed)

    @staticmethod
    def _generate_progress_bar(progress_count: int, max_count: int, bar_length: int = 20) -> str:
        """
        Generate a text-based progress bar.
        :param progress_count: Current progress count.
        :param max_count: Maximum count for the task.
        :param bar_length: Length of the progress bar.
        :return: A string representing the progress bar.
        """
        percent_complete = progress_count / max_count
        filled_length = int(bar_length * percent_complete)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        return f"{bar} {progress_count}/{max_count} ({percent_complete:.0%})"

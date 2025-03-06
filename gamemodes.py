from collections import defaultdict
from typing import List, Dict
from discord.ext import commands
import discord
from discord import app_commands, Interaction
from database_setup import conn, cursor

class Gamemodes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  # Store bot instance


    #BattleWorlds *Been Changed so will need to rework this*    
    @app_commands.command(name="battleworld", description="Battleworld Test")
    async def battleworld(self, interaction: Interaction):
        # Define each room's requirements and required characters
        rooms_requirements = {
            1: {"requirement": "diamonds", "min_value": 3, "required_characters": ["CharacterS", "CharacterT", "CharacterU", "CharacterV", "CharacterW", "CharacterX"]},
            2: {"requirement": "gear_tier", "min_value": 12, "required_characters": ["CharacterA", "CharacterB", "CharacterC", "CharacterD", "CharacterE", "CharacterF"]},
            3: {"requirement": "stars_red", "min_value": 5, "required_characters": ["CharacterG", "CharacterH", "CharacterI", "CharacterJ", "CharacterK", "CharacterL"]},
            # Add additional rooms as needed
        }

        # Define maximum characters per player and slots per room
        MAX_CHARACTERS_PER_PLAYER = 12
        MAX_SLOTS_PER_CHARACTER = 6  # Each character can have six players

        # Helper function to fetch player and character data
        def fetch_player_characters():
            conn.cursor.execute('''
                SELECT p.player_id, p.player_name, c.character_id, c.name, c.level, c.power, c.gear_tier, 
                    c.stars_red, c.normal_stars, c.diamonds 
                FROM players p
                JOIN characters c ON p.player_id = c.player_id
            ''')
            data = conn.cursor.fetchall()
            players = defaultdict(list)
            for row in data:
                player_id, player_name, character_id, name, level, power, gear_tier, stars_red, normal_stars, diamonds = row
                players[player_id].append({
                    "character_id": character_id,
                    "name": name,
                    "player_name": player_name,
                    "level": level,
                    "power": power,
                    "gear_tier": gear_tier,
                    "stars_red": stars_red,
                    "normal_stars": normal_stars,
                    "diamonds": diamonds
                })
            return players

        # Filter characters based on each room's requirement and required characters
        def filter_characters_for_room(room_id: int, characters: List[Dict]):
            requirement = rooms_requirements[room_id]
            required_characters = requirement["required_characters"]
            
            # Filter based on both requirement and required character names
            filtered = [
                char for char in characters 
                if char["name"] in required_characters and char[requirement["requirement"]] >= requirement["min_value"]
            ]
            return filtered

        # Sort rooms by difficulty (optional): for example, by the highest min_value requirement
        def prioritize_rooms():
            return sorted(rooms_requirements.keys(), key=lambda room_id: rooms_requirements[room_id]["min_value"], reverse=True)

        # Function to maximize room completion by assigning players to characters within rooms
        def assign_players_to_characters(players: Dict[int, List[Dict]]):
            selected_characters = defaultdict(list)
            room_assignments = defaultdict(lambda: defaultdict(list))  # Dictionary for each room's character slots

            # Prioritize rooms based on requirements
            prioritized_rooms = prioritize_rooms()
            
            for room_id in prioritized_rooms:
                # For each character in the room, ensure up to MAX_SLOTS_PER_CHARACTER players
                for player_id, characters in players.items():
                    # Limit each player to 12 characters in total across all rooms
                    if len(selected_characters[player_id]) >= MAX_CHARACTERS_PER_PLAYER:
                        continue
                    
                    # Filter eligible characters for this room
                    eligible_characters = filter_characters_for_room(room_id, characters)
                    
                    # Assign eligible characters to room-specific characters
                    for character in eligible_characters:
                        character_name = character["name"]
                        
                        # Check if the character in this room has remaining slots
                        if len(room_assignments[room_id][character_name]) < MAX_SLOTS_PER_CHARACTER:
                            room_assignments[room_id][character_name].append(character["player_name"])
                            selected_characters[player_id].append(character)
                        
                        # Stop if the player has used up all slots
                        if len(selected_characters[player_id]) >= MAX_CHARACTERS_PER_PLAYER:
                            break

            return room_assignments

        # Load player and character data from the database
        players_data = fetch_player_characters()

        # Sort and optimize the roster allocations
        room_assignments = assign_players_to_characters(players_data)

        # Format the sorted roster assignments for display
        message_lines = []
        for room_id, characters in room_assignments.items():
            room_info = rooms_requirements[room_id]
            message_lines.append(
                f"**Room {room_id}** (Requirement: {room_info['requirement']} >= {room_info['min_value']}, "
                f"Required Characters: {', '.join(room_info['required_characters'])}):"
            )
            for character_name, assigned_players in characters.items():
                message_lines.append(f"- {character_name}: {', '.join(assigned_players)}")
        
        # Send the roster assignment as a response
        if message_lines:
            await interaction.response.send_message("\n".join(message_lines))
        else:
            await interaction.response.send_message("No players meet the requirements for the Battleworld rooms.")
    
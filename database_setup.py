# database_setup.py

import sqlite3
import json
from config import DB_NAME

class db_setup():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    def initialize_db():
        db_setup.cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                player_discord_id TEXT,
                player_game_id TEXT
            )
        ''')
        db_setup.cursor.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                character_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER,
                name TEXT,
                level INTEGER,
                power INTEGER,
                gear_tier INTEGER,
                iso_class TEXT,
                abilities TEXT,
                stars_red INTEGER,
                normal_stars INTEGER,
                diamonds INTEGER,
                FOREIGN KEY (player_id) REFERENCES players (player_id) ON DELETE CASCADE
            )
        ''')
        db_setup.conn.commit()

    # Helper function to add a character to the database
    def add_character(player_id, character_data):
        abilities_json = json.dumps(character_data["Abilities"])
        db_setup.cursor.execute('''
            INSERT INTO characters (player_id, name, level, power, gear_tier, iso_class, abilities, stars_red, normal_stars, diamonds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            player_id,
            character_data["Name"],
            character_data["Level"],
            character_data["Power"],
            character_data["Gear Tier"],
            character_data["ISO Class"],
            abilities_json,
            character_data["Stars (Red)"],
            character_data["Normal Stars"],
            character_data["Diamonds"]
        ))
        db_setup.conn.commit()
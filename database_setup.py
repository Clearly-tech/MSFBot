# database_setup.py

import sqlite3
from config import DB_NAME

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

def initialize_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            player_discord_id TEXT,
            player_game_id TEXT,
            alliance_id INTEGER,
            FOREIGN KEY (alliance_id) REFERENCES alliance (alliance_id) ON DELETE CASCADE
        )
    ''')# add total power, add strongest team, participation rating(war), participation rating(Raids)
    cursor.execute('''
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alliance (
            alliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            name TEXT,
            level INTEGER,
            power INTEGER,
            num_players TEXT,
            zone_id INTEGER,
            
            FOREIGN KEY (zone_id) REFERENCES zone_times (zone_id) ON DELETE CASCADE
        )
    ''')#add War league, war rank, Raid rank, Average power
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alliance_discord_settings (
            alliance_discord_settings_id INTEGER PRIMARY KEY AUTOINCREMENT,
            War_channel INTEGER,
            bot_controls_channel_alliance INTEGER,
            bot_controls_channel_members INTEGER,
            alliance_id TEXT,

            FOREIGN KEY (alliance_id) REFERENCES alliance (alliance_id) ON DELETE CASCADE 
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alliance_war_enemy (
            alliance_war_id INTEGER PRIMARY KEY AUTOINCREMENT,
            alliance_name TEXT,
            alliance_url TEXT,
            alliance_description TEXT,
            alliance_level INTEGER,
            alliance_total_power INTEGER,
            alliance_average_power INTEGER,
            alliance_total_players INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS member_war_enemy (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            player_discord_id TEXT,
            player_game_id TEXT,
            alliance_war_id INTEGER,
            
            FOREIGN KEY (alliance_war_id) REFERENCES alliance_war_enemy (alliance_war_idance_id) ON DELETE CASCADE
        )
    ''')
    # Add a table for storing scheduled jobs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scheduled_jobs (
            job_id TEXT PRIMARY KEY,
            zone_id INTEGER,
            channel_id INTEGER,
            message TEXT,
            cron_expression TEXT,  -- Store CronTrigger details
            timezone TEXT,
            FOREIGN KEY (zone_id) REFERENCES zone_times (zone_id) ON DELETE CASCADE
        )
    ''')
     # Zone times table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zone_times (
            zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_name TEXT NOT NULL,
            time TEXT NOT NULL,
            days TEXT NOT NULL
        )
    ''')
    conn.commit()
    # Example zone times
    cursor.executemany('''
        INSERT OR IGNORE INTO zone_times (zone_id, zone_name, time, days)
        VALUES (?, ?, ?, ?)
    ''', [
        (1, 'ZONE 1', '8:00 PM', 'Mon, Wed, Fri'),
        (2, 'ZONE 2', '3:00 AM', 'Mon, Wed, Fri'),
        (3, 'ZONE 3', '8:00 AM', 'Tues, Thurs, Sat'),
        (4, 'ZONE 4', '3:00 PM', 'Tues, Thurs, Sat')
    ])
    conn.commit()
import requests
import pickle
import json
from selenium_setup import SeleniumSetup as selenium_setup
from bs4 import BeautifulSoup
from database_setup import db_setup
import time
'''
    Testing new way of grabbing data thats scalable
'''
class getdata():

    #Loading cookies for requests
    def load_cookies_for_requests(file_path="msf_cookies.pkl"):
        # Load cookies from the pickle file and format them for requests
        with open(file_path, "rb") as file:
            cookies = pickle.load(file)
        return {cookie['name']: cookie['value'] for cookie in cookies}

    # Function to add player's roster to the database
    def add_player_roster(player_id, player_game_id, is_self):
        url = f'https://marvelstrikeforce.com/en/player/{player_game_id}/characters' if is_self else f'https://marvelstrikeforce.com/en/member/{player_game_id}/characters'
        selenium_setup.driver.get(url)
        
        for cookie in selenium_setup.driver.get_cookies():
            selenium_setup.driver.add_cookie(cookie)
        selenium_setup.driver.refresh()
        time.sleep(5)

        page_source = selenium_setup.driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        character_blocks = soup.find_all('li', class_='character')

        for char_block in character_blocks:
            character_data = parse_character_block(char_block)
            db_setup.add_character(player_id, character_data)

        # Function to parse character block HTML
        def parse_character_block(char_block):
            name_tag = char_block.find('h4')
            name = name_tag.text.strip() if name_tag else "Unknown"

            toon_stats = char_block.find('div', id='toon-stats')
            level = int(toon_stats.find('div', style=lambda x: x and 'font-size: 12px;' in x).text.strip().replace("LVL", "")) if toon_stats else 0
            power = int(toon_stats.find('div', style=lambda x: x and 'font-size: 18px;' in x).text.strip().replace(",", "")) if toon_stats else 0

            gear_tier = 0
            gear_tier_ring = char_block.find('div', class_='gear-tier-ring')
            if gear_tier_ring:
                svg_tag = gear_tier_ring.find('svg')
                if svg_tag and 'class' in svg_tag.attrs:
                    gear_tier_class = svg_tag['class'][0]
                    if gear_tier_class.startswith("g"):
                        gear_tier = int(gear_tier_class[1:])

            iso_class = "Unknown"
            iso_wrapper = char_block.find('div', class_='iso-wrapper')
            if iso_wrapper:
                traits = ['restoration', 'assassin', 'skirmish', 'fortify', 'gambler']
                tiers = ['purple', 'blue', 'green']
                for trait in traits:
                    for tier in tiers:
                        class_name = f'iso-{trait}-{tier}'
                        if iso_wrapper.find('div', class_=class_name):
                            iso_class = class_name
                            break
                    if iso_class != "Unknown":
                        break

            ability_levels = []
            ability_wrapper = char_block.find('div', class_='ability-level-wrapper')
            if ability_wrapper:
                for ability_div in ability_wrapper.find_all('div', class_='ability-level'):
                    level_text = ability_div.get('title') or ability_div['class'][-1]
                    ability_levels.append(level_text)

            diamonds = 0
            red_star_count = 0
            normal_star_count = 0
            diamonds_container = char_block.find('div', class_='diamonds-container')
            if diamonds_container:
                diamonds = len(diamonds_container.find_all('div', class_='equipped-diamond diamond-filled'))
                red_star_count = diamonds if diamonds <= 3 else 7
                normal_star_count = diamonds if diamonds <= 3 else 7

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

    #New Get methods https://api-prod.marvelstrikeforce.com/services/alliance/getAllianceRosters
    def getAllianceInfo():
        # Define the API endpoint
        api_url = 'https://api-prod.marvelstrikeforce.com/services/alliance/getAllianceRosters'
        
        # Load cookies for the request
        cookies = getdata.load_cookies_for_requests()
        
        # Send a GET request to the API with cookies
        response = requests.get(api_url, cookies=cookies)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response into a dictionary
            data = response.json()
            
            # Save the JSON data to a file
            with open('data.json', 'w') as json_file:
                json.dump(data, json_file, indent=4)
            
            print("JSON data saved to data.json")
            return data
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return
        
    #https://api-prod.marvelstrikeforce.com/services/alliance/getPlayerAllianceMembers
    def getAllainceMembers():
            # Define the API endpoint
        api_url = 'https://api-prod.marvelstrikeforce.com/services/alliance/getPlayerAllianceMembers'
        
        # Load cookies for the request
        cookies = getdata.load_cookies_for_requests()
        
        # Send a GET request to the API with cookies
        response = requests.get(api_url, cookies=cookies)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response into a dictionary
            data = response.json()
            
            # Save the JSON data to a file
            with open('data.json', 'w') as json_file:
                json.dump(data, json_file, indent=4)
            
            print("JSON data saved to data.json")
            return data
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            return
# selenium_setup.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pickle
import time
from config import MSF_URL

def setup_driver():
    chrome_options = Options()
    driver = webdriver.Chrome(options=chrome_options)
    return driver

driver = setup_driver()

def save_cookies(driver):
    driver.get(MSF_URL)
    input("Log in manually and press Enter when done...")
    cookies = driver.get_cookies()
    pickle.dump(cookies, open("msf_cookies.pkl", "wb"))

def load_cookies():
    
    try:
        save_cookies(driver)
        return pickle.load(open("msf_cookies.pkl", "rb"))
    except FileNotFoundError:
        print("No cookies file found. Please log in manually.")
        save_cookies(driver)
        return pickle.load(open("msf_cookies.pkl", "rb"))

cookies = load_cookies()

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pickle
from config import MSF_URL

class SeleniumSetup:

    @staticmethod
    def setup_driver():
        """
        Set up the Selenium WebDriver with desired options.
        Returns a driver object for interacting with the browser.
        """
        chrome_options = Options()
        #chrome_options.add_argument("--headless")  # Running headless mode (can be commented if you want to see the browser)
        driver = webdriver.Chrome(options=chrome_options)
        return driver

    @staticmethod
    def save_cookies(driver):
        """
        Manually log in to the website and save cookies for future use.
        """
        driver.get(MSF_URL)
        input("Log in manually and press Enter when done...")  # Wait for manual login
        cookies = driver.get_cookies()
        
        # Save cookies to a file
        with open("msf_cookies.pkl", "wb") as file:
            pickle.dump(cookies, file)
        print("Cookies saved to msf_cookies.pkl")
        return cookies

    @staticmethod
    def load_cookies(driver, cookies_file="msf_cookies.pkl"):
        """
        Load saved cookies into the browser session.
        If the cookies file doesn't exist, print a message and do not load anything.
        """
        # This method will be removed if you want to always force manual login
        try:
            with open(cookies_file, "rb") as file:
                cookies = pickle.load(file)
            
            # Add each cookie to the current browser session
            for cookie in cookies:
                driver.add_cookie(cookie)
            print("Cookies loaded successfully.")
        except FileNotFoundError:
            print(f"No cookies found at {cookies_file}, please log in manually.")
        except Exception as e:
            print(f"An error occurred while loading cookies: {e}")
    # Step to start the Selenium WebDriver and force manual login
    driver = SeleniumSetup.setup_driver()
    driver.get(MSF_URL)
    cookies = SeleniumSetup.save_cookies(driver)  # Force manual login and save cookies
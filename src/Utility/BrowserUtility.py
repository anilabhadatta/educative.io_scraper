import os

from selenium import webdriver

from src.Common.Constants import constants


class BrowserUtility:
    def __init__(self, configJson):
        self.browser = None
        self.configJson = configJson


    def loadBrowser(self):
        userDataDir = os.path.join(
            constants.OS_ROOT, self.configJson["userDataDir"])
        options = webdriver.ChromeOptions()
        if self.configJson["headless"]:
            options.add_argument('headless')
        options.add_argument(f'user-data-dir={userDataDir}')
        options.add_argument('--profile-directory=Default')
        options.add_argument("--start-maximized")
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-web-security")
        options.add_argument('--allow-running-insecure-content')
        options.add_argument("--disable-site-isolation-trials")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument('--log-level=3')
        userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.56 Safari/537.36"
        options.add_argument(f'user-agent={userAgent}')
        options.binary_location = constants.chromeBinaryPath
        self.browser = webdriver.Remote(
            command_executor='http://127.0.0.1:9515', options=options)
        self.browser.set_window_size(1920, 1080)
        self.browser.command_executor._commands["send_command"] = (
            "POST", '/session/$sessionId/chromium/send_command')
        print("Driver Loaded")
        return self.browser

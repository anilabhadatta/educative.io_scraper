import time

from src.Utility.BrowserUtility import BrowserUtility


class LoginAccount:
    def __init__(self, configJson):
        self.configJson = configJson
        self.browserUtil = BrowserUtility(configJson)
        self.browser = None


    def start(self):
        try:
            self.browser = self.browserUtil.loadBrowser()
            self.browser.get("https://educative.io/login")
            # input("Press Enter to exit after login is over...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("Keyboard Interrupt occurred. Exiting...")
        except Exception as e:
            print("Error occurred while starting scraper: ", e)
        self.browser.quit()
        print("Exiting...")

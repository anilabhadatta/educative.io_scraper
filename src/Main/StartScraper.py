import time

from src.Utility.BrowserUtility import BrowserUtility


class StartScraper:
    def __init__(self, configJson):
        self.configJson = configJson
        self.browserUtil = BrowserUtility(configJson)
        self.browser = None


    def start(self):
        try:
            i = 0
            while True:
                print("Starting scraper...", i)
                i += 1
                time.sleep(1)
        except KeyboardInterrupt:
            print("Keyboard Interrupt occurred. Exiting...")
        except Exception:
            pass
        finally:
            print("Terminated")

import asyncio

from src.Utility.BrowserUtility import BrowserUtility


class StartScraper:
    def __init__(self, configJson):
        self.configJson = configJson
        self.browserUtil = BrowserUtility(configJson)
        self.browser = None
        self.stop_event = asyncio.Event()


    async def start(self):
        # Your asynchronous scraping code here
        while not self.stop_event.is_set():
            try:
                self.browser = self.browserUtil.loadBrowser()
                self.browser.get("https://www.google.com")
                input("Press Enter to exit...")
                self.browser.quit()
            except Exception as e:
                print("Error occurred while starting scraper: ", e)


    def stop(self):
        self.stop_event.set()  # Signal the scraper to stop

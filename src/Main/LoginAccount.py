import time

from src.Logging.Logger import Logger
from src.Utility.BrowserUtility import BrowserUtility


class LoginAccount:
    def __init__(self):
        self.browserUtil = None
        self.logger = None
        self.configJson = None
        self.browser = None


    def start(self, configJson):
        self.configJson = configJson
        self.browserUtil = BrowserUtility(self.configJson)
        self.logger = Logger(self.configJson, "LoginAccount").logger
        self.logger.debug("""   LoginAccount initiated...
                                Login your account in the browser...
                                To Terminate, Click on Logout Button
                         """)
        try:
            self.browser = self.browserUtil.loadBrowser()
            self.browser.get("https://educative.io/login")
            time.sleep(20)
            i = 0
            while True:
                time.sleep(1)
                i += 1
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            self.logger.error(e)
        finally:
            self.logger.debug("Exiting...")
            self.browser.quit()

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
        self.configJson['headless'] = False
        self.browserUtil = BrowserUtility(self.configJson)
        self.logger = Logger(self.configJson, "LoginAccount").logger
        self.logger.info("""LoginAccount initiated...
                            Login your account in the browser...
                            To Terminate, Click on Logout Button
                         """)
        try:
            self.browser = self.browserUtil.loadBrowser()
            self.browser.get("https://educative.io/login")
            while True:
                pass
        except KeyboardInterrupt:
            self.logger.error("Keyboard Interrupt")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            self.logger.error(f"start: {lineNumber}: {e}")
        finally:
            self.logger.debug("Exiting...")
            if self.browser is not None:
                self.browser.quit()


    def checkIfLoggedIn(self, browser):
        isLoggedIn = bool(browser.execute_script(
            '''return document.cookie.includes('logged_in')'''))
        if not isLoggedIn:
            raise Exception("Login to your account in the browser...")

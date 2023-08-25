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
            # self.browser.find_element(By.CSS_SELECTOR, "hello").click()
            time.sleep(20)
        except KeyboardInterrupt:
            self.saveUrlLog()
            print("Keyboard Interrupt occurred. Exiting...")
        except Exception as e:
            print("Error occurred while starting scraper: ", e)
            # self.saveUrlLog()
        finally:
            print("Terminated")
            self.browser.quit()
        print("Exiting...")


    def saveUrlLog(self):
        current_url = self.browser.current_url
        print(current_url)
        with open("url_log.txt", "a") as log_file:
            log_file.write(current_url + "\n")

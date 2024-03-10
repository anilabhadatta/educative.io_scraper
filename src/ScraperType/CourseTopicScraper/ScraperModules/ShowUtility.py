import os

from src.Logging.Logger import Logger
from src.Utility.BrowserUtility import BrowserUtility
from src.Utility.FileUtility import FileUtility
from src.Utility.OSUtility import OSUtility


class ShowUtility:
    def __init__(self, configJson):
        self.browser = None
        self.fileUtils = FileUtility()
        self.browserUtils = BrowserUtility(configJson)
        self.osUtils = OSUtility(configJson)
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["ShowUtility"]
        self.logger = Logger(configJson, "ShowUtility").logger


    def showSingleMarkDownQuizSolution(self):
        try:
            self.logger.info("Showing single markdown quiz solution")
            showMarkDownQuizSolutionSelector = self.selectors["showMarkDownQuizSolution"]
            showMarkDownQuizJsScript = f"""
            var divs = document.querySelectorAll('div');
            var count = 0;
            divs.forEach(div => {{
              if (div.textContent.trim() === "{showMarkDownQuizSolutionSelector}") {{
                  div.click();
                  count++;
              }}}});
            return count;
            """
            isPresent = self.browser.execute_script(showMarkDownQuizJsScript)
            if isPresent <= 0:
                self.logger.info("No single markdown quiz solution found")
            else:
                self.osUtils.sleep(2)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ShowUtility:showSingleMarkDownQuizSolution: {lineNumber}: {e}")


    def showCodeSolutions(self):
        try:
            self.logger.info("Showing code solutions")
            showCodeSolutionSelector = self.selectors["showCodeSolution"]
            confirmButtonSelector = self.selectors["confirmShowSolution"]
            showCodeSolutionJsScript = f"""
            async function clickForceShow() {{
              await new Promise(resolve => setTimeout(resolve, 2000));
              document.querySelector("{confirmButtonSelector}")?.click();
            }}
            var buttons = document.querySelectorAll('button');
            var count = 0;
            buttons.forEach(button => {{
              if (button.textContent.trim().includes("{showCodeSolutionSelector}") && button.disabled === false) {{
                  button.click();
                  clickForceShow();
                  button.disabled = true;
                  count++;
            }}}});
            return count;
            """
            isPresent = self.browser.execute_script(showCodeSolutionJsScript)
            if isPresent <= 0:
                self.logger.info("No code solution found")
            else:
                self.osUtils.sleep(2)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ShowUtility:showCodeSolutions: {lineNumber}: {e}")


    def showHints(self):
        try:
            self.logger.info("Showing hints")
            showHintSelector = self.selectors["showHints"]
            showHintJsScript = f"""
            var gs = document.querySelectorAll("{showHintSelector}");
            var count = 0;
            gs.forEach(g => {{
                var button = g.closest('svg').parentNode;
                if(button.disabled === false) {{
                  button.click();
                  button.disabled = true;
                  count++;
            }}}});
            return count;
            """
            isPresent = self.browser.execute_script(showHintJsScript)
            if isPresent <= 0:
                self.logger.info("No hints found")
            else:
                self.osUtils.sleep(2)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ShowUtility:showHints: {lineNumber}: {e}")


    def showSlides(self):
        try:
            self.logger.info("Showing slides")
            showSlideSelector = self.selectors["showSlides"]
            showSlideJsScript = f"""
            var svgs = document.querySelectorAll("{showSlideSelector}");
            var count = 0;
            svgs.forEach(svg => {{
                var button = svg.parentNode;
                if(button.disabled === false) {{
                  button.click();
                  button.disabled = true;
                  count++;
            }}}});
            return count;
            """
            isPresent = self.browser.execute_script(showSlideJsScript)
            if isPresent <= 0:
                self.logger.info("No slides found")
            else:
                self.browserUtils.browser = self.browser
                self.browserUtils.scrollPage()
                self.osUtils.sleep(10)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ShowUtility:showSlides: {lineNumber}: {e}")

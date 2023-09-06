import os

from src.Utility.FileUtility import FileUtility


class ShowUtility:
    def __init__(self):
        self.browser = None
        self.fileUtils = FileUtility()
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["ShowUtility"]


    def showSingleMarkDownQuizSolution(self):
        try:
            showMarkDownQuizSolutionSelector = self.selectors["showMarkDownQuizSolution"]
            showMarkDownQuizJsScript = f"""
            var divs = document.querySelectorAll('div');
            divs.forEach(div => {{
              if (div.textContent.trim() === "{showMarkDownQuizSolutionSelector}") {{
                  div.click();
              }}}});
            """
            self.browser.execute_script(showMarkDownQuizJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ShowUtility:showSingleMarkDownQuizSolution: {lineNumber}: {e}")


    def showCodeSolutions(self):
        try:
            showCodeSolutionSelector = self.selectors["showCodeSolution"]
            confirmButtonSelector = self.selectors["confirmShowSolution"]
            showCodeSolutionJsScript = f"""
            var buttons = document.querySelectorAll('button');
            buttons.forEach(button => {{
              if (button.textContent.trim() === "{showCodeSolutionSelector}" && button.disabled === false) {{
                  button.click();
                  document.querySelector("{confirmButtonSelector}").click();
                  button.disabled = true;
            }}}});
            """
            self.browser.execute_script(showCodeSolutionJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ShowUtility:showCodeSolutions: {lineNumber}: {e}")


    def showHints(self):
        try:
            showHintSelector = self.selectors["showHints"]
            showHintJsScript = f"""
            var gs = document.querySelectorAll("{showHintSelector}");
            gs.forEach(g => {{
                var button = g.closest('svg').parentNode;
                if(button.disabled === false) {{
                  button.click();
                  button.disabled = true;
            }}}});
            """
            self.browser.execute_script(showHintJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ShowUtility:showHints: {lineNumber}: {e}")


    def showSlides(self):
        try:
            showSlideSelector = self.selectors["showSlides"]
            showSlideJsScript = f"""
            var svgs = document.querySelectorAll("{showSlideSelector}");
            svgs.forEach(svg => {{
                var button = svg.parentNode;
                if(button.disabled === false) {{
                  button.click();
                  button.disabled = true;
            }}}});
            """
            self.browser.execute_script(showSlideJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"ShowUtility:showSlides: {lineNumber}: {e}")

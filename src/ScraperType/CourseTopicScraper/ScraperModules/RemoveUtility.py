import os

from src.Logging.Logger import Logger
from src.Utility.FileUtility import FileUtility


class RemoveUtility:
    def __init__(self, configJson):
        self.browser = None
        self.fileUtils = FileUtility()
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["RemoveUtility"]
        self.logger = Logger(configJson, "RemoveUtility").logger


    def removeBlurWithCSS(self):
        self.logger.info("Removing blur with CSS")
        removeBlurJsScript = """
        const head = document.querySelector('head');
        const style = document.createElement('style');
        style.type = 'text/css';
        const css = '* { filter: none !important; }';
        style.appendChild(document.createTextNode(css));
        head.appendChild(style);
        """
        return self.browser.execute_script(removeBlurJsScript)


    def removeMarkAsCompleted(self):
        try:
            self.logger.info("Removing mark-as-completed/completed tick mark")
            articleFooterSelector = self.selectors["articleFooter"]
            markAsCompletedSelector = self.selectors["markAsCompleted"]
            completedSelector = self.selectors["completed"]
            removeMarkAsCompletedJsScript = f"""
            try{{
                var articleFooter = document.evaluate("{articleFooterSelector}", document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                articleFooter = articleFooter.snapshotItem(0);
                var markAsCompleted = document.evaluate("{markAsCompletedSelector}", articleFooter, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                var completed = document.evaluate("{completedSelector}", articleFooter, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                
                if (markAsCompleted.snapshotLength > 0 || completed.snapshotLength > 0) {{    
                    if(markAsCompleted.snapshotLength > 0) {{
                        markAsCompleted.snapshotItem(0).parentNode.click();
                    }}
                    if (completed.snapshotLength > 0) {{
                        completed.snapshotItem(0).parentNode.click();
                    }}
                }}
            }} catch (e) {{
                console.log(e);
            }}
            """
            self.browser.execute_script(removeMarkAsCompletedJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"RemoveUtility:removeMarkAsCompleted: {lineNumber}: {e}")


    def removeUnwantedElements(self):
        try:
            self.logger.info("Removing unwanted elements")
            nodesToDelete = [self.selectors["navNode"], self.selectors["privacyNode"], self.selectors["streakNode"],
                             self.selectors["askQuestionDarkModeToolbar"], self.selectors["sidebar"]]
            selectors = ", ".join([f'{node}' for node in nodesToDelete])
            removeTagsJsScript = f"""
            var elements = document.querySelectorAll("{selectors}");
            elements.forEach(element => {{
                if (element.tagName === "STYLE" || element.tagName === "DIV" && element.id === "__next") {{
                    // do nothing
                }} else {{
                element.parentNode.removeChild(element);
                }}
            }});
            """
            self.browser.execute_script(removeTagsJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"RemoveUtility:removeUnwantedElements: {lineNumber}: {e}")

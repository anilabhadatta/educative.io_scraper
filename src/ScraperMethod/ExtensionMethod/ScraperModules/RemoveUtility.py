import os

from src.Utility.FileUtility import FileUtility


class RemoveUtility:
    def __init__(self):
        self.browser = None
        self.fileUtils = FileUtility()
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["RemoveUtility"]


    def removeBlurWithCSS(self):
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
            articleFooterSelector = self.selectors["articleFooter"]
            markAsCompletedSelector = self.selectors["markAsCompleted"]
            completedSelector = self.selectors["completed"]
            removeMarkAsCompletedJsScript = f"""
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
            """
            self.browser.execute_script(removeMarkAsCompletedJsScript)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"RemoveUtility:removeMarkAsCompleted: {lineNumber}: {e}")


    def removeTags(self):
        pass

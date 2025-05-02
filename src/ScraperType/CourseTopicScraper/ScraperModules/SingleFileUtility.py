import os

from src.Common.Constants import constants
from src.ScraperType.CourseTopicScraper.ScraperModules.SeleniumBasicUtility import SeleniumBasicUtility
from src.Utility.OSUtility import OSUtility
from src.Logging.Logger import Logger
from src.ScraperType.CourseTopicScraper.ScraperModules.ScreenshotUtility import ScreenshotUtility
from src.Utility.FileUtility import FileUtility


class SingleFileUtility:
    def __init__(self, configJson):
        self.browser = None
        self.osUtils = OSUtility(configJson)
        self.fileUtils = FileUtility()
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["SingleFileUtility"]
        self.logger = Logger(configJson, "SingleFileUtility").logger
        self.screenshotHtmlUtils = ScreenshotUtility(configJson)
        self.seleniumBasicUtils = SeleniumBasicUtility(configJson)


    def fixAllObjectTags(self):
        try:
            self.logger.info("Fixing all object tags")
            objectTagSelector = self.selectors["objectTag"]
            fixObjectTagsJsScript = f"""
            var objectTags = document.querySelectorAll("{objectTagSelector}");
            objectTags.forEach(objectTag => {{
                try{{
                    svgElement = objectTag.contentDocument.documentElement;
                    objectStyle = objectTag.getAttribute("style");
                    clsName = objectTag.className;
                    classNamesArray = clsName.split(' ');
                    classNamesArray.forEach(function(className) {{
                      svgElement.classList.add(className);
                    }});
                    parentTag = objectTag.parentNode;
                    parentTag.append(svgElement);
                    svgElement.classList.add(clsName);
                    svgElement.style.cssText = objectStyle;
                }}
                catch(error){{
                    console.log(error);
                }}
            }});           
            return objectTags.length;
            """
            isPresent = self.browser.execute_script(fixObjectTagsJsScript)
            if isPresent <= 0:
                self.logger.info("No object tag found")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SingleFileUtility:fixAllObjectTags: {lineNumber}: {e}")


    def injectSingleFileScripts(self):
        try:
            self.logger.info("Injecting SingleFile scripts")
            injectSingleFileJsScript = """
            function injectScriptToHTML(scriptTag, doc = document) {
                var targetElement = doc.body || doc.documentElement;
                targetElement.appendChild(scriptTag.cloneNode(true));
                var frames = doc.querySelectorAll("frame, iframe");
                frames.forEach(frame => {
                    var frameDocument = frame.contentDocument || frame.contentWindow.document;
                    if (frameDocument) {
                        injectScriptToHTML(scriptTag, frameDocument);
                    }
                });
            }
                             
            function createScriptTagFromLocal(data) {
                    var scriptElement = document.createElement('script');
                    scriptElement.type = 'text/javascript';
                    scriptElement.textContent = data;
                    return scriptElement;
                }
                
            window.__define = window.define;
            window.__require = window.require;
            window.define = undefined;
            window.require = undefined;
        
            injectScriptToHTML(createScriptTagFromLocal(arguments[0]));
            injectScriptToHTML(createScriptTagFromLocal(arguments[1]));
            """
            singleFileJs = self.fileUtils.loadSingleFileFile(constants.singleFileBundlePath)
            initSingleFilePath = self.fileUtils.loadSingleFileFile(constants.initSingleFilePath)
            script = self.browser.execute_script(f"{singleFileJs} return script;")
            hookScript = self.browser.execute_script(f"{singleFileJs} return hookScript;")
            script += initSingleFilePath
            self.browser.execute_script(injectSingleFileJsScript, hookScript, script)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SingleFileUtility:injectSingleFileScripts: {lineNumber}: {e}")


    def makeCodeSelectable(self):
        try:
            self.logger.info("Making code selectable")
            codeContainerClassName = self.selectors["codeContainerClass"]
            makeCodeSelectableJsScript = f"""
            var codes = document.getElementsByClassName("{codeContainerClassName}");
            for(let i=0;i<codes.length;i++) {{
                if(codes[i].classList.contains('no-user-select')) {{
                    codes[i].classList.remove('no-user-select');
                }} 
            }}
            return codes.length;
            """
            isPresent = self.browser.execute_script(makeCodeSelectableJsScript)
            if isPresent <= 0:
                self.logger.info("No code found")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SingleFileUtility:makeCodeSelectable: {lineNumber}: {e}")


    def getSingleFileHtml(self):
        htmlPageData = None
        singleFileJsScript = """singlefile.getPageData({
            removeImports: true,
            removeScripts: true,
            removeAudioSrc: true,
            removeVideoSrc: true,
            removeHiddenElements: true,
            removeUnusedStyles: true,
            removeUnusedFonts: true,
            compressHTML: true,
            blockVideos: true,
            blockScripts: true,
            networkTimeout: 60000
        });"""
        param = {
            "expression": singleFileJsScript,
            "awaitPromise": True,
            "returnByValue": True
        }
        try:
            try:
                self.logger.info("getSingleFileHtml: Getting SingleFile Html...")
                htmlPageData = self.browser.execute_cdp_cmd("Runtime.evaluate", param)["result"]["value"]["content"]
            except Exception as e1:
                try:
                    self.logger.error(f"getSingleFileHtml: Failed to get SingleFile Html, retrying...")
                    htmlPageData = self.browser.execute_cdp_cmd("Runtime.evaluate", param)["result"]["value"]["content"]
                    self.logger.info("getSingleFileHtml: Successfully Received Page using SingleFile...")
                except Exception as e2:
                    self.logger.error(f"getSingleFileHtml: Failed to get SingleFile Html, Creating Full Page Screenshot HTML...")
            return htmlPageData
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SingleFileUtility:getSingleFileHtml: {lineNumber}: {e}")
        

    def injectSingleFileViaCDP(self):
        try:
            self.logger.info("Injecting SingleFile via CDP")
            self.seleniumBasicUtils.browser = self.browser
            singleFileJs = self.fileUtils.loadSingleFileFile(constants.singleFileBundlePath)
            initSingleFilePath = self.fileUtils.loadSingleFileFile(constants.initSingleFilePath)
            script = self.browser.execute_script(f"{singleFileJs} return script;")
            hookScript = self.browser.execute_script(f"{singleFileJs} return hookScript;")

            params1 = {"enabled": True}
            params2 = {"ignore": True}
            params3 = {
                "source": hookScript,
                "runImmediately": True
            }
            script += initSingleFilePath
            params4 = {
                "source": script,
                "runImmediately": True
            }
            params5 = {
                "source": singleFileJs,
                "runImmediately": True
            }
            self.browser.execute_cdp_cmd('Page.enable', {})
            self.browser.execute_cdp_cmd("Page.setBypassCSP", params1)
            self.browser.execute_cdp_cmd("Security.setIgnoreCertificateErrors", params2)
            self.browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", params3)
            self.browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", params4)
            self.browser.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", params5)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SingleFileUtility:injectSingleFileViaCDP: {lineNumber}: {e}")

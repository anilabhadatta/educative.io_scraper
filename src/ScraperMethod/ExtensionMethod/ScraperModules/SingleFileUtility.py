import os
import time

from src.Logging.Logger import Logger
from src.ScraperMethod.ExtensionMethod.ScraperModules.ScreenshotHtmlUtility import ScreenshotHtmlUtility
from src.Utility.FileUtility import FileUtility


class SingleFileUtility:
    def __init__(self, configJson):
        self.browser = None
        self.fileUtils = FileUtility()
        selectorPath = os.path.join(os.path.dirname(__file__), "Selectors.json")
        self.selectors = self.fileUtils.loadJsonFile(selectorPath)["SingleFileUtility"]
        self.logger = Logger(configJson, "SingleFileUtility").logger
        self.screenshotHtmlUtils = ScreenshotHtmlUtility(configJson)


    def fixAllObjectTags(self):
        try:
            self.logger.info("Fixing all object tags")
            objectTagSelector = self.selectors["objectTag"]
            fixObjectTagsJsScript = f"""
            var objectTags = document.querySelectorAll("{objectTagSelector}");
            objectTags.forEach(objectTag => objectTag.type = "image/svg+xml");
            return objectTags.length;
            """
            isPresent = self.browser.execute_script(fixObjectTagsJsScript)
            if isPresent <= 0:
                self.logger.info("No object tag found")
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SingleFileUtility:fixAllObjectTags: {lineNumber}: {e}")


    def injectImportantScripts(self):
        try:
            self.logger.info("Injecting important scripts")
            injectImportantScriptsJsScript = """
            function injectScriptToHTML(scriptTag, location) {
                if (location === "iframe") {
                    var frames = document.querySelectorAll('frame, iframe, object');
                    frames.forEach(frame => {
                            var frameDocument = frame.contentDocument || frame.contentWindow.document;
                            var targetElement = frameDocument.head || frameDocument.body || frameDocument.documentElement;
                            targetElement.appendChild(scriptTag.cloneNode(true));
                    });
                }
                document.head.appendChild(scriptTag);
            }
                             
            function createScriptTagFromURL(url) {
                return fetch(url)
                    .then(response => response.text())
                    .then(data => {
                        var scriptElement = document.createElement('script');
                        scriptElement.type = 'text/javascript';
                        scriptElement.textContent = data;
                        return scriptElement;
                    })
                    .catch(error => {
                        console.error('Error loading script:', error);
                        return null;
                    });
            }
            
            var baseurl = 'https://anilabhadatta.github.io/SingleFile/';
            var urls = [
            'lib/single-file-bootstrap.js',
            'lib/single-file-hooks-frames.js',
            'lib/single-file-frames.js',
            'lib/single-file.js'
            ];
            var fullUrls = urls.map(url => baseurl + url);
            
            for(let i=0; i< fullUrls.length; i++){
                createScriptTagFromURL(fullUrls[i])
                    .then(scriptTag => {
                        if (scriptTag) {
                            if(i === 1 || i === 2){
                                injectScriptToHTML(scriptTag, "iframe") 
                            }
                            else {
                                injectScriptToHTML(scriptTag, "")
                            }
                        }
                    });
            }
            """
            self.browser.execute_script(injectImportantScriptsJsScript)
            time.sleep(5)
            self.browser.execute_script(injectImportantScriptsJsScript)
            time.sleep(10)
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SingleFileUtility:injectImportantScripts: {lineNumber}: {e}")


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


    def getSingleFileHtml(self, topicName):
        singleFileJsScript = """
        const { content, title, filename } = await singlefile.getPageData({
            removeHiddenElements: true,
            removeUnusedStyles: true,
            removeUnusedFonts: true,
            removeImports: true,
            blockScripts: true,
            blockAudios: true,
            blockVideos: true,
            compressHTML: true,
            removeAlternativeFonts: true,
            removeAlternativeMedias: true,
            removeAlternativeImages: true,
            groupDuplicateImages: true,
            insertMetaCSP: true,
            networkTimeout: 60000,
            shadowEnabled: true,
        });
        return content;
        """
        try:
            try:
                try:
                    self.logger.info("getSingleFileHtml: Getting SingleFile Html...")
                    htmlPageData = self.browser.execute_script(singleFileJsScript)
                except Exception as e:
                    self.logger.error(f"getSingleFileHtml: Failed to get SingleFile Html, retrying...{e}")
                    htmlPageData = self.browser.execute_script(singleFileJsScript)
                self.logger.info("getSingleFileHtml: Successfully Received Page using SingleFile...")
            except Exception as e:
                self.logger.error(f"getSingleFileHtml: Failed to get SingleFile Html, getting ScreenshotHtml...{e}")
                self.screenshotHtmlUtils.browser = self.browser
                htmlPageData = self.screenshotHtmlUtils.getFullPageScreenshotHtml(topicName)
                self.logger.info("getSingleFileHtml: Successfully Received Page using ScreenshotHtml...")
            return htmlPageData
        except Exception as e:
            lineNumber = e.__traceback__.tb_lineno
            raise Exception(f"SingleFileUtility:getSingleFileHtml: {lineNumber}: {e}")

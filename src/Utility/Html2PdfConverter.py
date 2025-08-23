from pypdf import PdfWriter, PdfReader, PageObject, Transformation
import io
import os
import base64
import time
import tempfile
import shutil
import re
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from seleniumbase import Driver
from src.Common.Constants import constants
import fitz

class PDFConverterConfig:
    """Configuration class for PDF converter settings"""
    
    def __init__(self, configJson):
        # Browser and Chrome paths
        self.configJson = configJson
        self.chrome_args = " --allow-running-insecure-content, --ignore-certificate-errors-spki-list,--ignore-ssl-errors"
        
        self.user_data_dir = os.path.join(constants.OS_ROOT, self.configJson["userDataDir"], f"ucDriver-{self.configJson['ucdriver']}")
        self.chrome_binary_path = constants.chromeBinaryPath
        self.chrome_driver_version = self.configJson['binaryversion']
        self.root_directory = self.configJson["saveDirectory"]
        # Don't set a fixed output_path - it will be determined per course
        self.output_path = None  # Will be set dynamically for each course

        # Processing settings
        self.max_browser_sessions = 30
        self.min_browser_sessions = 1
        self.page_load_timeout = 1
        self.pdf_generation_pause = 1
        
        # PDF settings
        self.pdf_scale = 0.8
        self.pdf_paper_width = 8.27
        self.min_paper_height = 8.5
        self.trim_whitespace = True
        self.smart_trimming = True  # Enable smart marker-based trimming
        self.fallback_trim_percentage = 0.15  # Fallback trim percentage
        
        # Folder exclusions
        self.excluded_folders = ['Codes_', 'Quiz', 'MarkDownQuiz']
    
    def get_optimal_browser_count(self, file_count):
        """Calculate optimal number of browsers based on file count"""
        optimal = min(file_count, self.max_browser_sessions)
        return max(optimal, self.min_browser_sessions)


class SmartTrimmingUtility:
    """Advanced PDF trimming utility with marker detection"""
    

    @staticmethod
    def extract_text_with_positions(pdf_bytes):
        """Extract text with positions from PDF to find trim marker"""

        try:
            pdf_document = fitz.open("pdf", pdf_bytes)
            page = pdf_document[0]  # First page
            
            # Search patterns in order of preference
            search_patterns = [
                "EDUCATIVE_TRIM_POINT_MARKER_HERE",
                "••TRIM••POINT••HERE••"
            ]
            
            for pattern in search_patterns:
                print(f"Searching for pattern: '{pattern}'")
                text_instances = page.search_for(pattern)
                
                if text_instances:
                    # Get the position of the marker
                    marker_rect = text_instances[0]
                    marker_y = marker_rect.y0  # Top of the marker
                    print(f"✅ Found trim marker '{pattern}' at Y position: {marker_y}")
                    return marker_y

            print("❌ No trim markers found in PDF")
            return None
                
        except Exception as e:
            print(f"Error extracting text positions: {e}")
            return None
        finally:
            if 'pdf_document' in locals():
                pdf_document.close()

    @staticmethod
    def trim_pdf_at_marker(pdf_bytes, marker_y_position=None):
        """Trim PDF content below the marker position"""
        if not marker_y_position:
            return pdf_bytes
            
        try:
            pdf_document = fitz.open("pdf", pdf_bytes)
            page = pdf_document[0]
            
            # Get current page dimensions
            page_rect = page.rect
            original_height = page_rect.height
            
            print(f"Original page height: {original_height}, Trim at: {marker_y_position}")
            
            # Create new rectangle that ends at marker position (with some padding)
            trim_padding = 20  # 20 points padding below marker
            new_height = marker_y_position + trim_padding
            
            if new_height < original_height:
                # Create new page with trimmed content
                new_rect = fitz.Rect(0, 0, page_rect.width, new_height)
                
                # Create new PDF with trimmed page
                new_pdf = fitz.open()
                new_page = new_pdf.new_page(width=page_rect.width, height=new_height)
                
                # Copy content from original page to new page within the crop area
                new_page.show_pdf_page(new_rect, pdf_document, 0, clip=new_rect)
                
                # Save trimmed PDF to bytes
                trimmed_bytes = new_pdf.tobytes()
                new_pdf.close()
                
                print(f"✂️ PDF trimmed from {original_height:.1f} to {new_height:.1f} points")
                return trimmed_bytes
            else:
                print("Marker position is beyond page height, no trimming needed")
                return pdf_bytes
                
        except Exception as e:
            print(f"Error trimming PDF: {e}")
            return pdf_bytes
        finally:
            if 'pdf_document' in locals():
                pdf_document.close()

    @staticmethod
    def fallback_trim_pdf(pdf_bytes, trim_percentage=0.15):
        """Fallback trimming method using pypdf when PyMuPDF is not available"""
        try:
            print(f"🔄 Applying fallback trim ({trim_percentage*100}% from bottom)")
            
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            outputPdf = PdfWriter()

            for page in pdf_reader.pages:
                # Get page dimensions
                media_box = page.mediabox
                page_width = float(media_box.width)
                page_height = float(media_box.height)
                
                 # Calculate how much to trim from bottom
                trim_amount = page_height * trim_percentage
                new_bottom = trim_amount  # Move bottom edge up by trim_amount
                
                # Update mediabox to remove bottom content
                # PDF coordinates: (0,0) is bottom-left, so we raise the bottom edge
                page.mediabox.lower_left = (0, new_bottom)
                page.mediabox.upper_right = (page_width, page_height)
                
                outputPdf.add_page(page)

            print(f"✂️ Trimmed {trim_percentage*100}% from bottom of PDF")

            output = io.BytesIO()
            outputPdf.write(output)
            return output.getvalue()
                
        except Exception as e:
            print(f"❌ Error in fallback trim: {e}")
            return pdf_bytes


class BrowserSessionManager:
    """Thread-safe browser session manager"""
    
    def __init__(self, config, browser_count=None):
        self.config = config
        self.browser_count = browser_count or config.max_browser_sessions
        self.browsers = queue.Queue(maxsize=self.browser_count)
        self.lock = threading.Lock()
        self._initialize_browsers()
    
    def _initialize_browsers(self):
        """Initialize browser sessions"""
        print(f"Initializing browser session pool ({self.browser_count} browsers)...")
        for i in range(self.browser_count):
            try:
                browser = Driver(
                    undetectable=True, 
                    user_data_dir=f"{self.config.user_data_dir}_{i}",
                    binary_location=self.config.chrome_binary_path, 
                    headless2=True,
                    proxy=None, 
                    chromium_arg=self.config.chrome_args,
                    headed=False, 
                    driver_version=self.config.chrome_driver_version
                )
                self.browsers.put(browser)
                print(f"  ✓ Browser session {i+1}/{self.browser_count} initialized")
            except Exception as e:
                print(f"  ✗ Failed to initialize browser session {i+1}: {e}")
        print(f"Browser pool ready with {self.browsers.qsize()} sessions\n")
    
    def get_browser(self):
        """Get a browser session"""
        return self.browsers.get()
    
    def return_browser(self, browser):
        """Return a browser session"""
        self.browsers.put(browser)
    
    def cleanup(self):
        """Cleanup all browser sessions"""
        while not self.browsers.empty():
            try:
                browser = self.browsers.get_nowait()
                browser.quit()
            except:
                pass


class PDFGenerator:
    """PDF generation utility class"""
    
    def __init__(self, config):
        self.config = config
    
    def _get_pdf_params(self, paper_height=5):
        """Get standard PDF generation parameters"""
        return {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "marginsType": 0,
            "paperWidth": self.config.pdf_paper_width,
            "paperHeight": paper_height,
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0,
            "preferCSSPageSize": False,
            "scale": self.config.pdf_scale
        }
    
    def _calculate_paper_height_from_browser(self, browser):
        """Calculate optimal paper height from currently loaded browser page with smart markers"""
        time.sleep(self.config.page_load_timeout)
        
        # Inject smart markers and get position data
        marker_result = browser.execute_script("""
            
            // Remove nav and header elements first
            var navElements = document.querySelectorAll('nav');
            navElements.forEach(function(nav) {
                nav.remove();
            });
            
            var headerElements = document.querySelectorAll('header');
            headerElements.forEach(function(header) {
                header.remove();
            });
                                               
            var footerElements = document.querySelectorAll('div[class*="PALBanner_container"]');
            footerElements.forEach(function(footer) {
                footer.remove();
            });
            
            console.log('Removed', navElements.length, 'nav elements and', headerElements.length, 'header elements');
            console.log('Removed', footerElements.length, 'footer elements');

            // Find the Next button using simplified selector
            var nextButton = document.querySelector('button[name="next"], button[aria-label="Next button"], button[aria-label="Previous button"], button[aria-label="Skip for now button"]');
            if (!nextButton) {
                var xpathQueries = [
                    "//button/span[contains(text(), 'Mark As Completed')]",
                    "//button/span[contains(text(), 'Complete')]"
                ];
                
                for (var q = 0; q < xpathQueries.length; q++) {
                    try {
                        var xpathResult = document.evaluate(
                            xpathQueries[q],
                            document,
                            null,
                            XPathResult.FIRST_ORDERED_NODE_TYPE,
                            null
                        );
                        if (xpathResult.singleNodeValue) {
                            nextButton = xpathResult.singleNodeValue;
                            console.log('Found button using XPath:', xpathQueries[q]);
                            break;
                        }
                    } catch (e) {
                        console.log('XPath search failed for:', xpathQueries[q], e);
                    }
                }
            }
            if (nextButton) {
                // Create a highly visible marker for PDF detection
                var markerDiv = document.createElement('div');
                markerDiv.id = 'EDUCATIVE_PDF_TRIM_MARKER';
                markerDiv.style.cssText = `
                    position: relative;
                    width: 100%;
                    height: 15px;
                    background: white;
                    font-size: 14px;
                    line-height: 15px;
                    color: black;
                    opacity: 1;
                    z-index: 9999;
                    margin: 5px 0;
                    padding: 2px;
                    border: 2px solid black;
                    display: block;
                `;
                
                // Add text content that will be rendered in PDF
                markerDiv.innerHTML = 'EDUCATIVE_TRIM_POINT_MARKER_HERE';
                
                // Create a more visible backup marker
                var backupMarker = document.createElement('div');
                backupMarker.style.cssText = `
                    position: relative;
                    width: 100%;
                    height: 12px;
                    background: white;
                    font-size: 12px;
                    line-height: 12px;
                    color: black;
                    opacity: 1;
                    z-index: 9998;
                    margin: 3px 0;
                    padding: 2px;
                    display: block;
                `;
                backupMarker.textContent = '••TRIM••POINT••HERE••';
                
                // Insert both markers right before the Next button
                nextButton.parentNode.insertBefore(markerDiv, nextButton);
                nextButton.parentNode.insertBefore(backupMarker, nextButton);
                
                // Get precise measurements
                var rect = nextButton.getBoundingClientRect();
                var buttonY = rect.top + window.pageYOffset;
                var windowHeight = window.innerHeight;
                var documentHeight = document.body.scrollHeight;
                
                console.log('Next button found at Y:', buttonY, 'Enhanced markers injected');
                
                return {
                    buttonY: buttonY,
                    windowHeight: windowHeight,
                    documentHeight: documentHeight,
                    buttonRect: {
                        top: rect.top,
                        bottom: rect.bottom,
                        left: rect.left,
                        right: rect.right,
                        width: rect.width,
                        height: rect.height
                    }
                };
            } else {
                // Check if this is simple HTML using XPath
                try {
                    var simpleHtmlResult = document.evaluate(
                        "//body[count(div)=1 and .//img]",
                        document,
                        null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                        null
                    );
                    
                    if (simpleHtmlResult.singleNodeValue) {
                        console.log('Simple HTML detected, adding marker after image');
                        
                        // Find the image tag and add markers after it
                        var allImages = document.querySelectorAll('img');
                        if (allImages.length > 0) {
                            var lastImage = allImages[allImages.length - 1];
                
                            // Create main marker
                            var markerDiv = document.createElement('div');
                            markerDiv.id = 'EDUCATIVE_PDF_TRIM_MARKER';
                            markerDiv.style.cssText = `
                                position: relative;
                                width: 100%;
                                height: 15px;
                                background: white;
                                font-size: 14px;
                                line-height: 15px;
                                color: black;
                                opacity: 1;
                                z-index: 9999;
                                margin: 5px 0;
                                padding: 2px;
                                border: 2px solid black;
                                display: block;
                            `;
                            markerDiv.innerHTML = 'EDUCATIVE_TRIM_POINT_MARKER_HERE';
                            
                            // Create backup marker
                            var backupMarker = document.createElement('div');
                            backupMarker.style.cssText = `
                                position: relative;
                                width: 100%;
                                height: 12px;
                                background: white;
                                font-size: 12px;
                                line-height: 12px;
                                color: black;
                                opacity: 1;
                                z-index: 9998;
                                margin: 3px 0;
                                padding: 2px;
                                display: block;
                            `;
                            backupMarker.textContent = '••TRIM••POINT••HERE••';                            // Insert markers after the last image
                            lastImage.parentNode.insertBefore(markerDiv, lastImage.nextSibling);
                            lastImage.parentNode.insertBefore(backupMarker, lastImage.nextSibling);
                            
                            console.log('Added markers after last image (image', allImages.length, 'of', allImages.length, ')');
                            
                            // Get last image position for button Y
                            var lastImageRect = lastImage.getBoundingClientRect();
                            var lastImageBottom = lastImageRect.bottom + window.pageYOffset;
                            
                            return {
                                buttonY: lastImageBottom,
                                windowHeight: window.innerHeight,
                                documentHeight: document.body.scrollHeight,
                                buttonRect: null
                            };
                        } else {
                            console.log('No image found in simple HTML');
                        }
                    }
                } catch (e) {
                    console.log('Simple HTML XPath check failed:', e);
                }
                
                console.log('Next button not found, using body height');
                return {
                    buttonY: document.body.scrollHeight,
                    windowHeight: window.innerHeight,
                    documentHeight: document.body.scrollHeight,
                    buttonRect: null
                };
            }
        """)
        
        content_height = marker_result['buttonY'] if marker_result else browser.execute_script("return document.body.scrollHeight")
        paper_height_inches = max(content_height / 96, self.config.min_paper_height)
        
        return paper_height_inches

    def _calculate_paper_height(self, browser, html_file):
        """Calculate optimal paper height based on content"""
        browser.get(f"file:///{html_file}")
        
        # Pre-inject highly visible markers before calculating height
        browser.execute_script("""
            // Make markers more visible for PDF rendering
            var existingMarkers = document.querySelectorAll('#EDUCATIVE_PDF_TRIM_MARKER');
            existingMarkers.forEach(function(marker) {
                marker.style.cssText = `
                    position: relative;
                    width: 100%;
                    height: 15px;
                    background: white;
                    font-size: 14px;
                    line-height: 15px;
                    color: black;
                    opacity: 1;
                    z-index: 9999;
                    margin: 5px 0;
                    padding: 2px;
                    border: 2px solid black;
                    display: block;
                `;
            });
            
            var existingBackups = document.evaluate(
                "//div[contains(text(), '••TRIM••POINT••HERE••')]",
                document,
                null,
                XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE,
                null
            );
            
            for (var i = 0; i < existingBackups.snapshotLength; i++) {
                var backup = existingBackups.snapshotItem(i);
                backup.style.cssText = `
                    position: relative;
                    width: 100%;
                    height: 12px;
                    background: white;
                    font-size: 12px;
                    line-height: 12px;
                    color: black;
                    opacity: 1;
                    z-index: 9998;
                    margin: 3px 0;
                    padding: 2px;
                    display: block;
                `;
            }
            
            console.log('Enhanced marker visibility for PDF rendering');
        """)
        
        return self._calculate_paper_height_from_browser(browser)
    
    def generate_pdf_from_browser(self, browser):
        """Generate PDF from currently loaded browser page without changing URL"""
        paper_height = self._calculate_paper_height_from_browser(browser)
        params = self._get_pdf_params(paper_height)
        
        pageData = browser.execute_cdp_cmd("Page.printToPDF", params)
        time.sleep(self.config.pdf_generation_pause)
        
        pdf_binary = base64.b64decode(pageData['data'])
        pdfBinaryData = io.BytesIO(pdf_binary)
        
        return self._merge_pdf_pages(pdfBinaryData, browser)
    
    def generate_single_pdf(self, html_file, browser=None):
        """Generate PDF from single HTML file"""
        should_quit_browser = browser is None
        
        if browser is None:
            browser = Driver(
                undetectable=True, 
                user_data_dir=f"{self.config.user_data_dir}_DEFAULT",
                binary_location=self.config.chrome_binary_path, 
                headless2=True,
                proxy=None, 
                chromium_arg=self.config.chrome_args,
                headed=False, 
                driver_version=self.config.chrome_driver_version
            )
        
        try:
            paper_height = self._calculate_paper_height(browser, html_file)
            params = self._get_pdf_params(paper_height)
            
            pageData = browser.execute_cdp_cmd("Page.printToPDF", params)
            time.sleep(self.config.pdf_generation_pause)
            
            pdf_binary = base64.b64decode(pageData['data'])
            pdfBinaryData = io.BytesIO(pdf_binary)
                
            pdf_output = self._merge_pdf_pages(pdfBinaryData, browser)
            return pdf_output
            
        finally:
            if should_quit_browser and browser:
                browser.quit()
        
    def _merge_pdf_pages(self, pdf_binary_data, browser=None):
        """Merge all PDF pages into a single continuous page with smart trimming"""
        reader = PdfReader(pdf_binary_data)
        output_pdf = PdfWriter()
        
        if len(reader.pages) == 0:
            raise Exception("No pages found in PDF")
        
        # If single page, apply smart trimming if enabled
        if len(reader.pages) == 1:
            page = reader.pages[0]
            
            if self.config.trim_whitespace:
                # Get PDF bytes for trimming
                temp_output = io.BytesIO()
                temp_writer = PdfWriter()
                temp_writer.add_page(page)
                temp_writer.write(temp_output)
                pdf_bytes = temp_output.getvalue()
                
                # Apply smart trimming
                trimmed_pdf_bytes, used_fallback, fallback_reason = self._apply_smart_trimming(pdf_bytes, browser)
                
                # Create a PdfWriter from trimmed bytes and return it
                trimmed_reader = PdfReader(io.BytesIO(trimmed_pdf_bytes))
                final_output = PdfWriter()
                final_output.add_page(trimmed_reader.pages[0])
                
                # Store fallback info on the writer for later retrieval
                final_output._fallback_used = used_fallback
                final_output._fallback_reason = fallback_reason
                
                return final_output
            else:
                # No trimming, just add the page
                output_pdf.add_page(page)
                # No fallback since no trimming was done
                output_pdf._fallback_used = False
                output_pdf._fallback_reason = None
                return output_pdf
        
        # For multiple pages, merge first then trim
        if len(reader.pages) > 1:
            # Calculate total height needed for all pages
            total_height = 0
            max_width = 0
            
            for page in reader.pages:
                page_box = page.mediabox
                total_height += float(page_box.height)
                max_width = max(max_width, float(page_box.width))
            
            # Create a new page with the combined dimensions
            combined_page = PageObject.create_blank_page(width=max_width, height=total_height)
            
            # Merge all pages into the single page
            current_y = total_height
            for page in reader.pages:
                page_height = float(page.mediabox.height)
                current_y -= page_height
                
                transformation = Transformation().translate(0, current_y)
                page.add_transformation(transformation)
                combined_page.merge_page(page)
            
            output_pdf.add_page(combined_page)
            print(f"Merged {len(reader.pages)} pages into single continuous page")
            
            # Apply smart trimming to merged page if enabled
            if self.config.trim_whitespace:
                temp_output = io.BytesIO()
                output_pdf.write(temp_output)
                pdf_bytes = temp_output.getvalue()
                
                # Apply smart trimming
                trimmed_pdf_bytes, used_fallback, fallback_reason = self._apply_smart_trimming(pdf_bytes, browser)
                
                # Read the trimmed PDF and return
                trimmed_reader = PdfReader(io.BytesIO(trimmed_pdf_bytes))
                final_output = PdfWriter()
                final_output.add_page(trimmed_reader.pages[0])
                
                # Store fallback info on the writer for later retrieval
                final_output._fallback_used = used_fallback
                final_output._fallback_reason = fallback_reason
                
                return final_output
        
        # Add fallback info to output_pdf for cases with no trimming
        if not hasattr(output_pdf, '_fallback_used'):
            output_pdf._fallback_used = False
            output_pdf._fallback_reason = None
            
        return output_pdf
    
    def _apply_smart_trimming(self, pdf_bytes, browser=None):
        """Apply smart trimming with fallback methods"""
        # Return tuple: (trimmed_pdf_bytes, used_fallback, fallback_reason)
        try:
            if not self.config.smart_trimming:
                print(f"🔄 Smart trimming disabled, using fallback trim ({self.config.fallback_trim_percentage*100}%)")
                trimmed_bytes = SmartTrimmingUtility.fallback_trim_pdf(pdf_bytes, self.config.fallback_trim_percentage)
                return trimmed_bytes, True, "Smart trimming disabled"
            
            print(f"🎯 Applying smart trimming...")
            
            marker_y_position = SmartTrimmingUtility.extract_text_with_positions(pdf_bytes)
            if marker_y_position:
                print(f"📍 Using text marker position: {marker_y_position}")
                trimmed_bytes = SmartTrimmingUtility.trim_pdf_at_marker(pdf_bytes, marker_y_position)
                return trimmed_bytes, False, None  # Success - no fallback
            
            # Only reach here if no marker was found - this is actual fallback
            print(f"🔄 Using fallback trimming ({self.config.fallback_trim_percentage*100}% from bottom)")
            trimmed_bytes = SmartTrimmingUtility.fallback_trim_pdf(pdf_bytes, self.config.fallback_trim_percentage)
            return trimmed_bytes, True, "Marker not found"
            
        except Exception as e:
            print(f"⚠️ Error in smart trimming: {e}")
            print(f"🔄 Falling back to original PDF")
            return pdf_bytes, True, f"Error: {str(e)[:50]}"


class TopicExtractor:
    """Extract topic information from HTML files"""
    
    @staticmethod
    def extract_topic_name_and_number(html_file_path):
        """Extract topic name and number from HTML file path"""
        filename = os.path.splitext(os.path.basename(html_file_path))[0]
        
        # Extract number from beginning of filename
        number_match = re.match(r'^(\d+)', filename)
        topic_number = int(number_match.group(1)) if number_match else 999999
        
        # Remove numbers and dashes from beginning
        topic_name = re.sub(r'^[\d\-\s]+', '', filename)
        topic_name = topic_name.replace('-', ' ').replace('_', ' ')
        topic_name = ' '.join(topic_name.split())
        
        if not topic_name:
            topic_name = filename
            
        return topic_number, topic_name


class CourseScanner:
    """Scan and organize courses and topics from folder structure"""
    
    def __init__(self, config):
        self.config = config
    
    def scan_courses_and_topics(self, root_directory):
        """
        Scan for courses and their topics
        Returns: dict with course_name -> {'path': course_path, 'topics': [topic_paths]}
        """
        courses = {}
        
        print(f"🔍 Scanning for courses in: {root_directory}")
        
        for item in os.listdir(root_directory):
            item_path = os.path.join(root_directory, item)
            
            if not os.path.isdir(item_path):
                continue
            
            # Skip excluded folders
            if any(excluded in item for excluded in self.config.excluded_folders):
                print(f"⏭️  Skipping excluded folder: {item}")
                continue
            
            if self._is_course_folder(item_path, item):
                course_topics = self._scan_course_topics(item_path)
                if course_topics:
                    courses[item] = {
                        'path': item_path,
                        'topics': course_topics
                    }
                    print(f"📚 Found course: {item} ({len(course_topics)} topics)")
                else:
                    print(f"⚠️  Course folder found but no topics: {item}")
        
        print(f"📊 Total courses found: {len(courses)}")
        return courses
    
    def _is_course_folder(self, folder_path, folder_name):
        """
        Determine if a folder is a course folder
        Course folder: NO dash in folder name
        """
        # Course folders do NOT contain dashes
        return '-' not in folder_name
    
    def _is_topic_folder(self, folder_name):
        """
        Determine if a folder is a topic folder  
        Topic folder: contains dash in folder name
        """
        # Topic folders contain dashes
        return '-' in folder_name
    
    def _scan_course_topics(self, course_path):
        """Scan for topic folders within a course and return HTML files"""
        topic_html_files = []
        
        for item in os.listdir(course_path):
            item_path = os.path.join(course_path, item)
            
            if not os.path.isdir(item_path):
                continue
            
            # Skip excluded folders
            if any(excluded in item for excluded in self.config.excluded_folders):
                continue
            
            if self._is_topic_folder(item):
                # Find HTML files in this topic folder
                html_files = self._find_html_files_in_folder(item_path)
                topic_html_files.extend(html_files)
        
        # Sort by topic number (extracted from folder name)
        topic_html_files.sort(key=self._extract_topic_number_from_path)
        return topic_html_files
    
    def _find_html_files_in_folder(self, folder_path):
        """Find all HTML files in a specific folder"""
        html_files = []
        for file in os.listdir(folder_path):
            if file.endswith('.html'):
                full_path = os.path.join(folder_path, file)
                html_files.append(full_path)
        return html_files
    
    def _extract_topic_number_from_path(self, file_path):
        """Extract topic number from file path for sorting"""
        import re
        folder_name = os.path.basename(os.path.dirname(file_path))
        # Extract number from beginning of folder name (works for "001-topic" format)
        match = re.match(r'^(\d+)', folder_name)
        return int(match.group(1)) if match else 999999


class Html2PdfConverter:
    """Main HTML to PDF converter class with parallel processing"""
    
    def __init__(self, config=None):
        self.config = config or PDFConverterConfig()
        self.pdf_generator = PDFGenerator(self.config)
        self.course_scanner = CourseScanner(self.config)
        self.topic_extractor = TopicExtractor()
    
    def convert_single_file(self, file_path, output_path):
        """Convert single HTML file to PDF"""
        print("Creating single page PDF without page breaks...")
        
        pdf_writer = self.pdf_generator.generate_single_pdf(file_path)
        
        with open(output_path, "wb") as f:
            pdf_writer.write(f)
            
        print(f"Single page PDF created successfully: {output_path}")
        return output_path
    
    def convert_browser_page_to_pdf(self, browser, output_path):
        """Convert currently loaded browser page to PDF without navigating"""
        print("Creating PDF from currently loaded browser page...")
        
        pdf_writer = self.pdf_generator.generate_pdf_from_browser(browser)
        
        with open(output_path, "wb") as f:
            pdf_writer.write(f)
            
        print(f"Browser page PDF created successfully: {output_path}")
        return output_path
    
    def _convert_html_threaded(self, html_file, temp_dir, browser_manager):
        """Thread-safe function to convert HTML to PDF"""
        thread_name = threading.current_thread().name
        start_time = time.time()
        
        try:
            base_name = os.path.splitext(os.path.basename(html_file))[0]
            temp_pdf_path = os.path.join(temp_dir, f"{base_name}.pdf")
            
            browser = browser_manager.get_browser()
            
            try:
                print(f"[{thread_name}] 🔄 Starting: {base_name}")
                
                # Generate PDF using shared browser
                pdf_writer = self.pdf_generator.generate_single_pdf(html_file, browser)
                
                with open(temp_pdf_path, "wb") as f:
                    pdf_writer.write(f)
                
                topic_number, topic_name = self.topic_extractor.extract_topic_name_and_number(html_file)
                
                # The PDF generation process returns fallback info directly
                # Check if fallback was used by examining the PDF generation process
                used_fallback = getattr(pdf_writer, '_fallback_used', False)
                fallback_reason = getattr(pdf_writer, '_fallback_reason', None)
                
                elapsed_time = time.time() - start_time
                status_icon = "🔄" if used_fallback else "✅"
                print(f"[{thread_name}] {status_icon} Completed: {topic_number}. {topic_name} ({elapsed_time:.1f}s)")
                if used_fallback:
                    print(f"[{thread_name}] 📝 Fallback used: {fallback_reason}")
                
                return {
                    'topic_number': topic_number,
                    'topic_name': topic_name,
                    'pdf_path': temp_pdf_path,
                    'html_file': html_file,
                    'processing_time': elapsed_time,
                    'used_fallback': used_fallback,
                    'fallback_reason': fallback_reason
                }
                
            finally:
                browser_manager.return_browser(browser)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"[{thread_name}] ❌ Failed: {base_name} ({elapsed_time:.1f}s) - {str(e)[:100]}")
            raise Exception(f"Html2PdfConverter:_convert_html_threaded: {e}")
    
    def convert_multiple_courses(self, root_directory=None, max_threads=None):
        """Convert multiple courses to separate PDFs"""
        root_directory = root_directory or self.config.root_directory
        
        print(f"🎓 Starting multi-course PDF generation...")
        
        # Scan for courses and topics
        courses = self.course_scanner.scan_courses_and_topics(root_directory)
        
        if not courses:
            print("❌ No courses found!")
            return
        
        # Calculate total topics across all courses
        total_topics = sum(len(course_info['topics']) for course_info in courses.values())
        
        print(f"\n📚 Found {len(courses)} courses to process:")
        for course_name, course_info in courses.items():
            topic_count = len(course_info['topics'])
            print(f"   📖 {course_name}: {topic_count} topics")
        
        # Calculate optimal browser count based on total topics across all courses
        optimal_browsers = self.config.get_optimal_browser_count(total_topics)
        if max_threads is None:
            max_threads = optimal_browsers
        else:
            max_threads = min(max_threads, optimal_browsers, total_topics)
        
        print(f"\n🔧 Global Configuration:")
        print(f"   📄 Total topics: {total_topics}")
        print(f"   📱 Browsers: {optimal_browsers} (optimal for {total_topics} topics)")
        print(f"   🧵 Max threads: {max_threads}")
        print(f"🚀 Initializing shared browser pool...\n")
        
        # Create shared browser manager for all courses
        browser_manager = BrowserSessionManager(self.config, optimal_browsers)
        
        try:
            # Process each course using the shared browser pool
            total_fallback_files = 0
            total_successful_files = 0
            all_fallback_files = []
            
            for course_name, course_info in courses.items():
                print(f"\n🔄 Processing course: {course_name}")
                
                course_output_path = os.path.join(course_info['path'], f"{course_name}.pdf")
                
                # Convert this course using shared browser pool
                course_results = self._convert_single_course(
                    course_name=course_name,
                    html_files=course_info['topics'],
                    output_path=course_output_path,
                    max_threads=max_threads,
                    browser_manager=browser_manager
                )
                
                # Track fallback usage globally
                if course_results:
                    course_fallback_count = sum(1 for result in course_results if result.get('used_fallback', False))
                    total_fallback_files += course_fallback_count
                    total_successful_files += len(course_results)
                    
                    # Collect fallback files for global summary
                    for result in course_results:
                        if result.get('used_fallback', False):
                            all_fallback_files.append({
                                'course': course_name,
                                'topic': f"{result['topic_number']}. {result['topic_name']}",
                                'reason': result.get('fallback_reason', 'Unknown')
                            })
            
            print(f"\n🎉 All courses processed successfully!")
            print(f"📊 Global Statistics:")
            print(f"   ✅ Total successful files: {total_successful_files}")
            print(f"   🎯 Smart trimming used: {total_successful_files - total_fallback_files}")
            print(f"   🔄 Fallback strategy used: {total_fallback_files}")
            
            if total_fallback_files > 0:
                print(f"\n📝 All files that used fallback strategy:")
                for fb_file in all_fallback_files:
                    print(f"   🔄 [{fb_file['course']}] {fb_file['topic']} - {fb_file['reason']}")
            
        finally:
            print("\n🧹 Cleaning up shared browser pool...")
            browser_manager.cleanup()
            print("✅ Cleanup completed!")
    
    def _convert_single_course(self, course_name, html_files, output_path, max_threads=None, browser_manager=None):
        """Convert a single course's HTML files to PDF"""
        total_files = len(html_files)
        
        if total_files == 0:
            print(f"⚠️  No HTML files found for course: {course_name}")
            return
        
        # Use provided browser_manager or create a new one (for backwards compatibility)
        should_cleanup_browser_manager = browser_manager is None
        if browser_manager is None:
            # Calculate optimal browser count for this course only (fallback for single course usage)
            optimal_browsers = self.config.get_optimal_browser_count(total_files)
            browser_manager = BrowserSessionManager(self.config, optimal_browsers)
        
        if max_threads is None:
            # Use the number of available browsers as max threads
            available_browsers = browser_manager.browsers.qsize()
            max_threads = min(available_browsers, total_files)
        else:
            available_browsers = browser_manager.browsers.qsize()
            max_threads = min(max_threads, available_browsers, total_files)
        
        print(f"📊 Course: {course_name}")
        print(f"   📄 Files: {total_files}")
        print(f"   📱 Available browsers: {browser_manager.browsers.qsize()}")
        print(f"   🧵 Threads: {max_threads}")
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            start_time = time.time()
            pdf_results = []
            failed_files = []
            
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                future_to_file = {
                    executor.submit(self._convert_html_threaded, html_file, temp_dir, browser_manager): html_file 
                    for html_file in html_files
                }
                
                for future in as_completed(future_to_file):
                    html_file = future_to_file[future]
                    try:
                        result = future.result()
                        pdf_results.append(result)
                        completed = len(pdf_results) + len(failed_files)
                        progress = (completed / total_files) * 100
                        avg_time = sum(r['processing_time'] for r in pdf_results) / len(pdf_results)
                        print(f"   📈 Progress: {completed}/{total_files} ({progress:.1f}%) | Avg: {avg_time:.1f}s/file")
                    except Exception as e:
                        failed_files.append(html_file)
                        print(f"   ❌ Failed: {os.path.basename(html_file)} - {str(e)[:80]}...")
            
            # Sort results by topic number
            pdf_results.sort(key=lambda x: x['topic_number'])
            
            self._create_combined_pdf(pdf_results, output_path)
            
            total_processing_time = time.time() - start_time
            success_count = len(pdf_results)
            fail_count = len(failed_files)
            
            # Count fallback usage
            fallback_count = sum(1 for result in pdf_results if result.get('used_fallback', False))
            smart_trimming_count = success_count - fallback_count
            
            print(f"   📋 Course Summary - {course_name}:")
            print(f"      ✅ Successful: {success_count}/{total_files}")
            print(f"      ❌ Failed: {fail_count}/{total_files}")
            print(f"      🎯 Smart trimming: {smart_trimming_count}/{success_count}")
            print(f"      🔄 Fallback used: {fallback_count}/{success_count}")
            print(f"      ⏱️  Total time: {total_processing_time:.1f}s")
            if success_count > 0:
                print(f"      📊 Avg per file: {total_processing_time/success_count:.1f}s")
            
            # List files that used fallback
            if fallback_count > 0:
                print(f"\n   📝 Files using fallback strategy:")
                for result in pdf_results:
                    if result.get('used_fallback', False):
                        reason = result.get('fallback_reason', 'Unknown')
                        print(f"      🔄 {result['topic_number']}. {result['topic_name']} - {reason}")
                print()  # Extra line for spacing
            
            return pdf_results  # Return results for global tracking
            
        finally:
            # Only cleanup browser manager if we created it locally
            if should_cleanup_browser_manager:
                browser_manager.cleanup()
            shutil.rmtree(temp_dir, ignore_errors=True)
    

    def _create_combined_pdf(self, pdf_results, output_path):
        """Create combined PDF with bookmarks from results"""
        if not pdf_results:
            print("❌ No files were successfully processed!")
            return
        
        success_count = len(pdf_results)
        print(f"\n📖 Creating combined PDF with {success_count} topics...")
        print("📑 Topic ordering:")
        
        for i, result in enumerate(pdf_results[:10], 1):
            print(f"   {result['topic_number']}. {result['topic_name']}")
        if len(pdf_results) > 10:
            print(f"   ... and {len(pdf_results) - 10} more topics")
        
        combined_pdf = PdfWriter()
        page_number = 0
        
        for result in pdf_results:
            try:
                with open(result['pdf_path'], 'rb') as pdf_file:
                    pdf_reader = PdfReader(pdf_file)
                    
                    bookmark_title = f"{result['topic_number']}. {result['topic_name']}"
                    combined_pdf.add_outline_item(bookmark_title, page_number)
                    
                    for page in pdf_reader.pages:
                        combined_pdf.add_page(page)
                        page_number += 1
                
                os.remove(result['pdf_path'])
                
            except Exception as e:
                print(f"⚠️  Error adding {result['topic_name']} to combined PDF: {e}")
                continue
        
        with open(output_path, 'wb') as output_file:
            combined_pdf.write(output_file)
        
        print(f"\n🎉 SUCCESS! Combined PDF created: {output_path}")
        print(f"📄 Total pages: {page_number}")
        print(f"📚 Total topics: {success_count}")
        print(f"📁 File size: {os.path.getsize(output_path) / (1024*1024):.1f} MB")

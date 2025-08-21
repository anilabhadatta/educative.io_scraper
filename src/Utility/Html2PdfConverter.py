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

# Configuration settings
class Config:
    # Browser and Chrome paths
    USER_DATA_DIR = r"C:\Users\Anilabha\EducativeScraper\UserData1\ucDriver-True"
    CHROME_BINARY_PATH = r"D:\Development\educative.io_scraper\src\ChromeBinary\win\chrome-win64\chrome.exe"
    CHROME_ARGS = " --allow-running-insecure-content, --ignore-certificate-errors-spki-list,--ignore-ssl-errors"
    CHROME_DRIVER_VERSION = 116
    
    # Processing settings
    MAX_BROWSER_SESSIONS = 10  # Maximum browser sessions to create
    MIN_BROWSER_SESSIONS = 1   # Minimum browser sessions
    PAGE_LOAD_TIMEOUT = 2      # Seconds to wait for page load
    PDF_GENERATION_PAUSE = 0.5 # Pause after PDF generation
    
    # PDF settings
    PDF_SCALE = 0.8
    PDF_PAPER_WIDTH = 8.27
    MIN_PAPER_HEIGHT = 8.5
    
    # Folder exclusions
    EXCLUDED_FOLDERS = ['Codes_', 'Quiz', 'MarkDownQuiz']
    
    @classmethod
    def get_optimal_browser_count(cls, file_count):
        """Calculate optimal number of browsers based on file count"""
        optimal = min(file_count, cls.MAX_BROWSER_SESSIONS)
        return max(optimal, cls.MIN_BROWSER_SESSIONS)


def printPdfAsCdp(file_path):
    print(f"printPdfAsCdp: Getting Full page PDF data without page breaks")
    
    params = {
        "landscape": False,
        "displayHeaderFooter": False,  # Disable header/footer for continuous page
        "printBackground": True,
        "marginsType": 0,  # No margins for continuous content
        "paperWidth": Config.PDF_PAPER_WIDTH,
        "paperHeight": 5,  # Very large height to accommodate all content
        "marginTop": 0,
        "marginBottom": 0,
        "marginLeft": 0,
        "marginRight": 0,
        "preferCSSPageSize": False,  # Don't respect CSS @page rules to override page breaks
        "scale": Config.PDF_SCALE  # Scale content to fit
    }
    
    browser = Driver(undetectable=True, user_data_dir=Config.USER_DATA_DIR,
                                      binary_location=Config.CHROME_BINARY_PATH, headless2=True,
                                      proxy=None, chromium_arg=Config.CHROME_ARGS,
                                      headed=False, driver_version=Config.CHROME_DRIVER_VERSION)
    try:
        browser.get(f"file:///{file_path}")
        
        # Wait for page to load completely
        time.sleep(Config.PAGE_LOAD_TIMEOUT)
        
        # Get browser DPI and more accurate conversion
        browser_info = browser.execute_script("""
            return {
                contentHeight: (function() {
                    var nextButton = document.querySelector('button[name="next"]');
                    if (nextButton) {
                        var rect = nextButton.getBoundingClientRect();
                        var buttonY = rect.bottom + window.pageYOffset;
                        console.log('Next button found at Y:', buttonY);
                        return buttonY + 10; // Small buffer
                    } else {
                        console.log('Next button not found, using body height');
                        return document.body.scrollHeight;
                    }
                })(),
                devicePixelRatio: window.devicePixelRatio,
                screenDPI: window.screen.width / (window.screen.availWidth / 96)
            };
        """)
        
        content_height = browser_info['contentHeight']
        device_pixel_ratio = browser_info['devicePixelRatio']
        
        # More accurate conversion considering device pixel ratio
        # PDF generation typically expects 72 DPI, but browser reports in 96 DPI
        # Adjust for device pixel ratio to get actual physical pixels
        actual_pixels = content_height / device_pixel_ratio
        paper_height_inches = actual_pixels / 72  # PDF uses 72 DPI
        
        # Ensure reasonable minimum
        paper_height_inches = max(paper_height_inches, Config.MIN_PAPER_HEIGHT)
        
        # Update params with calculated height
        params["paperHeight"] = paper_height_inches
        
        print(f"Content height: {content_height}px (device ratio: {device_pixel_ratio})")
        print(f"Actual pixels: {actual_pixels:.0f}px, Paper height: {paper_height_inches:.2f} inches")
        
        pageData = browser.execute_cdp_cmd("Page.printToPDF", params)
        time.sleep(2)
        pageData = base64.b64decode(pageData['data'])
        pdfBinaryData = io.BytesIO(pageData)
        return mergePdfPages(pdfBinaryData)
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"PrintFileUtility:printPdfAsCdp: {lineNumber}: {e}")
    finally:
        if browser:
            browser.quit()

def mergePdfPages(pdfBinaryData):
    """
    Merge all PDF pages into a single continuous page without page breaks
    """
    try:
        reader = PdfReader(pdfBinaryData)
        outputPdf = PdfWriter()
        
        if len(reader.pages) == 0:
            raise Exception("No pages found in PDF")
        
        # If there's only one page, just add it
        if len(reader.pages) == 1:
            outputPdf.add_page(reader.pages[0])
            return outputPdf
        
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
            
            # Transform to position the page at the correct location
            transformation = Transformation().translate(0, current_y)
            page.add_transformation(transformation)
            
            # Merge this page onto the combined page
            combined_page.merge_page(page)
        
        outputPdf.add_page(combined_page)
        
        print(f"Merged {len(reader.pages)} pages into single continuous page")
        return outputPdf
        
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:mergePdfPages: {lineNumber}: {e}")

def trimPdfWhiteSpace(pdfBinaryData):
    """
    Trim excessive white space from the bottom of PDF pages
    """
    try:
        reader = PdfReader(pdfBinaryData)
        outputPdf = PdfWriter()
        
        for page in reader.pages:
            # Get the media box (page dimensions)
            media_box = page.mediabox
            page_width = float(media_box.width)
            page_height = float(media_box.height)
            
            # For single page continuous PDFs, we want to trim bottom whitespace
            # This is a simple approach - you might need to adjust based on your content
            
            # Reduce height by 10% to remove bottom white space (adjust as needed)
            # You can make this more sophisticated by analyzing content
            trimmed_height = page_height * 0.9  # Remove 10% from bottom
            
            # Create new media box with trimmed height
            page.mediabox.lower_left = (0, page_height - trimmed_height)
            page.mediabox.upper_right = (page_width, page_height)
            
            outputPdf.add_page(page)
        
        print(f"Trimmed white space from PDF")
        return outputPdf
        
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:trimPdfWhiteSpace: {lineNumber}: {e}")

def createSinglePagePdf(file_path, output_path, trim_whitespace=True):
    """
    Alternative approach: Create a single continuous PDF without page breaks
    """
    try:
        print("Creating single page PDF without page breaks and excessive white space...")
        
        # Generate the PDF
        pdf_writer = printPdfAsCdp(file_path)
        
        # Optionally trim white space
        if trim_whitespace:
            # Convert to binary data for trimming
            temp_output = io.BytesIO()
            pdf_writer.write(temp_output)
            temp_output.seek(0)
            
            # Trim white space
            pdf_writer = trimPdfWhiteSpace(temp_output)
        
        # Write to output file
        with open(output_path, "wb") as f:
            pdf_writer.write(f)
            
        print(f"Single page PDF created successfully: {output_path}")
        return output_path
        
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:createSinglePagePdf: {lineNumber}: {e}")

def scan_html_files(root_directory):
    """
    Scan all HTML files in folder tree, excluding specific folders
    """
    try:
        html_files = []
        
        for root, dirs, files in os.walk(root_directory):
            # Remove excluded directories from dirs list to skip them
            dirs[:] = [d for d in dirs if not any(excluded in d for excluded in Config.EXCLUDED_FOLDERS)]
            
            for file in files:
                if file.endswith('.html'):
                    full_path = os.path.join(root, file)
                    html_files.append(full_path)
        
        # Sort files for consistent order
        html_files.sort()
        print(f"Found {len(html_files)} HTML files")
        return html_files
        
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:scan_html_files: {lineNumber}: {e}")

def extract_topic_name_and_number(html_file_path):
    """
    Extract topic name and number from HTML file path or filename
    """
    try:
        # Get filename without extension
        filename = os.path.splitext(os.path.basename(html_file_path))[0]
        
        # Extract number from beginning of filename
        number_match = re.match(r'^(\d+)', filename)
        topic_number = int(number_match.group(1)) if number_match else 999999  # Default high number for items without numbers
        
        # Remove numbers and dashes from beginning if present
        topic_name = re.sub(r'^[\d\-\s]+', '', filename)
        
        # Clean up the name
        topic_name = topic_name.replace('-', ' ').replace('_', ' ')
        topic_name = ' '.join(topic_name.split())  # Remove extra spaces
        
        if not topic_name:
            topic_name = filename
            
        return topic_number, topic_name
        
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:extract_topic_name_and_number: {lineNumber}: {e}")

# Thread-safe browser session manager
class BrowserSessionManager:
    def __init__(self, browser_count=None):
        self.browser_count = browser_count or Config.MAX_BROWSER_SESSIONS
        self.browsers = queue.Queue(maxsize=self.browser_count)
        self.lock = threading.Lock()
        self._initialize_browsers()
    
    def _initialize_browsers(self):
        """Initialize browser sessions"""
        print(f"Initializing browser session pool ({self.browser_count} browsers)...")
        # Create browser sessions
        for i in range(self.browser_count):
            try:
                browser = Driver(undetectable=True, user_data_dir=f"{Config.USER_DATA_DIR}_{i}",
                               binary_location=Config.CHROME_BINARY_PATH, headless2=True,
                               proxy=None, chromium_arg=Config.CHROME_ARGS,
                               headed=False, driver_version=Config.CHROME_DRIVER_VERSION)
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

def convert_html_to_pdf_threaded(html_file, temp_dir, browser_manager, trim_whitespace=True):
    """
    Thread-safe function to convert HTML to PDF using shared browser sessions
    """
    thread_name = threading.current_thread().name
    start_time = time.time()
    
    try:
        base_name = os.path.splitext(os.path.basename(html_file))[0]
        temp_pdf_path = os.path.join(temp_dir, f"{base_name}.pdf")
        
        # Get browser from pool
        browser = browser_manager.get_browser()
        params = {
            "landscape": False,
            "displayHeaderFooter": False,  # Disable header/footer for continuous page
            "printBackground": True,
            "marginsType": 0,  # No margins for continuous content
            "paperWidth": Config.PDF_PAPER_WIDTH,
            "paperHeight": 5,  # Very large height to accommodate all content
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0,
            "preferCSSPageSize": False,  # Don't respect CSS @page rules to override page breaks
            "scale": Config.PDF_SCALE  # Scale content to fit
        }
        
        try:
            print(f"[{thread_name}] 🔄 Starting: {base_name}")
            
            # Load the HTML file
            browser.get(f"file:///{html_file}")
            
            # Wait for page to load completely
            time.sleep(Config.PAGE_LOAD_TIMEOUT)  # Configurable timeout
            
            # Get browser DPI and more accurate conversion
            browser_info = browser.execute_script("""
                return {
                    contentHeight: (function() {
                        var nextButton = document.querySelector('button[name="next"]');
                        if (nextButton) {
                            var rect = nextButton.getBoundingClientRect();
                            var buttonY = rect.bottom + window.pageYOffset;
                            console.log('Next button found at Y:', buttonY);
                            return buttonY + 10; // Small buffer
                        } else {
                            console.log('Next button not found, using body height');
                            return document.body.scrollHeight;
                        }
                    })(),
                    devicePixelRatio: window.devicePixelRatio,
                    screenDPI: window.screen.width / (window.screen.availWidth / 96)
                };
            """)
            
            content_height = browser_info['contentHeight']
            device_pixel_ratio = browser_info['devicePixelRatio']
            
            # More accurate conversion considering device pixel ratio
            # PDF generation typically expects 72 DPI, but browser reports in 96 DPI
            # Adjust for device pixel ratio to get actual physical pixels
            actual_pixels = content_height / device_pixel_ratio
            paper_height_inches = actual_pixels / 72  # PDF uses 72 DPI
            
            # Ensure reasonable minimum
            paper_height_inches = max(paper_height_inches, Config.MIN_PAPER_HEIGHT)
            
            # Update params with calculated height
            params["paperHeight"] = paper_height_inches
            
            print(f"Content height: {content_height}px (device ratio: {device_pixel_ratio})")
            print(f"Actual pixels: {actual_pixels:.0f}px, Paper height: {paper_height_inches:.2f} inches")
            
            
            
            # Generate PDF
            pageData = browser.execute_cdp_cmd("Page.printToPDF", params)
            time.sleep(Config.PDF_GENERATION_PAUSE)  # Configurable pause
            
            # Decode and save PDF
            pdf_binary = base64.b64decode(pageData['data'])
            pdfBinaryData = io.BytesIO(pdf_binary)
            
            # Merge pages if needed
            pdf_writer = mergePdfPages(pdfBinaryData)
            if trim_whitespace:
                # Convert to binary data for trimming
                temp_output = io.BytesIO()
                pdf_writer.write(temp_output)
                temp_output.seek(0)
                
                # Trim white space
                pdf_writer = trimPdfWhiteSpace(temp_output)
            
            # Write to temporary file
            with open(temp_pdf_path, "wb") as f:
                pdf_writer.write(f)
            
            # Extract topic info
            topic_number, topic_name = extract_topic_name_and_number(html_file)
            
            elapsed_time = time.time() - start_time
            print(f"[{thread_name}] ✅ Completed: {topic_number}. {topic_name} ({elapsed_time:.1f}s)")
            
            return {
                'topic_number': topic_number,
                'topic_name': topic_name,
                'pdf_path': temp_pdf_path,
                'html_file': html_file,
                'processing_time': elapsed_time
            }
            
        finally:
            # Return browser to pool
            browser_manager.return_browser(browser)
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"[{thread_name}] ❌ Failed: {base_name} ({elapsed_time:.1f}s) - {str(e)[:100]}")
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:convert_html_to_pdf_threaded: {lineNumber}: {e}")

def extract_topic_name(html_file_path):
    """
    Extract topic name from HTML file path or filename
    """
    try:
        # Get filename without extension
        filename = os.path.splitext(os.path.basename(html_file_path))[0]
        
        # Remove numbers and dashes from beginning if present
        import re
        topic_name = re.sub(r'^[\d\-\s]+', '', filename)
        
        # Clean up the name
        topic_name = topic_name.replace('-', ' ').replace('_', ' ')
        topic_name = ' '.join(topic_name.split())  # Remove extra spaces
        
        return topic_name if topic_name else filename
        
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:extract_topic_name: {lineNumber}: {e}")

def convert_html_to_pdf_page(html_file, temp_dir, trim_whitespace=True):
    """
    Convert single HTML file to PDF and return the PDF path
    """
    try:
        base_name = os.path.splitext(os.path.basename(html_file))[0]
        temp_pdf_path = os.path.join(temp_dir, f"{base_name}.pdf")
        
        print(f"Converting: {html_file}")
        
        # Use the working PDF generation function
        pdf_writer = printPdfAsCdp(html_file)

        # Optionally trim white space
        if trim_whitespace:
            # Convert to binary data for trimming
            temp_output = io.BytesIO()
            pdf_writer.write(temp_output)
            temp_output.seek(0)
            
            # Trim white space
            pdf_writer = trimPdfWhiteSpace(temp_output)
        
        # Write to temporary file
        with open(temp_pdf_path, "wb") as f:
            pdf_writer.write(f)
        
        return temp_pdf_path
        
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:convert_html_to_pdf_page: {lineNumber}: {e}")

def create_combined_pdf_optimized(root_directory, output_path, max_threads=None):
    """
    Optimized version: Scan HTML files and create a single PDF with bookmarks using parallel processing
    """
    try:
        print(f"📁 Scanning HTML files in: {root_directory}")
        html_files = scan_html_files(root_directory)
        
        if not html_files:
            print("❌ No HTML files found!")
            return
        
        total_files = len(html_files)
        
        # Calculate optimal browser count and thread count
        optimal_browsers = Config.get_optimal_browser_count(total_files)
        if max_threads is None:
            max_threads = optimal_browsers
        else:
            max_threads = min(max_threads, optimal_browsers, total_files)
        
        print(f"📊 Found {total_files} HTML files")
        print(f"� Configuration:")
        print(f"   📱 Browsers: {optimal_browsers} (optimal for {total_files} files)")
        print(f"   🧵 Threads: {max_threads}")
        print(f"   ⏱️  Page load timeout: {Config.PAGE_LOAD_TIMEOUT}s")
        print(f"   📄 PDF scale: {Config.PDF_SCALE}")
        print(f"🚀 Starting parallel processing...\n")
        
        # Create temporary directory for individual PDFs
        temp_dir = tempfile.mkdtemp()
        
        # Initialize browser session manager with optimal count
        browser_manager = BrowserSessionManager(optimal_browsers)
        
        try:
            # Track overall progress
            start_time = time.time()
            pdf_results = []
            failed_files = []
            
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                # Submit all tasks
                future_to_file = {
                    executor.submit(convert_html_to_pdf_threaded, html_file, temp_dir, browser_manager): html_file 
                    for html_file in html_files
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_file):
                    html_file = future_to_file[future]
                    try:
                        result = future.result()
                        pdf_results.append(result)
                        completed = len(pdf_results) + len(failed_files)
                        progress = (completed / total_files) * 100
                        avg_time = sum(r['processing_time'] for r in pdf_results) / len(pdf_results)
                        print(f"📈 Progress: {completed}/{total_files} ({progress:.1f}%) | Avg: {avg_time:.1f}s/file")
                    except Exception as e:
                        failed_files.append(html_file)
                        print(f"❌ Failed: {os.path.basename(html_file)} - {str(e)[:80]}...")
            
            # Sort results by topic number
            pdf_results.sort(key=lambda x: x['topic_number'])
            
            total_processing_time = time.time() - start_time
            success_count = len(pdf_results)
            fail_count = len(failed_files)
            
            print(f"\n📋 Processing Summary:")
            print(f"   ✅ Successful: {success_count}/{total_files}")
            print(f"   ❌ Failed: {fail_count}/{total_files}")
            print(f"   ⏱️  Total time: {total_processing_time:.1f}s")
            print(f"   📊 Avg per file: {total_processing_time/success_count:.1f}s")
            
            if success_count == 0:
                print("❌ No files were successfully processed!")
                return
            
            print(f"\n📖 Creating combined PDF with {success_count} topics...")
            print("📑 Topic ordering:")
            for i, result in enumerate(pdf_results[:10], 1):  # Show first 10
                print(f"   {result['topic_number']}. {result['topic_name']}")
            if len(pdf_results) > 10:
                print(f"   ... and {len(pdf_results) - 10} more topics")
            
            # Create PDF writer for combined PDF
            combined_pdf = PdfWriter()
            page_number = 0
            
            # Add PDFs in the correct order
            for result in pdf_results:
                try:
                    # Read the generated PDF
                    with open(result['pdf_path'], 'rb') as pdf_file:
                        pdf_reader = PdfReader(pdf_file)
                        
                        # Add bookmark for this topic (just topic name with number)
                        bookmark_title = f"{result['topic_number']}. {result['topic_name']}"
                        combined_pdf.add_outline_item(bookmark_title, page_number)
                        
                        # Add all pages from this PDF
                        for page in pdf_reader.pages:
                            combined_pdf.add_page(page)
                            page_number += 1
                    
                    # Clean up temporary file
                    os.remove(result['pdf_path'])
                    
                except Exception as e:
                    print(f"⚠️  Error adding {result['topic_name']} to combined PDF: {e}")
                    continue
            
            # Write combined PDF
            with open(output_path, 'wb') as output_file:
                combined_pdf.write(output_file)
            
            print(f"\n🎉 SUCCESS! Combined PDF created: {output_path}")
            print(f"📄 Total pages: {page_number}")
            print(f"📚 Total topics: {success_count}")
            print(f"📁 File size: {os.path.getsize(output_path) / (1024*1024):.1f} MB")
            
        finally:
            # Clean up browser sessions and temporary directory
            print("\n🧹 Cleaning up resources...")
            browser_manager.cleanup()
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("✅ Cleanup completed!")
        
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:create_combined_pdf_optimized: {lineNumber}: {e}")

def create_combined_pdf(root_directory, output_path):
    """
    Scan HTML files and create a single PDF with bookmarks
    """
    try:
        print(f"Scanning HTML files in: {root_directory}")
        html_files = scan_html_files(root_directory)
        
        if not html_files:
            print("No HTML files found!")
            return
        
        # Create temporary directory for individual PDFs
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create PDF writer for combined PDF
            combined_pdf = PdfWriter()
            
            page_number = 0
            
            for i, html_file in enumerate(html_files, 1):
                try:
                    # Convert HTML to PDF
                    temp_pdf_path = convert_html_to_pdf_page(html_file, temp_dir)
                    
                    # Read the generated PDF
                    with open(temp_pdf_path, 'rb') as pdf_file:
                        pdf_reader = PdfReader(pdf_file)
                        
                        # Extract topic name for bookmark
                        topic_name = extract_topic_name(html_file)
                        
                        # Add bookmark for this topic
                        if topic_name:
                            combined_pdf.add_outline_item(f"{i}. {topic_name}", page_number)
                        
                        # Add all pages from this PDF
                        for page in pdf_reader.pages:
                            combined_pdf.add_page(page)
                            page_number += 1
                    
                    # Clean up temporary file
                    os.remove(temp_pdf_path)
                    
                except Exception as e:
                    print(f"Error processing {html_file}: {e}")
                    continue
            
            # Write combined PDF
            with open(output_path, 'wb') as output_file:
                combined_pdf.write(output_file)
            
            print(f"Combined PDF created successfully: {output_path}")
            print(f"Total pages: {page_number}")
            
        finally:
            # Clean up temporary directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        
    except Exception as e:
        lineNumber = e.__traceback__.tb_lineno
        raise Exception(f"Html2PdfConverter:create_combined_pdf: {lineNumber}: {e}")

# Main execution code
if __name__ == "__main__":
    # Configuration - Update these paths for your environment
    Config.USER_DATA_DIR = r"C:\Users\Anilabha\EducativeScraper\UserData1\ucDriver-True"
    Config.CHROME_BINARY_PATH = r"D:\Development\educative.io_scraper\src\ChromeBinary\win\chrome-win64\chrome.exe"
    
    # Example for single file
    # file_path = r"D:\Development\Courses_main\aws certified solutions architect associate saa c03 exam prep-incomplete\002-setting up aws account\002-setting up aws account.html"
    # output_path = r"D:\Development\Courses_main\aws certified solutions architect associate saa c03 exam prep-incomplete\002-setting up aws account\002-setting up aws account.pdf"
    # createSinglePagePdf(file_path, output_path)
    
    # Optimized scanning and combining all HTML files with parallel processing
    root_directory = r"D:\Development\Courses_main\aws certified solutions architect associate saa c03 exam prep-incomplete"
    output_path = r"D:\Development\Courses_main\aws certified solutions architect associate saa c03 exam prep-incomplete\combined_course.pdf"
    
    print("🚀 Starting optimized PDF generation with intelligent resource allocation...")
    print("✨ Features:")
    print("  ✓ Dynamic browser session pool (1-10 browsers based on file count)")
    print("  ✓ Intelligent thread allocation")
    print("  ✓ Automatic topic number ordering")
    print("  ✓ Clean bookmark names (no 'Chapter X')")
    print("  ✓ Configurable timeouts and settings")
    print()
    
    # Use intelligent threading - will automatically adjust based on file count
    create_combined_pdf_optimized(root_directory, output_path)
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
        self.output_path = os.path.join(self.root_directory, os.path.basename(self.root_directory)+".pdf")

        # Processing settings
        self.max_browser_sessions = 10
        self.min_browser_sessions = 1
        self.page_load_timeout = 1
        self.pdf_generation_pause = 1
        
        # PDF settings
        self.pdf_scale = 0.8
        self.pdf_paper_width = 8.27
        self.min_paper_height = 8.5
        self.trim_whitespace = True
        
        # Folder exclusions
        self.excluded_folders = ['Codes_', 'Quiz', 'MarkDownQuiz']
    
    def get_optimal_browser_count(self, file_count):
        """Calculate optimal number of browsers based on file count"""
        optimal = min(file_count, self.max_browser_sessions)
        return max(optimal, self.min_browser_sessions)


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
        """Calculate optimal paper height from currently loaded browser page"""
        time.sleep(self.config.page_load_timeout)
        
        browser_info = browser.execute_script("""
            return {
                contentHeight: (function() {
                    var nextButton = document.querySelector('button[name="next"]');
                    if (nextButton) {
                        var rect = nextButton.getBoundingClientRect();
                        var buttonY = rect.bottom + window.pageYOffset;
                        console.log('Next button found at Y:', buttonY);
                        return buttonY; // Small buffer
                    } else {
                        console.log('Next button not found, using body height');
                        return document.body.scrollHeight;
                    }
                })()
            };
        """)
        
        content_height = browser_info['contentHeight']
        paper_height_inches = max(content_height / 96, self.config.min_paper_height)
        
        return paper_height_inches

    def _calculate_paper_height(self, browser, html_file):
        """Calculate optimal paper height based on content"""
        browser.get(f"file:///{html_file}")
        return self._calculate_paper_height_from_browser(browser)
    
    def generate_pdf_from_browser(self, browser):
        """Generate PDF from currently loaded browser page without changing URL"""
        paper_height = self._calculate_paper_height_from_browser(browser)
        params = self._get_pdf_params(paper_height)
        
        pageData = browser.execute_cdp_cmd("Page.printToPDF", params)
        time.sleep(self.config.pdf_generation_pause)
        
        pdf_binary = base64.b64decode(pageData['data'])
        pdfBinaryData = io.BytesIO(pdf_binary)
        
        return self._merge_pdf_pages(pdfBinaryData)
    
    def generate_single_pdf(self, html_file, browser=None):
        """Generate PDF from single HTML file"""
        should_quit_browser = browser is None
        
        if browser is None:
            browser = Driver(
                undetectable=True, 
                user_data_dir=self.config.user_data_dir,
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
                
            pdf_output = self._merge_pdf_pages(pdfBinaryData)
            if self.config.trim_whitespace:
                temp_output = io.BytesIO()
                pdf_output.write(temp_output)
                temp_output.seek(0)
                
                # Trim white space
                pdf_output = self.trimPdfWhiteSpace(temp_output)
            return pdf_output
            
        finally:
            if should_quit_browser and browser:
                browser.quit()
    
    def trimPdfWhiteSpace(self, pdfBinaryData):
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
    
    def _merge_pdf_pages(self, pdf_binary_data):
        """Merge all PDF pages into a single continuous page"""
        reader = PdfReader(pdf_binary_data)
        output_pdf = PdfWriter()
        
        if len(reader.pages) == 0:
            raise Exception("No pages found in PDF")
        
        if len(reader.pages) == 1:
            output_pdf.add_page(reader.pages[0])
            return output_pdf
        
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
        return output_pdf


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


class FileScanner:
    """Scan and filter HTML files"""
    
    def __init__(self, config):
        self.config = config
    
    def scan_html_files(self, root_directory):
        """Scan all HTML files in folder tree, excluding specific folders"""
        html_files = []
        
        for root, dirs, files in os.walk(root_directory):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if not any(excluded in d for excluded in self.config.excluded_folders)]
            
            for file in files:
                if file.endswith('.html'):
                    full_path = os.path.join(root, file)
                    html_files.append(full_path)
        
        html_files.sort()
        print(f"Found {len(html_files)} HTML files")
        return html_files


class Html2PdfConverter:
    """Main HTML to PDF converter class with parallel processing"""
    
    def __init__(self, config=None):
        self.config = config or PDFConverterConfig()
        self.pdf_generator = PDFGenerator(self.config)
        self.file_scanner = FileScanner(self.config)
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
                browser_manager.return_browser(browser)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"[{thread_name}] ❌ Failed: {base_name} ({elapsed_time:.1f}s) - {str(e)[:100]}")
            raise Exception(f"Html2PdfConverter:_convert_html_threaded: {e}")
    
    def convert_multiple_files(self, root_directory=None, output_path=None, max_threads=None):
        """Convert multiple HTML files to single PDF with parallel processing"""
        # Use config paths if not provided
        root_directory = root_directory or self.config.root_directory
        output_path = output_path or self.config.output_path
        
        print(f"📁 Scanning HTML files in: {root_directory}")
        html_files = self.file_scanner.scan_html_files(root_directory)
        
        if not html_files:
            print("❌ No HTML files found!")
            return
        
        total_files = len(html_files)
        
        # Calculate optimal browser count and thread count
        optimal_browsers = self.config.get_optimal_browser_count(total_files)
        if max_threads is None:
            max_threads = optimal_browsers
        else:
            max_threads = min(max_threads, optimal_browsers, total_files)
        
        print(f"📊 Found {total_files} HTML files")
        print(f"🔧 Configuration:")
        print(f"   📱 Browsers: {optimal_browsers} (optimal for {total_files} files)")
        print(f"   🧵 Threads: {max_threads}")
        print(f"   ⏱️  Page load timeout: {self.config.page_load_timeout}s")
        print(f"   📄 PDF scale: {self.config.pdf_scale}")
        print(f"🚀 Starting parallel processing...\n")
        
        temp_dir = tempfile.mkdtemp()
        browser_manager = BrowserSessionManager(self.config, optimal_browsers)
        
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
                        print(f"📈 Progress: {completed}/{total_files} ({progress:.1f}%) | Avg: {avg_time:.1f}s/file")
                    except Exception as e:
                        failed_files.append(html_file)
                        print(f"❌ Failed: {os.path.basename(html_file)} - {str(e)[:80]}...")
            
            # Sort results by topic number
            pdf_results.sort(key=lambda x: x['topic_number'])
            
            self._create_combined_pdf(pdf_results, output_path)
            
            total_processing_time = time.time() - start_time
            success_count = len(pdf_results)
            fail_count = len(failed_files)
            
            print(f"\n📋 Processing Summary:")
            print(f"   ✅ Successful: {success_count}/{total_files}")
            print(f"   ❌ Failed: {fail_count}/{total_files}")
            print(f"   ⏱️  Total time: {total_processing_time:.1f}s")
            if success_count > 0:
                print(f"   📊 Avg per file: {total_processing_time/success_count:.1f}s")
            
        finally:
            print("\n🧹 Cleaning up resources...")
            browser_manager.cleanup()
            shutil.rmtree(temp_dir, ignore_errors=True)
            print("✅ Cleanup completed!")
    
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
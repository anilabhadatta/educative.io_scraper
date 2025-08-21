from pypdf import PdfWriter, PdfReader, PageObject, Transformation
import io
import os
import base64
import time
from seleniumbase import Driver


def printPdfAsCdp(file_path):
    print(f"printPdfAsCdp: Getting Full page PDF data without page breaks")
    
    params = {
        "landscape": False,
        "displayHeaderFooter": False,  # Disable header/footer for continuous page
        "printBackground": True,
        "marginsType": 0,  # No margins for continuous content
        "paperWidth": 8.27,
        "paperHeight": 5,  # Very large height to accommodate all content
        "marginTop": 0,
        "marginBottom": 0,
        "marginLeft": 0,
        "marginRight": 0,
        "preferCSSPageSize": False,  # Don't respect CSS @page rules to override page breaks
        "scale": 0.8  # Scale content to fit
    }
    userDataDir = r"C:\Users\Anilabha\EducativeScraper\UserData1\ucDriver-True"
    chromeBinaryPath = r"D:\Development\educative.io_scraper\src\ChromeBinary\win\chrome-win64\chrome.exe"
    chrome_args = " --allow-running-insecure-content, --ignore-certificate-errors-spki-list,--ignore-ssl-errors"
    browser = Driver(undetectable=True, user_data_dir=userDataDir,
                                      binary_location=chromeBinaryPath, headless2=True,
                                      proxy=None, chromium_arg=chrome_args,
                                      headed=False, driver_version=116)
    try:
        browser.get(f"file:///{file_path}")
        
        # Wait for page to load completely
        time.sleep(3)
        
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
        paper_height_inches = max(paper_height_inches, 8.5)
        
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

# Main execution code
if __name__ == "__main__":
    file_path = r"D:\Development\Courses_main\aws certified solutions architect associate saa c03 exam prep-incomplete\002-setting up aws account\002-setting up aws account.html"
    output_path = r"D:\Development\Courses_main\aws certified solutions architect associate saa c03 exam prep-incomplete\002-setting up aws account\002-setting up aws account.pdf"

    # Use the new single page creation function
    createSinglePagePdf(file_path, output_path)
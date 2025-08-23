# 📄 HTML to PDF Converter

## 🎯 Purpose

The **HTML to PDF Converter** intelligently converts HTML files to PDFs with automatic content trimming:

- **🎯 Smart Detection**: Automatically finds "Next" buttons and trims content below them
- **✂️ Precise Trimming**: Removes excessive whitespace and navigation elements
- **🔄 Fallback Strategy**: Uses percentage-based trimming when smart detection fails
- **📚 Batch Processing**: Converts entire courses with parallel processing
- **📖 Bookmarks**: Creates organized PDFs with topic bookmarks

---

## ⚙️ Configuration

### 📝 **Config File Location**
```
src/Common/config.ini
```

### 🔧 **Configuration Options**

#### **PDF Settings**
```
[pdf]
trim_whitespace = true          # Enable/disable trimming
smart_trimming = true           # Use smart marker detection
fallback_trim_percentage = 0.15 # Fallback trim amount (15% from bottom)
pdf_scale = 0.8                 # PDF scaling factor
pdf_paper_width = 8.27          # Paper width in inches
min_paper_height = 8.5          # Minimum paper height
```

#### **Processing Settings**
```
[processing]
max_browser_sessions = 10       # Maximum concurrent browsers
min_browser_sessions = 1        # Minimum browsers to maintain
page_load_timeout = 1           # Page load wait time (seconds)
pdf_generation_pause = 1        # Pause between PDF generations
```

#### **Directory Settings**
```ini
[directories]
saveDirectory = "D:/Courses"   
```

---

## 🛠️ Installation

### 📋 **Prerequisites**
- Python 3.8+
- Chrome browser

### 🔽 **Install Dependencies**
```bash
pip install -r requirements.txt
```

### ⚙️ **Setup Configuration**
1. Edit `/Users/<username>/EducativeScraper/config.ini`
2. Set correct paths for course directory
3. Adjust PDF and processing settings as needed in Html2PdfConverter.py

---

## � Usage Commands

### 🎯 **Single File Conversion**
```python
from src.Utility.Html2PdfConverter import Html2PdfConverter, PDFConverterConfig

# Load configuration from config.ini
config = PDFConverterConfig(config_json)
converter = Html2PdfConverter(config)

# Convert single HTML file
converter.convert_single_file(
    file_path="path/to/file.html",
    output_path="output/file.pdf"
)
```

### 📚 **Batch Course Conversion**
```python
# Convert all courses in directory
converter.convert_multiple_courses(
    root_directory="D:/Courses",
    max_threads=5
)
```

### 🌐 **Browser Page Conversion**
```python
# Convert currently loaded browser page
converter.convert_browser_page_to_pdf(
    browser=browser_instance,
    output_path="current_page.pdf"
)
```

---

## � Required Folder Structure

```
Courses/
├── course-name-1/              # Course folder (no dashes)
│   ├── 001-topic-one/          # Topic folder (with dashes)
│   │   └── 001-topic-one.html
│   ├── 002-topic-two/
│   │   └── 002-topic-two.html
│   └── course-name-1.pdf       # Generated output
└── course-name-2/
    ├── 001-intro/
    └── 002-advanced/
```

---

## 📊 Processing Summary

The converter provides detailed statistics:

- **✅ Success/Failure counts** per course
- **🎯 Smart trimming success rate** (marker detection)
- **🔄 Fallback usage tracking** (percentage-based trimming)
- **⏱️ Processing time metrics**
- **� List of files using fallback strategy**

---

## 🔧 Key Features

### 🧠 **Smart Trimming**
- Injects hidden markers near "Next" buttons
- Uses PyMuPDF for precise text detection in PDFs
- Automatically calculates trim points based on content

### ⚡ **Performance**
- Parallel processing with multiple browser sessions
- Thread-safe PDF generation
- Automatic resource cleanup

### �️ **Flexibility**
- Configurable trimming percentages
- Adjustable browser pool sizes
- Customizable PDF scaling and dimensions

---

## 🆘 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Empty PDFs | Set `trim_whitespace = false` in config |
| Always uses fallback | Install PyMuPDF, check "Next" button exists |
| Browser errors | Update `chromeBinaryPath` in config |
| Memory issues | Reduce `max_browser_sessions` |

---

## 📄 License

MIT License - See LICENSE file for details.

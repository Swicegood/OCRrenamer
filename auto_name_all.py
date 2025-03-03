import os
import sys
import subprocess
import time
import tempfile
from datetime import datetime
import PyPDF2
from PIL import Image
import io
from openai_api import getAiGeneratedName

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

def log(message):
    """
    Helper function to print messages with timestamps
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def process_file(file_path):
    """
    Define the action to perform on each file.
    """
    log(f"Processing file: {file_path}")
    
    # Make file searchable
    processed_file = makesearchable(file_path)
    
    if processed_file is None:
        log(f"Skipping file: {file_path} because it was not processed")
        return
    
    # Make file world readable and writable
    os.chmod(processed_file, 0o666)

    # Get AI generated name
    ai_name = getAiGeneratedName(processed_file)
    
    # Add file extension
    new_filename = ai_name + os.path.splitext(processed_file)[1]
    
    # Rename file
    new_path = os.path.join(os.path.dirname(processed_file), new_filename)
    os.rename(processed_file, new_path)
    log(f"Renamed to: {new_filename}")

def makesearchable(file_path):
    """
    This function makes a PDF searchable by adding OCR text back into the PDF.
    If the file is not a PDF, it converts it to PDF first.
    """
    log(f"Making file searchable: {file_path}")
    
    # Get file extension
    ext = os.path.splitext(file_path)[1].lower()
    
    # Convert to PDF if it's an image file
    if ext in ['.jpg', '.jpeg', '.png', '.svg']:
        file_path = convert_to_pdf(file_path)
        ext = '.pdf'
    
    # Process PDF with OCR
    if ext == '.pdf':
        # First check and correct orientation
        file_path = fix_pdf_orientation(file_path)
        return ocr_pdf(file_path)
    
    # If not a supported format, return the original path
    return file_path

def convert_to_pdf(image_path):
    """
    Convert image file to PDF
    """
    log(f"Converting {image_path} to PDF")
    
    # Preserve file timestamps
    mtime_seconds = os.path.getmtime(image_path)
    time_seconds = time.time()
    
    # Create PDF path
    basename = os.path.basename(image_path)
    dir_path = os.path.dirname(image_path)
    filebase = os.path.splitext(basename)[0]
    pdf_path = os.path.join(dir_path, filebase + '.pdf')
    
    # Convert image to PDF
    image = Image.open(image_path)
    im_converted = image.convert('RGB')
    im_converted.save(pdf_path)
    
    # Restore timestamp
    os.utime(pdf_path, (time_seconds, mtime_seconds))
    
    # Remove original image file
    os.remove(image_path)
    
    log(f"Converted to PDF: {pdf_path}")
    return pdf_path

def is_already_ocrd(pdf_path, min_text_per_page=20):
    """
    Check if a PDF already has OCR text by examining text content.
    Returns True if the PDF appears to already have OCR text.
    """
    log(f"Checking if PDF already has OCR: {pdf_path}")
    
    # Method 1: Use PyPDF2 - more reliable with lower threshold
    try:
        with open(pdf_path, 'rb') as file:
            try:
                # First try PyPDF2
                import PyPDF2
                reader = PyPDF2.PdfReader(file)
                total_pages = len(reader.pages)
                
                # Only check up to 5 pages for efficiency
                pages_to_check = min(total_pages, 5)
                text_found = False
                
                for i in range(pages_to_check):
                    page = reader.pages[i]
                    text = page.extract_text() or ""
                    
                    log(f"Page {i+1} text length: {len(text)}")
                    
                    # Even a small amount of text indicates OCR
                    if len(text.strip()) > min_text_per_page:
                        text_found = True
                        break
                
                if text_found:
                    log(f"PDF appears to already have OCR text (PyPDF2 detection)")
                    return True
                
                log(f"PyPDF2 didn't find sufficient text")
            except Exception as e:
                log(f"PyPDF2 detection failed: {str(e)}")
    except Exception as e:
        log(f"Error opening PDF file: {str(e)}")
    
    # Method 2: Use pdftotext from poppler-utils
    try:
        # Reset file position or reopen
        with open(pdf_path, 'rb') as file:
            try:
                result = subprocess.run(
                    ['pdftotext', '-f', '1', '-l', '1', pdf_path, '-'],  # Just the first page
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                extracted_text = result.stdout.strip()
                log(f"pdftotext extracted {len(extracted_text)} characters")
                
                if len(extracted_text) > min_text_per_page:
                    log(f"PDF appears to have text based on pdftotext")
                    return True
                    
            except Exception as e:
                log(f"pdftotext detection failed: {str(e)}")
    except Exception as e:
        log(f"Error in pdftotext processing: {str(e)}")
    
    # Method 3: Use a simple grep for text objects in the PDF
    try:
        # Simple grep for text objects
        result = subprocess.run(
            ['grep', '-l', '/Text', pdf_path],
            check=False,  # Don't raise exception on non-zero exit
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if result.returncode == 0:
            log(f"PDF appears to have text based on grep for text objects")
            return True
            
    except Exception as e:
        log(f"Text object grep failed: {str(e)}")
    
    # If all checks fail, assume PDF needs OCR
    log(f"All text detection methods failed, assuming PDF needs OCR")
    return False

def check_page_orientation(pdf_path):
    """
    Check if a PDF has correctly oriented text or if it needs rotation.
    Returns True if orientation seems correct, False if rotation likely needed.
    This function doesn't modify the original file.
    """
    log(f"Checking page orientation for: {pdf_path}")
    
    # First check if the file has any text at all
    if not is_already_ocrd(pdf_path):
        log(f"No text detected, OCR needed regardless of orientation")
        return False  # Needs OCR regardless of orientation
    
    try:
        # Extract text from the first page using pdftotext for analysis
        try:
            text_cmd = [
                'pdftotext',
                '-f', '1',  # First page
                '-l', '3',  # First few pages
                pdf_path,
                '-'  # Output to stdout
            ]
            
            # Check orientation of extracted pages
            page_files = sorted([f for f in os.listdir(tmp_dir) if f.startswith('page')])
            rotated_pages = 0
            total_checked = 0
            
            for page_file in page_files:
                page_path = os.path.join(tmp_dir, page_file)
                
                # Run tesseract with orientation detection only (no OCR)
                result = subprocess.run(
                    [
                        'tesseract', 
                        page_path, 
                        'stdout',
                        '--psm', '0',  # Orientation and script detection only
                        '-c', 'page_separator=""'
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Parse the orientation information from stderr
                stderr = result.stderr
                rotation_info = None
                
                for line in stderr.splitlines():
                    if "Orientation:" in line:
                        rotation_info = line
                        break
                
                if rotation_info:
                    log(f"Page {page_file} orientation info: {rotation_info}")
                    # If orientation is not 0 degrees, page needs rotation
                    if "Orientation: 0" not in rotation_info:
                        rotated_pages += 1
                
                total_checked += 1
                
                # Early exit if we've already found a rotated page
                if rotated_pages > 0:
                    break
            
            # If any pages need rotation, return False (needs correction)
            if rotated_pages > 0:
                log(f"Detected {rotated_pages}/{total_checked} pages with incorrect orientation")
                return False
            
            # Try a second method: check if text extraction yields valid words
            try:
                # Extract text from the first page
                text_cmd = [
                    'pdftotext',
                    '-f', '1',  # First page
                    '-l', '1',  # First page
                    pdf_path,
                    '-'  # Output to stdout
                ]
                
                result = subprocess.run(
                    text_cmd,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                extracted_text = result.stdout.strip()
                
                # Check for common English words as a simple heuristic
                # If we can find some common words, orientation is likely correct
                common_words = ['the', 'and', 'for', 'that', 'with', 'this', 'from']
                words_found = sum(1 for word in common_words if f" {word} " in f" {extracted_text.lower()} ")
                
                log(f"Found {words_found} common words in extracted text")
                
                if words_found >= 2:
                    log(f"Text appears properly oriented based on word recognition")
                    return True
                elif len(extracted_text) < 100:
                    # Very little text, can't make a determination
                    log(f"Too little text to determine orientation quality")
                    return True  # Assume it's fine if there's very little text
                else:
                    # Substantial text but few recognizable words - likely poor orientation
                    log(f"Text may be improperly oriented (few recognizable words)")
                    return False
                    
            except Exception as e:
                log(f"Text quality check failed: {str(e)}")
                
            # Default to assuming orientation is correct if we couldn't determine otherwise
            log(f"No rotation issues detected, orientation appears correct")
            return True
            
    except Exception as e:
        log(f"Orientation check failed: {str(e)}")
        # If we can't determine orientation, assume we need OCR to be safe
        return False

def ocr_pdf(pdf_path):
    """
    Run OCR on PDF file if it doesn't already have text or if text orientation is wrong
    Returns the path to the OCR'd PDF or the original if already properly OCR'd
    """
    log(f"Evaluating PDF for OCR: {pdf_path}")
    
    # Two-step check:
    # 1. Check if PDF has any text
    has_text = is_already_ocrd(pdf_path)
    
    # 2. If it has text, check if the orientation is correct
    if has_text:
        correct_orientation = check_page_orientation(pdf_path)
        
        if correct_orientation:
            log(f"PDF already has correctly oriented text, skipping OCR: {pdf_path}")
            return pdf_path
        else:
            log(f"PDF has text but orientation appears incorrect, proceeding with OCR and rotation")
    else:
        log(f"PDF has no text, OCR needed: {pdf_path}")
    
    # Preserve file timestamps
    mtime_seconds = os.path.getmtime(pdf_path)
    time_seconds = time.time()
    
    # Create output path
    filebase = os.path.splitext(pdf_path)[0]
    ocr_path = filebase + '-OCR.pdf'
    
    # Verify input file exists
    if not os.path.exists(pdf_path):
        log(f"Error: Input file does not exist: {pdf_path}")
        return None
    
    # Run OCR command using ocrmypdf with orientation correction
    try:
        log(f"Executing ocrmypdf with auto-rotation on: {pdf_path}")
        result = subprocess.run(
            [
                'ocrmypdf',
                '--rotate-pages',     # Auto-rotate pages based on detected text orientation
                '--deskew',           # Straighten text
                '--force-ocr',        # Force OCR even if text is already present
                pdf_path, 
                ocr_path
            ], 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        log(f"OCR stdout: {result.stdout.decode()}")
        
        # Check if OCR file exists
        if os.path.exists(ocr_path):
            # Set timestamp and remove original if successful
            os.utime(ocr_path, (time_seconds, mtime_seconds))
            os.remove(pdf_path)
            log(f"OCR completed successfully: {ocr_path}")
            return ocr_path
        else:
            # If OCR file doesn't exist but command succeeded, try alternative
            log(f"OCR output file not found, trying alternative method")
            
            # Try a different ocrmypdf approach with orientation correction
            try:
                log(f"Trying ocrmypdf with redo-ocr and orientation correction")
                result = subprocess.run(
                    [
                        'ocrmypdf',
                        '--rotate-pages',
                        '--deskew',
                        '--redo-ocr',
                        pdf_path, 
                        ocr_path
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                if os.path.exists(ocr_path):
                    os.utime(ocr_path, (time_seconds, mtime_seconds))
                    os.remove(pdf_path)
                    log(f"OCR alternative method completed successfully: {ocr_path}")
                    return ocr_path
                else:
                    # Fall back to original file
                    log(f"No OCR method produced output, using original file")
                    return pdf_path
            except Exception as e:
                log(f"OCR alternative method failed: {str(e)}")
                
            # Try with tesseract directly as a final fallback for orientation issues
            try:
                log(f"Trying tesseract directly for better orientation control")
                # Create a temporary directory for page images
                import tempfile
                with tempfile.TemporaryDirectory() as tmp_dir:
                    # Extract pages as images
                    extract_cmd = [
                        'pdftoppm', 
                        '-png', 
                        pdf_path, 
                        f"{tmp_dir}/page"
                    ]
                    subprocess.run(extract_cmd, check=True)
                    
                    # Process each image with tesseract with orientation detection
                    from reportlab.lib.pagesizes import letter
                    from reportlab.pdfgen import canvas
                    import os
                    
                    # Create a new PDF
                    c = canvas.Canvas(ocr_path, pagesize=letter)
                    c.setTitle(os.path.basename(pdf_path))
                    
                    # Process each page
                    page_files = sorted([f for f in os.listdir(tmp_dir) if f.startswith('page')])
                    for page_file in page_files:
                        page_path = os.path.join(tmp_dir, page_file)
                        
                        # Run tesseract with orientation detection
                        tess_out = os.path.join(tmp_dir, f"tess_{page_file}")
                        tess_cmd = [
                            'tesseract',
                            page_path,
                            tess_out.replace('.png', ''),  # tesseract adds extension
                            '-l', 'eng',
                            '--psm', '1',  # Auto page segmentation with OSD (orientation detection)
                            'pdf'  # Output format
                        ]
                        subprocess.run(tess_cmd, check=True)
                        
                        # Add the processed page to our PDF
                        # (using the original image but with text layer from tesseract)
                        from PIL import Image
                        img = Image.open(page_path)
                        width, height = img.size
                        c.setPageSize((width, height))
                        c.drawImage(page_path, 0, 0, width, height)
                        c.showPage()
                    
                    c.save()
                    
                    if os.path.exists(ocr_path):
                        os.utime(ocr_path, (time_seconds, mtime_seconds))
                        os.remove(pdf_path)
                        log(f"Tesseract OCR completed successfully: {ocr_path}")
                        return ocr_path
            except Exception as e:
                log(f"pdf2pdfocr fallback failed: {str(e)}")
                return None
            
    except subprocess.CalledProcessError as e:
        log(f"OCR process failed: {e}")
        log(f"Error output: {e.stderr.decode()}")
        log(f"Skipping file: {pdf_path}")
        return None
    

if __name__ == "__main__":
    # Check if a directory path was provided
    if len(sys.argv) != 2:
        log("Usage: python script.py <directory_path>")
        log("Usage: python script.py <directory_path>")
        sys.exit(1)

    directory_path = sys.argv[1]

    # Verify that the provided path is a directory
    if not os.path.isdir(directory_path):
        log("The provided path is not a directory.")
        log("The provided path is not a directory.")
        sys.exit(1)

    lock_file_path = os.path.join(directory_path, 'script.lock')

    # Check if the lock file exists
    if not os.path.exists(lock_file_path):
        # Create a lock file to signal that the script is running
        with open(lock_file_path, 'w') as lock_file:
            lock_file.write("")

        # Your main script functionality goes here
        scanExists = False
        # Perform an action on each file in the directory
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                if filename.startswith("Scan") and filename.endswith(".pdf"):
                    scanExists = True
        
        if scanExists:
            for filename in os.listdir(directory_path):
                file_path = os.path.join(directory_path, filename)
                if (os.path.isfile(file_path) 
                    and not filename.startswith(".") 
                    and not file_path.endswith(".lock")):
                    process_file(file_path)
        else:
            log("No Scan...pdf file found in the directory. Doing nothing.")
            log("No Scan...pdf file found in the directory. Doing nothing.")

        # Remove the lock file when done
        os.remove(lock_file_path)
    else:
        log("The script is already running or the lock file was not properly removed.")
        log("The script is already running or the lock file was not properly removed.")
    
    



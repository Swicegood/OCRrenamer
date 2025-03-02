import os
import sys
import subprocess
import time
import subprocess
import time
from datetime import datetime
import PyPDF2
from PIL import Image
import pytesseract
from openai_api import getAiGeneratedName

def log(message):
    """
    Helper function to print messages with timestamps
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

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

def fix_pdf_orientation(pdf_path):
    """
    Detect and fix orientation issues in PDF pages that would cause OCR problems.
    Returns the path to the fixed PDF file.
    """
    log(f"Checking and fixing PDF orientation: {pdf_path}")
    
    # Preserve file timestamps
    mtime_seconds = os.path.getmtime(pdf_path)
    time_seconds = time.time()
    
    # Create output path for rotated file
    filebase = os.path.splitext(pdf_path)[0]
    rotated_path = filebase + '-rotated.pdf'
    
    try:
        # Open the PDF
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            writer = PyPDF2.PdfWriter()
            
            rotation_applied = False
            
            # Process each page
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                
                # Check if we need to extract text to determine orientation
                # Extract a small sample of text to determine orientation
                # If the text extraction doesn't work well, the page may need rotation
                extracted_text = ""
                try:
                    # Extract just a portion of text to check orientation
                    extracted_text = page.extract_text()[:100]
                except Exception as e:
                    log(f"Text extraction error: {e}")
                
                # Try different rotations if text appears to be garbled or minimal
                if len(extracted_text.strip()) < 10 or not any(c.isalpha() for c in extracted_text):
                    # Try 90 degrees rotation (most common for sideways documents)
                    page.rotate(90)
                    rotation_applied = True
                    log(f"Rotating page {page_num + 1} by 90 degrees")
                
                # Add the page to our writer (rotated or not)
                writer.add_page(page)
            
            # Only create a new file if rotations were applied
            if rotation_applied:
                # Write the rotated PDF to a temporary file
                with open(rotated_path, 'wb') as output_file:
                    writer.write(output_file)
                
                # Set the original timestamp
                os.utime(rotated_path, (time_seconds, mtime_seconds))
                
                # Return the path to the rotated file
                return rotated_path
            else:
                log("No rotation needed")
                return pdf_path
            
    except Exception as e:
        log(f"Error fixing PDF orientation: {e}")
        return pdf_path

def ocr_pdf(pdf_path):
    """
    Run OCR on PDF file using pdf2pdfocr.py
    """
    log(f"Running OCR on PDF: {pdf_path}")
    
    # Preserve file timestamps
    mtime_seconds = os.path.getmtime(pdf_path)
    time_seconds = time.time()
    
    # Create output path
    filebase = os.path.splitext(pdf_path)[0]
    ocr_path = filebase + '-OCR.pdf'
    
    # Run OCR command with orientation detection (-d option)
    try:
        result = subprocess.run(
            ['pdf2pdfocr/pdf2pdfocr.py', '-t', '-d', '-i', pdf_path], 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        log(result.stdout.decode())
        
        # Check if OCR file exists
        if os.path.exists(ocr_path):
            # Set timestamp and remove original if successful
            os.utime(ocr_path, (time_seconds, mtime_seconds))
            os.remove(pdf_path)
            return ocr_path
        else:
            # If OCR file doesn't exist but command succeeded, rename original
            os.rename(pdf_path, ocr_path)
            os.utime(ocr_path, (time_seconds, mtime_seconds))
            return ocr_path
            
    except subprocess.CalledProcessError as e:
        log(f"OCR process failed: {e}")
        log(f"Error output: {e.stderr.decode()}")
        return pdf_path
    

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
    
    



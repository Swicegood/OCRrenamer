import os
import sys
import subprocess
import time
from datetime import datetime
from PIL import Image
from openai_api import getAiGeneratedName

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

def ocr_pdf(pdf_path):
    """
    Run OCR on PDF file using ocrmypdf (which is more reliable in Docker)
    """
    log(f"Running OCR on PDF: {pdf_path}")
    
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
    
    # Run OCR command using ocrmypdf (installed through apt-get)
    try:
        log(f"Executing ocrmypdf on: {pdf_path}")
        result = subprocess.run(
            ['ocrmypdf', '--force-ocr', '--skip-text', pdf_path, ocr_path], 
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
            # If OCR file doesn't exist but command succeeded, skip the file
            log(f"OCR output file not found, trying alternative method")
            
            # Try with pdf2pdfocr as fallback
            try:
                pdf2pdfocr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf2pdfocr", "pdf2pdfocr.py")
                log(f"Trying pdf2pdfocr: {pdf2pdfocr_path}")
                
                # Create a temporary directory to handle pdf2pdfocr output
                tmp_dir = os.path.join(os.path.dirname(pdf_path), "tmp")
                os.makedirs(tmp_dir, exist_ok=True)
                
                result = subprocess.run(
                    ["python", pdf2pdfocr_path, "-i", pdf_path, "-o", ocr_path, "-v"], 
                    check=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                log(f"pdf2pdfocr stdout: {result.stdout.decode()}")
                
                if os.path.exists(ocr_path):
                    os.utime(ocr_path, (time_seconds, mtime_seconds))
                    os.remove(pdf_path)
                    log(f"pdf2pdfocr completed successfully: {ocr_path}")
                    return ocr_path
                else:
                    log(f"No OCR method produced output, using original file")
                    return pdf_path
            except Exception as e:
                log(f"pdf2pdfocr fallback failed: {str(e)}")
                return pdf_path
            
    except subprocess.CalledProcessError as e:
        log(f"OCR process failed: {e}")
        log(f"Error output: {e.stderr.decode()}")
        log(f"Continuing with original file: {pdf_path}")
        return pdf_path
    

if __name__ == "__main__":
    # Check if a directory path was provided
    if len(sys.argv) != 2:
        log("Usage: python script.py <directory_path>")
        sys.exit(1)

    directory_path = sys.argv[1]

    # Verify that the provided path is a directory
    if not os.path.isdir(directory_path):
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

        # Remove the lock file when done
        os.remove(lock_file_path)
    else:
        log("The script is already running or the lock file was not properly removed.")
    
    



#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Import all modules at the top level
import os
import sys
import subprocess
import time
import tempfile
from datetime import datetime
import io
from openai_api import getAiGeneratedName

# Try to import optional modules
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    pass

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
    This function makes a PDF searchable by adding OCR text.
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
        return fix_orientation_and_ocr(file_path)
    
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
            
            result = subprocess.run(
                text_cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            extracted_text = result.stdout.strip()
            
            # Check for common English words as a simple heuristic
            common_words = ['the', 'and', 'for', 'that', 'with', 'this', 'from', 'have', 'are', 'not']
            words_found = sum(1 for word in common_words if f" {word} " in f" {extracted_text.lower()} ")
            
            log(f"Found {words_found} common words in extracted text of length {len(extracted_text)}")
            
            # If we find more than 2 common words, text is likely properly oriented
            if words_found >= 2:
                log(f"Text appears properly oriented based on word recognition")
                return True
            
            # If text is substantial but has few common words, it might be poorly oriented
            if len(extracted_text) > 500 and words_found < 2:
                log(f"Text may be improperly oriented (substantial text but few recognizable words)")
                return False
                
        except Exception as e:
            log(f"Text quality check failed: {str(e)}")
            
        # Try a safer method to detect orientation using image-based analysis
        # This avoids the tesseract --psm 0 failure
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Extract first page as image
                extract_cmd = [
                    'pdftoppm', 
                    '-png',
                    '-f', '1',  # Start from page 1
                    '-l', '1',  # Just the first page
                    pdf_path, 
                    f"{tmp_dir}/page"
                ]
                subprocess.run(extract_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Find the page file
                page_files = [f for f in os.listdir(tmp_dir) if f.startswith('page')]
                if not page_files:
                    log("No page images extracted, can't check orientation")
                    return False
                    
                page_path = os.path.join(tmp_dir, page_files[0])
                
                # Use tesseract with a more reliable mode
                # PSM 1 = Automatic page segmentation with OSD
                # PSM 3 = Fully automatic page segmentation, but no OSD (more reliable)
                result = subprocess.run(
                    [
                        'tesseract', 
                        page_path, 
                        'stdout',
                        '--psm', '3',  # Fully automatic page segmentation
                        '-l', 'eng'
                    ],
                    check=False,  # Don't fail on non-zero exit
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Check the quality of the output
                ocr_text = result.stdout.strip()
                common_words = ['the', 'and', 'for', 'that', 'with', 'this', 'from', 'have', 'are', 'not']
                words_found = sum(1 for word in common_words if f" {word} " in f" {ocr_text.lower()} ")
                
                log(f"OCR found {words_found} common words in first page")
                
                # If we find more than 1 common word, assume orientation is good
                if words_found > 1:
                    log(f"Page orientation appears correct based on OCR")
                    return True
                elif len(ocr_text) < 50:
                    # Very little text detected
                    log(f"Too little OCR text to determine orientation")
                    return True  # Assume it's fine if there's very little text
                else:
                    # Text detected but few common words - might need rotation
                    log(f"Page may need rotation (OCR found text but few common words)")
                    return False
                
        except Exception as e:
            log(f"Image-based orientation check failed: {str(e)}")
            
        # If text was found earlier but orientation is unclear, lean toward processing it
        log(f"Orientation check inconclusive but text exists, assuming needs OCR")
        return False
            
    except Exception as e:
        log(f"Orientation check failed: {str(e)}")
        # If we can't determine orientation, assume we need OCR to be safe
        return False

def fix_pdf_orientation(pdf_path):
    """
    Check if PDF needs rotation and fix orientation if needed.
    Returns the path to the fixed PDF or the original path if no rotation was needed.
    """
    log(f"Checking if PDF needs orientation correction: {pdf_path}")
    
    # Check if orientation needs fixing
    if check_page_orientation(pdf_path):
        log(f"PDF orientation appears correct, no rotation needed: {pdf_path}")
        return pdf_path
        
    log(f"PDF orientation needs correction, applying rotation: {pdf_path}")
    
    # Create output path for rotated file
    filebase = os.path.splitext(pdf_path)[0]
    rotated_path = filebase + '-rotated.pdf'
    
    # Preserve file timestamps
    mtime_seconds = os.path.getmtime(pdf_path)
    time_seconds = time.time()
    
    try:
        # Try using pdftk first (more reliable for PDF manipulation)
        try:
            log(f"Attempting rotation with pdftk")
            # First determine orientation using pdftotext and tesseract
            rotation_angle = 0
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Extract first page as image
                extract_cmd = [
                    'pdftoppm',
                    '-png',
                    '-f', '1',  # First page
                    '-l', '1',  # First page
                    '-r', '150',  # Resolution
                    pdf_path,
                    f"{tmp_dir}/page"
                ]
                subprocess.run(extract_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Find the page file
                page_files = [f for f in os.listdir(tmp_dir) if f.startswith('page')]
                if page_files:
                    page_path = os.path.join(tmp_dir, page_files[0])
                    # Use tesseract to detect orientation
                    result = subprocess.run(
                        [
                            'tesseract',
                            page_path,
                            'stdout',
                            '--psm', '0',  # Orientation and script detection only
                        ],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # Parse orientation from tesseract output
                    for line in result.stderr.splitlines():
                        if "Orientation in degrees:" in line:
                            try:
                                rotation_angle = int(line.split(":")[1].strip())
                                break
                            except:
                                pass
            
            if rotation_angle != 0:
                # Use pdftk to rotate the PDF
                rotate_cmd = [
                    'pdftk',
                    pdf_path,
                    'rotate',
                    f'{rotation_angle}east',  # east for clockwise rotation
                    'output',
                    rotated_path
                ]
                subprocess.run(rotate_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Validate the rotated PDF
                if validate_pdf(rotated_path):
                    os.utime(rotated_path, (time_seconds, mtime_seconds))
                    log(f"Rotation successful with pdftk: {rotated_path}")
                    return rotated_path
                else:
                    log(f"Pdftk rotation produced invalid PDF, trying alternative method")
                    if os.path.exists(rotated_path):
                        os.remove(rotated_path)
        except Exception as e:
            log(f"Pdftk rotation failed: {str(e)}")
        
        # If pdftk fails, try qpdf (another reliable PDF tool)
        try:
            log(f"Attempting rotation with qpdf")
            rotate_cmd = [
                'qpdf',
                '--rotate=+90',  # Try 90-degree rotation
                pdf_path,
                rotated_path
            ]
            subprocess.run(rotate_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Validate the rotated PDF
            if validate_pdf(rotated_path):
                os.utime(rotated_path, (time_seconds, mtime_seconds))
                log(f"Rotation successful with qpdf: {rotated_path}")
                return rotated_path
            else:
                log(f"Qpdf rotation produced invalid PDF")
                if os.path.exists(rotated_path):
                    os.remove(rotated_path)
        except Exception as e:
            log(f"Qpdf rotation failed: {str(e)}")
        
        # If all else fails, try using ocrmypdf just for rotation
        try:
            log(f"Attempting rotation with ocrmypdf")
            result = subprocess.run(
                [
                    'ocrmypdf',
                    '--rotate-pages',
                    '--skip-text',  # Don't do OCR, just rotation
                    '--jobs', '1',
                    pdf_path,
                    rotated_path
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Validate the rotated PDF
            if validate_pdf(rotated_path):
                os.utime(rotated_path, (time_seconds, mtime_seconds))
                log(f"Rotation successful with ocrmypdf: {rotated_path}")
                return rotated_path
            else:
                log(f"Ocrmypdf rotation produced invalid PDF")
                if os.path.exists(rotated_path):
                    os.remove(rotated_path)
        except Exception as e:
            log(f"Ocrmypdf rotation failed: {str(e)}")
        
        # If all rotation attempts failed, return original
        log(f"All rotation methods failed, using original: {pdf_path}")
        return pdf_path
            
    except Exception as e:
        log(f"Error in rotation process: {str(e)}")
        # Clean up any failed output
        if os.path.exists(rotated_path):
            try:
                os.remove(rotated_path)
            except:
                pass
        log(f"Continuing with original file: {pdf_path}")
        return pdf_path

def validate_pdf(pdf_path):
    """
    Validate that a PDF file exists and can be opened.
    Returns True if valid, False otherwise.
    """
    if not os.path.exists(pdf_path):
        log(f"PDF file does not exist: {pdf_path}")
        return False
        
    try:
        with open(pdf_path, 'rb') as f:
            try:
                reader = PyPDF2.PdfReader(f)
                num_pages = len(reader.pages)
                if num_pages == 0:
                    log(f"PDF has no pages: {pdf_path}")
                    return False
                log(f"PDF validation successful: {num_pages} pages")
                return True
            except Exception as e:
                log(f"Error reading PDF: {str(e)}")
                return False
    except Exception as e:
        log(f"Error opening PDF: {str(e)}")
        return False

def try_rotation_angle(pdf_path, angle, output_path):
    """
    Try rotating a PDF by a specific angle.
    Returns True if rotation was successful and produced valid PDF.
    """
    # Convert angle to pdftk rotation letter
    rotation_map = {
        90: 'east',   # East = 90 degrees
        180: 'south',  # South = 180 degrees
        270: 'west'   # West = 270 degrees
    }
    
    if angle not in rotation_map:
        log(f"Invalid rotation angle: {angle}")
        return False
        
    rotation_letter = rotation_map[angle]
    
    try:
        # Use correct pdftk syntax for rotation
        rotate_cmd = [
            'pdftk',
            pdf_path,
            'cat',
            f'1-end{rotation_letter}',  # Correct syntax: e.g., '1-endE' for 90 degrees
            'output',
            output_path
        ]
        result = subprocess.run(rotate_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            log(f"Rotate failed with return code {result.returncode}")
            log(f"Rotate stdout: {result.stdout}")
            log(f"Rotate stderr: {result.stderr}")
            return False
        
        # Validate the rotated PDF
        if validate_pdf(output_path):
            return True
        else:
            if os.path.exists(output_path):
                os.remove(output_path)
            return False
            
    except Exception as e:
        log(f"Rotation by {angle} degrees failed: {str(e)}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False

def fix_orientation_and_ocr(pdf_path):
    """
    Iteratively fix orientation and OCR until we get good text.
    Returns the path to the final processed PDF.
    """
    log(f"Starting orientation and OCR process for: {pdf_path}")
    original_path = pdf_path  # Keep track of the original file path
    
    # If this is already a rotated file, skip orientation check and go straight to OCR
    if '-rotated' in pdf_path:
        log(f"Processing already rotated file, proceeding directly to OCR")
        filebase = os.path.splitext(pdf_path)[0]
        ocr_path = filebase + '-ocr.pdf'
        
        try:
            log(f"Running OCR on rotated file")
            result = subprocess.run(
                [
                    'ocrmypdf',
                    '--deskew',
                    '--force-ocr',
                    '--jobs', '1',
                    '--output-type', 'pdf',
                    '--skip-big', '0',
                    pdf_path,
                    ocr_path
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                log(f"OCR failed with return code {result.returncode}")
                log(f"OCR stdout: {result.stdout}")
                log(f"OCR stderr: {result.stderr}")
            elif os.path.exists(ocr_path) and validate_pdf(ocr_path):
                # Check if the OCR'd text is good
                has_text = is_already_ocrd(ocr_path)
                if has_text:
                    correct_orientation = check_page_orientation(ocr_path)
                    if correct_orientation:
                        log(f"Successfully OCR'd rotated file with good text")
                        # Clean up all previous files including original
                        if current_path != original_path and os.path.exists(current_path):
                            os.remove(current_path)
                        if os.path.exists(original_path):
                            log(f"Cleaning up original file: {original_path}")
                            os.remove(original_path)
                        return ocr_path
                
                log(f"OCR'd text quality not good, will need further processing")
            else:
                log(f"OCR failed to produce valid PDF")
                if os.path.exists(ocr_path):
                    os.remove(ocr_path)
        except Exception as e:
            log(f"OCR failed: {str(e)}")
            if os.path.exists(ocr_path):
                os.remove(ocr_path)
        
        # If we get here, OCR failed or produced bad text
        return pdf_path
    
    # For original files, check if they already have good text
    has_text = is_already_ocrd(pdf_path)
    if has_text:
        correct_orientation = check_page_orientation(pdf_path)
        if correct_orientation:
            log(f"Original file has good text and orientation")
            return pdf_path
    
    # Keep track of attempts to avoid infinite loops
    max_attempts = 4  # Maximum number of rotation attempts
    attempts = 0
    current_path = pdf_path
    
    while attempts < max_attempts:
        attempts += 1
        log(f"Attempt {attempts}: Trying rotation and OCR")
        
        # Create paths for this attempt
        filebase = os.path.splitext(current_path)[0]
        rotated_path = f"{filebase}-rot{attempts}.pdf"
        ocr_path = f"{filebase}-rot{attempts}-ocr.pdf"
        
        # Try different rotation angles
        rotation_successful = False
        for angle in [90, 180, 270]:
            if try_rotation_angle(current_path, angle, rotated_path):
                rotation_successful = True
                log(f"Successfully rotated by {angle} degrees")
                break
        
        if not rotation_successful:
            log(f"All rotation angles failed on attempt {attempts}")
            continue  # Try next attempt
        
        # After rotation, immediately OCR without checking for text
        try:
            log(f"Running OCR on rotated file (attempt {attempts})")
            result = subprocess.run(
                [
                    'ocrmypdf',
                    '--deskew',
                    '--force-ocr',
                    '--jobs', '1',
                    '--output-type', 'pdf',
                    '--skip-big', '0',
                    rotated_path,
                    ocr_path
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                log(f"OCR failed with return code {result.returncode}")
                log(f"OCR stdout: {result.stdout}")
                log(f"OCR stderr: {result.stderr}")
                if os.path.exists(ocr_path):
                    os.remove(ocr_path)
                if os.path.exists(rotated_path):
                    os.remove(rotated_path)
                continue  # Try next attempt
            
            # Clean up the intermediate rotated file
            if os.path.exists(rotated_path):
                os.remove(rotated_path)
            
            # Check if OCR was successful and produced valid PDF
            if os.path.exists(ocr_path) and validate_pdf(ocr_path):
                # Check if the OCR'd text is good
                has_text = is_already_ocrd(ocr_path)
                if has_text:
                    correct_orientation = check_page_orientation(ocr_path)
                    if correct_orientation:
                        log(f"Found good text orientation after rotation and OCR")
                        # Clean up all previous files including original
                        if current_path != original_path and os.path.exists(current_path):
                            os.remove(current_path)
                        if os.path.exists(original_path):
                            log(f"Cleaning up original file: {original_path}")
                            os.remove(original_path)
                        return ocr_path
                
                # If text isn't good, continue to next rotation attempt
                log(f"OCR successful but text quality not good, trying next rotation")
                # Clean up previous file if it's not the original
                if current_path != original_path and os.path.exists(current_path):
                    os.remove(current_path)
                current_path = ocr_path
            else:
                log(f"OCR failed to produce valid PDF")
                if os.path.exists(ocr_path):
                    os.remove(ocr_path)
                continue  # Try next attempt
            
        except Exception as e:
            log(f"OCR failed on attempt {attempts}: {str(e)}")
            if os.path.exists(ocr_path):
                os.remove(ocr_path)
            if os.path.exists(rotated_path):
                os.remove(rotated_path)
            continue  # Try next attempt
    
    log(f"Reached maximum rotation attempts ({max_attempts})")
    return current_path


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

        # Remove the lock file when done
        os.remove(lock_file_path)
    else:
        log("The script is already running or the lock file was not properly removed.")
    
    



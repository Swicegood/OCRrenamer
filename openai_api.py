import time
from cache import get_cached_filename, cache_md5sum, get_md5sum
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

def truncate_text(text, max_chars=4000):
    """
    Truncate text to a reasonable size, trying to break at paragraph or sentence.
    """
    if not text or len(text) <= max_chars:
        return text
        
    # Try to find a paragraph break near the limit
    truncated = text[:max_chars]
    last_para = truncated.rfind('\n\n')
    if last_para > max_chars // 2:
        return truncated[:last_para].strip()
        
    # If no good paragraph break, try sentence break
    last_sentence = max(
        truncated.rfind('. '),
        truncated.rfind('.\n'),
        truncated.rfind('! '),
        truncated.rfind('?\n')
    )
    if last_sentence > max_chars // 2:
        return truncated[:last_sentence + 1].strip()
        
    # If no good breaks found, just truncate at word boundary
    last_space = truncated.rfind(' ')
    if last_space > max_chars // 2:
        return truncated[:last_space].strip()
        
    return truncated.strip()

def get_name_from_text(text_content):
    """
    Get a filename suggestion using chat completion based on text content.
    Much more efficient than using the assistants API with file uploads.
    """
    try:
        # Truncate text to avoid context length issues
        truncated_text = truncate_text(text_content)
        
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a file naming assistant. Generate a descriptive filename based on the content provided. Use only alphanumeric characters and underscores. Do not include spaces or special characters. Do not include any explanation, just output the filename without extension."},
                {"role": "user", "content": truncated_text}
            ],
            max_tokens=50,  # We only need a short response
            temperature=0.7  # Some creativity but not too random
        )
        
        filename = completion.choices[0].message.content.strip()
        print("Generated filename:", filename)
        return filename
    except Exception as e:
        print(f"Error generating filename: {str(e)}")
        return f"file_{int(time.time())}"

def extract_text_from_pdf(pdf_path):
    """
    Extract text content from a PDF using pdftotext.
    Returns the extracted text or None if extraction fails.
    """
    try:
        import subprocess
        
        # First try to extract just the first few pages
        try:
            result = subprocess.run(
                ['pdftotext', '-f', '1', '-l', '3', pdf_path, '-'],  # First 3 pages
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            text = result.stdout.strip()
            if text and len(text) > 100:  # If we got enough text from first pages
                return text
        except Exception as first_try_error:
            print(f"First attempt at text extraction failed: {str(first_try_error)}")
        
        # If first attempt didn't get enough text, try whole document
        result = subprocess.run(
            ['pdftotext', pdf_path, '-'],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
        return None

def getAiGeneratedName(file_path):
    """
    Get an AI-generated name for a file based on its content.
    Now uses text extraction and chat completion instead of assistants API.
    """
    md5sum = get_md5sum(file_path)
    cached = get_cached_filename(md5sum)
    if cached:
        print("Using cached name:", cached)
        return cached

    # Extract text from PDF
    text_content = extract_text_from_pdf(file_path)
    
    if not text_content:
        # If text extraction fails, use a timestamp-based name
        fallback_name = f"file_{int(time.time())}"
        print(f"Text extraction failed, using fallback name: {fallback_name}")
        cache_md5sum(file_path, fallback_name)
        return fallback_name
    
    # Get name suggestion from text content
    filename = get_name_from_text(text_content)
    
    # Cache the result
    cache_md5sum(file_path, filename)
    return filename

if __name__ == "__main__":
    generated_name = getAiGeneratedName('/mnt/y/My Drive/Brother (1)/Scan2023-10-21_130607.pdf')
    print("Generated name:", generated_name)

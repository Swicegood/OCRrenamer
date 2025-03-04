import time
from cache import get_cached_filename, cache_md5sum, get_md5sum
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

def get_name_from_text(text_content):
    """
    Get a filename suggestion using chat completion based on text content.
    Much more efficient than using the assistants API with file uploads.
    """
    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a file naming assistant. Generate a descriptive filename based on the content provided. Use only alphanumeric characters and underscores. Do not include spaces or special characters. Do not include any explanation, just output the filename without extension."},
                {"role": "user", "content": text_content}
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

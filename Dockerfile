FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    imagemagick \
    poppler-utils \
    poppler-data \
    tesseract-ocr \
    tesseract-ocr-eng \
    ghostscript \
    pdftk-java \
    qpdf \
    build-essential \
    git \
    ocrmypdf \
    unpaper \
    python3-pil \
    python3-pikepdf \
    python3-reportlab \
    python3-psutil \
    python3-bs4 \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir PyPDF2

# Clone pdf2pdfocr repository (needed for OCR functionality)
RUN git clone https://github.com/LeoFCardoso/pdf2pdfocr.git && \
    cd pdf2pdfocr && \
    pip install -r requirements.txt && \
    cd .. && \
    chmod -R 755 /app/pdf2pdfocr

# Copy application files
COPY auto_name_all.py openai_api.py cache.py ./

# Create an empty cache file if it doesn't exist
RUN touch cache.txt && chmod 666 cache.txt

# Create a directory for files to be processed
RUN mkdir -p /data

# Make sure the data directory is writable
RUN chmod 777 /data

# Fix for ImageMagick PDF policy
RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
    sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml; \
fi

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app:/app/pdf2pdfocr:${PATH}"
ENV PYTHONIOENCODING=utf-8

# Run the application
ENTRYPOINT ["python", "auto_name_all.py", "/data"]

# Default command (can be overridden)
CMD [] 
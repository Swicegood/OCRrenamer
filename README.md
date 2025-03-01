# GPT File Namer

This application uses AI to automatically rename files (especially PDFs) based on their content. It can process image files (converting them to PDF) and make PDFs searchable with OCR before generating an appropriate name.

## Dockerized Application

The application has been containerized for easy deployment and use.

### Prerequisites

- Docker
- Docker Compose
- OpenAI API key

### Setup

1. Clone this repository
2. Set your OpenAI API key as an environment variable:
   ```
   export OPENAI_API_KEY=your_openai_api_key
   ```

3. Create an input directory for files (or use the default `./input`):
   ```
   mkdir input
   ```

### Usage

1. Place the files you want to rename in the input directory.

2. Run the application using Docker Compose:
   ```
   docker-compose up
   ```

3. Alternatively, specify a custom input directory:
   ```
   INPUT_DIR=/path/to/your/files docker-compose up
   ```

4. The application will process all files in the input directory, making them searchable with OCR if needed, and rename them based on AI-generated names.

5. Renamed files will remain in the same input directory.

### Cache

The application maintains a cache of file checksums and their corresponding AI-generated names to avoid reprocessing the same files. The cache is stored in `cache.txt` and is persisted as a volume in the Docker container.

## Manual Build and Run

If you prefer to build and run the Docker container directly:

1. Build the Docker image:
   ```
   docker build -t gptfilenamer .
   ```

2. Run the container:
   ```
   docker run -e OPENAI_API_KEY=$OPENAI_API_KEY -v $(pwd)/cache.txt:/app/cache.txt -v /path/to/your/files:/data gptfilenamer
   ```

## Notes

- The application requires files starting with "Scan" and ending with ".pdf" to be present in the input directory to trigger processing.
- The application creates a lock file to prevent multiple instances from running simultaneously. 
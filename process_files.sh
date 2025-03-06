#!/bin/bash

# Configuration
RCLONE_CONFIG="/boot/config/plugins/rclone/.rclone.conf"
SOURCE_DIR="remote:Brother"  # Remote directory containing files to process
COMPLETE_DIR="remote:Complete"  # Remote directory for completed files
CACHE_FILE="$(pwd)/cache.txt"  # Path to cache file
#OPENAI_API_KEY="your_api_key_here"  # OpenAI API key

# Function to check if Docker command was successful
check_docker_success() {
    local exit_code=$1
    local temp_dir=$2
    local timestamp_file=$3
    
    if [ $exit_code -eq 0 ]; then
        # Check if any files were created/modified in the temp directory
        if [ -n "$(find "$temp_dir" -type f -newer "$timestamp_file")" ]; then
            return 0  # Success
        fi
    fi
    return 1  # Failure
}

# List files in remote directory
echo "Listing files in remote directory..."
remote_files=$(rclone --config "$RCLONE_CONFIG" ls "$SOURCE_DIR")

# Process each file from the remote listing
while IFS= read -r line; do
    # Extract filename from rclone ls output (removes size and spaces)
    filename=$(echo "$line" | sed 's/^[0-9]* //g')
    [ -z "$filename" ] && continue  # Skip empty lines
    
    # Skip hidden files
    [[ "$filename" == .* ]] && continue
    
    echo "Processing: $filename"
    
    # Create temporary directory name based on file name
    temp_dir="/tmp/gptfilenamer_$(basename "$filename")"
    echo "Creating temporary directory: $temp_dir"
    
    # Create temporary directory
    mkdir -p "$temp_dir"
    
    # Create a timestamp file in system temp directory
    timestamp_file=$(mktemp)
    touch "$timestamp_file"
    
    # Copy file from remote to temporary directory
    echo "Copying file from remote..."
    rclone --config "$RCLONE_CONFIG" copy "$SOURCE_DIR/$filename" "$temp_dir/"
    
    if [ $? -ne 0 ]; then
        echo "Failed to copy file from remote"
        rm -rf "$temp_dir"
        rm -f "$timestamp_file"
        continue
    fi
    
    # Run Docker command with the temporary directory
    echo "Running Docker container for: $filename"
    docker run -it --rm \
        -e OPENAI_API_KEY="$OPENAI_API_KEY" \
        -v "$CACHE_FILE:/app/cache.txt" \
        -v "$temp_dir:/data" \
        --name gptfilenamer \
        jagadguru/gptfilenamer
    
    docker_exit=$?
    
    # Check if processing was successful
    if check_docker_success $docker_exit "$temp_dir" "$timestamp_file"; then
        echo "Processing successful for: $filename"
        
        # Copy processed files to remote complete directory
        echo "Copying processed files to remote..."
        find "$temp_dir" -type f -newer "$timestamp_file" -exec rclone --config "$RCLONE_CONFIG" copy {} "$COMPLETE_DIR/" \;
        
        # Remove original file from remote only if processing was successful
        echo "Removing original file from remote..."
        rclone --config "$RCLONE_CONFIG" delete "$SOURCE_DIR/$filename"
        
        echo "Moved processed file to: $COMPLETE_DIR"
    else
        echo "Processing failed for: $filename"
        echo "Copying Original file to remote complete directory..."
        rclone --config "$RCLONE_CONFIG" copy "$SOURCE_DIR/$filename" "$COMPLETE_DIR/"
    fi
    
    # Clean up temporary files
    rm -f "$timestamp_file"
    rm -rf "$temp_dir"
    echo "Cleaned up temporary directory: $temp_dir"
    echo "----------------------------------------"
done <<< "$remote_files"

echo "All files processed" 
import os
import sys
from datetime import datetime
from openai_api import getAiGeneratedName

def process_file(file_path):
    """
    Define the action to perform on each file.
    """
    print(f"Processing file: {file_path}")
    # Add your file processing code here
    basename = os.path.basename(file_path)
    filename = getAiGeneratedName(file_path)+"."+basename.split('.')[1]
    os.rename(file_path, os.path.join(os.path.dirname(file_path), filename))


if __name__ == "__main__":
    # Check if a directory path was provided
    if len(sys.argv) != 2:
        print("Usage: python script.py <directory_path>")
        sys.exit(1)

    directory_path = sys.argv[1]

    # Verify that the provided path is a directory
    if not os.path.isdir(directory_path):
        print("The provided path is not a directory.")
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
            print("No Scan...pdf file found in the directory. Doing nothing.")

        # Remove the lock file when done
        os.remove(lock_file_path)
    else:
        print("The script is already running or the lock file was not properly removed.")
    
    



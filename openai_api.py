import time
from cache import get_cached_filename, cache_md5sum, get_md5sum
from openai import OpenAI

# This client will use v2 of the Assistants API by default.
client = OpenAI(default_headers={"OpenAI-Beta": "assistants=v2"})

assistant_id = "asst_x12T5oG4veSRKIhgeJkw7303"

def upload_file(file_path):
    """
    This function uploads a file to OpenAI and returns the file ID.
    """
    with open(file_path, 'rb') as file:
        response = client.files.create(file=file, purpose='assistants')
    return response.id

def delete_file(file_id):
    """
    This function deletes a file from the user's file library.
    Deleting a file from the library removes it from all v1 and v2 references.
    """
    response = client.files.delete(file_id)
    return response

def list_files():
    """
    This function lists all files in the user's library.
    """
    response = client.files.list()
    return response.data

def create_vector_store_and_ingest(file_id):
    """
    In v2, we attach files to the 'file_search' tool by creating a vector store
    that references the files directly with the file_ids parameter. Since the
    creation is asynchronous, we'll poll until the vector store is 'completed'
    or 'failed'.
    """
    # 1) Create a new vector store, inserting the file_id during creation:
    vs = client.beta.vector_stores.create(
        file_ids=[file_id]
    )

    # 2) Poll until ingestion is done
    while True:
        polled_vs = client.beta.vector_stores.retrieve(
            vs.id
        )
        if polled_vs.status in ["completed", "failed"]:
            if polled_vs.status == "failed":
                raise Exception("File ingestion failed.")
            break
        time.sleep(2)

    return vs.id

def create_assistant(vector_store_id=None):
    """
    In v2, we create an assistant using 'tools' plus 'tool_resources'.
    We now use 'file_search' instead of 'retrieval'.
    If we want to associate a vector store at creation time, provide it in tool_resources.
    """
    tools = [{"type": "file_search"}]  # previously 'retrieval'
    # Optionally attach the vector store to the assistant:
    if vector_store_id is not None:
        tool_resources = {
            "file_search": {
                "vector_store_ids": [vector_store_id]
            }
        }
    else:
        tool_resources = {}

    assistant = client.beta.assistants.create(
        name="PDF File Namer (v2)",
        instructions=(
            "You are a personal assistant. Look at PDF files and name them accordingly. "
            "You only communicate by filenames. You do not output any other text."
        ),
        tools=tools,
        tool_resources=tool_resources,
        model="gpt-4o"
    )
    return assistant

def create_thread(assistant_id):
    """
    Threads in v2 can also have 'tools' and 'tool_resources'; if the thread needs
    direct access to a vector store or code interpreter tools, you can attach them here.
    """
    thread = client.beta.threads.create(
    )

    # Attach a user message. Note that in v2, if you need to attach files directly
    # to this message, you would do so via the 'attachments' parameter.
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="I need a good name for this PDF file. You should only output the name without spaces and with underscores and not any other text. Do not output any illegal characters."
    )

    # Create a run
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
        instructions="Please address the user as Jagadguru. The user has a premium account."
    )

    # Wait for the run to finish
    while True:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run.status in ["completed", "failed"]:
            if run.status == "failed":
                raise Exception(f"Run failed: {run.error}")
            break
        time.sleep(5)

    # Fetch messages from the thread
    messages = client.beta.threads.messages.list(
        thread_id=thread.id
    )
    return messages

def print_messages(messages):
    """
    Helper to print out message text content.
    """
    for message in messages:
        for content in message.content:
            print(content.text.value)

def test_poetic_completion():
    """
    Example function not changed significantly for v2 – simple chat completion usage remains the same.
    """
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a poetic assistant, skilled in explaining programming concepts with creative flair."},
            {"role": "user", "content": "Compose a poem that explains the concept of recursion in programming."}
        ]
    )
    print(completion.choices[0].message)

def getAiGeneratedName(file_path):
    """
    Main function:
    1) Check if we have a cached name for this file based on its md5.
    2) If not, upload the file, create a vector store, ingest the file into that store.
    3) Create an assistant referencing that vector store.
    4) Create a thread, run it, fetch the AI's PDF name recommendation.
    5) Remove the vector store reference if desired (cleanup).
    6) Cache the name under the file's md5, and return it.
    """

    md5sum = get_md5sum(file_path)
    cached = get_cached_filename(md5sum)
    if cached:
        print(cached)
        return cached

    # Step 1: Upload file so it's in user library
    file_id = upload_file(file_path)
    print("Uploaded file_id:", file_id)

    try:
        # Step 2: Create vector store & ingest file
        vs_id = create_vector_store_and_ingest(file_id)
        print("Created vector store:", vs_id)

        # Step 3: Create an assistant with reference to that vector store
        assistant = create_assistant(vector_store_id=vs_id)
        print("Assistant created (v2):", assistant.id)

        # Step 4: Create a thread and let the assistant name the PDF
        messages = create_thread(assistant.id)

        # The assistant's recommended filename will (hopefully) appear
        # in the first assistant message, or possibly a later message.
        # This is just an example picking the first message.
        # Adjust as needed based on your actual conversation flow.
        filename = None
        for msg in messages.data:
            if msg.role == "assistant":
                if msg.content and len(msg.content) > 0:
                    filename = msg.content[0].text.value
                    break

        if not filename:
            filename = f"pdf_file_{int(time.time())}"

        print("Proposed filename:", filename)

        # Step 5 (Optional): If you'd like to fully remove references in your
        # v2 data, you could remove the vector store or detach it. For example:
        # client.beta.vector_stores.delete(vs_id)

        # You can also do practice housekeeping by removing the file from
        # your library:
        delete_file(file_id)

        # Step 6: Cache for future calls
        cache_md5sum(file_path, filename)
        return filename

    except Exception as e:
        # Cleanup if something fails
        delete_file(file_id)
        raise e

if __name__ == "__main__":
    generated_name = getAiGeneratedName('/mnt/y/My Drive/Brother (1)/Scan2023-10-21_130607.pdf')
    print("Generated name:", generated_name)

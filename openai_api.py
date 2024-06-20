import time
from cache import get_cached_filename, cache_md5sum, get_md5sum
from openai import OpenAI
client = OpenAI()

assistant_id = "asst_x12T5oG4veSRKIhgeJkw7303"

def create_assistant(file_id):
    assistant = client.beta.assistants.create(
        name="PDF File Namer",
        instructions="You are a personal assistant. Look at PDF files and name them accordingly. Do not output any backslashes, forwardslashes or any other illegal characters for filenames. You only communicate by filenames. You do not output any other text",
        tools=[{"type": "retrieval"}],
        file_ids=[file_id],
        model="gpt-4-1106-preview"
    )

def create_file_in_assistant(assistant_id, file_id):
    file = client.beta.assistants.files.create(
        file_id=file_id,
        assistant_id=assistant_id
    )
    return file

def delete_file_in_assistant(assistant_id, file_id):
    file = client.beta.assistants.files.delete(
        file_id=file_id,
        assistant_id=assistant_id
    )
    return file
def create_thread(assistant_id):
    thread = client.beta.threads.create()

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="I need a good name for this PDF file. You should only output the name without spaces and with underscores and not any other text. Please do not output anything else."
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
        instructions="Please address the user as Jagadguru. The user has a premium account."
    )

    time.sleep(5)
    
    run = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )

    print(run.status)

    while run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        print(run.status)
        time.sleep(5)
    if run.status == "failed":
        raise Exception(run.error)
    if run.status == "completed":
        messages = client.beta.threads.messages.list(
        thread_id=thread.id
        )
        return messages

def print_messages(messages):
    for message in messages:
            for content in message.content:
                print(content.text.value)

def test():
    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair."},
        {"role": "user", "content": "Compose a poem that explains the concept of recursion in programming."}
    ]
    )
    print(completion.choices[0].message)
    
def upload_file(file_path):
    """
    This function uploads a file to OpenAI and returns the file ID.
    """
    with open(file_path, 'rb') as file:
        response = client.files.create(file=file, purpose='assistants')
    return response.id

def delete_file(file_id):
    """
    This function deletes a file from OpenAI using the file ID.
    """
    response = client.files.delete(file_id)
    return response

def list_files():
    """
    This function lists all files uploaded to OpenAI.
    """
    response = client.files.list()
    return response.data


def getAiGeneratedName(file_id):
    md5sum = get_md5sum(file_id)
    if get_cached_filename(md5sum):
        print(get_cached_filename(md5sum))
        return get_cached_filename(md5sum)
    id = upload_file(file_id)
    print(id)
    create_file_in_assistant(assistant_id, id)
    messages = create_thread(assistant_id)
    filename = messages.data[0].content[0].text.value
    print(filename)
    delete_file_in_assistant(assistant_id, id)
    delete_file(id)
    cache_md5sum(file_id, filename)

    return filename

if __name__ == "__main__":
    getAiGeneratedName('/mnt/y/My Drive/Brother (1)/Scan2023-10-21_130607.pdf')

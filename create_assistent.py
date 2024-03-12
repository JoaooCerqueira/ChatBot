from openai import OpenAI

OPENAI_API_KEY = "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"

client = OpenAI(api_key=OPENAI_API_KEY)


def upload_file(file_name):
    file = client.files.retrieve(file_name)
    return file


def create_assistent(file): 
    assistent = client.beta.assistants.create(
        name="Rangel Assistent",
        instructions="",
        tools=[{"type": "retrieval"},{"type": "code_interpreter"}],
        model="gpt-3.5-turbo-0125",
        file_ids=[file.id]
    )
    return assistent


file = upload_file("file-6annsLSRciUiCBmztQv5uOWO")
assistent = create_assistent(file)

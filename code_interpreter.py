from openai import OpenAI
from time import sleep
import json
from types import SimpleNamespace

def process_message_with_citations(message):
    """Extract content and annotations from the message and format citations as footnotes."""
    message_content = message.content[0].text
    annotations = (
        message_content.annotations if hasattr(message_content, "annotations") else []
    )
    citations = []

    # Iterate over the annotations and add footnotes
    for index, annotation in enumerate(annotations):
        # Replace the text with a footnote
        message_content.value = message_content.value.replace(
            annotation.text, f" [{index + 1}]"
        )
    # Add the citation to the list
        # Iterate over the annotations and add footnotes
    for index, annotation in enumerate(annotations):
        # Replace the text with a footnote
        message_content.value = message_content.value.replace(annotation.text, f' [{index}]')

        # Gather citations based on annotation attributes
        if (file_citation := getattr(annotation, 'file_citation', None)):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f'[{index}] {file_citation.quote} from {cited_file.filename}')
        elif (file_path := getattr(annotation, 'file_path', None)):
            cited_file = client.files.retrieve(file_path.file_id)
            citations.append(f'[{index}] Click <here> to download {cited_file.filename}')
            # Note: File download functionality not implemented above for brevity
        
    # Add footnotes to the end of the message content
    full_response = message_content.value + "\n\n" + "\n".join(citations)
    return full_response



OPENAI_API_KEY = "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"

client = OpenAI(api_key=OPENAI_API_KEY)

# Ask if previous run should be used.

use_run = input("Use previous run? (y/n): ")

# Yes? Load the run from the json file.

if use_run == "y":
    with open("run.json") as json_file:
        data = json.load(json_file)

    assistant = SimpleNamespace(id=data["assistant_id"])
    thread = SimpleNamespace(id=data["thread_id"])
    run = SimpleNamespace(id=data["run_id"])

# No? Create a new assistant, thread and run.

if use_run == "n":
    assistant_id = "asst_wyxEi4wVIxDKHheu8o3mu5qU"
    # create the assistant

    # assistant = client.beta.assistants.create(
    #     name="Math tutor",
    #     instructions="You are a helpfull math instructor. Write and run code to answer math questions.",
    #     tools=[{
    #         "type": "code_interpreter"
    #     }],
    #     model="gpt-3.5-turbo-1106"
    # )

    # Create the thread

    thread = client.beta.threads.create()

while True:

    user_choice = input("Do you want to ask a question? (y/n): ")
    if user_choice == "n":
        break

    # Get user question input
    user_question = input("What is your math question? ")

    # Add message to thread
    message = client.beta.threads.messages.create(
        thread_id = thread.id,
        role= "user",
        # content="Solve this problem: 3x + 11 = 14"
        content=user_question
    )

    # Create the run
    run = client.beta.threads.runs.create(
        thread_id = thread.id,
        assistant_id = assistant_id,
    )

    # Save the assistant, thread and run to a json file for later use.
    data = {
        "assistant_id": assistant_id,
        "thread_id": thread.id,
        "run_id": run.id
    }

    with open("run.json", "w") as json_file:
        json.dump(data, json_file)

    # Retrieve information about the run and wait for it to complete.
    run = client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )

    while run.status != "completed":
        sleep(2)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

        if run.status == "failed":
            print("Failed")
            break

    # Find the code interpreter step and print the output.
    # obs.: Should have a better way to do this, verifying if the step is a code interpreter step. And if it has an output.
    run_steps = client.beta.threads.runs.steps.list(
        thread_id=thread.id,
        run_id=run.id
    )

    messages = client.beta.threads.messages.list(
        thread_id=thread.id,
    )

    assistant_messages_for_run = [
        message
        for message in reversed(messages.data)
        if message.run_id == run.id and message.role == "assistant"
    ] 

    runstep_dict = {}

    for i,runstep in enumerate(list(reversed(run_steps.data))):
        print("==================== RUN STEP " + str(i+1) + " ====================")
        for key, val in runstep:
            runstep_dict[key] = val
        
        #print(runstep_dict)
        tmp_list = list(runstep_dict["step_details"])

        if runstep_dict["type"] == "message_creation":
            print("Message creation:")
            mensage_id = tmp_list[0][1].message_id
            for message in assistant_messages_for_run:
                if message.id == mensage_id:
                    message_tmp= process_message_with_citations(message)
                    print("assistant: " + message_tmp)

        elif runstep_dict["type"] == "tool_calls":
            for detail in tmp_list[0][1]:
                tool_type = detail.type

                if tool_type == "code_interpreter":
                    print("tool call id: " + detail.id)
                    print("-----------INPUT-----------")
                    print(detail.code_interpreter.input)
                    # try:
                    #     print("-----------OUTPUT-----------")
                    #     print(detail.code_interpreter.outputs[0])
                    # except:
                    #     print("No output")
        else:
            print("ERR: runstep type not recognized")
    

    # # Get the list of messages between assistant and user.
    # messages = client.beta.threads.messages.list(
    #     thread_id=thread.id
    # )


    # # Print the messages
    # for message in reversed(messages.data):
    #     print(message.role + ": "+message.content[0].text.value)
    #     print("\n")

    # # Print with code from code interpreter
    # print("\n\n")
    # print("Interpreter code: " + interpreter_code)
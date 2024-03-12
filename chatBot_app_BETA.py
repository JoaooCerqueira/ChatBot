from openai import OpenAI
import streamlit as st
import time
import os
from io import BytesIO
from PIL import Image

OPENAI_API_KEY = "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"

client = OpenAI(api_key=OPENAI_API_KEY)

model = "gtp-3.5-turbo-0125"

thread_id = ""
assistant_id = "asst_wyxEi4wVIxDKHheu8o3mu5qU"

# Initialize all the session
if "file_id_list" not in st.session_state:
    assistant_files = client.beta.assistants.files.list(
        assistant_id= assistant_id
        )
    st.session_state.file_id_list = [file.id for file in assistant_files.data]

if "stat_chat" not in st.session_state:
    st.session_state.stat_chat = False

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

# ================================================================================== #

# Set up our front end page
st.set_page_config(
    page_title="Rangel ChatBot",
    page_icon=":bar_chart:",
    #layout="wide",
    initial_sidebar_state="expanded",
)

# initialize css
with open("beta_openAI/styles.css") as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --------------------- Functions definitions -------------------------------- #
    
def upload_file(file_path):
    with open(file_path, "rb") as file:
        response = client.files.create(file=file.read(), purpose="assistants")
    return response.id

def process_message_with_citations(message):
    """Extract content and annotations from the message and format citations as footnotes."""
    #print(message)
    for message in message.content:
        if message.type == "text":
            message_content = message.text
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
                if (file_path := getattr(annotation, 'file_path', None)):
                    cited_file = client.files.retrieve(file_path.file_id)
                    cited_file_id = cited_file.id
                    output_path = "C:/Users/joao.cerqueira/Desktop/projeto - automação/beta_openAI/"+ os.path.basename(cited_file.filename)
                    write_file_to_temp_dir(cited_file_id, output_path)
                    citations.append(f'[{index}] File was been created in {output_path}')
                    
            full_response = message_content.value + "\n\n" + "\n".join(citations)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": full_response,
                    "type": "text"
                }
                )
            with st.chat_message("assistant"):
                st.markdown(full_response, unsafe_allow_html=True)
        elif message.type == "image_file":
            image_file = message.image_file.file_id
            image = client.files.content(image_file).content
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": image,
                    "type": "image"
                }
                )
            with st.chat_message("assistant"):
                st.image(image)

def display_messages(run_steps):
    runstep_dict = {}
    for i,runstep in enumerate(list(reversed(run_steps.data))):
        print("==================== RUN STEP " + str(i+1) + " ====================")
        for key, val in runstep:
            runstep_dict[key] = val      
        #print(runstep_dict)
        
        tmp_list = list(runstep_dict["step_details"])

        if runstep_dict["type"] == "message_creation":
            print("Message created")
            mensage_id = tmp_list[0][1].message_id
            for message in assistant_messages_for_run:
                if message.id == mensage_id:
                    process_message_with_citations(message)

        elif runstep_dict["type"] == "tool_calls":
            for detail in tmp_list[0][1]:
                tool_type = detail.type
                if tool_type == "code_interpreter":
                    print("Code created")
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": detail.code_interpreter.input,
                            "type": "code"
                        }
                    )
                    with st.chat_message("assistant"):
                        st.code(detail.code_interpreter.input, language='python')
        else:
            print("ERR: runstep type not recognized")


def write_file_to_temp_dir(file_id, output_path):
    file_data = client.files.content(file_id)
    file_data_bytes = file_data.read()
    with open(output_path, "wb") as file:
        file.write(file_data_bytes)

# ===================================================================================== #

# SideBar - Image 
st.sidebar.image("images/Rangel.png")
st.sidebar.divider()

# SideBar - Upload files
with st.sidebar:
    with st.expander("**Upload files**"):
        file_upload = st.file_uploader(
            "**Upload other files:**",
            key="file_upload_",
        )

        # Upload file button - store the file id
        if st.button("**Upload file**",use_container_width=True) and file_upload is not None:
            with open(f"{file_upload.name}", "wb") as f:
                f.write(file_upload.getbuffer())
            another_file_id = upload_file(f"{file_upload.name}")
            st.session_state.file_id_list.append(another_file_id)
            st.write(f"File id: {another_file_id}")
st.sidebar.divider()
# Display those file ids
if st.session_state.file_id_list:
    st.sidebar.write("**Uploaded files:**")
    assistant_files = client.beta.assistants.files.list(
        assistant_id= assistant_id
        )
    
    file_ids = ''
    for file_id in st.session_state.file_id_list:
        file = client.files.retrieve(file_id=file_id).filename
        file_ids += (f"- {file} ") + "\n"
        if file_id not in assistant_files.data:
            assistant_file = client.beta.assistants.files.create(
                assistant_id = assistant_id,
                file_id = file_id
            )
    st.sidebar.markdown(file_ids)

st.sidebar.divider()

# Button to initiate the chat session
if st.sidebar.button("**Start Chatting**"):
    if st.session_state.file_id_list:
        st.session_state.stat_chat = True
        # Create a new thread for this chat session
        chat_thread = client.beta.threads.create()
        st.session_state.thread_id = chat_thread.id
        st.write(f"Assistant id: {assistant_id}")
        st.write(f"Thread id: {chat_thread.id}")

    else:
        st.sidebar.warning("**No files found. Please upload a file first.**")

# =============================== Main interface ==================================== #
st.title("Rangel ChatBot - Beta 💻")

# Check sessions
if st.session_state.stat_chat:
    if "openai_model" not in st.session_state:
        st.session_state.openai_model = "gtp-3.5-turbo-0125"
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
            "role": "assistant", 
            "content": "Olá, em que posso ajudar?",
            "type": "text",
            }
        ]
        
    # Show existing messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["type"] == "text":
                st.markdown(message["content"])
            elif message["type"] == "code":
                st.code(message["content"], language="python")
            elif message["type"] == "image":
                st.image(message["content"])

    # Chat input for users
    if answer := st.chat_input("Escreve aqui a tua mensagem..."):
        st.session_state.messages.append(
            {
                "role": "user",
                "content": answer,
                "type": "text"
            }
        )
        with st.chat_message("user"):
            st.markdown(answer)

        # add the user's message to the thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=answer
        )

        # Create a run with additional instructions
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id,
        )

        # Show a spinner while the assistant is thinking
        with st.spinner("Waiting for the assistant to answer..."):
            while run.status != "completed":
                print(run.status)
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id = st.session_state.thread_id,
                    run_id = run.id
                )
            print(run.status)

            # Retrieve the run steps
            run_steps = client.beta.threads.runs.steps.list(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )

            # Retrieve messages added by the assistant
            messages = client.beta.threads.messages.list(
                thread_id=st.session_state.thread_id,
            )
        
            # Process and display assis messages
            assistant_messages_for_run = [
                message
                for message in reversed(messages.data)
                if message.run_id == run.id and message.role == "assistant"
            ] 

            # Display the run steps
            display_messages(run_steps)

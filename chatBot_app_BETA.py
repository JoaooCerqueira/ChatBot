from openai import OpenAI
import streamlit as st

from utils.utils import (
    EventHandler,
    update_chat_history,
    upload_chat_history,
    upload_file,
)

# =============================== Global variables ================================= #

OPENAI_API_KEY = "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"

assistant_id = "asst_Mt4yGoyIFPK7bEvms5pa6qlR"

# Initialize all the session
if "client" not in st.session_state:
    st.session_state.client = OpenAI(api_key=OPENAI_API_KEY)


if "error" not in st.session_state:
    st.session_state.error = ""


if "file_id_list" not in st.session_state:
    assistant_files = st.session_state.client.beta.assistants.files.list(
        assistant_id= assistant_id
        )
    st.session_state.file_id_list = [file.id for file in assistant_files.data]


if "stat_chat" not in st.session_state:
    st.session_state.stat_chat = False


if "thread_id" not in st.session_state:
    st.session_state.thread_id = None


if "thread_list" not in st.session_state:
    with open("files/thread_list.txt", "r") as file:
        lines = file.readlines()

    thread_info = {}

    for line in lines:
        name, thread_id = line.strip().split(",")
        thread_info[name.strip()] = thread_id.strip()

    st.session_state.thread_list = thread_info


if "messages" not in st.session_state:
    st.session_state.messages = []

# ================================================================================== #

# Set up our front end page
st.set_page_config(
    page_title="ChatBot",
    page_icon=":bar_chart:",
    initial_sidebar_state="expanded",
)

# initialize css
with open("utils/styles.css") as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# SideBar - Image 
st.sidebar.image("images/Chatbot.png")
st.sidebar.divider()

# SideBar - Upload files
with st.sidebar:
    with st.expander("**Upload files**"):
        file_upload = st.file_uploader(
            "**Upload other files:**",
            key="file_upload"
        )

        # Upload file button - store the file id
        if st.button("**Upload file**",use_container_width=True) and file_upload is not None:
            upload_file(assistant_id, file_upload)
            st.write("**File uploaded**")

        
# Display those file ids
if st.session_state.file_id_list:
    st.sidebar.write("**Uploaded files:**")
    assistant_files = st.session_state.client.beta.assistants.files.list(
        assistant_id= assistant_id
        ) 
    file_ids = ''
    for file_id in st.session_state.file_id_list:
        file = st.session_state.client.files.retrieve(file_id=file_id).filename
        file_ids += (f"- {file} ") + "\n"

    st.sidebar.markdown(file_ids)
else:
    st.sidebar.write("**Uploaded files:**")


st.sidebar.divider()

# SideBar - Chat history
with st.sidebar:
    with st.expander("**Chat history:**"):
        for thread_list, id_thread in reversed(st.session_state.thread_list.items()):
            st.button(thread_list,use_container_width=True, on_click=upload_chat_history, args=[id_thread])

st.sidebar.divider()

# Button to initiate the chat session
if st.sidebar.button("**New chat**",use_container_width=True, key='teste'):
    if st.session_state.messages != []:
        st.session_state.messages = []

    st.session_state.messages.append(
        {
            "role": "assistant", 
            "content": "Olá, em que posso ajudar?",
            "type": "text",
        }
    )

    if st.session_state.file_id_list:
        st.session_state.stat_chat = True
        # Create a new thread for this chat session
        chat_thread = st.session_state.client.beta.threads.create()
        st.session_state.thread_id = chat_thread.id
        update_chat_history(chat_thread.id)
        st.rerun()
    else:
        st.sidebar.warning("**No files found. Please upload a file first.**")

# =============================== Main interface ==================================== #
st.title("ChatBot - v2.1 💻")
st.write("#")

# Check sessions
if st.session_state.stat_chat:
    # Show existing messages
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            with st.chat_message(message["role"],avatar="🤖"):
                if message["type"] == "text":
                    st.markdown(message["content"])
                elif message["type"] == "code":
                    st.code(message["content"], language="python")
                elif message["type"] == "image":
                    st.image(message["content"])
                elif message["type"] == "link":
                    st.markdown("Clica no link para fazer download do arquivo: ")
                    st.markdown(f'<a href="data:file/csv;base64,{message["content"]}" download="dados.csv">Download CSV</a>',unsafe_allow_html=True)
        else:
            with st.chat_message(message["role"],avatar="👤"):
                if message["type"] == "text":
                    st.markdown(message["content"])

    if st.session_state.error != "":
        st.error(st.session_state.error)


    # Chat input for users
    if answer := st.chat_input("Escreve aqui a tua mensagem..."):
        st.session_state.error = ""
        st.session_state.messages.append(
            {
                "role": "user",
                "content": answer,
                "type": "text"
            }
        )
        with st.chat_message("user",avatar="👤"):
            st.markdown(answer)

        # Add the user's message to the thread
        st.session_state.client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=answer
        )
        try:
            with st.session_state.client.beta.threads.runs.create_and_stream(
                thread_id=st.session_state.thread_id,
                assistant_id=assistant_id,
                event_handler=EventHandler(),
            ) as stream:
                stream.until_done()
        except Exception as e:
            st.write(e)
            



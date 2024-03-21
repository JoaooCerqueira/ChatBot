import streamlit as st
import datetime

def upload_file(client, file_path):
    response = client.files.create(
        file=open(file_path, "rb"),
        purpose="assistants",
        )
    return response.id

#TODO: ARRANJAR ESTA FUNCÃO, ACHO QUE NAO PRECISO DAS ANNOTATIONS
def process_message_with_citations(client, message):
    """Extract content and annotations from the message and format citations as footnotes."""
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
            # for index, annotation in enumerate(annotations):
                # Replace the text with a footnote
                # message_content.value = message_content.value.replace(annotation.text, f' [{index}]')
                # if (file_path := getattr(annotation, 'file_path', None)):
                #     cited_file = client.files.retrieve(file_path.file_id)
                #     cited_file_id = cited_file.id
                #     output_path = "C:/Users/joao.cerqueira/Desktop/projeto - automação/beta_openAI/"+ os.path.basename(cited_file.filename)
                #     write_file_to_temp_dir(cited_file_id, output_path)
                #     citations.append(f'[{index}] File was been created in {output_path}')

            full_response = message_content.value + "\n\n" + "\n".join(citations)
            st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": full_response,
                        "type": "text"
                    }
                )
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

def process_execution_steps(client, run_id):
     # Retrieve the run steps
    run_steps = client.beta.threads.runs.steps.list(
        thread_id=st.session_state.thread_id,
        run_id=run_id
    )

    # Retrieve messages added by the assistant
    messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id,
        limit=100
    )
        
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
            for message in messages:
                if message.id == mensage_id:
                    process_message_with_citations(client,message)

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
                    # if type == "display":
                    #     with st.chat_message("assistant"):
                    #         st.code(detail.code_interpreter.input, language='python')
        else:
            print("ERR: runstep type not recognized")

def process_execution_steps_stream(client, stream, messages):
    aux = None
    for event in stream:
        with open("beta_openAI/teste.txt","a") as file:
            file.write("/n"+ "----------------------------------------------------------------------------")
            file.write("/n" + str(event))
        if event.event == "thread.message.in_progress":
            with st.chat_message("user",avatar="🤖"):
                res_box = st.empty()
                report = []
            st.session_state.message_id = event.data.id

            for content in stream:
                with open("beta_openAI/teste.txt","a") as file:
                    file.write("/n" + " ----------------------------------------------------------------------------")
                    file.write("/n" + str(content))
                if content.event == 'thread.message.delta' and content.data.id == st.session_state.message_id:
                    for content_1 in content.data.delta.content:
                        if content_1.type == 'text':
                            aux = "text"
                            report.append(content_1.text.value)
                            result = "". join (report). strip()
                            res_box.markdown(f'{result}')
                        if content_1.type == 'image_file':
                            aux = "image"
                            image_file = content_1.image_file.file_id
                            print("--------------"+image_file+"-------------------")
                            image = client.files.content(image_file).content
                            messages.append(
                                {
                                    "role": "assistant",
                                    "content": image,
                                    "type": "image"
                                }
                            )   
                            with st.chat_message("user",avatar="🤖"):
                                st.image(image)
                else:
                    if aux == "text":
                        messages.append(
                        {
                            "role": "assistant",
                            "content": result,
                            "type": "text"
                        }
                    )
                    break

        elif event.event == "thread.run.step.in_progress" and event.data.type == "tool_calls":
            with st.chat_message("user",avatar="🤖"):
                res_box = st.empty()
                report = []
            st.session_state.step_id = event.data.id
            for content in stream:
                with open("beta_openAI/teste.txt","a") as file:
                    file.write("/n"+ "----------------------------------------------------------------------------")
                    file.write("/n" + str(content))
                if content.event == 'thread.run.step.delta' and content.data.id == st.session_state.step_id:
                    for content in content.data.delta.step_details.tool_calls:
                        if content.code_interpreter.input == None:
                            print("terminou")
                            report = []
                        else:
                            report.append(content.code_interpreter.input)
                            result = "". join (report). strip()
                            res_box.code(f'{result}')
                else:
                    messages.append(
                        {
                        "role": "assistant",
                        "content": result,
                        "type": "code"
                    }
                    )
                    break

def upload_chat_history(client, thread_id):
    # Retrieve messages added by the assistant
    st.session_state.messages = []
    st.session_state.thread_id = thread_id

    messages = client.beta.threads.messages.list(
        thread_id=thread_id, limit=100
    )

    reversed_messages = [
        message
        for message in reversed(messages.data)
    ] 

    user_messages = [
        message
        for message in reversed_messages
        if message.role == "user"
    ]

    # Retrieve the run and run steps
    run = client.beta.threads.runs.list(
        thread_id=st.session_state.thread_id,
        limit=100
    )
    with st.spinner("Retrieving chat history..."):
        for i,run in enumerate(reversed(run.data)):
            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": user_messages[i].content[0].text.value,
                    "type": "text"
                }
            )
            process_execution_steps(client, run.id)
    
    if st.session_state.messages == []:
        st.session_state.messages.append(
            {
                "role": "assistant", 
                "content": "Olá, em que posso ajudar?",
                "type": "text",
            }
        )

    st.session_state.stat_chat = True

def update_chat_history(thread_id):
    data_hora_atual = datetime.datetime.now()
    data_atual = data_hora_atual.date()
    hora_atual = data_hora_atual.time()

    data_atual = datetime.date.today()
    name = "chat "+ data_atual.strftime("%d-%m-%Y") + " " + hora_atual.strftime("%H:%M:%S")
    with open("beta_openAI/files/thread_list.txt", "a") as file:
        file.write("\n" + name + " , " + thread_id)
    file.close()
    st.session_state.thread_list[name] = thread_id

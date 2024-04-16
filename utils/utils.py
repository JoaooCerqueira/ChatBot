import streamlit as st
import datetime, base64
from openai import AssistantEventHandler, BadRequestError
from openai.types.beta.threads import Message, MessageDelta
from openai.types.beta.threads.runs import RunStep
from typing_extensions import override

def delete_file(assistant_id):
    file_id = st.session_state.file_id_list.pop(0)
    st.session_state.client.beta.assistants.files.delete(
        assistant_id=assistant_id,
        file_id=file_id,
    )

def upload_file(assistant_id, file_path):
    if st.session_state.file_id_list != []:
        file_id = st.session_state.file_id_list.pop(0)
        st.session_state.client.beta.assistants.files.delete(
            assistant_id=assistant_id,
            file_id=file_id,
        )
               
    response =  st.session_state.client.files.create(
        file=file_path,
        purpose="assistants",
        )

    try: 
        st.session_state.client.beta.assistants.files.create(
            assistant_id = assistant_id,
            file_id = response.id
            )
    except BadRequestError as e:
        pass
    
    st.session_state.file_id_list.append(response.id)


def process_message_with_citations(message):
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
            image =  st.session_state.client.files.content(image_file).content
            st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": image,
                        "type": "image"
                    }
                )

def process_execution_steps(run_id):
     # Retrieve the run steps
    run_steps =  st.session_state.client.beta.threads.runs.steps.list(
        thread_id=st.session_state.thread_id,
        run_id=run_id
    )

    # Retrieve messages added by the assistant
    messages =  st.session_state.client.beta.threads.messages.list(
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
                    # if type == "display":
                    #     with st.chat_message("assistant"):
                    #         st.code(detail.code_interpreter.input, language='python')
        else:
            print("ERR: runstep type not recognized")

def process_execution_steps_stream(stream, messages):
    aux = None
    for event in stream:
        with open("teste.txt","a") as file:
            file.write("/n"+ "----------------------------------------------------------------------------")
            file.write("/n" + str(event))
        if event.event == "thread.message.in_progress":
            with st.chat_message("user",avatar="🤖"):
                res_box = st.empty()
                report = []
            st.session_state.message_id = event.data.id

            for content in stream:
                with open("teste.txt","a") as file:
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
                            image =  st.session_state.client.files.content(image_file).content
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
                with open("teste.txt","a") as file:
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

def upload_chat_history(thread_id):
    # Retrieve messages added by the assistant
    st.session_state.messages = []
    st.session_state.thread_id = thread_id

    messages =  st.session_state.client.beta.threads.messages.list(
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
    run =  st.session_state.client.beta.threads.runs.list(
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
            process_execution_steps( run.id)
    
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
    with open("files/thread_list.txt", "a") as file:
        file.write("\n" + name + " , " + thread_id)
    file.close()
    st.session_state.thread_list[name] = thread_id

class EventHandler(AssistantEventHandler):
  # ------------------------------------------  Errors  ------------------------------------------
  def on_event(self, event):
      if event.data.last_error != None:
        st.session_state.error = event.data.last_error.message

  # ------------------------------------------  Message  ------------------------------------------ 
  def on_message_created(self, message: Message) -> None:
      print("\n" + "--------------------------- vai ser message ---------------------------"+ "\n")
      with st.chat_message("user",avatar="🤖"):
          st.session_state.message_chat = st.empty()
      st.session_state.report = []
      print(f"\nassistant > ", end="", flush=True)

  def on_message_delta(self, delta: MessageDelta, snapshot: Message):
      print("\n" + "-----------------------------------------------------"+ "\n")
      print(delta)
      print("\n" + "-----------------------------------------------------"+ "\n")
      if delta.content[0].text.value != None:
            st.session_state.report.append(delta.content[0].text.value)
            result = "".join(st.session_state.report).strip()
            st.session_state.message_chat.markdown(f'{result}')

      if delta.content[0].text.annotations != [] and delta.content[0].text.annotations != None:
          file_id = delta.content[0].text.annotations[0].file_path.file_id
          file = st.session_state.client.files.content(file_id).content
          print(file)
          print(type(file))
          b64_data = base64.b64encode(file).decode()
          st.session_state.messages.append(
              {
                  "role": "assistant",
                    "content": b64_data,
                    "type": "link"
              }
          ) 


  def on_message_done(self, message: Message):
     print("\n" + "--------------------------- terminou message ---------------------------"+ "\n")
     if message.content[0].text.value.count("sandbox") == 0:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": message.content[0].text.value,
                "type": "text"
                }
        ) 
     with open("teste.txt","a") as file:
            file.write("\n"+ "------------------------------- Message -------------------------------------")
            file.write("\n" + str(message.content[0].text.value))
            file.write("\n"+ "---------------------------------------------------------------------------")
  
  # ------------------------------------------  Image  ------------------------------------------ 
  @override
  def on_image_file_done(self, image_file):
      image_1file = image_file.file_id
      image =  st.session_state.client.files.content(image_1file).content
      st.session_state.messages.append(
         {
             "role": "assistant",
             "content": image,
             "type": "image"
             }
      ) 
      with st.chat_message("user",avatar="🤖"):
          st.image(image)


  # -------------------------------------------  Code  --------------------------------------------
  @override
  def on_run_step_created(self, run_step: RunStep) -> None:
     if run_step.step_details.type == "tool_calls":
        print("\n" + "--------------------------- vai ser codigo ---------------------------"+ "\n")
        st.session_state.code_id = None
        with st.chat_message("user",avatar="🤖"):
            st.session_state.code_chat = st.empty()
        st.session_state.report = []

  
  @override
  def on_tool_call_delta(self, delta, snapshot):
    if delta.type == 'code_interpreter':
      if delta.code_interpreter.input:
        st.session_state.report.append(delta.code_interpreter.input)
        result = "". join (st.session_state.report). strip()
        st.session_state.code_chat.code(f'{result}')
        print(delta.code_interpreter.input, end="", flush=True)

  @override
  def on_run_step_done(self, run_step: RunStep):
    if run_step.step_details.type == "tool_calls":
        print("\n" + "--------------------------- terminou codido ---------------------------"+ "\n")
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": run_step.step_details.tool_calls[0].code_interpreter.input,
                "type": "code"
            }
        ) 
        with open("teste.txt","a") as file:
            file.write("\n"+ "------------------------------- CODIGO ------------------------------------")
            file.write("\n" + str(run_step.step_details.tool_calls[0].code_interpreter.input))
            file.write("\n"+ "---------------------------------------------------------------------------")
       
  # -------------------------------------------  Finish  --------------------------------------------
  def on_end(self):
      
      print("\n" + "--------------------------- terminou ---------------------------"+ "\n")
      st.rerun()


#   # ------------------------------------------  Text  ------------------------------------------  
#   @override
#   def on_text_created(self, text) -> None:
#     print("\n" + "--------------------------- vai ser texto ---------------------------"+ "\n")
#     with st.chat_message("user",avatar="🤖"):
#         st.session_state.message_chat = st.empty()
#     st.session_state.report = []
#     print(f"\nassistant > ", end="", flush=True)

#   @override
#   def on_text_delta(self, delta, snapshot):
#     print("\n" + "-----------------------------------------------------"+ "\n")
#     print(delta.value, end="", flush=True)
#     print("\n" + "-----------------------------------------------------"+ "\n")
#     if delta.value != None:
#         st.session_state.report.append(delta.value)
#         result = "".join(st.session_state.report).strip()
#         st.session_state.message_chat.markdown(f'{result}')


#   @override
#   def on_text_done(self, text: Text):
#      print("\n" + "--------------------------- terminou texto ---------------------------"+ "\n")
#      st.session_state.messages.append(
#          {
#              "role": "assistant",
#              "content": text.value,
#              "type": "text"
#              }
#      )   
#      with open("teste.txt","a") as file:
#             file.write("\n"+ "------------------------------- TEXTO -------------------------------------")
#             file.write("\n" + str(text.value))
#             file.write("\n"+ "---------------------------------------------------------------------------")
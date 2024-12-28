# functions.py
import json
import requests
import os
from openai import OpenAI
from prompts import assistant_instructions

OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Init OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY, default_headers={"OpenAI-Beta": "assistants=v2"})

# Send data to webhook
# Send data to webhook
def send_data(summary):
    url = "https://hook.eu2.make.com/fb9ha2shk0o0h33plmlx6dy7ajvcd23c"
    headers = {
        "Content-Type": "application/json"
    }
    data = {"summary": summary}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print("Data sent successfully.")
        return response.text  # Return the response text instead of parsing as JSON
    else:
        print(f"Failed to send data: {response.text}")
        return None  # Return None to indicate failure

# Create or load assistant
def create_assistant(client):
    assistant_file_path = 'assistant.json'

    if os.path.exists(assistant_file_path):
        with open(assistant_file_path, 'r') as file:
            assistant_data = json.load(file)
            assistant_id = assistant_data['assistant_id']
            print("Loaded existing assistant ID.")
    else:
        vector_store = client.beta.vector_stores.create(name="Knowledge Base")

        # Upload .docx file
        docx_file_path = "knowledge.docx"
        if os.path.exists(docx_file_path):
            with open(docx_file_path, "rb") as file:
                client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=vector_store.id,
                    files=[file]
                )

        # Upload .pdf file
        json_file_path = "suburbs.json"
        if os.path.exists(json_file_path):
            with open(json_file_path, "rb") as file:
                client.beta.vector_stores.file_batches.upload_and_poll(
                    vector_store_id=vector_store.id,
                    files=[file]
                )

        assistant = client.beta.assistants.create(
            instructions=assistant_instructions,
            model="gpt-4o",
            tools=[
                {
                    "type": "file_search"
                },
                {
                    "type": "function",
                    "function": {
                        "name": "send_data",
                        "description": "Send summary data to the webhook.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "summary": {
                                    "type": "string",
                                    "description": "Summary of the conversation."
                                }
                            },
                            "required": ["summary"]
                        }
                    }
                }
            ],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store.id]
                }
            }
        )

        with open(assistant_file_path, 'w') as file:
            json.dump({'assistant_id': assistant.id}, file)
            print("Created a new assistant and saved the ID.")

        assistant_id = assistant.id

    return assistant_id
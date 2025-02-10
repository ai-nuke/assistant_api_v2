# main.py
import json
import os
import time
from flask import Flask, request, jsonify
from openai import OpenAI
import functions
import openai

app = Flask(__name__)
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
client = OpenAI(api_key=OPENAI_API_KEY, default_headers={"OpenAI-Beta": "assistants=v2"})

# Load assistant ID from file or create new one
assistant_id = functions.create_assistant(client)
print("Assistant created with ID:", assistant_id)

# Create thread
@app.route('/start', methods=['GET'])
def start_conversation():
    thread = client.beta.threads.create()
    print("New conversation started with thread ID:", thread.id)
    return jsonify({"thread_id": thread.id})

# Start run
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    thread_id = data.get('thread_id')
    user_input = data.get('message', '')
    if not thread_id:
        print("Error: Missing thread_id in /chat")
        return jsonify({"error": "Missing thread_id"}), 400
    print("Received message for thread ID:", thread_id, "Message:", user_input)

    # Start run and send run ID back to ManyChat
    client.beta.threads.messages.create(thread_id=thread_id,
                                        role="user",
                                        content=user_input)
    run = client.beta.threads.runs.create(thread_id=thread_id,
                                          assistant_id=assistant_id)
    print("Run started with ID:", run.id)
    return jsonify({"run_id": run.id})

# Check status of run
@app.route('/check', methods=['POST'])
def check_run_status():
    data = request.json
    thread_id = data.get('thread_id')
    run_id = data.get('run_id')
    if not thread_id or not run_id:
        print("Error: Missing thread_id or run_id in /check")
        return jsonify({"response": "error"})

    # Start timer ensuring no more than 9 seconds, ManyChat timeout is 10s
    start_time = time.time()
    while time.time() - start_time < 8:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                       run_id=run_id)
        print("Checking run status:", run_status.status)

        if run_status.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            message_content = messages.data[0].content[0].text
            # Remove annotations
            annotations = message_content.annotations
            for annotation in annotations:
                message_content.value = message_content.value.replace(
                    annotation.text, '')
            print("Run completed, returning response")
            return jsonify({
                "response": message_content.value,
                "status": "completed"
            })

        if run_status.status == 'requires_action':
            print("Action in progress...")
            # Handle the function call
            for tool_call in run_status.required_action.submit_tool_outputs.tool_calls:
                if tool_call.function.name == "send_data":
                    # Process sending data
                    arguments = json.loads(tool_call.function.arguments)
                    summary = arguments.get("summary", "")  # Extract the summary from the assistant's arguments
                    output = functions.send_data(summary)
                    client.beta.threads.runs.submit_tool_outputs(thread_id=thread_id,
                                                                 run_id=run_id,
                                                                 tool_outputs=[{
                                                                     "tool_call_id": tool_call.id,
                                                                     "output": json.dumps(output)
                                                                 }])
        time.sleep(0.5)

    print("Run timed out")
    return jsonify({"response": "timeout"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
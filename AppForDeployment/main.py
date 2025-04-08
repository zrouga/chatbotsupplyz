import json
import os
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from data_fetching import update_data, get_data
from configs import SYSTEM_PROMPT, TABLES_DEFINITIONS
from functions import InventoryCodeInterpreter
from functools import lru_cache


app = FastAPI()

# Global state variables
_global_initialized = False
_len_tokens = 0
_instructions = ""
OPENAI_MODEL = "gpt-4o"
PRICE_PER_TOKEN = 2.5e-6
TOKEN_LENGTH_RATIO = 1.3
MAX_FUNCTION_CALL_ITERATIONS = 10
client = None

# Request/response models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    conversation_history: List[Message]

class ChatResponse(BaseModel):
    response: str

@lru_cache(maxsize=1)
def load_cached_data():
    update_data()
    return get_data()

def initialize():
    """Initialize data, build the system prompt, and create the OpenAI client."""
    global _global_initialized, _len_tokens, _instructions, client

    load_dotenv()
    data = load_cached_data() 


    # Extract signatures from the fetched data
    invoices_sig = data["invoices"][1]
    items_sig = data["items"][1]
    purchases_sig = data["purchases"][1]
    suppliers_sig = data["suppliers"][1]
    clients_sig = data["clients"][1]

    # Build the system prompt using the provided configurations
    _instructions = SYSTEM_PROMPT.format(
        TABLES_DEFINITIONS=TABLES_DEFINITIONS.format(
            clients_mapping=clients_sig,
            items_mapping=items_sig,
            suppleirs_mapping=suppliers_sig,
            purrchases_mapping=purchases_sig,
            invoices_mapping=invoices_sig,
        )
    )

    # Initialize token count based on the system prompt
    _len_tokens = len(_instructions.split()) * TOKEN_LENGTH_RATIO

    # Create the OpenAI client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    _global_initialized = True

def chatbot_response(conversation_history: List[dict]) -> str:
    """
    Process a conversation history and return the chatbot's final response.
    
    The conversation_history should be a list of messages, where each message is a dict:
        {"role": "user" or "assistant", "content": "Your message text"}
    """
    global _len_tokens, _instructions, client

    if not _global_initialized:
        initialize()

    # Prepare messages starting with the system prompt
    messages = [{"role": "system", "content": _instructions}] + conversation_history.copy()

    iteration = 0
    assistant_message = None

    while iteration < MAX_FUNCTION_CALL_ITERATIONS:
        # Call the OpenAI API with the current conversation messages
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": InventoryCodeInterpreter.__class__.__name__,
                        "description": InventoryCodeInterpreter.__class__.__doc__,
                        "parameters": InventoryCodeInterpreter.schema(),
                    },
                }
            ],
            stream=False,
            temperature=0,
            parallel_tool_calls=False,
        )

        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content,
            "tool_calls": response.choices[0].message.tool_calls,
        }
        messages.append(assistant_message)

        # Update token count (simple estimation)
        message_content = assistant_message["content"] or ""
        _len_tokens += len(message_content.split()) * TOKEN_LENGTH_RATIO

        # Process tool calls if any
        if assistant_message["tool_calls"]:
            tool_call = response.choices[0].message.tool_calls[0]
            tc_args = tool_call.function.arguments
            tc_id = tool_call.id

            # Parse tool call arguments and run the tool
            python_code_arg = json.loads(tc_args).get("python_code")
            tool_result = InventoryCodeInterpreter.parse_raw(tc_args).run()

            # Append the tool result as a new message
            tool_result_message = {
                "role": "tool",
                "content": json.dumps({"python_code": python_code_arg, "result": tool_result}),
                "tool_call_id": tc_id,
            }
            messages.append(tool_result_message)
        else:
            break

        iteration += 1

    return assistant_message["content"] if assistant_message else ""

@app.get("/ping")
def ping():
    return {"message": "pong"}

@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    FastAPI endpoint to process a chat request.
    Expects a JSON payload with the conversation_history (list of messages)
    and returns the final assistant response.
    """
    conversation_history = [message.dict() for message in request.conversation_history]
    try:
        response_text = chatbot_response(conversation_history)
        return ChatResponse(response=response_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

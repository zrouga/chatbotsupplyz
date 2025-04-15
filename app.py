import json
import os
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from data_fetching import update_data, get_data
from auth import login
from configs import SYSTEM_PROMPT, TABLES_DEFINITIONS
from functions import InventoryCodeInterpreter

load_dotenv()
# login()
st.set_page_config(
    page_title="SupplyZPro LLM", layout="wide", initial_sidebar_state="expanded"
)

if "data_updated" not in st.session_state:
    with st.spinner("Updating Data from Server"):
        update_data()
        data = get_data()

        st.session_state["invoices_sig"] = data["invoices"][1]
        st.session_state["items_sig"] = data["items"][1]
        st.session_state["purchases_sig"] = data["purchases"][1]
        st.session_state["suppliers_sig"] = data["suppliers"][1]
        st.session_state["clients_sig"] = data["clients"][1]
        st.session_state["SYSTEM_PROMPT"] = SYSTEM_PROMPT.format(
            TABLES_DEFINITIONS=TABLES_DEFINITIONS.format(
                clients_mapping=data["clients"][1],
                items_mapping=data["items"][1],
                suppleirs_mapping=data["suppliers"][1],
                purrchases_mapping=data["purchases"][1],
                invoices_mapping=data["invoices"][1],
            )
        )

        st.session_state.data_updated = True


# Config
OPENAI_MODEL = "gpt-4o"
INSTRUCTIONS = st.session_state["SYSTEM_PROMPT"]
PRICE_PER_TOKEN = 2.5e-6
TOKEN_LENGTH_RATIO = 1.3
MAX_FUNCTION_CALL_ITERATIONS = 10


# State management
if "len_tokens" not in st.session_state:
    st.session_state["len_tokens"] = len(INSTRUCTIONS.split()) * TOKEN_LENGTH_RATIO

if "messages_generation" not in st.session_state:
    st.session_state["messages_generation"] = []

# Custom CSS for styling
st.markdown(
    """
<style>
    /* Page and sidebar background */
    .reportview-container {
        background: #111827;
    }
    .sidebar .sidebar-content {
        background: #1f2937;
    }

    /* Typography */
    .big-font {
        font-size: 30px !important; 
        font-weight: bold; 
        color: #FFFFFF;
        text-align: center;
    }
    .medium-font {
        font-size: 20px !important; 
        font-weight: bold; 
        color: #FFFFFF;
    }
    .analysis-card {
        background: linear-gradient(135deg, #1E3A8A, #3B82F6);
        border-radius: 10px;
        padding: 30px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        margin-bottom: 20px;
        color: #ffffff;
    }
    .analysis-title {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 15px;
        text-align: center;
    }
    .analysis-content {
        font-size: 16px;
        line-height: 1.8;
        margin-bottom: 15px;
    }
    .analysis-list {
        padding-left: 20px;
    }
    .analysis-list-item {
        margin-bottom: 10px;
        font-size: 16px;
    }

    /* Flex container to ensure equal card heights */
    .equal-columns {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        margin: 20px 0;
    }
    .equal-columns > div {
        flex: 1;
        display: flex;           /* Let each card stretch to fill height */
        flex-direction: column;
        justify-content: space-between;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.sidebar.markdown("## Configuration")
st.markdown(
    """
<div class="equal-columns">
    <div class="analysis-card">
        <h2 class="analysis-title">AI-Powered Supply Chain Query Extraction Platform</h2>
        <p class="analysis-content">
            Leverage Artificial Intelligence and Large Language Models (LLMs) to extract complex queries from supply chain data. Our platform provides:
        </p>
        <ul class="analysis-list">
            <li class="analysis-list-item">Comprehensive analysis across inventory levels, shipments, supplier performance, and warehouse operations</li>
        </ul>
        <p class="analysis-content">
            Empower your decision-making with detailed, AI-generated insights. Uncover hidden patterns, optimize logistics, and make data-driven decisions with ease.
        </p>
    </div>
</div>
""",
    unsafe_allow_html=True,
)


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

token_placeholder = st.sidebar.empty()
cost_placeholder = st.sidebar.empty()

token_placeholder.markdown(f"**Tokens length:** {st.session_state['len_tokens']:,.0f}")
cost_placeholder.markdown(
    f"**Cost Estimation:** {round(st.session_state['len_tokens'] * PRICE_PER_TOKEN,5) } USD"
)

for message in st.session_state["messages_generation"]:  # [1:]:
    if message["role"] != "tool":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

if prompt := st.chat_input("Type your message:"):
    # Add the user message to the list of messages
    st.session_state["messages_generation"].append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    iteration = 0
    while iteration < MAX_FUNCTION_CALL_ITERATIONS:
        system_message = {"role": "system", "content": INSTRUCTIONS}
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[system_message] + st.session_state["messages_generation"],
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
            # NOTE: this app doesn't currently support parallel tool calls
            parallel_tool_calls=False,
        )

        # Add the model response to the list of messages
        assistant_message = {
            "role": "assistant",
            "content": response.choices[0].message.content,
            "tool_calls": response.choices[0].message.tool_calls,
        }
        st.session_state["messages_generation"].append(assistant_message)

        # Handle empty contents (e.g., when the model doesn't generate any text for tool calls)
        message_content = assistant_message["content"] or ""
        if message_content:
            with st.chat_message("assistant"):
                st.markdown(assistant_message["content"])

        # Update consumed tokens and cost
        # NOTE: This underestimates the cost as it doesn't account for the tool calls
        st.session_state["len_tokens"] += (
            len(message_content.split()) * TOKEN_LENGTH_RATIO
        )
        token_placeholder.markdown(f"Tokens length: {st.session_state['len_tokens']}")
        cost_placeholder.markdown(
            f"Cost Estimation: {round(st.session_state['len_tokens'] * PRICE_PER_TOKEN,5)} USD"
        )

        # Handle tool calls
        if assistant_message["tool_calls"]:
            tool_call = response.choices[0].message.tool_calls[0]
            tc_args = tool_call.function.arguments
            tc_id = tool_call.id

            # with st.chat_message("assistant"):
            # st.json(tool_call)

            python_code_arg = json.loads(tc_args).get("python_code")
            with st.spinner("Calling SupplyZPro Analysis tool ..."):
                # NOTE: .parse_raw is deprecated in newer versions of Pydantic
                tool_result = InventoryCodeInterpreter.parse_raw(tc_args).run()

            # Add the tool result to the list of messages
            tool_result_message = {
                "role": "tool",
                "content": json.dumps(
                    {
                        "python_code": python_code_arg,
                        "result": tool_result,
                    }
                ),
                "tool_call_id": tc_id,
            }
            st.session_state["messages_generation"].append(tool_result_message)
        else:
            break
        iteration += 1

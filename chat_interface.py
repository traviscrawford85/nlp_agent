#!/usr/bin/env python3
"""
Gradio Chat Interface for Clio NLP Agent

A user-friendly web chat interface that makes it easy to send natural language
requests to the Clio NLP Agent without using curl commands.
"""

import os
import json
import asyncio
import requests
from datetime import datetime
from typing import List, Tuple, Optional

import gradio as gr
from loguru import logger

# Configure logging
logger.add("chat_interface.log", rotation="1 day", retention="7 days")

class ClioNLPChat:
    """Chat interface for the Clio NLP Agent."""

    def __init__(self, agent_url: str = "http://localhost:8000"):
        self.agent_url = agent_url
        self.session_history: List[Tuple[str, str, str]] = []  # (timestamp, user, assistant)

    def check_agent_health(self) -> dict:
        """Check if the NLP agent is running and healthy."""
        try:
            response = requests.get(f"{self.agent_url}/health", timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to check agent health: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def get_auth_status(self) -> dict:
        """Get current authentication status."""
        try:
            response = requests.get(f"{self.agent_url}/auth/status", timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get auth status: {e}")
            return {"error": str(e)}

    def send_query(self, query: str, include_raw_data: bool = False) -> dict:
        """Send a natural language query to the NLP agent."""
        try:
            payload = {
                "query": query,
                "include_raw_data": include_raw_data
            }

            response = requests.post(
                f"{self.agent_url}/nlp",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60  # 1 minute timeout
            )

            return response.json()

        except Exception as e:
            logger.error(f"Failed to send query: {e}")
            return {
                "success": False,
                "message": f"Error communicating with agent: {str(e)}",
                "error": str(e)
            }

    def process_chat_message(self, message: str, history: List[dict], include_details: bool = False) -> Tuple[List[dict], str]:
        """Process a chat message and return updated history."""
        if not message.strip():
            return history, ""

        # Send query to agent
        logger.info(f"Processing query: {message[:100]}...")
        result = self.send_query(message, include_raw_data=include_details)

        # Format response
        if result.get("success", False):
            response = result.get("message", "Query processed successfully")

            if include_details:
                # Add execution details if requested
                details = []
                if result.get("execution_time"):
                    details.append(f"⏱️ Execution time: {result['execution_time']:.2f}s")
                if result.get("operation_type"):
                    details.append(f"🔧 Operation: {result['operation_type']}")
                if result.get("confidence_score"):
                    details.append(f"🎯 Confidence: {result['confidence_score']:.1%}")

                if details:
                    response += "\n\n" + " | ".join(details)

                # Add structured data if available
                if result.get("data") and isinstance(result["data"], dict):
                    response += f"\n\n📊 **Data:** {json.dumps(result['data'], indent=2)}"
        else:
            response = f"❌ Error: {result.get('message', 'Unknown error occurred')}"

        # Add messages to history in OpenAI format
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response})

        # Store in session history
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.session_history.append((timestamp, message, response))

        return history, ""

    def get_example_queries(self) -> List[str]:
        """Get example queries for the interface."""
        return [
            "Check my authentication status",
            "List all contacts",
            "Create a contact named John Smith with email john@example.com",
            "Show me all open matters",
            "Add 2 hours of work on matter 123 for contract review",
            "List all custom fields for contacts",
            "Generate a custom fields usage report",
            "Find all contacts with the last name Johnson",
            "Show time entries for this week",
            "Run a data sync for all contacts"
        ]

def create_interface():
    """Create and configure the Gradio interface."""

    # Initialize chat client
    chat_client = ClioNLPChat()

    # Check agent status
    health_status = chat_client.check_agent_health()
    auth_status = chat_client.get_auth_status()

    # Create interface
    with gr.Blocks(
        title="Clio NLP Agent Chat",
        theme=gr.themes.Soft(),
        css="""
        .container { max-width: 1200px; margin: 0 auto; }
        .status-healthy { color: green; font-weight: bold; }
        .status-unhealthy { color: red; font-weight: bold; }
        .example-btn { margin: 2px; }
        """
    ) as interface:

        gr.Markdown("# 🤖 Clio NLP Agent Chat Interface")
        gr.Markdown("Ask questions in natural language and get results from your Clio system!")

        # Status section
        with gr.Row():
            with gr.Column(scale=1):
                status_text = "🟢 **Healthy**" if health_status.get("status") == "healthy" else "🔴 **Unhealthy**"
                gr.Markdown(f"**Agent Status:** {status_text}")

            with gr.Column(scale=1):
                if auth_status.get("authenticated"):
                    auth_text = f"🔐 **Authenticated** as {auth_status.get('user_name', 'Unknown')}"
                else:
                    auth_text = "❌ **Not Authenticated**"
                gr.Markdown(auth_text)

        # Main chat interface
        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    height=500,
                    show_label=False,
                    container=True,
                    type="messages"
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Type your question here... (e.g., 'List all contacts' or 'Create a contact named John Doe')",
                        container=False,
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

                with gr.Row():
                    clear_btn = gr.Button("Clear Chat", variant="secondary")
                    include_details = gr.Checkbox(
                        label="Include execution details",
                        value=False,
                        info="Show timing, confidence, and structured data"
                    )

            with gr.Column(scale=1):
                gr.Markdown("### 💡 Example Queries")
                gr.Markdown("Click any example to try it:")

                examples = chat_client.get_example_queries()
                example_buttons = []

                for example in examples:
                    btn = gr.Button(
                        example,
                        size="sm",
                        elem_classes=["example-btn"]
                    )
                    example_buttons.append((btn, example))

        # Help section
        with gr.Accordion("📖 Help & Tips", open=False):
            gr.Markdown("""
            ### How to Use This Chat Interface

            **Natural Language Examples:**
            - *"Create a contact named Sarah Johnson with email sarah@company.com"*
            - *"Find all matters for client John Doe"*
            - *"Add 1.5 hours of work on matter 456 for document review"*
            - *"Show me custom fields that aren't being used"*
            - *"Generate a backup of the custom fields database"*

            **Tips:**
            - Be specific with names, IDs, and details
            - Use natural language - no need for technical syntax
            - The agent will ask for clarification if needed
            - Check "Include execution details" for more technical information

            **Available Operations:**
            - 👥 Contact management (create, search, update)
            - ⚖️ Matter management (create, list, search)
            - ⏱️ Time tracking (create entries, view activities)
            - 🏷️ Custom fields (manage, analyze, report)
            - 🛠️ CLI operations (sync, backup, validate)
            """)

        # Event handlers
        def handle_message(message, history, details):
            return chat_client.process_chat_message(message, history, details)

        def clear_chat():
            chat_client.session_history.clear()
            return []

        def use_example():
            # This will be handled by individual button clicks
            pass

        # Connect events
        msg_input.submit(
            handle_message,
            inputs=[msg_input, chatbot, include_details],
            outputs=[chatbot, msg_input]
        )

        send_btn.click(
            handle_message,
            inputs=[msg_input, chatbot, include_details],
            outputs=[chatbot, msg_input]
        )

        clear_btn.click(clear_chat, outputs=[chatbot])

        # Connect example buttons with specific lambda functions
        for btn, example_text in example_buttons:
            btn.click(lambda text=example_text: text, outputs=[msg_input])

    return interface

def main():
    """Main function to launch the chat interface."""

    # Check if agent is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("⚠️  Warning: Clio NLP Agent may not be running properly")
            print("   Make sure the agent is started with: uvicorn main:app --host 0.0.0.0 --port 8000")
    except Exception as e:
        print(f"❌ Cannot connect to Clio NLP Agent at http://localhost:8000")
        print(f"   Error: {e}")
        print("\n🚀 Please start the agent first:")
        print("   cd /home/sysadmin01/clio_assistant/clio-nlp-agent")
        print("   source .venv/bin/activate")
        print("   uvicorn main:app --host 0.0.0.0 --port 8000")
        print("\n   Then run this chat interface again.")
        return

    # Create and launch interface
    interface = create_interface()

    print("\n🎉 Starting Clio NLP Agent Chat Interface...")
    print("📱 The chat will open in your web browser")
    print("🌐 You can also access it at: http://localhost:7860")
    print("🛑 Press Ctrl+C to stop")

    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,  # Set to True if you want a public link
        show_error=True,
        show_api=False
    )

if __name__ == "__main__":
    main()
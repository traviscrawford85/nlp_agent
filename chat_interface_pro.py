#!/usr/bin/env python3
"""
Professional Gradio Chat Interface for Clio NLP Agent

A modern, professional web chat interface with Clio brand colors and UX best practices.
Features responsive design, accessibility, and intuitive user interactions.
"""

import os
import json
import asyncio
import requests
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

import gradio as gr
from loguru import logger

# Import Clio brand colors from config
try:
    from config import CLIO_BRAND_COLORS, CHART_COLORS
except ImportError:
    # Fallback brand colors if config not available
    CLIO_BRAND_COLORS = {
        "sand": "#EEEDEA",
        "ocean_blue": "#0070E0",
        "mountain_blue": "#04304C",
        "coral": "#D74417",
        "emerald": "#018b76",
        "white": "#FFFFFF",
        "ocean_light": "#3D8FE8",
        "coral_light": "#E6674A",
        "emerald_light": "#33A691",
        "amber": "#F4A540",
    }

# Configure logging
logger.add("chat_interface.log", rotation="1 day", retention="7 days")

class ClioNLPChatPro:
    """Professional chat interface for the Clio NLP Agent."""

    def __init__(self, agent_url: str = "http://localhost:8001"):
        self.agent_url = agent_url
        self.session_history: List[Dict[str, Any]] = []
        self.user_preferences = {
            "show_details": False,
            "auto_scroll": True,
            "sound_notifications": False
        }

    def check_agent_health(self) -> Dict[str, Any]:
        """Check if the NLP agent is running and healthy."""
        try:
            response = requests.get(f"{self.agent_url}/health", timeout=5)
            health_data = response.json()
            return {**health_data, "connection": "connected"}
        except requests.exceptions.ConnectionError:
            return {
                "status": "unreachable",
                "connection": "disconnected",
                "error": "Cannot connect to NLP agent. Please ensure it's running."
            }
        except Exception as e:
            logger.error(f"Failed to check agent health: {e}")
            return {
                "status": "error",
                "connection": "error",
                "error": str(e)
            }

    def get_auth_status(self) -> Dict[str, Any]:
        """Get current authentication status."""
        try:
            response = requests.get(f"{self.agent_url}/auth/status", timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get auth status: {e}")
            return {"error": str(e), "authenticated": False}

    def send_query(self, query: str, include_raw_data: bool = False) -> Dict[str, Any]:
        """Send a natural language query to the NLP agent."""
        if not query.strip():
            return {"success": False, "message": "Please enter a query"}

        try:
            payload = {
                "query": query,
                "include_raw_data": include_raw_data
            }

            response = requests.post(
                f"{self.agent_url}/nlp",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )

            return response.json()

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": "Request timed out. The query may be too complex.",
                "error": "timeout"
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "message": "Cannot connect to NLP agent. Please check if it's running.",
                "error": "connection_error"
            }
        except Exception as e:
            logger.error(f"Failed to send query: {e}")
            return {
                "success": False,
                "message": f"Error communicating with agent: {str(e)}",
                "error": str(e)
            }

    def process_chat_message(self, message: str, history: List[Dict], include_details: bool = False) -> Tuple[List[Dict], str]:
        """Process a chat message and return updated history."""
        if not message.strip():
            return history, ""

        # Add user message to history
        user_msg = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        }

        # Send query to agent
        logger.info(f"Processing query: {message[:100]}...")
        start_time = datetime.now()
        result = self.send_query(message, include_raw_data=include_details)
        execution_time = (datetime.now() - start_time).total_seconds()

        # Format response with enhanced presentation
        if result.get("success", False):
            response = result.get("message", "Query processed successfully")

            # Add execution details if requested
            if include_details and result.get("execution_time"):
                details_parts = []
                if result.get("execution_time"):
                    details_parts.append(f"⏱️ {result['execution_time']:.2f}s")
                if result.get("operation_type"):
                    details_parts.append(f"🔧 {result['operation_type'].replace('_', ' ').title()}")
                if result.get("confidence_score"):
                    confidence = result['confidence_score']
                    confidence_emoji = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"
                    details_parts.append(f"{confidence_emoji} {confidence:.0%} confidence")

                if details_parts:
                    response += f"\n\n📊 **Execution Details:** {' • '.join(details_parts)}"

            # Add structured data if available
            if include_details and result.get("data"):
                if isinstance(result["data"], (dict, list)):
                    if len(str(result["data"])) < 1000:  # Only show if reasonable size
                        response += f"\n\n```json\n{json.dumps(result['data'], indent=2)}\n```"
                    else:
                        response += f"\n\n📋 **Data:** Large dataset returned ({len(str(result['data']))} characters)"

        else:
            error_msg = result.get("message", "Unknown error occurred")
            response = f"❌ **Error:** {error_msg}"

            # Add helpful suggestions for common errors
            if "connection" in error_msg.lower():
                response += "\n\n💡 **Suggestion:** Make sure the NLP agent is running at `http://localhost:8001`"
            elif "timeout" in error_msg.lower():
                response += "\n\n💡 **Suggestion:** Try a simpler query or check if the agent is overloaded"

        # Create assistant message
        assistant_msg = {
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            "success": result.get("success", False)
        }

        # Update history and session storage
        history.extend([user_msg, assistant_msg])
        self.session_history.extend([user_msg, assistant_msg])

        return history, ""

    def get_example_queries(self) -> List[Dict[str, Any]]:
        """Get categorized example queries for the interface."""
        return [
            {
                "category": "👥 Contact Management",
                "color": CLIO_BRAND_COLORS["emerald"],
                "queries": [
                    "Check my authentication status",
                    "List all contacts",
                    "Create a contact named John Smith with email john@example.com",
                    "Find contacts with the last name Johnson",
                    "Search for contacts at Microsoft"
                ]
            },
            {
                "category": "⚖️ Matter Management",
                "color": CLIO_BRAND_COLORS["ocean_blue"],
                "queries": [
                    "Show me all open matters",
                    "Create a matter for client ID 456 called Personal Injury Case",
                    "Find matters created in the last 30 days",
                    "List matters for client John Doe"
                ]
            },
            {
                "category": "⏱️ Time Tracking",
                "color": CLIO_BRAND_COLORS["coral"],
                "queries": [
                    "Add 2 hours of work on matter 123 for contract review",
                    "Show time entries for this week",
                    "Create time entry: 1.5 hours on matter 456 for client meeting",
                    "Log 30 minutes on matter 789 for phone call"
                ]
            },
            {
                "category": "🏷️ Custom Fields",
                "color": CLIO_BRAND_COLORS["amber"],
                "queries": [
                    "List all custom fields",
                    "Show custom field values for contact ID 123",
                    "Set the Priority custom field to High for matter 456",
                    "Find all custom fields that are not being used"
                ]
            },
            {
                "category": "🛠️ System Operations",
                "color": CLIO_BRAND_COLORS["mountain_blue"],
                "queries": [
                    "Run a data sync for all contacts",
                    "Generate a custom fields usage report",
                    "Backup the custom fields database",
                    "Validate custom field data integrity"
                ]
            }
        ]

def create_professional_theme():
    """Create a professional Gradio theme with Clio brand colors."""
    return gr.themes.Soft(
        primary_hue=gr.themes.Color(
            c50="#f0f9ff",
            c100="#e0f2fe",
            c200="#bae6fd",
            c300=CLIO_BRAND_COLORS["ocean_light"],
            c400=CLIO_BRAND_COLORS["ocean_blue"],
            c500=CLIO_BRAND_COLORS["ocean_blue"],
            c600=CLIO_BRAND_COLORS["ocean_blue"],
            c700="#0369a1",
            c800="#075985",
            c900=CLIO_BRAND_COLORS["mountain_blue"],
            c950="#0c4a6e",
        ),
        secondary_hue=gr.themes.Color(
            c50="#fafaf9",
            c100="#f5f5f4",
            c200="#e7e5e4",
            c300="#d6d3d1",
            c400="#a8a29e",
            c500="#78716c",
            c600="#57534e",
            c700="#44403c",
            c800="#292524",
            c900="#1c1917",
            c950="#0c0a09",
        ),
        neutral_hue=gr.themes.Color(
            c50=CLIO_BRAND_COLORS["sand"],
            c100=CLIO_BRAND_COLORS["sand"],
            c200="#f3f4f6",
            c300="#e5e7eb",
            c400="#9ca3af",
            c500="#6b7280",
            c600="#4b5563",
            c700="#374151",
            c800="#1f2937",
            c900="#111827",
            c950="#030712",
        ),
        font=[
            gr.themes.GoogleFont("Inter"),
            "ui-sans-serif",
            "system-ui",
            "sans-serif"
        ],
        font_mono=[
            gr.themes.GoogleFont("JetBrains Mono"),
            "ui-monospace",
            "Consolas",
            "monospace"
        ],
        text_size=gr.themes.sizes.text_md,
        spacing_size=gr.themes.sizes.spacing_md,
        radius_size=gr.themes.sizes.radius_md,
    )

def create_custom_css():
    """Generate custom CSS for professional styling."""
    return f"""
    /* === PROFESSIONAL CLIO CHAT INTERFACE === */

    /* Main container styling */
    .gradio-container {{
        max-width: 1400px !important;
        margin: 0 auto;
        background: linear-gradient(135deg, {CLIO_BRAND_COLORS["sand"]} 0%, #f8f9fa 100%);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Header styling */
    .main-header {{
        background: linear-gradient(135deg, {CLIO_BRAND_COLORS["mountain_blue"]} 0%, {CLIO_BRAND_COLORS["ocean_blue"]} 100%);
        color: white;
        padding: 24px;
        border-radius: 12px 12px 0 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin-bottom: 24px;
    }}

    .main-header h1 {{
        margin: 0;
        font-weight: 600;
        font-size: 28px;
        display: flex;
        align-items: center;
        gap: 12px;
    }}

    .main-header p {{
        margin: 8px 0 0 0;
        opacity: 0.9;
        font-size: 16px;
    }}

    /* Status indicators */
    .status-container {{
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        margin: 16px 0;
    }}

    .status-card {{
        background: rgba(255,255,255,0.95);
        border-radius: 8px;
        padding: 12px 16px;
        border-left: 4px solid;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        flex: 1;
        min-width: 200px;
    }}

    .status-healthy {{ border-left-color: {CLIO_BRAND_COLORS["emerald"]}; }}
    .status-warning {{ border-left-color: {CLIO_BRAND_COLORS["amber"]}; }}
    .status-error {{ border-left-color: {CLIO_BRAND_COLORS["coral"]}; }}
    .status-info {{ border-left-color: {CLIO_BRAND_COLORS["ocean_blue"]}; }}

    /* Chat interface styling */
    .chat-container {{
        background: white;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        overflow: hidden;
    }}

    .chatbot {{
        border: none !important;
        background: white;
    }}

    /* Message styling improvements */
    .message {{
        margin: 8px 0;
        padding: 12px 16px;
        border-radius: 12px;
        max-width: 85%;
        word-wrap: break-word;
        line-height: 1.5;
    }}

    .user-message {{
        background: {CLIO_BRAND_COLORS["ocean_blue"]};
        color: white;
        margin-left: auto;
    }}

    .assistant-message {{
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        color: #2c3e50;
    }}

    /* Input area styling */
    .input-container {{
        background: white;
        border-top: 1px solid #e9ecef;
        padding: 16px;
    }}

    .input-row {{
        display: flex;
        gap: 12px;
        align-items: flex-end;
    }}

    .chat-input {{
        flex: 1;
        border: 2px solid #e9ecef;
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 16px;
        transition: all 0.2s ease;
        resize: vertical;
        min-height: 44px;
    }}

    .chat-input:focus {{
        border-color: {CLIO_BRAND_COLORS["ocean_blue"]};
        box-shadow: 0 0 0 3px rgba(0, 112, 224, 0.1);
        outline: none;
    }}

    /* Button styling */
    .btn-primary {{
        background: {CLIO_BRAND_COLORS["ocean_blue"]};
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 16px;
    }}

    .btn-primary:hover {{
        background: #005bb8;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 112, 224, 0.3);
    }}

    .btn-secondary {{
        background: #f8f9fa;
        color: #495057;
        border: 1px solid #dee2e6;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
    }}

    .btn-secondary:hover {{
        background: #e9ecef;
        border-color: #adb5bd;
    }}

    /* Example buttons styling */
    .examples-section {{
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        overflow: hidden;
        margin: 16px 0;
    }}

    .examples-header {{
        background: linear-gradient(135deg, {CLIO_BRAND_COLORS["sand"]} 0%, #f1f3f4 100%);
        padding: 16px;
        border-bottom: 1px solid #e9ecef;
        font-weight: 600;
        color: {CLIO_BRAND_COLORS["mountain_blue"]};
    }}

    .examples-grid {{
        padding: 16px;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 12px;
    }}

    .example-category {{
        border: 1px solid #e9ecef;
        border-radius: 8px;
        overflow: hidden;
        transition: all 0.2s ease;
    }}

    .example-category:hover {{
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }}

    .example-header {{
        padding: 12px 16px;
        font-weight: 600;
        font-size: 14px;
        color: white;
        text-align: center;
    }}

    .example-button {{
        display: block;
        width: 100%;
        padding: 10px 16px;
        border: none;
        background: white;
        color: #495057;
        text-align: left;
        cursor: pointer;
        transition: all 0.2s ease;
        border-bottom: 1px solid #f8f9fa;
        font-size: 13px;
    }}

    .example-button:hover {{
        background: #f8f9fa;
        color: {CLIO_BRAND_COLORS["ocean_blue"]};
        padding-left: 20px;
    }}

    .example-button:last-child {{
        border-bottom: none;
    }}

    /* Controls styling */
    .controls-row {{
        display: flex;
        gap: 16px;
        align-items: center;
        padding: 12px 16px;
        background: #f8f9fa;
        border-top: 1px solid #e9ecef;
        font-size: 14px;
    }}

    .control-item {{
        display: flex;
        align-items: center;
        gap: 8px;
        color: #6c757d;
    }}

    /* Help section styling */
    .help-section {{
        background: linear-gradient(135deg, #f8f9fa 0%, white 100%);
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 20px;
        margin: 16px 0;
    }}

    .help-title {{
        color: {CLIO_BRAND_COLORS["mountain_blue"]};
        font-weight: 600;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 8px;
    }}

    /* Responsive design */
    @media (max-width: 768px) {{
        .gradio-container {{
            margin: 0;
            border-radius: 0;
        }}

        .status-container {{
            flex-direction: column;
        }}

        .examples-grid {{
            grid-template-columns: 1fr;
        }}

        .main-header h1 {{
            font-size: 24px;
        }}

        .controls-row {{
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
        }}
    }}

    /* Loading and transitions */
    .loading {{
        opacity: 0.6;
        pointer-events: none;
        transition: opacity 0.3s ease;
    }}

    .fade-in {{
        animation: fadeIn 0.5s ease-in;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* Accessibility improvements */
    .sr-only {{
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
    }}

    /* Focus indicators */
    *:focus-visible {{
        outline: 2px solid {CLIO_BRAND_COLORS["ocean_blue"]};
        outline-offset: 2px;
    }}
    """

def create_interface():
    """Create and configure the professional Gradio interface."""

    # Initialize chat client
    chat_client = ClioNLPChatPro()

    # Check system status
    health_status = chat_client.check_agent_health()
    auth_status = chat_client.get_auth_status()

    # Create interface with professional theme
    with gr.Blocks(
        title="Clio NLP Agent - Professional Chat",
        theme=create_professional_theme(),
        css=create_custom_css(),
        analytics_enabled=False,
        head='<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">'
    ) as interface:

        # Header Section
        with gr.Row():
            with gr.Column():
                gr.HTML(f"""
                <div class="main-header">
                    <h1>🤖 Clio NLP Agent</h1>
                    <p>Professional Natural Language Interface for Clio Operations</p>
                </div>
                """)

        # Status Dashboard
        with gr.Row():
            with gr.Column():
                status_html = create_status_dashboard(health_status, auth_status)
                status_display = gr.HTML(status_html)

        # Main Chat Interface
        with gr.Row():
            with gr.Column(scale=3):
                with gr.Group(elem_classes=["chat-container"]):
                    chatbot = gr.Chatbot(
                        height=500,
                        show_label=False,
                        container=False,
                        type="messages",
                        avatar_images=("https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
                                     "https://cdn-icons-png.flaticon.com/512/4712/4712027.png"),
                        show_copy_button=True,
                        elem_classes=["chatbot"]
                    )

                    with gr.Group(elem_classes=["input-container"]):
                        with gr.Row(elem_classes=["input-row"]):
                            msg_input = gr.Textbox(
                                placeholder="Ask me anything about your Clio data... (e.g., 'List all contacts' or 'Show matters from last month')",
                                container=False,
                                scale=4,
                                lines=2,
                                max_lines=4,
                                elem_classes=["chat-input"],
                                label=""
                            )
                            send_btn = gr.Button(
                                "Send",
                                variant="primary",
                                scale=1,
                                size="lg",
                                elem_classes=["btn-primary"]
                            )

                        with gr.Row(elem_classes=["controls-row"]):
                            clear_btn = gr.Button(
                                "🗑️ Clear Chat",
                                variant="secondary",
                                size="sm",
                                elem_classes=["btn-secondary"]
                            )
                            include_details = gr.Checkbox(
                                label="Show execution details",
                                value=False,
                                info="Include timing, confidence scores, and raw data",
                                elem_classes=["control-item"]
                            )
                            refresh_btn = gr.Button(
                                "🔄 Refresh Status",
                                variant="secondary",
                                size="sm",
                                elem_classes=["btn-secondary"]
                            )

            # Examples Sidebar
            with gr.Column(scale=1):
                create_examples_section(chat_client)

        # Help Section
        with gr.Accordion("📖 Help & Tips", open=False, elem_classes=["help-section"]):
            gr.Markdown(f"""
            <div class="help-title">💡 How to Use This Interface</div>

            **Quick Tips:**
            - Use natural language - no technical syntax needed
            - Be specific with names, IDs, and details when possible
            - Click example queries to try them instantly
            - Enable "Show execution details" for technical information

            **Example Queries:**
            - *"Create a contact named Sarah Johnson with email sarah@company.com"*
            - *"Find all matters for client John Doe"*
            - *"Add 2 hours of work on matter 456 for document review"*
            - *"Show me custom fields that aren't being used"*

            **System Status:**
            - 🟢 **Green:** Everything working perfectly
            - 🟡 **Yellow:** Minor issues, reduced functionality
            - 🔴 **Red:** Major problems, may not work properly

            **Keyboard Shortcuts:**
            - `Enter` - Send message
            - `Shift + Enter` - New line in message
            - `Ctrl + L` - Clear chat
            """)

        # Event Handlers
        def handle_message(message, history, details):
            return chat_client.process_chat_message(message, history, details)

        def clear_chat():
            chat_client.session_history.clear()
            return []

        def refresh_status():
            health = chat_client.check_agent_health()
            auth = chat_client.get_auth_status()
            return create_status_dashboard(health, auth)

        def use_example(example_text):
            return example_text

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
        refresh_btn.click(refresh_status, outputs=[status_display])

        # Example button connections are created in create_examples_section

    return interface, chat_client

def create_status_dashboard(health_status: Dict[str, Any], auth_status: Dict[str, Any]) -> str:
    """Create HTML for the status dashboard."""

    # Determine overall status
    connection = health_status.get("connection", "unknown")
    agent_status = health_status.get("status", "unknown")

    if connection == "connected" and agent_status == "healthy":
        status_class = "status-healthy"
        status_icon = "🟢"
        status_text = "All Systems Operational"
    elif connection == "connected":
        status_class = "status-warning"
        status_icon = "🟡"
        status_text = "Partially Operational"
    else:
        status_class = "status-error"
        status_icon = "🔴"
        status_text = "System Offline"

    # Authentication status
    auth_authenticated = auth_status.get("authenticated", False)
    auth_icon = "🔐" if auth_authenticated else "❌"
    auth_text = f"Authenticated as {auth_status.get('user_name', 'Unknown')}" if auth_authenticated else "Not Authenticated"
    auth_class = "status-healthy" if auth_authenticated else "status-error"

    # Services status
    services = health_status.get("services", {})
    services_status = []

    for service, status in services.items():
        if "authenticated" in status or status in ["healthy", "configured", "available"]:
            services_status.append(f"✅ {service.replace('_', ' ').title()}")
        else:
            services_status.append(f"❌ {service.replace('_', ' ').title()}")

    return f"""
    <div class="status-container">
        <div class="status-card {status_class}">
            <strong>{status_icon} {status_text}</strong>
            <div style="font-size: 12px; margin-top: 4px; opacity: 0.8;">
                Agent Connection: {connection.title()}
            </div>
        </div>
        <div class="status-card {auth_class}">
            <strong>{auth_icon} Authentication</strong>
            <div style="font-size: 12px; margin-top: 4px; opacity: 0.8;">
                {auth_text}
            </div>
        </div>
        <div class="status-card status-info">
            <strong>🛠️ Services</strong>
            <div style="font-size: 11px; margin-top: 4px; opacity: 0.8;">
                {' • '.join(services_status[:3]) if services_status else 'No services info'}
            </div>
        </div>
    </div>
    """

def create_examples_section(chat_client: ClioNLPChatPro):
    """Create the examples section with categorized queries."""
    examples = chat_client.get_example_queries()

    with gr.Group(elem_classes=["examples-section"]):
        gr.HTML('<div class="examples-header">💡 Quick Examples</div>')

        with gr.Column(elem_classes=["examples-grid"]):
            example_buttons = []

            for category in examples:
                with gr.Group(elem_classes=["example-category"]):
                    # Category header with color
                    gr.HTML(f"""
                    <div class="example-header" style="background-color: {category['color']};">
                        {category['category']}
                    </div>
                    """)

                    # Example buttons
                    for query in category['queries'][:4]:  # Limit to 4 per category
                        btn = gr.Button(
                            query,
                            size="sm",
                            variant="secondary",
                            elem_classes=["example-button"]
                        )
                        example_buttons.append((btn, query))

    return example_buttons

def main():
    """Main function to launch the professional chat interface."""

    # Check if agent is running
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code != 200:
            print("⚠️  Warning: Clio NLP Agent may not be responding properly")
    except Exception:
        print(f"❌ Cannot connect to Clio NLP Agent at http://localhost:8001")
        print(f"   Please start the agent first:")
        print(f"   1. cd /home/sysadmin01/clio_assistant/clio-nlp-agent")
        print(f"   2. source .venv/bin/activate")
        print(f"   3. uvicorn main:app --host 0.0.0.0 --port 8001")
        print(f"\n   Then run this chat interface again.")
        return

    # Create and launch interface
    interface, chat_client = create_interface()

    print("\n🎉 Starting Professional Clio NLP Agent Chat Interface...")
    print("🎨 Enhanced with Clio brand colors and professional UX")
    print("📱 Responsive design with accessibility features")
    print("🌐 Access at: http://localhost:7861")
    print("🛑 Press Ctrl+C to stop")

    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Use different port to avoid conflicts
        share=False,
        show_error=True,
        show_api=False,
        favicon_path=None,
        auth=None,
        max_threads=10
    )

if __name__ == "__main__":
    main()
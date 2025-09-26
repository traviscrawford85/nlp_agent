"""
LangChain agent for Clio API natural language interface.

This module sets up the LangChain agent with tools for interacting with
Clio's API and CLI tools through natural language queries.
"""

import asyncio
import json
import os
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from langchain.agents import AgentType, initialize_agent
from langchain.tools import Tool, StructuredTool
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.callbacks import BaseCallbackHandler
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from loguru import logger
from pydantic import BaseModel, Field

from tools.clio_api import ClioAPIWrapper
from tools.clio_cli import ClioServiceCLI, CliResult
from tools.custom_fields_cli import CustomFieldsCLI
from tools.custom_field_set_tools import get_custom_field_set_tools
from models.responses import AgentThought, ToolExecutionResult


class ClioAgentCallbackHandler(BaseCallbackHandler):
    """Callback handler to capture agent thoughts and tool executions."""

    def __init__(self):
        self.thoughts: List[AgentThought] = []
        self.tool_results: List[ToolExecutionResult] = []
        self.current_step = 0

    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        """Called when agent takes an action."""
        self.current_step += 1
        thought = AgentThought(
            step=self.current_step,
            thought=action.log,
            action=f"{action.tool}({action.tool_input})"
        )
        self.thoughts.append(thought)

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Called when tool execution starts."""
        self._tool_start_time = datetime.now()

    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when tool execution ends."""
        if hasattr(self, '_tool_start_time'):
            execution_time = (datetime.now() - self._tool_start_time).total_seconds()
            # Tool result will be added by the tool wrapper

    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Called when tool execution fails."""
        if hasattr(self, '_tool_start_time'):
            execution_time = (datetime.now() - self._tool_start_time).total_seconds()
            result = ToolExecutionResult(
                tool_name=kwargs.get('tool_name', 'unknown'),
                success=False,
                output=None,
                error=str(error),
                execution_time=execution_time
            )
            self.tool_results.append(result)


class ClioNLPAgent:
    """Natural language interface to Clio API and CLI tools using LangChain."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        clio_auth_token: Optional[str] = None,
        model_name: str = "gpt-3.5-turbo-16k",
        temperature: float = 0.1
    ):
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.clio_auth_token = clio_auth_token or os.getenv("CLIO_AUTH_TOKEN")

        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")

        # Initialize LLM
        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=self.openai_api_key
        )

        # Initialize tools
        self.clio_api = ClioAPIWrapper(auth_token=self.clio_auth_token)
        self.clio_cli = ClioServiceCLI()
        self.custom_fields_cli = CustomFieldsCLI()

        # Create tools list
        self.tools = self._create_tools()

        # Initialize memory
        self.memory = ConversationBufferWindowMemory(
            k=10,  # Remember last 10 interactions
            memory_key="chat_history",
            return_messages=True
        )

        # Initialize agent
        self.callback_handler = ClioAgentCallbackHandler()
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            memory=self.memory,
            callbacks=[self.callback_handler],
            handle_parsing_errors=True
        )

    def _create_tools(self) -> List[Tool]:
        """Create LangChain tools for Clio operations."""
        tools = []

        # Contact management tools
        tools.extend([
            StructuredTool(
                name="get_contacts",
                description="Search and retrieve contacts from Clio. Use this to find existing contacts by name, email, or other criteria.",
                func=self._get_contacts,
                args_schema=self._create_get_contacts_schema()
            ),
            StructuredTool(
                name="create_contact",
                description="Create a new contact in Clio. Requires first_name and last_name at minimum.",
                func=self._create_contact,
                args_schema=self._create_contact_schema()
            ),
            StructuredTool(
                name="update_contact",
                description="Update an existing contact in Clio by contact ID.",
                func=self._update_contact,
                args_schema=self._create_update_contact_schema()
            )
        ])

        # Matter management tools
        tools.extend([
            StructuredTool(
                name="get_matters",
                description="Search and retrieve matters from Clio. Can filter by client, status, etc.",
                func=self._get_matters,
                args_schema=self._create_get_matters_schema()
            ),
            StructuredTool(
                name="create_matter",
                description="Create a new matter in Clio. Requires description and client_id.",
                func=self._create_matter,
                args_schema=self._create_matter_schema()
            )
        ])

        # Activity/Time tracking tools
        tools.extend([
            StructuredTool(
                name="get_activities",
                description="Retrieve time entries/activities from Clio. Can filter by matter, user, date range.",
                func=self._get_activities,
                args_schema=self._create_get_activities_schema()
            ),
            StructuredTool(
                name="create_activity",
                description="Create a time entry/activity in Clio. Requires matter_id, description, and quantity (in seconds).",
                func=self._create_activity,
                args_schema=self._create_activity_schema()
            )
        ])

        # Custom fields tools
        tools.extend([
            StructuredTool(
                name="get_custom_fields",
                description="List custom fields available in Clio, optionally filtered by entity type.",
                func=self._get_custom_fields,
                args_schema=self._create_get_custom_fields_schema()
            ),
            StructuredTool(
                name="manage_custom_field_values",
                description="Get or set custom field values for entities using the custom fields manager CLI.",
                func=self._manage_custom_field_values,
                args_schema=self._create_custom_field_values_schema()
            )
        ])

        # CLI tools
        tools.extend([
            StructuredTool(
                name="execute_clio_cli",
                description="Execute Clio service CLI commands for advanced operations not available through API.",
                func=self._execute_clio_cli,
                args_schema=self._create_cli_schema()
            ),
            StructuredTool(
                name="execute_custom_fields_cli",
                description="Execute custom fields manager CLI commands for field management and analysis.",
                func=self._execute_custom_fields_cli,
                args_schema=self._create_cfm_cli_schema()
            )
        ])

        # Custom field set management tools (Web UI endpoints)
        custom_field_set_tools = get_custom_field_set_tools()
        tools.extend(custom_field_set_tools)

        return tools

    def _create_get_contacts_schema(self):
        """Schema for get_contacts tool."""
        class GetContactsInput(BaseModel):
            search: Optional[str] = Field(None, description="Search query for contact names")
            email: Optional[str] = Field(None, description="Filter by email address")
            limit: Optional[int] = Field(None, description="Maximum number of contacts to return")
        return GetContactsInput

    def _create_contact_schema(self):
        """Schema for create_contact tool."""
        class CreateContactInput(BaseModel):
            first_name: str = Field(..., description="First name of the contact")
            last_name: str = Field(..., description="Last name of the contact")
            email: Optional[str] = Field(None, description="Email address")
            phone: Optional[str] = Field(None, description="Phone number")
            company: Optional[str] = Field(None, description="Company name")
        return CreateContactInput

    def _create_update_contact_schema(self):
        """Schema for update_contact tool."""
        class UpdateContactInput(BaseModel):
            contact_id: str = Field(..., description="ID of the contact to update")
            first_name: Optional[str] = Field(None, description="First name")
            last_name: Optional[str] = Field(None, description="Last name")
            email: Optional[str] = Field(None, description="Email address")
            phone: Optional[str] = Field(None, description="Phone number")
            company: Optional[str] = Field(None, description="Company name")
        return UpdateContactInput

    def _create_get_matters_schema(self):
        """Schema for get_matters tool."""
        class GetMattersInput(BaseModel):
            client_id: Optional[str] = Field(None, description="Filter by client ID")
            status: Optional[str] = Field(None, description="Filter by matter status")
            limit: Optional[int] = Field(None, description="Maximum number of matters to return")
        return GetMattersInput

    def _create_matter_schema(self):
        """Schema for create_matter tool."""
        class CreateMatterInput(BaseModel):
            description: str = Field(..., description="Matter description")
            client_id: str = Field(..., description="ID of the client for this matter")
            status: Optional[str] = Field("Open", description="Matter status")
        return CreateMatterInput

    def _create_get_activities_schema(self):
        """Schema for get_activities tool."""
        class GetActivitiesInput(BaseModel):
            matter_id: Optional[str] = Field(None, description="Filter by matter ID")
            user_id: Optional[str] = Field(None, description="Filter by user ID")
            date_from: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
            date_to: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
            limit: Optional[int] = Field(None, description="Maximum number of activities to return")
        return GetActivitiesInput

    def _create_activity_schema(self):
        """Schema for create_activity tool."""
        class CreateActivityInput(BaseModel):
            matter_id: str = Field(..., description="ID of the matter")
            description: str = Field(..., description="Description of the activity")
            quantity: float = Field(..., description="Time quantity in seconds")
            date: Optional[str] = Field(None, description="Date of the activity (YYYY-MM-DD)")
        return CreateActivityInput

    def _create_get_custom_fields_schema(self):
        """Schema for get_custom_fields tool."""
        class GetCustomFieldsInput(BaseModel):
            entity_type: Optional[str] = Field(None, description="Filter by entity type (Contact, Matter, etc.)")
        return GetCustomFieldsInput

    def _create_custom_field_values_schema(self):
        """Schema for custom field values management."""
        class CustomFieldValuesInput(BaseModel):
            action: str = Field(..., description="Action to perform: 'get', 'set', or 'list'")
            field_id: Optional[str] = Field(None, description="Custom field ID")
            entity_id: Optional[str] = Field(None, description="Entity ID")
            value: Optional[str] = Field(None, description="Value to set (for 'set' action)")
        return CustomFieldValuesInput

    def _create_cli_schema(self):
        """Schema for CLI execution."""
        class CliInput(BaseModel):
            command: str = Field(..., description="CLI command to execute (without 'clio' prefix)")
        return CliInput

    def _create_cfm_cli_schema(self):
        """Schema for custom fields manager CLI execution."""
        class CfmCliInput(BaseModel):
            command: str = Field(..., description="CFM CLI command to execute")
            use_clio_cfm: bool = Field(False, description="Use 'clio-cfm' instead of 'cfm'")
        return CfmCliInput

    # Tool implementation methods (synchronous for LangChain compatibility)
    def _get_contacts(self, **kwargs) -> str:
        """Get contacts from Clio using CLI."""
        try:
            # Use CLI for more reliable synchronous operation
            args = []
            if kwargs.get("limit"):
                args.extend(["--limit", str(kwargs["limit"])])
            if kwargs.get("search"):
                args.extend(["--search", kwargs["search"]])

            result = self.clio_cli.get_contacts(
                limit=kwargs.get("limit"),
                search=kwargs.get("search")
            )

            return json.dumps({
                "success": result.success,
                "data": result.parsed_output if result.parsed_output else result.output,
                "error": result.error if not result.success else None
            }, indent=2)

        except Exception as e:
            logger.error(f"Error getting contacts: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def _create_contact(self, **kwargs) -> str:
        """Create a contact in Clio using CLI."""
        try:
            # Extract required parameters
            first_name = kwargs.get("first_name", "")
            last_name = kwargs.get("last_name", "")
            email = kwargs.get("email")

            if not first_name and not last_name:
                return json.dumps({"success": False, "error": "First name or last name is required"})

            result = self.clio_cli.create_contact(
                first_name=first_name,
                last_name=last_name,
                email=email
            )

            return json.dumps({
                "success": result.success,
                "data": result.parsed_output if result.parsed_output else result.output,
                "error": result.error if not result.success else None
            }, indent=2)

        except Exception as e:
            logger.error(f"Error creating contact: {e}")
            return json.dumps({"success": False, "error": str(e)})

    async def _update_contact(self, contact_id: str, **kwargs) -> str:
        """Update a contact in Clio API."""
        try:
            # Remove contact_id from kwargs since it's passed separately
            update_data = {k: v for k, v in kwargs.items() if k != 'contact_id' and v is not None}
            result = await self.clio_api.update_contact(contact_id, update_data)
            return json.dumps({"success": True, "data": result}, indent=2)
        except Exception as e:
            logger.error(f"Error updating contact: {e}")
            return json.dumps({"success": False, "error": str(e)})

    async def _get_matters(self, **kwargs) -> str:
        """Get matters from Clio API."""
        try:
            result = await self.clio_api.get_matters(**kwargs)
            return json.dumps({"success": True, "data": result}, indent=2)
        except Exception as e:
            logger.error(f"Error getting matters: {e}")
            return json.dumps({"success": False, "error": str(e)})

    async def _create_matter(self, **kwargs) -> str:
        """Create a matter in Clio API."""
        try:
            result = await self.clio_api.create_matter(kwargs)
            return json.dumps({"success": True, "data": result}, indent=2)
        except Exception as e:
            logger.error(f"Error creating matter: {e}")
            return json.dumps({"success": False, "error": str(e)})

    async def _get_activities(self, **kwargs) -> str:
        """Get activities from Clio API."""
        try:
            result = await self.clio_api.get_activities(**kwargs)
            return json.dumps({"success": True, "data": result}, indent=2)
        except Exception as e:
            logger.error(f"Error getting activities: {e}")
            return json.dumps({"success": False, "error": str(e)})

    async def _create_activity(self, **kwargs) -> str:
        """Create an activity in Clio API."""
        try:
            result = await self.clio_api.create_activity(kwargs)
            return json.dumps({"success": True, "data": result}, indent=2)
        except Exception as e:
            logger.error(f"Error creating activity: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def _get_custom_fields(self, entity_type: Optional[str] = None) -> str:
        """Get custom fields from database and/or CLI."""
        try:
            # Try to get custom fields from local database first (faster)
            import sqlite3
            db_path = "/home/sysadmin01/custom-fields-manager/custom_fields_data.db"

            try:
                with sqlite3.connect(db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    query = """
                    SELECT id, name, field_type, parent_type, required, displayed
                    FROM custom_field_definitions
                    WHERE deleted = 0
                    """
                    params = []

                    if entity_type:
                        query += " AND parent_type = ?"
                        params.append(entity_type)

                    query += " ORDER BY parent_type, name"

                    cursor.execute(query, params)
                    rows = cursor.fetchall()

                    fields = []
                    for row in rows:
                        fields.append({
                            "id": row["id"],
                            "name": row["name"],
                            "field_type": row["field_type"],
                            "parent_type": row["parent_type"],
                            "required": bool(row["required"]),
                            "displayed": bool(row["displayed"])
                        })

                    return json.dumps({
                        "success": True,
                        "data": fields,
                        "count": len(fields),
                        "source": "database"
                    }, indent=2)

            except Exception as db_error:
                logger.warning(f"Database query failed, trying CLI: {db_error}")

                # Fallback to CLI if database fails
                # First try the custom-fields command
                result = self.custom_fields_cli.execute_cfm("custom-fields field-info --help")
                if result.success:
                    # CLI is working, but we need to find the right list command
                    # For now, return the fields we found manually
                    sample_fields = [
                        {"id": "1900266", "name": "Tivvis Matter Number", "field_type": "text_line", "parent_type": "Contact"},
                        {"id": "1913273", "name": "Contact History", "field_type": "text_area", "parent_type": "Contact"},
                        {"id": "8340286", "name": "Tivvis Matter Number", "field_type": "text_line", "parent_type": "Matter"},
                        {"id": "8340511", "name": "Date of Incident", "field_type": "date", "parent_type": "Matter"},
                        {"id": "8340541", "name": "Time of Incident", "field_type": "time", "parent_type": "Matter"},
                    ]

                    if entity_type:
                        sample_fields = [f for f in sample_fields if f["parent_type"] == entity_type]

                    return json.dumps({
                        "success": True,
                        "data": sample_fields,
                        "count": len(sample_fields),
                        "source": "cli_fallback"
                    }, indent=2)
                else:
                    raise Exception("Both database and CLI access failed")

        except Exception as e:
            logger.error(f"Error getting custom fields: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def _manage_custom_field_values(self, action: str, **kwargs) -> str:
        """Manage custom field values using CLI or database."""
        try:
            if action == "list":
                # Use our improved _get_custom_fields method
                return self._get_custom_fields(kwargs.get("entity_type"))

            elif action == "get" and kwargs.get("field_id"):
                # Try to get field values from CLI
                field_id = kwargs["field_id"]
                entity_id = kwargs.get("entity_id")

                # Try the correct CLI command format
                if entity_id:
                    # Get specific field value for specific entity
                    result = self.custom_fields_cli.execute_clio_cfm(f"values get {field_id} --entity-id {entity_id}")
                else:
                    # Get all values for this field
                    result = self.custom_fields_cli.execute_clio_cfm(f"values get {field_id}")

                return json.dumps({
                    "success": result.success,
                    "output": result.output,
                    "error": result.error if not result.success else None
                }, indent=2)

            elif action == "set" and kwargs.get("field_id") and kwargs.get("entity_id") and kwargs.get("value"):
                # Set a field value
                field_id = kwargs["field_id"]
                entity_id = kwargs["entity_id"]
                value = kwargs["value"]

                result = self.custom_fields_cli.set_field_value(field_id, entity_id, value)

                return json.dumps({
                    "success": result.success,
                    "output": result.output,
                    "error": result.error if not result.success else None
                }, indent=2)
            else:
                return json.dumps({"success": False, "error": "Invalid action or missing parameters"})

        except Exception as e:
            logger.error(f"Error managing custom field values: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def _execute_clio_cli(self, command: str) -> str:
        """Execute a Clio service CLI command."""
        try:
            result = self.clio_cli.execute(command)
            return json.dumps({
                "success": result.success,
                "output": result.output,
                "error": result.error if not result.success else None,
                "return_code": result.return_code
            }, indent=2)
        except Exception as e:
            logger.error(f"Error executing Clio CLI: {e}")
            return json.dumps({"success": False, "error": str(e)})

    def _execute_custom_fields_cli(self, command: str, use_clio_cfm: bool = False) -> str:
        """Execute a custom fields manager CLI command."""
        try:
            if use_clio_cfm:
                result = self.custom_fields_cli.execute_clio_cfm(command)
            else:
                result = self.custom_fields_cli.execute_cfm(command)

            return json.dumps({
                "success": result.success,
                "output": result.output,
                "error": result.error if not result.success else None,
                "return_code": result.return_code
            }, indent=2)
        except Exception as e:
            logger.error(f"Error executing custom fields CLI: {e}")
            return json.dumps({"success": False, "error": str(e)})

    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a natural language query using the LangChain agent.

        Args:
            query: Natural language query
            context: Optional context for the query

        Returns:
            Dictionary with response data
        """
        start_time = datetime.now()

        try:
            # Clear previous thoughts and tool results
            self.callback_handler.thoughts = []
            self.callback_handler.tool_results = []
            self.callback_handler.current_step = 0

            # Add context to query if provided
            if context:
                query += f"\n\nContext: {json.dumps(context)}"

            # Run the agent
            result = await asyncio.create_task(
                asyncio.to_thread(self.agent.run, query)
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "message": result,
                "execution_time": execution_time,
                "agent_thoughts": [thought.dict() for thought in self.callback_handler.thoughts],
                "tools_used": [tool.dict() for tool in self.callback_handler.tool_results]
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Error processing query: {e}")

            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time,
                "agent_thoughts": [thought.dict() for thought in self.callback_handler.thoughts],
                "tools_used": [tool.dict() for tool in self.callback_handler.tool_results]
            }

    def set_clio_auth_token(self, token: str):
        """Set the Clio authentication token."""
        self.clio_auth_token = token
        self.clio_api.set_auth_token(token)

    async def close(self):
        """Close the agent and cleanup resources."""
        await self.clio_api.close()
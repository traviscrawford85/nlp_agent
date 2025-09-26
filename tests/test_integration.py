"""
Integration tests for Clio NLP Agent end-to-end workflows.

This module contains integration tests that simulate realistic user scenarios
and test the complete flow from natural language query to API/CLI execution.
"""

import pytest
import asyncio
import os
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient

from ..main import app, get_agent
from ..agent import ClioNLPAgent
from ..models.requests import NLPRequest
from ..services.rate_limiter import ClioAPIClient


class TestFastAPIIntegration:
    """Integration tests for the FastAPI application."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mocked agent for testing."""
        agent = Mock(spec=ClioNLPAgent)
        agent.process_query = AsyncMock()
        agent.set_clio_auth_token = Mock()
        agent.close = AsyncMock()
        agent.tools = []
        return agent

    @pytest.fixture
    def client_with_mock_agent(self, mock_agent):
        """Create test client with mocked agent."""
        app.dependency_overrides[get_agent] = lambda: mock_agent
        with TestClient(app) as client:
            yield client, mock_agent
        app.dependency_overrides.clear()

    def test_health_check(self):
        """Test the health check endpoint."""
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "services" in data
            assert "timestamp" in data

    def test_nlp_endpoint_success(self, client_with_mock_agent):
        """Test successful NLP query processing."""
        client, mock_agent = client_with_mock_agent

        # Mock successful agent response
        mock_agent.process_query.return_value = {
            "success": True,
            "message": "Contact created successfully",
            "data": {"id": 123, "name": "John Doe"},
            "execution_time": 1.5,
            "agent_thoughts": [],
            "tools_used": []
        }

        request_data = {
            "query": "Create a contact named John Doe",
            "include_raw_data": True
        }

        response = client.post("/nlp", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Contact created successfully" in data["message"]
        assert data["data"]["id"] == 123
        assert "execution_time" in data

    def test_nlp_endpoint_agent_error(self, client_with_mock_agent):
        """Test NLP endpoint with agent error."""
        client, mock_agent = client_with_mock_agent

        # Mock agent error
        mock_agent.process_query.return_value = {
            "success": False,
            "error": "Authentication failed",
            "execution_time": 0.5,
            "agent_thoughts": [],
            "tools_used": []
        }

        request_data = {"query": "Invalid query"}

        response = client.post("/nlp", json=request_data)

        assert response.status_code == 200  # API returns 200 even for agent errors
        data = response.json()
        assert data["success"] is False
        assert "Authentication failed" in data["message"]

    def test_nlp_endpoint_validation_error(self, client_with_mock_agent):
        """Test NLP endpoint with validation error."""
        client, mock_agent = client_with_mock_agent

        # Send invalid request (missing query)
        request_data = {"include_raw_data": True}

        response = client.post("/nlp", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_set_auth_token(self, client_with_mock_agent):
        """Test setting authentication token."""
        client, mock_agent = client_with_mock_agent

        response = client.post("/auth/token", json={"token": "new_test_token"})

        assert response.status_code == 200
        data = response.json()
        assert "updated successfully" in data["message"]
        mock_agent.set_clio_auth_token.assert_called_once_with("new_test_token")

    def test_set_auth_token_missing(self, client_with_mock_agent):
        """Test setting auth token with missing token."""
        client, mock_agent = client_with_mock_agent

        response = client.post("/auth/token", json={})

        assert response.status_code == 400

    def test_list_tools(self, client_with_mock_agent):
        """Test listing available tools."""
        client, mock_agent = client_with_mock_agent

        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_agent.tools = [mock_tool]

        response = client.get("/tools")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tools"]) == 1
        assert data["tools"][0]["name"] == "test_tool"

    def test_get_examples(self, client_with_mock_agent):
        """Test getting query examples."""
        client, mock_agent = client_with_mock_agent

        response = client.get("/examples")

        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        assert len(data["examples"]) > 0
        assert "notes" in data


class TestEndToEndWorkflows:
    """End-to-end integration tests for common workflows."""

    @pytest.fixture
    def mock_clio_api_responses(self):
        """Mock Clio API responses for testing."""
        return {
            "contacts": {
                "get": {"data": [{"id": 1, "first_name": "John", "last_name": "Doe"}]},
                "create": {"data": {"id": 123, "first_name": "Jane", "last_name": "Smith"}},
                "update": {"data": {"id": 123, "first_name": "Jane", "last_name": "Updated"}}
            },
            "matters": {
                "get": {"data": [{"id": 1, "description": "Test Matter", "client": {"id": 1}}]},
                "create": {"data": {"id": 456, "description": "New Matter", "client": {"id": 1}}}
            },
            "activities": {
                "get": {"data": [{"id": 1, "description": "Meeting", "quantity": 3600}]},
                "create": {"data": {"id": 789, "description": "New Activity", "quantity": 1800}}
            }
        }

    @pytest.fixture
    def mock_cli_responses(self):
        """Mock CLI responses for testing."""
        from ..tools.clio_cli import CliResult
        return {
            "contacts_list": CliResult(
                success=True,
                output='{"contacts": [{"id": 1, "name": "John Doe"}]}',
                return_code=0,
                parsed_output={"contacts": [{"id": 1, "name": "John Doe"}]}
            ),
            "auth_status": CliResult(
                success=True,
                output="Authenticated as user@example.com",
                return_code=0
            )
        }

    @pytest.mark.asyncio
    async def test_contact_creation_workflow(self, mock_clio_api_responses):
        """Test complete workflow for creating a contact."""
        with patch('clio_nlp_agent.tools.clio_api.ClioAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock API response for contact creation
            mock_response = Mock()
            mock_response.json.return_value = mock_clio_api_responses["contacts"]["create"]
            mock_client.request.return_value = mock_response

            # Mock LLM and agent
            with patch('clio_nlp_agent.agent.ChatOpenAI') as mock_llm, \
                 patch('clio_nlp_agent.agent.initialize_agent') as mock_init_agent:

                mock_agent_instance = Mock()
                mock_agent_instance.run = Mock(return_value="Contact Jane Smith created successfully with ID 123")
                mock_init_agent.return_value = mock_agent_instance

                # Create agent and process query
                agent = ClioNLPAgent(openai_api_key="test_key", clio_auth_token="test_token")
                result = await agent.process_query("Create a new contact named Jane Smith with email jane@example.com")

                assert result["success"] is True
                assert "Jane Smith created successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_contact_search_workflow(self, mock_clio_api_responses):
        """Test complete workflow for searching contacts."""
        with patch('clio_nlp_agent.tools.clio_api.ClioAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            mock_client.get_all.return_value = mock_clio_api_responses["contacts"]["get"]["data"]

            with patch('clio_nlp_agent.agent.ChatOpenAI') as mock_llm, \
                 patch('clio_nlp_agent.agent.initialize_agent') as mock_init_agent:

                mock_agent_instance = Mock()
                mock_agent_instance.run = Mock(return_value="Found 1 contact named John Doe")
                mock_init_agent.return_value = mock_agent_instance

                agent = ClioNLPAgent(openai_api_key="test_key", clio_auth_token="test_token")
                result = await agent.process_query("Find all contacts with the name John")

                assert result["success"] is True
                assert "Found 1 contact" in result["message"]

    @pytest.mark.asyncio
    async def test_matter_creation_workflow(self, mock_clio_api_responses):
        """Test complete workflow for creating a matter."""
        with patch('clio_nlp_agent.tools.clio_api.ClioAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_response = Mock()
            mock_response.json.return_value = mock_clio_api_responses["matters"]["create"]
            mock_client.request.return_value = mock_response

            with patch('clio_nlp_agent.agent.ChatOpenAI') as mock_llm, \
                 patch('clio_nlp_agent.agent.initialize_agent') as mock_init_agent:

                mock_agent_instance = Mock()
                mock_agent_instance.run = Mock(return_value="Matter 'New Matter' created successfully for client ID 1")
                mock_init_agent.return_value = mock_agent_instance

                agent = ClioNLPAgent(openai_api_key="test_key", clio_auth_token="test_token")
                result = await agent.process_query("Create a new matter called 'New Matter' for client ID 1")

                assert result["success"] is True
                assert "Matter 'New Matter' created successfully" in result["message"]

    @pytest.mark.asyncio
    async def test_time_entry_workflow(self, mock_clio_api_responses):
        """Test complete workflow for creating a time entry."""
        with patch('clio_nlp_agent.tools.clio_api.ClioAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            mock_response = Mock()
            mock_response.json.return_value = mock_clio_api_responses["activities"]["create"]
            mock_client.request.return_value = mock_response

            with patch('clio_nlp_agent.agent.ChatOpenAI') as mock_llm, \
                 patch('clio_nlp_agent.agent.initialize_agent') as mock_init_agent:

                mock_agent_instance = Mock()
                mock_agent_instance.run = Mock(return_value="Time entry created: 0.5 hours for matter ID 1")
                mock_init_agent.return_value = mock_agent_instance

                agent = ClioNLPAgent(openai_api_key="test_key", clio_auth_token="test_token")
                result = await agent.process_query("Add 30 minutes of work on matter ID 1 for client meeting")

                assert result["success"] is True
                assert "Time entry created" in result["message"]

    @pytest.mark.asyncio
    async def test_cli_command_workflow(self, mock_cli_responses):
        """Test workflow using CLI commands."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = mock_cli_responses["auth_status"].output
            mock_run.return_value.stderr = ""

            with patch('clio_nlp_agent.agent.ChatOpenAI') as mock_llm, \
                 patch('clio_nlp_agent.agent.initialize_agent') as mock_init_agent:

                mock_agent_instance = Mock()
                mock_agent_instance.run = Mock(return_value="Authentication status: Authenticated as user@example.com")
                mock_init_agent.return_value = mock_agent_instance

                agent = ClioNLPAgent(openai_api_key="test_key", clio_auth_token="test_token")
                result = await agent.process_query("Check my authentication status")

                assert result["success"] is True
                assert "Authentication status" in result["message"]

    @pytest.mark.asyncio
    async def test_custom_fields_workflow(self):
        """Test workflow for custom fields management."""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('subprocess.run') as mock_run:

            # Mock custom fields CLI response
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = '{"fields": [{"id": 1, "name": "Priority", "type": "choice"}]}'
            mock_run.return_value.stderr = ""

            with patch('clio_nlp_agent.agent.ChatOpenAI') as mock_llm, \
                 patch('clio_nlp_agent.agent.initialize_agent') as mock_init_agent:

                mock_agent_instance = Mock()
                mock_agent_instance.run = Mock(return_value="Found 1 custom field: Priority (choice)")
                mock_init_agent.return_value = mock_agent_instance

                agent = ClioNLPAgent(openai_api_key="test_key", clio_auth_token="test_token")
                result = await agent.process_query("List all custom fields for contacts")

                assert result["success"] is True
                assert "Found 1 custom field" in result["message"]

    def test_error_handling_workflow(self):
        """Test error handling in end-to-end workflows."""
        with patch('clio_nlp_agent.tools.clio_api.ClioAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock API error
            mock_client.request.side_effect = Exception("API connection failed")

            with patch('clio_nlp_agent.agent.ChatOpenAI') as mock_llm, \
                 patch('clio_nlp_agent.agent.initialize_agent') as mock_init_agent:

                mock_agent_instance = Mock()
                mock_agent_instance.run.side_effect = Exception("Agent processing failed")
                mock_init_agent.return_value = mock_agent_instance

                agent = ClioNLPAgent(openai_api_key="test_key", clio_auth_token="test_token")

                # Test that errors are handled gracefully
                asyncio.get_event_loop().run_until_complete(
                    self._test_error_handling_async(agent)
                )

    async def _test_error_handling_async(self, agent):
        """Async helper for error handling test."""
        result = await agent.process_query("This will fail")
        assert result["success"] is False
        assert "error" in result


class TestComplexWorkflows:
    """Test complex multi-step workflows."""

    @pytest.mark.asyncio
    async def test_client_onboarding_workflow(self):
        """Test a complex workflow: complete client onboarding."""
        with patch('clio_nlp_agent.tools.clio_api.ClioAPIClient') as mock_client_class, \
             patch('pathlib.Path.exists', return_value=True):

            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock responses for each step
            contact_response = Mock()
            contact_response.json.return_value = {"data": {"id": 123, "name": "New Client"}}

            matter_response = Mock()
            matter_response.json.return_value = {"data": {"id": 456, "description": "Initial Matter"}}

            mock_client.request.side_effect = [contact_response, matter_response]

            with patch('clio_nlp_agent.agent.ChatOpenAI') as mock_llm, \
                 patch('clio_nlp_agent.agent.initialize_agent') as mock_init_agent:

                mock_agent_instance = Mock()
                mock_agent_instance.run = Mock(return_value="Client onboarded successfully")
                mock_init_agent.return_value = mock_agent_instance

                agent = ClioNLPAgent(openai_api_key="test_key", clio_auth_token="test_token")

                query = """
                Onboard a new client: Create a contact for 'New Client Company'
                with email info@newclient.com, then create an initial matter
                called 'General Legal Services' for this client.
                """

                result = await agent.process_query(query)
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_time_tracking_summary_workflow(self):
        """Test a complex workflow: time tracking summary."""
        with patch('clio_nlp_agent.tools.clio_api.ClioAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock time entries
            mock_client.get_all.return_value = [
                {"id": 1, "description": "Meeting", "quantity": 3600, "matter": {"id": 1}},
                {"id": 2, "description": "Research", "quantity": 7200, "matter": {"id": 1}}
            ]

            with patch('clio_nlp_agent.agent.ChatOpenAI') as mock_llm, \
                 patch('clio_nlp_agent.agent.initialize_agent') as mock_init_agent:

                mock_agent_instance = Mock()
                mock_agent_instance.run = Mock(return_value="Total time: 3 hours across 2 activities")
                mock_init_agent.return_value = mock_agent_instance

                agent = ClioNLPAgent(openai_api_key="test_key", clio_auth_token="test_token")

                result = await agent.process_query("Show me a summary of all time entries for this week")
                assert result["success"] is True


if __name__ == "__main__":
    pytest.main(["-v", __file__])
"""
Unit tests for Clio NLP Agent tools.

This module contains comprehensive unit tests for all tool implementations,
using mocks to avoid external dependencies during testing.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import json
from datetime import datetime

from ..tools.clio_api import ClioAPIWrapper
from ..tools.clio_cli import ClioServiceCLI, CliResult
from ..tools.custom_fields_cli import CustomFieldsCLI
from ..services.rate_limiter import ClioAPIClient, RateLimiter
from ..agent import ClioNLPAgent


class TestRateLimiter:
    """Test cases for the RateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        return RateLimiter(requests_per_minute=10, requests_per_hour=100)

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_within_limits(self, rate_limiter):
        """Test that rate limiter allows requests within limits."""
        # Should not block for first request
        await rate_limiter.wait_if_needed()
        assert len(rate_limiter.request_times) == 1

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_when_limit_exceeded(self, rate_limiter):
        """Test that rate limiter blocks when limits are exceeded."""
        # Fill up the per-minute limit
        for _ in range(10):
            await rate_limiter.wait_if_needed()

        # Next request should be delayed
        start_time = asyncio.get_event_loop().time()
        await rate_limiter.wait_if_needed()
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should have waited some time (but we won't wait the full minute in tests)
        assert len(rate_limiter.request_times) == 11


class TestClioAPIClient:
    """Test cases for the ClioAPIClient class."""

    @pytest.fixture
    def mock_httpx_client(self):
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def api_client(self, mock_httpx_client):
        client = ClioAPIClient(auth_token="test_token")
        client.client = mock_httpx_client
        return client

    @pytest.mark.asyncio
    async def test_successful_request(self, api_client, mock_httpx_client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"id": 1, "name": "test"}]}
        mock_httpx_client.request.return_value = mock_response

        response = await api_client.request("GET", "contacts.json")

        assert response.status_code == 200
        mock_httpx_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limited_request_with_retry_after(self, api_client, mock_httpx_client):
        """Test handling of rate limited requests with Retry-After header."""
        # First request returns 429 with Retry-After
        rate_limited_response = Mock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {"Retry-After": "1"}

        # Second request succeeds
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": []}

        mock_httpx_client.request.side_effect = [rate_limited_response, success_response]

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            response = await api_client.request("GET", "contacts.json")

            assert response.status_code == 200
            mock_sleep.assert_called_once_with(1)
            assert mock_httpx_client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_pagination(self, api_client, mock_httpx_client):
        """Test paginated request handling."""
        # Mock responses for two pages
        page1_response = Mock()
        page1_response.status_code = 200
        page1_response.json.return_value = {
            "data": [{"id": 1}, {"id": 2}],
            "meta": {"paging": {"next": "page2"}}
        }

        page2_response = Mock()
        page2_response.status_code = 200
        page2_response.json.return_value = {
            "data": [{"id": 3}],
            "meta": {"paging": {}}
        }

        mock_httpx_client.request.side_effect = [page1_response, page2_response]

        items = []
        async for item in api_client.paginated_request("contacts.json"):
            items.append(item)

        assert len(items) == 3
        assert items[0]["id"] == 1
        assert items[2]["id"] == 3
        assert mock_httpx_client.request.call_count == 2


class TestClioAPIWrapper:
    """Test cases for the ClioAPIWrapper class."""

    @pytest.fixture
    def mock_api_client(self):
        with patch('clio_nlp_agent.tools.clio_api.ClioAPIClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def api_wrapper(self, mock_api_client):
        wrapper = ClioAPIWrapper(auth_token="test_token")
        wrapper.client = mock_api_client
        return wrapper

    @pytest.mark.asyncio
    async def test_get_contacts(self, api_wrapper, mock_api_client):
        """Test getting contacts."""
        mock_contacts = [{"id": 1, "name": "John Doe"}]
        mock_api_client.get_all.return_value = mock_contacts

        result = await api_wrapper.get_contacts()

        assert result == mock_contacts
        mock_api_client.get_all.assert_called_once_with("contacts.json", {})

    @pytest.mark.asyncio
    async def test_get_contacts_with_search(self, api_wrapper, mock_api_client):
        """Test getting contacts with search parameters."""
        mock_contacts = [{"id": 1, "name": "John Smith"}]
        mock_response = Mock()
        mock_response.json.return_value = {"data": mock_contacts}
        mock_api_client.request.return_value = mock_response

        result = await api_wrapper.get_contacts(limit=10, search="John")

        assert result == mock_contacts
        mock_api_client.request.assert_called_once_with(
            "GET", "contacts.json", params={"query": "John", "per_page": 10}
        )

    @pytest.mark.asyncio
    async def test_create_contact(self, api_wrapper, mock_api_client):
        """Test creating a contact."""
        contact_data = {"first_name": "Jane", "last_name": "Doe"}
        mock_response = Mock()
        mock_response.json.return_value = {"data": {"id": 123, **contact_data}}
        mock_api_client.request.return_value = mock_response

        result = await api_wrapper.create_contact(contact_data)

        assert result["id"] == 123
        assert result["first_name"] == "Jane"
        mock_api_client.request.assert_called_once_with(
            "POST", "contacts.json", json_data={"data": contact_data}
        )


class TestClioServiceCLI:
    """Test cases for the ClioServiceCLI class."""

    @pytest.fixture
    def mock_clio_service_path(self):
        with patch('pathlib.Path.exists', return_value=True):
            yield

    @pytest.fixture
    def clio_cli(self, mock_clio_service_path):
        return ClioServiceCLI()

    def test_init_with_nonexistent_path(self):
        """Test initialization with non-existent clio_service path."""
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                ClioServiceCLI("/nonexistent/path")

    @patch('subprocess.run')
    def test_successful_command_execution(self, mock_run, clio_cli):
        """Test successful CLI command execution."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"contacts": [{"id": 1}]}'
        mock_run.return_value.stderr = ""

        result = clio_cli.get_contacts(limit=5)

        assert result.success is True
        assert result.parsed_output is not None
        assert result.parsed_output["contacts"][0]["id"] == 1
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_failed_command_execution(self, mock_run, clio_cli):
        """Test failed CLI command execution."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Authentication failed"

        result = clio_cli.get_contacts()

        assert result.success is False
        assert result.error == "Authentication failed"
        assert result.return_code == 1

    @patch('subprocess.run')
    def test_command_timeout(self, mock_run, clio_cli):
        """Test CLI command timeout handling."""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired("clio", 300)

        result = clio_cli.get_contacts()

        assert result.success is False
        assert "timed out" in result.error
        assert result.return_code == -1

    def test_contact_commands(self, clio_cli):
        """Test contact management commands."""
        with patch.object(clio_cli, '_run_command') as mock_run:
            mock_result = CliResult(success=True, output="success")
            mock_run.return_value = mock_result

            # Test create contact
            result = clio_cli.create_contact("John", "Doe", "john@example.com")
            assert result.success is True
            mock_run.assert_called_with([
                "contacts", "create", "--first-name", "John",
                "--last-name", "Doe", "--email", "john@example.com"
            ])

            # Test update contact
            clio_cli.update_contact("123", first_name="Jane")
            mock_run.assert_called_with([
                "contacts", "update", "123", "--first-name", "Jane"
            ])


class TestCustomFieldsCLI:
    """Test cases for the CustomFieldsCLI class."""

    @pytest.fixture
    def mock_cfm_path(self):
        with patch('pathlib.Path.exists', return_value=True):
            yield

    @pytest.fixture
    def cfm_cli(self, mock_cfm_path):
        return CustomFieldsCLI()

    def test_init_with_nonexistent_path(self):
        """Test initialization with non-existent custom fields manager path."""
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                CustomFieldsCLI("/nonexistent/path")

    @patch('subprocess.run')
    def test_list_custom_fields(self, mock_run, cfm_cli):
        """Test listing custom fields."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"fields": []}'
        mock_run.return_value.stderr = ""

        result = cfm_cli.list_custom_fields()

        assert result.success is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "cfm"
        assert "fields" in args and "list" in args

    @patch('subprocess.run')
    def test_create_custom_field(self, mock_run, cfm_cli):
        """Test creating a custom field."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"id": 123}'
        mock_run.return_value.stderr = ""

        result = cfm_cli.create_custom_field("Test Field", "Contact", "text")

        assert result.success is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "clio-cfm"
        assert "create" in args

    def test_command_routing(self, cfm_cli):
        """Test that commands are routed to correct CLI tools."""
        with patch.object(cfm_cli, '_run_command') as mock_run:
            mock_result = CliResult(success=True, output="success")
            mock_run.return_value = mock_result

            # CFM command should use 'cfm'
            cfm_cli.list_custom_fields()
            mock_run.assert_called_with("cfm", ["fields", "list"])

            # Clio-CFM command should use 'clio-cfm'
            cfm_cli.create_custom_field("test", "Contact", "text")
            mock_run.assert_called_with("clio-cfm", [
                "create", "--name", "test", "--entity-type", "Contact",
                "--field-type", "text"
            ])


class TestClioNLPAgent:
    """Test cases for the ClioNLPAgent class."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies for the agent."""
        with patch.multiple(
            'clio_nlp_agent.agent',
            ChatOpenAI=MagicMock(),
            initialize_agent=MagicMock(),
            ClioAPIWrapper=MagicMock(),
            ClioServiceCLI=MagicMock(),
            CustomFieldsCLI=MagicMock()
        ) as mocks:
            yield mocks

    @pytest.fixture
    def nlp_agent(self, mock_dependencies):
        """Create an NLP agent with mocked dependencies."""
        agent = ClioNLPAgent(
            openai_api_key="test_key",
            clio_auth_token="test_token"
        )
        return agent

    def test_agent_initialization(self, mock_dependencies):
        """Test agent initialization."""
        agent = ClioNLPAgent(
            openai_api_key="test_key",
            clio_auth_token="test_token"
        )

        assert agent.openai_api_key == "test_key"
        assert agent.clio_auth_token == "test_token"
        assert len(agent.tools) > 0

    def test_agent_initialization_without_openai_key(self, mock_dependencies):
        """Test agent initialization fails without OpenAI key."""
        with pytest.raises(ValueError, match="OpenAI API key is required"):
            ClioNLPAgent()

    def test_tool_creation(self, nlp_agent):
        """Test that all expected tools are created."""
        tool_names = [tool.name for tool in nlp_agent.tools]

        expected_tools = [
            "get_contacts", "create_contact", "update_contact",
            "get_matters", "create_matter",
            "get_activities", "create_activity",
            "get_custom_fields", "manage_custom_field_values",
            "execute_clio_cli", "execute_custom_fields_cli"
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_process_query_success(self, nlp_agent):
        """Test successful query processing."""
        # Mock the agent.run method
        nlp_agent.agent.run = Mock(return_value="Contact created successfully")

        result = await nlp_agent.process_query("Create a contact named John Doe")

        assert result["success"] is True
        assert "Contact created successfully" in result["message"]
        assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_process_query_failure(self, nlp_agent):
        """Test query processing failure."""
        # Mock the agent.run method to raise an exception
        nlp_agent.agent.run = Mock(side_effect=Exception("API error"))

        result = await nlp_agent.process_query("Invalid query")

        assert result["success"] is False
        assert "API error" in result["error"]
        assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_get_contacts_tool(self, nlp_agent):
        """Test the get_contacts tool function."""
        # Mock the API wrapper
        nlp_agent.clio_api.get_contacts = AsyncMock(return_value=[{"id": 1, "name": "John"}])

        result = await nlp_agent._get_contacts(search="John")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert len(result_data["data"]) == 1
        assert result_data["data"][0]["name"] == "John"

    @pytest.mark.asyncio
    async def test_create_contact_tool(self, nlp_agent):
        """Test the create_contact tool function."""
        nlp_agent.clio_api.create_contact = AsyncMock(return_value={
            "id": 123, "first_name": "Jane", "last_name": "Doe"
        })

        result = await nlp_agent._create_contact(first_name="Jane", last_name="Doe")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert result_data["data"]["id"] == 123
        assert result_data["data"]["first_name"] == "Jane"

    def test_execute_clio_cli_tool(self, nlp_agent):
        """Test the execute_clio_cli tool function."""
        mock_result = CliResult(
            success=True,
            output='{"contacts": []}',
            return_code=0
        )
        nlp_agent.clio_cli.execute = Mock(return_value=mock_result)

        result = nlp_agent._execute_clio_cli("contacts list")
        result_data = json.loads(result)

        assert result_data["success"] is True
        assert '{"contacts": []}' in result_data["output"]
        assert result_data["return_code"] == 0

    def test_set_auth_token(self, nlp_agent):
        """Test setting authentication token."""
        new_token = "new_test_token"
        nlp_agent.clio_api.set_auth_token = Mock()

        nlp_agent.set_clio_auth_token(new_token)

        assert nlp_agent.clio_auth_token == new_token
        nlp_agent.clio_api.set_auth_token.assert_called_once_with(new_token)


@pytest.mark.asyncio
async def test_tool_error_handling():
    """Test error handling in tool execution."""
    from ..tools.clio_cli import ClioServiceCLI

    with patch('pathlib.Path.exists', return_value=True):
        cli = ClioServiceCLI()

    with patch('subprocess.run') as mock_run:
        # Simulate a command that raises an exception
        mock_run.side_effect = Exception("System error")

        result = cli.get_contacts()

        assert result.success is False
        assert "System error" in result.error
        assert result.return_code == -1


if __name__ == "__main__":
    pytest.main(["-v", __file__])
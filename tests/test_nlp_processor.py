"""Tests for NLP processor."""

import pytest

from nlp_agent.nlp.processor import NLPProcessor
from nlp_agent.models.schemas import HTTPMethod, CLIService


@pytest.fixture
def processor():
    """NLP processor fixture."""
    return NLPProcessor()


@pytest.mark.asyncio
async def test_health_query_processing(processor):
    """Test processing health-related queries."""
    result = await processor.process_query("check health status", {}, {})
    
    assert "api_calls" in result
    assert len(result["api_calls"]) > 0
    
    api_call = result["api_calls"][0]
    assert api_call.endpoint == "/health"
    assert api_call.method == HTTPMethod.GET


@pytest.mark.asyncio
async def test_list_queries_processing(processor):
    """Test processing query list requests."""
    result = await processor.process_query("show me all queries", {}, {})
    
    assert "api_calls" in result
    assert len(result["api_calls"]) > 0
    
    api_call = result["api_calls"][0]
    assert api_call.endpoint == "/queries"
    assert api_call.method == HTTPMethod.GET


@pytest.mark.asyncio
async def test_clio_list_processing(processor):
    """Test processing Clio list commands."""
    result = await processor.process_query("clio list", {}, {})
    
    assert "cli_calls" in result
    assert len(result["cli_calls"]) > 0
    
    cli_call = result["cli_calls"][0]
    assert cli_call.command == CLIService.CLIO_SERVICE
    assert "list" in cli_call.args


@pytest.mark.asyncio
async def test_custom_fields_processing(processor):
    """Test processing custom fields commands."""
    result = await processor.process_query("list custom fields", {}, {})
    
    assert "cli_calls" in result
    assert len(result["cli_calls"]) > 0
    
    cli_call = result["cli_calls"][0]
    assert cli_call.command == CLIService.CUSTOM_FIELDS_MANAGER
    assert "list" in cli_call.args


@pytest.mark.asyncio
async def test_create_custom_field_processing(processor):
    """Test processing custom field creation."""
    result = await processor.process_query("create custom field named test_field", {}, {})
    
    assert "cli_calls" in result
    assert len(result["cli_calls"]) > 0
    
    cli_call = result["cli_calls"][0]
    assert cli_call.command == CLIService.CUSTOM_FIELDS_MANAGER
    assert "create" in cli_call.args
    assert "test_field" in cli_call.args


@pytest.mark.asyncio
async def test_unknown_query_processing(processor):
    """Test processing unknown queries."""
    result = await processor.process_query("some random unknown query", {}, {})
    
    # Should still return a result with low confidence
    assert "result" in result
    assert "confidence_score" in result
    assert result["confidence_score"] < 0.5


@pytest.mark.asyncio
async def test_confidence_scoring(processor):
    """Test confidence score calculation."""
    # High confidence query
    high_conf_result = await processor.process_query("health", {}, {})
    
    # Low confidence query
    low_conf_result = await processor.process_query("xyz unknown query abc", {}, {})
    
    assert high_conf_result["confidence_score"] > low_conf_result["confidence_score"]


@pytest.mark.asyncio
async def test_query_with_context(processor):
    """Test processing query with context."""
    context = {"user_id": "test_user", "session_id": "test_session"}
    result = await processor.process_query("show queries", context, {})
    
    assert "result" in result
    # Context should be considered in processing
    assert result["result"]["query"] == "show queries"


@pytest.mark.asyncio
async def test_result_structure(processor):
    """Test that results have expected structure."""
    result = await processor.process_query("health check", {}, {})
    
    # Check required fields
    assert "result" in result
    assert "api_calls" in result
    assert "cli_calls" in result
    assert "confidence_score" in result
    assert "tokens_used" in result
    
    # Check result structure
    assert "query" in result["result"]
    assert "interpretation" in result["result"]
    assert "suggested_actions" in result["result"]
    
    # Check types
    assert isinstance(result["api_calls"], list)
    assert isinstance(result["cli_calls"], list)
    assert isinstance(result["confidence_score"], float)
    assert isinstance(result["tokens_used"], int)
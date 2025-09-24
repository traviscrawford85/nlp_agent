"""FastAPI dependencies."""

from nlp_agent.api.services import QueryService, CLIService
from nlp_agent.cli_integration.manager import CLIManager
from nlp_agent.nlp.processor import NLPProcessor


def get_query_service() -> QueryService:
    """Get query service instance."""
    nlp_processor = NLPProcessor()
    cli_manager = CLIManager()
    return QueryService(nlp_processor, cli_manager)


def get_cli_service() -> CLIService:
    """Get CLI service instance."""
    cli_manager = CLIManager()
    return CLIService(cli_manager)
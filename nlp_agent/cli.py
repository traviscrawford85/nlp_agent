"""Command-line interface for NLP Agent."""

import asyncio
import json
from datetime import datetime
from typing import Optional

import click
import structlog

from nlp_agent.client.client import NLPAgentClient, SyncNLPAgentClient
from nlp_agent.models.schemas import QueryStatus

logger = structlog.get_logger()


@click.group()
@click.option("--base-url", default="http://localhost:8000", help="API base URL")
@click.option("--timeout", default=30.0, help="Request timeout in seconds")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def main(ctx, base_url: str, timeout: float, verbose: bool):
    """NLP Agent CLI - Natural language processing with API and CLI integration."""
    if verbose:
        structlog.configure(
            processors=[
                structlog.dev.ConsoleRenderer()
            ],
            logger_factory=structlog.PrintLoggerFactory(),
            level="DEBUG",
        )
    
    # Store context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["client_kwargs"] = {"base_url": base_url, "timeout": timeout}


@main.command()
@click.pass_context
def health(ctx):
    """Check API health status."""
    client = SyncNLPAgentClient(**ctx.obj["client_kwargs"])
    
    try:
        response = client.health_check()
        click.echo(f"Status: {response.status}")
        click.echo(f"Version: {response.version}")
        click.echo(f"Timestamp: {response.timestamp}")
        
        if response.status == "healthy":
            click.secho("✓ API is healthy", fg="green")
        else:
            click.secho("✗ API is unhealthy", fg="red")
            
    except Exception as e:
        click.secho(f"✗ Health check failed: {e}", fg="red")


@main.command()
@click.argument("query")
@click.option("--context", help="JSON context for the query")
@click.option("--timeout", type=int, help="Query timeout in seconds")
@click.option("--metadata", is_flag=True, help="Include processing metadata")
@click.option("--json-output", is_flag=True, help="Output raw JSON response")
@click.pass_context
def query(ctx, query: str, context: Optional[str], timeout: Optional[int], metadata: bool, json_output: bool):
    """Process a natural language query."""
    client = SyncNLPAgentClient(**ctx.obj["client_kwargs"])
    
    try:
        # Parse context if provided
        parsed_context = None
        if context:
            try:
                parsed_context = json.loads(context)
            except json.JSONDecodeError:
                click.secho(f"✗ Invalid JSON context: {context}", fg="red")
                return
        
        # Process the query
        response = client.process_query(
            query=query,
            context=parsed_context,
            timeout=timeout,
            include_metadata=metadata,
        )
        
        if json_output:
            click.echo(json.dumps(response.dict(), indent=2, default=str))
        else:
            click.echo(f"Query ID: {response.id}")
            click.echo(f"Status: {response.status}")
            click.echo(f"Created: {response.created_at}")
            
            if response.completed_at:
                click.echo(f"Completed: {response.completed_at}")
            
            if response.result:
                click.echo("\nResult:")
                if isinstance(response.result, dict):
                    for key, value in response.result.items():
                        click.echo(f"  {key}: {value}")
                else:
                    click.echo(f"  {response.result}")
            
            if response.api_calls:
                click.echo(f"\nAPI Calls: {len(response.api_calls)}")
                for i, call in enumerate(response.api_calls, 1):
                    click.echo(f"  {i}. {call.method} {call.endpoint}")
            
            if response.cli_calls:
                click.echo(f"\nCLI Calls: {len(response.cli_calls)}")
                for i, call in enumerate(response.cli_calls, 1):
                    click.echo(f"  {i}. {call.command} {' '.join(call.args)}")
            
            if response.metadata and metadata:
                click.echo("\nMetadata:")
                if response.metadata.processing_time_ms:
                    click.echo(f"  Processing time: {response.metadata.processing_time_ms:.2f}ms")
                if response.metadata.tokens_used:
                    click.echo(f"  Tokens used: {response.metadata.tokens_used}")
                if response.metadata.confidence_score:
                    click.echo(f"  Confidence: {response.metadata.confidence_score:.2f}")
            
            # Status indicator
            if response.status == QueryStatus.COMPLETED:
                click.secho("✓ Query completed successfully", fg="green")
            elif response.status == QueryStatus.FAILED:
                click.secho("✗ Query failed", fg="red")
            elif response.status == QueryStatus.PROCESSING:
                click.secho("⏳ Query is processing", fg="yellow")
            else:
                click.secho("⏸ Query is pending", fg="blue")
                
    except Exception as e:
        click.secho(f"✗ Query processing failed: {e}", fg="red")


@main.command()
@click.option("--page", default=1, help="Page number")
@click.option("--limit", default=20, help="Items per page")
@click.option("--status", type=click.Choice(["pending", "processing", "completed", "failed"]), help="Filter by status")
@click.option("--created-after", help="Filter by creation date (ISO format)")
@click.option("--json-output", is_flag=True, help="Output raw JSON response")
@click.pass_context
def list_queries(ctx, page: int, limit: int, status: Optional[str], created_after: Optional[str], json_output: bool):
    """List processed queries with pagination and filtering."""
    client = SyncNLPAgentClient(**ctx.obj["client_kwargs"])
    
    try:
        # Parse created_after if provided
        parsed_created_after = None
        if created_after:
            try:
                parsed_created_after = datetime.fromisoformat(created_after)
            except ValueError:
                click.secho(f"✗ Invalid date format: {created_after}", fg="red")
                return
        
        # Parse status
        parsed_status = None
        if status:
            parsed_status = QueryStatus(status)
        
        # List queries
        response = client.list_queries(
            page=page,
            limit=limit,
            status=parsed_status,
            created_after=parsed_created_after,
        )
        
        if json_output:
            click.echo(json.dumps(response.dict(), indent=2, default=str))
        else:
            # Display pagination info
            pagination = response.pagination
            click.echo(f"Page {pagination.page} of {pagination.pages} ({pagination.total} total)")
            
            if not response.queries:
                click.echo("No queries found.")
                return
            
            # Display queries
            for query in response.queries:
                click.echo(f"\n{query.id} ({query.status})")
                click.echo(f"  Created: {query.created_at}")
                if query.completed_at:
                    click.echo(f"  Completed: {query.completed_at}")
                
                if query.result and isinstance(query.result, dict) and "query" in query.result:
                    preview = query.result["query"][:100]
                    if len(query.result["query"]) > 100:
                        preview += "..."
                    click.echo(f"  Query: {preview}")
            
            # Navigation hints
            if pagination.has_prev or pagination.has_next:
                click.echo("\nNavigation:")
                if pagination.has_prev:
                    click.echo(f"  Previous: --page {page - 1}")
                if pagination.has_next:
                    click.echo(f"  Next: --page {page + 1}")
                    
    except Exception as e:
        click.secho(f"✗ Failed to list queries: {e}", fg="red")


@main.command()
@click.argument("service", type=click.Choice(["clio_service", "custom-fields-manager"]))
@click.argument("command")
@click.option("--args", multiple=True, help="Command arguments")
@click.option("--input-data", help="JSON input data")
@click.option("--json-output", is_flag=True, help="Output raw JSON response")
@click.pass_context
def cli(ctx, service: str, command: str, args: tuple, input_data: Optional[str], json_output: bool):
    """Execute CLI commands on local services."""
    client = SyncNLPAgentClient(**ctx.obj["client_kwargs"])
    
    try:
        # Parse input data if provided
        parsed_input_data = None
        if input_data:
            try:
                parsed_input_data = json.loads(input_data)
            except json.JSONDecodeError:
                click.secho(f"✗ Invalid JSON input data: {input_data}", fg="red")
                return
        
        # Execute CLI command
        response = client.execute_cli(
            service=service,
            command=command,
            args=list(args) if args else None,
            input_data=parsed_input_data,
        )
        
        if json_output:
            click.echo(json.dumps(response.dict(), indent=2, default=str))
        else:
            click.echo(f"Exit Code: {response.exit_code}")
            click.echo(f"Duration: {response.duration_ms:.2f}ms")
            
            if response.stdout:
                click.echo("\nStdout:")
                click.echo(response.stdout)
            
            if response.stderr:
                click.echo("\nStderr:")
                click.echo(response.stderr)
            
            if response.parsed_output:
                click.echo("\nParsed Output:")
                click.echo(json.dumps(response.parsed_output, indent=2))
            
            # Status indicator
            if response.exit_code == 0:
                click.secho("✓ Command executed successfully", fg="green")
            else:
                click.secho(f"✗ Command failed with exit code {response.exit_code}", fg="red")
                
    except Exception as e:
        click.secho(f"✗ CLI execution failed: {e}", fg="red")


@main.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the NLP Agent API server."""
    try:
        import uvicorn
        uvicorn.run(
            "nlp_agent.api.main:app",
            host=host,
            port=port,
            reload=reload,
        )
    except ImportError:
        click.secho("✗ uvicorn not installed. Install with: pip install uvicorn", fg="red")
    except Exception as e:
        click.secho(f"✗ Failed to start server: {e}", fg="red")


if __name__ == "__main__":
    main()
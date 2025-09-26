"""
Wrapper for the custom-fields-manager CLI tool.

This module provides a Python interface to the custom-fields-manager CLI tool
located at ~/custom-fields-manager with 'cfm' and 'clio-cfm' commands.
"""

import subprocess
import json
import os
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from loguru import logger
from pydantic import BaseModel

from tools.clio_cli import CliResult  # Reuse the CliResult model


class CustomFieldsCLI:
    """Python wrapper for the custom-fields-manager CLI tool."""

    def __init__(self, cfm_path: str = "/home/sysadmin01/custom-fields-manager"):
        self.cfm_path = Path(cfm_path)
        self.cfm_command = "cfm"
        self.clio_cfm_command = "clio-cfm"

        if not self.cfm_path.exists():
            raise FileNotFoundError(f"Custom fields manager directory not found: {cfm_path}")

    def _run_command(self, command: str, args: List[str], cwd: Optional[str] = None) -> CliResult:
        """
        Execute a custom fields CLI command.

        Args:
            command: Base command ('cfm' or 'clio-cfm')
            args: Command arguments
            cwd: Working directory (defaults to cfm path)

        Returns:
            CliResult with command output and status
        """
        if cwd is None:
            cwd = str(self.cfm_path)

        cmd = [command] + args
        logger.debug(f"Executing command: {' '.join(cmd)} in {cwd}")

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            cli_result = CliResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip(),
                return_code=result.returncode
            )

            # Try to parse JSON output
            if cli_result.success and cli_result.output:
                try:
                    cli_result.parsed_output = json.loads(cli_result.output)
                except json.JSONDecodeError:
                    # Not JSON, that's fine
                    pass

            logger.debug(f"Command {'succeeded' if cli_result.success else 'failed'}: {cli_result.return_code}")
            return cli_result

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return CliResult(
                success=False,
                output="",
                error="Command timed out after 300 seconds",
                return_code=-1
            )
        except Exception as e:
            logger.error(f"Error executing command: {e}")
            return CliResult(
                success=False,
                output="",
                error=str(e),
                return_code=-1
            )

    # CFM Commands (local database operations)
    def list_custom_fields(self, entity_type: Optional[str] = None) -> CliResult:
        """List custom fields from local database."""
        args = ["fields", "list"]
        if entity_type:
            args.extend(["--type", entity_type])
        return self._run_command(self.cfm_command, args)

    def get_field_details(self, field_id: str) -> CliResult:
        """Get detailed information about a custom field."""
        return self._run_command(self.cfm_command, ["fields", "get", field_id])

    def search_fields(self, query: str) -> CliResult:
        """Search for custom fields by name or description."""
        return self._run_command(self.cfm_command, ["fields", "search", query])

    def get_field_usage(self, field_id: str) -> CliResult:
        """Get usage statistics for a custom field."""
        return self._run_command(self.cfm_command, ["fields", "usage", field_id])

    def sync_from_api(self) -> CliResult:
        """Sync custom fields from Clio API to local database."""
        return self._run_command(self.cfm_command, ["sync", "from-api"])

    def export_fields(self, format: str = "json", output_file: Optional[str] = None) -> CliResult:
        """Export custom fields data."""
        args = ["export", "--format", format]
        if output_file:
            args.extend(["--output", output_file])
        return self._run_command(self.cfm_command, args)

    # Clio-CFM Commands (API operations)
    def create_custom_field(self, name: str, entity_type: str, field_type: str, **kwargs) -> CliResult:
        """Create a new custom field in Clio."""
        args = ["create", "--name", name, "--entity-type", entity_type, "--field-type", field_type]

        # Add optional parameters
        for key, value in kwargs.items():
            if value is not None:
                args.extend([f"--{key.replace('_', '-')}", str(value)])

        return self._run_command(self.clio_cfm_command, args)

    def update_custom_field(self, field_id: str, **kwargs) -> CliResult:
        """Update an existing custom field in Clio."""
        args = ["update", field_id]

        for key, value in kwargs.items():
            if value is not None:
                args.extend([f"--{key.replace('_', '-')}", str(value)])

        return self._run_command(self.clio_cfm_command, args)

    def delete_custom_field(self, field_id: str, confirm: bool = False) -> CliResult:
        """Delete a custom field from Clio."""
        args = ["delete", field_id]
        if confirm:
            args.append("--confirm")
        return self._run_command(self.clio_cfm_command, args)

    def get_field_values(self, field_id: str, entity_id: Optional[str] = None) -> CliResult:
        """Get values for a custom field."""
        args = ["values", "get", field_id]
        if entity_id:
            args.extend(["--entity-id", entity_id])
        return self._run_command(self.clio_cfm_command, args)

    def set_field_value(self, field_id: str, entity_id: str, value: str) -> CliResult:
        """Set a value for a custom field on an entity."""
        return self._run_command(
            self.clio_cfm_command,
            ["values", "set", field_id, entity_id, value]
        )

    def bulk_update_values(self, field_id: str, csv_file: str) -> CliResult:
        """Bulk update custom field values from CSV file."""
        return self._run_command(
            self.clio_cfm_command,
            ["values", "bulk-update", field_id, "--csv", csv_file]
        )

    # Analysis and reporting commands
    def analyze_field_usage(self) -> CliResult:
        """Analyze usage patterns across all custom fields."""
        return self._run_command(self.cfm_command, ["analyze", "usage"])

    def generate_field_report(self, report_type: str = "summary") -> CliResult:
        """Generate a report about custom fields."""
        return self._run_command(self.cfm_command, ["report", report_type])

    def find_duplicate_fields(self) -> CliResult:
        """Find potentially duplicate custom fields."""
        return self._run_command(self.cfm_command, ["analyze", "duplicates"])

    def validate_field_data(self) -> CliResult:
        """Validate custom field data integrity."""
        return self._run_command(self.cfm_command, ["validate"])

    # Database operations
    def backup_database(self, output_file: Optional[str] = None) -> CliResult:
        """Backup the local custom fields database."""
        args = ["db", "backup"]
        if output_file:
            args.extend(["--output", output_file])
        return self._run_command(self.cfm_command, args)

    def restore_database(self, backup_file: str) -> CliResult:
        """Restore the local custom fields database from backup."""
        return self._run_command(self.cfm_command, ["db", "restore", backup_file])

    def reset_database(self, confirm: bool = False) -> CliResult:
        """Reset the local custom fields database."""
        args = ["db", "reset"]
        if confirm:
            args.append("--confirm")
        return self._run_command(self.cfm_command, args)

    # Generic command execution
    def execute_cfm(self, command: str) -> CliResult:
        """
        Execute a raw cfm CLI command.

        Args:
            command: Full command string (without 'cfm' prefix)

        Returns:
            CliResult with command output
        """
        args = command.split()
        return self._run_command(self.cfm_command, args)

    def execute_clio_cfm(self, command: str) -> CliResult:
        """
        Execute a raw clio-cfm CLI command.

        Args:
            command: Full command string (without 'clio-cfm' prefix)

        Returns:
            CliResult with command output
        """
        args = command.split()
        return self._run_command(self.clio_cfm_command, args)

    # Help commands
    def help_cfm(self, subcommand: Optional[str] = None) -> CliResult:
        """Get help for cfm CLI commands."""
        args = ["--help"]
        if subcommand:
            args = [subcommand, "--help"]
        return self._run_command(self.cfm_command, args)

    def help_clio_cfm(self, subcommand: Optional[str] = None) -> CliResult:
        """Get help for clio-cfm CLI commands."""
        args = ["--help"]
        if subcommand:
            args = [subcommand, "--help"]
        return self._run_command(self.clio_cfm_command, args)
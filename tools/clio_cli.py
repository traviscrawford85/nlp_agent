"""
Wrapper for the clio_service CLI tool.

This module provides a Python interface to the clio_service CLI tool
located at ~/clio_service with the 'clio' command.
"""

import subprocess
import json
import os
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from loguru import logger
from pydantic import BaseModel


class CliResult(BaseModel):
    """Result from a CLI command execution."""
    success: bool
    output: str
    error: str = ""
    return_code: int = 0
    parsed_output: Optional[Dict[str, Any]] = None


class ClioServiceCLI:
    """Python wrapper for the clio_service CLI tool."""

    def __init__(self, clio_service_path: str = "/home/sysadmin01/clio_service"):
        self.clio_service_path = Path(clio_service_path)
        self.cli_command = "clio"

        if not self.clio_service_path.exists():
            raise FileNotFoundError(f"Clio service directory not found: {clio_service_path}")

    def _run_command(self, args: List[str], cwd: Optional[str] = None) -> CliResult:
        """
        Execute a clio CLI command.

        Args:
            args: Command arguments
            cwd: Working directory (defaults to clio_service path)

        Returns:
            CliResult with command output and status
        """
        if cwd is None:
            cwd = str(self.clio_service_path)

        cmd = [self.cli_command] + args
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

    # Contact management commands
    def get_contacts(self, limit: Optional[int] = None, search: Optional[str] = None) -> CliResult:
        """Get contacts from Clio."""
        args = ["contacts", "list"]
        if limit:
            args.extend(["--limit", str(limit)])
        if search:
            args.extend(["--search", search])
        return self._run_command(args)

    def create_contact(self, first_name: str, last_name: str, email: Optional[str] = None) -> CliResult:
        """Create a new contact in Clio."""
        args = ["contacts", "create", "--first-name", first_name, "--last-name", last_name]
        if email:
            args.extend(["--email", email])
        return self._run_command(args)

    def update_contact(self, contact_id: str, **kwargs) -> CliResult:
        """Update a contact in Clio."""
        args = ["contacts", "update", contact_id]
        for key, value in kwargs.items():
            if value is not None:
                args.extend([f"--{key.replace('_', '-')}", str(value)])
        return self._run_command(args)

    # Matter management commands
    def get_matters(self, limit: Optional[int] = None, client_id: Optional[str] = None) -> CliResult:
        """Get matters from Clio."""
        args = ["matters", "list"]
        if limit:
            args.extend(["--limit", str(limit)])
        if client_id:
            args.extend(["--client-id", client_id])
        return self._run_command(args)

    def create_matter(self, description: str, client_id: str, **kwargs) -> CliResult:
        """Create a new matter in Clio."""
        args = ["matters", "create", "--description", description, "--client-id", client_id]
        for key, value in kwargs.items():
            if value is not None:
                args.extend([f"--{key.replace('_', '-')}", str(value)])
        return self._run_command(args)

    # Activity/Time tracking commands
    def get_activities(self, matter_id: Optional[str] = None, date_from: Optional[str] = None) -> CliResult:
        """Get activities/time entries from Clio."""
        args = ["activities", "list"]
        if matter_id:
            args.extend(["--matter-id", matter_id])
        if date_from:
            args.extend(["--from", date_from])
        return self._run_command(args)

    def create_activity(self, matter_id: str, description: str, hours: float, **kwargs) -> CliResult:
        """Create a time entry/activity in Clio."""
        args = ["activities", "create", "--matter-id", matter_id, "--description", description, "--hours", str(hours)]
        for key, value in kwargs.items():
            if value is not None:
                args.extend([f"--{key.replace('_', '-')}", str(value)])
        return self._run_command(args)

    # Document management commands
    def get_documents(self, matter_id: Optional[str] = None, limit: Optional[int] = None) -> CliResult:
        """Get documents from Clio."""
        args = ["documents", "list"]
        if matter_id:
            args.extend(["--matter-id", matter_id])
        if limit:
            args.extend(["--limit", str(limit)])
        return self._run_command(args)

    def upload_document(self, file_path: str, matter_id: Optional[str] = None, **kwargs) -> CliResult:
        """Upload a document to Clio."""
        args = ["documents", "upload", file_path]
        if matter_id:
            args.extend(["--matter-id", matter_id])
        for key, value in kwargs.items():
            if value is not None:
                args.extend([f"--{key.replace('_', '-')}", str(value)])
        return self._run_command(args)

    # Authentication commands
    def get_auth_status(self) -> CliResult:
        """Check authentication status."""
        return self._run_command(["auth", "status"])

    def login(self, username: Optional[str] = None) -> CliResult:
        """Login to Clio (interactive)."""
        args = ["auth", "login"]
        if username:
            args.extend(["--username", username])
        return self._run_command(args)

    def logout(self) -> CliResult:
        """Logout from Clio."""
        return self._run_command(["auth", "logout"])

    # Generic command execution
    def execute(self, command: str) -> CliResult:
        """
        Execute a raw clio CLI command.

        Args:
            command: Full command string (without 'clio' prefix)

        Returns:
            CliResult with command output
        """
        args = command.split()
        return self._run_command(args)

    def help(self, subcommand: Optional[str] = None) -> CliResult:
        """Get help for clio CLI commands."""
        args = ["--help"]
        if subcommand:
            args = [subcommand, "--help"]
        return self._run_command(args)
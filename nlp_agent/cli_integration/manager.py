"""CLI integration manager for local services."""

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from nlp_agent.models.schemas import CLIService

logger = structlog.get_logger()


class CLIManager:
    """Manager for CLI integration with local services."""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.service_paths = {
            CLIService.CLIO_SERVICE: self.home_dir / "clio_service",
            CLIService.CUSTOM_FIELDS_MANAGER: self.home_dir / "custom-fields-manager",
        }
    
    async def execute_command(
        self,
        service: CLIService,
        command: str,
        args: List[str],
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a CLI command for the specified service."""
        service_path = self.service_paths.get(service)
        
        if not service_path or not service_path.exists():
            raise FileNotFoundError(f"Service '{service}' not found at {service_path}")
        
        # Build the full command
        cmd_parts = [str(service_path), command] + args
        
        logger.info(
            "Executing CLI command",
            service=service,
            command=command,
            args=args,
            service_path=str(service_path),
        )
        
        try:
            # Prepare input data as JSON if provided
            stdin_input = None
            if input_data:
                stdin_input = json.dumps(input_data)
            
            # Execute the command
            process = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdin=asyncio.subprocess.PIPE if stdin_input else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=service_path.parent,
            )
            
            stdout, stderr = await process.communicate(
                input=stdin_input.encode() if stdin_input else None
            )
            
            result = {
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "exit_code": process.returncode,
            }
            
            # Try to parse JSON output if it looks like JSON
            if result["stdout"].strip().startswith(("{", "[")):
                try:
                    result["parsed_output"] = json.loads(result["stdout"])
                except json.JSONDecodeError:
                    pass  # Not valid JSON, leave as string
            
            logger.info(
                "CLI command completed",
                service=service,
                command=command,
                exit_code=result["exit_code"],
                stdout_length=len(result["stdout"]),
                stderr_length=len(result["stderr"]),
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "CLI command execution failed",
                service=service,
                command=command,
                exc_info=e,
            )
            raise
    
    def is_service_available(self, service: CLIService) -> bool:
        """Check if a CLI service is available."""
        service_path = self.service_paths.get(service)
        return service_path is not None and service_path.exists()
    
    def list_available_services(self) -> List[CLIService]:
        """List all available CLI services."""
        available = []
        for service, path in self.service_paths.items():
            if path.exists():
                available.append(service)
        return available
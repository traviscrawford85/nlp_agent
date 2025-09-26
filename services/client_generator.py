"""
OpenAPI client generation service for Clio API.

This module handles generating type-safe Python client models from the Clio OpenAPI specification.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

import httpx
from loguru import logger


class ClioClientGenerator:
    """Generates type-safe Python client from Clio OpenAPI specification."""

    def __init__(self, openapi_spec_path: str = "/home/sysadmin01/clio_assistant/clio_client/openapi.json"):
        self.openapi_spec_path = Path(openapi_spec_path)
        self.generated_client_dir = Path("generated_client")

    def load_openapi_spec(self) -> Dict[str, Any]:
        """Load and validate the OpenAPI specification."""
        try:
            with open(self.openapi_spec_path) as f:
                spec = json.load(f)
            logger.info(f"Loaded OpenAPI spec from {self.openapi_spec_path}")
            return spec
        except FileNotFoundError:
            logger.error(f"OpenAPI spec not found at {self.openapi_spec_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in OpenAPI spec: {e}")
            raise

    def generate_client(self, output_dir: Optional[str] = None) -> Path:
        """
        Generate Python client using openapi-python-client.

        Args:
            output_dir: Directory to generate client in. Defaults to ./generated_client

        Returns:
            Path to generated client directory
        """
        if output_dir:
            self.generated_client_dir = Path(output_dir)

        # Ensure output directory exists
        self.generated_client_dir.mkdir(exist_ok=True)

        # Generate client using openapi-python-client
        cmd = [
            "openapi-python-client",
            "generate",
            "--path", str(self.openapi_spec_path),
            "--output-path", str(self.generated_client_dir),
            "--config", self._create_config_file()
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info("Successfully generated Clio API client")
            logger.debug(f"Generator output: {result.stdout}")
            return self.generated_client_dir
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate client: {e.stderr}")
            raise

    def _create_config_file(self) -> str:
        """Create configuration file for openapi-python-client."""
        config = {
            "class_overrides": {
                "Contact": "ClioContact",
                "Matter": "ClioMatter",
                "Activity": "ClioActivity",
                "Document": "ClioDocument"
            },
            "project_name_override": "clio_api_client",
            "package_name_override": "clio_api_client",
            "use_path_prefixes_for_title_model_names": False
        }

        config_path = self.generated_client_dir / "config.yaml"
        with open(config_path, 'w') as f:
            import yaml
            yaml.dump(config, f)

        return str(config_path)

    def get_available_endpoints(self) -> Dict[str, Any]:
        """Extract available endpoints from OpenAPI spec for tool descriptions."""
        spec = self.load_openapi_spec()
        endpoints = {}

        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "PATCH", "DELETE"]:
                    operation_id = details.get("operationId", f"{method}_{path}")
                    endpoints[operation_id] = {
                        "path": path,
                        "method": method.upper(),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "tags": details.get("tags", []),
                        "parameters": details.get("parameters", []),
                    }

        return endpoints
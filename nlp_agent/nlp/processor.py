"""Natural language processor for query mapping."""

import re
import json
from typing import Any, Dict, List, Optional

import structlog

from nlp_agent.models.schemas import APICall, CLICall, HTTPMethod, CLIService

logger = structlog.get_logger()


class NLPProcessor:
    """Natural language processor for mapping queries to API/CLI calls."""
    
    def __init__(self):
        self.api_patterns = self._load_api_patterns()
        self.cli_patterns = self._load_cli_patterns()
    
    def _load_api_patterns(self) -> Dict[str, Dict]:
        """Load API mapping patterns."""
        return {
            "health": {
                "patterns": [r"health", r"status", r"alive", r"running"],
                "endpoint": "/health",
                "method": HTTPMethod.GET,
            },
            "list_queries": {
                "patterns": [r"list queries", r"show queries", r"get queries", r"query history"],
                "endpoint": "/queries",
                "method": HTTPMethod.GET,
            },
        }
    
    def _load_cli_patterns(self) -> Dict[str, Dict]:
        """Load CLI mapping patterns."""
        return {
            "clio_list": {
                "patterns": [r"clio list", r"list clio", r"show clio items"],
                "service": CLIService.CLIO_SERVICE,
                "command": "list",
            },
            "clio_search": {
                "patterns": [r"clio search (.+)", r"search clio for (.+)"],
                "service": CLIService.CLIO_SERVICE,
                "command": "search",
            },
            "custom_fields_list": {
                "patterns": [r"list custom fields", r"show custom fields", r"custom fields list"],
                "service": CLIService.CUSTOM_FIELDS_MANAGER,
                "command": "list",
            },
            "custom_fields_create": {
                "patterns": [r"create custom field (?:named |called )?([a-zA-Z0-9_-]+)", r"add custom field (?:named |called )?([a-zA-Z0-9_-]+)"],
                "service": CLIService.CUSTOM_FIELDS_MANAGER,
                "command": "create",
            },
        }
    
    async def process_query(
        self,
        query: str,
        context: Dict[str, Any],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process a natural language query and map it to API/CLI calls."""
        logger.info("Processing NLP query", query=query, context=context)
        
        query_lower = query.lower().strip()
        
        # Try to match API patterns first
        api_calls = []
        api_match = self._match_api_patterns(query_lower)
        if api_match:
            api_calls.append(api_match)
        
        # Try to match CLI patterns
        cli_calls = []
        cli_match = self._match_cli_patterns(query_lower)
        if cli_match:
            cli_calls.append(cli_match)
        
        # If no specific patterns matched, try to extract intent
        if not api_calls and not cli_calls:
            intent_result = self._extract_intent(query_lower, context)
            if intent_result.get("api_calls"):
                api_calls.extend(intent_result["api_calls"])
            if intent_result.get("cli_calls"):
                cli_calls.extend(intent_result["cli_calls"])
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(query_lower, api_calls, cli_calls)
        
        result = {
            "result": {
                "query": query,
                "interpretation": self._generate_interpretation(api_calls, cli_calls),
                "suggested_actions": self._generate_suggestions(api_calls, cli_calls),
            },
            "api_calls": api_calls,
            "cli_calls": cli_calls,
            "confidence_score": confidence_score,
            "tokens_used": len(query.split()),  # Simple token count
        }
        
        logger.info(
            "NLP processing completed",
            api_calls_count=len(api_calls),
            cli_calls_count=len(cli_calls),
            confidence_score=confidence_score,
        )
        
        return result
    
    def _match_api_patterns(self, query: str) -> Optional[APICall]:
        """Match query against API patterns."""
        for pattern_name, config in self.api_patterns.items():
            for pattern in config["patterns"]:
                if re.search(pattern, query):
                    return APICall(
                        endpoint=config["endpoint"],
                        method=config["method"],
                        payload=self._extract_api_payload(query, pattern_name),
                    )
        return None
    
    def _match_cli_patterns(self, query: str) -> Optional[CLICall]:
        """Match query against CLI patterns."""
        for pattern_name, config in self.cli_patterns.items():
            for pattern in config["patterns"]:
                match = re.search(pattern, query)
                if match:
                    args = []
                    if match.groups():
                        args = [group.strip() for group in match.groups()]
                    
                    return CLICall(
                        command=config["service"],
                        args=[config["command"]] + args,
                        exit_code=0,  # Will be filled when executed
                    )
        return None
    
    def _extract_intent(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract intent from query when no specific patterns match."""
        result = {"api_calls": [], "cli_calls": []}
        
        # Simple keyword-based intent extraction
        if any(word in query for word in ["show", "list", "display", "get"]):
            if "query" in query or "queries" in query:
                result["api_calls"].append(APICall(
                    endpoint="/queries",
                    method=HTTPMethod.GET,
                ))
            elif "clio" in query:
                result["cli_calls"].append(CLICall(
                    command=CLIService.CLIO_SERVICE,
                    args=["list"],
                    exit_code=0,
                ))
            elif "custom field" in query:
                result["cli_calls"].append(CLICall(
                    command=CLIService.CUSTOM_FIELDS_MANAGER,
                    args=["list"],
                    exit_code=0,
                ))
        
        elif any(word in query for word in ["create", "add", "new"]):
            if "custom field" in query:
                # Extract field name if possible - look for patterns after "named" or "called"
                field_match = re.search(r"(?:named |called )([a-zA-Z0-9_-]+)", query)
                args = ["create"]
                if field_match:
                    field_name = field_match.group(1).strip()
                    args.append(field_name)
                
                result["cli_calls"].append(CLICall(
                    command=CLIService.CUSTOM_FIELDS_MANAGER,
                    args=args,
                    exit_code=0,
                ))
        
        return result
    
    def _extract_api_payload(self, query: str, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Extract payload for API calls based on query."""
        payload = {}
        
        if pattern_name == "list_queries":
            # Extract pagination parameters
            limit_match = re.search(r"(?:show|limit|top) (\d+)", query)
            if limit_match:
                payload["limit"] = int(limit_match.group(1))
            
            # Extract status filter
            status_match = re.search(r"status (\w+)", query)
            if status_match:
                payload["status"] = status_match.group(1)
        
        return payload if payload else None
    
    def _calculate_confidence(
        self,
        query: str,
        api_calls: List[APICall],
        cli_calls: List[CLICall],
    ) -> float:
        """Calculate confidence score for the interpretation."""
        if not api_calls and not cli_calls:
            return 0.1  # Very low confidence for no matches
        
        # Base confidence for having matches
        confidence = 0.5
        
        # Increase confidence for exact pattern matches
        total_patterns = len(self.api_patterns) + len(self.cli_patterns)
        for pattern_name, config in {**self.api_patterns, **self.cli_patterns}.items():
            for pattern in config["patterns"]:
                if re.search(pattern, query):
                    confidence += 0.3 / total_patterns
        
        # Increase confidence for multiple matches
        total_calls = len(api_calls) + len(cli_calls)
        if total_calls > 1:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _generate_interpretation(
        self,
        api_calls: List[APICall],
        cli_calls: List[CLICall],
    ) -> str:
        """Generate human-readable interpretation of the query."""
        interpretations = []
        
        for call in api_calls:
            if call.endpoint == "/health":
                interpretations.append("Check system health status")
            elif call.endpoint == "/queries":
                interpretations.append("List processed queries")
        
        for call in cli_calls:
            if call.command == CLIService.CLIO_SERVICE:
                if "list" in call.args:
                    interpretations.append("List items from Clio service")
                elif "search" in call.args:
                    interpretations.append("Search Clio service")
            elif call.command == CLIService.CUSTOM_FIELDS_MANAGER:
                if "list" in call.args:
                    interpretations.append("List custom fields")
                elif "create" in call.args:
                    interpretations.append("Create a new custom field")
        
        if not interpretations:
            return "No specific action identified"
        
        return "; ".join(interpretations)
    
    def _generate_suggestions(
        self,
        api_calls: List[APICall],
        cli_calls: List[CLICall],
    ) -> List[str]:
        """Generate suggestions for the user."""
        suggestions = []
        
        if not api_calls and not cli_calls:
            suggestions.extend([
                "Try asking to 'list queries' or 'show health status'",
                "Use 'clio list' to see Clio items",
                "Ask to 'list custom fields' to see available fields",
            ])
        else:
            suggestions.extend([
                "You can add filters like 'status completed' for query lists",
                "Use specific field names when creating custom fields",
                "Check the health endpoint to verify system status",
            ])
        
        return suggestions
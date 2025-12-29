"""
Tool Call Parser Module

Provides a clean, modular interface for parsing and formatting tool calls
in the standard XML format:

    <tool_call>tool_name<arg_key>key</arg_key><arg_value>value</arg_value></tool_call>

This parser extracts tool calls from AI responses, cleans the content for UI display,
and provides utilities for formatting tool calls.
"""

import re
from typing import Tuple, List, Dict, Any, Optional


class ToolCallParser:
    """
    Parser for extracting and formatting tool calls in XML format.
    
    The standard format is:
        <tool_call>tool_name<arg_key>param1</arg_key><arg_value>value1</arg_value>...</tool_call>
    """
    
    # Regex patterns for parsing
    TOOL_CALL_PATTERN = re.compile(
        r'<\s*tool_call\s*>(.*?)<\s*/\s*tool_call\s*>',
        re.DOTALL
    )
    
    ARG_PATTERN = re.compile(
        r'<\s*arg_key\s*>(.*?)<\s*/\s*arg_key\s*>\s*<\s*arg_value\s*>(.*?)<\s*/\s*arg_value\s*>',
        re.DOTALL
    )
    
    # Tools that require automatic project_id injection
    PROJECT_TOOLS = {"web_builder", "file_reader", "file_editor", "file_list"}
    
    # Parameter name aliases - map common AI variations to actual tool parameter names
    PARAM_ALIASES = {
        "searchText": "search",
        "replaceText": "replace",
        "search_text": "search",
        "replace_text": "replace",
        "content": "code",
        "file_content": "code",
        "file_name": "filename",
        "fileName": "filename",
    }
    
    @classmethod
    def parse_tool_calls(
        cls,
        content: str,
        project_id: Optional[str] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse tool calls from content and return cleaned content + parsed calls.
        
        Args:
            content: The raw AI response content that may contain tool call XML
            project_id: Optional project ID to inject into file-related tools
            
        Returns:
            Tuple of (clean_content, tool_calls) where:
                - clean_content: Content with tool call XML removed
                - tool_calls: List of parsed tool call dicts in standard format
        """
        tool_calls = []
        clean_content = content
        
        matches = list(cls.TOOL_CALL_PATTERN.finditer(content))
        
        for idx, match in enumerate(matches):
            tool_xml = match.group(0)
            tool_body = match.group(1)
            
            # Remove from UI text
            clean_content = clean_content.replace(tool_xml, "").strip()
            
            # Extract tool name (text before first <arg_key>)
            tool_name = cls._extract_tool_name(tool_body)
            
            if tool_name:
                # Parse arguments
                args = cls._parse_arguments(tool_body)
                
                # Auto-inject project_id for file tools
                if project_id and tool_name in cls.PROJECT_TOOLS:
                    args['project_id'] = project_id
                
                tool_calls.append({
                    "id": f"call_{tool_name}_{idx}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": args
                    }
                })
        
        return clean_content, tool_calls
    
    @classmethod
    def _extract_tool_name(cls, tool_body: str) -> Optional[str]:
        """Extract the tool name from the body of a tool call."""
        # Pattern 1: Name is text before first <arg_key>
        name_match = re.search(r'^(.*?)<\s*arg_key', tool_body, re.DOTALL)
        if name_match:
            name = name_match.group(1).strip()
            if name:
                return name
        
        # Fallback: Take the first word
        first_word = tool_body.split('<')[0].strip()
        return first_word if first_word else None
    
    @classmethod
    def _parse_arguments(cls, tool_body: str) -> Dict[str, str]:
        """Parse all argument key-value pairs from a tool call body and normalize names."""
        args = {}
        for arg_match in cls.ARG_PATTERN.finditer(tool_body):
            key = arg_match.group(1).strip()
            value = arg_match.group(2).strip()
            # Normalize parameter names using aliases
            normalized_key = cls.PARAM_ALIASES.get(key, key)
            args[normalized_key] = value
        return args
    
    @staticmethod
    def format_tool_call(tool_name: str, **kwargs) -> str:
        """
        Format a tool call into the standard XML format.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Arguments to pass to the tool
            
        Returns:
            Formatted XML string for the tool call
        """
        parts = [f"<tool_call>{tool_name}"]
        for key, value in kwargs.items():
            parts.append(f"<arg_key>{key}</arg_key><arg_value>{value}</arg_value>")
        parts.append("</tool_call>")
        return "".join(parts)
    
    @classmethod
    def has_tool_calls(cls, content: str) -> bool:
        """Check if content contains any tool calls."""
        return bool(cls.TOOL_CALL_PATTERN.search(content))

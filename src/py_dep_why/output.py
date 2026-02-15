"""
Output handling utilities for py-dep-why.

Centralizes printing to ensure:
- JSON mode keeps stdout pure (only JSON)
- Warnings go to stderr when in JSON mode
- Color formatting can be disabled with --no-color
"""

import sys
from typing import Optional


class OutputHelper:
    """Helper for managing output with JSON purity and color support."""
    
    def __init__(self, json_mode: bool = False, no_color: bool = False):
        """
        Initialize output helper.
        
        Args:
            json_mode: If True, stdout is reserved for JSON only
            no_color: If True, disable ANSI color codes
        """
        self.json_mode = json_mode
        self.no_color = no_color
    
    def print(self, message: str, file=None):
        """
        Print a message to the appropriate stream.
        
        In JSON mode, regular output goes to stderr.
        Otherwise, goes to stdout (or specified file).
        
        Args:
            message: Message to print
            file: Optional file stream (defaults based on json_mode)
        """
        if file is None:
            file = sys.stderr if self.json_mode else sys.stdout
        print(message, file=file)
    
    def warning(self, message: str):
        """
        Print a warning message.
        
        Always goes to stderr, with optional color.
        
        Args:
            message: Warning message
        """
        if self.no_color:
            print(f"Warning: {message}", file=sys.stderr)
        else:
            # Yellow color for warnings
            print(f"\033[33mWarning: {message}\033[0m", file=sys.stderr)
    
    def error(self, message: str):
        """
        Print an error message.
        
        Always goes to stderr, with optional color.
        
        Args:
            message: Error message
        """
        if self.no_color:
            print(f"Error: {message}", file=sys.stderr)
        else:
            # Red color for errors
            print(f"\033[31mError: {message}\033[0m", file=sys.stderr)
    
    def bold(self, text: str) -> str:
        """
        Make text bold (if color is enabled).
        
        Args:
            text: Text to make bold
            
        Returns:
            Text with ANSI bold codes (or plain text if no_color)
        """
        if self.no_color:
            return text
        return f"\033[1m{text}\033[0m"
    
    def json_output(self, data: str):
        """
        Print JSON data to stdout.
        
        This should only be called in JSON mode.
        
        Args:
            data: JSON string to output
        """
        print(data, file=sys.stdout)

import pytest
from io import StringIO
from unittest.mock import patch

from py_dep_why.output import OutputHelper


def test_output_helper_normal_mode_prints_to_stdout():
    """Test that in normal mode, print() goes to stdout."""
    helper = OutputHelper(json_mode=False, no_color=True)
    
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        helper.print("test message")
        assert "test message" in mock_stdout.getvalue()


def test_output_helper_json_mode_prints_to_stderr():
    """Test that in JSON mode, print() goes to stderr."""
    helper = OutputHelper(json_mode=True, no_color=True)
    
    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        helper.print("test message")
        assert "test message" in mock_stderr.getvalue()


def test_output_helper_warning_goes_to_stderr():
    """Test that warnings always go to stderr."""
    helper = OutputHelper(json_mode=False, no_color=True)
    
    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        helper.warning("test warning")
        assert "Warning: test warning" in mock_stderr.getvalue()


def test_output_helper_warning_in_json_mode():
    """Test that warnings in JSON mode don't pollute stdout."""
    helper = OutputHelper(json_mode=True, no_color=True)
    
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            helper.warning("test warning")
            # Warning should be in stderr
            assert "Warning: test warning" in mock_stderr.getvalue()
            # stdout should be empty
            assert mock_stdout.getvalue() == ""


def test_output_helper_error_goes_to_stderr():
    """Test that errors always go to stderr."""
    helper = OutputHelper(json_mode=False, no_color=True)
    
    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        helper.error("test error")
        assert "Error: test error" in mock_stderr.getvalue()


def test_output_helper_json_output_goes_to_stdout():
    """Test that json_output() always goes to stdout."""
    helper = OutputHelper(json_mode=True, no_color=True)
    
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        helper.json_output('{"test": "data"}')
        assert '{"test": "data"}' in mock_stdout.getvalue()


def test_output_helper_color_disabled():
    """Test that no_color disables ANSI codes."""
    helper = OutputHelper(json_mode=False, no_color=True)
    
    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        helper.warning("test")
        # Should not contain ANSI codes
        assert "\033[" not in mock_stderr.getvalue()


def test_output_helper_color_enabled():
    """Test that color is enabled by default."""
    helper = OutputHelper(json_mode=False, no_color=False)
    
    with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
        helper.warning("test")
        # Should contain ANSI codes
        assert "\033[33m" in mock_stderr.getvalue()  # Yellow
        assert "\033[0m" in mock_stderr.getvalue()   # Reset


def test_output_helper_bold_with_color():
    """Test that bold() adds ANSI codes when color is enabled."""
    helper = OutputHelper(json_mode=False, no_color=False)
    
    result = helper.bold("test")
    assert "\033[1m" in result  # Bold
    assert "\033[0m" in result  # Reset


def test_output_helper_bold_without_color():
    """Test that bold() returns plain text when color is disabled."""
    helper = OutputHelper(json_mode=False, no_color=True)
    
    result = helper.bold("test")
    assert result == "test"
    assert "\033[" not in result


def test_output_helper_json_purity():
    """Test that in JSON mode, only json_output() writes to stdout."""
    helper = OutputHelper(json_mode=True, no_color=True)
    
    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            # These should all go to stderr
            helper.print("regular message")
            helper.warning("warning message")
            helper.error("error message")
            
            # Only this should go to stdout
            helper.json_output('{"key": "value"}')
            
            # Verify stdout only has JSON
            stdout_content = mock_stdout.getvalue()
            assert '{"key": "value"}' in stdout_content
            assert "regular message" not in stdout_content
            assert "warning message" not in stdout_content
            assert "error message" not in stdout_content
            
            # Verify stderr has the other messages
            stderr_content = mock_stderr.getvalue()
            assert "regular message" in stderr_content
            assert "warning message" in stderr_content
            assert "error message" in stderr_content

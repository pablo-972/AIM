from typing import Any

class AIMError(Exception):
    """Base exception for AIM."""
    pass


class CLIValidationError(AIMError):
    """Invalid CLI arguments."""
    pass


class ToolError(AIMError):
    """Tool error."""
    pass


class AgentError(AIMError):
    """Agent error."""
    pass


class ConfigurationError(AIMError):
    """Configuration error."""
    pass


class ProviderError(AIMError):
    """LLM provider error."""
    pass


class FileReadError(Exception):
    """File error."""
    pass


class DocumentationNotFoundError(Exception):
    """Documentation page was not found."""
    pass


class VirtualBoxError(Exception):
    """VirtualBox error."""
    
    def __init__(self, detail: Any, status_code: int = 500) -> None:
        super().__init__(str(detail))

        self.detail = detail
        self.status_code = status_code


class HTTPError(Exception):
    """HTTP error."""
    pass

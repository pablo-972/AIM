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
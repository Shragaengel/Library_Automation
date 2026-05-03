"""
Custom exception hierarchy for the OpenLibrary automation suite.

All project-specific exceptions inherit from AutomationError so callers
can catch the entire family with a single except clause if needed.
"""


class AutomationError(Exception):
    """Base class for all automation-suite exceptions."""


class ConfigError(AutomationError):
    """Raised when the configuration file is missing, malformed, or fails validation."""


class LocatorNotFoundError(AutomationError):
    """Raised when a smart locator exhausts all fallback strategies without a match."""


class PerformanceThresholdExceeded(AutomationError):
    """
    Soft warning: a page-load metric exceeded its configured threshold.

    This exception is defined for completeness and structured reporting;
    it is NOT raised by the performance decorator — only logged as a warning.
    """

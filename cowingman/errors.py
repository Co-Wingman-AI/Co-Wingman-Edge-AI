"""Content-free errors safe to show during a presentation."""


class ConfigurationError(ValueError):
    pass


class PrivacyBoundaryError(ValueError):
    pass


class CloudRequestError(RuntimeError):
    pass


class SpeechError(RuntimeError):
    pass

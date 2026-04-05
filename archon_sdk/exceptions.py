class ArchonError(Exception):
    """Base exception for all Archon SDK errors."""
    pass

class StepUpAuthRequired(ArchonError):
    """Raised when an action strictly requires Step-Up authentication but polling wasn't used."""
    def __init__(self, action_id: str, auth_url: str):
        super().__init__(f"Action {action_id} requires Step-Up Authorization.")
        self.action_id = action_id
        self.auth_url = auth_url

class QuorumRequired(ArchonError):
    """Raised when an action strictly requires a multi-party Quorum."""
    def __init__(self, action_id: str, required: int, auth_urls: dict[str, str]):
        super().__init__(f"Action {action_id} requires Quorum ({required} approvals).")
        self.action_id = action_id
        self.required = required
        self.auth_urls = auth_urls

class ArchonTimeoutError(ArchonError):
    """Raised when a time-boxed poll for Step-Up or Quorum approval times out."""
    pass

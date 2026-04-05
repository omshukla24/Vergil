from pydantic import BaseModel, Field
from typing import List, Optional, Set, Dict
from enum import Enum

class ActionState(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    EXECUTABLE = "EXECUTABLE"
    REJECTED = "REJECTED"

class ActionRequest(BaseModel):
    action: str = Field(..., description="The action to be executed")
    confidence: float = Field(..., description="Confidence score from the AI agent")
    threshold: float = Field(..., description="The minimum confidence required for auto-approval")
    user_id: str = Field(..., description="The ID of the user requesting/owning the agent")

class ActionResponse(BaseModel):
    action_id: str
    status: ActionState
    auth_url: Optional[str] = None
    message: str

class QuorumRequest(BaseModel):
    action: str = Field(..., description="High stakes action requiring multiple approvals")
    trustees: List[str] = Field(..., description="List of user IDs required for the quorum")
    required: int = Field(..., description="Number of approvals required")

class QuorumStateModel(BaseModel):
    action_id: str
    action: str
    status: ActionState
    required_approvals: int
    current_approvals: int
    approved_by: Set[str] = Field(default_factory=set)
    auth_urls: Optional[Dict[str, str]] = None

import uuid
import logging
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from archon_engine.models import (
    ActionRequest, ActionResponse, ActionState, QuorumRequest, QuorumStateModel
)
from archon_engine.redis_store import store
from archon_engine.auth0_utils import generate_step_up_url, generate_quorum_urls, decode_state

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("archon_engine")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB/Redis connections
    logger.info("Connecting to Redis...")
    await store.connect()
    yield
    # Shutdown: Clean up connections
    logger.info("Disconnecting from Redis...")
    await store.disconnect()

app = FastAPI(
    title="Archon State Engine",
    description="Control plane for Confidence-Gated AI Authorization via Auth0.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — allow the dashboard to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the dashboard static files
dashboard_dir = Path(__file__).resolve().parent.parent / "dashboard"
if dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")

@app.get("/", include_in_schema=False)
async def root_redirect():
    """Redirect root to the Command Center dashboard."""
    return RedirectResponse(url="/dashboard/")

@app.post("/api/v1/actions/execute", response_model=ActionResponse)
async def execute_action(req: ActionRequest, request: Request):
    """
    Called by SDK to execute an action. If confidence < threshold,
    triggers Step-Up authentication.
    """
    action_id = str(uuid.uuid4())
    
    if req.confidence >= req.threshold:
        # Auto-approve
        await store.set_action_state(action_id, ActionState.EXECUTABLE)
        logger.info(f"Action {action_id} auto-approved (confidence {req.confidence} >= threshold {req.threshold})")
        return ActionResponse(action_id=action_id, status=ActionState.EXECUTABLE, message="Auto-approved")
    
    # Needs Step-up
    await store.set_action_state(action_id, ActionState.PENDING)
    
    # Construct base URL for redirect, handles local or deployed URL schema implicitly
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/auth0/callback"
    
    auth_url = generate_step_up_url(action_id, req.user_id, redirect_uri)
    logger.info(f"Action {action_id} requested Step-Up Auth for user: {req.user_id}.")
    
    return ActionResponse(
        action_id=action_id, 
        status=ActionState.PENDING, 
        auth_url=auth_url,
        message="Step-up authentication required"
    )

@app.post("/api/v1/actions/quorum", response_model=QuorumStateModel)
async def require_quorum(req: QuorumRequest, request: Request):
    """
    Initiates a multi-party authorization quorum.
    """
    action_id = str(uuid.uuid4())
    
    base_url = str(request.base_url).rstrip("/")
    redirect_uri = f"{base_url}/api/v1/auth0/callback"
    
    auth_urls = generate_quorum_urls(action_id, req.trustees, redirect_uri)
    
    quorum = QuorumStateModel(
        action_id=action_id,
        action=req.action,
        status=ActionState.PENDING,
        required_approvals=req.required,
        current_approvals=0,
        approved_by=set(),
        auth_urls=auth_urls
    )
    
    await store.create_quorum(quorum)
    logger.info(f"Quorum {action_id} initiated, requiring {req.required} approvals out of {len(req.trustees)} trustees.")
    
    return quorum

@app.get("/api/v1/actions/{action_id}/status")
async def get_action_status(action_id: str):
    """
    SDK polls this to check status of standard action or quorum.
    """
    # Check quorum first in our system
    quorum = await store.get_quorum(action_id)
    if quorum:
        return {
            "action_id": action_id, 
            "status": quorum.status.value, 
            "type": "quorum", 
            "required_approvals": quorum.required_approvals,
            "current_approvals": quorum.current_approvals
        }
    
    # Check standard action
    state = await store.get_action_state(action_id)
    if state:
        return {"action_id": action_id, "status": state.value, "type": "standard"}
        
    raise HTTPException(status_code=404, detail="Action not found or expired")

@app.get("/api/v1/auth0/callback", response_class=HTMLResponse)
async def auth0_callback(code: str = None, state: str = None, error: str = None, error_description: str = None):
    """
    Auth0 redirects here after successful (or failed) step-up authentication.
    """
    if error:
        logger.error(f"Auth0 Error: {error} - {error_description}")
        return f"<h1>Authentication Failed</h1><p>{error_description}</p>"
        
    if not state:
        raise HTTPException(status_code=400, detail="Missing state parameter")
        
    state_data = decode_state(state)
    action_id = state_data.get("action_id")
    user_id = state_data.get("user_id")
    
    if not action_id or not user_id:
        raise HTTPException(status_code=400, detail="Invalid state parameter payload")
        
    # Process Quorum Response 
    quorum = await store.get_quorum(action_id)
    if quorum:
        updated_quorum = await store.add_quorum_approval(action_id, user_id)
        
        if updated_quorum:
            if updated_quorum.status == ActionState.EXECUTABLE:
                logger.info(f"Quorum {action_id} met its required threshold and is EXECUTABLE.")
                return f"<h1>Quorum Complete</h1><p>Thank you {user_id}. Agent is authorized.</p>"
            return f"<h1>Approval Registered</h1><p>Thank you {user_id}. {updated_quorum.current_approvals} out of {updated_quorum.required_approvals} received.</p>"
            
    # Process Standard Response
    state_val = await store.get_action_state(action_id)
    if state_val:
        # NOTE: A real implementation would now exchange the custom `code` using Auth0 /oauth/token endpoint
        # to acquire a Step-Up enhanced Access Token. For architectural sim, we assume verification and upgrade state.
        await store.set_action_state(action_id, ActionState.APPROVED)
        logger.info(f"Action {action_id} approved via Step-Up Auth by {user_id}")
        return f"<h1>Action Approved</h1><p>Agent Step-Up Verification successful. Agent may proceed.</p>"
        
    return f"<h1>Error</h1><p>Action {action_id} not found, already executed, or expired.</p>"

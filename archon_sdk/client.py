import httpx
import logging
import asyncio
from typing import List, Dict, Any, Optional

from archon_sdk.exceptions import ArchonTimeoutError

logger = logging.getLogger("archon_sdk")

class ArchonClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        # We set an explicit timeout for overall connection handling to the engine
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def execute(self, action: str, confidence: float, threshold: float, user_id: str) -> bool:
        """
        Request authorization to execute a potentially high-stakes action.
        If the agent's confidence meets the threshold, it is instantly approved.
        Otherwise, triggers an Auth0 Step-Up Auth redirect and polls until approved.
        """
        payload = {
            "action": action,
            "confidence": confidence,
            "threshold": threshold,
            "user_id": user_id
        }
        res = await self.client.post("/api/v1/actions/execute", json=payload)
        res.raise_for_status()
        data = res.json()
        
        action_id = data["action_id"]
        status = data["status"]
        
        if status == "EXECUTABLE":
            return True
            
        if status == "PENDING" and data.get("auth_url"):
            logger.info(f"====== STEP-UP AUTH REQUIRED ======")
            logger.info(f"Targeting User: {user_id}")
            logger.info(f"Action: {action} (Confidence: {confidence})")
            logger.info(f"URL: {data['auth_url']}")
            logger.info(f"===================================")
            
            try:
                # Delegate to an asynchronous exponential polling method
                await self._poll_for_approval(action_id)
                return True
            except ArchonTimeoutError:
                logger.error(f"Timed out waiting for Step-Up Auth for {action_id}.")
                return False
                
        return False

    async def require_quorum(self, action: str, trustees: List[str], required: int) -> bool:
        """
        Initiates a quorum, emits step-up approval URLs for each trustee, and polls
        the engine until the N of M quorum is successfully met.
        """
        payload = {
            "action": action,
            "trustees": trustees,
            "required": required
        }
        res = await self.client.post("/api/v1/actions/quorum", json=payload)
        res.raise_for_status()
        data = res.json()
        
        action_id = data["action_id"]
        
        logger.info(f"====== QUORUM INITIATED ======")
        logger.info(f"Action: {action}")
        logger.info(f"Required Approvals: {required} from {trustees}")
        for trustee, url in data["auth_urls"].items():
            logger.info(f"-> Trustee [{trustee}] Auth URL: {url}")
        logger.info(f"==============================")
            
        try:
            await self._poll_for_approval(action_id)
            return True
        except ArchonTimeoutError:
            logger.error(f"Timed out waiting for Quorum for {action_id}.")
            return False

    async def _poll_for_approval(self, action_id: str, max_attempts: int = 30) -> bool:
        """
        Internal polling with a small exponential backoff until state is EXECUTABLE/APPROVED.
        """
        delay = 2.0
        for i in range(max_attempts):
            try:
                res = await self.client.get(f"/api/v1/actions/{action_id}/status")
                if res.status_code == 200:
                    data = res.json()
                    status = data["status"]
                    
                    if data.get("type") == "quorum":
                        # Reduced verbosity to avoid spam
                        pass 
                    
                    if status in ["APPROVED", "EXECUTABLE"]:
                        return True
                        
            except httpx.HTTPError as e:
                logger.warning(f"Engine connection issue during poll: {e}")
                
            await asyncio.sleep(delay)
            # Cap delay
            if delay < 5.0:
                delay *= 1.25
                
        raise ArchonTimeoutError(f"Action {action_id} approval timed out.")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

import pytest
from httpx import AsyncClient, ASGITransport
import urllib.parse
from vergil_engine.main import app
from vergil_engine.models import ActionState, QuorumStateModel

class MockRedisStore:
    def __init__(self):
        self.data = {}
    
    async def connect(self):
        pass
    
    async def disconnect(self):
        pass
        
    async def set_action_state(self, action_id: str, state: ActionState) -> None:
        self.data[f"action:{action_id}"] = state.value
        
    async def get_action_state(self, action_id: str):
        val = self.data.get(f"action:{action_id}")
        if val:
            return ActionState(val)
        return None
        
    async def create_quorum(self, quorum: QuorumStateModel) -> None:
        self.data[f"quorum:{quorum.action_id}"] = quorum
        
    async def get_quorum(self, action_id: str):
        return self.data.get(f"quorum:{action_id}")
        
    async def add_quorum_approval(self, action_id: str, user_id: str):
        quorum = self.data.get(f"quorum:{action_id}")
        if quorum:
            quorum.approved_by.add(user_id)
            quorum.current_approvals = len(quorum.approved_by)
            if quorum.current_approvals >= quorum.required_approvals:
                quorum.status = ActionState.EXECUTABLE
            self.data[f"quorum:{action_id}"] = quorum
            return quorum
        return None

@pytest.fixture
def mock_store(monkeypatch):
    mock = MockRedisStore()
    monkeypatch.setattr("vergil_engine.main.store", mock)
    monkeypatch.setattr("vergil_engine.redis_store.store", mock)
    return mock

@pytest.fixture
async def async_client(mock_store):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_execute_auto_approve(async_client, mock_store):
    response = await async_client.post("/api/v1/actions/execute", json={
        "action": "test_action",
        "confidence": 0.95,
        "threshold": 0.90,
        "user_id": "test_user_1"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EXECUTABLE"
    assert data["message"] == "Auto-approved"
    
    # Store should have executable state
    state = mock_store.data.get(f"action:{data['action_id']}")
    assert state == "EXECUTABLE"

@pytest.mark.asyncio
async def test_execute_requires_step_up(async_client, mock_store):
    response = await async_client.post("/api/v1/actions/execute", json={
        "action": "test_action",
        "confidence": 0.50,
        "threshold": 0.90,
        "user_id": "test_user_2"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING"
    assert "authorize?response_type=code" in data["auth_url"]
    
    action_id = data["action_id"]
    state = mock_store.data.get(f"action:{action_id}")
    assert state == "PENDING"

@pytest.mark.asyncio
async def test_quorum_flow(async_client, mock_store):
    response = await async_client.post("/api/v1/actions/quorum", json={
        "action": "critical_action",
        "trustees": ["user1@company.com", "user2@company.com"],
        "required": 2
    })
    
    assert response.status_code == 200
    data = response.json()
    action_id = data["action_id"]
    assert data["status"] == "PENDING"
    assert "user1@company.com" in data["auth_urls"]
    
    # Simulate Callback for User 1
    state1 = f"action_id={action_id}&user_id=user1@company.com"
    qs1 = urllib.parse.urlencode({"state": state1, "code": "fake_code_1"})
    res1 = await async_client.get(f"/api/v1/auth0/callback?{qs1}")
    assert res1.status_code == 200
    assert b"Approval Registered" in res1.content
    
    # Verify incomplete quorum
    q_state = await async_client.get(f"/api/v1/actions/{action_id}/status")
    assert q_state.json()["status"] == "PENDING"
    assert q_state.json()["current_approvals"] == 1
    
    # Simulate Callback for User 2
    state2 = f"action_id={action_id}&user_id=user2@company.com"
    qs2 = urllib.parse.urlencode({"state": state2, "code": "fake_code_2"})
    res2 = await async_client.get(f"/api/v1/auth0/callback?{qs2}")
    assert res2.status_code == 200
    assert b"Quorum Complete" in res2.content
    
    # Verify complete quorum
    q_state2 = await async_client.get(f"/api/v1/actions/{action_id}/status")
    assert q_state2.json()["status"] == "EXECUTABLE"

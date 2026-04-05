import redis.asyncio as redis
import json
from typing import Optional
from archon_engine.config import settings
from archon_engine.models import ActionState, QuorumStateModel

class RedisStore:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)

    async def disconnect(self):
        if self.redis:
            await self.redis.close()

    async def set_action_state(self, action_id: str, state: ActionState) -> None:
        await self.redis.set(f"action:{action_id}", state.value, ex=3600)  # expiry 1 hr

    async def get_action_state(self, action_id: str) -> Optional[ActionState]:
        val = await self.redis.get(f"action:{action_id}")
        if val:
            return ActionState(val)
        return None

    async def create_quorum(self, quorum: QuorumStateModel) -> None:
        key = f"quorum:{quorum.action_id}"
        # Convert set to list for json serialization
        data = quorum.model_dump()
        data['approved_by'] = list(data['approved_by'])
        await self.redis.set(key, json.dumps(data), ex=3600)

    async def get_quorum(self, action_id: str) -> Optional[QuorumStateModel]:
        key = f"quorum:{action_id}"
        data_str = await self.redis.get(key)
        if not data_str:
            return None
        data = json.loads(data_str)
        # Convert list back to set
        data['approved_by'] = set(data['approved_by'])
        return QuorumStateModel(**data)

    async def add_quorum_approval(self, action_id: str, user_id: str) -> Optional[QuorumStateModel]:
        """
        Uses Redis WATCH for optimistic concurrency control to safely update
        the quorum approvals when multiple requests might arrive concurrently.
        """
        key = f"quorum:{action_id}"
        async with self.redis.pipeline(transaction=True) as pipe:
            while True:
                try:
                    await pipe.watch(key)
                    data_str = await pipe.get(key)
                    if not data_str:
                        return None
                    
                    data = json.loads(data_str)
                    approved_by = set(data['approved_by'])
                    
                    if user_id not in approved_by:
                        approved_by.add(user_id)
                        data['approved_by'] = list(approved_by)
                        data['current_approvals'] = len(approved_by)
                        
                        if data['current_approvals'] >= data['required_approvals']:
                            data['status'] = ActionState.EXECUTABLE.value
                    
                    pipe.multi()
                    pipe.set(key, json.dumps(data), ex=3600)
                    await pipe.execute()
                    break
                except redis.WatchError:
                    continue
        
        data['approved_by'] = set(data['approved_by'])
        return QuorumStateModel(**data)

store = RedisStore()

from pydantic import BaseModel

class RewardRequest(BaseModel):
    user_address: str

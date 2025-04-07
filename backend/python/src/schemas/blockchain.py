from pydantic import BaseModel

class XpMintRequest(BaseModel):
    wallet_address: str
    xp_amount: int

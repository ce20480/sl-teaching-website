from fastapi import APIRouter, Depends, HTTPException
from ...services.blockchain.erc20_service import ERC20Service
from ...core.contracts.registry import ContractRegistry
from ...schemas.blockchain import XpMintRequest

router = APIRouter(prefix="/blockchain", tags=["Blockchain"])

@router.post("/mint-xp")
async def mint_xp(
    request: XpMintRequest,
    erc20_service: ERC20Service = Depends(ERC20Service),
    registry: ContractRegistry = Depends(ContractRegistry)
):
    """
    Mints XP tokens to a user's wallet using ERC20 contract
    """
    try:
        contract = registry.get_contract("erc20_xp")
        tx_hash = await erc20_service.mint_tokens(
            contract_address=contract.address,
            recipient=request.wallet_address,
            amount=request.xp_amount
        )
        return {"transaction_hash": tx_hash.hex()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

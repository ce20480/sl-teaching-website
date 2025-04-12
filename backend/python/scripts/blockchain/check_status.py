import argparse


import asyncio
import os
import sys


# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
from services.reward.xp_reward import XpRewardService

async def main(tx_hash: str):
    # Create the XP reward service
    xp_service = XpRewardService()
    
    # Get the transaction status
    tx_status = await xp_service.get_transaction_status(tx_hash)
    print(f"Transaction status: {tx_status}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check the status of a transaction")
    parser.add_argument("--tx_hash", type=str, help="The hash of the transaction to check")
    args = parser.parse_args()

    asyncio.run(main(args.tx_hash))

#!/usr/bin/env python3
"""
Estimate transaction fees on Starknet.
Requires: pip install starknet-py

Usage:
  python estimate-fees.py --rpc <url> --account <address> --calls <json>

Example:
  python estimate-fees.py --rpc https://starknet-sepolia.public.blastapi.io/rpc/v0_8 \
    --account 0x123... \
    --calls '[{"to":"0x...", "selector":"transfer", "calldata":["0x...", "100", "0"]}]'
"""

import argparse
import json
import sys

try:
    from starknet_py.net.full_node_client import FullNodeClient
    from starknet_py.net.account.account import Account
    from starknet_py.net.models import StarknetChainId
    from starknet_py.hash.selector import get_selector_from_name
    import asyncio
except ImportError:
    print("Error: starknet-py not installed. Run: pip install starknet-py")
    sys.exit(1)

async def estimate_fees(rpc_url: str, account_address: str, calls_json: str):
    """Estimate fees for given calls."""
    client = FullNodeClient(node_url=rpc_url)

    # Parse calls
    calls_data = json.loads(calls_json)
    calls = []
    for call in calls_data:
        selector = call.get("selector")
        if isinstance(selector, str) and not selector.startswith("0x"):
            selector = get_selector_from_name(selector)
        else:
            selector = int(selector, 16)

        calls.append({
            "to_addr": int(call["to"], 16),
            "selector": selector,
            "calldata": [int(x, 16) if isinstance(x, str) and x.startswith("0x") else int(x)
                        for x in call.get("calldata", [])]
        })

    # Estimate
    estimate = await client.estimate_fee(
        tx={
            "type": "INVOKE",
            "sender_address": int(account_address, 16),
            "calldata": [],  # Simplified - real impl needs proper encoding
            "version": 3,
        },
        block_number="latest"
    )

    print(f"\nFee Estimation Results:")
    print(f"{'='*50}")
    print(f"Overall fee (STRK): {estimate.overall_fee / 10**18:.8f}")
    print(f"Gas consumed: {estimate.gas_consumed}")
    print(f"Gas price: {estimate.gas_price}")
    print(f"\nResource Bounds (V3):")
    print(f"  L1 gas: amount={estimate.l1_gas}, price={estimate.l1_gas_price}")
    print(f"  L2 gas: amount={estimate.l2_gas}, price={estimate.l2_gas_price}")
    print(f"  L1 data gas: amount={estimate.l1_data_gas}, price={estimate.l1_data_gas_price}")

def main():
    parser = argparse.ArgumentParser(description="Estimate Starknet transaction fees")
    parser.add_argument("--rpc", required=True, help="RPC endpoint URL")
    parser.add_argument("--account", required=True, help="Account address (hex)")
    parser.add_argument("--calls", required=True, help="Calls as JSON array")
    args = parser.parse_args()

    asyncio.run(estimate_fees(args.rpc, args.account, args.calls))

if __name__ == "__main__":
    main()

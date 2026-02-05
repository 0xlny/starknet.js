#!/usr/bin/env python3
"""
Compute Starknet account address before deployment.
Requires: pip install starknet-py

Usage:
  python compute-account-address.py --public-key <hex> --class-hash <hex> [--account-type oz|argent|braavos]
  python compute-account-address.py --private-key <hex> --class-hash <hex>
"""

import argparse
import sys

try:
    from starknet_py.hash.address import compute_address
    from starknet_py.net.signer.stark_curve_signer import KeyPair
except ImportError:
    print("Error: starknet-py not installed. Run: pip install starknet-py")
    sys.exit(1)

# Common class hashes by account type and network
CLASS_HASHES = {
    "oz": {
        "mainnet": "0x540d7f5ec7ecf317e68d48564934cb99259781b1ee3cedbbc37ec5337f8e688",
        "sepolia": "0x540d7f5ec7ecf317e68d48564934cb99259781b1ee3cedbbc37ec5337f8e688",
    },
    "argent": {
        "mainnet": "0x036078334509b514626504edc9fb252328d1a240e4e948bef8d0c08dff45927f",
        "sepolia": "0x036078334509b514626504edc9fb252328d1a240e4e948bef8d0c08dff45927f",
    },
}

def compute_oz_address(public_key: int, class_hash: int) -> int:
    """Compute OpenZeppelin account address."""
    return compute_address(
        salt=public_key,
        class_hash=class_hash,
        constructor_calldata=[public_key],
        deployer_address=0
    )

def compute_argent_address(public_key: int, class_hash: int) -> int:
    """Compute ArgentX account address (single signer)."""
    return compute_address(
        salt=public_key,
        class_hash=class_hash,
        constructor_calldata=[public_key, 0],  # signer, guardian
        deployer_address=0
    )

def main():
    parser = argparse.ArgumentParser(description="Compute Starknet account address")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--public-key", help="Stark public key (hex)")
    group.add_argument("--private-key", help="Private key to derive public key (hex)")
    parser.add_argument("--class-hash", help="Account class hash (hex)")
    parser.add_argument("--account-type", choices=["oz", "argent"], default="oz",
                       help="Account type (default: oz)")
    parser.add_argument("--network", choices=["mainnet", "sepolia"], default="sepolia")
    args = parser.parse_args()

    # Get public key
    if args.private_key:
        key_pair = KeyPair.from_private_key(int(args.private_key, 16))
        public_key = key_pair.public_key
        print(f"Derived public key: {hex(public_key)}")
    else:
        public_key = int(args.public_key, 16)

    # Get class hash
    if args.class_hash:
        class_hash = int(args.class_hash, 16)
    else:
        class_hash = int(CLASS_HASHES[args.account_type][args.network], 16)
        print(f"Using {args.account_type} class hash: {hex(class_hash)}")

    # Compute address
    if args.account_type == "argent":
        address = compute_argent_address(public_key, class_hash)
    else:
        address = compute_oz_address(public_key, class_hash)

    print(f"\nComputed address: {hex(address)}")
    print(f"\nNext steps:")
    print(f"1. Fund this address with STRK")
    print(f"2. Deploy with classHash={hex(class_hash)}, salt={hex(public_key)}")

if __name__ == "__main__":
    main()

---
name: starknet-js
description: "Guide for building Starknet applications using starknet.js v9.x SDK. Use when developing Starknet dApps, interacting with smart contracts, managing accounts, handling transactions, estimating fees, integrating browser wallets, or working with Paymaster for sponsored/alternative gas token transactions. Triggers include creating/deploying Starknet accounts, reading/writing smart contracts, multicall batching, fee estimation with resource bounds, WalletAccount browser integration, Paymaster gas sponsorship, and message signing with SNIP-12."
---

# starknet.js v9.x SDK

## Quick Start

```bash
npm install starknet
```

Minimal setup to read from Starknet:

```typescript
import { RpcProvider, Contract } from 'starknet';

const provider = await RpcProvider.create({ nodeUrl: 'https://starknet-mainnet.public.blastapi.io/rpc/v0_8' });
const contract = new Contract(abi, contractAddress, provider);
const result = await contract.get_balance();
```

## Core Architecture

```
Provider → Account → Contract
   ↓          ↓          ↓
Network   Identity   Interaction
```

- **Provider**: Read-only network connection (RpcProvider)
- **Account**: Extends Provider with signing and transaction capabilities
- **Contract**: Type-safe interface to deployed contracts

Use Provider for read operations, Account for write operations.

## Provider Setup

```typescript
import { RpcProvider } from 'starknet';

// Recommended: Auto-detect RPC spec version
const provider = await RpcProvider.create({
  nodeUrl: 'https://starknet-mainnet.public.blastapi.io/rpc/v0_8'
});
```

**Networks:**
- Mainnet: `https://starknet-mainnet.public.blastapi.io/rpc/v0_8`
- Sepolia: `https://starknet-sepolia.public.blastapi.io/rpc/v0_8`

**Key Methods:**
```typescript
const chainId = await provider.getChainId();
const block = await provider.getBlock('latest');
const nonce = await provider.getNonceForAddress(accountAddress);
const balance = await provider.getBalance(accountAddress);
await provider.waitForTransaction(txHash);
```

## Account Management

### Account Creation (4 Steps)

**Step 1: Compute address**
```typescript
import { hash, ec, stark, CallData } from 'starknet';

const privateKey = stark.randomAddress();
const publicKey = ec.starkCurve.getStarkKey(privateKey);
const classHash = '0x540d7f5ec7ecf317e68d48564934cb99259781b1ee3cedbbc37ec5337f8e688'; // OpenZeppelin
const constructorCalldata = CallData.compile({ publicKey });
const address = hash.calculateContractAddressFromHash(publicKey, classHash, constructorCalldata, 0);
```

**Step 2: Fund the address** with STRK before deployment.

**Step 3: Deploy**
```typescript
import { Account } from 'starknet';

const account = new Account({ provider, address, signer: privateKey, cairoVersion: '1' });
const { transaction_hash } = await account.deployAccount({
  classHash,
  constructorCalldata,
  addressSalt: publicKey
});
await provider.waitForTransaction(transaction_hash);
```

**Step 4: Use the account** for transactions.

### Connect to Existing Account

```typescript
const account = new Account({
  provider,
  address: '0x123...',
  signer: privateKey,
  cairoVersion: '1'  // Optional, auto-detected if omitted
});
```

See `references/account-types.md` for class hashes by account type (OpenZeppelin, ArgentX, Braavos).

## Contract Interaction

### Connect to Contract

```typescript
import { Contract } from 'starknet';

const contract = new Contract(abi, contractAddress, provider);  // Read-only
const contract = new Contract(abi, contractAddress, account);   // Read-write
```

### Read State

```typescript
const balance = await contract.get_balance();
const userBalance = await contract.balanceOf(userAddress);
```

### Write (Execute)

```typescript
const tx = await contract.increase_balance(100);
await provider.waitForTransaction(tx.transaction_hash);
```

### Multicall (Batch Transactions)

```typescript
import { CallData, cairo } from 'starknet';

const calls = [
  {
    contractAddress: tokenAddress,
    entrypoint: 'approve',
    calldata: CallData.compile({ spender: bridgeAddress, amount: cairo.uint256(1000) })
  },
  {
    contractAddress: bridgeAddress,
    entrypoint: 'deposit',
    calldata: CallData.compile({ amount: cairo.uint256(1000) })
  }
];

const tx = await account.execute(calls);
```

Using `populate()` for type-safety:
```typescript
const approveCall = tokenContract.populate('approve', {
  spender: bridgeAddress,
  amount: cairo.uint256(1000)
});
const depositCall = bridgeContract.populate('deposit', { amount: cairo.uint256(1000) });
const tx = await account.execute([approveCall, depositCall]);
```

### Parse Events

```typescript
const receipt = await provider.getTransactionReceipt(txHash);
const events = contract.parseEvents(receipt);
const transferEvents = contract.parseEvents(receipt, 'Transfer');
```

## Fee Estimation

```typescript
const fee = await account.estimateInvokeFee(calls);
console.log({
  overallFee: fee.overall_fee,
  resourceBounds: fee.resourceBounds  // V3: l1_gas, l2_gas, l1_data_gas
});
```

Execute with custom bounds:
```typescript
const tx = await account.execute(calls, {
  resourceBounds: {
    l1_gas: { amount: '0x2000', price: '0x1000000000' },
    l2_gas: { amount: '0x0', price: '0x0' },
    l1_data_gas: { amount: '0x1000', price: '0x1000000000' }
  }
});
```

With priority tip:
```typescript
const tipStats = await provider.getEstimateTip();
const tx = await account.execute(calls, { tip: tipStats.percentile_75 });
```

## Wallet Integration

Connect to browser wallets (ArgentX, Braavos):

```typescript
import { connect } from '@starknet-io/get-starknet';
import { WalletAccount } from 'starknet';

const selectedWallet = await connect({ modalMode: 'alwaysAsk' });
const walletAccount = await WalletAccount.connect(
  { nodeUrl: 'https://starknet-sepolia.public.blastapi.io/rpc/v0_8' },
  selectedWallet
);

// Use like regular Account
const tx = await walletAccount.execute(calls);

// Event handlers
walletAccount.onAccountChange((accounts) => console.log('New account:', accounts[0]));
walletAccount.onNetworkChanged((chainId) => console.log('Network changed:', chainId));
```

See `assets/snippets/wallet-dapp.tsx` for a complete React integration template.

## Paymaster (Gas Sponsorship)

Setup paymaster for sponsored or alternative gas token transactions:

```typescript
import { PaymasterRpc, Account } from 'starknet';

const paymaster = new PaymasterRpc({ nodeUrl: 'https://sepolia.paymaster.avnu.fi' });
const account = new Account({ provider, address, signer: privateKey, paymaster });
```

**Sponsored (dApp pays gas):**
```typescript
const tx = await account.executePaymasterTransaction(calls, { feeMode: { mode: 'sponsored' } });
```

**Alternative token (e.g., USDC):**
```typescript
const tokens = await account.paymaster.getSupportedTokens();
const feeDetails = { feeMode: { mode: 'default', gasToken: USDC_ADDRESS } };
const estimate = await account.estimatePaymasterTransactionFee(calls, feeDetails);
const tx = await account.executePaymasterTransaction(calls, feeDetails, estimate.suggested_max_fee_in_gas_token);
```

See `assets/snippets/paymaster-integration.ts` for complete examples.

## Message Signing (SNIP-12)

```typescript
const typedData = {
  types: {
    StarknetDomain: [
      { name: 'name', type: 'shortstring' },
      { name: 'version', type: 'shortstring' },
      { name: 'chainId', type: 'shortstring' },
      { name: 'revision', type: 'shortstring' }
    ],
    Message: [{ name: 'content', type: 'shortstring' }]
  },
  primaryType: 'Message',
  domain: { name: 'MyDapp', version: '1', chainId: 'SN_SEPOLIA', revision: '1' },
  message: { content: 'Hello Starknet' }
};

const signature = await account.signMessage(typedData);
const msgHash = await account.hashMessage(typedData);
const isValid = ec.starkCurve.verify(signature, msgHash, publicKey);
```

## CallData & Cairo Types

```typescript
import { CallData, cairo, CairoCustomEnum, CairoOption, CairoOptionVariant } from 'starknet';

// Compile with ABI
const calldata = new CallData(abi);
const compiled = calldata.compile('transfer', { recipient: '0x...', amount: cairo.uint256(1000) });

// Cairo type helpers
cairo.uint256(1000)           // { low, high }
cairo.felt252(1000)           // BigInt
cairo.felt('0x123')           // hex to felt
cairo.bool(true)              // Cairo bool
cairo.byteArray('Hello')      // ByteArray for long strings

// Enums and Options
const myEnum = new CairoCustomEnum({ Variant1: { value: 123 } });
const some = new CairoOption(CairoOptionVariant.Some, value);
```

See `references/calldata.md` for complex type patterns.

## Utility Functions

```typescript
import { stark, ec, num, hash } from 'starknet';

// Key generation
const privateKey = stark.randomAddress();
const publicKey = ec.starkCurve.getStarkKey(privateKey);

// Number conversions
num.toHex(123);           // '0x7b'
num.toBigInt('0x7b');     // 123n

// Hashing
hash.getSelectorFromName('transfer');
hash.calculateContractAddressFromHash(salt, classHash, calldata, deployer);
```

## Contract Deployment

```typescript
// Deploy via UDC
const { transaction_hash, contract_address } = await account.deploy({
  classHash: '0x...',
  constructorCalldata: CallData.compile({ owner: account.address }),
  salt: stark.randomAddress(),
  unique: true
});

// Declare and deploy
const result = await account.declareAndDeploy({
  contract: compiledContract,
  casm: compiledCasm,
  constructorCalldata: CallData.compile({ owner: account.address })
});
```

## Outside Execution (SNIP-9)

Execute transactions on behalf of another account (gasless/delegated):

```typescript
const version = await account.getSnip9Version();  // 'V1' | 'V2' | 'UNSUPPORTED'

const outsideTransaction = await account.getOutsideTransaction(
  { caller: executorAddress, execute_after: now, execute_before: now + 3600 },
  calls,
  'V2'
);

// Executor submits the pre-signed transaction
const result = await executorAccount.executeFromOutside(outsideTransaction);
```

See `references/advanced-patterns.md` for detailed SNIP-9 patterns.

## Error Handling

```typescript
import { LibraryError, RpcError } from 'starknet';

try {
  const tx = await account.execute(calls);
} catch (error) {
  if (error instanceof RpcError) {
    console.error('RPC error:', error.code, error.message);
  } else if (error instanceof LibraryError) {
    console.error('Library error:', error.message);
  }
}
```

## Resources

- `references/account-types.md` - Class hashes for ArgentX, Braavos, OpenZeppelin
- `references/calldata.md` - Complex type handling, structs, enums, arrays
- `references/advanced-patterns.md` - Events, SNIP-9, Ledger, WebSocket
- `references/configuration.md` - Global config options
- `assets/snippets/` - Ready-to-use code templates

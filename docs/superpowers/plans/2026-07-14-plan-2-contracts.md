# RotorVault — Plan 2: Contracts (Foundry / Coston2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** An FXRP vault on Flare **Coston2** whose on-chain logic genuinely consumes all three enshrined protocols — **FTSOv2** (an on-chain regime gate + NAV), **FAssets/FXRP** (the asset, resolved at runtime), **FDC Web2Json** (an attested APY) — routing FXRP across the **real** Firelight & Upshift testnet vaults + idle via adapters, fork-tested against the live vaults and deployed to Coston2.

**Architecture:** `RotorVault` (an ERC-4626-style FXRP share vault) holds user FXRP and, on `rebalance(weights)`, routes it across `IYieldVenue` adapters — but only within bounds a `RegimeGate` (fed by FTSOv2 XRP/USD) allows: when the on-chain regime is risk-off, funds are forced to idle. Firelight and Upshift redemptions are **asynchronous** (request-now / claim-later), so the vault models pending redemptions and a `claimMatured()` step. An `ApyOracle` consumes an FDC Web2Json proof of the Upshift APY to tilt the deployed split. Every Flare address is resolved at runtime from `FlareContractRegistry`.

**Tech Stack:** Foundry (flare-foundry-starter), Solidity 0.8.25 / evm cancun / viaIR, Soldeer deps (`flare-periphery 0.1.37`, `solady`, `forge-std`, `surl`), viem `flareTestnet` (chainId 114) for later plans.

---

## ⚠️ How to read this plan (important)

These contracts integrate with **live external contracts** (Firelight, Upshift, FTSOv2, FDC, FAssets) that cannot be compiled or run in the planning environment. Therefore:

- The **fork tests are the correctness gate** — every integration task ends by running `forge test --fork-url $COSTON2_RPC_URL` against the *real* Coston2 vaults. A task is not done until its fork test passes.
- Exact external struct/enum field names (e.g. `IWeb2Json.Proof`, `FtsoV2Interface`) MUST be taken from the **pinned periphery package** `dependencies/flare-periphery-0.1.37/src/coston2/…` at implementation time; this plan gives the verified **method signatures and addresses** and the import paths, and flags each "confirm-on-fork" item. Treat a signature that doesn't compile against the pinned package as a signal to read the package's actual interface (not to guess).
- The **must-verify-on-fork** items (from the pre-plan research) are woven into Tasks 0/1/4/5/7 as the first assertions.

## Prerequisites (USER — Claude does not do these)

- **Install Foundry** (`foundryup`) — not present locally.
- Create a **Coston2 testnet wallet**; fund it from `https://faucet.flare.network/coston2` (gives C2FLR gas + FXRP + USDT0). Claude never touches the key.
- `contracts/.env` (gitignored) with `COSTON2_RPC_URL=https://coston2-api.flare.network/ext/C/rpc` and, for deployment only, `DEPLOYER_PRIVATE_KEY=…` filled by the user. All `--broadcast` signing is the user's.

## Verified facts (from on-chain research — resolve addresses at runtime regardless)

| Item | Value |
|---|---|
| FlareContractRegistry (all nets) | `0xaD67FE66660Fb8dFE9d6b1b4240d8650e30F6019` |
| Coston2 | chainId 114, RPC `https://coston2-api.flare.network/ext/C/rpc` |
| FXRP (Coston2, resolve via `AssetManagerFXRP.fAsset()`) | `0x0b6A3645c240605887a5532109323A3E12273dc7`, **6 decimals**, symbol FTestXRP |
| Firelight vault (Coston2) | `0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B` (vault IS the stFXRP share token, 6dp) |
| Upshift vault (Coston2) | `0x24c1a47cD5e8473b64EAB2a94515a196E10C7C81`; LP/share token `0xE084F7328DdAb082A139B880782dCC424D20a1db` |
| FTSO XRP/USD feed id | `0x015852502f55534400000000000000000000000000` |
| FDC (Coston2) | FdcHub `0x48aC463d7975828989331F4De43341627b9c5f1D`, FdcVerification `0x906507E0B64bcD494Db73bd0459d1C667e14B933` |
| FDC verifier / DA (testnet) | `https://fdc-verifiers-testnet.flare.network/verifier/web2/Web2Json/prepareRequest` ; `https://ctn2-data-availability.flare.network/api/v1/fdc/proof-by-request-round-raw` |
| Upshift APY API (mainnet-indexed) | `https://api.upshift.finance/v1/tokenized_vaults/{addr}` → `reported_apy.apy` (fraction) |

**Verified interface signatures** (declare local minimal interfaces for Firelight/Upshift; import FTSO/FDC/FAssets from periphery):
- Firelight: `deposit(uint256 assets,address receiver)→uint256`, `mint(uint256 shares,address receiver)→uint256`, `withdraw(uint256 assets,address receiver,address owner)→uint256` and `redeem(uint256 shares,address receiver,address owner)→uint256` (BOTH burn shares now + create a request for `currentPeriod()`, transfer NO assets), `claimWithdraw(uint256 period)→uint256`, `withdrawalsOf(uint256 period,address account)→uint256`, `isWithdrawClaimed(uint256 period,address account)→bool`, `currentPeriod()→uint256`, `currentPeriodEnd()→uint48`, `asset()→address`, `convertToAssets/Shares`, `totalAssets()`. Source of truth: `flare-hardhat-starter/contracts/firelight/IFirelightVault.sol` (BUSL-1.1; copy it into `src/interfaces/`).
- Upshift (Flare `ITokenizedVault` form — NOT docs.upshift.finance's): `deposit(address assetIn,uint256 amountIn,address receiver)→uint256 shares`, `instantRedeem(uint256 shares,address receiver)`, `requestRedeem(uint256 shares,address receiver)→(uint256 claimableEpoch,uint32 y,uint32 m,uint32 d)`, `claim(uint32 y,uint32 m,uint32 d,address receiver)→(uint256 shares,uint256 assetsAfterFee)`, `previewRedemption(uint256 shares,bool isInstant)→(uint256 assetsAmount,uint256 assetsAfterFee)`, `asset()→address`, `lpTokenAddress()→address`, `lagDuration()→uint256`, `withdrawalFee()→uint256`, `instantRedemptionFee()→uint256`. **Confirm the exact arg types/selectors on a live fork (Task 5) — only the view getters were eth_call-verified; use `previewRedemption`'s `assetsAfterFee` for fees, never a hardcoded %.**
- FTSOv2: `ContractRegistry.getTestFtsoV2().getFeedById(bytes21)→(uint256 value,int8 decimals,uint64 timestamp)` (view/FREE on Coston2). Import `ContractRegistry`, `TestFtsoV2Interface` from `@flarenetwork/flare-periphery-contracts/coston2/…`.
- FAssets: `ContractRegistry.getContractAddressByName("AssetManagerFXRP")` → `IAssetManager.fAsset()`. **Confirm the exact registry name string on a live fork (Task 1).**
- FDC: `ContractRegistry.getFdcVerification().verifyWeb2Json(IWeb2Json.Proof)` (NOT `verifyJsonApi`). Pull `IWeb2Json.Proof`/`.Response`/`.ResponseBody` from the pinned periphery package.

## File Structure

```
contracts/                       Foundry root (based on flare-foundry-starter)
├── foundry.toml  remappings.txt  .env.example  Makefile
├── src/
│   ├── lib/FlareResolver.sol        runtime registry → {FXRP, TestFtsoV2, FdcVerification, AssetManager}
│   ├── RegimeGate.sol               FTSOv2 XRP/USD ring-buffer sampler → riskOn()/nav helpers
│   ├── ApyOracle.sol                FDC verifyWeb2Json consumer → stored per-venue APY (bips)
│   ├── venues/IYieldVenue.sol       uniform adapter interface
│   ├── venues/IdleVenue.sol         holds FXRP, 0 yield, instant
│   ├── venues/MockVenue.sol         our ERC-4626 (fallback + unit tests)
│   ├── venues/FirelightAdapter.sol  wraps live Firelight (async claim)
│   ├── venues/UpshiftAdapter.sol    wraps live Upshift (instant/requested)
│   ├── interfaces/IFirelightVault.sol  IUpshiftVault.sol   (verified minimal)
│   └── RotorVault.sol               FXRP share vault + rebalance + claimMatured
├── test/  (unit *.t.sol + fork *.fork.t.sol)
└── script/Deploy.s.sol
```

---

### Task 0: Foundry scaffold + smoke fork test (de-risk the environment FIRST)

**Files:** `contracts/foundry.toml`, `remappings.txt`, `.env.example`, `test/Smoke.fork.t.sol`

- [ ] **Step 1: Scaffold from the flare-foundry-starter and install deps**

```bash
cd f:/Hacks/rotorvault
git clone --depth 1 https://github.com/flare-foundation/flare-foundry-starter contracts_tmp
mkdir -p contracts && cp contracts_tmp/foundry.toml contracts/foundry.toml
# copy the starter's Makefile + soldeer config; then remove the clone
cp -r contracts_tmp/dependencies contracts/dependencies 2>/dev/null || true
rm -rf contracts_tmp
cd contracts && forge soldeer install
```
If `forge soldeer install` is the wrong incantation for this starter, run `make install` (the starter ships a Makefile target). Confirm `dependencies/flare-periphery-0.1.37/` exists.

The committed `foundry.toml` must be exactly (verified from the starter):
```toml
[profile.default]
solc = "0.8.25"
evm_version = "cancun"
src = "src"
out = "out"
libs = ["dependencies"]
fs_permissions = [{ access = "read-write", path = "./" }]
viaIR = true

[dependencies]
forge-std = "1.9.5"
"@openzeppelin-contracts" = "5.2.0-rc.1"
surl = { version = "0.0.0", git = "https://github.com/memester-xyz/surl.git", rev = "034c912ae9b5e707a5afd21f145b452ad8e800df" }
flare-periphery = "0.1.37"
solady = "0.1.26"

[soldeer]
remappings_generate = false
remappings_regenerate = false
remappings_version = false
remappings_location = "txt"
recursive_deps = true

[rpc_endpoints]
coston2 = "${COSTON2_RPC_URL}"
flare = "${FLARE_RPC_URL}"
```
Ensure `remappings.txt` contains `@flarenetwork/flare-periphery-contracts/=dependencies/flare-periphery-0.1.37/src/` (verify the exact left-hand alias the periphery package expects by grepping the starter's example contracts).

- [ ] **Step 2: Write `.env.example`** (real `.env` is gitignored, user-filled)

```
COSTON2_RPC_URL=https://coston2-api.flare.network/ext/C/rpc
# DEPLOYER_PRIVATE_KEY=  # user fills for deploy only; never commit
```

- [ ] **Step 3: Write the smoke fork test** `test/Smoke.fork.t.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Test} from "forge-std/Test.sol";

interface IERC20Meta { function decimals() external view returns (uint8); function symbol() external view returns (string memory); }
interface IFirelightMin { function asset() external view returns (address); function totalAssets() external view returns (uint256); function currentPeriod() external view returns (uint256); }

contract SmokeForkTest is Test {
    address constant FIRELIGHT = 0x91Bfe6A68aB035DFebb6A770FFfB748C03C0E40B;
    address constant FXRP_C2   = 0x0b6A3645c240605887a5532109323A3E12273dc7;

    function setUp() public { vm.createSelectFork(vm.envString("COSTON2_RPC_URL")); }

    function test_liveFirelightReadable() public view {
        IFirelightMin fl = IFirelightMin(FIRELIGHT);
        address asset = fl.asset();
        assertEq(asset, FXRP_C2, "Firelight.asset() should be Coston2 FXRP");
        assertEq(IERC20Meta(asset).decimals(), 6, "FXRP is 6 decimals");
        fl.totalAssets();        // must not revert
        fl.currentPeriod();      // must not revert
    }
}
```

- [ ] **Step 4: Run the smoke fork test**

```bash
cd contracts && source ../.env 2>/dev/null; forge test --match-path test/Smoke.fork.t.sol --fork-url "$COSTON2_RPC_URL" -vv
```
Expected: PASS. If the public RPC 429s, pin a recent block (`vm.createSelectFork(url, <block>)`) or set `FLARE_RPC_API_KEY`. **If `asset()` is not the FXRP address or decimals ≠ 6, STOP** — the live environment differs from research; re-resolve before continuing.

- [ ] **Step 5: Commit**
```bash
cd f:/Hacks/rotorvault && git add contracts/foundry.toml contracts/remappings.txt contracts/.env.example contracts/test/Smoke.fork.t.sol && git commit -m "chore(contracts): flare-foundry scaffold + live-Firelight smoke fork test"
```

---

### Task 1: `FlareResolver` — resolve FXRP/oracles at runtime (fork test)

**Files:** `src/lib/FlareResolver.sol`, `test/FlareResolver.fork.t.sol`

- [ ] **Step 1: Write the fork test first** — assert the registry resolves the FXRP AssetManager and that `fAsset()` is the 6-dp FXRP.

```solidity
// test/FlareResolver.fork.t.sol
// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;
import {Test} from "forge-std/Test.sol";
import {FlareResolver} from "../src/lib/FlareResolver.sol";

contract FlareResolverForkTest is Test {
    function setUp() public { vm.createSelectFork(vm.envString("COSTON2_RPC_URL")); }
    function test_resolvesFxrp() public view {
        address fxrp = FlareResolver.fxrp();
        assertEq(fxrp, 0x0b6A3645c240605887a5532109323A3E12273dc7);
    }
}
```

- [ ] **Step 2: Implement `src/lib/FlareResolver.sol`** using the periphery `ContractRegistry`. Verified: registry name string is `"AssetManagerFXRP"`, then `IAssetManager.fAsset()`.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {ContractRegistry} from "@flarenetwork/flare-periphery-contracts/coston2/ContractRegistry.sol";
import {IAssetManager} from "@flarenetwork/flare-periphery-contracts/coston2/IAssetManager.sol";
import {TestFtsoV2Interface} from "@flarenetwork/flare-periphery-contracts/coston2/TestFtsoV2Interface.sol";
import {IFdcVerification} from "@flarenetwork/flare-periphery-contracts/coston2/IFdcVerification.sol";

library FlareResolver {
    function assetManagerFXRP() internal view returns (IAssetManager) {
        return IAssetManager(ContractRegistry.getContractAddressByName("AssetManagerFXRP"));
    }
    function fxrp() internal view returns (address) {
        return assetManagerFXRP().fAsset();
    }
    function ftso() internal view returns (TestFtsoV2Interface) {
        return ContractRegistry.getTestFtsoV2();
    }
    function fdc() internal view returns (IFdcVerification) {
        return ContractRegistry.getFdcVerification();
    }
}
```
**Confirm-on-fork:** the exact periphery import paths + the `getTestFtsoV2()`/`getFdcVerification()`/`getContractAddressByName` availability in `flare-periphery 0.1.37`. If `getTestFtsoV2` isn't exposed on Coston2's registry helper, use `ContractRegistry.getFtsoV2()` and mark reads `payable` with a 0 fee. If `"AssetManagerFXRP"` is not found, enumerate `getAllContracts()` on the fork to find the exact name and fix the string.

- [ ] **Step 3: Run** `forge test --match-path test/FlareResolver.fork.t.sol --fork-url "$COSTON2_RPC_URL" -vv` → PASS.
- [ ] **Step 4: Commit** `feat(contracts): FlareResolver runtime address resolution (fork-verified FXRP)`

---

### Task 2: `IYieldVenue` + `IdleVenue` + `MockVenue` (unit tests, no fork)

**Files:** `src/venues/IYieldVenue.sol`, `src/venues/IdleVenue.sol`, `src/venues/MockVenue.sol`, `test/Venues.t.sol`

The uniform adapter interface the vault talks to — hides each venue's async mechanics.

- [ ] **Step 1: `IYieldVenue.sol`**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

/// Uniform adapter over a yield venue. Amounts are in FXRP (6 dp). Redemptions may be async.
interface IYieldVenue {
    function asset() external view returns (address);            // FXRP
    function deposit(uint256 assets) external returns (uint256);  // pulls FXRP from caller, deploys
    function positionValue() external view returns (uint256);     // current FXRP value held for the vault
    /// Request redemption of `assets` FXRP. Returns claimable timestamp (0 == already available/instant).
    function requestRedeem(uint256 assets) external returns (uint256 claimableAt);
    /// Pull any matured FXRP back to the vault. Returns amount delivered.
    function claimMatured() external returns (uint256 delivered);
    function isInstant() external view returns (bool);
}
```

- [ ] **Step 2: Write `test/Venues.t.sol`** (TDD) covering: IdleVenue deposit→positionValue→instant redeem returns exactly the FXRP; MockVenue accrues a set yield and its async request/claim delivers principal+yield after a warp. (Use an OpenZeppelin `ERC20` mock as FXRP.) Write the failing tests first.

- [ ] **Step 3: Implement `IdleVenue.sol`** (holds FXRP, `isInstant()==true`, `requestRedeem` transfers immediately, `claimMatured` returns 0) and **`MockVenue.sol`** (a minimal `solady` ERC-4626 with a settable `exchangeRate` and an async queue keyed by timestamp, `isInstant()==false`). Full code per the tests.

- [ ] **Step 4: Run** `forge test --match-path test/Venues.t.sol -vv` → PASS. **Commit** `feat(contracts): IYieldVenue + IdleVenue + MockVenue (async model)`.

---

### Task 3: `RegimeGate` — FTSOv2 ring-buffer regime (fork read + unit math)

**Files:** `src/RegimeGate.sol`, `test/RegimeGate.t.sol`, `test/RegimeGate.fork.t.sol`

FTSOv2 block-latency feeds keep **no on-chain history**, so the gate self-samples XRP/USD into a ring buffer and computes an SMA; `riskOn()` = latest price ≥ SMA.

- [ ] **Step 1: Unit test (TDD)** the SMA/gate math with prices injected via an internal `_sample(uint256 price, uint64 ts)` test hook (so no oracle needed): fill the buffer, assert `riskOn()` flips when the latest price crosses the mean, assert `sample()` respects a minimum interval.

- [ ] **Step 2: Implement `RegimeGate.sol`**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;
import {FlareResolver} from "./lib/FlareResolver.sol";

contract RegimeGate {
    bytes21 public constant XRP_USD = 0x015852502f55534400000000000000000000000000;
    uint256 public constant N = 20;            // ring size (SMA window)
    uint256 public immutable minInterval;      // seconds between samples
    uint256[N] private _px; uint256 private _count; uint256 private _head; uint64 public lastSampled;

    constructor(uint256 minInterval_) { minInterval = minInterval_; }

    function _read() internal view returns (uint256 price1e18) {
        (uint256 v, int8 dec, ) = FlareResolver.ftso().getFeedById(XRP_USD);
        // normalize to 1e18 regardless of feed decimals (never hardcode `dec`)
        price1e18 = dec >= 0 ? v * (10 ** uint256(uint8(18 - uint8(int8(18) - dec)))) : v; // see note
    }

    function sample() public {
        require(block.timestamp >= lastSampled + minInterval, "too soon");
        _store(_read(), uint64(block.timestamp));
    }
    function _store(uint256 p, uint64 ts) internal {
        _px[_head] = p; _head = (_head + 1) % N; if (_count < N) _count++; lastSampled = ts;
    }
    function sma() public view returns (uint256) {
        if (_count == 0) return 0; uint256 s; for (uint256 i; i < _count; i++) s += _px[i]; return s / _count;
    }
    function latest() public view returns (uint256) { return _px[(_head + N - 1) % N]; }
    function riskOn() public view returns (bool) { return _count >= N && latest() >= sma(); }
}
```
**Confirm-on-fork / fix in code:** the `_read` decimal normalization above is a sketch — implement it cleanly as `price1e18 = v * 10**(18 - uint(uint8(dec)))` when `dec <= 18`, reading `dec` from the feed each call (the research is explicit: **never hardcode decimals**). Consider `getFeedByIdInWei` if the periphery exposes it (returns 18-dp directly), which avoids manual scaling.

- [ ] **Step 3: Fork test** `test/RegimeGate.fork.t.sol` — `vm.createSelectFork`, deploy the gate, call `sample()` once, assert `latest() > 0` and the normalized price is in a sane band (e.g. 0.1e18–100e18 USD). This proves the live FTSO read + scaling.

- [ ] **Step 4: Run both test files (unit no-fork, fork with `--fork-url`). Commit** `feat(contracts): RegimeGate FTSOv2 ring-buffer risk-on/off`.

---

### Task 4: `IFirelightVault` + `FirelightAdapter` (fork test the async claim)

**Files:** `src/interfaces/IFirelightVault.sol`, `src/venues/FirelightAdapter.sol`, `test/FirelightAdapter.fork.t.sol`

- [ ] **Step 1:** Copy the verified interface from `flare-hardhat-starter/contracts/firelight/IFirelightVault.sol` into `src/interfaces/IFirelightVault.sol` (BUSL-1.1 — keep the license header). Trim to the functions the adapter uses: `deposit`, `redeem`, `claimWithdraw`, `withdrawalsOf`, `isWithdrawClaimed`, `currentPeriod`, `currentPeriodEnd`, `asset`, `convertToAssets`, `balanceOf`.

- [ ] **Step 2: Fork test (TDD)** `test/FirelightAdapter.fork.t.sol`: fork Coston2; `deal` or prank an FXRP holder to fund the adapter; `deposit` → assert `positionValue() ≈ deposited`; `requestRedeem(all)` → assert Firelight shares burned and a request recorded for `currentPeriod()`; `vm.warp` past `currentPeriodEnd()`; `claimMatured()` → assert FXRP returned to the vault. (Getting test FXRP on a fork: impersonate a known FXRP holder via `vm.startPrank`, or `deal(FXRP, addr, amt)` — note FXRP may block `deal` if it uses non-standard storage; fall back to pranking a whale found on flarescan.)

- [ ] **Step 3: Implement `FirelightAdapter.sol`** — `deposit` approves+calls Firelight `deposit`; `positionValue` = `convertToAssets(firelight.balanceOf(address(this)))` minus pending; `requestRedeem` calls `redeem(shares,...)`, stores `(period ⇒ amount)`, returns `currentPeriodEnd()`; `claimMatured` iterates matured periods, calls `claimWithdraw(period)`, forwards FXRP to the vault (owner). `isInstant()==false`.

- [ ] **Step 4: Run fork test → PASS. Commit** `feat(contracts): FirelightAdapter over live Coston2 vault (async claim)`.

---

### Task 5: `IUpshiftVault` + `UpshiftAdapter` (fork test selectors + fees)

**Files:** `src/interfaces/IUpshiftVault.sol`, `src/venues/UpshiftAdapter.sol`, `test/UpshiftAdapter.fork.t.sol`

- [ ] **Step 1:** Declare `src/interfaces/IUpshiftVault.sol` with the verified Flare-form signatures (see top of plan). **Fork test FIRST** must byte-confirm the action selectors (only view getters were eth_call-verified): a fork test that `deposit`s, then `previewRedemption(shares,true)` vs `(shares,false)` (asserting instant nets less), then `instantRedeem`, then a separate `requestRedeem`→`vm.warp(+lagDuration)`→`claim(y,m,d,...)`. If a selector reverts, read the live contract's ABI on flarescan and correct `IUpshiftVault.sol`.

- [ ] **Step 2: Implement `UpshiftAdapter.sol`** — `deposit(assets)` approves FXRP to the vault and calls `deposit(FXRP, assets, address(this))`; **before any redeem, approve the LP token (`lpTokenAddress()`) to the vault** (confirm this is required on the fork); `requestRedeem(assets)` converts assets→shares, calls `requestRedeem`, stores the returned `(y,m,d)`, returns the claimable timestamp; `claimMatured` calls `claim(y,m,d,owner)`; `positionValue` via `previewRedemption(shares,false).assetsAmount`. **Never hardcode the fee** — always use `previewRedemption`'s `assetsAfterFee`.

- [ ] **Step 3: Run fork test → PASS. Commit** `feat(contracts): UpshiftAdapter over live Coston2 vault (instant/requested)`.

---

### Task 6: `RotorVault` core (unit tests with MockVenue)

**Files:** `src/RotorVault.sol`, `test/RotorVault.t.sol`

- [ ] **Step 1: Unit tests (TDD)** with FXRP = OZ ERC20 mock and two `MockVenue`s + `IdleVenue`, and a `RegimeGate` seeded via its test hook: user `deposit` mints shares 1:1 on first deposit; `rebalance([w_fire, w_up, w_idle])` moves FXRP into venues per weights **only when `gate.riskOn()`** — assert that when the gate is risk-off, `rebalance` forces everything to idle regardless of weights; `claimMatured()` pulls matured venue funds back; user `withdraw` burns shares for FXRP (from idle first, else queues). Assert share accounting and that weights sum-check reverts on >1e4 bips.

- [ ] **Step 2: Implement `RotorVault.sol`** — a `solady` ERC20 share token; holds FXRP; `agent`/`owner` roles (agent may only call `rebalance` within gate bounds); `rebalance(uint16[3] bipsWeights, apy inputs)` reads `gate.riskOn()` and, if risk-off, overrides to `[0,0,10000]`; deploys/withdraws venues to hit target; `claimMatured()` loops venues; pausable; no key custody. Keep the file focused (< ~250 lines); if it grows past that, report DONE_WITH_CONCERNS.

- [ ] **Step 3: Run `forge test --match-path test/RotorVault.t.sol` → PASS. Commit** `feat(contracts): RotorVault FXRP share vault + FTSO-gated rebalance`.

---

### Task 7: `ApyOracle` — FDC Web2Json consumer (unit + structure)

**Files:** `src/ApyOracle.sol`, `test/ApyOracle.t.sol`

- [ ] **Step 1:** Pull `IWeb2Json.Proof/.Response/.ResponseBody` from `dependencies/flare-periphery-0.1.37/src/coston2/…` (read the actual file for exact fields). **Unit test (TDD)**: construct a `Proof` whose `ResponseBody.abiEncodedData` decodes to a `uint256 apyBips`, stub `FdcVerification.verifyWeb2Json` to return true via an injected verifier interface (constructor-injected so tests don't need a fork), and assert `submitApy(proof)` stores `apyBips`. Assert it reverts when the verifier returns false.

- [ ] **Step 2: Implement `ApyOracle.sol`** — constructor takes the `IFdcVerification` (default = `FlareResolver.fdc()`); `submitApy(IWeb2Json.Proof calldata p)` requires `verifier.verifyWeb2Json(p)`, decodes `p.data.responseBody.abiEncodedData` to `(uint256 apyBips)`, stores it with `block.timestamp`; `apy()` view returns the latest. Document that the jq transform scales `reported_apy.apy` (a fraction) to integer bips off-chain (floor/round are disallowed jq builtins → truncate via string-split), `abiSignature = uint256`.

- [ ] **Step 3:** Add a `script/RequestApy.s.sol` (uses `surl`) that hits the FDC verifier `prepareRequest` + DA `proof-by-request-round-raw` for the Upshift API — this is the off-chain half, run by the user (needs the testnet verifier key). Mark it a script, not a test.

- [ ] **Step 4: Run unit test → PASS. Commit** `feat(contracts): ApyOracle FDC verifyWeb2Json consumer`.

---

### Task 8: `RotorVault` end-to-end fork integration (real venues + FTSO)

**Files:** `test/RotorVault.fork.t.sol`

- [ ] **Step 1: Fork integration test** — fork Coston2; deploy `FlareResolver`-using `RegimeGate`, `FirelightAdapter`, `UpshiftAdapter`, `IdleVenue`, `RotorVault`; fund with real FXRP (prank a holder); `gate.sample()` (or seed via warp+multiple samples); user deposits; agent `rebalance` splits across the **real** Firelight + Upshift; assert `positionValue`s move; force risk-off (seed a falling price) and assert the next `rebalance` pulls to idle; `claimMatured` after warping periods. This is the headline "it really works on Coston2" proof.

- [ ] **Step 2: Run `forge test --match-path test/RotorVault.fork.t.sol --fork-url "$COSTON2_RPC_URL" -vv`.** Some steps (real redemptions) may need block warping; if a live vault path is flaky, document it and fall back to `MockVenue` for that leg while keeping ≥1 real-venue leg green. **Commit.**

---

### Task 9: Deploy to Coston2 + verify + record addresses (USER signs)

**Files:** `script/Deploy.s.sol`, `README` deploy section

- [ ] **Step 1: Write `script/Deploy.s.sol`** — deploys RegimeGate, the three adapters (pointed at the real Coston2 vault addresses), ApyOracle, and RotorVault, wiring them; reads no secrets in code (uses `--private-key`/env at broadcast).
- [ ] **Step 2 (USER):** dry-run then broadcast:
```bash
cd contracts && forge script script/Deploy.s.sol --rpc-url coston2 --sender <addr> -vvvv         # simulate
forge script script/Deploy.s.sol --rpc-url coston2 --broadcast --private-key $DEPLOYER_PRIVATE_KEY  # user signs
```
- [ ] **Step 3 (USER): verify on Blockscout** (compiler settings must match exactly 0.8.25/cancun/viaIR):
```bash
forge verify-contract <addr> src/RotorVault.sol:RotorVault --verifier blockscout --verifier-url https://coston2-explorer.flare.network/api/ --watch
```
- [ ] **Step 4:** Record deployed addresses in `contracts/deployments/coston2.json` + the top-level README; commit (addresses only — no keys). `docs(contracts): Coston2 deployment addresses`.

---

## Self-Review (plan author)

- **Spec coverage:** implements spec §3 (contracts), §4 (all three enshrined protocols on-chain: FTSOv2 in RegimeGate, FAssets/FXRP as the asset via FlareResolver, FDC Web2Json in ApyOracle), §7 (RotorVault + IYieldVenue adapters + real-vs-mock via MockVenue). Agent (§8) and dashboard (§9) are Plans 3–4.
- **Placeholder scan:** external-contract structs (IWeb2Json.Proof, exact periphery paths) are referenced to the pinned package with confirm-on-fork gates rather than guessed — this is deliberate for live-contract integration, and each is a named fork assertion, not a vague TODO. All *our* contracts have concrete code or a concrete test-first spec.
- **Type consistency:** `IYieldVenue` (asset/deposit/positionValue/requestRedeem/claimMatured/isInstant) is used identically by IdleVenue, MockVenue, FirelightAdapter, UpshiftAdapter, and RotorVault. `RegimeGate.riskOn()` is consumed by RotorVault.rebalance. `ApyOracle.apy()` feeds the deployed split.
- **Known risks carried from research:** async redemptions (modeled via requestRedeem/claimMatured), Upshift selector/fee/LP-approve unknowns (fork-gated in Task 5), FXRP 6-dp (no 18-dp assumptions), upgradeable-proxy vaults (pin behavior via fork tests), public-RPC rate limits (pin block / api key), FDC mainnet-whitelist caveat (Coston2 PublicWeb2 only).
- **Execution prerequisite:** Foundry + a funded Coston2 wallet (user). Tasks 0/1/3–5/8 require `--fork-url`; Tasks 2/6/7 are pure unit tests runnable without network once Foundry is installed.

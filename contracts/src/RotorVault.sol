// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {ERC20} from "@openzeppelin-contracts/token/ERC20/ERC20.sol";
import {IERC20} from "@openzeppelin-contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin-contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin-contracts/access/Ownable.sol";
import {IYieldVenue} from "./venues/IYieldVenue.sol";
import {IRegimeGate} from "./interfaces/IRegimeGate.sol";

/// A self-driving, risk-managed FXRP yield vault. Users deposit FXRP for `rvFXRP` shares. An agent
/// proposes an allocation across the Firelight and Upshift venues (the remainder stays idle as
/// vault-held FXRP), but the FTSOv2-driven RegimeGate can VETO it: whenever riskOn() is false, the
/// vault forces everything to idle. Redemptions from venues are asynchronous, so reducing a venue
/// requests a redemption that is delivered later via claimMatured().
///
/// Known simplification (documented): in-flight (requested-but-unclaimed) redemptions are not counted
/// in totalAssets(); deposits/withdrawals should not be made in the middle of a rebalance cycle.
contract RotorVault is ERC20, Ownable {
    using SafeERC20 for IERC20;

    uint16 public constant BPS = 10_000;

    IERC20 public immutable fxrp;
    IRegimeGate public immutable gate;
    IYieldVenue public immutable firelight;
    IYieldVenue public immutable upshift;

    address public agent;
    bool public paused;
    uint256 public inflight; // FXRP requested out of venues, awaiting claim (kept in NAV)

    event AgentSet(address indexed agent);
    event PausedSet(bool paused);
    event Rebalanced(uint16 wFirelight, uint16 wUpshift, bool riskOn, uint256 nav);
    event Deposited(address indexed who, uint256 assets, uint256 shares);
    event Withdrawn(address indexed who, uint256 shares, uint256 assets);

    constructor(address fxrp_, address gate_, address firelight_, address upshift_)
        ERC20("RotorVault FXRP", "rvFXRP")
        Ownable(msg.sender)
    {
        fxrp = IERC20(fxrp_);
        gate = IRegimeGate(gate_);
        firelight = IYieldVenue(firelight_);
        upshift = IYieldVenue(upshift_);
    }

    modifier onlyAgent() {
        require(msg.sender == agent || msg.sender == owner(), "RotorVault: not agent");
        _;
    }

    modifier notPaused() {
        require(!paused, "RotorVault: paused");
        _;
    }

    function decimals() public pure override returns (uint8) {
        return 6; // match FXRP
    }

    function setAgent(address a) external onlyOwner {
        agent = a;
        emit AgentSet(a);
    }

    function setPaused(bool p) external onlyOwner {
        paused = p;
        emit PausedSet(p);
    }

    /// Idle FXRP + value deployed in venues + FXRP in-flight from redemptions, so NAV stays continuous
    /// across an async rebalance and mid-rebalance deposits/withdrawals can't misprice shares.
    function totalAssets() public view returns (uint256) {
        return fxrp.balanceOf(address(this)) + firelight.positionValue() + upshift.positionValue() + inflight;
    }

    function deposit(uint256 assets, address receiver) external notPaused returns (uint256 shares) {
        require(assets > 0, "RotorVault: zero");
        uint256 ta = totalAssets();
        uint256 ts = totalSupply();
        shares = (ts == 0 || ta == 0) ? assets : (assets * ts) / ta;
        fxrp.safeTransferFrom(msg.sender, address(this), assets);
        _mint(receiver, shares);
        emit Deposited(msg.sender, assets, shares);
    }

    /// Withdraw shares for FXRP from the idle buffer. If idle is insufficient (funds are deployed or
    /// in-flight), the caller must wait for a rebalance-to-idle + claimMatured to free liquidity.
    function withdraw(uint256 shares, address receiver) external notPaused returns (uint256 assets) {
        require(shares > 0 && shares <= balanceOf(msg.sender), "RotorVault: bad shares");
        assets = (shares * totalAssets()) / totalSupply();
        require(assets <= fxrp.balanceOf(address(this)), "RotorVault: insufficient idle; claimMatured/rebalance first");
        _burn(msg.sender, shares);
        fxrp.safeTransfer(receiver, assets);
        emit Withdrawn(msg.sender, shares, assets);
    }

    /// Agent proposes weights (bips) for firelight + upshift; the remainder stays idle. The FTSO gate
    /// overrides everything to idle when risk-off.
    function rebalance(uint16 wFirelight, uint16 wUpshift) external onlyAgent notPaused {
        require(uint256(wFirelight) + wUpshift <= BPS, "RotorVault: weights > 100%");
        bool on = gate.riskOn();
        if (!on) {
            wFirelight = 0;
            wUpshift = 0;
        }
        uint256 nav = totalAssets();
        _target(firelight, (nav * wFirelight) / BPS);
        _target(upshift, (nav * wUpshift) / BPS);
        emit Rebalanced(wFirelight, wUpshift, on, nav);
    }

    function _target(IYieldVenue v, uint256 target) internal {
        uint256 cur = v.positionValue();
        if (cur < target) {
            uint256 need = target - cur;
            uint256 avail = fxrp.balanceOf(address(this));
            uint256 amt = need < avail ? need : avail;
            if (amt > 0) {
                fxrp.forceApprove(address(v), amt);
                v.deposit(amt);
            }
        } else if (cur > target) {
            uint256 amt = cur - target;
            inflight += amt; // keep the requested amount in NAV until it is claimed back
            v.requestRedeem(amt); // async; delivered later via claimMatured()
        }
    }

    /// Pull any matured venue redemptions back into the idle buffer; clear them from in-flight.
    function claimMatured() external returns (uint256 delivered) {
        delivered = firelight.claimMatured() + upshift.claimMatured();
        inflight = inflight > delivered ? inflight - delivered : 0;
    }
}

// SPDX-License-Identifier: MIT
pragma solidity 0.8.25;

import {Script} from "forge-std/Script.sol";
import {Surl} from "surl/Surl.sol";
import {Strings} from "@openzeppelin-contracts/utils/Strings.sol";
import {Base as StringsBase} from "src/utils/fdcStrings/Base.sol";
import {Base} from "./fdcExample/Base.s.sol";
import {IWeb2Json} from "flare-periphery/src/coston2/IWeb2Json.sol";
import {ApyOracle} from "src/ApyOracle.sol";

// FDC Web2Json round-trip for the Upshift APY -> ApyOracle. Four steps (files in data/):
//   1) PrepareApyRequest    (no broadcast) -> data/Apy_abiEncodedRequest.txt
//   2) SubmitApyRequest     (broadcast)    -> data/Apy_votingRoundId.txt
//   3) [wait ~180s for the voting round to finalize]
//   4) RetrieveApyProof     (no broadcast) -> data/Apy_proof.txt
//   5) SubmitApyToOracle     (broadcast)   -> ApyOracle.submitApy(proof)
// See contracts/scripts/fdc-run.sh for the orchestrator.

string constant dirPath = "data/";
string constant prefix = "Apy";

contract PrepareApyRequest is Script {
    using Surl for *;

    // The APY source bound into ApyOracle.expectedUrlHash. jq scales reported_apy.apy (a fraction)
    // to integer bips; floor/round are disallowed jq builtins, so truncate via string-split on ".".
    string public apiUrl = "https://api.upshift.finance/v1/tokenized_vaults/0x373D7d201C8134D4a2f7b5c63560da217e3dEA28";
    string public httpMethod = "GET";
    string public headers = "";
    string public queryParams = "{}";
    string public body = "{}";
    string public postProcessJq =
        "{apyBips: ((.reported_apy.apy * 10000) | tostring | split(\\\".\\\") | .[0] | tonumber)}";
    string public abiSignature =
        "{\\\"components\\\": [{\\\"internalType\\\": \\\"uint256\\\", \\\"name\\\": \\\"apyBips\\\", \\\"type\\\": \\\"uint256\\\"}],\\\"name\\\": \\\"dto\\\",\\\"type\\\": \\\"tuple\\\"}";
    string public sourceName = "PublicWeb2";

    function run() external {
        string memory attestationType = Base.toUtf8HexString("Web2Json");
        string memory sourceId = Base.toUtf8HexString(sourceName);
        string memory requestBody = _body();
        (string[] memory hdrs, string memory reqBody) =
            Base.prepareAttestationRequest(attestationType, sourceId, requestBody);
        string memory url = string.concat(vm.envString("VERIFIER_URL_TESTNET"), "/verifier/web2/Web2Json/prepareRequest");
        (, bytes memory data) = url.post(hdrs, reqBody);
        Base.AttestationResponse memory response = Base.parseAttestationRequest(data);
        require(
            keccak256(bytes(response.status)) == keccak256(bytes("VALID")),
            string.concat("Verifier error: ", response.status)
        );
        Base.writeToFile(
            dirPath, string.concat(prefix, "_abiEncodedRequest"), StringsBase.toHexString(response.abiEncodedRequest), true
        );
    }

    function _body() private view returns (string memory) {
        return string.concat(
            '{"url": "', apiUrl,
            '","httpMethod": "', httpMethod,
            '","headers": "', headers,
            '","queryParams": "', queryParams,
            '","body": "', body,
            '","postProcessJq": "', postProcessJq,
            '","abiSignature": "', abiSignature, '"}'
        );
    }
}

contract SubmitApyRequest is Script {
    function run() external {
        bytes memory request = vm.parseBytes(vm.readLine(string.concat(dirPath, prefix, "_abiEncodedRequest.txt")));
        uint256 timestamp = Base.submitAttestationRequest(request);
        uint256 votingRoundId = Base.calculateRoundId(timestamp);
        Base.writeToFile(dirPath, string.concat(prefix, "_votingRoundId"), Strings.toString(votingRoundId), true);
    }
}

contract RetrieveApyProof is Script {
    using Surl for *;

    function run() external {
        string memory requestBytes = vm.readLine(string.concat(dirPath, prefix, "_abiEncodedRequest.txt"));
        string memory votingRoundId = vm.readLine(string.concat(dirPath, prefix, "_votingRoundId.txt"));

        string[] memory hdrs = Base.prepareHeaders(vm.envString("X_API_KEY"));
        string memory reqBody =
            string.concat('{"votingRoundId":', votingRoundId, ',"requestBytes":"', requestBytes, '"}');
        string memory url =
            string.concat(vm.envString("COSTON2_DA_LAYER_URL"), "/api/v1/fdc/proof-by-request-round-raw");

        (, bytes memory data) = Base.postAttestationRequest(url, hdrs, reqBody);
        bytes memory dataJson = Base.parseData(data);
        Base.ParsableProof memory proof = abi.decode(dataJson, (Base.ParsableProof));
        IWeb2Json.Response memory proofResponse = abi.decode(proof.responseHex, (IWeb2Json.Response));
        IWeb2Json.Proof memory _proof = IWeb2Json.Proof(proof.proofs, proofResponse);
        Base.writeToFile(dirPath, string.concat(prefix, "_proof"), StringsBase.toHexString(abi.encode(_proof)), true);
    }
}

contract SubmitApyToOracle is Script {
    function run() external {
        address oracleAddr = vm.envAddress("APY_ORACLE");
        bytes memory proofBytes = vm.parseBytes(vm.readLine(string.concat(dirPath, prefix, "_proof.txt")));
        IWeb2Json.Proof memory proof = abi.decode(proofBytes, (IWeb2Json.Proof));
        vm.startBroadcast(vm.envUint("PRIVATE_KEY"));
        ApyOracle(oracleAddr).submitApy(proof);
        vm.stopBroadcast();
    }
}

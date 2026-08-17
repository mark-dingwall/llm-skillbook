"""Real-bwrap containment proof for evidence-gate execution.

Task 5's carry-forward (task-5-report.md, "CARRY-FORWARD"): the ordinary
Codex mapping always mounts auth.json and leaves network on; a gate/FIX
child MUST use a separate no-auth/no-network mapping and must not reuse
build_codex_call. These tests prove evidence.py's gate mapping is that
separate, stricter mapping -- empirically, against real bwrap, the same way
tests/integration/test_execution_containment.py proved the ordinary mapping.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from review_loop.evidence import (
    Gate,
    build_gate_mapping,
    execute_gate,
    resolve_gate_host_paths,
)
from review_loop.seals import GitPolicy, seal_target

GATE_PROBE = Path(__file__).resolve().parent / "fixtures" / "gate_probe.py"

BWRAP_AVAILABLE = shutil.which("bwrap") is not None


def probe_gate(argv_tail, *, extra_inputs=(), timeout=30):
    """Run gate_probe.py under the real gate mapping; return its results dict."""
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    target = root / "target"
    target.mkdir()
    (target / "readonly.txt").write_bytes(b"hello")
    subprocess.run(["git", "init", "-q"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=target, check=True)
    subprocess.run(["git", "add", "-A"], cwd=target, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=target, check=True)

    seal = seal_target(target, GitPolicy(enabled=True, base="HEAD"))
    host = resolve_gate_host_paths()
    call_dir = root / "call"
    mapping = build_gate_mapping(host, seal, call_dir, inputs_ro=(GATE_PROBE, *extra_inputs))
    results_path = mapping.scratch_rw / "results.json"

    gate = Gate(
        id="tests",
        argv=("python3", "/inputs/0/gate_probe.py", *argv_tail, "--results", "/scratch/results.json"),
        applicability="applicable",
        classification="required",
        rationale="probe",
        provenance="scout",
    )
    result = execute_gate(gate, mapping, seal, timeout=timeout)
    data = json.loads(results_path.read_text()) if results_path.exists() else None
    return result, data, root, seal, mapping, tmp


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class GateContainmentTests(unittest.TestCase):
    def test_no_credential_or_secret_env_visible(self):
        import os

        os.environ["FAKE_PROVIDER_TOKEN"] = "should-never-be-visible"
        self.addCleanup(lambda: os.environ.pop("FAKE_PROVIDER_TOKEN", None))
        result, data, root, seal, mapping, tmp = probe_gate(["--env-dump"])
        try:
            self.assertEqual(result.status, "PASSED")
            env = data["env"]
            self.assertNotIn("FAKE_PROVIDER_TOKEN", env)
            # the gate mapping mounts no auth/credential file at all
            self.assertNotIn("CODEX_HOME", env)
        finally:
            tmp.cleanup()

    def test_network_is_unreachable(self):
        result, data, root, seal, mapping, tmp = probe_gate(["--connect", "127.0.0.1:80"])
        try:
            self.assertEqual(result.status, "PASSED")
            self.assertFalse(data["connects"]["127.0.0.1:80"]["ok"])
        finally:
            tmp.cleanup()

    def test_target_is_read_only_scratch_is_writable(self):
        result, data, root, seal, mapping, tmp = probe_gate([
            "--write", "/subject/readonly.txt",
            "--write", "/scratch/ok.txt",
        ])
        try:
            self.assertEqual(result.status, "PASSED")
            self.assertFalse(data["writes"]["/subject/readonly.txt"]["ok"])
            self.assertTrue(data["writes"]["/scratch/ok.txt"]["ok"])
        finally:
            tmp.cleanup()

    def test_cannot_read_an_unmounted_host_secret(self):
        with tempfile.NamedTemporaryFile(prefix="host-secret-", suffix=".txt", delete=False) as fh:
            fh.write(b"top secret")
            secret_path = fh.name
        try:
            result, data, root, seal, mapping, tmp = probe_gate(["--read", secret_path])
            try:
                self.assertEqual(result.status, "PASSED")
                self.assertFalse(data["reads"][secret_path]["ok"])
            finally:
                tmp.cleanup()
        finally:
            Path(secret_path).unlink(missing_ok=True)

    def test_argv_result_and_seal_are_recorded_exactly(self):
        result, data, root, seal, mapping, tmp = probe_gate(["--exit", "0"])
        try:
            self.assertEqual(result.gate_id, "tests")
            self.assertEqual(result.target_seal, seal.digest)
            self.assertEqual(
                result.argv,
                (
                    "python3", "/inputs/0/gate_probe.py", "--exit", "0",
                    "--results", "/scratch/results.json",
                ),
            )
            self.assertEqual(result.status, "PASSED")
            self.assertEqual(result.exit_status, 0)
        finally:
            tmp.cleanup()

    def test_gate_mapping_has_no_network_and_no_credentials(self):
        _, _, root, seal, mapping, tmp = probe_gate(["--exit", "0"])
        try:
            self.assertFalse(mapping.network)
            self.assertEqual(mapping.credentials, ())
        finally:
            tmp.cleanup()


@unittest.skipUnless(BWRAP_AVAILABLE, "bwrap is not installed")
class OrphanCleanupTests(unittest.TestCase):
    """A double-forked orphan spawned inside a gate cannot survive completion."""

    def test_orphan_heartbeat_stops_when_the_gate_process_tree_ends(self):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        target = root / "target"
        target.mkdir()
        (target / "a.txt").write_bytes(b"x")
        subprocess.run(["git", "init", "-q"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=target, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=target, check=True)
        subprocess.run(["git", "add", "-A"], cwd=target, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=target, check=True)
        seal = seal_target(target, GitPolicy(enabled=True, base="HEAD"))
        host = resolve_gate_host_paths()
        call_dir = root / "call"
        mapping = build_gate_mapping(host, seal, call_dir, inputs_ro=(GATE_PROBE,))
        gate = Gate(
            id="tests",
            argv=(
                "python3", "/inputs/0/gate_probe.py",
                "--spawn-orphan", "/scratch/heartbeat",
                "--results", "/scratch/results.json",
            ),
            applicability="applicable", classification="required",
            rationale="orphan", provenance="scout",
        )
        result = execute_gate(gate, mapping, seal, timeout=10)
        self.addCleanup(tmp.cleanup)
        self.assertEqual(result.status, "PASSED")
        heartbeat = mapping.scratch_rw / "heartbeat"
        # give any surviving writer a moment to write, then confirm it stops
        self.assertTrue(heartbeat.exists())
        first = heartbeat.read_text()
        time.sleep(0.3)
        second = heartbeat.read_text()
        self.assertEqual(first, second, "orphan heartbeat kept advancing after the gate ended")


if __name__ == "__main__":
    unittest.main()

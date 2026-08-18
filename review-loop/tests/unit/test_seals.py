import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from review_loop.seals import (
    DeltaArtifact,
    DeltaEntry,
    GitPolicy,
    InputSeal,
    SealError,
    TargetSeal,
    apply_delta_to_target,
    check_run_root_disjoint,
    materialize_delta,
    seal_inputs,
    seal_target,
)

NO_GIT = GitPolicy(enabled=False)


def run_git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def init_repo(root):
    run_git(root, "init", "-q")
    run_git(root, "config", "user.email", "test@example.com")
    run_git(root, "config", "user.name", "Test")


class SealTargetTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_seals_readable_regular_files_and_directories(self):
        (self.root / "sub").mkdir()
        (self.root / "sub" / "a.txt").write_bytes(b"hello")
        seal = seal_target(self.root, NO_GIT)
        self.assertIsInstance(seal, TargetSeal)
        paths = {entry.path for entry in seal.entries}
        self.assertEqual(paths, {"sub", "sub/a.txt"})

    def test_rejects_symlink(self):
        target = self.root / "real.txt"
        target.write_bytes(b"x")
        (self.root / "link").symlink_to(target)
        with self.assertRaises(SealError):
            seal_target(self.root, NO_GIT)

    def test_rejects_fifo(self):
        os.mkfifo(self.root / "pipe")
        with self.assertRaises(SealError):
            seal_target(self.root, NO_GIT)

    def test_rejects_socket(self):
        import socket

        sock = socket.socket(socket.AF_UNIX)
        self.addCleanup(sock.close)
        sock.bind(str(self.root / "sock"))
        with self.assertRaises(SealError):
            seal_target(self.root, NO_GIT)

    def test_rejects_unreadable_entry(self):
        path = self.root / "secret.txt"
        path.write_bytes(b"x")
        path.chmod(0o000)
        self.addCleanup(path.chmod, 0o644)
        if os.geteuid() == 0:
            self.skipTest("root ignores mode bits")
        with self.assertRaises(SealError):
            seal_target(self.root, NO_GIT)

    def test_type_change_during_enumeration_is_rejected(self):
        # A file swapped for a symlink between lstat and open must fail closed,
        # not silently admit whatever the descriptor now resolves to.
        path = self.root / "shifting"
        path.write_bytes(b"x")
        real_open = os.open
        calls = {"n": 0}

        def flaky_open(name, flags, *args, **kwargs):
            if isinstance(name, str) and name == "shifting" and calls["n"] == 0:
                calls["n"] += 1
                path.unlink()
                (self.root / "elsewhere").write_bytes(b"y")
                path.symlink_to(self.root / "elsewhere")
            return real_open(name, flags, *args, **kwargs)

        os.open = flaky_open
        try:
            with self.assertRaises(SealError):
                seal_target(self.root, NO_GIT)
        finally:
            os.open = real_open

    def test_mode_only_change_is_detected_in_delta(self):
        path = self.root / "a.txt"
        path.write_bytes(b"hello")
        before = seal_target(self.root, NO_GIT)
        path.chmod(0o755)
        after = seal_target(self.root, NO_GIT)
        with tempfile.TemporaryDirectory() as out:
            artifact = materialize_delta(before, after, Path(out) / "delta.bin")
        [entry] = artifact.entries
        self.assertEqual(entry.path, "a.txt")
        self.assertTrue(entry.mode_changed)
        self.assertFalse(entry.content_changed)

    def test_empty_directory_change_is_detected_in_delta(self):
        before = seal_target(self.root, NO_GIT)
        (self.root / "empty").mkdir()
        after = seal_target(self.root, NO_GIT)
        with tempfile.TemporaryDirectory() as out:
            artifact = materialize_delta(before, after, Path(out) / "delta.bin")
        [entry] = artifact.entries
        self.assertEqual(entry.path, "empty")
        self.assertEqual(entry.change, "added")

    def test_content_change_is_detected_in_delta(self):
        path = self.root / "a.txt"
        path.write_bytes(b"hello")
        before = seal_target(self.root, NO_GIT)
        path.write_bytes(b"goodbye")
        after = seal_target(self.root, NO_GIT)
        with tempfile.TemporaryDirectory() as out:
            artifact = materialize_delta(before, after, Path(out) / "delta.bin")
        [entry] = artifact.entries
        self.assertEqual(entry.path, "a.txt")
        self.assertTrue(entry.content_changed)
        self.assertFalse(entry.mode_changed)

    def test_delta_output_file_is_written_and_byte_stable(self):
        path = self.root / "a.txt"
        path.write_bytes(b"hello")
        before = seal_target(self.root, NO_GIT)
        path.write_bytes(b"goodbye")
        after = seal_target(self.root, NO_GIT)
        with tempfile.TemporaryDirectory() as out:
            output = Path(out) / "delta.bin"
            first = materialize_delta(before, after, output)
            data = output.read_bytes()
            second = materialize_delta(before, after, Path(out) / "delta2.bin")
            self.assertEqual(data, (Path(out) / "delta2.bin").read_bytes())
            self.assertEqual(first.digest, second.digest)

    def test_nul_safe_path_framing_survives_newline_in_name(self):
        weird = self.root / "weird\nname.txt"
        weird.write_bytes(b"x")
        seal = seal_target(self.root, NO_GIT)
        self.assertIn("weird\nname.txt", {entry.path for entry in seal.entries})

    def test_exclusions_remove_the_path_and_its_descendants(self):
        (self.root / "keep.txt").write_text("keep")
        excluded = self.root / "private"
        excluded.mkdir()
        (excluded / "secret.txt").write_text("secret")

        seal = seal_target(self.root, NO_GIT, exclusions=("private",))

        self.assertEqual({entry.path for entry in seal.entries}, {"keep.txt"})


class GitIndexIdentityTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        init_repo(self.root)
        (self.root / "a.txt").write_bytes(b"hello")
        run_git(self.root, "add", "a.txt")
        run_git(self.root, "commit", "-q", "-m", "initial")

    def test_index_only_change_is_bound_separately_from_tree(self):
        policy = GitPolicy(enabled=True, base="HEAD", head=None, include_index=True)
        before = seal_target(self.root, policy)
        run_git(self.root, "rm", "--cached", "-q", "a.txt")
        after = seal_target(self.root, policy)
        # Working-tree bytes are untouched: the tree digest must not move.
        self.assertEqual(before.tree_digest, after.tree_digest)
        self.assertNotEqual(before.git_index_digest, after.git_index_digest)
        self.assertNotEqual(before.digest, after.digest)
        with tempfile.TemporaryDirectory() as out:
            artifact = materialize_delta(before, after, Path(out) / "delta.bin")
        self.assertTrue(artifact.git_index_changed)
        self.assertEqual(artifact.entries, ())

    def test_absent_base_is_rejected(self):
        policy = GitPolicy(enabled=True, base="", head=None)
        with self.assertRaises(SealError):
            seal_target(self.root, policy)

    def test_excluded_index_changes_do_not_change_the_governing_identity(self):
        (self.root / "private.txt").write_text("one")
        run_git(self.root, "add", "private.txt")
        policy = GitPolicy(enabled=True, base="HEAD", head=None, include_index=True)
        before = seal_target(self.root, policy, exclusions=("private.txt",))
        (self.root / "private.txt").write_text("two")
        run_git(self.root, "add", "private.txt")
        after = seal_target(self.root, policy, exclusions=("private.txt",))
        self.assertEqual(after.digest, before.digest)

    def test_unresolvable_base_is_rejected(self):
        policy = GitPolicy(enabled=True, base="does-not-exist", head=None)
        with self.assertRaises(SealError):
            seal_target(self.root, policy)

    def test_ambiguous_base_is_rejected(self):
        run_git(self.root, "branch", "dup")
        run_git(self.root, "tag", "dup")
        policy = GitPolicy(enabled=True, base="dup", head=None)
        with self.assertRaises(SealError):
            seal_target(self.root, policy)


class SealInputsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_seals_explicit_regular_file_inputs(self):
        f = self.root / "ground-truth.md"
        f.write_bytes(b"truth")
        seal = seal_inputs([f], "target-seal-digest")
        self.assertIsInstance(seal, InputSeal)
        self.assertEqual(seal.target_seal, "target-seal-digest")
        self.assertEqual(len(seal.entries), 1)

    def test_rejects_symlink_input(self):
        real = self.root / "real.md"
        real.write_bytes(b"truth")
        link = self.root / "link.md"
        link.symlink_to(real)
        with self.assertRaises(SealError):
            seal_inputs([link], "target-seal-digest")

    def test_rejects_directory_input(self):
        (self.root / "d").mkdir()
        with self.assertRaises(SealError):
            seal_inputs([self.root / "d"], "target-seal-digest")

    def test_rejects_symlinked_parent_directory(self):
        real_dir = self.root / "real-dir"
        real_dir.mkdir()
        (real_dir / "truth.md").write_bytes(b"truth")
        link_dir = self.root / "link-dir"
        link_dir.symlink_to(real_dir)
        with self.assertRaises(SealError):
            seal_inputs([link_dir / "truth.md"], "target-seal-digest")


class ApplyDeltaToTargetTests(unittest.TestCase):
    """The write-back primitive: replay an already-verified delta from a
    disposable-copy source onto the real target. Highest blast radius in the
    module -- the first thing that writes outside a disposable copy.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.source = self.root / "source"
        self.dest = self.root / "dest"
        self.source.mkdir()
        self.dest.mkdir()

    def test_added_changed_removed_replay_reproduces_after_seal(self):
        (self.source / "keep.txt").write_bytes(b"keep")
        (self.dest / "keep.txt").write_bytes(b"keep")
        (self.source / "gone.txt").write_bytes(b"bye")
        (self.dest / "gone.txt").write_bytes(b"bye")
        before = seal_target(self.dest, NO_GIT)

        # Mutate the source to represent the verified after-state: a content
        # change, a removal, a new file, and a new empty directory.
        (self.source / "keep.txt").write_bytes(b"keep-changed")
        (self.source / "gone.txt").unlink()
        (self.source / "new.txt").write_bytes(b"new")
        (self.source / "newdir").mkdir()
        after = seal_target(self.source, NO_GIT)

        with tempfile.TemporaryDirectory() as out:
            delta = materialize_delta(before, after, Path(out) / "delta.bin")

        apply_delta_to_target(delta, source_root=self.source, dest_root=self.dest)

        result = seal_target(self.dest, NO_GIT)
        self.assertEqual(result.digest, after.digest)

    def test_large_file_replay_is_byte_exact(self):
        # os.write can short-write on a single call; a file large enough to
        # exceed one write's chunk must still land byte-for-byte, not
        # silently truncated. 8 MiB of pseudorandom bytes (not compressible,
        # not all-zero) comfortably exceeds any single-call write chunk.
        import random

        payload = random.Random(0).randbytes(8 * 1024 * 1024)
        (self.source / "big.bin").write_bytes(payload)
        (self.dest / "big.bin").write_bytes(b"")
        before = seal_target(self.dest, NO_GIT)
        after = seal_target(self.source, NO_GIT)

        with tempfile.TemporaryDirectory() as out:
            delta = materialize_delta(before, after, Path(out) / "delta.bin")

        apply_delta_to_target(delta, source_root=self.source, dest_root=self.dest)

        self.assertEqual((self.dest / "big.bin").read_bytes(), payload)
        result = seal_target(self.dest, NO_GIT)
        self.assertEqual(result.digest, after.digest)

    def test_reverse_order_removal_empties_a_directory_the_fix_also_removed(self):
        (self.dest / "sub").mkdir()
        (self.dest / "sub" / "only.txt").write_bytes(b"x")
        before = seal_target(self.dest, NO_GIT)
        # source has neither the file nor the directory: the FIX removed both.
        after = seal_target(self.source, NO_GIT)

        with tempfile.TemporaryDirectory() as out:
            delta = materialize_delta(before, after, Path(out) / "delta.bin")
        self.assertEqual({e.path for e in delta.entries}, {"sub", "sub/only.txt"})

        apply_delta_to_target(delta, source_root=self.source, dest_root=self.dest)

        self.assertFalse((self.dest / "sub").exists())
        result = seal_target(self.dest, NO_GIT)
        self.assertEqual(result.digest, after.digest)

    def test_rejects_a_delta_entry_path_that_escapes_dest_root(self):
        (self.source / "evil.txt").write_bytes(b"x")
        entry = DeltaEntry(
            path="../evil.txt", change="added", before_type=None, after_type="file",
            content_changed=True, mode_changed=True,
        )
        delta = DeltaArtifact(
            output_path=Path("unused"), digest="d", before_seal="b", after_seal="a",
            entries=(entry,), git_index_changed=False,
        )
        with self.assertRaises(SealError):
            apply_delta_to_target(delta, source_root=self.source, dest_root=self.dest)
        self.assertFalse((self.root / "evil.txt").exists())

    def test_rejects_a_symlink_component_at_the_write_boundary(self):
        real_elsewhere = self.root / "elsewhere"
        real_elsewhere.mkdir()
        (self.dest / "linked").symlink_to(real_elsewhere)
        (self.source / "linked").mkdir()
        (self.source / "linked" / "file.txt").write_bytes(b"x")
        entry = DeltaEntry(
            path="linked/file.txt", change="added", before_type=None, after_type="file",
            content_changed=True, mode_changed=True,
        )
        delta = DeltaArtifact(
            output_path=Path("unused"), digest="d", before_seal="b", after_seal="a",
            entries=(entry,), git_index_changed=False,
        )
        with self.assertRaises(SealError):
            apply_delta_to_target(delta, source_root=self.source, dest_root=self.dest)
        self.assertFalse((real_elsewhere / "file.txt").exists())


class RunRootOverlapTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.target = self.root / "target"
        self.target.mkdir()

    def test_run_root_inside_target_is_rejected(self):
        with self.assertRaises(SealError):
            check_run_root_disjoint(self.target, self.target / "runs" / "1")

    def test_target_inside_run_root_is_rejected(self):
        run_root = self.root / "runs"
        run_root.mkdir()
        nested_target = run_root / "sub" / "target"
        nested_target.mkdir(parents=True)
        with self.assertRaises(SealError):
            check_run_root_disjoint(nested_target, run_root)

    def test_identical_paths_are_rejected(self):
        with self.assertRaises(SealError):
            check_run_root_disjoint(self.target, self.target)

    def test_disjoint_paths_are_accepted(self):
        run_root = self.root / "runs" / "1"
        check_run_root_disjoint(self.target, run_root)


if __name__ == "__main__":
    unittest.main()

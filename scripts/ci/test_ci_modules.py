"""Contracts for the CI path split and the fail-closed gate."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import classify_changes as classify_mod
import require_job_results as gate_mod

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / ".github" / "workflows" / "ci.yml"
COLLECT = Path(__file__).resolve().parent / "collect_changed_paths.sh"
UPDATER = classify_mod.IMAGE_UPDATER

CACHE_WORKFLOWS = (
    ".github/workflows/ci.yml",
    ".github/workflows/build-images.yml",
    ".github/workflows/verify-backend.yml",
    ".github/workflows/verify-frontend.yml",
    ".github/workflows/verify-browser.yml",
    ".github/workflows/verify-labs.yml",
    ".github/workflows/verify-safety.yml",
    ".github/workflows/cluster-smoke.yml",
)


def flags(*paths: str) -> dict[str, bool]:
    return classify_mod.classify(list(paths))


class ClassifyTests(unittest.TestCase):
    def test_empty_selects_nothing(self) -> None:
        self.assertEqual(set(flags()), set(classify_mod.MODULES))
        self.assertFalse(any(flags().values()))
        self.assertFalse(any(flags("", "  ").values()))

    def test_unknown_runs_every_module(self) -> None:
        selected = flags("#unknown")
        self.assertTrue(all(selected.values()))
        self.assertTrue(all(flags("docs/readme.md", "#unknown").values()))

    def test_image_updater_alone_selects_nothing(self) -> None:
        self.assertFalse(any(flags(UPDATER).values()))

    def test_image_updater_plus_helm_still_deploys(self) -> None:
        selected = flags(UPDATER, "infra/helm/wellbe-local/values.yaml")
        self.assertTrue(selected["deploy"])
        self.assertFalse(selected["python"])
        self.assertFalse(selected["browser"])

    def test_docs_run_capability_only(self) -> None:
        selected = flags("docs/decisions/example.md")
        self.assertTrue(selected["capability"])
        self.assertFalse(selected["python"])
        self.assertFalse(selected["node"])
        self.assertFalse(selected["deploy"])

    def test_backend_runs_python_and_deploy(self) -> None:
        selected = flags("backend/apps/api/src/wellbe_api/main.py")
        self.assertTrue(selected["python"])
        self.assertTrue(selected["deploy"])
        self.assertFalse(selected["node"])
        self.assertFalse(selected["browser"])

    def test_dependency_script_is_python(self) -> None:
        selected = flags("scripts/qa/check_workspace_deps.py")
        self.assertTrue(selected["python"])
        self.assertFalse(selected["deploy"])

    def test_mobile_is_node_only(self) -> None:
        selected = flags("apps/mobile/App.tsx")
        self.assertTrue(selected["node"])
        self.assertFalse(selected["browser"])
        self.assertFalse(selected["deploy"])

    def test_web_runs_node_browser_and_deploy(self) -> None:
        selected = flags("apps/web/app/page.tsx")
        self.assertTrue(selected["node"])
        self.assertTrue(selected["browser"])
        self.assertTrue(selected["deploy"])
        self.assertFalse(selected["python"])

    def test_ui_package_is_a_browser_input(self) -> None:
        selected = flags("packages/ui/src/button.tsx")
        self.assertTrue(selected["browser"])
        self.assertTrue(selected["node"])
        self.assertTrue(selected["deploy"])

    def test_eslint_package_does_not_start_the_browser(self) -> None:
        selected = flags("packages/eslint-config/index.js")
        self.assertTrue(selected["node"])
        self.assertTrue(selected["deploy"])
        self.assertFalse(selected["browser"])

    def test_labs_stay_in_their_module(self) -> None:
        selected = flags("labs/raw-context-brain/src/store.ts")
        self.assertEqual(
            [name for name, on in selected.items() if on],
            ["labs"],
        )

    def test_migrations_and_postgres_image(self) -> None:
        self.assertTrue(flags("db/migrations/001_init.py")["migrations"])
        self.assertTrue(flags("infra/local/Dockerfile.postgres")["migrations"])
        self.assertTrue(flags("infra/local/Dockerfile.postgres")["deploy"])

    def test_each_safety_input(self) -> None:
        samples = [
            "backend/packages/c10_safety/src/gate.py",
            "backend/packages/contracts/src/wellbe_contracts/triage/red.py",
            "backend/apps/safety-gate/src/main.py",
            "evals/safety/tests/test_triage_corpus.py",
            "docs/safety/safety_model.md",
            ".cursor/rules/wellbe-vision-guardrails.mdc",
            ".cursor/rules/audience-guardrails.mdc",
        ]
        for path in samples:
            with self.subTest(path=path):
                self.assertTrue(flags(path)["safety"], path)

    def test_workflow_edit_runs_every_module(self) -> None:
        self.assertTrue(all(flags(".github/workflows/ci.yml").values()))
        self.assertTrue(all(flags("./.github/actions/setup-uv/action.yml").values()))

    def test_classifier_script_does_not_force_product_modules(self) -> None:
        selected = flags("scripts/ci/classify_changes.py")
        self.assertFalse(any(selected.values()))

    def test_output_is_stable_github_syntax(self) -> None:
        text = classify_mod.format_output(flags("README.md"))
        lines = text.splitlines()
        self.assertEqual([line.split("=")[0] for line in lines], list(classify_mod.MODULES))
        self.assertTrue(all(line.endswith("=true") or line.endswith("=false") for line in lines))

    def test_windows_separators_are_normalized(self) -> None:
        self.assertTrue(flags(r"backend\apps\api\main.py")["python"])


class GateTests(unittest.TestCase):
    def test_docs_shape_passes(self) -> None:
        results = {name: "skipped" for name in gate_mod.EXPECTED}
        results["changes"] = "success"
        results["classifier"] = "success"
        results["capability"] = "success"
        self.assertEqual(gate_mod.evaluate(results), [])

    def test_failed_backend_fails_even_if_cluster_was_skipped(self) -> None:
        results = {name: "success" for name in gate_mod.EXPECTED}
        results["backend"] = "failure"
        results["cluster"] = "skipped"
        problems = gate_mod.evaluate(results)
        self.assertTrue(any(problem.startswith("backend:") for problem in problems))

    def test_missing_result_fails_closed(self) -> None:
        results = {name: "success" for name in gate_mod.EXPECTED}
        del results["browser"]
        self.assertIn("browser: missing result", gate_mod.evaluate(results))
        results["browser"] = "  "
        self.assertIn("browser: missing result", gate_mod.evaluate(results))

    def test_cancelled_and_unknown_fail(self) -> None:
        results = {name: "success" for name in gate_mod.EXPECTED}
        results["cluster"] = "cancelled"
        self.assertTrue(gate_mod.evaluate(results))
        results["cluster"] = "timed_out"
        self.assertTrue(gate_mod.evaluate(results))

    def test_changes_must_succeed(self) -> None:
        results = {name: "success" for name in gate_mod.EXPECTED}
        results["changes"] = "skipped"
        self.assertTrue(gate_mod.evaluate(results))

    def test_env_reader(self) -> None:
        found = gate_mod.results_from_env({"RESULT_BACKEND": "success", "OTHER": "1"})
        self.assertEqual(found, {"backend": "success"})


class WorkflowContractTests(unittest.TestCase):
    def test_orchestrator_wires_every_job_and_result(self) -> None:
        text = CI.read_text(encoding="utf-8")
        for name in gate_mod.EXPECTED:
            self.assertIn(f"\n  {name}:", text, name)
            self.assertIn(f"RESULT_{name.upper()}:", text, name)

    def test_called_workflows_exist_and_are_not_push_triggers(self) -> None:
        text = CI.read_text(encoding="utf-8")
        uses = [
            line.split("uses:", 1)[1].strip()
            for line in text.splitlines()
            if "uses: ./." in line
        ]
        self.assertGreaterEqual(len(uses), 8)
        for relative in uses:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            body = path.read_text(encoding="utf-8")
            self.assertIn("workflow_call:", body, relative)
            self.assertNotIn("pull_request:", body, relative)
            self.assertNotIn("\n  push:", body, relative)

    def test_cluster_allows_a_skipped_module_and_ignores_pull_requests(self) -> None:
        text = CI.read_text(encoding="utf-8")
        self.assertIn("!cancelled()", text)
        self.assertIn('["success","skipped"]', text)
        self.assertIn("outputs.deploy", text)
        self.assertIn("github.event_name == 'pull_request'", text)

    def test_updater_commit_does_not_start_ci_or_image_builds(self) -> None:
        ci = CI.read_text(encoding="utf-8")
        images = (ROOT / ".github/workflows/build-images.yml").read_text(encoding="utf-8")
        self.assertIn("infra/helm/wellbe-local/.argocd-source-wellbe.yaml", ci)
        self.assertNotIn("infra/helm/**", images)

    def test_cache_writers_request_actions_write(self) -> None:
        for relative in CACHE_WORKFLOWS:
            body = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("actions: write", body, relative)

    def test_retired_workflows_are_gone(self) -> None:
        self.assertFalse((ROOT / ".github/workflows/safety-gate.yml").exists())
        self.assertFalse((ROOT / ".github/workflows/db-migrations.yml").exists())

    def test_smoke_command_is_what_the_cluster_runs(self) -> None:
        script = (ROOT / "infra/k8s/deploy-and-smoke.sh").read_text(encoding="utf-8")
        package = (ROOT / "apps/web/package.json").read_text(encoding="utf-8")
        self.assertIn("npm run e2e:smoke", script)
        self.assertNotIn("npm run e2e --workspace", script)
        self.assertIn('"e2e:smoke"', package)


class CollectTests(unittest.TestCase):
    def collect(self, repo: Path, event: str, head: str, base: str = "", before: str = "") -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(
            {
                "EVENT_NAME": event,
                "HEAD_SHA": head,
                "BASE_SHA": base,
                "BEFORE_SHA": before,
            }
        )
        return subprocess.run(
            ["bash", str(COLLECT)],
            cwd=repo,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    def git(self, repo: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", "-c", "user.email=ci@example.com", "-c", "user.name=ci", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    def test_push_diff_rename_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.git(repo, "init", "-b", "main")
            (repo / "keep.txt").write_text("a\n", encoding="utf-8")
            (repo / "gone.txt").write_text("b\n", encoding="utf-8")
            (repo / "old.txt").write_text("c\n", encoding="utf-8")
            self.git(repo, "add", ".")
            self.git(repo, "commit", "-m", "base")
            base = self.git(repo, "rev-parse", "HEAD")
            (repo / "keep.txt").write_text("aa\n", encoding="utf-8")
            (repo / "gone.txt").unlink()
            (repo / "renamed.txt").write_text("c\n", encoding="utf-8")
            (repo / "old.txt").unlink()
            self.git(repo, "add", "-A")
            self.git(repo, "commit", "-m", "edit")
            head = self.git(repo, "rev-parse", "HEAD")
            result = self.collect(repo, "push", head, before=base)
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = set(result.stdout.splitlines())
            self.assertIn("keep.txt", paths)
            self.assertIn("gone.txt", paths)
            self.assertIn("renamed.txt", paths)

    def test_missing_base_and_zero_sha_are_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self.git(repo, "init", "-b", "main")
            (repo / "a.txt").write_text("a\n", encoding="utf-8")
            self.git(repo, "add", ".")
            self.git(repo, "commit", "-m", "one")
            head = self.git(repo, "rev-parse", "HEAD")
            missing = self.collect(repo, "push", head, before="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
            self.assertEqual(missing.returncode, 0, missing.stderr)
            self.assertEqual(missing.stdout.strip(), "#unknown")
            zero = self.collect(repo, "push", head, before="0" * 40)
            self.assertEqual(zero.stdout.strip(), "#unknown")

    def test_dispatch_and_missing_event_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            dispatched = self.collect(repo, "workflow_dispatch", "abc")
            self.assertEqual(dispatched.returncode, 0, dispatched.stderr)
            self.assertEqual(dispatched.stdout.strip(), "#unknown")
            broken = self.collect(repo, "pull_request", "abc")
            self.assertNotEqual(broken.returncode, 0)


if __name__ == "__main__":
    unittest.main()

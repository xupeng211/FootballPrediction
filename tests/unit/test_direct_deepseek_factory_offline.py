"""原费用测试中的完整离线 Factory 模拟；不提供正式 Provider 审核证据。"""

# 保留原测试的延迟导入、fixture alias、模拟接口与断言。
# ruff: noqa: PLR2004, PLC0414, PLC0415, ARG002
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.devops import direct_deepseek_dispute as dispute
from scripts.devops import direct_deepseek_independent_review as runner
from scripts.devops.independent_review_backends import direct_deepseek as backend
from scripts.devops.independent_review_protocol import canonical_json
from tests.helpers.direct_harness_source import portable_harness as portable_harness
from tests.unit.test_direct_deepseek_bound import case as case
from tests.unit.test_direct_deepseek_bound import git
from tests.unit.test_direct_deepseek_bound import no_network as no_network
from tests.unit.test_direct_deepseek_cost_estimate import offline_harness_root
from tests.unit.test_direct_deepseek_dispute import DisputeTransport
from tests.unit.test_direct_deepseek_dispute import integrated as integrated
from tests.unit.test_direct_deepseek_standalone import standalone_case as standalone_case


def test_factory_full_task_rework_two_v2_reviews_shared_budget(integrated, tmp_path, monkeypatch):  # noqa: C901, PLR0915
    """真实 Factory.run / V2 runner / 原 receipt validator；Provider 与环境事实为 fixture。

    Fixture consumer 只接受原 validate_receipt 已验证的 OFFLINE 上下文，不能用于
    CLI 或生产 consumer；正式 consumer 拒绝 fixture 的既有回归仍须通过。
    """
    from argparse import Namespace
    import contextlib
    from copy import deepcopy
    from dataclasses import asdict, replace
    import hashlib
    import importlib
    import importlib.util
    import io
    import shutil
    import subprocess
    import sys

    args, registry = integrated
    runner.build_plan(args)  # 先从冻结 companion 加载原资格模块。
    harness_root = offline_harness_root()
    # 冻结 companion 的资格模块保持原样；仅加载本轮修改的 Controller 模块。
    import harness

    monkeypatch.setattr(harness, "__path__", [str(harness_root / "src/harness"), *harness.__path__])
    for name in (
        "adapters",
        "factory_budget",
        "factory_project",
        "factory_runtime",
        "factory_preflight",
        "factory",
    ):
        spec = importlib.util.spec_from_file_location(
            "harness." + name, harness_root / "src/harness" / (name + ".py")
        )
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, "harness." + name, module)
        spec.loader.exec_module(module)
    from harness import factory_validation as validation
    from harness.adapters import FootballPredictionAdapter
    from harness.factory import Factory, validate_mission
    from harness.factory_budget import TASK_POLICY, TASK_ROUTE, TaskBudget, budget_digest
    from harness.factory_project import FootballPredictionContract
    from harness.factory_runtime import LocalRuntime

    monkeypatch.syspath_prepend(str(harness_root / "tests"))
    phase2 = importlib.import_module("test_factory_phase2")
    from scripts.devops import codex_independent_review as codex_runner
    from scripts.devops import direct_deepseek_receipt_evidence as direct_consumer
    from scripts.devops import independent_review_receipt as receipts
    from scripts.devops.codex_review_contract import review_challenge
    from scripts.devops.codex_reviewer_isolation import ISOLATION_POLICY_VERSION
    from scripts.devops.review_policy import (
        CandidateBinding,
        ReviewEvidence,
        evaluate_review_policy,
    )

    # 临时可信工具仓库包括实际本轮代码；生产 dirty 工作树不会被启用。
    tool = tmp_path / "pinned-toolchain"
    tool.mkdir()
    import tarfile

    archive = subprocess.check_output(
        [
            "git",
            "-C",
            str(Path(runner.__file__).resolve().parents[2]),
            "archive",
            "HEAD",
            "scripts",
            "schemas",
            "Makefile",
            "docs/agentic/independent_review_backends.json",
        ]
    )
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        stream.extractall(tool, filter="data")
    for name in (
        "scripts/devops/independent_review_backends/direct_deepseek.py",
        "scripts/devops/independent_review_backends/direct_deepseek_wire.py",
        "scripts/devops/direct_deepseek_receipt_evidence.py",
        "scripts/devops/direct_deepseek_independent_review.py",
        "scripts/devops/codex_reviewer_isolation.py",
    ):
        (tool / name).write_bytes((Path(runner.__file__).resolve().parents[2] / name).read_bytes())
    git(tool, "init", "-q")
    git(tool, "config", "user.name", "Fixture")
    git(tool, "config", "user.email", "fixture@example.invalid")
    git(tool, "add", ".")
    git(tool, "commit", "-qm", "TEST_ONLY pinned tools")
    # 候选 baseline 带可信治理及 QA 文件，改动仅为 example.py + owner scope。
    for path in tool.rglob("*"):
        if path.is_file() and ".git" not in path.relative_to(tool).parts:
            dest = args.repo_root / path.relative_to(tool)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
    for name, content in {**phase2.QA_SOURCE, **phase2.LOCKS}.items():
        path = args.repo_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    frozen_scope = json.loads(args.mission_scope_file.read_bytes())
    args.mission_scope_file.unlink()  # 仅临时 fixture：scope 由 owner 在候选中 materialize。
    (args.repo_root / "example.py").write_text("VALUE = 1\n")
    git(args.repo_root, "add", ".")
    git(args.repo_root, "commit", "-qm", "TEST_ONLY complete baseline")
    args.base_sha = git(args.repo_root, "rev-parse", "HEAD")
    scope = frozen_scope
    for i, text in enumerate(scope["protected_invariants"]):
        if text.startswith(runner.STANDALONE_MARKER):
            value = json.loads(text[len(runner.STANDALONE_MARKER) :])
            value["football_base"] = args.base_sha
            scope["protected_invariants"][i] = runner.STANDALONE_MARKER + json.dumps(value)
        if text.startswith(dispute.MARKER):
            groups = {
                f"football:{i}": [{"source": "football", "start": 0, "end": 256}] for i in range(11)
            }
            groups["harness:0"] = [{"source": "harness", "start": 0, "end": 256}]
            scope["protected_invariants"][i] = dispute.MARKER + json.dumps(
                {"version": dispute.VERSION, "groups": groups}
            )
    content = json.dumps(scope)
    price = tmp_path / "price.json"
    price.write_bytes(canonical_json(args.price_snapshot))
    control = tmp_path / "task-controller"
    control.mkdir(mode=0o700)
    authority_path = control / "budget.sqlite"
    home = str(tmp_path / "fixture-plus-home")
    email = "fixture@example.invalid"
    binding = {
        "codex_home": home,
        "expires_at": 4102444800,
        "user_confirmed_no_credits_no_topup": True,
        "workspace_id": "fixture-workspace",
        "account_sha256": hashlib.sha256(email.encode()).hexdigest(),
    }
    raw = {
        "version": 2,
        "mission_id": args.mission_id,
        "repository": str(args.repo_root),
        "base": args.base_sha,
        "objective": "TEST_ONLY implement and independently review the example",
        "scope": scope["authorized_paths"],
        "approved_mission_scope": {
            "approval_id": "fixture-owner-scope",
            "mission_id": args.mission_id,
            "base": args.base_sha,
            "path": str(args.mission_scope_file.relative_to(args.repo_root)),
            "content": content,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "expires_at": "2099-01-01T00:00:00+00:00",
        },
    }
    approval = {
        "id": "explicit-e2e-user-authorization",
        "approval_reference": "TEST_ONLY_E2E_APPROVAL",
        "task_sha256": budget_digest(validate_mission(raw)),
        "route": TASK_ROUTE,
        "expires_at": 4102444800,
        "policy": TASK_POLICY,
        "stages": ["plan", "implement", "rework", "checks", "ci", "review", "project_gate"],
        "user_approved": True,
        "authority": str(authority_path),
    }
    approval_file = control / "approval.json"
    approval_file.write_text(json.dumps(approval))
    approval_file.chmod(0o600)
    TaskBudget.initialize(authority_path, approval_file)
    config = {
        "version": 1,
        "simulation": True,
        "budget": {"max_agent_runs": 30},
        "max_rounds": 3,
        "timeout_seconds": 120,
        "checks": [["make", "verify-strict"]],
        "ci": [["make", "verify-pr"]],
        "project_contract": "footballprediction",
        "project_deepseek_backend": "direct-deepseek-api",
        "trusted_validation": phase2.VALIDATION,
        "profiles": {
            "developer": {"provider": "openai", "codex_home": home},
            "reviewer": {"provider": "openai"},
            "second_reviewer": {
                "provider": "deepseek",
                "model": "deepseek-flash",
                "token_file": "/fixture/never-read",
            },
        },
        "task_budget": {
            "authority": str(authority_path),
            "authorization": approval["id"],
            "plus_bindings": {"developer": binding, "reviewer": binding},
            "toolchain": {
                "root": str(tool),
                "head": git(tool, "rev-parse", "HEAD"),
                "runtime_sha256": backend.runtime_identity(),
            },
            "direct": {
                "price_snapshot_file": str(price),
                "credential_sha256": args.credential_sha256,
                "balance_micro_cny": 50_000_000,
                "accepted_account_exposure_micro_cny": 50_000_000,
            },
            "ci_billing": "VERIFIED_NO_INCREMENTAL_COST",
        },
    }
    contexts, order = {}, []
    original_validate = receipts.validate_receipt

    def capture_validate(receipt, **kwargs):
        result = original_validate(receipt, **kwargs)
        contexts[receipt["head_sha"]] = (kwargs, deepcopy(receipt))
        return result

    monkeypatch.setattr(receipts, "validate_receipt", capture_validate)

    def fixture_consume(
        path, *, repo_root, expected_base, expected_head, expected_mission_id, expected_scope_hash
    ):
        receipt = json.loads(Path(path).read_bytes())
        kwargs, original = contexts[expected_head]
        assert receipt == original
        assert receipt["provenance"]["execution_mode"] == "OFFLINE_FIXTURE"
        assert receipt["base_sha"] == expected_base
        assert receipt["head_sha"] == expected_head
        assert receipt["mission_id"] == expected_mission_id
        assert receipt["mission_scope_sha256"] == expected_scope_hash
        assert Path(repo_root).resolve() == kwargs["evidence_context"].repo_root
        stem = receipt["provenance"]["artifact_stem"]
        prompt, raw, final = [
            (Path(path).parent / f"{stem}-{suffix}.json").read_bytes()
            for suffix in ("prompt", "raw", "final")
        ]
        context = kwargs["evidence_context"]
        assert (prompt, raw, final) == (
            context.prompt_bytes,
            context.raw_output_bytes,
            context.final_result_bytes,
        )
        context = replace(
            context, prompt_bytes=prompt, raw_output_bytes=raw, final_result_bytes=final
        )
        result = original_validate(receipt, **{**kwargs, "evidence_context": context})
        return ReviewEvidence(
            backend.BACKEND_ID,
            True,
            result["review_result"],
            expected_base,
            expected_head,
            receipt["diff_sha256"],
            expected_mission_id,
            expected_scope_hash,
            result["finding_counts_by_severity"],
            review_model=backend.MODEL,
            standalone_identity=receipt["provenance"]["standalone_identity"],
            source_bindings_sha256=receipt["provenance"]["source_bindings_sha256"],
            qualification_sha256=receipt["provenance"]["qualification_sha256"],
        )

    # 仅测试内 offline-context consumer；不改变正式 consumer 的 fixture 拒绝语义。
    monkeypatch.setattr(direct_consumer, "consume_direct", fixture_consume)
    original_run = subprocess.run

    def fake_codex(command, **kwargs):
        if str(command[0]) != "/usr/lib/chatgpt/resources/codex":
            return original_run(command, **kwargs)
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, b"codex-cli 0.131.0\n", b"")
        assert "exec" in command
        assert "--output-last-message" in command
        order.append("codex-provider")
        role_args = current_codex[0]
        source = (role_args.repo_root / "example.py").read_text()
        findings = (
            []
            if "VALUE = 2" in source
            else [
                {
                    "severity": "P2",
                    "title": "TEST_ONLY repair value",
                    "path": "example.py",
                    "line": 1,
                    "summary": "Set the fixture value to 2.",
                }
            ]
        )
        output = {
            "result": "FAIL" if findings else "PASS",
            "findings": findings,
            "review_challenge": review_challenge(
                mission_id=role_args.mission_id,
                base_sha=role_args.base_sha,
                head_sha=role_args.head_sha,
                mission_scope_sha256=hashlib.sha256(
                    role_args.mission_scope_file.read_bytes()
                ).hexdigest(),
            ),
        }
        final = json.dumps(output)
        Path(command[command.index("--output-last-message") + 1]).write_text(final)
        events = [
            {"type": "thread.started", "thread_id": "fixture-thread"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": final}},
            {"type": "turn.completed"},
        ]
        return subprocess.CompletedProcess(
            command, 0, ("\n".join(json.dumps(e) for e in events) + "\n").encode(), b""
        )

    monkeypatch.setattr(subprocess, "run", fake_codex)
    monkeypatch.setattr(
        codex_runner,
        "canonical_reviewer_preflight",
        lambda **_kw: {
            "policy": ISOLATION_POLICY_VERSION,
            "canonical_codex_home_external": True,
            "canonical_codex_home_owner_only": True,
            "authentication_mode": "official_chatgpt_stored_state",
            "builder_auth_override_inherited": False,
            "custom_model_provider_inherited": False,
            "cliproxyapi_routing_inherited": False,
            "generic_network_proxy_preserved": False,
            "user_codex_config_ignored": True,
            "pinned_model_active": True,
            "pinned_reasoning_active": True,
        },
    )
    current_codex = [None]
    docker = phase2.FakeDocker()
    actual_preflight = validation.preflight
    monkeypatch.setattr(
        validation,
        "preflight",
        lambda policy, executor=None, *_a, **_kw: actual_preflight(
            policy, executor or docker, *_a, **_kw
        ),
    )
    monkeypatch.setattr(
        validation.DockerExecutor, "call", lambda *_a, **_kw: pytest.fail("REAL Docker forbidden")
    )

    class FixtureAdapter(FootballPredictionAdapter):
        def _call(self, argv, **kwargs):
            if "-c" in argv and "task_balance_end" in argv[argv.index("-c") + 1]:
                value = direct_consumer.task_balance_end(
                    Path(argv[-3]), repo_root=Path(argv[-2]), mission_id=argv[-1]
                )
                return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")
            if "-c" in argv and "_deepseek_receipt_evidence as v" in argv[argv.index("-c") + 1]:
                path, root, base, head, mission, scope_hash = argv[-6:]
                evidence = fixture_consume(
                    path,
                    repo_root=Path(root),
                    expected_base=base,
                    expected_head=head,
                    expected_mission_id=mission,
                    expected_scope_hash=scope_hash,
                )
                return subprocess.CompletedProcess(argv, 0, json.dumps(asdict(evidence)), "")
            if "classify" in argv and "codex_independent_review.py" in "".join(argv):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    code = codex_runner.main(argv[argv.index("classify") :])
                return subprocess.CompletedProcess(argv, code, output.getvalue(), "")
            return super()._call(argv, **kwargs)

    original_adapter_call = FootballPredictionAdapter._call

    def fixture_adapter_call(_self, argv, **kwargs):
        if "-c" in argv and "task_balance_end" in argv[argv.index("-c") + 1]:
            value = direct_consumer.task_balance_end(
                Path(argv[-3]), repo_root=Path(argv[-2]), mission_id=argv[-1]
            )
            return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")
        return original_adapter_call(argv, **kwargs)

    monkeypatch.setattr(FootballPredictionAdapter, "_call", fixture_adapter_call)

    active_role, app_reads = [None], []

    class FixtureAppServer:
        def __init__(self, profile, cwd, transcript, *_a, **_kw):
            self.cwd, self.transcript = cwd, transcript
            self.proc, self._proxy_relay = None, None
            self._source_home = profile["codex_home"]
            self.usage, self.runtime_identity = {"fixture_provider_calls": 0}, {"fixture": True}

        def _request(self, method, params):
            assert (method, params) == ("account/read", {"refreshToken": False})
            app_reads.append(active_role[0])
            return {
                "account": {
                    "type": "chatgpt",
                    "planType": "plus",
                    "email": email,
                    "workspaceId": "fixture-workspace",
                }
            }

        def execute(self, prompt, schema):
            role = active_role[0]
            cwd, transcript = self.cwd, self.transcript
            order.append(role)
            if role == "plan":
                output = {
                    "plan": "TEST_ONLY bounded implementation",
                    "tasks": ["Edit fixture example"],
                    "acceptance": ["value 2"],
                    "decisions_required": [],
                }
            else:
                target = (11 - 1) * 32000 + 12000
                source = (
                    "VALUE = "
                    + ("1" if role == "implement" else "2")
                    + "\n"
                    + "#source lin\n" * (target // 13)
                )
                (cwd / "example.py").write_text(source)
                output = {"summary": "TEST_ONLY fixture implementation", "known_risks": []}
            transcript.write_text(json.dumps(output))
            return {
                "output": output,
                "usage": {"fixture_provider_calls": 0},
                "runtime_identity": {"fixture": True},
            }

        def close(self):
            pass

    monkeypatch.setattr(
        sys.modules["harness.factory_runtime"], "FactoryAppServer", FixtureAppServer
    )

    class Runtime(LocalRuntime):
        simulation = True

        def profile_identity(self, profile):
            return {"fixture": True, "profile": profile}

        def agent(self, role, profile, cwd, payload, transcript, timeout, denied_roots):
            active_role[0] = role
            return super().agent(role, profile, cwd, payload, transcript, timeout, denied_roots)

        def project_validation(self, policy, spec, command, cwd, target, transcript, timeout):
            order.append(command[1])
            return validation.run(
                policy, spec, cwd, target, command, transcript, timeout, executor=docker
            )

        def prepare_direct_project_review(self, *a, **kw):
            prepared = super().prepare_direct_project_review(*a, **kw)
            prepared["plan"]["execution_mode"] = "OFFLINE_FIXTURE"
            digest = backend.sha256_bytes(canonical_json(prepared["plan"]))
            prepared["grant"].update(mode="OFFLINE_FIXTURE", plan_sha256=digest)
            prepared["task_binding"]["manifest_sha256"] = digest
            return prepared

        def prepare_project_review(self, spec, cwd, target, lane, timeout):
            contract = FootballPredictionContract(
                task_policy=self.task_budget_policy, deepseek_receipt=self.task_deepseek_receipt
            )
            argv, evidence = contract.review_arguments(spec, cwd, target, lane)
            return argv, evidence, {}

        def project_review(self, spec, cwd, target, lane, transcript, timeout, *, prepared=None):
            evidence = Path(prepared["evidence_dir"]) if isinstance(prepared, dict) else prepared[1]
            error = transcript.with_suffix(".stderr")
            error.write_text("")
            if lane == "second_reviewer":
                order.append("deepseek")
                argv = prepared["argv"]

                def value(name):
                    return argv[argv.index("--" + name) + 1]

                local = Namespace(
                    repo_root=Path(cwd),
                    base_sha=target["base"],
                    head_sha=target["head"],
                    mission_id=spec["mission_id"],
                    mission_scope_file=Path(cwd) / target["mission_scope_file"],
                    evidence_dir=evidence,
                    execution_id=value("execution-id"),
                    price_sha256=value("price-sha256"),
                    credential_sha256=value("credential-sha256"),
                    currency="CNY",
                    price_snapshot=args.price_snapshot,
                    price_raw=args.price_raw,
                )
                transport = DisputeTransport(local, finding=False)
                path = runner.run_review(
                    local,
                    transport=transport,
                    grant=json.loads(Path(prepared["grant_file"]).read_bytes()),
                    registry=registry,
                )
                assert len(transport.calls) == 33  # 29 POST + 4 GET。
                transcript.write_text(json.dumps({"review_receipt": str(path)}))
                code = 0
            else:
                current_codex[0] = codex_runner.build_parser().parse_args(
                    prepared[0][prepared[0].index("run") :]
                )
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    code = codex_runner.main(prepared[0][prepared[0].index("run") :])
                transcript.write_text(output.getvalue())
            result = {
                "exit_code": code,
                "stdout_path": str(transcript),
                "stderr_path": str(error),
                "evidence_dir": str(evidence),
                "fixture": True,
                "usage": {"fixture_provider_calls": 0},
            }
            if lane == "second_reviewer":
                result["direct_plan"] = prepared["plan"]
                result["task_end_balance_micro_cny"] = direct_consumer.task_balance_end(
                    path, repo_root=cwd, mission_id=spec["mission_id"]
                )
                result["project_evidence"] = [
                    {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                    for p in evidence.iterdir()
                    if p.is_file()
                ]
            return result

        def project_validate_review(self, spec, cwd, target, lane, result, **kw):
            return FootballPredictionContract(
                FixtureAdapter(), task_policy=self.task_budget_policy
            ).validate_review(spec, cwd, target, lane, result, **kw)

        def project_final_gate(self, spec, cwd, target, reviews, transcript, timeout, **kw):
            assert {r["lane"] for r in reviews} == {"reviewer", "second_reviewer"}
            assert all(r["status"] == "PASS" for r in reviews)
            # 原 project policy 检查 exact 双审身份与 qualification 绑定。
            deep = next(r for r in reviews if r["lane"] == "second_reviewer")
            fact = fixture_consume(
                deep["canonical_receipt"],
                repo_root=cwd,
                expected_base=target["base"],
                expected_head=target["head"],
                expected_mission_id=spec["mission_id"],
                expected_scope_hash=target["mission_scope_sha256"],
            )
            codex = next(r for r in reviews if r["lane"] == "reviewer")["canonical_receipt_data"]
            prov = codex["provenance"]["standalone"]
            codex_fact = ReviewEvidence(
                "codex-cli",
                True,
                codex["review_result"],
                target["base"],
                target["head"],
                fact.diff_sha256,
                spec["mission_id"],
                target["mission_scope_sha256"],
                codex["finding_counts_by_severity"],
                review_model=codex["model_provenance"]["review_model"],
                standalone_identity=prov["standalone_identity"],
                source_bindings_sha256=prov["source_bindings_sha256"],
                qualification_sha256=prov["qualification_sha256"],
            )
            policy = evaluate_review_policy(
                "CRITICAL",
                CandidateBinding(
                    target["base"],
                    target["head"],
                    fact.diff_sha256,
                    spec["mission_id"],
                    target["mission_scope_sha256"],
                    standalone_required=True,
                ),
                [fact, codex_fact],
            )
            assert policy.status == "SATISFIED", policy
            result = {
                "status": "PASS",
                "target": target,
                "fixture": True,
                "dual_policy": policy.to_dict(),
            }
            transcript.write_text(json.dumps(result))
            return result

    runtime = Runtime()
    factory = Factory(tmp_path / "factory-state", config, runtime)
    try:
        factory.submit(raw)
        result = factory.run(args.mission_id)
        assert result["DELIVERY_STATUS"] == "OFFLINE_CONTRACT_PASS", result
        assert app_reads == ["plan", "implement", "rework"]
        assert order.count("deepseek") == 2
        assert order.count("codex-provider") == 2
        assert "rework" in order
        assert order.index("deepseek") < order.index("codex-provider")
        assert result["TASK_BUDGET"]["committed_micro_cny"] == 2 * 4_220_718
        assert result["TASK_BUDGET"]["unresolved"] == 0
        # 真实 Factory 重新打开同一 state，缓存 evidence 不触发 Provider。
        previous = list(order)
        factory.close()
        factory = Factory(tmp_path / "factory-state", config, Runtime())
        resumed = factory.run(args.mission_id)
        assert resumed["DELIVERY_STATUS"] == "OFFLINE_CONTRACT_PASS"
        assert resumed["TASK_BUDGET"]["committed_micro_cny"] == 8_441_436
        assert order == previous
        # 第二 state 引用同一授权，不能再次运行 planning 或重新取得一份钱包。
        second = Factory(tmp_path / "second-state", config, Runtime())
        try:
            second.submit(raw)
            previous = list(order)
            blocked = second.run(args.mission_id)
            assert blocked["DELIVERY_STATUS"] == "BLOCKED_BY_TASK_BUDGET_POLICY"
            assert order == previous
            assert blocked["TASK_BUDGET"]["committed_micro_cny"] == 8_441_436
        finally:
            second.close()
        changed = deepcopy(config)
        changed["profiles"]["developer"]["model"] = "changed-fixture-model"
        third = Factory(tmp_path / "changed-model-state", changed, Runtime())
        try:
            third.submit(raw)
            assert third.run(args.mission_id)["DELIVERY_STATUS"] == "BLOCKED_BY_TASK_BUDGET_POLICY"
            assert order == previous
        finally:
            third.close()
        for lane in ("developer", "reviewer"):
            legacy = deepcopy(config)
            legacy["profiles"][lane]["transport"] = {"type": "cli_proxy"}
            with pytest.raises(ValueError, match="BLOCKED_BY_TASK_BUDGET_POLICY"):
                Factory(tmp_path / (lane + "-legacy-state"), legacy, Runtime())
        assert order == previous
    finally:
        factory.close()

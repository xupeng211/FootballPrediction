"""Direct runner 身份和原始请求证据校验；复用原 generic source/HEAD gate。

lifecycle: permanent
owner: engineering workflow governance
"""

# 安全拒绝分支保留在原事务/响应校验内，避免改变异常生命周期。
# ruff: noqa: TRY301, PLC0415
from __future__ import annotations

from argparse import Namespace
from datetime import UTC, datetime
from html.parser import HTMLParser
import json
import re

from scripts.devops.independent_review_backends import direct_deepseek as backend
from scripts.devops.independent_review_protocol import canonical_json, sha256_bytes


def validate_direct_provenance(receipt, context, registry_entry):  # noqa: C901, PLR0912, PLR0915
    """校验观察事实、原始输出、完整 source/HEAD 和持久发送记录。"""
    from scripts.devops.deepseek_review_chunks import aggregate
    from scripts.devops.direct_deepseek_independent_review import (
        build_plan,
        standalone_provenance,
        standalone_result,
    )
    from scripts.devops.independent_review_protocol import IndependentReviewProtocolError

    if receipt["review_backend"] != backend.BACKEND_ID:
        return
    try:
        if registry_entry["minimum_harness_version"] != backend.RUNNER_VERSION:
            raise ValueError
        evidence = context.direct_execution
        if (
            evidence is None
            or context.claude_deepseek_execution is not None
            or context.codex_execution is not None
            or context.chunked_claude_evidence
        ):
            raise ValueError
        manifest, bodies, chunks = build_plan(
            Namespace(
                repo_root=context.repo_root,
                base_sha=context.base_sha,
                head_sha=context.head_sha,
                mission_id=receipt["mission_id"],
                mission_scope_file=context.repo_root / context.mission_scope_path,
                execution_id=evidence.manifest.get("standalone", {}).get("execution_id"),
                price_sha256=evidence.manifest.get("standalone", {}).get("price_sha256"),
                credential_sha256=evidence.manifest.get("standalone", {}).get("credential_sha256"),
                currency=backend.currency(evidence.manifest),
                price_snapshot=evidence.manifest.get("standalone", {}).get("price_snapshot"),
            )
        )
        manifest["execution_mode"] = evidence.execution_mode
        planned = bodies
        if "dispute" in manifest.get("standalone", {}):
            from scripts.devops.direct_deepseek_dispute import replay

            bodies = replay(manifest, planned, evidence.raw_responses)["actual_bodies"]
        provenance = receipt["provenance"]
        if (
            evidence.manifest != manifest
            or evidence.bodies != tuple(bodies)
            or evidence.runtime_sha256 != backend.runtime_identity()
            or provenance
            != {
                "runner_runtime_sha256": evidence.runtime_sha256,
                "runner_version": backend.RUNNER_VERSION,
                "provider_endpoint": backend.ENDPOINT,
                "cost_policy_sha256": backend.POLICY_SHA,
                "review_plan_sha256": sha256_bytes(canonical_json(manifest)),
                "request_count": len(bodies),
                "execution_mode": evidence.execution_mode,
                "artifact_stem": f"direct-deepseek-{context.head_sha[:12]}-{receipt['review_run_id']}",
                **(
                    standalone_provenance(manifest, bodies, evidence.raw_responses)
                    if manifest.get("standalone") is not None
                    else {}
                ),
            }
            or evidence.execution_mode not in {"OFFLINE_FIXTURE", "DIRECT_HTTPS"}
            or receipt["resolved_model"] != backend.MODEL
            or receipt["review_harness"] != backend.HARNESS_ID
            or len(evidence.raw_responses) != len(bodies)
        ):
            raise ValueError
        prompt = canonical_json({"manifest": manifest, "requests": [json.loads(b) for b in bodies]})
        raw = canonical_json({"responses": [r.decode("utf-8") for r in evidence.raw_responses]})
        standalone = manifest.get("standalone") is not None
        if standalone:
            from scripts.ops.helpers.agent_workflow_contract import load_mission_scope_file

            scope = load_mission_scope_file(
                context.repo_root / context.mission_scope_path,
                repo_root=context.repo_root,
                expected_mission_id=receipt["mission_id"],
            )
            normalized = standalone_result(scope, manifest, bodies, evidence.raw_responses)
        else:
            normalized = aggregate(
                [
                    {"chunk_index": i, "result": backend.decode(r, bodies[i])}
                    for i, r in enumerate(evidence.raw_responses)
                ],
                chunks,
            )
        final = canonical_json(
            {
                "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
                "review_result": normalized["review_result"],
                "findings": normalized["findings"],
            }
        )
        if (
            prompt != context.prompt_bytes
            or raw != context.raw_output_bytes
            or final != context.final_result_bytes
        ):
            raise ValueError
        # consumer/runner 都需绑定 authority 中发送前冻结的 bytes 和成功原始 response。
        journal = backend.Journal()
        try:
            if standalone:
                admission = journal.db.execute(
                    "SELECT grant FROM admissions WHERE review_id=?", (manifest["review_identity"],)
                ).fetchone()
                if not admission:
                    raise ValueError
                grant = json.loads(admission[0])
                backend.validate_standalone_admission(
                    manifest, planned, grant, offline=evidence.execution_mode == "OFFLINE_FIXTURE"
                )
                if evidence.execution_mode == "DIRECT_HTTPS":
                    attempts = journal.db.execute(
                        "SELECT idx FROM http_attempts WHERE review_id=? ORDER BY idx",
                        (manifest["review_identity"],),
                    ).fetchall()
                    redirects = journal.db.execute(
                        "SELECT target FROM price_redirects WHERE review_id=?",
                        (manifest["review_identity"],),
                    ).fetchall()
                    snapshot = manifest["standalone"].get("price_snapshot")
                    expected_redirects = (
                        [(snapshot["source_url"],)]
                        if snapshot and snapshot["source_url"] != json.loads(bodies[0])["endpoint"]
                        else []
                    )
                    if (
                        redirects != expected_redirects
                        or len(attempts) + len(redirects) > grant["http_count"]
                    ):
                        raise ValueError("price physical HTTP evidence mismatch")
                    if attempts != [(i,) for i in range(len(bodies))]:
                        raise ValueError("missing durable physical HTTP evidence")
                approved = journal.db.execute(
                    "SELECT digest FROM grants WHERE id=?", (grant["id"],)
                ).fetchone()
                if not approved or approved[0] != sha256_bytes(canonical_json(grant)):
                    raise ValueError
            saved = journal.db.execute(
                "SELECT manifest FROM reviews WHERE id=?", (manifest["review_identity"],)
            ).fetchone()
            completed = journal.db.execute(
                "SELECT idx,raw FROM completed WHERE review_id=? ORDER BY idx",
                (manifest["review_identity"],),
            ).fetchall()
            requests = journal.db.execute(
                "SELECT idx,body,status FROM requests WHERE review_id=? ORDER BY idx",
                (manifest["review_identity"],),
            ).fetchall()
            if (
                not saved
                or saved[0] != canonical_json(manifest)
                or completed != list(enumerate(evidence.raw_responses))
                or requests != [(i, b, "UNKNOWN") for i, b in enumerate(planned)]
            ):
                raise ValueError
            if "dispute" in manifest.get("standalone", {}):
                materialized = journal.db.execute(
                    "SELECT idx,body FROM materialized WHERE review_id=? ORDER BY idx",
                    (manifest["review_identity"],),
                ).fetchall()
                if materialized != list(enumerate(bodies)):
                    raise ValueError("missing or changed materialized request bytes")
        finally:
            journal.close()
    except Exception:
        raise IndependentReviewProtocolError(
            "Direct runtime/request/source evidence invalid"
        ) from None


def consume_direct(
    path, *, repo_root, expected_base, expected_head, expected_mission_id, expected_scope_hash
):
    """正式 consumer 拒绝 offline fixture、未批准身份和失效绑定。"""
    from scripts.devops.deepseek_receipt_evidence import _assert_external_artifact, _load_json
    from scripts.devops.direct_deepseek_independent_review import DirectExecutionEvidence
    from scripts.devops.independent_review_receipt import (
        ReceiptEvidenceContext,
        load_backend_registry,
        validate_receipt,
    )
    from scripts.devops.review_policy import ReviewEvidence

    try:
        _assert_external_artifact(path, repo_root=repo_root, kind="receipt")
        receipt = _load_json(path)
        # Offline JSON 绝不能成为生产 approval，也不能通过 registry 激活抹掉 fixture 标记。
        if (
            receipt["provenance"]["execution_mode"] != "DIRECT_HTTPS"
            or (
                not backend.LIVE_EXECUTION_APPROVED
                and "standalone_identity" not in receipt["provenance"]
            )
            or receipt["mission_id"] != expected_mission_id
            or receipt["mission_scope_sha256"] != expected_scope_hash
        ):
            raise ValueError
        stem = f"direct-deepseek-{expected_head[:12]}-{receipt['review_run_id']}"
        artifacts = []
        for suffix in ("prompt", "raw", "final"):
            artifact = path.parent / f"{stem}-{suffix}.json"
            _assert_external_artifact(artifact, repo_root=repo_root, kind=suffix)
            artifacts.append(artifact.read_bytes())
        prompt, raw, final = artifacts
        p, r = json.loads(prompt), json.loads(raw)
        execution = DirectExecutionEvidence(
            p["manifest"],
            tuple(canonical_json(b) for b in p["requests"]),
            tuple(b.encode("utf-8") for b in r["responses"]),
            backend.runtime_identity(),
            "DIRECT_HTTPS",
        )
        context = ReceiptEvidenceContext(
            repo_root=repo_root,
            base_sha=expected_base,
            head_sha=expected_head,
            mission_scope_path=receipt["mission_scope_path"],
            prompt_bytes=prompt,
            raw_output_bytes=raw,
            final_result_bytes=final,
            direct_execution=execution,
        )
        registry = load_backend_registry(
            repo_root / "docs/agentic/independent_review_backends.json"
        )
        standalone = execution.manifest.get("standalone") is not None
        if standalone:
            if registry[backend.BACKEND_ID]["status"] != "reserved":
                raise ValueError
            registry[backend.BACKEND_ID]["status"] = "active"
        result = validate_receipt(
            receipt,
            registry=registry,
            evidence_context=context,
        )
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
            standalone_identity=receipt["provenance"].get("standalone_identity"),
            source_bindings_sha256=receipt["provenance"].get("source_bindings_sha256"),
            qualification_sha256=receipt["provenance"].get("qualification_sha256"),
        )
    except Exception:
        return ReviewEvidence(
            backend.BACKEND_ID,
            False,
            "NO_VERDICT",
            expected_base,
            expected_head,
            "",
            expected_mission_id,
            expected_scope_hash,
            {},
            infrastructure_failure=True,
        )


class _PriceRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, _attrs):
        if tag == "tr":
            self.row = []
        if tag in {"td", "th"} and self.row is not None:
            self.cell = []

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data + " ")


def _price_rates(rows, models, column, unit):
    rates, category = {}, None
    for row in rows:
        label = " ".join(row[: -len(models)]).upper()
        if any(
            k in label
            for k in ("CACHE MISS", "缓存未命中", "CACHE HIT", "缓存命中", "OUTPUT TOKENS", "输出")
        ) and not ("1M" in label or "百万" in label):
            raise ValueError
        if "CACHE MISS" in label or "缓存未命中" in label:
            category = "input_cache_miss"
        elif "CACHE HIT" in label or "缓存命中" in label:
            category = "input_cache_hit"
        elif "OUTPUT TOKENS" in label or "输出" in label:
            category = "output"
        tier = (
            "off_peak"
            if "OFF-PEAK" in label or "低谷" in label or "空闲时段" in label
            else "peak"
            if "PEAK" in label or "高峰" in label
            else None
        )
        if category and tier:
            value = row[-len(models) + column]
            prefix = r"(?:\$|USD)" if unit == "USD" else r"(?:¥|￥|CNY)"
            amount = r"([0-9]+(?:\.[0-9]{1,6})?)"
            match = re.fullmatch(prefix + r"\s*" + amount, value)
            if unit == "CNY" and not match:
                match = re.fullmatch(amount + "元", value)
            key = tier + ":" + category
            if not match or key in rates:
                raise ValueError
            rates[key] = backend.money_amount(match[1])
    if set(rates) != {
        t + ":" + k
        for t in ("peak", "off_peak")
        for k in ("input_cache_hit", "input_cache_miss", "output")
    }:
        raise ValueError
    return rates


def parse_price_snapshot(raw, *, source_url, unit, observed_at):
    """从完整官方表格读取模型、币种和六档价格；格式变化拒绝，不猜价格。"""
    try:
        if source_url not in {backend.price_url(unit) + suffix for suffix in ("", "/")}:
            raise ValueError
        parser = _PriceRows()
        parser.feed(raw.decode("utf-8"))
        (models,) = [r[1:] for r in parser.rows if r and r[0] in {"MODEL", "模型"}]
        (column,) = [
            i
            for i, v in enumerate(models)
            if re.fullmatch(re.escape(backend.MODEL) + r"(?: \(1\))?", v)
        ]
        if not any(
            len(r) == len(models) + 1
            and r[0] in {"MODEL VERSION", "模型版本"}
            and r[column + 1] == backend.POLICY["model_version"]
            for r in parser.rows
        ):
            raise ValueError
        rates = _price_rates(parser.rows, models, column, unit)
        stamp = datetime.fromisoformat(observed_at)
        if stamp.tzinfo is None:
            raise ValueError
        return {
            "source_url": source_url,
            "raw_sha256": sha256_bytes(raw),
            "currency": unit,
            "model": backend.MODEL,
            "model_version": backend.POLICY["model_version"],
            "observed_at": observed_at,
            "rates_micro_per_million": rates,
            "reservation_tier": "peak_cache_miss",
        }
    except Exception:
        raise backend.DirectError("OFFICIAL_PRICE_INCOMPLETE_OR_MISMATCH") from None


def validate_price_snapshot(snapshot, unit, digest):
    """强制完整价格、固定来源和24小时内的观察身份。"""
    try:
        if (
            set(snapshot)
            != {
                "source_url",
                "raw_sha256",
                "currency",
                "model",
                "model_version",
                "observed_at",
                "rates_micro_per_million",
                "reservation_tier",
            }
            or snapshot["source_url"]
            not in {backend.price_url(unit) + suffix for suffix in ("", "/")}
            or snapshot["currency"] != unit
            or snapshot["raw_sha256"] != digest
            or snapshot["model"] != backend.MODEL
            or snapshot["model_version"] != backend.POLICY["model_version"]
            or snapshot["reservation_tier"] != "peak_cache_miss"
        ):
            raise ValueError
        rates = snapshot["rates_micro_per_million"]
        if set(rates) != {
            t + ":" + k
            for t in ("peak", "off_peak")
            for k in ("input_cache_hit", "input_cache_miss", "output")
        } or any(type(v) is not int or not 0 <= v <= 10**12 for v in rates.values()):
            raise ValueError
        if any(
            rates["peak:" + k] < rates["off_peak:" + k]
            for k in ("input_cache_hit", "input_cache_miss", "output")
        ):
            raise ValueError
        stamp = datetime.fromisoformat(snapshot["observed_at"])
        age = (datetime.now(UTC) - stamp).total_seconds()
        if stamp.tzinfo is None or not 0 <= age <= backend.PRICE_MAX_AGE_SECONDS:
            raise ValueError
    except Exception:
        raise backend.DirectError("PRICE_SNAPSHOT_REQUIRED") from None


def validate_standalone_admission(manifest, bodies, grant, *, offline):  # noqa: C901
    """一次性显式有限风险授权；不是费用硬帽、Factory fallback 或 live 开关。"""
    unit = backend.currency(manifest)
    cap_key, balance_key, exposure_key = [
        backend.money_key(k, unit) for k in ("cap", "balance", "accepted_account_exposure")
    ]
    from scripts.devops import direct_deepseek_dispute as dispute

    integrated = dispute.enabled(manifest)
    fields = {
        "id",
        "review_identity",
        "policy_sha256",
        "runtime_sha256",
        cap_key,
        "contract",
        "mode",
        "plan_sha256",
        "execution_id",
        "expires_at",
        "currency",
        "accepted_residual_billing_risk",
        "standalone_authority_approved",
        "post_count",
        "http_count",
        "capacity_units",
        "price_sha256",
        "credential_sha256",
        balance_key,
        exposure_key,
        "codex_invocations",
    }
    if integrated:
        fields.add("dispute_authority_approved")
    try:
        if integrated:
            from scripts.devops.direct_deepseek_independent_review import rebuild_standalone_plan

            _, canonical_bodies, _ = rebuild_standalone_plan(manifest)
            if bodies != canonical_bodies or grant.get("dispute_authority_approved") is not True:
                raise ValueError
        snapshot = manifest["standalone"].get("price_snapshot")
        if snapshot is not None:
            validate_price_snapshot(snapshot, unit, manifest["standalone"]["price_sha256"])
        elif not offline or unit != "USD":
            raise ValueError
        if manifest["standalone"].get("price_redirect_limit", 0) != (1 if snapshot else 0):
            raise ValueError
        post_count = sum(json.loads(b).get("method") != "GET" for b in bodies)
        if (
            not isinstance(grant, dict)
            or set(grant) != fields
            or grant["contract"]
            != (
                "standalone-informed-risk/dispute-v2"
                if integrated
                else "standalone-informed-risk/v1"
            )
            or grant["mode"] != ("OFFLINE_FIXTURE" if offline else "PRODUCTION_AUTHORIZED")
            or grant["currency"] != unit
            or grant["accepted_residual_billing_risk"] is not True
            or grant["standalone_authority_approved"] is not True
            or grant["plan_sha256"] != sha256_bytes(canonical_json(manifest))
            or grant["execution_id"] != manifest["standalone"]["execution_id"]
            or not grant["execution_id"]
            or grant["price_sha256"] != manifest["standalone"]["price_sha256"]
            or grant["credential_sha256"] != manifest["standalone"]["credential_sha256"]
            or grant["codex_invocations"] != 1
            or grant["post_count"] != post_count
            or not backend.QUALIFICATION_COUNT
            <= post_count
            <= (dispute.MAX_POSTS if integrated else backend.MAX_STANDALONE_POSTS)
            or grant["http_count"]
            != len(bodies) + manifest["standalone"].get("price_redirect_limit", 0)
            or grant["http_count"]
            > (dispute.MAX_HTTP if integrated else backend.MAX_STANDALONE_HTTP)
            or grant["capacity_units"] != manifest["reserve_capacity_units"]
            or any(
                type(grant[k]) is not int or grant[k] < 0
                for k in (
                    cap_key,
                    balance_key,
                    exposure_key,
                    "capacity_units",
                    "post_count",
                    "http_count",
                    "codex_invocations",
                )
            )
            or not manifest[backend.money_key("reserve", unit)]
            <= grant[cap_key]
            <= grant[balance_key]
            <= grant[exposure_key]
            or datetime.fromisoformat(grant["expires_at"]).astimezone(UTC) <= datetime.now(UTC)
        ):
            raise ValueError
        if datetime.fromisoformat(grant["expires_at"]).tzinfo is None:
            raise ValueError
        for field in ("review_identity", "policy_sha256", "runtime_sha256"):
            if grant[field] != manifest[field]:
                raise ValueError
    except (KeyError, TypeError, ValueError, OverflowError):
        raise backend.DirectError("STANDALONE_AUTHORIZATION_DENIED") from None

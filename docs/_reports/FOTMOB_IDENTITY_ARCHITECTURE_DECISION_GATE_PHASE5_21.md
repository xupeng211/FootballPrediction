# FotMob Identity Architecture Decision Gate

> **Date:** 2026-05-27
> **Phase:** Phase 5.21 (Architecture Decision Gate)
> **Trigger:** L2V3BC No-Progress Stop Rule

## 1. Current Factual Summary

- **8 targets** remain suspended (from L2V3BA).
- **42 targets** are classified as `needs_new_evidence` (from L2V3BC).
- **0 targets** are clean, rejected, superseded, or eligible for re-acceptance.
- **raw_write_execution_ready** is `false`.
- The current source-controlled evidence is insufficient to reliably map the fixture identity (schedule) with the detailed pageProps identity.
- The `no-progress stop rule` was strictly triggered, halting normal ingestion phases.

## 2. Problem Diagnostic

This is **not** a standard "needs manual review" blocker. The fact that an entire batch of 42 active targets lacks sufficient identity evidence inside `pageProps` indicates a systemic **identity/source strategy blocker**. The canonical identity mapping strategy established previously cannot be satisfied by the actual JSON structures being served in this environment or under these proxy/bot-defense conditions.

## 3. Potential Root Causes

The absence of alignable identity markers may stem from:
- **FotMob direct API / pageProps request contract drift:** The structure of the hydration data (`__NEXT_DATA__`) or direct API payload may have changed.
- **Anti-bot / header / session discrepancy:** The defensive mechanisms might serve an incomplete or structurally different hydration payload to our fetcher compared to a real browser.
- **Route identity strategy flaw:** Relying purely on the `pageProps` extraction method might be fundamentally incompatible with the latest site architecture.
- **Schedule/detail identity mapping failure:** The expected keys mapping a schedule to its details may be missing or obfuscated.
- **Source-controlled evidence limits:** Existing artifacts cannot produce the data we need without new network requests.
- **Candidate generation flaw:** The current batch of 50 candidates might have been generated through an outdated discovery mechanism.

## 4. Decision Options Analysis

### Option 1: Abandon current 50-target batch
- **Benefit:** Instantly unblocks the pipeline state machine.
- **Risk:** Ignores the root cause. Future batches will likely fail the exact same way.
- **Cost:** Low immediate cost, high long-term cost.
- **Yields New Evidence:** No.
- **Safely Unblocks Write:** No.

### Option 2: Rebuild FotMob canonical identity pipeline
- **Benefit:** Solves the root mapping issue fundamentally.
- **Risk:** We don't yet know *how* to rebuild it because we lack diagnostic evidence of what changed.
- **Cost:** High development effort.
- **Yields New Evidence:** Requires it as a prerequisite.
- **Safely Unblocks Write:** Yes, eventually.

### Option 3: Redo source inventory strategy
- **Benefit:** Might find a better way to source candidates.
- **Risk:** The detail fetch step would still fail if the pageProps structure is broken.
- **Cost:** Medium.
- **Yields New Evidence:** No.
- **Safely Unblocks Write:** No.

### Option 4: Introduce second fixture identity source for cross-validation
- **Benefit:** Reduces reliance on a single, potentially obfuscated source.
- **Risk:** High complexity, adds another external dependency.
- **Cost:** Very high.
- **Yields New Evidence:** No (for the primary source).
- **Safely Unblocks Write:** Yes, but via a major architecture pivot.

### Option 5: Perform FotMob identity / anti-bot differential diagnosis spike
- **Benefit:** Directly tests the hypotheses. Allows us to compare direct API responses vs. headless browser routing vs. known-good historical payloads.
- **Risk:** Very low, provided it remains a no-write, bounded spike.
- **Cost:** Low to medium.
- **Yields New Evidence:** Yes.
- **Safely Unblocks Write:** No, but provides the data needed to design the fix.

### Option 6: Continue current pipeline without changes
- **Benefit:** None.
- **Risk:** Pipeline remains permanently blocked. Violates the no-progress stop rule.
- **Cost:** Infinite.
- **Yields New Evidence:** No.
- **Safely Unblocks Write:** No.

## 5. Recommended Decision

**Recommendation: Pause current raw write route and execute Option 5 (Differential Diagnosis Spike).**

We must **not** continue normal L2V3 review phases. The pipeline is fundamentally blocked by an data architecture issue. We should run a strictly bounded diagnostic spike to capture real network responses under different access strategies (direct API vs headless browser) and compare them against historical norms.
- `raw_write_execution_ready` remains `false`.
- The current 50-target write chain is paused.

## 6. Next Step

**Recommended Next Action:** Plan a bounded FotMob identity / anti-bot differential diagnosis spike.
(e.g., `Phase 5.21-ADG1: FotMob identity / anti-bot differential diagnosis spike planning`)

This spike must be strictly isolated: no DB writes, no raw data ingestion, and no re-acceptance. It exists purely to gather the intelligence needed to rebuild the identity pipeline.

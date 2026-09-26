---
name: forensic-resolution
description: Use when the user wants to diagnose an issue, implement a fix, or verify a broken feature. Triggers on "debug", "diagnose", "fix", "failing", "trace", or "error". Drives a relentless investigation, root-cause resolution, and test-driven verification.
---

# Forensic Resolution

You are executing a **Forensic** debugging and resolution session. Provide clear, direct, concise, and precise responses at all times. There are no rigid sequential steps; apply the following reference modules flexibly based on the current state of the investigation. Actively leverage **MCP tools** and invoke other relevant **skills** whenever appropriate and necessary to expand your investigative legwork.

## Diagnostic Phase (Flat Reference)
*   **Contextual Foundation:** Proactively locate and read `CONTEXT.md`, Architecture Decision Records (ADRs), and existing documentation. Base your understanding on these established single sources of truth before proceeding.
*   **Ground-Truth Mapping:** Deeply analyze the codebase and architecture (defaulting to modern and latest TypeScript Svelte v5+, etc., paradigms unless the environment dictates otherwise). **Reject all assumptions.** You must rely strictly on explicit evidence and analysis. If any architectural detail, logic path, or symptom is unclear or confusing, immediately halt and interrogate the user for clarification.
*   **State the Delta:** Isolate the exact variance between the working baseline and the failing state.
*   **Trace the Execution:** Map the data and logic path backward from the error emission directly to the point of origin.

## Resolution Phase (Flat Reference)
*   **Diagnosis Report & Approval:** Present a highly confident diagnosis report detailing the exact mechanism of failure. You MUST output a **Confidence Score (0% - 100%)**. If below 100%, state precisely what missing data prevents absolute certainty. **Do not write code for a fix until the user approves this report.**
*   **Surgical Fix:** Once the user approves the diagnosis, implement an optimal, accurate fix that eradicates the root cause. Absolutely **NO** mitigations, band-aids, or temporary workarounds are permitted and no regressions in existing or new code or logic. The fix must be structurally sound and permanent.

## Verification Phase (Flat Reference)
*   **Test-Driven Fortification:** Analyze the existing test suite. Proactively propose comprehensive test additions or updates to guarantee the new fix is covered from every angle. Encourage a Test-Driven Development (TDD) approach to make the architecture completely future-proof and production-ready.
*   **Reproduction Protocol:** Provide a precise, direct, and step-by-step sequence to test and reproduce the previously broken behavior. This allows the user to empirically confirm that the issue is fully eradicated and no trace of the problem remains.

## Completion Criterion
The skill is strictly incomplete until the root cause is proven, a non-mitigation fix is implemented, comprehensive TDD-aligned test coverage is proposed, and a strict reproduction protocol is provided to empirically verify the resolution.
---
name: code-audit
description: Enterprise-grade code and architecture audit. Identifies security vulnerabilities, runtime failure modes, performance bottlenecks, architectural anti-patterns, and logic flaws. Use when reviewing code, systems, or architecture for production readiness.
---

This skill guides the execution of an expert-level code and architecture review. It elevates applications from "merely functional" to "enterprise-grade" by anticipating failure modes, identifying hidden flaws, and enforcing industry-leading engineering practices tailored to the specific technology stack.

## Phase 0: Context Assessment

Before executing the audit, quickly determine the required scope. **Do not use a rigid questionnaire.**
1. **Determine Scope:** Identify if this is a Full Audit (entire repo), Focused Audit (single module), Change/PR Audit (git diff), or Spot Check (small snippet).
2. **Infer First:** Extract as much context as possible from the code itself (e.g., Python async handlers imply event loop and concurrency constraints; frontend components imply browser constraints; database adapters imply data integrity concerns).
3. **Ask Only If Blocked:** If critical or non-trivial context needed to accurately assess *this specific codebase* is missing (e.g., the threat model for a custom auth middleware, or the target execution environment for a complex script), ask 1-3 highly targeted, context-specific questions.
4. **Proceed Immediately if Unblocked:** If the code is self-contained or you can safely infer the context, do not block the user. Proceed straight to the audit specifying any assumptions or inferences made in the report.

*Always state all context assumptions at the top of every audit report.*

## Phase 1: Logic Intent Verification

Before auditing for vulnerabilities, you must meticulously comprehend what the code is *supposed* to do versus what it *actually* does based on end-to-end evidence.
1. **Deep Architectural Comprehension:** Before proceeding, you must first take a deep, accurate, and holistic understanding of the *whole* codebase and architecture provided. Trace the end-to-end core logic, authorization rules, and data pipelines to ensure no part of the application is ignored and no behavior is baselessly assumed.
2. **Proactive Clarification:** If a logic flow seems unconventional, highly permissive, or misaligned, **stop and proactively ask the user to confirm their intent.** (e.g., "In this file, the authorization logic permits any user to access this endpoint. Is this intended?")
3. **Flag Discrepancies:** If the user's intent contradicts the code's execution, immediately flag this discrepancy and clearly explain what the code is doing incorrectly.

## Phase 2: Multi-Pass Cognitive Sweep

To prevent missing subtle bugs due to "attention decay" or "first-finding bias," you must silently execute a multi-step internal sweep of the codebase before drafting the final report. Apply the **Enterprise Audit Guidelines** (detailed below) across distinct passes:
* **Sweep 1:** Focus exclusively on Security & Vulnerabilities.
* **Sweep 2:** Focus exclusively on Edge Cases, Logic Flaws & Behavior.
* **Sweep 3:** Focus exclusively on Architecture & Modern Patterns.
* **Sweep 4:** Focus exclusively on Robustness & Runtime Resilience.
* **Sweep 5:** Focus exclusively on Performance & Resource Optimization.
* **Sweep 6:** Focus exclusively on Empirical Optimization & Feature Evolution (auditing for concrete performance unlocks/upgrades, UX/DX responsiveness, state simplification, and architectural resiliency and robustness upgrades).

## Audit Thinking & Persona

Adopt the mindset of a seasoned Principal Engineer whose reputation depends on the accuracy of this report—not on finding the most issues, but on only raising issues that are real, evidenced by the code provided, and clearly explained. 
- **Start from Scratch (Zero-Bias)**: Never refer to or read past or existing audit reports. Start every new audit from scratch, completely free of bias or old audit context.
- A clean audit of solid code is a valuable outcome. **Do not invent issues to fill sections.**
- Do not nitpick stylistic choices unless they objectively impact maintainability. 
- Focus on structural integrity, logic gaps, and high-impact vulnerabilities. 
- **Modern Standards:** Default code remediations to modern, idiomatic standards native to the target stack:
  - *Python Projects:* Target modern Python 3.10+ idioms (PEP 585/604 type annotations e.g. `list[str]`, `X | Y`, Pydantic v2 / dataclasses, explicit context managers, non-blocking async, strict exception chaining).
  - *TypeScript/Frontend Projects:* Modern TypeScript and contemporary framework paradigms (e.g., Svelte 5 runes, React 19).
  - *General:* Align strictly with the repository's native conventions and official best practices without introducing alien abstractions or deprecated patterns.
- **Empirical Value Delivery:** Beyond finding defects, actively locate opportunities where the implementation can be made demonstrably superior. Prioritize upgrades that yield tangible outcomes: measurable latency cuts, bulletproof recovery patterns, reduced cognitive load, or responsive UX enhancements (e.g., optimistic updates, streaming, zero-layout-shift patterns), etc.

## Assumption Flagging

When you cannot see the full picture (e.g., a partial snippet, missing DB schema, missing middleware), you must not state assumptions as facts. Any finding that relies on an assumption about code not provided must be prefixed with `[ASSUMPTION: ...]` explaining what was assumed. 

> *Example:* "[ASSUMPTION: No middleware validation layer exists above this handler] — The endpoint at `/api/users` accepts an unsanitized `userId` directly."

## Severity Definitions

Use this strict rubric to classify all findings:
- **CRITICAL**: Direct path to RCE, authentication bypass, data breach, data loss with no recovery path, or immediate system unavailability.
- **HIGH**: Significant security risk, data integrity corruption, exploitable race condition, or service failure under realistic load.
- **MEDIUM**: Partial exposure, degraded functionality under edge inputs, missing defensive pattern that becomes dangerous with other changes.
- **LOW**: Inefficiency, maintainability debt, or best-practice deviation with no immediate exploitability.

## Enterprise Audit Guidelines

Evaluate the provided context against the following flexible factors, adapting your analysis to the specific domain and framework:

### 1. Edge Cases, Logic Flaws & Behavior
- **Unpredictable Inputs**: Audit for unhandled boundary conditions (e.g., missing null/None checks, out-of-bounds values, empty streams/collections).
- **Language-Specific Traps**: In Python, scrutinize mutable default arguments (`def f(x=[])`), late-binding closures in loops, truthiness pitfalls (`if val:` vs `if val is not None:` when 0 or empty string is valid), and unhandled `NoneType` / type-narrowing gaps.
- **Real-World Interaction**: Identify vulnerabilities to erratic human/machine interaction (e.g., duplicate submissions, out-of-order execution, interrupted workflows).
- **Concurrency & State**: Identify asynchronous or multithreaded operations that lack proper locking, atomic updates, or transactional integrity (e.g., GIL misconceptions where shared mutable state is falsely assumed thread-safe).

### 2. Security & Vulnerabilities
- **Zero-Trust Validation**: Ensure all inputs across all boundaries are strictly validated and parsed (e.g., Pydantic schemas, validation layers).
- **Injection & Serialization Exploits**: Check for context-specific vulnerabilities: SQL/NoSQL injection (e.g., f-strings or string concatenation in queries vs parameterized queries), command/code injection (`subprocess` with `shell=True`, `eval`, `exec`), insecure deserialization (`pickle.loads`, `yaml.load` without `SafeLoader`, untrusted `joblib.load`), and path traversal (e.g., `os.path.join` with absolute component overrides vs `pathlib.Path.resolve()`).
- **Identity, Access & Cryptography**: Verify proper authorization scopes, IDOR, secret exposure in logs/exceptions, and insecure randomness (e.g., `random` instead of `secrets` for security-sensitive tokens).

### 3. Architecture & Modern Patterns
- **Anti-Patterns**: Call out tight coupling, god objects, circular imports, domain-logic leakage, or untyped dictionary bags passed across layers instead of strongly-typed models (`dataclasses`, Pydantic models).
- **Optimal Paradigms**: Enforce strict architectural standards relevant to the stack (e.g., PEP 585/604 type annotations, dependency injection, pure separation of I/O from core business logic).

### 4. Robustness & Runtime Resilience
- **Deterministic Resource Management**: Ensure guaranteed cleanup of files, database connections/sessions, sockets, and thread/process pools using context managers (`with`, `async with`).
- **Environmental Failures & Error Handling**: How does it handle third-party service outages, filesystem locks, or sudden resource exhaustion? Audit for swallowed exceptions (`except:` or `except Exception: pass`), missing exception chaining (`raise ... from err`), and unhandled panics/crashes.
- **Resilient Integrations**: Network/I/O calls must utilize defensive patterns (e.g., timeouts, retries with jitter, circuit breakers).
- **Async Runtime Resilience**: In async frameworks (`asyncio`, FastAPI), ensure background tasks maintain strong references to prevent premature garbage collection, coroutines are never unawaited, and `asyncio.CancelledError` is cleanly handled.

### 5. Performance & Resource Optimization
- **Algorithmic & Collection Efficiency**: Identify accidental exponential/quadratic loops or suboptimal data structures (e.g., linear lookups in `list` instead of O(1) `set`/`dict`, `list.pop(0)` instead of `collections.deque`).
- **Event Loop & Concurrency Health**: In Python async runtimes, flag blocking synchronous calls (e.g., `time.sleep`, synchronous I/O, heavy CPU/ML inference) inside coroutines that freeze the event loop without `asyncio.to_thread` or worker pools.
- **Resource & Memory Footprint**: Flag memory bloat (e.g., loading whole files or datasets into memory instead of generator pipelines/chunked streams, unnecessary dataframe copies, missing `__slots__` on high-throughput objects).
- **I/O Optimization**: Flag N+1 query problems, missing indexes, unbatched API/DB calls, and lack of connection pooling.

### 6. Empirical Refinements & Feature Evolution
- **Performance & Throughput:** Pinpoint concrete wins (e.g., generator pipelines, query batching, streaming responses, derived memoization, payload compression, vectorized operations over pure Python loops).
- **UX & Perceived Responsiveness:** Identify where synchronous blocking, naive loaders, or lack of optimistic states degrade user interaction.
- **Resilience Multipliers:** Suggest patterns that upgrade basic error handling to self-healing behavior (e.g., exponential backoff with jitter, stale-while-revalidate caching, circuit breaking, atomic fallbacks).
- **Feature Depth & Completeness:** Identify missing primitives that turn naive features into production-grade solutions (e.g., cursor pagination, idempotency keys, race-condition-free state machines, audit logs).

## Output Format

You MUST output your final review strictly using the following Markdown template.

```markdown
# Enterprise Code Audit Report

## Context & Assumptions
* **Audit Confidence Score:** [e.g., 90% - High (Full context provided) | 50% - Moderate (Missing routing layers and DB schemas. See Assumptions)]
* **Inferred Context:** [Summary of inferred execution environment, runtime, and architecture]
* **Assumptions Made:**
  - [List any overarching assumptions made about the broader system]

## Strengths Observed
*(Acknowledge any solid patterns, well-handled edge cases, or strong architectural choices present in the code, only IF ANY, if not you can leave this section empty or acknowledge that no significant strengths were observed).*
* **[Strength 1]**: [Brief explanation of why this is good]
* **[Strength 2]**: [Brief explanation]

## Audit Findings

### [Finding Title e.g., Unsanitized Input in User Update Handler]
* **Severity**: [CRITICAL | HIGH | MEDIUM | LOW]
* **Category**: [Security | Performance | Architecture | Edge Case | Robustness | Intent Discrepancy]
* **Impact**: [Clear, concise explanation of what happens if this fails or is exploited in the real world].
* **Observation**: [Describe the flaw. Use `[ASSUMPTION: ...]` here if the finding relies on unseen context].
* **Remediation**:
  [Provide concrete explanation and production-ready code snippet to resolve the issue]

*(Repeat Finding block for all valid issues discovered. Order by Severity: CRITICAL first, LOW last).*

## Opportunities & Empirical Upgrades
*(Tangible enhancements that measurably improve performance, UX, resilience, or feature capability. Do not list cosmetic tweaks—focus on verifiable upside).*

### [Upgrade Title e.g., Replace Sequential Waterfalls with Parallel Prefetching]
* **Target Area**: [Performance | UX Responsiveness | Robustness | Feature Depth]
* **Empirical Metric/Outcome**: [e.g., Eliminates 300ms blocking I/O; prevents UI flash; ensures zero-loss offline sync]
* **Current Limitation**: [Explain the bottleneck, fragility, or missed potential in the current implementation]
* **The Refinement**: [Describe the upgraded logic, pattern, or mechanism]
* **Upgraded Implementation**:
  [Provide clean, production-ready code snippet demonstrating the refined approach]

*(Repeat block for all high-leverage upgrade opportunities discovered).*

```

## Post-Audit Action Required (if not explicitly told or stated)
**Export Instruction:** Save this complete report to the `audit-reports/` directory within the project repository to maintain a historical log of security and architectural reviews. 
* **Suggested Filename:** `audit-reports/YYYY-MM-DD-[target-module-or-feature]-audit.md`
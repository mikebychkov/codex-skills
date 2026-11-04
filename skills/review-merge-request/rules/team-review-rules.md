# Team MR Review Rules

These rules are derived from 14 earlier and 5 additional annotated GitLab MR screenshots. They express team expectations, not universal defects. Apply them to **changed code**. Cite a concrete path and line range. If an architectural/style preference does not establish a runtime defect, treat it as **P3 / non-blocking**. Where the intent is uncertain, raise a question rather than fabricate a finding.

## JAVA-STYLE-001 — Do not introduce static imports

- **Applies to:** New/modified Java files, including tests.
- **Check:** Avoid `import static`; qualify static members explicitly (e.g. `Assertions.assertThat(...)`).
- **Exceptions:** Do not flag untouched legacy code. This is a team convention, not a Java bug; flag a conflict with an explicit repository-wide convention rather than asserting a defect.
- **Default priority:** P3.
- **Fix:** Use qualified class references; remove newly introduced static imports.

## SPRING-SEC-001 — Verify alignment of Swagger/OpenAPI and Spring Security

- **Applies to:** Changes in `SecurityFilterChain`, JWT/Bearer authentication, endpoint whitelist, `SwaggerConfig`, and OpenAPI security declarations.
- **Check:** Verify actual Spring Security access requirements agree with intended endpoint authorization and OpenAPI documentation. Compare URL patterns, HTTP methods, matcher ordering, multiple chains, and authentication requirements.
- **Exceptions:** OpenAPI `SecurityScheme` is documentation, *not* authorization enforcement. `permitAll` endpoints need not match OpenAPI definitions one-to-one; documentation endpoints can be public while APIs are protected. Do not assert security bypass without proving it from actual security config.
- **Default priority:** P2; P1 only for a concrete exploitable authentication/authorization bypass.
- **Fix:** Correct security matcher/policy where necessary and document endpoint requirements accurately.

## JAVA-ARCH-001 — Reuse shared ApplicationException hierarchy

- **Applies to:** Newly introduced custom application exceptions.
- **Check:** If the project/common library supplies a standard `ApplicationException` base for application-domain errors, do not introduce a competing hierarchy extending `RuntimeException` directly.
- **Exceptions:** First verify shared type availability, dependency direction, constructors, cause handling, and error-code/status semantics. Library use is not mandatory where the type is unsuitable or would introduce a dependency cycle.
- **Default priority:** P3; P2 if the change demonstrably breaks shared exception mapping.
- **Fix:** Extend/reuse the shared base with existing error semantics preserved.

## JAVA-ARCH-002 — Do not mix operational domain responsibilities into configuration classes

- **Applies to:** `AppProps` / `@ConfigurationProperties` classes and nested types (e.g. `AppProps.RateLimit`).
- **Check:** Identify operational/domain models or behavior incorrectly owned by configuration property classes; avoid coupling runtime objects to configuration binding internals.
- **Exceptions:** Nested immutable property DTOs are normal and do *not* violate single responsibility merely by being nested. Report only concrete problematic reuse, mutable runtime state, lifecycle confusion, or wrong dependency direction.
- **Default priority:** P3.
- **Fix:** Extract a separate domain/configuration-derived model only where responsibilities genuinely diverge.

## SQL-STYLE-001 — Prefer half-open time ranges

- **Applies to:** New/changed `from`/`to` SQL filters for adjacent time windows.
- **Check:** Prefer `created_at >= :from AND created_at < :to` over inclusive `<= :to`.
- **Exceptions:** This is a range *contract*, not an unconditional rule. Inclusive upper bounds can be correct for explicitly closed intervals. Validate precision, nullability, time zone, and calling API semantics first.
- **Default priority:** P3; P2 if a real duplicate/missed boundary record is demonstrated.
- **Fix:** Make API and SQL consistently implement `[from, to)` where appropriate.

## SQL-PERF-001 — Review correlated latest-state subqueries for large result sets

- **Applies to:** Search/page queries using correlated per-row status lookups, especially `ORDER BY created_at DESC LIMIT 1` against history tables.
- **Check:** Review scale, selectivity, indexes, plan, and whether `JOIN LATERAL`, `DISTINCT ON`, window functions, or materialized/current state are more efficient.
- **Exceptions:** A correlated subquery is **not inherently N+1 at the application level**, and PostgreSQL can execute it efficiently with suitable indexes. Do not flag without a plausible expensive execution path; preserve latest-status tie-breaking/filter semantics in rewrites.
- **Default priority:** P3; P2 only with concrete high-cardinality/plan evidence.
- **Fix:** Use an appropriate plan/index or query rewrite supported by measurements where available; never require access to production DB.

## JAVA-TIME-001 — Choose Instant vs LocalDateTime according to domain semantics

- **Applies to:** Repository method parameters, entity mappings, services, and SQL timestamp filters.
- **Check:** Ensure temporal types align with database `timestamp`/`timestamptz`, application UTC/local-time convention, and conversion boundaries.
- **Exceptions:** Do **not** blindly require `Instant -> LocalDateTime`. `Instant` correctly represents an absolute point in time; `LocalDateTime` is zone-less. Only report actual type/offset/DB mismatch.
- **Default priority:** P3; P2 if an actual timestamp filter/offset bug is shown.
- **Fix:** Choose coherent types and explicit zone conversion where necessary.

## SQL-STYLE-002 — Format SQL even when the query is short

- **Applies to:** Newly introduced/changed native SQL or JPQL in `@Query`/text blocks.
- **Check:** Keep a consistent readable layout: clauses on separate lines, indentation, predicates and joins easy to inspect.
- **Exceptions:** A one-line trivial query is not a functional defect. Do not demand formatting-only changes in untouched code or contradict automated project formatting conventions.
- **Default priority:** P3.
- **Fix:** Reformat for readability without changing query semantics.

## JPA-STYLE-001 — Prefer native queries where this team convention applies

- **Applies to:** New/changed custom Spring Data JPA queries.
- **Check:** Follow the team's preference for native SQL rather than mixing JPQL/native queries in the same repository.
- **Exceptions:** JPQL is a valid, sometimes preferable abstraction, especially for entity joins/fetch behavior and portability. `JOIN FETCH` cannot be mechanically changed into native SQL. Do not call correct JPQL broken merely because it is non-native. This remains a style decision unless contract or performance impact is shown.
- **Default priority:** P3.
- **Fix:** If native SQL is chosen, preserve entity mapping, projections, count queries and fetch semantics.

## JPA-ARCH-001 — Reduce repetition in complex optional-filter queries

- **Applies to:** New/changed `findAll`/search methods with repeated `(:param IS NULL OR ...)` predicates, duplicated main/count SQL, or long parameter lists.
- **Check:** Consider query specifications, criteria/prototype pattern, reusable filter DTO, Querydsl, or a small dedicated repository query builder when it clearly reduces repetition.
- **Exceptions:** Do not force abstraction for one simple query, or make unsafe dynamic SQL. `findAll` does not intrinsically require prototype. Native SQL/complex projections may be clearer as explicit queries.
- **Default priority:** P3.
- **Fix:** Centralize reusable filter construction only when it simplifies the actual codebase.

## JAVA-DOMAIN-001 — Centralize terminal/nonterminal OperationStatus classification

- **Applies to:** New hardcoded lists/sets of statuses in schedulers/services.
- **Check:** Prefer one authoritative `OperationStatus.isFinal()` or immutable predefined collection of final/nonfinal states over independently maintained per-job lists.
- **Exceptions:** Enum method vs set are alternatives, not both mandatory. If finality is context/provider dependent, a domain policy service may be more correct. No requirement to recreate a list per call.
- **Default priority:** P3; P2 for demonstrated inconsistent classification.
- **Fix:** Move stable status classification to the responsible domain owner.

## SPRING-CONFIG-001 — Validate nested configuration before dereference

- **Applies to:** New/changed chains such as `appProps.getScheduler().getOperationCountMetricJob().getWindowSeconds()`.
- **Check:** Ensure intermediate nested configuration is guaranteed non-null or guarded before use.
- **Exceptions:** Validated `@ConfigurationProperties` with `@NotNull`, constructor binding, defaults, or startup assertions can already guarantee non-null. Do not demand defensive `null` checks at every call site.
- **Default priority:** P2 for a concrete reachable NPE; otherwise P3.
- **Fix:** Prefer startup validation/defaults of required config properties.

## SCHED-001 — Avoid overlapping scheduled jobs and unbounded work per run

- **Applies to:** Scheduled jobs that page/process all eligible DB records on every invocation.
- **Check:** Determine whether job duration exceeds schedule interval; whether there are multiple instances or async triggers; whether batches are bounded; and whether offset paging remains correct if processed rows change eligibility.
- **Exceptions:** `fixedDelay` commonly waits for the prior invocation on the same scheduler. Cron alone does not prove overlapping execution on one instance; replicas can still overlap. Do not assert overlap without scheduling/deployment evidence.
- **Default priority:** P2 for demonstrated overlapping or starvation risk, else P3.
- **Fix:** Use an appropriate fixed-delay/coordination strategy or bounded batches and stable pagination; consider distributed lock if replicas need exclusivity.

## JAVA-ARCH-003 — Place cross-layer value objects outside the service package

- **Applies to:** New data-only records/classes like `TransactionContext` declared in `service` packages.
- **Check:** Consider `domain`, `model`, `dto`, or a context-specific package consistent with ownership and reuse.
- **Exceptions:** A type private to a service's implementation can reasonably reside in its package; `record` does not imply DTO. This is a packaging convention, not a defect by itself.
- **Default priority:** P3.
- **Fix:** Relocate only when ownership/layering become clearer.

## JAVA-ERROR-001 — Establish the correct error boundary around message publishing

- **Applies to:** New/changed Kafka or other message publish paths containing data preparation, mapping, serialization, and `send`.
- **Check:** Determine which preparation/publish failures should be handled by a common retry/reporting boundary; verify errors are not silently lost.
- **Exceptions:** Do not wrap everything in `try/catch` by default. Preparation errors may need different semantics from transport errors. Asynchronous send failures occur via future/callback and may not be caught synchronously.
- **Default priority:** P2 for a concrete missed failure path, else P3.
- **Fix:** Define recovery policy and catch/observe failures at the appropriate boundary.

## JAVA-ERROR-002 — Narrow catch scope to the failures it can handle

- **Applies to:** Broad `try/catch` around JSON serialization, exchange-rate calculation, request building, or other mixed business logic.
- **Check:** Flag catches that collapse unrelated exceptions into one recovery path or mask business failures.
- **Exceptions:** An integration boundary may intentionally catch broadly if logging/classification/rethrow semantics are sound. Do not make stylistic changes without a clear behavioral advantage.
- **Default priority:** P3; P2 when an actual failure is swallowed/misclassified.
- **Fix:** Keep JSON-processing error handling appropriately scoped; distinguish recovery paths when their semantics differ.

## JAVA-API-001 — Verify argument-to-parameter mapping in repository queries

- **Applies to:** Changed repository method signatures, especially `@Query` methods with multiple parameters of the same Java type and named SQL parameters.
- **Check:** Match each Java parameter name, `@Param("...")` name, placeholder in SQL, and actual business meaning. Detect swapped bounds such as `@Param("endAmount") Long startAmount` and `@Param("startAmount") Long endAmount`. Verify the overlap condition itself matches the intended inclusive/exclusive range semantics.
- **Exceptions:** Different Java and SQL names are legal when intentionally mapped; a mismatch is a finding only when the actual value-to-placeholder binding contradicts the intended meaning. Read callers and SQL if necessary. Do not infer the error from ordering alone because named parameters do not depend on order.
- **Default priority:** P2 for demonstrated wrong query behavior; P3 for confusing naming with correct binding.
- **Fix:** Align `@Param` values, Java parameter names and caller arguments, and test both overlapping and non-overlapping ranges, including equality at boundaries.

## JAVA-TIME-002 — Use the business-defined timezone for fixed-local schedules

- **Applies to:** Changed scheduled jobs and schedule calculations using `ZoneId`, configured timezones, `now()`, or clock conversions.
- **Check:** When the business contract explicitly defines a schedule in Tashkent local time, ensure computations use that fixed zone (`Asia/Tashkent`) or an equivalent approved centralized clock/zone configuration; do not derive the zone from the server environment or an unrelated corridor/provider when that would shift the intended schedule.
- **Exceptions:** A dynamically resolved zone is appropriate for per-region or per-provider schedules. UTC storage of timestamps is not a conflict with execution in a fixed local timezone. `Asia/Tashkent` is **not** a universal timezone rule for all projects or schedulers. Verify the schedule's actual contract before reporting.
- **Default priority:** P3 for needless complexity; P2 if a real scheduling-time bug or environment-dependent behavior is demonstrated.
- **Fix:** Use a clear business clock/zone constant or injected `Clock` where the schedule truly has a fixed time basis; keep tests independent of the host timezone.

## JAVA-VALIDATION-001 — Extract repeated or substantial business-condition checks into validation methods

- **Applies to:** New or significantly modified service workflows containing repeated inline `if` checks for state, expiration, sender/receiver presence, or other business preconditions.
- **Check:** Where validation is reused or obscures the main business flow, express the precondition through a clearly named method such as `validateSenderNotChecked(...)` / `validateReceiverChecked(...)`, preserving the expected exception type and message.
- **Exceptions:** Do not mechanically extract every short `if`: a single obvious local guard may be clearer inline. Only propose extraction when it improves reuse, readability, consistency, or isolation of the business invariant. Do not hide side effects in methods misleadingly named `validate...`.
- **Default priority:** P3; P2 only if duplicated validation already results in demonstrably inconsistent behavior.
- **Fix:** Encapsulate the condition and failure handling in a dedicated validation method or shared validator when warranted; preserve the order of checks and the externally visible error contract.

## JAVA-ERROR-003 — Preserve specific context in business-conflict error responses

- **Applies to:** Changed branches throwing `ConflictException`, `InvalidStatusException`, or other business exceptions for distinct domain conflicts.
- **Check:** Ensure the externally visible error response or stable error code distinguishes materially different conflicts (e.g. sender already verified vs receiver not yet verified). Replacing a specific exception message with `log.error(...)` and a generic exception must not remove information required by callers or operators.
- **Exceptions:** Do not expose secrets, account identifiers, internal details or sensitive values in public responses. A generic exception class is acceptable when a structured, stable response code or safe message already supplies the concrete reason. Logging details alone do not necessarily satisfy the API's error contract; conversely not every internal detail belongs in the API response.
- **Default priority:** P2 if the change breaks the expected API error semantics; otherwise P3 for improving diagnostics.
- **Fix:** Use distinct safe messages or structured domain error codes, while retaining consistent HTTP semantics and logging without duplicate sensitive data.

---

## Reviewer instructions

1. Report only new/changed code issues, with a stable rule ID and exact evidence.
2. Prioritize correctness, data integrity, concurrency, and security ahead of style.
3. Use P0/P1 only with concrete evidence under `references/severity.md`.
4. Do not automatically apply fixes; the target repository remains source-read-only.
5. Avoid duplicate findings for the same root cause.
6. Do not present a team preference as a universal Java/Spring/PostgreSQL requirement.

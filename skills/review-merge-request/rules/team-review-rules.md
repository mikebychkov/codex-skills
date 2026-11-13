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

## JPA-STYLE-001 — Require native SQL for application-defined database queries

- **Applies to:** New or changed application-defined database queries, including Spring Data JPA `@Query`, named queries, derived query methods, and queries built through EntityManager, Criteria or Specifications.
- **Check:** Require native SQL. For Spring Data JPA `@Query`, require `nativeQuery = true` (the actual annotation attribute, not `native = true`). Report JPQL/HQL, `@Query` with omitted/false `nativeQuery`, and newly introduced or changed derived/Criteria/Specification queries as violations of this mandatory team convention. Native JDBC SQL and equivalent native JPA query APIs satisfy the requirement without an annotation flag.
- **Exceptions:** Do not flag untouched queries or inherited framework CRUD methods solely because their implementation has no configurable `nativeQuery` flag. Report this as a team-policy violation, not a claim that JPQL is inherently invalid or slower. Do not mechanically translate `JOIN FETCH` or other ORM-specific behavior without preserving its semantics.
- **Default priority:** P2.
- **Fix:** Express the application-defined query as native SQL using `@Query(nativeQuery = true)` or an equivalent native API. Preserve parameter binding, entity mapping, projections, pagination/count queries and fetch behavior.

## JPA-ENTITY-001 — Keep entities immutable and define equality and hashing

- **Applies to:** New or changed JPA `@Entity` classes and application code or MapStruct mappings that update entity instances.
- **Check:** Entity state must not be mutated in place by application code. Prohibit handwritten and Lombok-generated entity setters, including setters introduced by `@Setter` or `@Data`; state changes must produce a new instance through a builder or copying, such as `toBuilder()` or a copy constructor. Builder setters are permitted because they construct a new entity rather than mutate an existing entity. Flag other in-place mutation methods, direct field writes and exposed mutable state that bypass this requirement. Prohibit MapStruct `@MappingTarget` parameters whose target type is an entity, including inherited entity types; use mappings that return a new entity instead. Every entity must have both `equals(Object)` and `hashCode()` implementations; Lombok generation, including `@EqualsAndHashCode`, is acceptable, but an annotation generating setters still violates the immutability requirement. Verify inherited implementations and Lombok configuration rather than requiring handwritten overrides in every class.
- **Exceptions:** Do not flag untouched code or non-entity DTOs and builders. JPA-required constructors, provider field hydration and framework-managed generated identifiers do not by themselves violate application-level immutability; do not require final classes or final persistent fields that conflict with the actual JPA provider contract. Inherited equality/hash implementations satisfy the requirement only when they define entity equality, rather than merely inheriting Object identity. If the relevant superclass or generated implementation cannot be established, use UNVERIFIED. This is a mandatory team convention, not a claim that JPA universally prohibits mutable entities.
- **Default priority:** P3 — mandatory entity immutability and equality convention; report concrete persistence or equality defects separately at the severity justified by their impact.
- **Fix:** Remove entity setters and in-place update mappings; construct a new entity using a builder or copy operation while preserving identity, version and required persistent state. Define consistent `equals` and `hashCode` manually or through suitable Lombok configuration, accounting for generated identifiers, transient instances, proxies and mutable associations; do not mechanically include every field or association.

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

## JAVA-ERROR-004 — Keep try blocks small, exception-focused and free of nested try/catch

- **Applies to:** New or changed Java `try/catch` blocks, including try-with-resources with catch handlers.
- **Check:** Limit the protected `try` body to at most four executable logical lines, normally three or fewer. Ignore blank lines, comments and standalone braces; count a wrapped invocation or expression as one logical line, but count separate statements on the same physical line separately. Include only operations that can throw the exceptions the associated catch handlers are intended to handle. Move unrelated logging, pure calculations, assignments of already computed values and other non-throwing preparation or post-processing outside the try boundary. Nested `try/catch` blocks inside the enclosing try body, catch handlers or finally block are prohibited. Cite the oversized body, unrelated statements or nested handler explicitly; do not report a generic preference without identifying the violated condition.
- **Exceptions:** Do not flag untouched blocks. Assess relevant checked and unchecked exceptions from the actual operation and handling contract; absence of a declared checked exception does not prove that an operation cannot throw. Resource acquisition/closing handled by try-with-resources can justify the boundary. If the exception behavior cannot be established from available source or contracts, use UNVERIFIED for that aspect. This mandatory team rule is stricter than JAVA-ERROR-002's general broad-boundary allowance; avoid duplicate findings for the same block.
- **Default priority:** P2 — mandatory exception-handling structure convention.
- **Fix:** Narrow the try body to the relevant throwing operations and move other work outside it without changing evaluation order, side effects, resource lifetimes or recovery semantics. Replace nested try/catch with separate, clearly named operations or sequential handling boundaries where appropriate; preserve exception types, causes and fallback behavior rather than mechanically flattening handlers or hiding a large mixed-purpose block in a helper.

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

## JAVA-VALIDATION-002 — Consider extracting exception-throwing if blocks into private validation methods

- **Applies to:** New or changed Java `if` blocks containing a `throw` statement, including a single condition that is not repeated elsewhere.
- **Check:** Mark the block as a candidate for extraction into an internal private validation method with a descriptive name such as `validateAmountRange(...)`. Present this as a non-blocking maintainability recommendation, not a functional defect or mandatory refactoring.
- **Exceptions:** Do not flag untouched code or checks already encapsulated in a private validation method. A short, obvious guard may remain inline when extraction would reduce clarity. Do not duplicate a recommendation already reported under JAVA-VALIDATION-001, or describe side-effectful processing as pure validation.
- **Default priority:** P3 — advisory, non-critical maintainability recommendation.
- **Fix:** Consider moving the condition and exception into a private `validate...` method within the same class, preserving the exception type, message, evaluation order and externally visible behavior.

## JAVA-ERROR-003 — Preserve specific context in business-conflict error responses

- **Applies to:** Changed branches throwing `ConflictException`, `InvalidStatusException`, or other business exceptions for distinct domain conflicts.
- **Check:** Ensure the externally visible error response or stable error code distinguishes materially different conflicts (e.g. sender already verified vs receiver not yet verified). Replacing a specific exception message with `log.error(...)` and a generic exception must not remove information required by callers or operators.
- **Check:** When the failure context contains a relevant `id`, `number`, or value being validated, include that value with a descriptive label in the exception message and in any corresponding error log. A detailed reason without the available identifying or validated value is insufficient. For example, prefer `Invalid status for transfer id=123: status=PENDING` to `Invalid status`. Existing structured log fields satisfy the logging requirement when they carry the same context; this rule does not require adding a separate log statement.
- **Exceptions:** Do not expose secrets, account identifiers, internal details or sensitive values in public responses. A generic exception class is acceptable when a structured, stable response code or safe message already supplies the concrete reason. Logging details alone do not necessarily satisfy the API's error contract; conversely not every internal detail belongs in the API response.
- **Exceptions:** Include contextual values only where disclosure is permitted. Mask or redact sensitive values as required by the project's policy, and keep internal diagnostic context out of public responses when necessary. Do not demand values unavailable at the failure site or unrelated to the failure.
- **Default priority:** P2 if the change breaks the expected API error semantics; otherwise P3 for improving diagnostics.
- **Fix:** Use distinct safe messages or structured domain error codes, while retaining consistent HTTP semantics and logging without duplicate sensitive data.

## JAVA-LOG-001 — Include relevant entity identifiers and values in logs

- **Applies to:** New or changed log statements describing entity processing, validation, or state changes, at any log level.
- **Check:** Logs must contain concrete context for the situation, not only a static textual message. Include the relevant available identifiers (`id`, `number`, external/internal IDs) and values being processed or validated, with descriptive field names. When processing an `OperationEntity`, include its available operation identifiers, such as `operation.getId()`, `operation.getExternalId()` and `operation.getInternalId()`; one unrelated identifier or a generic request ID is not a substitute for the entity identifiers. For a log describing an operation status update, include both the current status before the update and the new status, together with the operation identifiers. Cite the log and the available context it omits.
- **Exceptions:** Do not flag untouched logs, or messages for events that have no relevant entity identifiers or values. Structured log fields or reliably populated MDC fields attached to the same log event satisfy the requirement. Do not require unavailable fields, extra database/network calls, or adding logs where none exist. Never require secrets or sensitive values to be logged; mask or redact them according to project policy. Avoid duplicate findings for the same missing context already reported under JAVA-ERROR-003.
- **Default priority:** P3 — mandatory team logging-context convention.
- **Fix:** Use parameterized messages or structured fields containing the relevant identifiers and values. For example: `log.info("Operation status update: id={}, externalId={}, internalId={}, currentStatus={}, newStatus={}", operation.getId(), operation.getExternalId(), operation.getInternalId(), operation.getStatus(), newStatus)` before mutation; if logging after mutation, preserve the previous status beforehand so the two fields describe the actual transition.

## SPRING-TX-001 — Do not call external APIs inside an active database transaction

- **Applies to:** New or changed execution paths making external API calls while a database transaction is active, including HTTP/RPC calls to internal services and payment providers.
- **Check:** Treat an external API call inside an active database transaction as a prohibited pattern. Trace the call chain and actual transaction boundary: method/class-level `@Transactional`, transactional callers, propagation and programmatic transactions. Explain the concrete impact: network latency or timeouts prolong database resource/lock retention, and a database rollback cannot undo an external side effect. `readOnly = true` and configured network timeouts do not exempt the call.
- **Exceptions:** Do not infer an active transaction solely from an annotation: account for proxy interception and self-invocation. Do not flag local Java method calls, request construction, or deferred work whose external execution occurs after transaction completion. A call executed with the transaction actually suspended (for example, an effective `NOT_SUPPORTED` boundary) is outside this rule. If transaction activity or the external call cannot be established, use UNVERIFIED rather than inventing a violation.
- **Default priority:** P1 — high-priority, blocking transaction-boundary defect; support the finding with the concrete transactional call path and impact, not annotation presence alone.
- **Fix:** Move external API execution outside the active database transaction and keep database transactions short. Where remote side effects and persistence require coordination, use explicit operation states, idempotency and an appropriate outbox/compensation workflow; preserve consistency when splitting the transaction. Merely extracting the call into a private method or adding `REQUIRES_NEW` does not remove the external call from a transaction.

## SPRING-TX-002 — Keep write-transaction methods short and focused on persistence

- **Applies to:** New or changed methods annotated with `@Transactional`, including methods covered by class-level transaction configuration, whose effective transaction configuration is not `readOnly = true`.
- **Check:** Require short methods focused primarily on saving data to the database. Business decisions, calculations, data preparation and substantial workflow orchestration must occur outside the write-transaction method; the method should mainly apply prepared changes and coordinate the database writes that must be atomic. Inspect delegated work as part of the same boundary: a short method that calls a helper containing substantial business logic does not satisfy the rule. Cite the concrete business logic or excessive responsibilities within the method's transaction boundary; do not invent a fixed line-count limit or flag a method solely by its physical length.
- **Exceptions:** Methods with effective `readOnly = true` are exempt from this rule. Do not flag untouched methods. Minimal persistence-related coordination, locking, version checks and checks that must remain atomic with writes to preserve consistency are permitted; explain that necessity from the actual persistence contract rather than treating arbitrary business logic as a database check. Resolve method-level overrides and inherited/class-level transaction settings; use UNVERIFIED if the effective configuration cannot be established. The read-only exception applies only to this rule and does not exempt external calls prohibited by SPRING-TX-001. Avoid duplicate findings for the same root cause.
- **Default priority:** P3 — mandatory team convention for small persistence-focused write transactions; report demonstrated consistency or transaction defects separately at the severity justified by their impact.
- **Fix:** Perform business processing and prepare the required changes before entering a short transactional persistence method. Preserve atomicity, locking, optimistic version checks and rollback semantics when separating responsibilities, and ensure the persistence method is invoked through an effective transaction boundary; merely moving business logic into a helper called inside the same transaction does not satisfy the rule.

## SPRING-CONFIG-002 — Require milliseconds for RestTemplate duration settings

- **Applies to:** New or changed RestTemplate duration settings and their configuration-to-client mappings, including connection, read/socket and connection-pool acquisition timeouts, connection time-to-live and validation-after-inactivity intervals.
- **Check:** Require configuration values to use milliseconds consistently across properties, defaults, environment-variable bindings and client construction. Trace each value to the consuming API: use `Duration.ofMillis(...)`, `TimeUnit.MILLISECONDS` or a setter whose documented unit is milliseconds. For Spring duration binding, use explicit `ms` values or an explicit millisecond binding unit for bare numbers. Report settings expressed in seconds/minutes and ambiguous numeric duration settings whose millisecond interpretation is not established. Cite the concrete property and consuming call; distinguish a mandatory team-unit convention violation from a demonstrated timeout scaling bug.
- **Exceptions:** Do not flag untouched settings, non-duration values such as connection counts, or internal conversions required by a client API when the external configuration remains in milliseconds and the conversion preserves the intended duration. Do not infer units from a property name alone. If the consuming library or binding contract is unavailable, use UNVERIFIED rather than inventing a unit mismatch.
- **Default priority:** P1 — high-priority mandatory configuration convention; provide concrete evidence of a non-millisecond or ambiguous configuration contract, and describe any demonstrated scaling/runtime impact separately.
- **Fix:** Express configured durations in milliseconds and make their binding/conversion explicit. Convert existing defaults and deployment values together to preserve effective durations; do not merely rename a property or change the consuming time unit without adjusting its values.

## JAVA-FLOW-001 — Keep conditions simple and control flow flat

- **Applies to:** New or changed Java conditions and control flow, including `if`/`else if`, loop conditions, ternary conditions and boolean predicates used to decide execution flow.
- **Check:** Do not combine more than two logical checks in one condition. Count the constituent boolean predicates connected by `&&` or `||`, including predicates inside parentheses; grouping does not reset the count, and comparison operands or method arguments are not separate checks. Recommend splitting a condition with three or more checks into several simple guards or decision steps that preserve its meaning, rather than introducing nested `if` blocks or merely hiding the same complex expression in a helper.
- **Check:** Avoid unnecessary nesting of conditions and loops; keep as much of the main method flow as possible at the method-body level, outside nested control-flow blocks. When an `if` encloses most of the method body, recommend an inverted guard with an early `return`/`throw`, or a sequence of simple guards that decides whether execution should continue. Within loops, use an appropriate early `continue` or `break` where it removes unnecessary nesting. Cite the concrete nesting or dominant enclosing branch and explain a behavior-preserving flatter flow; do not impose an arbitrary nesting-depth or line-count threshold.
- **Exceptions:** Do not flag untouched code or nesting required by the actual algorithm solely because it is nested. Do not mechanically split `||` into independent rejection guards or otherwise change truth tables, short-circuit evaluation, null safety, evaluation order, side effects, loop targets, cleanup or return behavior. Preserve all `else` paths when recommending inversion. A necessary nested loop is not itself a violation; report avoidable nesting with a concrete alternative. Avoid duplicate findings for the same guard already reported under JAVA-VALIDATION-001 or JAVA-VALIDATION-002.
- **Default priority:** P3 — mandatory team convention for simple conditions and readable control flow.
- **Fix:** Replace compound decisions with simple sequential checks and early exits, preserving the original boolean semantics. For example, replace `if (a && b && c) { work(); }` at the end of a void method with `if (!a) return; if (!b) return; if (!c) return; work();`, formatted as separate guards. For mixed conjunctions/disjunctions, derive equivalent decision steps explicitly rather than applying this transformation mechanically.

## JAVA-CONCURRENCY-001 — Match executor queue semantics and propagate asynchronous failures correctly

- **Applies to:** New or changed ExecutorService implementations/configuration, task submission and cross-thread result handling, including ThreadPoolExecutor, executor factories, CompletableFuture tasks, dependent stages and completion handlers.
- **Check:** Identify the actual executor implementation, work-queue type/capacity, worker limits and rejection policy together. For ThreadPoolExecutor, account for an effectively unbounded queue normally preventing growth beyond corePoolSize, bounded queues reaching rejection under load, and SynchronousQueue handing work directly to workers rather than buffering it. Check the demonstrated workload, producer/consumer balance and blocking dependencies for unbounded backlog, starvation or deadlock when tasks wait for other work on the same exhausted pool. Trace shutdown and submission rejection: discarded work must not leave callers believing it succeeded or waiting forever; CallerRunsPolicy must be suitable for the submitting thread and shutdown behavior. Do not assume every ExecutorService has ThreadPoolExecutor queue semantics.
- **Check:** Trace each task's success, failure, cancellation and timeout to its owner. Distinguish execute from submit: exceptions captured in a Future are not automatically reported by a worker's UncaughtExceptionHandler, and a caller-side try/catch around submission does not catch later worker failures. Require observation through a consumed Future, an observed completion stage or an explicit failure-reporting mechanism appropriate to the operation. Preserve exception causes across ExecutionException/CompletionException and application wrappers. Ensure failure is represented by exceptional task/future completion or a defined failed-operation state; logging alone must not turn required work into apparent success. Java Thread has no general-purpose error flag: do not use interrupt status to label arbitrary business or runtime failures. For InterruptedException, propagate interruption or restore the current thread's interrupt status when it cannot be propagated, and stop/recover according to the cancellation contract rather than silently continuing.
- **Check:** For CompletableFuture, verify the intended executor and stage placement, composition of dependent asynchronous work and observation of the terminal stage. Do not lose failures in ignored futures, nested futures, callbacks or completion handlers. Check that manually created futures reach a terminal state on every path, including worker exceptions and rejected submission. Recovery through exceptionally/handle must be intentional and preserve required business failure semantics; whenComplete is an observation hook, not automatic recovery, and failures in its returned stage must remain observable. Check allOf/anyOf against the required aggregation semantics; do not assume they automatically cancel remaining work. Cancellation or timeout of a future does not by itself prove that the underlying operation stopped or rolled back its side effects.
- **Exceptions:** Do not flag untouched code, choose a queue solely by its class name, require every queue to be bounded, or prohibit the common pool without a concrete workload/context problem. Explicit best-effort tasks may use documented failure reporting without a waiting caller. A propagated future can be consumed elsewhere: inspect its owner before claiming it is ignored. Runtime-created executors, unknown queue capacity or unavailable library behavior must be UNVERIFIED when evidence is insufficient. Avoid duplicate findings already covered by GENERIC-002, JAVA-ERROR-001 or SCHED-001.
- **Default priority:** P2; P1 only with concrete evidence of serious lost critical work, deadlock, resource exhaustion or incorrect externally visible success.
- **Fix:** Align the executor, queue, worker limits and overload policy with the workload; provide an explicit backpressure/rejection outcome. Connect worker failures to the owning future or operation, preserve causes and interruption semantics, and observe asynchronous completion. Compose and handle CompletableFuture stages deliberately, keeping fallback, cancellation and timeout behavior consistent with the operation contract; do not replace asynchronous work with blocking get/join indiscriminately.

---

## Reviewer instructions

1. Report only new/changed code issues, with a stable rule ID and exact evidence.
2. Prioritize correctness, data integrity, concurrency, and security ahead of style.
3. Use P0/P1 only with concrete evidence under `references/severity.md`.
4. Do not automatically apply fixes; the target repository remains source-read-only.
5. Avoid duplicate findings for the same root cause.
6. Do not present a team preference as a universal Java/Spring/PostgreSQL requirement.

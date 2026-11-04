# Database and Flyway Review Reference

Check changed database-related code for:

- data consistency defects;
- invalid SQL;
- unsafe schema changes;
- incompatible Flyway migrations;
- missing constraints when required by the changed behavior;
- inefficient database access introduced by the patch;
- accidental N+1 or repeated queries;
- transaction/data consistency mismatches;
- backward compatibility during rollout.

Do not require access to an external database unless the caller explicitly
authorizes such validation.

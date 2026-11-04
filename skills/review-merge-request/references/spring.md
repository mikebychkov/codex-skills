# Spring Review Reference

Check changed Spring code for:

- invalid bean wiring or dependency injection;
- missing or conflicting configuration;
- incorrect profile or property behavior;
- incorrect transaction boundaries;
- proxy-related transactional behavior;
- unsafe singleton mutable state;
- broken validation or exception handling;
- backward-incompatible endpoint or serialization behavior;
- authentication or authorization regressions.

Only report issues that are attributable to the reviewed change or clearly
classifiable as pre-existing observations.

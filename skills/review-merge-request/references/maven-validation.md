# Maven Validation Procedure

## Required environment

Maven settings are external to the target repository and are provided only by:

    MAVEN_SETTINGS

Before running Maven, verify:

    test -n "$MAVEN_SETTINGS" &&
    test -r "$MAVEN_SETTINGS"

If the variable is missing or unreadable, do not run Maven.

Report:

    Maven validation was not executed because MAVEN_SETTINGS was not
    configured or was unavailable to the review environment.

Do not:

- search for another settings file;
- use `./settings.xml`;
- inspect or print the external settings file;
- modify it;
- expose credentials from it.

## Allowed commands

Use Maven Wrapper when present:

    ./mvnw -s "$MAVEN_SETTINGS" compile
    ./mvnw -s "$MAVEN_SETTINGS" test
    ./mvnw -s "$MAVEN_SETTINGS" verify

Otherwise:

    mvn -s "$MAVEN_SETTINGS" compile
    mvn -s "$MAVEN_SETTINGS" test
    mvn -s "$MAVEN_SETTINGS" verify

Never run Maven without `-s "$MAVEN_SETTINGS"`.

## Forbidden validation behavior

Do not run:

    deploy
    release:prepare
    release:perform
    versions:set
    versions:use-latest-versions
    dependency:purge-local-repository

Do not run formatter or auto-repair goals such as:

    spotless:apply
    fmt:format
    spring-javaformat:apply

## Build output

Maven may create ignored output such as `target/`.

That is acceptable only if tracked files and Git state remain unchanged.

The baseline is captured once at review start by `hooks/init-review/hook.py`.
The harness invokes `after-validation` and final verification even when Maven fails.

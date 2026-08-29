#!/usr/bin/env bash
set -euo pipefail

printf '=== Pertineo AI harness init ===\n'
printf 'Java: '
java -version 2>&1 | head -n 1
printf 'Gradle wrapper: '
./gradlew --version | awk '/Gradle / {print $2; exit}'

printf '\n=== Test suite ===\n'
./gradlew --no-daemon test

printf '\n=== Harness check ===\n'
test -f AGENTS.md
test -f docs/agent-harness.md
test -f agent-harness/feature_list.json
test -f agent-harness/progress.md
test -f agent-harness/session-handoff.md
printf 'Harness files present.\n'

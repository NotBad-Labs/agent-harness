---
name: Bug report
about: Report a bug in agent-harness
title: '[BUG] '
labels: bug
assignees: ''
---

## Environment

- **agent-harness commit**: <!-- `git -C /path/to/agent-harness rev-parse HEAD` -->
- **Consumer project type**: <!-- ios / web / backend / cli / other -->
- **Init tier**: <!-- --minimal / --pragmatic / no init (bare usage) -->
- **OS**: <!-- macOS 14.x / Ubuntu 22.04 / etc. -->
- **Python**: <!-- python3 --version -->
- **Agent runtime**: <!-- Claude Code x.y.z / Codex CLI x.y.z / manual usage / etc. -->

## What I expected

<!-- Describe what you thought would happen -->

## What actually happened

<!-- Describe what actually happened. Include error messages / exit codes / stderr output. -->

## Steps to reproduce

1.
2.
3.

## Logs / output

```text
<!-- Paste relevant terminal output, CI log excerpts, or hook stderr here -->
```

## Additional context

<!-- Optional: link to related issues, PR, or upstream docs -->

---

**Before filing**: Please check `BOOTSTRAP.md` and run `bin/agent-harness doctor <path>` to rule out consumer config errors.

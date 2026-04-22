---
name: Feature request
about: Suggest an enhancement or new capability
title: '[FR] '
labels: enhancement
assignees: ''
---

## Problem / motivation

<!-- What problem are you running into? What's the pain point?
     Example: "When using agent-harness with a Python project, I have to manually
     rewrite the docaudit policy layout because there's no `preset-python/` yet." -->

## Proposed solution

<!-- What you'd like to see added / changed. Be specific about scope. -->

## Alternative approaches considered

<!-- Other ways to solve this; pros and cons -->

## Consumer evidence

<!-- Per CONTRIBUTING.md's two-consumer rule, please describe:
     1. Is this a need that shows up in at least 2 different consumer projects (ideally independent)?
     2. Or is it a safety-critical / data-loss-preventing mechanism?
     If neither, it may belong in a consumer overlay rather than agent-harness core. -->

## Layer fit

Which layer should this live in (per [docs/contracts/project-overlay.md](../../docs/contracts/project-overlay.md))?

- [ ] `core/` (language / tool / agent agnostic)
- [ ] `adapter-<agent>/` (specific agent tooling)
- [ ] `preset-<domain>/` (specific stack / domain)
- [ ] `examples/` (just a usage sample)
- [ ] Not sure — please advise

## Additional context

<!-- Optional: similar tools / prior art / references -->

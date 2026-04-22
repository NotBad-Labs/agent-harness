# Security Policy

## Supported versions

**agent-harness** is currently in early experimental phase (Phase D closed, Phase E planning). There is no "released version" — the `main` branch is the current supported state.

Future releases will be versioned (semver planned for Phase F+).

## Reporting a vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them by email to: `chramboliao@gmail.com`

Include in your report:

- A description of the vulnerability
- Steps to reproduce
- The commit SHA you tested against (or "main" if latest)
- Potential impact (data leak / RCE / supply-chain / hook bypass / etc.)
- Any suggested mitigation

You should receive an initial response within **7 days**. If the vulnerability is confirmed, we will work with you on a fix and coordinated disclosure timeline.

## Scope

In scope for security reports:

- Hook bypass vulnerabilities (e.g., `block-dangerous-bash.sh` can be circumvented)
- Injection or arbitrary code execution via `policy.yaml`, `project.yaml`, or CLI arguments
- Supply-chain risks in `core/tools/docaudit/docaudit.py` or `core/cli/*`
- Credential leakage via hooks or CLI output
- Any mechanism that allows a malicious consumer project to exfiltrate data from another consumer using the same upstream

Out of scope:

- Missing features or enhancements (use regular issues)
- Bugs that only affect documentation rendering
- Issues in third-party dependencies (report upstream; we'll track after)

## Responsible disclosure

We commit to:

- Acknowledging your report within 7 days
- Keeping you informed as we triage and fix
- Crediting you in the fix commit / release notes (unless you prefer anonymity)
- Not taking legal action against good-faith security research

Thank you for helping keep agent-harness and its consumers safe.

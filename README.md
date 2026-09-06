# devops-tools

`devops-tools` is a collection of command-line utilities for common DevOps troubleshooting workflows.

## Current tooling

### `logparser`

`logparser` scans log output for known error patterns and reports matching rules with suggested solutions.

Capabilities:

- Parse logs from different sources (for example local files and Jenkins builds).
- Match single-line or multi-line patterns.
- Follow downstream Jenkins failures and parse their logs recursively.
- Output readable summaries of matches and suggested remediation.

---
name: openspec-sync-specs
description: Merge delta specs from an OpenSpec change into openspec/specs/ main capabilities. Use when archiving a change or when main specs drift from implemented behaviour.
license: MIT
compatibility: Requires openspec CLI for validation after sync.
metadata:
  author: openspec
  version: "1.0"
---

Sync delta specifications from a change folder into canonical `openspec/specs/<capability>/spec.md` files.

**Input:** Change name (directory under `openspec/changes/<name>/` or already under `openspec/changes/archive/YYYY-MM-DD-<name>/`).

**Steps**

1. **Locate deltas**

   Read all files under `<change>/specs/*/spec.md`. Each subdirectory name is the capability id (for example `geo-probe`, `batch-export-runner`).

2. **Parse delta sections**

   For each delta file, apply sections in order:
   - `## ADDED Requirements` — append new `### Requirement:` blocks to the main spec (avoid duplicates by requirement title).
   - `## MODIFIED Requirements` — replace the matching `### Requirement:` block in the main spec (match by requirement title after `### Requirement:`).
   - `## REMOVED Requirements` — delete matching requirement blocks from the main spec.

   Preserve the main spec's `# Capability` header and `## Purpose` unless the change explicitly adds a new capability (then create `openspec/specs/<capability>/spec.md` with Purpose + Requirements).

3. **Scenario format**

   Keep OpenSpec scenario formatting (`#### Scenario:` with **WHEN** / **THEN** / **AND** bullets). Do not drop scenarios when merging MODIFIED requirements.

4. **Validate**

   From repo root:

   ```bash
   npx --yes @fission-ai/openspec@latest validate --specs --strict
   ```

   Fix Purpose placeholders and duplicate requirement titles until specs pass (warnings fail in `--strict`).

5. **Report**

   Summarize which capabilities were updated and whether any delta requirement had no matching main spec block (manual merge needed).

**Guardrails**

- Canonical behaviour lives only in `openspec/specs/`; delta files in changes/archive are historical.
- Do not sync product code in this skill — specs only.
- When a retroactive change already merged specs manually, still keep archive deltas as the audit trail; re-run validate only.

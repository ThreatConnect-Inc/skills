# Versions

Each plugin is versioned with semver in its `.claude-plugin/plugin.json`: patch = wording or small learnings, minor = new capability, major = behaviour change. This file is the index and the changelog. `./validate-skills.sh` fails if a row here disagrees with `plugin.json`.

Release pass: bump `plugin.json`, update the row below (version and date), add a changelog entry at the top of the list, run `./validate-skills.sh`, commit.

## Plugins

| Plugin | Version | Last updated |
|---|---|---|
| `tip-intel-lookup` | 0.1.1 | 2026-10-27 |
| `tc-jmespath-assistant` | 0.1.0 | 2026-10-22 |
| `dataminr-playbook-builder` | 0.1.2 | 2026-10-27 |
| `dataminr-playbook-explorer` | 0.1.2 | 2026-10-27 |
| `dataminr-playbook-qa` | 1.3.1 | 2026-10-27 |

## Changelog

Newest first.

### dataminr-playbook-qa 1.3.1 — 2026-10-27
- Anonymised for publication: internal hostnames, instance names, ids, report and owner names, env-file names and local paths replaced with placeholders. Technical content of worked examples kept.

### dataminr-playbook-explorer 0.1.2 — 2026-10-27
- Anonymised for publication: internal hostnames, instance names, ids, report and owner names, env-file names and local paths replaced with placeholders. Technical content of worked examples kept.

### dataminr-playbook-builder 0.1.2 — 2026-10-27
- Anonymised for publication: internal hostnames, instance names, ids, report and owner names, env-file names and local paths replaced with placeholders. Technical content of worked examples kept.
- `example_build_playbook.py` takes its working folders from `PLAYBOOK_WORKDIR` and `PLAYBOOK_EXPORT_DIR`.

### tip-intel-lookup 0.1.1 — 2026-10-27
- Anonymised for publication: internal hostnames, instance names, ids, report and owner names, env-file names and local paths replaced with placeholders. Technical content of worked examples kept.

### dataminr-playbook-qa 1.3.0 — 2026-10-26
- Added section 2.2 (follow-up offers and actions started from chat) and section 16 (script-first, subagents-for-flagged-items QA campaigns).
- Added `references/retrieval_eval.py`.

### dataminr-playbook-explorer 0.1.1 — 2026-10-26
- Synced latest reference updates: Regex Operations, Cache Store/Lookup, Build JSON, native-trigger batch reliability, JSON-8 self-check pitfall, disabled template jobs, per-instance app versions.
- Shortened the description to the 1024-character limit.

### dataminr-playbook-builder 0.1.1 — 2026-10-26
- Synced latest learnings: retrieval-eval echo harness, offer/follow-up flow with Cache Store and case creation, JSON-escaping, disabled template jobs, per-instance app versions, concurrent-load diagnosis worked examples.

### tip-intel-lookup 0.1.0 — 2026-10-22
- Initial import.

### tc-jmespath-assistant 0.1.0 — 2026-10-22
- Initial import.

### dataminr-playbook-builder, dataminr-playbook-explorer, dataminr-playbook-qa 0.1.0 / 0.1.0 / 1.2.0 — 2026-10-22
- Initial import.

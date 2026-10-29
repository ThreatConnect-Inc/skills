# Versions

Skills are grouped into plugins by topic. Each plugin is versioned with semver in its `.claude-plugin/plugin.json`: patch = wording or small learnings, minor = new capability or new skill, major = behaviour change. This file indexes the plugins and their skills and holds the changelog. `./validate-skills.sh` fails if a plugin row here disagrees with `plugin.json`.

Release pass: bump `plugin.json`, update the plugin row and the rows of the skills that changed (version and date), add a changelog entry at the top, run `./validate-skills.sh`, commit.

## Plugins

| Plugin | Version | Last updated |
|---|---|---|
| `cti` | 0.4.0 | 2026-10-29 |
| `playbooks` | 0.3.1 | 2026-10-29 |

## Skills

| Skill | Version | Last updated | Plugin |
|---|---|---|---|
| `intel-lookup` | 0.1.2 | 2026-10-29 | `cti` |
| `playbook-builder` | 0.1.3 | 2026-10-29 | `playbooks` |
| `playbook-explorer` | 0.1.3 | 2026-10-29 | `playbooks` |
| `playbook-qa` | 1.3.1 | 2026-10-29 | `playbooks` |
| `jmespath-assistant` | 0.1.0 | 2026-10-29 | `playbooks` |

## Changelog

Newest first.

### cti 0.4.0 — 2026-10-29
- The bundled MCP server is now named `dataminr-atip` (was `threatconnect`), shown as Dataminr ATIP. Its tools are now `mcp__plugin_cti_dataminr-atip__*`; update any saved permissions or references to the old prefix.
- Added search keywords: dataminr, cyber, threat intelligence.

### playbooks 0.3.1 — 2026-10-29
- Added search keywords: dataminr, cyber, threat intelligence.
- The builder and explorer skills mention the plugin's MCP tool prefix alongside the hand-added one.

### playbooks 0.3.0 — 2026-10-29
- Renamed for clarity. Skills are now `playbook-builder`, `playbook-explorer`, `playbook-qa` and `jmespath-assistant` (were `dataminr-playbook-*` and `tc-jmespath-assistant`); the plugin is `playbooks` (was `dataminr-playbooks`). Install it as `playbooks@dataminr`.
- Added `playbook-builder/references/execution_logs.md` and updated the builder, explorer and QA skills to read execution logs when needed.

### cti 0.3.0 — 2026-10-29
- Renamed: the plugin is `cti` (was `dataminr-cti`) and the lookup skill is `intel-lookup` (was `tip-intel-lookup`). Install it as `cti@dataminr`. The bundled MCP server tools are now `mcp__plugin_cti_threatconnect__*`.
- Bundles the TIP MCP server, configured with the instance hostname and an API token.

### playbooks 0.2.0 — 2026-10-28
- Regrouped (then named `dataminr-playbooks`): the playbook builder, explorer and QA skills and the JMESPath assistant now ship together in one plugin. Skill content is unchanged.

### cti 0.2.0 — 2026-10-28
- Regrouped (then named `dataminr-cti`): the intel lookup skill now ships in this plugin, which is the home for future CTI skills. Skill content is unchanged.

## Earlier history (before skills were grouped into plugins)

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

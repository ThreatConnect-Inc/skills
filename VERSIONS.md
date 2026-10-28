# Versions

Skills are grouped into plugins by topic. Each plugin is versioned with semver in its `.claude-plugin/plugin.json`: patch = wording or small learnings, minor = new capability or new skill, major = behaviour change. This file indexes the plugins and their skills and holds the changelog. `./validate-skills.sh` fails if a plugin row here disagrees with `plugin.json`.

Release pass: bump `plugin.json`, update the plugin row and the rows of the skills that changed (version and date), add a changelog entry at the top, run `./validate-skills.sh`, commit.

## Plugins

| Plugin | Version | Last updated |
|---|---|---|
| `dataminr-cti` | 0.2.0 | 2026-10-28 |
| `dataminr-playbooks` | 0.2.0 | 2026-10-28 |

## Skills

| Skill | Version | Last updated | Plugin |
|---|---|---|---|
| `tip-intel-lookup` | 0.1.1 | 2026-10-27 | `dataminr-cti` |
| `dataminr-playbook-builder` | 0.1.2 | 2026-10-27 | `dataminr-playbooks` |
| `dataminr-playbook-explorer` | 0.1.2 | 2026-10-27 | `dataminr-playbooks` |
| `dataminr-playbook-qa` | 1.3.1 | 2026-10-27 | `dataminr-playbooks` |
| `tc-jmespath-assistant` | 0.1.0 | 2026-10-22 | `dataminr-playbooks` |

## Changelog

Newest first.

### dataminr-playbooks 0.2.0 — 2026-10-28
- Regrouped: the playbook builder, explorer and QA skills and the JMESPath assistant now ship together in one plugin. Install it as `dataminr-playbooks@dataminr-skills`. Skill content is unchanged.

### dataminr-cti 0.2.0 — 2026-10-28
- Regrouped: the intel lookup skill now ships in the `dataminr-cti` plugin, which is the home for future CTI skills. Install it as `dataminr-cti@dataminr-skills`. Skill content is unchanged.

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

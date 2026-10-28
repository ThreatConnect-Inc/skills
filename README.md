# Dataminr CTI Skills

Claude skills for threat intelligence work on the Dataminr and ThreatConnect TIP platform: intel lookup, playbook and agent building, QA and automation. Published as a Claude Code plugin marketplace, one plugin per skill.

## Plugins

| Plugin | What it does |
|---|---|
| `tip-intel-lookup` | Natural-language lookup and reporting over a TIP via the ThreatConnect MCP server or API |
| `tc-jmespath-assistant` | JMESPath help scoped to ThreatConnect Playbooks |
| `dataminr-playbook-builder` | Build, push and live-test Playbooks from their JSON definition |
| `dataminr-playbook-explorer` | Retrieve, explain, audit and diff Playbooks |
| `dataminr-playbook-qa` | QA agent-based playbooks across every trigger pathway |

The playbook skills name each other, so Claude hands off between them in one conversation.

## Requirements

- Claude Code (or claude.ai for skills that work in chat; `scripts/build-chat-zips.sh` builds upload zips).
- Access to a ThreatConnect/TIP instance, with an API key or the ThreatConnect MCP connector. Keep keys in local files such as `.env_<instance>` outside this repo; never commit them.

Playbook skills can change a live instance. They ask for confirmation, back up before a push and can revert, but try them on a test instance first.

## Install

```
/plugin marketplace add ThreatConnect-Inc/skills
/plugin install tip-intel-lookup@dataminr-skills
```

The marketplace is named `dataminr-skills`, so install any plugin as `<plugin>@dataminr-skills`.

## Develop

Clone the repo and run `scripts/link-skills.sh` to symlink every skill in `plugins/` into `~/.claude/skills/` so edits are live in Claude Code. Run `./validate-skills.sh` before committing. See `CONTRIBUTING.md` for conventions.

## Layout

```
.claude-plugin/marketplace.json     marketplace catalog
plugins/<name>/.claude-plugin/plugin.json
plugins/<name>/skills/<name>/SKILL.md (+ references/, scripts/)
scripts/                            helpers (link-skills.sh, build-chat-zips.sh)
validate-skills.sh                  repo checks
VERSIONS.md                         plugin versions and changelog
```

## License

Apache License 2.0. See `LICENSE`.

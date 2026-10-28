# Dataminr CTI Skills

Claude skills for threat intelligence work on the Dataminr and ThreatConnect TIP platform: intel lookup, playbook and agent building, QA and automation. Published as a Claude Code plugin marketplace, one plugin per skill.

## Plugins and skills

Skills are grouped into plugins by topic. Install a plugin to get all of its skills.

- **`dataminr-playbooks`**: build, explore, test and QA ThreatConnect Playbooks and agents.
- **`dataminr-cti`**: cyber threat intelligence skills for a TIP.

| Skill | Plugin | What it does |
|---|---|---|
| `tip-intel-lookup` | `dataminr-cti` | Natural-language lookup and reporting over a TIP via the ThreatConnect MCP server or API |
| `dataminr-playbook-builder` | `dataminr-playbooks` | Build, push and live-test Playbooks from their JSON definition |
| `dataminr-playbook-explorer` | `dataminr-playbooks` | Retrieve, explain, audit and diff Playbooks |
| `dataminr-playbook-qa` | `dataminr-playbooks` | QA agent-based playbooks across every trigger pathway |

The playbook skills name each other, so Claude hands off between them in one conversation.

## Requirements

- Claude Code (or claude.ai for skills that work in chat; `scripts/build-chat-zips.sh` builds upload zips).
- Access to a ThreatConnect/TIP instance, with an API key or the ThreatConnect MCP connector. Keep keys in local files such as `.env_<instance>` outside this repo; never commit them.

Playbook skills can change a live instance. They ask for confirmation, back up before a push and can revert, but try them on a test instance first.

## Install

```
- In Claude Desktop, go to Settings
- Plugins
- + Add
- Add Marketplace
- Paste in ThreatConnect-Inc/skills
```

OR

```
/plugin marketplace add ThreatConnect-Inc/skills
/plugin install dataminr-playbooks@dataminr-skills
/plugin install dataminr-cti@dataminr-skills
```


If using the `playbook` skills - you will need to create a `.env` file in the project folder which contains your TIP APIV2 key.
example .env file
```
TC_KEY=APIV2.........
```

You can get an APIV2 key by editing any API account in the TIP.

The marketplace is named `dataminr-skills`; install each plugin as `<plugin>@dataminr-skills`.

## Develop

Clone the repo and run `scripts/link-skills.sh` to symlink every skill in `plugins/` into `~/.claude/skills/` so edits are live in Claude Code. Run `./validate-skills.sh` before committing. See `CONTRIBUTING.md` for conventions.

## Layout

```
.claude-plugin/marketplace.json     marketplace catalog
plugins/<plugin>/.claude-plugin/plugin.json
plugins/<plugin>/skills/<skill>/SKILL.md (+ references/, scripts/)
scripts/                            helpers (link-skills.sh, build-chat-zips.sh)
validate-skills.sh                  repo checks
VERSIONS.md                         plugin versions and changelog
```

## License

Apache License 2.0. See `LICENSE`.

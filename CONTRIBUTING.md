# Contributing

- One skill or fix per pull request.
- Layout is `plugins/<plugin>/skills/<skill>/SKILL.md`. Plugins group skills by topic (`dataminr-playbooks`, `dataminr-cti`); a skill's `name` must match its directory. Every plugin needs `.claude-plugin/plugin.json` and an entry in `.claude-plugin/marketplace.json`. A new skill goes into the plugin for its topic; add a plugin only for a new topic.
- `SKILL.md` needs `name` and `description` frontmatter. The description is at most 1024 characters and should say when to use the skill. Keep `SKILL.md` under about 500 lines and put detail in `references/`.
- Write for every ThreatConnect/TIP user, not one environment. Worked examples are welcome if anonymised: no real hostnames, instance names, playbook ids, customer or report names, local paths, credentials or customer data. Use placeholders such as `<instance>` and `<id>`.
- Version bumps (semver in `plugin.json`): patch = wording or small learnings, minor = new capability, major = behaviour change. Update the plugin and skill rows and add a changelog entry in `VERSIONS.md`.
- Before opening a pull request, run `./validate-skills.sh`. It must exit 0.

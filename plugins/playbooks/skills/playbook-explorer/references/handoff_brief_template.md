# Hand-off brief template (for another engineer's Claude Code session)

Use when someone else (a UI/viewer engineer, a platform engineer, a customer team) will load a playbook into their own Claude Code session to debug or extend it. Their session knows nothing about the playbook, so a short, accurate brief saves far more time than the raw JSON alone. Write ONE markdown file, verified against the live definition (re-fetch first; state the instance, groupXid and version at the top), and put anything you have not verified under a clearly labelled "UNVERIFIED" heading or marker. Never include credentials, `.env` contents or customer data.

Sections, in this order (cut any that do not apply):

1. **What it is**: one paragraph. Trigger type, what launches it, what the trigger returns, the payload keys it reads.
2. **Modes / branches**: the values that choose a path (object type, format, flag) and what each path does.
3. **Pipeline in execution order**: numbered, by job NAME (ids change on every save), grouping parallel jobs. Name the LLM jobs and what each outputs, and the job whose output is the final result.
4. **Where the output comes from**: which parts of the final output the playbook generates and which are added afterwards by another layer (viewer, post-processor, email renderer). State plainly what you have not seen.
5. **The open problem**: symptom, then an evidence table (one row per experiment: input size/shape, where it landed, result) with the raw samples in an appendix. Say which dimension was varied (row count, section length, page position). Write down the hypotheses, each marked verified or unverified, and the experiment that would separate them.
6. **Other known issues**: one line each, and who owns them, so the reader does not chase them.
7. **Conventions and gotchas** for this playbook: ids change per save (look jobs up by name), drafts versus published versions, custom-library behaviours that differ from the standard, how data is passed between jobs, whether a webhook exists for automated runs, log level.
8. **Other material**: what else exists (full export, template, sample payloads) and who can supply it. Embed only the small part the problem depends on.
9. **Suggested first prompt** for their session: the goal, the files to read, where in their repo to search, and what a good answer looks like (a fix or a template-side workaround).

Keep it to a few pages. State facts, not narrative of how you found them. Date it and say it describes one version.

# Reading playbook execution logs (steps, inputs, outputs, app logs)

**Use this only when you really need it.** It is slow (several calls per run, large payloads, and it needs the user's signed-in browser), so escalate in this order and stop as soon as you have the answer:

1. **Cheap signals first:** the response/output the playbook already returns, and a distinct message per failure branch (see "Debugging" in `SKILL.md`). Compare the output against what you expect.
2. **Execution status (v3 API, API key, fast):** did the run fail, and when? See section A.
3. **Step list (internal API, browser session):** which step failed and its exit message. See section B. This usually names the cause on its own.
4. **One step's inputs/outputs:** to see what the failing step actually received or produced. See section C.
5. **App logs:** last resort. Most lines are TRACE boilerplate; the useful content is usually the exit message from step 3 and the input from step 4.

The UI's own failure banner is not a reliable signal (it can show on runs whose execution completed and produced output). Treat the execution status and the step exit messages as the truth.

## A. Find the execution (v3 API, works with the normal API key)

```
GET /api/v3/playbook/executions?tql=playbookXid = "<groupXid>" and status = "Failed" and startedTime > "2026-01-01T00:00:00Z"&resultLimit=50
```

- Filter by `playbookXid` (stable across versions), not `playbookId` (it changes on every push).
- Valid TQL fields (list them with `OPTIONS /api/v3/playbook/executions/tql`): `id`, `playbookId`, `playbookXid`, `status`, `queuedTime`, `startedTime`, `completedTime`, `failedTime`.
- The JSON field is `startTime` but the TQL field is `startedTime`; using `startTime` in TQL is a parse error.
- **Failed executions have `failedTime` and no `completedTime`**, so a `completedTime` filter silently drops every failure. Filter on `startedTime`, `failedTime` or `status`.
- The record has `id`, `status` (for example `Completed`, `Failed`), `playbookId`, `startTime`, `completedTime`/`failedTime`. It does **not** include the session UUID the internal API needs, and `GET /api/v3/playbook/executions/<id>` is not supported.

## B. Get the session UUID and the steps (internal API, browser session only)

The internal endpoints (`/api/internal/...`) are undocumented, can change without notice, and **return 401 for the API key**; they accept the signed-in browser session. So run them as same-origin `fetch` calls from a page the user is already signed in to (open your own tab on the instance, then run JavaScript there). Never ask for or type credentials.

1. List executions for the playbook id (the id the UI uses, from the v3 playbook record or the execution record's `playbookId`):
   `GET /api/internal/playbooks/executions/<playbookId>?pageOffset=0&pageLimit=100&search=` -> `data[]` rows with `id` (same integer as v3), `status`, `sessionId` (the top-level session UUID), `startedTime`, `endTime`. Match your execution by `id` (from section A), not by eyeballing times. Older versions of a playbook sit under their own `playbookId`; use the id from the v3 execution record.
2. Steps: `GET /api/internal/playbooks/executions/<sessionId>/steps` -> `data[]` with `name`, `type`, `status` (`Completed`, `Executed` for the trigger, `Failed`), `exitMessage`, `executionTime`, `completeTime`, and the step's own `sessionId`.

Example (browser console / a JavaScript tool; the result of the last expression is returned):

```js
const j = await (await fetch('/api/internal/playbooks/executions/<playbookId>?pageOffset=0&pageLimit=100&search=', {credentials:'include'})).json();
const ex = j.data.find(x => x.id === <executionId>);
const steps = (await (await fetch('/api/internal/playbooks/executions/' + ex.sessionId + '/steps', {credentials:'include'})).json()).data;
JSON.stringify(steps.filter(s => s.status === 'Failed').map(s => ({name: s.name, exit: (s.exitMessage||'').slice(0,500), sid: s.sessionId})))
```

**A step marked `Failed` is not necessarily the cause.** Optional steps (for example an "extract name" job with "No results found") fail benignly in good runs too. Always fetch one known-good run of the same playbook and compare the failed-step list and step count; the cause is the failed step that is *not* in the good run.

## C. Inputs, outputs and app logs for one step

Using the top-level `sessionId` and the step's own `sessionId`:

- `GET /api/internal/playbooks/executions/<sessionId>/<stepSessionId>/details/inputs`
- `GET /api/internal/playbooks/executions/<sessionId>/<stepSessionId>/details/outputs`
- `GET /api/internal/playbooks/executions/<sessionId>/<stepSessionId>/details/appLogs?pageOffset=0&pageLimit=1000&messageFilter=`

Each input/output is `{name, value}` with the value stored as an escaped JSON string; `appLogs` returns `{data:[{level,message,timestamp,...}]}`.

Tips:
- Payloads can be tens of KB and may contain customer or intelligence data. Do not paste them wholesale: extract the specific fact you need (a length, whether a marker string is present, a short snippet around a keyword such as the model's stray prose) and keep tool output small (it truncates near 1,000 characters).
- Some JavaScript tools block output that contains URLs with query strings or cookie-like text; strip `?`, `&` and `=` from any snippet you print.
- Keep intermediate results in a page variable (for example `window.__steps`) between calls instead of refetching.
- Log level matters: the playbook needs `logLevel` `DEBUG` or `TRACE` for step detail (see `SKILL.md`). A run executed before a log-level change will not have it.
- After a programmatic push and activation the Designer can show no execution data until the user disables, refreshes and re-enables (user-reported platform bug). Not tested whether the API calls above are affected; if a run you started does not appear in the list, check this before assuming it did not run.

## When it paid off (worked example)

An LLM planner step, followed by a JMESPath extract, failed intermittently. The execution list showed the run as `Failed`; the step list showed one failed step beyond the benign one, with the JMESPath exit message "invalid type for value: None"; that step's input showed the planner's JSON followed by prose and a second JSON object. The fix was a cleanup job that keeps the last JSON object, plus a prompt rule to emit one object only. The whole diagnosis took four short calls and needed no help from the user.

# FreeMarker (FTL) debugging in Template Builder jobs

Confirmed failure modes and fixes, learned from real `Error completing template` traces in Template Builder jobs. Read this when a playbook's `Template Builder`/`FTL Assembler`/`Concat Sections`-style job is erroring, rather than guessing at FreeMarker semantics.

## `?then(a, b)` is NOT short-circuiting — don't use it to guard a failing call
It's tempting to write `cond?then(doSomething(x), "fallback")` to avoid calling `doSomething(x)` when `x` is null/missing. **This doesn't work** — FreeMarker evaluates both arguments before `?then` picks one, so the failing call still happens even on the branch you didn't want. The only construct that actually skips evaluating the untaken branch is a real `<#if>/<#else>` block:
```
<#if x??>
  <#local result = doSomething(x) />
<#else>
  <#local result = "fallback" />
</#if>
```
Confirmed both the syntax error from writing `?then` wrong (`x?? then(...)` — missing a `?` before `then`, should be `(x??)?then(...)`) and, after fixing the syntax, that it still didn't prevent the underlying failure — only switching to `<#if>/<#else>` actually fixed it.

## A null/missing value passed as a function argument throws *before* the function body runs
Calling a user-defined `<#function>`/`<#macro>` with an argument expression that resolves to null/missing throws `"required parameter 'val' ... had null/missing value"` **at the call site**, before the function's own internal `<#if !val??>`-style guard ever executes. This matters most for **recursive** functions (e.g. a hand-rolled generic JSON serializer): guarding only the function's own top-level entry isn't enough — every recursive self-call site *inside* the function body needs its own `<#if ...??> ... <#else> ... </#if>` guard before it recurses, not just the function's first line. A function that looks completely null-safe at a glance can still break if its recursive calls (e.g. iterating a sequence's items, or a hash's values) aren't independently guarded.

## `?eval_json` on an empty string throws "Empty JSON (contains no value)"
Seen when a job references another job's output via `?eval_json` and that upstream output came back as a genuinely empty (zero-length) string — commonly because an upstream worker/job produced no content for that particular run (e.g. a parallel worker whose assigned slice of data was empty), not because of a bug in the parsing itself. Guard with `?has_content` before parsing, defaulting to an empty collection:
```
<#if someVar?has_content>
  <#assign parsed = someVar?eval_json />
<#else>
  <#assign parsed = [] />
</#if>
```
If this error surfaces in a *downstream* job (e.g. an Assembler receiving an already-blank string from an upstream Template Builder step), the real failure is almost always one step further upstream — check whether the job that produced the blank string itself errored out (possibly on this exact same error, one level up) rather than debugging the downstream job in isolation.

## "Evaluated to null or missing" on a variable you expected to be wired in
This means the variable was referenced in the template body but never actually bound via that job's `inputs` parameter — FreeMarker isn't guessing wrong, the binding genuinely doesn't exist. Two ways to fix it: (a) actually add the missing input binding on the job, or (b) **check whether the template already computes an equivalent value earlier in the same file** before introducing a new one — confirmed case: a template needed a UI base-URL, and rather than wiring up a new unbound variable, the fix was to reuse an `origin` variable the same template already derived (stripping a trailing `/api` from an existing `hostApi`/`hostDirect` input) a few lines above, which was already in scope and already used elsewhere later in the same file. Search the template for an existing variable serving the same purpose before adding new job-input plumbing.

## Useful built-ins for exactly this class of problem
- `?remove_ending("/api")` / `?remove_beginning("...")` — strips a suffix/prefix only if present, no-op otherwise. Safer and clearer than a manual `?ends_with(...)` + `?substring(...)` check, and much safer than a naive `?replace(...)` (which isn't anchored to the end of the string and can misfire if the substring appears elsewhere too).
- `??` tests existence (null/missing) and returns a boolean; it does **not** itself prevent evaluation of anything else in the same expression — it's a test, not a guard, unless used inside a real `<#if>`.
- `!defaultValue` supplies a default for a single null/missing reference inline (e.g. `meta.subtitle!''`) — fine for simple substitution, but does not protect a function call made with that value as an argument (see the recursive-call note above); for that, still use `<#if>`.

## Authoring pitfalls found when a template cannot be run offline
- String literals do not accept `\u` escapes (use the literal character) and `\s` is an invalid escape (use `[ ]*` or `\\s`). Regex strings need doubled backslashes in FTL literals (`\\[`). Avoid `#{` inside strings.
- In a `<#function>` use `<#local>`, not `<#assign>`. Wrap `?then` conditions in parentheses (precedence), and never index a possibly empty sequence inside `?then` (assign first).
- A variable you add must not collide with one already in the template: reusing `total` silently changed section numbering. Search the file for the name first.
- Dynamic hash keys are written `{k: v}` with `k` computed. Interpolation printed raw here is `[= ... ]` with no auto-escape, so to render safe bold from model text split on `**` and alternate `<b>` and plain text by index parity instead of emitting model-written HTML.
- There is no offline runtime without Java: check tag balance after every edit and treat the first live run as the test.

import json, copy, glob

import os
# Local working folders: set these to your own paths (an export of the test playbook, and a folder of reference job exports).
S = os.environ.get("PLAYBOOK_WORKDIR", "./workdir")
EXP = os.environ.get("PLAYBOOK_EXPORT_DIR", "./playbook-export/") + "/"

base = json.load(open(S + "/latest_after.json"))          # instance A playbook: trigger, agent, JMESPath v2.0
ifelse_pb = json.load(open(S + "/latest_after.json"))     # has If/Else, Set Variable, Merge
ex = json.load(open(EXP + "generative-report-agent-v1.json"))   # API v3 fetch job shape
kvpb = json.load(open(S + "/kv_found.json"))           # has KeyValue Operations job


def find(pb, prog, name=None):
    return [j for j in pb["jobList"]
            if j["appCatalogItem"]["programName"] == prog and (name is None or j["name"] == name)][0]


T_API = find(ex, "TCPB - ThreatConnect API v3", "Fetch q2_iocs")
T_JM = find(base, "TCPB - JMESPath v2.0")
T_KV = find(kvpb, "TCPB - KeyValue Operations v1")
T_IF = find(ifelse_pb, "If / Else")
T_SV = find(ifelse_pb, "TCPB - SetVariable v1.0")
T_MG = find(ifelse_pb, "Merge")
T_AG = find(base, "Base Agent")


def js(o):
    return json.dumps(o, separators=(",", ":"))


def mk(tpl, name, jid, x, y, params, outs=None):
    j = copy.deepcopy(tpl)
    j["id"] = jid
    j["name"] = name
    j["locationLeft"] = x
    j["locationTop"] = y
    names = {p["appCatalogItemParameter"]["paramName"] for p in j["jobParameterList"]}
    for k in params:
        assert k in names, (name, k, names)
    for p in j["jobParameterList"]:
        n = p["appCatalogItemParameter"]["paramName"]
        if n in params:
            p["value"] = params[n]
    if outs is not None:
        j["outputVariables"] = js([{"sourceInputList": [], "loopVariables": False, "name": n,
                                    "type": t, "encrypt": False} for n, t in outs])
    return j


ids = iter(range(1125899906869401, 1125899906869499))
KV, FG, SG, FI, SI, FT, ST, IF, AG, ER, MG = [next(ids) for _ in range(11)]
TRIG = base["playbookTriggerList"][0]["id"]
G = f"#App:{KV}:group.id!String"
x, y, dx = 100, 300, 260

jobs = [
    mk(T_KV, "Parse Query Params", KV, x, y, {
        "tc_action": "Value Lookup",
        "input_array": f"#Trigger:{TRIG}:trg.http.queryparam!KeyValueArray",
        "fail_on_no_results": "true",
        "column_mapping_lookup": js([{"key": "group.id", "value": "groupId"}])}),
    mk(T_API, "Fetch Group", FG, x + dx, y, {
        "http_method": "GET", "url": f"/v3/groups/{G}",
        "params": js([{"key": "resultLimit", "value": "1"}]), "fail_on_error": "false"},
       [("tc.api.content", "String")]),
    mk(T_JM, "Shape Group", SG, x + 2 * dx, y, {
        "json_data": f"#App:{FG}:tc.api.content!String", "strip_quotes": "true",
        "string_expressions": js([{"key": "group.name", "value": "data.name || 'UNKNOWN'"},
                                  {"key": "group.type", "value": "data.type || 'UNKNOWN'"}])}),
    mk(T_API, "Fetch IOCs", FI, x + 3 * dx, y, {
        "http_method": "GET", "url": "/v3/indicators",
        "params": js([{"key": "tql", "value": f"hasGroup(id = {G} OR hasGroup(id = {G}))"},
                      {"key": "resultLimit", "value": "100"}]),
        "fail_on_error": "true"}, [("tc.api.content", "String")]),
    mk(T_JM, "Shape IOCs", SI, x + 4 * dx, y, {
        "json_data": f"#App:{FI}:tc.api.content!String", "strip_quotes": "false",
        "string_expressions": js([{"key": "shaped",
                                   "value": "data[*].{type: type, indicator: summary, rating: rating, confidence: confidence}"}])}),
    mk(T_API, "Fetch ATT&CK Tags", FT, x + 5 * dx, y, {
        "http_method": "GET", "url": "/v3/tags",
        "params": js([{"key": "tql", "value": f"hasGroup(id = {G} OR hasGroup(id = {G})) AND techniqueId is not null"},
                      {"key": "resultLimit", "value": "100"}]),
        "fail_on_error": "true"}, [("tc.api.content", "String")]),
    mk(T_JM, "Shape TTPs", ST, x + 6 * dx, y, {
        "json_data": f"#App:{FT}:tc.api.content!String", "strip_quotes": "false",
        "string_expressions": js([{"key": "shaped", "value": "data[*].{techniqueId: techniqueId, name: name}"}])}),
    mk(T_IF, "If no data", IF, x + 7 * dx, y, {
        "operator": "equals", "operand_1": f"#App:{SI}:shaped!String#App:{ST}:shaped!String",
        "operand_2": "[][]", "as_numeric": "false"}),
]

SYS = """# Threat Hunt Pack Builder

You are a senior threat hunter. From the intelligence provided, build an actionable threat hunt pack for a SOC / hunt team.

## Rules
- Use ONLY the IOCs and ATT&CK techniques supplied in the user message. Never invent IOCs, technique IDs, or attribution. If an input list is empty, say so and skip that part.
- Be concrete and concise. Write in Markdown.

## Output structure
1. **Hunt Pack Overview** - the intelligence source (name/type), what the IOCs and TTPs suggest, and a 2-3 sentence hunting focus.
2. **IOC Sweep** - the supplied IOCs grouped by type in a table (indicator, rating, confidence) plus where to sweep (DNS/proxy logs for hosts and URLs, firewall/NetFlow for addresses, EDR/file telemetry for hashes).
3. **TTP Hunt Hypotheses** - for each supplied ATT&CK technique: technique ID and name, a one-line hypothesis ("if the adversary used X, we would expect Y"), the data source(s) to check, and 1-2 concrete hunt queries (generic pseudocode plus an example for one common platform such as KQL or Splunk SPL).
4. **Prioritisation** - which 3 hunts to run first and why, using the ratings/confidence and technique relevance.
5. **Triage and Validation** - how to confirm a true positive, likely false positives, and escalation criteria.
6. **Gaps and Caveats** - anything the data cannot support.
"""
USR = (f"Intelligence source: #App:{SG}:group.name!String (type: #App:{SG}:group.type!String, id: {G})\n\n"
       f"IOCs (JSON):\n#App:{SI}:shaped!String\n\n"
       f"ATT&CK techniques (JSON):\n#App:{ST}:shaped!String\n\n"
       "current ISO timestamp: #Global:0:gbl.timestamp.iso!String\n")
ag = mk(T_AG, "Threat Hunt Pack Agent", AG, x + 8 * dx, y - 120, {"systemPrompt": SYS, "userPrompt": USR},
        [("agent.out", "String")])
ag["languageModelConfiguration"]["maxOutputTokens"] = 8000
ag["languageModelConfiguration"].pop("id", None)
ERR = (f"ERROR[no-data]: group {G} (#App:{SG}:group.name!String) has no IOCs or ATT&CK tags "
       "(checked the group and its linked groups).")
er = mk(T_SV, "Set No-Data Error", ER, x + 8 * dx, y + 160,
        {"variable_mapping": js([{"key": "error.message", "value": ERR}])}, [("error.message", "String")])
mg = mk(T_MG, "Merge Response", MG, x + 9 * dx, y, {
    "output_array": js([{"key": "response.merged",
                         "value": f"#App:{AG}:agent.out!String#App:{ER}:error.message!String"}])},
        [("response.merged", "String")])
jobs += [ag, er, mg]

pb = copy.deepcopy(base)
pb.pop("version", None)
pb["name"] = "ZZ Claude Threat Hunt Pack Test"
pb["groupXid"] = "ZZthp001x"
pb["description"] = ("Created via API by Claude. Webhook ?groupId=<TC group id> -> IOCs + ATT&CK tags -> agent -> "
                     "threat hunt pack. Test playbook, safe to delete.")
pb["logLevel"] = "TRACE"   # dev playbooks: DEBUG/TRACE (WARN/INFO only when promoting to production)
pb["jobList"] = jobs
trig = pb["playbookTriggerList"][0]
trig["httpResponseBody"] = f"#App:{MG}:response.merged!String"
trig.pop("scheduleType", None)


def conn(t, **k):
    return dict({"type": t, "isCircularOnTarget": False}, **k)


chain = [KV, FG, SG, FI, SI, FT, ST, IF]
C = [conn("Pass", sourceTriggerId=TRIG, targetJobId=KV)]
C += [conn("Pass", sourceJobId=a, targetJobId=b) for a, b in zip(chain, chain[1:])]
C += [conn("Fail", sourceJobId=IF, targetJobId=AG), conn("Pass", sourceJobId=IF, targetJobId=ER),
      conn("Pass", sourceJobId=AG, targetJobId=MG), conn("Pass", sourceJobId=ER, targetJobId=MG),
      conn("Pass", sourceJobId=MG, targetTriggerId=TRIG, isCircularOnTarget=True)]
pb["playbookConnectionList"] = C
json.dump(pb, open(S + "/thp_new.json", "w"))
print("built", len(jobs), "jobs", len(C), "connections")

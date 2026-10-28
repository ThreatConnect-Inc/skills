# ThreatConnect JMESPath Custom Functions Reference

## null_leaf
Returns null from an array of objects when a key doesn't exist in one or more objects. Ensures the return array matches the length of the original array.

**Usage:** `null_leaf(array, key)`

| Arg | Type | Description |
|-----|------|-------------|
| `array` | array | Array of objects to process |
| `key` | string | Key to extract; missing keys return `null` |

**Example:**
```json
// Expression: team[] | null_leaf(@, `age`)
// Input:
{
  "team": [
    { "age": "44", "name": "Bob" },
    { "age": "43", "name": "Sue" },
    { "age": "33", "name": "Joe" },
    { "name": "Sally" }
  ]
}
// Result:
[ "44", "43", "33", null ]
```

---

## delete
Deletes a key from an object.

**Usage:** `delete(object, key)`

| Arg | Type | Description |
|-----|------|-------------|
| `object` | object | Object or array of objects to process |
| `key` | string | Key to delete |

**Example:**
```json
// Expression: locations[] | delete(@, 'state')
// Input:
{
  "locations": [
    { "name": "Seattle",  "state": "WA" },
    { "name": "New York", "state": "NY" },
    { "name": "Bellevue", "state": "WA" },
    { "name": "Olympia",  "state": "WA" }
  ]
}
// Result:
[
  { "name": "Seattle" },
  { "name": "New York" },
  { "name": "Bellevue" },
  { "name": "Olympia" }
]
```

---

## expand
Expands a list of objects based on a provided key. Works with both lists of objects and nested objects.

**Usage:** `expand(array, &key)`

| Arg | Type | Description |
|-----|------|-------------|
| `array` | array | Array of objects to expand |
| `&key` | expression ref | Key whose array value will be expanded; use `&nested.key` for nested access |

**Example (flat):**

```json
// Expression: expand(@, &urls)
// Input:
[
  { "category": "Malicious", "id": "123", "urls": ["abc.example.com", "def.example.com"] },
  { "category": "Benign",    "id": "456", "urls": ["ghi.example.com", "jkl.example.com"] }
]
// Result:
[
  { "category": "Malicious", "id": "123", "urls": "abc.example.com" },
  { "category": "Malicious", "id": "123", "urls": "def.example.com" },
  { "category": "Benign",    "id": "456", "urls": "ghi.example.com" },
  { "category": "Benign",    "id": "456", "urls": "jkl.example.com" }
]
```

**Example (nested — full objects preserved):**

Uses a named array (`items`) as input and a nested expression ref (`&data.urls`). The outer `data` wrapper is retained in each result object.

```json
// Expression: expand(items, &data.urls)
// Input:
{
  "items": [
    { "data": { "category": "Malicious", "id": "123", "urls": ["abc.example.com", "def.example.com"] } },
    { "data": { "category": "Benign",    "id": "456", "urls": ["ghi.example.com", "jkl.example.com"] } }
  ]
}
// Result:
[
  { "data": { "category": "Malicious", "id": "123", "urls": "abc.example.com" } },
  { "data": { "category": "Malicious", "id": "123", "urls": "def.example.com" } },
  { "data": { "category": "Benign",    "id": "456", "urls": "ghi.example.com" } },
  { "data": { "category": "Benign",    "id": "456", "urls": "jkl.example.com" } }
]
```

---

## format_datetime
Takes a datetime string (many input formats supported) and formats it using Python strftime output format.

**Usage:** `format_datetime(datetime_string, output_format)`

| Arg | Type | Description |
|-----|------|-------------|
| `datetime_string` | string | Input datetime in any common format |
| `output_format` | string | Python strftime format string (e.g. `"%Y-%m-%d %H:%M:%S"`) |

**Example:**
```json
// Expression: {group: {name: post_title, type: 'Event', eventDate: format_datetime(discovered, '%Y-%m-%dT%H:%M:%SZ')}}
// Input:
{
  "discovered": "2020-01-12 00:00:00.000000",
  "group_name": "lorenz",
  "post_title": "Wind-muller"
}
// Result:
{
  "group": {
    "name": "Wind-muller",
    "type": "Event",
    "eventDate": "2020-01-12T00:00:00Z"
  }
}
```

---

## group_by
Groups array items by a provided key. Returns a dict where each key is a unique value of the group key and the value is a list of matching items. Supports nested keys.

**Usage:** `group_by(array, &key)`

| Arg | Type | Description |
|-----|------|-------------|
| `array` | array | Array of objects to group |
| `&key` | expression ref | Key to group by; use `&nested.key` for nested access |

**Example (flatten first, then group):**

Flattens into `spec` objects first via `items[].spec`, then groups by `nodeName`. Result objects are the `spec` contents directly — the outer `spec` wrapper is gone.

```json
// Expression: group_by(items[].spec, &nodeName)
// Input:
{
  "items": [
    { "spec": { "nodeName": "node_01", "other": "values_01" } },
    { "spec": { "nodeName": "node_02", "other": "values_02" } },
    { "spec": { "nodeName": "node_03", "other": "values_03" } },
    { "spec": { "nodeName": "node_01", "other": "values_04" } }
  ]
}
// Result:
{
  "node_01": [
    { "nodeName": "node_01", "other": "values_01" },
    { "nodeName": "node_01", "other": "values_04" }
  ],
  "node_02": [ { "nodeName": "node_02", "other": "values_02" } ],
  "node_03": [ { "nodeName": "node_03", "other": "values_03" } ]
}
```

**Example (nested key, full objects preserved):**

Keeps full item objects intact and groups by the nested path `spec.nodeName`. Result objects retain the outer `spec` wrapper.

```json
// Expression: group_by(items, &spec.nodeName)
// Input:
{
  "items": [
    { "spec": { "nodeName": "node_01", "other": "values_01" } },
    { "spec": { "nodeName": "node_02", "other": "values_02" } },
    { "spec": { "nodeName": "node_03", "other": "values_03" } },
    { "spec": { "nodeName": "node_01", "other": "values_04" } }
  ]
}
// Result:
{
  "node_01": [
    { "spec": { "nodeName": "node_01", "other": "values_01" } },
    { "spec": { "nodeName": "node_01", "other": "values_04" } }
  ],
  "node_02": [ { "spec": { "nodeName": "node_02", "other": "values_02" } } ],
  "node_03": [ { "spec": { "nodeName": "node_03", "other": "values_03" } } ]
}
```

---

## replace
Replaces occurrences of an old value with a new value in a string. Optional count argument limits replacements. Can be combined with `map()` for arrays.

**Usage:** `replace(string, old, new [, count])`  
**With map:** `map(&replace(@, old, new), array)`

| Arg | Type | Description |
|-----|------|-------------|
| `string` | string | Input string |
| `old` | string | Value to replace |
| `new` | string | Replacement value |
| `count` | number (optional) | Max number of replacements |

**Note:** String arguments use single quotes; numeric arguments (e.g. count) use backticks.

**Example (replace all occurrences):**
```json
// Expression: replace(numbers, 'one', 'zero')
// Input:
{
  "numbers": "one one two three four five"
}
// Result:
"zero zero two three four five"
```

**Example (replace first occurrence only, count limited):**
```json
// Expression: replace(numbers, 'one', 'zero', `1`)
// Input:
{
  "numbers": "one one two three four five"
}
// Result:
"zero one two three four five"
```

**Example (replace across array with map):**
```json
// Expression: map(&replace(@, 'one', 'zero', `1`), [].numbers)
// Input:
[
  { "numbers": "one one" },
  { "numbers": "one one two" },
  { "numbers": "one one two three" }
]
// Result:
["zero one", "zero one two", "zero one two three"]
```

---

## uuid5
Generates a reproducible UUID5 value from a string input. Useful when working with Group objects in the ThreatConnect batch API.

**Usage:** `uuid5(string)`

| Arg | Type | Description |
|-----|------|-------------|
| `string` | string | Input string to generate UUID from |

---

## zip
Converts multiple lists into a list of lists grouped by index position. Shorter lists are padded with a fill value (default: `null`).

**Usage:** `zip([list1, list2, ...] [, fillvalue])`

| Arg | Type | Description |
|-----|------|-------------|
| `[list1, list2, ...]` | array of arrays | Lists to zip together |
| `fillvalue` | any (optional) | Pad value for shorter lists; defaults to `null` |

**Example (default fill):**
```json
// Expression: {data: zip([first_names, last_names, ages])}
// Input:
{
  "ages":        ["30", "40"],
  "first_names": ["bob", "joe", "sally"],
  "last_names":  ["smith", "jones", "blah"]
}
// Result:
{
  "data": [
    ["bob",   "smith", "30"],
    ["joe",   "jones", "40"],
    ["sally", "blah",  null]
  ]
}
```

**Example (custom fill):**
```json
// Expression: {data: zip([first_names, last_names, ages], 'my_custom_fill_value')}
// Result:
{
  "data": [
    ["bob",   "smith", "30"],
    ["joe",   "jones", "40"],
    ["sally", "blah",  "my_custom_fill_value"]
  ]
}
```

---

## zip_to_objects
Converts multiple lists into a list of objects grouped by index position.

**Usage:** `zip_to_objects(keys_list, values_list)`

| Arg | Type | Description |
|-----|------|-------------|
| `keys_list` | array of strings | Property names for the resulting objects |
| `values_list` | array of arrays | Lists of values, one per key |

**Example:**
```json
// Expression: {data: zip_to_objects(['first_name', 'last_name', 'age'], [first_names, last_names, ages])}
// Input:
{
  "ages":        ["30", "40"],
  "first_names": ["bob", "joe", "sally"],
  "last_names":  ["smith", "jones", "blah"]
}
// Result:
{
  "data": [
    { "first_name": "bob",   "last_name": "smith", "age": "30" },
    { "first_name": "joe",   "last_name": "jones", "age": "40" },
    { "first_name": "sally", "last_name": "blah",  "age": null }
  ]
}
```

---

## General Notes
- Minify all expressions for production use.
- Nested key access uses dot notation (e.g. `parent.child`).
- Custom functions can be combined with built-in JMESPath functions (e.g. `map`, `keys`, `values`, `sort_by`).
- `expand()` and `group_by()` take expression references (`&key`), not string keys.
- `zip()` produces a list of lists; `zip_to_objects()` produces a list of named objects.

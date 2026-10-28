# JMESPath Standard Functions Reference

Sourced from the [JMESPath specification](https://jmespath.org/specification.html#built-in-functions).

## Type system

| Type | Description |
|------|-------------|
| `number` | Integer or double-precision float |
| `string` | Unicode string |
| `boolean` | `true` or `false` |
| `array` | Ordered sequence of values |
| `object` | Unordered key-value pairs |
| `null` | Null value |
| `expression` | Unevaluated expression reference, denoted `&expr` |
| `any` | Any of the above types |

Array subtypes use `array[number]` syntax. Expression return types use `expression->type` syntax.

---

## abs

```
number abs(number $value)
```

Returns the absolute value of the provided number.

---

## avg

```
number avg(array[number] $elements)
```

Returns the average of the elements in the array. Returns `null` for an empty array.

---

## ceil

```
number ceil(number $value)
```

Returns the next highest integer by rounding up if necessary.

---

## contains

```
boolean contains(array|string $subject, any $search)
```

Returns `true` if `$subject` contains `$search`. For arrays, checks element equality. For strings, checks substring match.

---

## ends_with

```
boolean ends_with(string $subject, string $suffix)
```

Returns `true` if `$subject` ends with `$suffix`.

---

## floor

```
number floor(number $value)
```

Returns the next lowest integer by rounding down if necessary.

---

## join

```
string join(string $glue, array[string] $stringsarray)
```

Joins all elements of `$stringsarray` into a single string, separated by `$glue`.

```
join(', ', ['a', 'b', 'c']) -> "a, b, c"
join('', ['a', 'b', 'c'])   -> "abc"
```

---

## keys

```
array keys(object $obj)
```

Returns an array of the object's keys. Order is not guaranteed.

---

## length

```
number length(string|array|object $subject)
```

Returns the length of the subject:
- string → number of code points
- array → number of elements
- object → number of key-value pairs

---

## map

```
array[any] map(expression->any->any $expr, array[any] $elements)
```

Applies `$expr` to every element in `$elements` and returns the results as an array. Unlike projections, `map()` preserves `null` results — the output array always has the same length as the input.

```
map(&foo, array)        -> extracts foo from each element, nulls included
map(&[], @)             -> flattens each sub-array
```

---

## max

```
number max(array[number]|array[string] $collection)
```

Returns the highest value in the array. Returns `null` for an empty array. Array must be homogeneous (all numbers or all strings).

---

## max_by

```
max_by(array $elements, expression->number|expression->string $expr)
```

Returns the element in `$elements` for which `$expr` produces the maximum value. The entire element is returned, not just the key.

```
max_by(people, &age)              -> element with highest age
max_by(people, &to_number(age_str))
```

---

## merge

```
object merge([object $argument [, object $...]])
```

Merges one or more objects. Each subsequent object's keys override the preceding object's keys. Later arguments take precedence.

```
merge(`{"a": "b"}`, `{"c": "d"}`)           -> {"a": "b", "c": "d"}
merge(`{"a": "b"}`, `{"a": "override"}`)    -> {"a": "override"}
```

---

## min

```
number min(array[number]|array[string] $collection)
```

Returns the lowest value in the array. Returns `null` for an empty array.

---

## min_by

```
min_by(array $elements, expression->number|expression->string $expr)
```

Returns the element in `$elements` for which `$expr` produces the minimum value.

```
min_by(people, &age)
min_by(people, &to_number(age_str))
```

---

## not_null

```
any not_null([any $argument [, any $...]])
```

Returns the first argument that does not resolve to `null`. Accepts one or more arguments. Returns `null` if all arguments are `null`.

```
not_null(no_exist, a, b, c, d)  -> first non-null value
```

---

## reverse

```
array reverse(string|array $argument)
```

Reverses the order of an array or string.

---

## sort

```
array sort(array[number]|array[string] $list)
```

Sorts an array of numbers or strings. Array must be homogeneous. String sorting is based on Unicode code points.

---

## sort_by

```
sort_by(array $elements, expression->number|expression->string $expr)
```

Sorts `$elements` using `$expr` as the sort key. The `expr` must resolve to a number or string for each element.

```
sort_by(people, &age)[].age
sort_by(people, &to_number(age_str))
```

---

## starts_with

```
boolean starts_with(string $subject, string $prefix)
```

Returns `true` if `$subject` starts with `$prefix`.

---

## sum

```
number sum(array[number] $collection)
```

Returns the sum of the array. Returns `0` for an empty array.

---

## to_array

```
array to_array(any $arg)
```

- array → returned as-is
- any other type → wrapped in a single-element array

---

## to_number

```
number to_number(any $arg)
```

- string → parsed as a number (must be valid JSON number format)
- number → returned as-is
- array/object/boolean/null → returns `null`

---

## to_string

```
string to_string(any $arg)
```

- string → returned as-is
- any other type → JSON-encoded string representation

---

## type

```
string type(any $subject)
```

Returns the type of the argument as a string. Return values: `"number"`, `"string"`, `"boolean"`, `"array"`, `"object"`, `"null"`.

---

## values

```
array values(object $obj)
```

Returns an array of the object's values. Order is not guaranteed. Use `sort` or `sort_by` if order matters.

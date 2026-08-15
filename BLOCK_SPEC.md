# Block descriptor reference

A block is a single JSON object. Unknown keys are ignored by the device, so the
format can grow without breaking older firmware. The whole descriptor must be
**≤ 4096 bytes**.

```json
{
  "id": "air-quality",
  "name": "Air quality",
  "author": "epaper-dashboard contributors",
  "version": "1.0",
  "description": "US AQI + PM2.5 from Open-Meteo (no API key)",
  "category": "environment",
  "source": { "type": "json",
    "url": "https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi" },
  "params": [
    { "key": "lat", "label": "Latitude", "type": "string", "default": "34.05" }
  ],
  "extract": [
    { "name": "aqi", "path": "current.us_aqi", "round": true }
  ],
  "render": { "widget": "big-number", "title": "AIR QUALITY", "value": "{aqi}",
              "sub": "US AQI", "accent": true, "minW": 5, "minH": 3 }
}
```

## Identity

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | short lowercase-kebab, **≤ 26 characters**; must equal the directory name |
| `name` | yes | shown in the store and layout editor |
| `author` | yes | free text |
| `version` | yes | string, e.g. `"1.0"` |
| `description` | yes | one line, shown in the store |
| `category` | yes | `environment`, `finance`, `news`, `developer`, `calendar`, `fun`, `other` |

## `source`

| Field | Notes |
| --- | --- |
| `type` | `json` or `text` |
| `url` | `https://` only; may contain `{param}` placeholders |

The URL is fetched once per wake cycle with a 10 s timeout, and the response is
capped at **16 KB**. Placeholders are URL-encoded on substitution.

Placeholders may appear only in the **path or query string**. A `{param}` in the
host is refused at install time: the device can only judge a host after
substitution, so a parameterised one is never trusted.

The device refuses any URL that is not `https://`, or that names a literal
private/loopback/link-local address or a `.local` host.

## `params` (≤ 6)

User-editable values, filled in from the layout editor.

| Field | Notes |
| --- | --- |
| `key` | placeholder name used in the URL |
| `label` | shown in the editor |
| `type` | `string`, `number`, or `choice` — **`secret` is rejected** |
| `default` | prefilled value |
| `choices` | comma-separated, for `type: "choice"` |

Blocks have no access to device settings, credentials, or anything other than
their own params. That is what makes a secret param meaningless here and why it
is refused outright.

## `extract` (≤ 8)

Pulls values out of the response and applies **whitelisted** transforms, in this
order: `mult` → `round` → `map` → `prefix`/`suffix`.

| Field | Notes |
| --- | --- |
| `name` | binding name used by `render`; must be unique within the block |
| `path` | dotted path, `a.b[2].c` or `a.b.2.c`; may contain `{param}` placeholders |
| `mult` | multiply (number) |
| `round` | round to integer |
| `map` | `"0:Clear,1:Cloudy"` value→label table |
| `prefix` / `suffix` | literal text |
| `primary` / `secondary` | when `path` points at an **array**: per-row fields |
| `limit` | rows kept (device shows at most 6) |

For `text` sources the whole body is bound to the first extract's `name`.

Only an extract with `primary` produces rows, and only the `list` widget draws
them. A `list` widget pointing at a scalar extract, or list rows under any other
widget, draws nothing at all — so both are rejected by the validator.

## `render`

| Field | Notes |
| --- | --- |
| `widget` | `big-number`, `list`, `text`, `bar` |
| `title` | frame title; `""` for none |
| `label` | small label (`big-number`, `bar`) |
| `value` | `"{binding}"` for `big-number` / `bar` |
| `sub` | sub-line template, may mix literal text and `{bindings}` |
| `list` | extract name feeding `list` |
| `max` | full-scale value for `bar` (default 100) |
| `accent` | `true` draws in red on 3-colour panels (black on b/w) |
| `minW`, `minH` | minimum grid cells (grid is 16 × 12) |

Widget vocabulary is fixed. `clock`, `date-status`, `weather-now`, `forecast`,
`calendar` and `inbox` are native built-ins (`source.type: "builtin"`) and
cannot be declared by a contributed block.

## Distribution envelope

Blocks are published as `.epb` files:

```json
{ "format": "epb1",
  "payload": "<base64 of the block JSON bytes>",
  "sigs": [ { "keyid": "my-registry-2026", "alg": "ecdsa-p256-sha256",
              "sig": "<base64 DER signature over the payload bytes>" } ] }
```

The signature covers the exact payload bytes — no canonicalisation. The device
verifies it with ECDSA P-256 + SHA-256 (mbedTLS) *before* parsing or storing
anything.

`index.json` is the same envelope wrapping `{"format":"epb-index1","blocks":[…]}`,
where each entry carries `id`, `name`, `author`, `version`, `description`,
`category`, `epb`, and optionally `minW`, `minH`, `screenshot`. The signed index
is fetched with a **24 KB** cap; a device holds **16 installed blocks**.

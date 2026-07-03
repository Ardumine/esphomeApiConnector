# ESPHome API Connector

HTTP bridge between C programs and ESPHome devices. Registers multiple ESPHome devices at runtime, keeps real-time state caches, and serves entity values via a simple REST API.

## Architecture

```
 ┌──────────┐      HTTP (poll)       ┌──────────────────────────┐
 │          │ ──── GET /devices ───> │                          │
 │ C client │ <──── 200 OK ──────── │   FastAPI :9734          │
 │          │                        │                          │
 │          │ ── POST /devices ───> │  ┌──────────────────────┐ │
 │          │ <─── 201 Created ──── │  │    DeviceManager     │ │
 └──────────┘                        │  │                      │ │
                                     │  │ "greenhouse" ──> ESPHome 1  │
                                     │  │ "garage"    ──> ESPHome 2  │
                                     │  │ ...                    │ │
                                     │  └──────────────────────┘ │
                                     └──────────────────────────┘
```

- **DeviceManager** spawns one `APIClient` + `ReconnectLogic` per device
- **Per-device state cache** updated in real-time via `subscribe_states`
- **Auto-reconnect** on WiFi drop or device reboot
- **Failure isolation** — one offline device never blocks others

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python server.py
# Listening on http://0.0.0.0:9734
# Interactive docs at http://localhost:9734/docs
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/devices` | Register a device |
| `DELETE` | `/devices/{id}` | Unregister and disconnect |
| `GET` | `/devices` | List all devices |
| `GET` | `/devices/{id}/entities` | All entities with values |
| `GET` | `/devices/{id}/entities/{object_id}` | Single entity value |

Registration is non-blocking — the response returns immediately while connection happens in the background. Poll `/devices` to check connection status.

### Examples

**Register a device:**

```bash
curl -X POST http://localhost:9734/devices \
  -H "Content-Type: application/json" \
  -d '{"id":"greenhouse","address":"esp-movimento.local","api_key":"ZcNzgkp3P3Zk0tX3Z1bjB961UxOZ0GU0JpueBy2obtc"}'
```

```json
{"id":"greenhouse","connected":false,"entity_count":0}
```

Wait a few seconds and check again:

```bash
curl http://localhost:9734/devices
```

```json
[{"id":"greenhouse","connected":true,"entity_count":24}]
```

**Read all entities:**

```bash
curl http://localhost:9734/devices/greenhouse/entities
```

```json
{
  "device_id": "greenhouse",
  "connected": true,
  "entities": {
    "temperatura":     {"name":"Temperatura",    "type":"sensor",        "value":29.9, "unit":"°C"},
    "humidade":        {"name":"Humidade",       "type":"sensor",        "value":32.2, "unit":"%"},
    "bmp_temperatura": {"name":"BMP Temperatura","type":"sensor",        "value":30.2, "unit":"°C"},
    "neopixel":        {"name":"NeoPixel",       "type":"light",         "value":true},
    "ld2410_bluetooth":{"name":"LD2410 Bluetooth","type":"switch",       "value":false},
    "presence":        {"name":"Presence",       "type":"binary_sensor", "value":false},
    "thread_ip_address":{"name":"Thread IP","type":"text_sensor","value":"fd54:9a6:..."}
  }
}
```

**Read a single entity:**

```bash
curl http://localhost:9734/devices/greenhouse/entities/temperatura
```

```json
{"name":"Temperatura","type":"sensor","value":29.9,"unit":"°C"}
```

**Unregister:**

```bash
curl -X DELETE http://localhost:9734/devices/greenhouse
```

### Entity types

| `type` | `value` C type | `unit` |
|--------|---------------|--------|
| `sensor` | `float` | Varies (`°C`, `%`, `hPa`, …) |
| `binary_sensor` | `bool` | — |
| `switch` | `bool` | — |
| `light` | `bool` | — |
| `button` | `null` | — |
| `text_sensor` | `string` | — |
| `select` | `string` | — |
| `number` | `float` | Varies |
| `fan` | `bool` | — |
| `cover` | `float` (0-1) | — |
| `climate` | — (future) | — |

### Request schemas

**`POST /devices`** (`RegisterRequest`):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | Yes | Unique device identifier |
| `address` | `string` | Yes | IP, IPv6, or `.local` mDNS hostname |
| `api_key` | `string` | No | Base64 API key from ESPHome dashboard |

### Response schemas

**`DeviceSummary`** — returned by `/devices` list and register response:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Device identifier |
| `connected` | `bool` | Whether currently connected |
| `entity_count` | `int` | Number of entities discovered |

**`EntityValue`** — single entity:

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string` | Human-readable name |
| `type` | `string` | Entity type (see table above) |
| `value` | `float\|bool\|string\|null` | Current state |
| `unit` | `string\|null` | Unit of measurement if applicable |

**`DeviceEntities`** — all entities for a device:

| Field | Type | Description |
|-------|------|-------------|
| `device_id` | `string` | Device identifier |
| `connected` | `bool` | Whether currently connected |
| `entities` | `dict[str, EntityValue]` | Map of `object_id` → entity state |

## C client integration

```c
// Register a device
// POST /devices {"id":"greenhouse","address":"esp-movimento.local","api_key":"..."}

// Poll entities every N seconds
// GET /devices/greenhouse/entities
// Parse JSON → extract temperatures by checking type=="sensor" && unit=="°C"

// On shutdown
// DELETE /devices/greenhouse
```

Use libcurl or any HTTP library. The API is standard REST/JSON.

## OpenAPI

Interactive docs at `http://localhost:9734/docs` (Swagger UI) and `/redoc`.

Static spec available in `openapi.json` — auto-generated from the code, can be used for client code generation.

## Future

- `POST /devices/{id}/entities/{object_id}` — toggle switches, set light brightness, etc.

## Files

| File | Purpose |
|------|---------|
| `server.py` | FastAPI app, lifespan, route definitions |
| `device_manager.py` | Device registration, connection lifecycle, state cache |
| `models.py` | Pydantic request/response schemas |
| `requirements.txt` | Python dependencies |
| `openapi.json` | OpenAPI 3.1 specification |

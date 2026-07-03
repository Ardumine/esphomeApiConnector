import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from starlette.responses import RedirectResponse

from device_manager import DeviceManager
from models import (
    DeviceEntities,
    DeviceSummary,
    EntityValue,
    MessageResponse,
    RegisterRequest,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger("server")

manager = DeviceManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server starting on port 9734")
    yield
    logger.info("Shutting down...")
    await manager.shutdown()


app = FastAPI(title="ESPHome API Connector", version="0.1.0", lifespan=lifespan)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


# ── Device management ────────────────────────────────────────────────


@app.post("/devices", response_model=DeviceSummary, status_code=201)
async def register_device(req: RegisterRequest):
    if req.id == "devices":
        raise HTTPException(400, '"devices" is a reserved device id')
    handle = await manager.register(req.id, req.address, req.api_key)
    return DeviceSummary(
        id=handle.device_id,
        connected=handle.connected,
        entity_count=handle.entity_count(),
    )


@app.delete("/devices/{device_id}", response_model=MessageResponse)
async def unregister_device(device_id: str):
    if not await manager.unregister(device_id):
        raise HTTPException(404, f"Device '{device_id}' not found")
    return MessageResponse(detail=f"Device '{device_id}' unregistered")


@app.get("/devices", response_model=list[DeviceSummary])
async def list_devices():
    return [DeviceSummary(**d) for d in manager.list_devices()]


# ── Entities ─────────────────────────────────────────────────────────


@app.get("/devices/{device_id}/entities", response_model=DeviceEntities)
async def get_entities(device_id: str):
    handle = manager.get(device_id)
    if handle is None:
        raise HTTPException(404, f"Device '{device_id}' not found")

    raw = handle.get_all()
    entities = {
        obj_id: EntityValue(**data) for obj_id, data in raw.items()
    }

    return DeviceEntities(
        device_id=device_id, connected=handle.connected, entities=entities
    )


@app.get(
    "/devices/{device_id}/entities/{object_id}",
    response_model=EntityValue,
)
async def get_entity(device_id: str, object_id: str):
    handle = manager.get(device_id)
    if handle is None:
        raise HTTPException(404, f"Device '{device_id}' not found")

    data = handle.get_one(object_id)
    if data is None:
        raise HTTPException(
            404, f"Entity '{object_id}' not found on device '{device_id}'"
        )

    return EntityValue(**data)


# ── Startup ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9734)

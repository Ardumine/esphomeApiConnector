import logging
from typing import Any

from aioesphomeapi import (
    APIClient,
    AlarmControlPanelInfo,
    BinarySensorInfo,
    ButtonInfo,
    CameraInfo,
    ClimateInfo,
    CoverInfo,
    DateInfo,
    DateTimeInfo,
    EntityInfo,
    EntityState,
    EventInfo,
    FanInfo,
    LightInfo,
    LockInfo,
    MediaPlayerInfo,
    NumberInfo,
    ReconnectLogic,
    SelectInfo,
    SensorInfo,
    SirenInfo,
    SwitchInfo,
    TextInfo,
    TextSensorInfo,
    TimeInfo,
    UpdateInfo,
    ValveInfo,
    WaterHeaterInfo,
)

logger = logging.getLogger(__name__)

_ENTITY_TYPE_MAP: dict[type[EntityInfo], str] = {
    SensorInfo: "sensor",
    BinarySensorInfo: "binary_sensor",
    TextSensorInfo: "text_sensor",
    SwitchInfo: "switch",
    LightInfo: "light",
    FanInfo: "fan",
    CoverInfo: "cover",
    ClimateInfo: "climate",
    NumberInfo: "number",
    SelectInfo: "select",
    ButtonInfo: "button",
    LockInfo: "lock",
    TextInfo: "text",
    DateInfo: "date",
    TimeInfo: "time",
    DateTimeInfo: "datetime",
    UpdateInfo: "update",
    SirenInfo: "siren",
    AlarmControlPanelInfo: "alarm_control_panel",
    MediaPlayerInfo: "media_player",
    WaterHeaterInfo: "water_heater",
    ValveInfo: "valve",
    CameraInfo: "camera",
    EventInfo: "event",
}

PORT = 6053


def _entity_type_str(info: EntityInfo) -> str:
    return _ENTITY_TYPE_MAP.get(type(info), "unknown")


def _entity_unit(info: EntityInfo) -> str | None:
    return getattr(info, "unit_of_measurement", None)


def _extract_value(state: EntityState) -> Any:
    if hasattr(state, "state"):
        return state.state
    return None


class DeviceHandle:
    def __init__(self, device_id: str, address: str, api_key: str | None):
        self.device_id = device_id
        self.connected = False

        psk: str | None = None
        if api_key:
            padding = len(api_key) % 4
            psk = api_key + "=" * (4 - padding) if padding else api_key

        self.client = APIClient(address, PORT, noise_psk=psk)
        self.reconnect: ReconnectLogic | None = None

        self._entity_infos: dict[int, EntityInfo] = {}
        self._state_cache: dict[int, Any] = {}
        self._object_id_to_key: dict[str, int] = {}

    async def _on_connect(self):
        entities, _ = await self.client.list_entities_services()

        self._entity_infos.clear()
        self._object_id_to_key.clear()
        for entity in entities:
            self._entity_infos[entity.key] = entity
            self._object_id_to_key[entity.object_id] = entity.key

        self.client.subscribe_states(self._on_state)
        self.connected = True
        logger.info(
            "[%s] Ready: %d entities", self.device_id, len(entities)
        )

    async def _on_disconnect(self, expected: bool):
        self.connected = False
        logger.info(
            "[%s] Disconnected (expected=%s)", self.device_id, expected
        )

    def _on_state(self, state: EntityState):
        if state.key in self._entity_infos:
            self._state_cache[state.key] = _extract_value(state)

    def entity_count(self) -> int:
        return len(self._entity_infos)

    def get_all(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for obj_id, key in self._object_id_to_key.items():
            info = self._entity_infos[key]
            result[obj_id] = {
                "name": info.name,
                "type": _entity_type_str(info),
                "value": self._state_cache.get(key),
                "unit": _entity_unit(info),
            }
        return result

    def get_one(self, object_id: str) -> dict[str, Any] | None:
        key = self._object_id_to_key.get(object_id)
        if key is None:
            return None
        info = self._entity_infos[key]
        return {
            "name": info.name,
            "type": _entity_type_str(info),
            "value": self._state_cache.get(key),
            "unit": _entity_unit(info),
        }

    async def start(self):
        self.reconnect = ReconnectLogic(
            client=self.client,
            on_connect=self._on_connect,
            on_disconnect=self._on_disconnect,
        )
        await self.reconnect.start()

    async def stop(self):
        if self.reconnect:
            await self.reconnect.stop()
        await self.client.disconnect()


class DeviceManager:
    def __init__(self):
        self._devices: dict[str, DeviceHandle] = {}

    def __contains__(self, device_id: str) -> bool:
        return device_id in self._devices

    def get(self, device_id: str) -> DeviceHandle | None:
        return self._devices.get(device_id)

    async def register(
        self, device_id: str, address: str, api_key: str | None = None
    ) -> DeviceHandle:
        if device_id in self._devices:
            await self.unregister(device_id)

        handle = DeviceHandle(device_id, address, api_key)
        self._devices[device_id] = handle
        await handle.start()
        return handle

    async def unregister(self, device_id: str) -> bool:
        handle = self._devices.pop(device_id, None)
        if handle is None:
            return False
        await handle.stop()
        return True

    def list_devices(self) -> list[dict[str, Any]]:
        return [
            {
                "id": handle.device_id,
                "connected": handle.connected,
                "entity_count": handle.entity_count(),
            }
            for handle in self._devices.values()
        ]

    async def shutdown(self):
        for device_id in list(self._devices):
            await self.unregister(device_id)

#!/usr/bin/env python3
import asyncio
import sys

from aioesphomeapi import APIClient, SensorState, SensorInfo

DEVICE_ADDRESS = "fd54:9a6:651b:1:6390:3914:dd55:bb90"
API_KEY = "ZcNzgkp3P3Zk0tX3Z1bjB961UxOZ0GU0JpueBy2obtc"
PORT = 6053


async def main():
    padding = len(API_KEY) % 4
    padded_key = API_KEY + "=" * (4 - padding) if padding else API_KEY
    client = APIClient(DEVICE_ADDRESS, PORT, noise_psk=padded_key)

    try:
        await asyncio.wait_for(client.connect(login=True), timeout=10)

        entities = await client.list_entities_services()
        sensor_infos = {
            e.key: e
            for e in entities[0]
            if isinstance(e, SensorInfo) and e.unit_of_measurement == "°C"
        }

        if not sensor_infos:
            print("No temperature sensors found", file=sys.stderr)
            return 1

        latest = {}

        def on_state(state):
            if isinstance(state, SensorState) and state.key in sensor_infos:
                if not state.missing_state:
                    latest[state.key] = state.state

        client.subscribe_states(on_state)
        await asyncio.sleep(3)

        for info in sensor_infos.values():
            val = latest.get(info.key)
            if val is not None:
                print(f"{info.name}: {val:.1f}°C")
            else:
                print(f"{info.name}: N/A")

    except asyncio.TimeoutError:
        print("Connection timed out", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Failed to connect: {e}", file=sys.stderr)
        return 1
    finally:
        await client.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

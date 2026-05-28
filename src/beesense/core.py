"""Core functionality for BeeSense."""

import asyncio
import time
try:
    from beesense.rest_api import send_inside_temp, send_outside_temp, send_bee_counter
except ImportError:
    from rest_api import send_inside_temp, send_outside_temp, send_bee_counter

LOOP_INTERVAL_SECONDS = 60
LIGHT_INTERVAL_SECONDS = 0.1
SOUND_INTERVAL_SECONDS = 10


async def _temperature_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Read both MCP9808 sensors concurrently every 60 seconds."""
    while True:
        await asyncio.gather(
            loop.run_in_executor(None, lambda: read_mcp9808_example(sensortype=1, address=0x18)),
            loop.run_in_executor(None, lambda: read_mcp9808_example(sensortype=2, address=0x19)),
        )
        await asyncio.sleep(LOOP_INTERVAL_SECONDS)


async def _light_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Read both light sensors concurrently every 100 ms."""
    IDLE = 0
    BEE_ENTERING = 1
    BEE_EXITING = 2
    WAIT_FOR_LEAVE_ENTER = 3
    WAIT_FOR_LEAVE_EXIT = 4 

    status = IDLE
    while True:
        light_pin17, light_pin27 = await asyncio.gather(
            loop.run_in_executor(None, lambda: read_light_sensor_example(data_pin=17, active_low=True, samples=1)),
            loop.run_in_executor(None, lambda: read_light_sensor_example(data_pin=27, active_low=True, samples=1)),
        )

        if status == IDLE:
            if light_pin17 and not light_pin27:
                print("Bee entering detected (pin 17 light, pin 27 dark)")
                status = BEE_ENTERING
            elif light_pin27 and not light_pin17:
                print("Bee exiting detected (pin 27 light, pin 17 dark)")
                status = BEE_EXITING
        elif status == BEE_ENTERING:
            if light_pin27 and not light_pin17:
                print("Bee has fully entered (pin 27 light, pin 17 dark)")
                status = WAIT_FOR_LEAVE_ENTER
            elif light_pin27 and light_pin17:
                print("Bee has left the sensor area prematurely")
                status = IDLE
        elif status == BEE_EXITING:
            if light_pin17 and not light_pin27:
                print("Bee has fully exited (pin 17 light, pin 27 dark)")
                status = WAIT_FOR_LEAVE_EXIT
            elif light_pin17 and light_pin27:
                print("Bee has left the sensor area prematurely")
                status = IDLE
        elif status == WAIT_FOR_LEAVE_ENTER:
            if not light_pin27 and light_pin17:
                print("Bee goes back into the hive")
                status = IDLE
            elif light_pin17 and light_pin27:
                print("Bee has left the sensor area, increment enter count")
                send_bee_counter(1)  # Send to API
                status = IDLE
        elif status == WAIT_FOR_LEAVE_EXIT:
            if light_pin27 and not light_pin17:
                print("Bee goes back to the outside")
                status = IDLE
            elif light_pin17 and light_pin27:
                print("Bee has left the sensor area, increment exit count")
                send_bee_counter(-1)  # Send to API
                status = IDLE

        # TODO: add processing on light_pin17 and light_pin27 here
        await asyncio.sleep(LIGHT_INTERVAL_SECONDS)


async def _sound_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Run do_sound from sph0645 every 10 seconds."""
    try:
        from sph0645 import do_sound
    except ImportError:
        try:
            from beesense.sph0645 import do_sound
        except ImportError as exc:
            print(f"sph0645 unavailable, sound loop disabled: {exc}")
            return
    while True:
        await loop.run_in_executor(None, do_sound)
        await asyncio.sleep(SOUND_INTERVAL_SECONDS)


async def main_async() -> None:
    """Async entry point: runs temperature and light sensor loops concurrently."""
    print("BeeSense is ready to run.")
    loop = asyncio.get_running_loop()
    await asyncio.gather(
        _temperature_loop(loop),
        _light_loop(loop),
        _sound_loop(loop),
    )


def main() -> None:
    """Entry point for the BeeSense package."""
    asyncio.run(main_async())


def hello() -> str:
    """Return a simple greeting string."""
    return "Hello from BeeSense!"


def read_mcp9808_example(sensortype: int = 1, address: int = 0x18, bus_num: int = 1, samples: int = 1, interval_seconds: float = 10.0) -> None:
    try:
        from .mcp9808 import MCP9808
    except ImportError:
        from mcp9808 import MCP9808
    except Exception as exc:
        print("MCP9808 driver unavailable:", exc)
        return

    dev = MCP9808(address=address, bus_num=bus_num)
    try:
        for i in range(max(1, samples)):
            c, f = dev.read_temperature()
            if sensortype == 1:
                print(f"Inside temperature: {c:.2f} °C / {f:.2f} °F")
                send_inside_temp(c)
            elif sensortype == 2:
                print(f"Outside temperature: {c:.2f} °C / {f:.2f} °F")
                send_outside_temp(c)

    except Exception as exc:
        print("Failed to read MCP9808:", exc)
    finally:
        dev.close()


def read_light_sensor_example(data_pin: int = 17, active_low: bool = False, samples: int = 5, interval: float = 1.0) -> bool | None:
    try:
        from .light_sensor import LightSensor
    except ImportError:
        from light_sensor import LightSensor
    except Exception as exc:
        print("Light sensor driver unavailable:", exc)
        return None

    sensor = LightSensor(data_pin=data_pin, active_low=active_low)
    status: bool | None = None
    try:
        sensor.open()
        for i in range(max(1, samples)):
            status = sensor.is_light()
            #print(f"Light sensor on pin {data_pin}: {'LIGHT' if status else 'DARK'}")
            if i < samples - 1:
                import time

                time.sleep(interval)
    except Exception as exc:
        print("Failed to read light sensor:", exc)
    finally:
        sensor.close()
    return status


if __name__ == "__main__":
    main()

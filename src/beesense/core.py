"""Core functionality for BeeSense."""


def main() -> None:
    """Entry point for the BeeSense package."""
    print("BeeSense is ready to run.")
    read_mcp9808_example()
    read_mcp9808_example(address=0x19)


def hello() -> str:
    """Return a simple greeting string."""
    return "Hello from BeeSense!"


def read_mcp9808_example(address: int = 0x18, bus_num: int = 1, samples: int = 1) -> None:
    try:
        from mcp9808 import MCP9808
    except Exception as exc:
        print("MCP9808 driver unavailable:", exc)
        return

    dev = MCP9808(address=address, bus_num=bus_num)
    try:
        for i in range(max(1, samples)):
            c, f = dev.read_temperature()
            print(f"MCP9808 temperature: {c:.2f} °C / {f:.2f} °F")
    except Exception as exc:
        print("Failed to read MCP9808:", exc)
    finally:
        dev.close()


def read_light_sensor_example(data_pin: int = 17, active_low: bool = False, samples: int = 5, interval: float = 1.0) -> None:
    try:
        from light_sensor import LightSensor
    except Exception as exc:
        print("Light sensor driver unavailable:", exc)
        return

    sensor = LightSensor(data_pin=data_pin, active_low=active_low)
    try:
        sensor.open()
        for i in range(max(1, samples)):
            status = sensor.is_light()
            print(f"Light sensor on pin {data_pin}: {'LIGHT' if status else 'DARK'}")
            if i < samples - 1:
                import time

                time.sleep(interval)
    except Exception as exc:
        print("Failed to read light sensor:", exc)
    finally:
        sensor.close()


if __name__ == "__main__":
    main()

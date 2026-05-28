"""Core functionality for BeeSense."""


from beesense.rest_api import send_inside_temp, send_outside_temp


def main() -> None:
    """Entry point for the BeeSense package."""
    print("BeeSense is ready to run.")

    """Temperature sensors"""
    """sensortype=1: inside sensortype=2: outside"""
    read_mcp9808_example(1, address=0x18); 
    read_mcp9808_example(2, address=0x19);

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
        while True:
            for i in range(max(1, samples)):
                c, f = dev.read_temperature()
                if sensortype == 1:
                    print(f"Inside temperature: {c:.2f} °C / {f:.2f} °F")
                    send_inside_temp(c)
                elif sensortype == 2:
                    print(f"Outside temperature: {c:.2f} °C / {f:.2f} °F")
                    send_outside_temp(c)

            import time

            time.sleep(interval_seconds)
    except Exception as exc:
        print("Failed to read MCP9808:", exc)
    finally:
        dev.close()


def read_light_sensor_example(data_pin: int = 17, active_low: bool = False, samples: int = 5, interval: float = 1.0) -> None:
    try:
        from .light_sensor import LightSensor
    except ImportError:
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

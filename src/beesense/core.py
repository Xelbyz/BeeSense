"""Core functionality for BeeSense."""


def main() -> None:
    """Entry point for the BeeSense package."""
    print("BeeSense is ready to run.")
    read_mcp9808_example();


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


if __name__ == "__main__":
    main()

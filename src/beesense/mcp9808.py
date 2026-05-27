"""Minimal MCP9808 driver using smbus2.

This provides a small `MCP9808` class with `temperature_c` and
`temperature_f` accessors and a convenience `read_temperature` method.

It depends on the `smbus2` package. On systems without I2C or where
`smbus2` is unavailable, the module raises ImportError when attempted
to open the bus.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from smbus2 import SMBus
except Exception:
    SMBus = None  # type: ignore


@dataclass
class MCP9808:
    address: int = 0x18
    bus_num: int = 1
    _bus: Optional[object] = None

    TEMP_REG = 0x05

    def open(self) -> None:
        if SMBus is None:
            raise ImportError("smbus2 is required to use MCP9808 on real hardware")
        if self._bus is None:
            self._bus = SMBus(self.bus_num)

    def close(self) -> None:
        if self._bus is not None:
            try:
                self._bus.close()
            except Exception:
                pass
            self._bus = None

    def read_raw_temperature(self) -> int:
        """Read the raw 16-bit temperature value from the sensor.

        Returns the raw word with the sensor's endianness corrected.
        """
        if self._bus is None:
            self.open()
        # read_word_data returns little-endian on many platforms; swap bytes
        raw = self._bus.read_word_data(self.address, self.TEMP_REG)
        raw_swapped = ((raw & 0xFF) << 8) | (raw >> 8)
        return int(raw_swapped)

    def temperature_c(self) -> float:
        """Return temperature in degrees Celsius."""
        raw = self.read_raw_temperature()
        temp = (raw & 0x0FFF) / 16.0
        # sign bit (0x1000) indicates negative temperature
        if raw & 0x1000:
            temp -= 256.0
        return float(temp)

    def temperature_f(self) -> float:
        """Return temperature in degrees Fahrenheit."""
        c = self.temperature_c()
        return c * 9.0 / 5.0 + 32.0

    def read_temperature(self) -> tuple[float, float]:
        """Return (celsius, fahrenheit)."""
        c = self.temperature_c()
        return c, self.temperature_f()


__all__ = ["MCP9808"]

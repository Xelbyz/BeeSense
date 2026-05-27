"""Minimal digital light sensor driver using Raspberry Pi GPIO.

This driver supports a single digital data pin. The sensor is read as a
boolean input: high means light detected and low means dark, unless the
sensor is configured as active-low.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    import RPi.GPIO as GPIO
except Exception:
    GPIO = None  # type: ignore


@dataclass
class LightSensor:
    data_pin: int
    active_low: bool = False
    pull_up: bool = True
    _initialized: bool = False

    def open(self) -> None:
        if GPIO is None:
            raise ImportError("RPi.GPIO is required to use LightSensor on real hardware")

        if not self._initialized:
            GPIO.setmode(GPIO.BCM)
            pud = GPIO.PUD_UP if self.pull_up else GPIO.PUD_DOWN
            GPIO.setup(self.data_pin, GPIO.IN, pull_up_down=pud)
            self._initialized = True

    def close(self) -> None:
        if GPIO is not None and self._initialized:
            try:
                GPIO.cleanup(self.data_pin)
            except Exception:
                pass
            self._initialized = False

    def read(self) -> bool:
        """Read the raw digital pin state."""
        if GPIO is None:
            raise ImportError("RPi.GPIO is required to use LightSensor on real hardware")
        if not self._initialized:
            self.open()

        state = GPIO.input(self.data_pin) != 0
        return not state if self.active_low else state

    def is_light(self) -> bool:
        """Return True when light is detected."""
        return self.read()

    def is_dark(self) -> bool:
        """Return True when no light is detected."""
        return not self.read()


__all__ = ["LightSensor"]

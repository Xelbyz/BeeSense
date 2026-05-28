#!/usr/bin/env python3
"""Periodic SPH0645 FFT analyzer for Raspberry Pi I2S.

Behavior:
- Every 10 seconds, capture 1 second of audio at 48 kHz from ALSA.
- Apply a window (Hann by default).
- Run FFT and summarize magnitude in 100 Hz bands.
"""

from __future__ import annotations

import argparse
import cmath
import math
import shutil
import struct
import subprocess
import sys
import time
import wave



try:
    from beesense.rest_api import send_sound
except ImportError:
    from rest_api import send_sound

def next_power_of_two(n: int) -> int:
	value = 1
	while value < n:
		value <<= 1
	return value


def fft_radix2(values: list[complex]) -> list[complex]:
	"""Iterative radix-2 FFT for power-of-two lengths."""
	n = len(values)
	if n == 0 or (n & (n - 1)) != 0:
		raise ValueError("FFT input length must be a power of two")

	# Bit-reversal permutation
	result = values[:]
	j = 0
	for i in range(1, n):
		bit = n >> 1
		while j & bit:
			j ^= bit
			bit >>= 1
		j ^= bit
		if i < j:
			result[i], result[j] = result[j], result[i]

	length = 2
	while length <= n:
		half = length // 2
		twiddle_step = -2.0j * math.pi / length
		for start in range(0, n, length):
			for k in range(half):
				twiddle = cmath.exp(twiddle_step * k)
				even = result[start + k]
				odd = result[start + k + half] * twiddle
				result[start + k] = even + odd
				result[start + k + half] = even - odd
		length <<= 1

	return result

def window_value(kind: str, i: int, n: int) -> float:
	if n <= 1:
		return 1.0
	angle = 2.0 * math.pi * i / (n - 1)
	if kind == "hamming":
		return 0.54 - 0.46 * math.cos(angle)
	# Hann is a robust default for spectral analysis with lower leakage.
	return 0.5 * (1.0 - math.cos(angle))


def list_devices() -> int:
	try:
		result = subprocess.run(["arecord", "-l"], check=False)
	except FileNotFoundError:
		print("Error: 'arecord' not found. Install ALSA utils: sudo apt install alsa-utils")
		return 1
	return result.returncode


def capture_raw(
	device: str,
	rate: int,
	channels: int,
	seconds: float,
	retries: int = 5,
	retry_delay: float = 2.0,
) -> bytes:
	seconds_for_arecord = int(round(seconds))
	if seconds_for_arecord <= 0:
		raise RuntimeError("capture duration must round to at least 1 second")

	cmd = [
		"arecord",
		"-D",
		device,
		"-f",
		"S32_LE",
		"-c",
		str(channels),
		"-r",
		str(rate),
		"-d",
		str(seconds_for_arecord),
		"-t",
		"raw",
		"-q",
	]
	last_error = ""
	for attempt in range(1, retries + 1):
		try:
			return subprocess.check_output(cmd, stderr=subprocess.PIPE)
		except subprocess.CalledProcessError as exc:
			last_error = exc.stderr.decode("utf-8", errors="replace").strip()
			if "busy" in last_error.lower() or "resource" in last_error.lower():
				print(f"  Device busy (attempt {attempt}/{retries}), retrying in {retry_delay:.0f}s...")
				time.sleep(retry_delay)
			else:
				raise RuntimeError(last_error or "arecord failed") from exc
	raise RuntimeError(f"Device still busy after {retries} attempts: {last_error}")


def extract_channel_int32(raw: bytes, channels: int, data_channel: int) -> list[float]:
	if channels <= 0:
		raise ValueError("channels must be > 0")
	if data_channel < 0 or data_channel >= channels:
		raise ValueError("data_channel must be in [0, channels)")

	total_samples = len(raw) // 4
	if total_samples == 0:
		return []

	all_samples = struct.unpack("<" + "i" * total_samples, raw[: total_samples * 4])
	selected = all_samples[data_channel::channels]
	return [float(s) / 2147483648.0 for s in selected]


def write_wav(raw: bytes, out_path: str, channels: int, rate: int) -> None:
	with wave.open(out_path, "wb") as wav_file:
		wav_file.setnchannels(channels)
		wav_file.setsampwidth(4)  # S32_LE
		wav_file.setframerate(rate)
		wav_file.writeframes(raw)


def summarize_fft(
	samples: list[float],
	rate: int,
	window_kind: str,
	bin_width_hz: float,
	gain: float,
) -> list[tuple[float, float, float]]:
	if not samples:
		return []
	n = len(samples)
	windowed = [samples[i] * gain * window_value(window_kind, i, n) for i in range(n)]

	n_fft = next_power_of_two(n)
	fft_in = [complex(v, 0.0) for v in windowed] + [0j] * (n_fft - n)
	spectrum = fft_radix2(fft_in)

	nyquist = rate / 2.0
	half = n_fft // 2

	mags: list[tuple[float, float]] = []
	for k in range(half + 1):
		freq = k * rate / n_fft
		mag = (abs(spectrum[k]) / n) ** 2
		mags.append((freq, mag))

	results: list[tuple[float, float, float]] = []
	start = 0.0
	while start < nyquist:
		end = min(start + bin_width_hz, nyquist)
		bucket = [m for f, m in mags if (start <= f < end) or (end == nyquist and f == nyquist)]
		avg_mag = sum(bucket) / len(bucket) if bucket else 0.0
		results.append((start, end, avg_mag))
		start = end

	return results


def print_fft_summary(
	summary: list[tuple[float, float, float]],
	bin_width_hz: float,
	min_mag: float,
) -> None:
	print(f"Frequency summary (average magnitude per {bin_width_hz:.0f} Hz bin):")
	printed = False
	for start, end, mag in summary:
		if mag >= min_mag  and start > 0.0:
			print(f"  {start:6.1f}-{end:6.1f} Hz: {mag:.6f}")
			send_sound(mag, int(start // bin_width_hz))  # Send to API
			printed = True
	if not printed:
		print(f"  No bins with magnitude >= {min_mag:.6f}.")


def do_sound() -> int:

	device = "hw:2,0"
	interval = 10.0
	capture_seconds = 2.0
	skip_seconds = 1.0
	rate = 48_000
	channels = 2
	data_channel = 0
	window = "hann"
	bin_width = 100.0
	gain = 100.0
	min_mag = 1e-4
	cycles = 0
	dump_wav = "bee-audio.wav"

	if shutil.which("arecord") is None:
		print("Error: 'arecord' not found. Install ALSA utils: sudo apt install alsa-utils")
		return 1

	if interval <= 0:
		print("Error: --interval must be > 0")
		return 1
	if capture_seconds <= 0:
		print("Error: --capture-seconds must be > 0")
		return 1
	if skip_seconds < 0:
		print("Error: --skip-seconds must be >= 0")
		return 1
	if skip_seconds >= capture_seconds:
		print("Error: --skip-seconds must be less than --capture-seconds")
		return 1
	if rate <= 0:
		print("Error: --rate must be > 0")
		return 1
	if channels <= 0:
		print("Error: --channels must be > 0")
		return 1
	if data_channel < 0 or data_channel >= channels:
		print("Error: --data-channel must be within [0, --channels)")
		return 1
	if bin_width <= 0:
		print("Error: --bin-width must be > 0")
		return 1
	if gain <= 0:
		print("Error: --gain must be > 0")
		return 1
	if min_mag < 0:
		print("Error: --min-mag must be >= 0")
		return 1
	if cycles < 0:
		print("Error: --cycles must be >= 0")
		return 1

	print("SPH0645 periodic FFT analyzer")
	print(
		f"Device={device}, rate={rate} Hz, capture={capture_seconds}s, "
		f"skip={skip_seconds}s, interval={interval}s, window={window}, "
		f"bin={bin_width} Hz, gain={gain}x, min_mag={min_mag}"
	)
	print(f"WAV dump path: {dump_wav}")
	print("Press Ctrl+C to stop.")

	next_tick = time.monotonic()
	try:
		try:
			raw = capture_raw(device, rate, channels, capture_seconds)
		except RuntimeError as exc:
			print(f"Capture failed: {exc}")
			next_tick += interval
			time.sleep(max(0.0, next_tick - time.monotonic()))
			return 1

		skip_bytes = int(skip_seconds * rate) * channels * 4
		raw_trimmed = raw[skip_bytes:]

		try:
			write_wav(raw_trimmed, dump_wav, channels, rate)
		except Exception as exc:
			print(f"Failed to write WAV dump '{dump_wav}': {exc}")
		else:
			print(f"Saved capture to {dump_wav}")

		samples = extract_channel_int32(raw_trimmed, channels, data_channel)
		if not samples:
			print("No samples captured from selected data channel.")
			next_tick += interval
			time.sleep(max(0.0, next_tick - time.monotonic()))
			return 1

		peak_abs = max(abs(s) for s in samples)
		peak_db = 20 * math.log10(peak_abs) if peak_abs > 0.0 else float("-inf")
		print(f"Peak: {peak_abs:.6f}  ({peak_db:.1f} dBFS)")

		summary = summarize_fft(
			samples=samples,
			rate=rate,
			window_kind=window,
			bin_width_hz=bin_width,
			gain=gain,
		)
		print_fft_summary(summary, bin_width, min_mag)

		next_tick += interval
	except KeyboardInterrupt:
		print("\nStopped by user.")
		return 0

	return 0


if __name__ == "__main__":
	sys.exit(main())

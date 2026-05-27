#!/usr/bin/env python3
"""Record audio from an SPH0645 I2S microphone on Raspberry Pi.

This script uses ALSA's ``arecord`` command so it does not require extra
Python audio packages. It captures raw 32-bit PCM samples, writes them to a
WAV file, and prints a live level meter in dBFS.
"""

from __future__ import annotations

import argparse
import math
import shutil
import struct
import subprocess
import sys
import wave


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Record from SPH0645 I2S mic and save to WAV"
	)
	parser.add_argument(
		"-o",
		"--output",
		default="sph0645_recording.wav",
		help="Output WAV path (default: %(default)s)",
	)
	parser.add_argument(
		"-d",
		"--duration",
		type=float,
		default=5.0,
		help="Recording duration in seconds (default: %(default)s)",
	)
	parser.add_argument(
		"-r",
		"--rate",
		type=int,
		default=48_000,
		help="Sample rate in Hz (default: %(default)s)",
	)
	parser.add_argument(
		"-c",
		"--channels",
		type=int,
		default=1,
		help="Number of channels (default: %(default)s)",
	)
	parser.add_argument(
		"--device",
		default="plughw:1,0",
		help="ALSA capture device (default: %(default)s)",
	)
	parser.add_argument(
		"--list-devices",
		action="store_true",
		help="List ALSA capture devices via arecord -l and exit",
	)
	return parser.parse_args()


def rms_dbfs_int32_le(chunk: bytes) -> float:
	if len(chunk) < 4:
		return float("-inf")

	sample_count = len(chunk) // 4
	samples = struct.unpack("<" + "i" * sample_count, chunk[: sample_count * 4])
	if not samples:
		return float("-inf")

	sum_sq = 0.0
	for s in samples:
		v = float(s)
		sum_sq += v * v

	rms = math.sqrt(sum_sq / len(samples))
	if rms <= 0.0:
		return float("-inf")

	# int32 full scale reference
	return 20.0 * math.log10(rms / 2147483648.0)


def list_devices() -> int:
	try:
		result = subprocess.run(["arecord", "-l"], check=False)
	except FileNotFoundError:
		print("Error: 'arecord' not found. Install ALSA utils: sudo apt install alsa-utils")
		return 1
	return result.returncode


def main() -> int:
	args = parse_args()

	if args.list_devices:
		return list_devices()

	if shutil.which("arecord") is None:
		print("Error: 'arecord' not found. Install ALSA utils: sudo apt install alsa-utils")
		return 1

	if args.duration <= 0:
		print("Error: --duration must be > 0")
		return 1
	if args.rate <= 0:
		print("Error: --rate must be > 0")
		return 1
	if args.channels <= 0:
		print("Error: --channels must be > 0")
		return 1

	chunk_frames = 1024
	bytes_per_sample = 4  # S32_LE
	chunk_bytes = chunk_frames * args.channels * bytes_per_sample
	total_frames_target = int(args.duration * args.rate)
	total_bytes_target = total_frames_target * args.channels * bytes_per_sample

	cmd = [
		"arecord",
		"-D",
		args.device,
		"-f",
		"S32_LE",
		"-c",
		str(args.channels),
		"-r",
		str(args.rate),
		"-t",
		"raw",
		"-q",
	]

	print(f"Recording {args.duration:.2f}s from {args.device} at {args.rate} Hz...")
	print(f"Saving to: {args.output}")

	with wave.open(args.output, "wb") as wav_file:
		wav_file.setnchannels(args.channels)
		wav_file.setsampwidth(bytes_per_sample)
		wav_file.setframerate(args.rate)

		try:
			proc = subprocess.Popen(
				cmd,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
			)
		except FileNotFoundError:
			print("Error: Failed to start 'arecord'.")
			return 1

		captured = 0
		try:
			while captured < total_bytes_target:
				to_read = min(chunk_bytes, total_bytes_target - captured)
				chunk = proc.stdout.read(to_read) if proc.stdout else b""
				if not chunk:
					break

				wav_file.writeframesraw(chunk)
				captured += len(chunk)

				db = rms_dbfs_int32_le(chunk)
				meter = "-inf" if math.isinf(db) else f"{db:6.1f} dBFS"
				print(f"\rLevel: {meter}", end="", flush=True)

		finally:
			proc.terminate()
			try:
				proc.wait(timeout=1.5)
			except subprocess.TimeoutExpired:
				proc.kill()
				proc.wait(timeout=1.5)

			if proc.stderr:
				err = proc.stderr.read().decode("utf-8", errors="replace").strip()
				if err:
					print(f"\nALSA message: {err}")

	print()

	if captured == 0:
		print("No audio data captured. Check I2S overlay, wiring, and --device value.")
		print("Tip: run with --list-devices to discover the correct ALSA input.")
		return 2

	captured_seconds = captured / (args.channels * bytes_per_sample * args.rate)
	print(f"Done. Captured {captured_seconds:.2f} seconds.")
	return 0


if __name__ == "__main__":
	sys.exit(main())

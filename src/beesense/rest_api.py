"""Consumer REST API for the BeeSense Swagger definition."""

from __future__ import annotations

import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

BASE_URL = os.environ.get("BEESENSE_API_BASE_URL", "https://outsystems.phact.nl").rstrip("/")
API_BASE_PATH = "/BeeSense/rest/BeeSenseAPI"


def _post_to_consumer(path: str, params: dict[str, float | int]) -> tuple[object, int]:
    """Send a POST request to the remote BeeSense API."""
    print(f"Posting to {path} with params: {params}")
    url = f"{BASE_URL}{API_BASE_PATH}/{path}"
    response = requests.post(url, params=params, timeout=10)

    with app.app_context():
        return jsonify({"status": response.status_code, "text": response.text}), response.status_code


def send_inside_temp(temperature: float | None = None) -> tuple[object, int]:
    """Send inside temperature to the BeeSense API."""
    if temperature is None:
        temperature = request.args.get("Temperature", type=float)
    if temperature is None:
        return jsonify({"error": "Temperature is required."}), 400
    return _post_to_consumer("SendInsideTemp", {"Temperature": temperature})


@app.post("/BeeSense/rest/BeeSenseAPI/SendInsideTemp")
def send_inside_temp_route():
    """POST /SendInsideTemp consumer endpoint."""
    return send_inside_temp()


def send_outside_temp(temperature: float | None = None) -> tuple[object, int]:
    """Send outside temperature to the BeeSense API."""
    if temperature is None:
        temperature = request.args.get("Temperature", type=float)
    if temperature is None:
        return jsonify({"error": "Temperature is required."}), 400
    return _post_to_consumer("SendOutsideTemp", {"Temperature": temperature})


@app.post("/BeeSense/rest/BeeSenseAPI/SendOutsideTemp")
def send_outside_temp_route():
    """POST /SendOutsideTemp consumer endpoint."""
    return send_outside_temp()


def send_sound(value: float | None = None, bin_value: int | None = None) -> tuple[object, int]:
    """Send sound data to the BeeSense API."""
    if value is None:
        value = request.args.get("Value", type=float)
    if bin_value is None:
        bin_value = request.args.get("Bin", type=int)
    if value is None:
        return jsonify({"error": "Value is required."}), 400
    if bin_value is None:
        return jsonify({"error": "Bin is required."}), 400
    return _post_to_consumer("SendSound", {"Value": value, "Bin": bin_value})


@app.post("/BeeSense/rest/BeeSenseAPI/SendSound")
def send_sound_route():
    """POST /SendSound consumer endpoint."""
    return send_sound()


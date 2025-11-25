#!/usr/bin/env python3
"""
UniFi Wireless Assessment

Pulls client and AP data from the UniFi gateway/controller and summarizes:
- RSSI quality buckets for wireless clients
- Per-AP client counts
- Basic recommendations

Uses the existing secure Ubiquiti configuration from Settings:
- Host, API key from SecretsManager

Run:
  ./glassdome_start           # ensure session is active
  python scripts/wifi_assessment_unifi.py
"""

import sys
import os
import math
from collections import Counter, defaultdict
from statistics import mean
from typing import Dict, Any, List

import requests

# Add project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from glassdome.core.security import ensure_security_context, get_secure_settings


def get_ubiquiti_config() -> Dict[str, Any]:
    """Get Ubiquiti configuration from secure settings."""
    ensure_security_context()
    settings = get_secure_settings()
    return settings.get_ubiquiti_config()


def get_unifi_data() -> Dict[str, Any]:
    """Fetch clients and device (AP) data from UniFi API."""
    config = get_ubiquiti_config()
    base_url = f"https://{config.get('host', '192.168.2.1')}"
    api_key = config.get("api_key", "")
    site_id = "default"

    if not api_key:
        raise RuntimeError("Ubiquiti API key not configured in secrets store.")

    session = requests.Session()
    session.verify = False  # Lab environment; accept self-signed

    headers = {
        "X-API-KEY": api_key,
        "Accept": "application/json",
    }

    result: Dict[str, Any] = {"clients": [], "devices": []}

    # Clients (wireless stations)
    resp_clients = session.get(
        f"{base_url}/proxy/network/api/s/{site_id}/stat/sta",
        headers=headers,
        timeout=10,
    )
    if resp_clients.status_code == 200:
        data = resp_clients.json()
        result["clients"] = data.get("data", [])
    else:
        print(f"⚠️  Failed to fetch clients: {resp_clients.status_code} {resp_clients.text[:120]}")

    # Devices (APs, switches, etc.)
    resp_devices = session.get(
        f"{base_url}/proxy/network/api/s/{site_id}/stat/device",
        headers=headers,
        timeout=10,
    )
    if resp_devices.status_code == 200:
        data = resp_devices.json()
        result["devices"] = data.get("data", [])
    else:
        print(f"⚠️  Failed to fetch devices: {resp_devices.status_code} {resp_devices.text[:120]}")

    return result


def bucket_rssi(rssi: int) -> str:
    """Bucket RSSI into quality ranges."""
    if rssi >= -60:
        return "excellent (>= -60 dBm)"
    if -67 <= rssi < -60:
        return "good (-67 to -60 dBm)"
    if -72 <= rssi < -67:
        return "fair (-72 to -67 dBm)"
    if -80 <= rssi < -72:
        return "poor (-80 to -72 dBm)"
    return "very poor (< -80 dBm)"


def assess_wireless(clients: List[Dict[str, Any]], devices: List[Dict[str, Any]]) -> None:
    print("=" * 70)
    print("UNI FI WIRELESS ASSESSMENT")
    print("=" * 70)
    print()

    # Filter to wireless clients only
    wifi_clients = [c for c in clients if c.get("is_wired") is False or "is_wired" not in c]

    if not wifi_clients:
        print("No wireless clients reported by controller.")
        return

    # RSSI distribution
    rssi_values = [c.get("signal") for c in wifi_clients if isinstance(c.get("signal"), (int, float))]
    buckets = Counter(bucket_rssi(r) for r in rssi_values)

    print("Client RSSI distribution (based on UniFi 'signal' field):")
    total = len(rssi_values)
    for bucket_name in [
        "excellent (>= -60 dBm)",
        "good (-67 to -60 dBm)",
        "fair (-72 to -67 dBm)",
        "poor (-80 to -72 dBm)",
        "very poor (< -80 dBm)",
    ]:
        count = buckets.get(bucket_name, 0)
        pct = (count / total * 100) if total else 0
        print(f"  {bucket_name:26}: {count:3} clients ({pct:5.1f}%)")

    if total:
        avg_rssi = mean(rssi_values)
        worst_rssi = min(rssi_values)
        best_rssi = max(rssi_values)
        print()
        print(f"Average RSSI: {avg_rssi:.1f} dBm  (best: {best_rssi} dBm, worst: {worst_rssi} dBm)")

    # Per-AP client counts
    ap_clients: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in wifi_clients:
        ap_mac = c.get("ap_mac") or c.get("bssid")
        if ap_mac:
            ap_clients[ap_mac].append(c)

    # Map AP MAC -> device info
    ap_info: Dict[str, Dict[str, Any]] = {}
    for d in devices:
        if d.get("type") in ("uap", "usw", "udm", "udm-pro") or d.get("model", "").startswith("U7"):
            mac = d.get("mac")
            if mac:
                ap_info[mac] = d

    print()
    print("Per-AP client counts:")
    for ap_mac, clist in sorted(ap_clients.items(), key=lambda x: len(x[1]), reverse=True):
        dev = ap_info.get(ap_mac, {})
        name = dev.get("name") or dev.get("hostname") or ap_mac
        num = len(clist)
        # Simple flag: > 25 is starting to be heavy
        flag = "" if num <= 25 else "  (HEAVY LOAD)" if num <= 40 else "  (OVERLOADED)"
        print(f"  {name:24} [{ap_mac}] : {num:3} clients{flag}")

    print()
    print("Worst 10 clients by RSSI (lowest signal):")
    worst_clients = sorted(
        [c for c in wifi_clients if isinstance(c.get("signal"), (int, float))],
        key=lambda c: c.get("signal"),
    )[:10]

    for c in worst_clients:
        hostname = c.get("hostname") or c.get("name") or c.get("mac")
        rssi = c.get("signal")
        ap_mac = c.get("ap_mac") or c.get("bssid")
        bucket = bucket_rssi(rssi)
        print(f"  {hostname:24} RSSI={rssi:4} dBm  ({bucket}), AP={ap_mac}")

    # Simple recommendations
    print()
    print("Recommendations:")

    # Coverage
    poor_or_worse = sum(1 for r in rssi_values if r < -72)
    if total and (poor_or_worse / total) > 0.15:
        print("  - More than 15% of clients are below -72 dBm → consider adding APs or adjusting placement.")
    else:
        print("  - RSSI coverage looks generally acceptable (most clients above -72 dBm).")

    # AP load
    heavy_aps = [ap for ap, clist in ap_clients.items() if len(clist) > 25]
    if heavy_aps:
        print("  - Some APs have >25 clients → consider load balancing or additional APs.")
    else:
        print("  - AP client counts look reasonable (<25 clients per AP).")

    # Edge clients
    if worst_clients and worst_clients[0].get("signal", 0) < -80:
        print("  - At least one client is below -80 dBm → likely at the very edge of coverage; investigate location.")
    else:
        print("  - No clients below -80 dBm reported.")


def main() -> int:
    try:
        data = get_unifi_data()
    except Exception as e:
        print(f"❌ Failed to pull data from UniFi API: {e}")
        return 1

    clients = data.get("clients", [])
    devices = data.get("devices", [])

    assess_wireless(clients, devices)

    return 0


if __name__ == "__main__":
    sys.exit(main())

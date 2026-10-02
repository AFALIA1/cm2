from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

import psutil

RTSP_PORT = 554
MAX_HOSTS_SAFETY_CAP = 1024  # refuse to scan anything bigger than a /22


def local_ipv4_networks() -> list[ipaddress.IPv4Network]:
    networks = []
    for addrs in psutil.net_if_addrs().values():
        for addr in addrs:
            if addr.family != socket.AF_INET or not addr.address or not addr.netmask:
                continue
            if addr.address.startswith("127."):
                continue
            try:
                net = ipaddress.ip_network(f"{addr.address}/{addr.netmask}", strict=False)
            except ValueError:
                continue
            networks.append(net)
    return networks


def _probe(ip: str, timeout: float) -> bool:
    try:
        with socket.create_connection((ip, RTSP_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def scan_subnet_for_rtsp(network: ipaddress.IPv4Network, timeout: float = 0.5, max_workers: int = 64) -> list[str]:
    hosts = list(network.hosts())
    if len(hosts) > MAX_HOSTS_SAFETY_CAP:
        raise ValueError(
            f"{network} has {len(hosts)} hosts — refusing to scan more than "
            f"{MAX_HOSTS_SAFETY_CAP}; pass a narrower subnet"
        )
    found: list[str] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_probe, str(ip), timeout): str(ip) for ip in hosts}
        for future in as_completed(futures):
            ip = futures[future]
            if future.result():
                found.append(ip)
    return sorted(found, key=lambda ip: tuple(int(p) for p in ip.split(".")))

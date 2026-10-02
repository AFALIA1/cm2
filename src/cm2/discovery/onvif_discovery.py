from __future__ import annotations

import socket
import uuid
from dataclasses import dataclass
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

MCAST_GROUP = "239.255.255.250"
MCAST_PORT = 3702

NS = {
    "e": "http://www.w3.org/2003/05/soap-envelope",
    "w": "http://schemas.xmlsoap.org/ws/2004/08/addressing",
    "d": "http://schemas.xmlsoap.org/ws/2005/04/discovery",
}

PROBE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <e:Header>
    <w:MessageID>uuid:{message_id}</w:MessageID>
    <w:To e:mustUnderstand="1">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action e:mustUnderstand="1">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body>
    <d:Probe>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </e:Body>
</e:Envelope>"""


@dataclass
class OnvifDevice:
    ip: str
    xaddr: str
    name: str


def _friendly_name(scopes_text: str) -> str:
    for scope in scopes_text.split():
        if "/name/" in scope:
            return unquote(scope.split("/name/", 1)[1])
    return "ONVIF device"


def _parse_probe_match(data: bytes, source_ip: str) -> OnvifDevice | None:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return None
    xaddrs_el = root.find(".//d:ProbeMatch/d:XAddrs", NS)
    if xaddrs_el is None or not xaddrs_el.text:
        return None
    xaddr = xaddrs_el.text.split()[0]
    scopes_el = root.find(".//d:ProbeMatch/d:Scopes", NS)
    name = _friendly_name(scopes_el.text) if scopes_el is not None and scopes_el.text else "ONVIF device"
    return OnvifDevice(ip=source_ip, xaddr=xaddr, name=name)


def discover(timeout: float = 4.0) -> list[OnvifDevice]:
    message = PROBE_TEMPLATE.format(message_id=uuid.uuid4())
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
    sock.settimeout(timeout)
    devices: dict[str, OnvifDevice] = {}
    try:
        sock.sendto(message.encode("utf-8"), (MCAST_GROUP, MCAST_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(65535)
            except socket.timeout:
                break
            device = _parse_probe_match(data, addr[0])
            if device is not None:
                devices[device.ip] = device
    finally:
        sock.close()
    return list(devices.values())


def xaddr_host(xaddr: str) -> str:
    return urlparse(xaddr).hostname or ""


def xaddr_port(xaddr: str, default: int = 80) -> int:
    return urlparse(xaddr).port or default

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import quote, urlparse

from onvif import ONVIFCamera


@dataclass
class OnvifStreamInfo:
    device_name: str
    profile_name: str
    rtsp_url: str  # with credentials embedded, ready for ffmpeg/MediaMTX


async def _fetch_stream_info(ip: str, port: int, username: str, password: str) -> OnvifStreamInfo:
    camera = ONVIFCamera(ip, port, username, password)
    try:
        await camera.update_xaddrs()

        devicemgmt = await camera.create_devicemgmt_service()
        info = await devicemgmt.GetDeviceInformation()
        device_name = f"{info.Manufacturer} {info.Model}".strip() or "ONVIF camera"

        media = await camera.create_media_service()
        profiles = await media.GetProfiles()
        if not profiles:
            raise RuntimeError("camera reported no media profiles")
        profile = profiles[0]

        stream_setup = {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}}
        uri_response = await media.GetStreamUri(
            {"StreamSetup": stream_setup, "ProfileToken": profile.token}
        )
        raw_url = uri_response.Uri
    finally:
        await camera.close()

    rtsp_url = _inject_credentials(raw_url, username, password)
    return OnvifStreamInfo(device_name=device_name, profile_name=profile.Name, rtsp_url=rtsp_url)


def _inject_credentials(url: str, username: str, password: str) -> str:
    parsed = urlparse(url)
    if parsed.username:
        return url  # camera already embedded credentials in the URI
    netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return parsed._replace(netloc=netloc).geturl()


def fetch_stream_info(ip: str, port: int, username: str, password: str) -> OnvifStreamInfo:
    """Sync-facing adapter around onvif-zeep-async's asyncio API."""
    return asyncio.run(_fetch_stream_info(ip, port, username, password))

from __future__ import annotations

from urllib.parse import quote

import yaml

from . import storage

# {channel} is substituted as a plain integer; brands whose URL scheme needs
# zero-padding do it themselves via a format spec, e.g. {channel:02d}.
BUILTIN_BRANDS: dict[str, dict[str, str]] = {
    "generic_onvif": {
        "label": "Generic / ONVIF default",
        "template": "rtsp://{user}:{password}@{ip}:{port}/onvif1",
    },
    "hikvision": {
        "label": "Hikvision",
        "template": "rtsp://{user}:{password}@{ip}:{port}/Streaming/Channels/{channel}01",
    },
    "dahua": {
        "label": "Dahua",
        "template": "rtsp://{user}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=0",
    },
    "reolink": {
        "label": "Reolink",
        "template": "rtsp://{user}:{password}@{ip}:{port}/h264Preview_{channel:02d}_main",
    },
    "axis": {
        "label": "Axis",
        "template": "rtsp://{user}:{password}@{ip}:{port}/axis-media/media.amp?videocodec=h264",
    },
}

DEFAULT_RTSP_PORT = 554
DEFAULT_CHANNEL = 1


def seed_user_brands_file() -> None:
    if storage.BRANDS_FILE.exists():
        return
    storage.write_text(storage.BRANDS_FILE, yaml.safe_dump(BUILTIN_BRANDS, sort_keys=False))


def load_brands() -> dict[str, dict[str, str]]:
    seed_user_brands_file()
    merged = dict(BUILTIN_BRANDS)
    try:
        with open(storage.BRANDS_FILE) as f:
            user_brands = yaml.safe_load(f) or {}
        if isinstance(user_brands, dict):
            merged.update(user_brands)
    except (OSError, yaml.YAMLError):
        pass
    return merged


def build_rtsp_url(
    brand_key: str,
    ip: str,
    username: str,
    password: str,
    port: int = DEFAULT_RTSP_PORT,
    channel: int = DEFAULT_CHANNEL,
) -> str:
    brands = load_brands()
    if brand_key not in brands:
        raise KeyError(f"Unknown brand: {brand_key}")
    template = brands[brand_key]["template"]
    return template.format(
        user=quote(username, safe=""),
        password=quote(password, safe=""),
        ip=ip,
        port=port,
        channel=channel,
    )

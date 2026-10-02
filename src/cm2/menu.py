from __future__ import annotations

import ipaddress

import questionary

from . import brands as brands_module
from . import onvif_client, storage, testing, ui
from .discovery import onvif_discovery, rtsp_portscan, webcam
from .models import Camera, new_id
from .streaming import manager, ports

PROTOCOL_CHOICES = {
    "M3U8": ("hls", "M3U8"),
    "any http": ("mjpeg", "HTTP"),
}

MANUAL_ENTRY = "+ Enter camera manually (RTSP/ONVIF)"
RESCAN = "(rescan)"
BACK = "<- Back"


def _select(message: str, choices: list[str]) -> str | None:
    """Every select gets an explicit back choice; Esc/Ctrl-C also means back."""
    picked = questionary.select(message, choices=[BACK] + choices).ask()
    if picked in (None, BACK):
        return None
    return picked


def _text(message: str, default: str | None = None) -> str | None:
    kwargs = {"default": default} if default is not None else {}
    return questionary.text(f"{message}  (Esc = back)", **kwargs).ask()


def _password(message: str) -> str | None:
    return questionary.password(f"{message}  (Esc = back)").ask()


def _load_cameras() -> list[Camera]:
    return [Camera.from_dict(d) for d in storage.load_json_list(storage.CAMERAS_FILE)]


def _save_camera(camera: Camera) -> None:
    with storage.locked():
        cameras = _load_cameras()
        cameras = [c for c in cameras if not (c.kind == camera.kind and c.address == camera.address and c.brand == camera.brand)]
        cameras.append(camera)
        storage.save_json_list(storage.CAMERAS_FILE, [c.to_dict() for c in cameras])


def run_scan() -> list[dict]:
    ui.info("Scanning for webcams...")
    webcams = webcam.scan_webcams()
    ui.info("Scanning network for ONVIF cameras (WS-Discovery, ~4s)...")
    onvif_devices = onvif_discovery.discover()

    candidates: list[dict] = []
    for cam in webcams:
        candidates.append({"kind": "webcam", "name": cam.name, "address": cam.path})
    for dev in onvif_devices:
        candidates.append({
            "kind": "onvif", "name": dev.name, "address": dev.ip,
            "port": onvif_discovery.xaddr_port(dev.xaddr, default=80),
        })

    if questionary.confirm("Also scan the local subnet for plain RTSP cameras? (slower)", default=False).ask():
        found_any = False
        for network in rtsp_portscan.local_ipv4_networks():
            ui.info(f"Scanning {network} for RTSP (port 554)...")
            try:
                hits = rtsp_portscan.scan_subnet_for_rtsp(network)
            except ValueError as exc:
                ui.error(str(exc))
                continue
            for ip in hits:
                if any(c["address"] == ip for c in candidates):
                    continue
                candidates.append({"kind": "rtsp", "name": f"RTSP camera ({ip})", "address": ip, "port": 554})
                found_any = True
        if not found_any:
            ui.info("No additional RTSP cameras found on the local subnet.")

    return candidates


def _choose_candidate(candidates: list[dict]) -> dict | None:
    choice_labels = [f"[{c['kind'].upper()}] {c['name']} ({c['address']})" for c in candidates]
    choice_labels += [MANUAL_ENTRY, RESCAN]
    if not candidates:
        ui.info("No cameras found — you can still enter one manually.")
    while True:
        picked = _select("Choose a camera:", choice_labels)
        if picked is None:
            return None
        if picked == RESCAN:
            return {"_rescan": True}
        if picked == MANUAL_ENTRY:
            ip = _text("Camera IP address:")
            if ip is None:
                continue  # back to the candidate list
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                ui.error("Not a valid IP address.")
                continue
            return {"kind": "rtsp", "name": f"Camera ({ip})", "address": ip, "port": 554}
        index = choice_labels.index(picked)
        return candidates[index]


def _test_camera(camera: Camera) -> bool:
    ui.info("Testing connection...")
    if camera.kind == "webcam":
        result = testing.test_webcam(camera.address)
    else:
        result = testing.test_rtsp(camera.rtsp_url)
    if result.success:
        ui.success(result.message)
        return True
    ui.error(result.message)
    return False


def scan_flow() -> None:
    """A step state-machine: every prompt can go back to the one before it
    (Esc, Ctrl-C, or the explicit "<- Back" choice all mean the same thing)."""
    candidates = run_scan()
    step = "candidate"
    data: dict = {}

    while True:
        if step == "candidate":
            candidate = _choose_candidate(candidates)
            if candidate is None:
                return
            if candidate.get("_rescan"):
                candidates = run_scan()
                continue
            data = {"candidate": candidate}
            step = "webcam_camera" if candidate["kind"] == "webcam" else "username"
            continue

        if step == "webcam_camera":
            c = data["candidate"]
            data["camera"] = Camera(id=new_id(), kind="webcam", name=c["name"], address=c["address"])
            data["_before_test"] = "candidate"
            step = "test"
            continue

        if step == "username":
            username = _text("Username:")
            if username is None:
                step = "candidate"
                continue
            data["username"] = username
            step = "password"
            continue

        if step == "password":
            password = _password("Password:")
            if password is None:
                step = "username"
                continue
            data["password"] = password
            step = "brand"
            continue

        if step == "brand":
            catalog = brands_module.load_brands()
            brand_choices = ["Auto (ONVIF discovery)"] + [b["label"] for b in catalog.values()]
            brand_keys = [None] + list(catalog.keys())
            picked = _select("Camera brand:", brand_choices)
            if picked is None:
                step = "password"
                continue
            data["brand_key"] = brand_keys[brand_choices.index(picked)]
            step = "onvif_port" if data["brand_key"] is None else "rtsp_port"
            continue

        if step == "onvif_port":
            onvif_port = _text("ONVIF port:", default=str(data["candidate"].get("port", 80)))
            if onvif_port is None:
                step = "brand"
                continue
            data["onvif_port"] = onvif_port
            ip = data["candidate"]["address"]
            try:
                info = onvif_client.fetch_stream_info(ip, int(onvif_port), data["username"], data["password"])
            except Exception as exc:  # ONVIF/SOAP/network failures are all "camera didn't cooperate"
                ui.error(f"ONVIF auto-detect failed: {exc}")
                continue  # stay on onvif_port so they can retry/adjust
            data["camera"] = Camera(
                id=new_id(), kind="onvif", name=info.device_name, address=ip,
                port=int(onvif_port), brand="auto",
                username=data["username"], password=data["password"], rtsp_url=info.rtsp_url,
            )
            data["_before_test"] = "onvif_port"
            step = "test"
            continue

        if step == "rtsp_port":
            rtsp_port = _text("RTSP port:", default=str(data["candidate"].get("port", brands_module.DEFAULT_RTSP_PORT)))
            if rtsp_port is None:
                step = "brand"
                continue
            data["rtsp_port"] = rtsp_port
            step = "channel"
            continue

        if step == "channel":
            channel = _text("Channel number:", default=str(brands_module.DEFAULT_CHANNEL))
            if channel is None:
                step = "rtsp_port"
                continue
            data["channel"] = channel
            c = data["candidate"]
            ip = c["address"]
            try:
                rtsp_url = brands_module.build_rtsp_url(
                    data["brand_key"], ip, data["username"], data["password"],
                    port=int(data["rtsp_port"]), channel=int(channel),
                )
            except (KeyError, ValueError) as exc:
                ui.error(f"Could not build RTSP URL: {exc}")
                continue  # stay on channel so they can retry/adjust
            data["camera"] = Camera(
                id=new_id(), kind=c["kind"], name=c["name"], address=ip,
                port=int(data["rtsp_port"]), brand=data["brand_key"],
                username=data["username"], password=data["password"],
                channel=int(channel), rtsp_url=rtsp_url,
            )
            data["_before_test"] = "channel"
            step = "test"
            continue

        if step == "test":
            if _test_camera(data["camera"]):
                _save_camera(data["camera"])
                step = "protocol"
            else:
                step = data["_before_test"]
            continue

        if step == "protocol":
            protocol_label = _select("Stream protocol:", list(PROTOCOL_CHOICES.keys()))
            if protocol_label is None:
                step = data["_before_test"]
                continue
            data["protocol_label"] = protocol_label
            step = "port"
            continue

        if step == "port":
            port_text = _text("Port to run this stream on:")
            if port_text is None:
                step = "protocol"
                continue
            try:
                port = int(port_text)
            except ValueError:
                ui.error("Enter a numeric port.")
                continue
            if not ports.is_tcp_port_free(port):
                ui.error(f"Port {port} is already in use, choose another.")
                continue
            data["port"] = port
            step = "launch"
            continue

        if step == "launch":
            protocol, display_protocol = PROTOCOL_CHOICES[data["protocol_label"]]
            try:
                stream = manager.start_stream(data["camera"], protocol, display_protocol, data["port"])
            except Exception as exc:
                ui.error(f"Failed to start stream: {exc}")
                step = "port"
                continue
            extra = ""
            if stream.hls_time and stream.hls_time != manager.DEFAULT_HLS_TIME:
                extra = f" (segment length is {stream.hls_time}s, matched to this camera's own keyframe interval)"
            ui.done(f"stream '{stream.id}' is live at {stream.url}{extra}")
            step = "done"
            continue

        if step == "done":
            again = _select("What next?", ["Back to camera list", "End"])
            if again == "Back to camera list":
                step = "candidate"
                data = {}
                continue
            return


def status_flow() -> None:
    result = manager.reconcile()
    if not result.alive:
        ui.info("No streams are currently running.")
    else:
        rows = [
            {
                "id": s.id, "camera": s.camera_name, "protocol": s.display_protocol,
                "port": s.port, "status": manager.health(s), "url": s.url,
            }
            for s in result.alive
        ]
        ui.console.print(ui.streams_table(rows))
    if result.orphans:
        ui.error(
            f"Found {len(result.orphans)} orphaned ffmpeg process(es) whose worker is gone "
            f"(pids: {result.orphans}) — likely left over from a crash."
        )
        if questionary.confirm("Clean these up now?", default=True).ask():
            for pid in result.orphans:
                manager.kill_orphan(pid)
            ui.success("orphaned ffmpeg processes stopped.")


def stop_flow(stream_id: str | None = None) -> None:
    streams = manager.load_streams()
    if not streams:
        ui.info("No streams are currently running.")
        return
    if stream_id is None:
        labels = [f"{s.id}  {s.camera_name}  {s.display_protocol}:{s.port}" for s in streams]
        picked = _select("Stop which stream?", labels)
        if picked is None:
            return
        stream_id = streams[labels.index(picked)].id
    if manager.stop_stream(stream_id):
        ui.success(f"stream '{stream_id}' stopped.")
    else:
        ui.error(f"no stream with id '{stream_id}'.")


def main_menu() -> None:
    while True:
        choice = questionary.select(
            "cm2",
            choices=["Scan", "Status", "Stop a stream", "Exit"],
        ).ask()
        if choice in (None, "Exit"):
            return
        if choice == "Scan":
            scan_flow()
        elif choice == "Status":
            status_flow()
        elif choice == "Stop a stream":
            stop_flow()

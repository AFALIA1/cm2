from __future__ import annotations

from cm2 import brands


def test_build_rtsp_url_hikvision():
    url = brands.build_rtsp_url("hikvision", "192.168.1.10", "admin", "pa:ss", port=554, channel=2)
    assert url == "rtsp://admin:pa%3Ass@192.168.1.10:554/Streaming/Channels/201"


def test_build_rtsp_url_reolink_zero_pads_channel():
    url = brands.build_rtsp_url("reolink", "192.168.1.20", "user", "pass", channel=3)
    assert "h264Preview_03_main" in url


def test_build_rtsp_url_unknown_brand_raises():
    try:
        brands.build_rtsp_url("nope", "1.2.3.4", "u", "p")
    except KeyError:
        pass
    else:
        raise AssertionError("expected KeyError")


def test_load_brands_seeds_and_merges_user_file(isolated_home):
    catalog = brands.load_brands()
    assert "hikvision" in catalog
    assert (isolated_home / "brands.yaml").exists()

    (isolated_home / "brands.yaml").write_text(
        "custom_brand:\n  label: Custom\n  template: 'rtsp://{user}:{password}@{ip}/custom'\n"
    )
    catalog = brands.load_brands()
    assert "custom_brand" in catalog
    assert "hikvision" in catalog  # built-ins still present alongside user additions

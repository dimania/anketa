import importlib

import config


def test_proxy_settings_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("PROXY_SCHEME", "socks5h")
    monkeypatch.setenv("PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("PROXY_PORT", "1080")
    monkeypatch.setenv("USE_PROXY", "yes")

    loaded = importlib.reload(config)

    assert loaded.use_proxy is True
    assert loaded.proxies == {
        "http": "socks5h://127.0.0.1:1080",
        "https": "socks5h://127.0.0.1:1080",
    }


def test_proxy_can_be_disabled(monkeypatch):
    monkeypatch.setenv("USE_PROXY", "false")

    loaded = importlib.reload(config)

    assert loaded.use_proxy is False

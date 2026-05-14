from __future__ import annotations

import atexit
import logging
import os
import re
import shutil
import socket
import subprocess
import threading
from urllib import request as urlrequest
from urllib.parse import urlparse

from django.conf import settings

from apps.common.legacy import ensure_legacy_path

logger = logging.getLogger(__name__)

_BOOTSTRAPPED = False
_ACCESS_SERVER_THREAD: threading.Thread | None = None
_TUNNEL_PROCESS: subprocess.Popen | None = None


def bootstrap_runtime_services() -> None:
    """Start services that the web app needs immediately at launch."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    _BOOTSTRAPPED = True

    if getattr(settings, "ACCESS_SERVER_AUTOSTART", True):
        start_access_server()
    else:
        logger.info("ESP32/camera access server autostart disabled")

    if getattr(settings, "ACCESS_APPROVAL_AUTOSTART", True):
        start_access_approval_tunnel()
    else:
        logger.info("Access approval tunnel autostart disabled")


def start_access_server() -> None:
    """Start access_server.py in a daemon thread, unless its port is already used."""
    global _ACCESS_SERVER_THREAD

    host = os.getenv("ACCESS_SERVER_HOST", "0.0.0.0").strip() or "0.0.0.0"
    port = _int_env("ESP32_PORT", 5050)
    probe_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host

    if _is_port_open(probe_host, port):
        logger.info("ESP32/camera access server already listening on %s:%s", probe_host, port)
        return

    if _ACCESS_SERVER_THREAD and _ACCESS_SERVER_THREAD.is_alive():
        return

    _ACCESS_SERVER_THREAD = threading.Thread(
        target=_run_access_server,
        kwargs={"host": host, "port": port},
        name="uor-access-server",
        daemon=True,
    )
    _ACCESS_SERVER_THREAD.start()
    logger.info("ESP32/camera access server startup requested on %s:%s", host, port)


def start_access_approval_tunnel() -> None:
    """Expose the web backend for email approve/reject links."""
    if not getattr(settings, "ACCESS_APPROVAL_TUNNEL_AUTOSTART", True):
        _sync_access_approval_base_url(getattr(settings, "ACCESS_APPROVAL_BASE_URL", ""))
        logger.info("Access approval public tunnel disabled")
        return

    provider = getattr(settings, "ACCESS_APPROVAL_TUNNEL_PROVIDER", "localtunnel")
    base_url = _sync_access_approval_base_url(getattr(settings, "ACCESS_APPROVAL_BASE_URL", ""))

    base_host = (urlparse(base_url).hostname or "").lower()
    if base_url and provider == "localtunnel" and "loca.lt" not in base_host:
        logger.info("Access approval base URL configured externally: %s", base_url)
        return

    if provider != "localtunnel":
        logger.warning("Unsupported access approval tunnel provider: %s", provider)
        return

    if base_url and _public_backend_healthy(base_url):
        logger.info("Access approval public URL already responds: %s", base_url)
        return

    _start_localtunnel(base_url=base_url)


def _run_access_server(*, host: str, port: int) -> None:
    try:
        ensure_legacy_path()
        from access_server import run_server

        run_server(host=host, port=port)
    except OSError as exc:
        logger.warning("Unable to start ESP32/camera access server on %s:%s: %s", host, port, exc)
    except Exception:
        logger.exception("Unexpected error while starting ESP32/camera access server")


def _start_localtunnel(*, base_url: str) -> None:
    global _TUNNEL_PROCESS

    if _TUNNEL_PROCESS and _TUNNEL_PROCESS.poll() is None:
        return

    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if not npx:
        logger.warning("npx was not found; access approval public tunnel cannot start")
        return

    port = int(getattr(settings, "ACCESS_APPROVAL_TUNNEL_PORT", 8000) or 8000)
    host = getattr(settings, "ACCESS_APPROVAL_TUNNEL_HOST", "127.0.0.1") or "127.0.0.1"
    subdomain = getattr(settings, "ACCESS_APPROVAL_TUNNEL_SUBDOMAIN", "") or _localtunnel_subdomain(base_url)

    if subdomain and not base_url:
        _sync_access_approval_base_url(f"https://{subdomain}.loca.lt")

    cmd = [npx, "--yes", "localtunnel", "--port", str(port), "--local-host", host]
    if subdomain:
        cmd.extend(["--subdomain", subdomain])

    try:
        _TUNNEL_PROCESS = subprocess.Popen(
            cmd,
            cwd=str(settings.MIGRATION_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        logger.exception("Unable to start localtunnel for access approval links")
        return

    atexit.register(_stop_tunnel_process)
    threading.Thread(
        target=_watch_localtunnel_output,
        args=(_TUNNEL_PROCESS,),
        name="uor-access-approval-tunnel",
        daemon=True,
    ).start()
    logger.info("Access approval public tunnel startup requested for backend port %s", port)


def _watch_localtunnel_output(process: subprocess.Popen) -> None:
    stream = process.stdout
    if not stream:
        return

    for line in stream:
        message = line.strip()
        if not message:
            continue

        match = re.search(r"https?://[^\s]+", message)
        if match and ("your url is" in message.lower() or "loca.lt" in message.lower()):
            public_url = match.group(0).rstrip("/")
            _sync_access_approval_base_url(public_url)
            logger.info("Access approval public URL ready: %s", public_url)
        else:
            logger.info("localtunnel: %s", message)


def _sync_access_approval_base_url(value: str) -> str:
    base_url = (value or os.getenv("ACCESS_APPROVAL_BASE_URL", "") or "").strip().rstrip("/")
    if not base_url:
        return ""

    os.environ["ACCESS_APPROVAL_BASE_URL"] = base_url
    try:
        setattr(settings, "ACCESS_APPROVAL_BASE_URL", base_url)
    except Exception:
        pass

    for module_name in ("config.settings", "app.services.auth.authentication_service"):
        try:
            module = __import__(module_name, fromlist=["ACCESS_APPROVAL_BASE_URL"])
            setattr(module, "ACCESS_APPROVAL_BASE_URL", base_url)
        except Exception:
            pass

    return base_url


def _localtunnel_subdomain(base_url: str) -> str:
    parsed = urlparse(base_url or "")
    host = (parsed.hostname or "").lower()
    if host.endswith(".loca.lt"):
        return host[: -len(".loca.lt")]
    return ""


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _public_backend_healthy(base_url: str) -> bool:
    try:
        with urlrequest.urlopen(f"{base_url.rstrip('/')}/api/health/", timeout=3) as response:
            return 200 <= int(response.status) < 300
    except Exception:
        return False


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _stop_tunnel_process() -> None:
    process = _TUNNEL_PROCESS
    if process and process.poll() is None:
        process.terminate()

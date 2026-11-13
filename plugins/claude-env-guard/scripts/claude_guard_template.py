#!/usr/bin/env python3
"""
Cross-Platform Claude Environment Guard (Windows / macOS / Linux)
- Automatically inspects Clash / Clash Verge Rev runtime config (HTTP API or Windows Named Pipe)
- Locks the dedicated proxy group ("🔒 Claude-固定出口") and fallback group to the target node
- Verifies outbound IP, country, ASN, and timezone via https://ipinfo.io/json (blocks CN/HK/MO)
- Syncs process-level TZ, proxy env vars, and non-destructive ~/.claude / CLAUDE_CONFIG_DIR privacy settings
- Launches isolated Chrome (--user-data-dir + WebRTC leak protection) or guarded Claude Code CLI with
  OAuth / link browser isolation (via adjacent claude-browser-opener.exe on Windows or .sh on POSIX)
"""

import argparse
from datetime import datetime
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ================= AGENT-CUSTOMIZABLE DEFAULTS =================
DEFAULT_PROXY_PORT = None          # Auto-detected from Clash config if None (fallback: 7897)
CLASH_CONTROLLER = None            # Auto-detected from Clash config if None (e.g. "127.0.0.1:9097")
CLASH_PIPE = None                  # Windows Named Pipe override if needed
CLASH_SECRET = None                # Auto-detected from Clash config if None
CLAUDE_GROUP_NAME = "🔒 Claude-固定出口"
FALLBACK_GROUP_NAME = "🚀 节点选择"
DEFAULT_TARGET_NODE = ""           # Set to user's preferred node name
TELEMETRY_MODE = "strict"          # "strict" or "balanced"
DEFAULT_CHROME_PROFILE_DIR = None  # Override isolated Chrome profile dir if desired
# ===============================================================

BANNED_COUNTRIES = {"CN", "HK", "MO"}

IANA_TO_WIN_TZ = {
    "America/Los_Angeles": "Pacific Standard Time",
    "America/Denver": "Mountain Standard Time",
    "America/Chicago": "Central Standard Time",
    "America/New_York": "Eastern Standard Time",
    "America/Toronto": "Eastern Standard Time",
    "America/Vancouver": "Pacific Standard Time",
    "Europe/London": "GMT Standard Time",
    "Europe/Berlin": "W. Europe Standard Time",
    "Europe/Amsterdam": "W. Europe Standard Time",
    "Europe/Paris": "Romance Standard Time",
    "Asia/Tokyo": "Tokyo Standard Time",
    "Asia/Seoul": "Korea Standard Time",
    "Asia/Singapore": "Singapore Standard Time",
    "Asia/Taipei": "Taipei Standard Time",
    "Asia/Shanghai": "China Standard Time",
    "Asia/Hong_Kong": "China Standard Time",
    "Australia/Sydney": "AUS Eastern Standard Time",
    "UTC": "UTC",
}

WIN_TO_IANA_TZ = {
    "Pacific Standard Time": "America/Los_Angeles",
    "Mountain Standard Time": "America/Denver",
    "Central Standard Time": "America/Chicago",
    "Eastern Standard Time": "America/New_York",
    "GMT Standard Time": "Europe/London",
    "W. Europe Standard Time": "Europe/Berlin",
    "Romance Standard Time": "Europe/Paris",
    "Tokyo Standard Time": "Asia/Tokyo",
    "Korea Standard Time": "Asia/Seoul",
    "Singapore Standard Time": "Asia/Singapore",
    "Taipei Standard Time": "Asia/Taipei",
    "China Standard Time": "Asia/Shanghai",
    "AUS Eastern Standard Time": "Australia/Sydney",
    "UTC": "UTC",
}

STRICT_ENV_VARS = {
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_TELEMETRY": "1",
    "DISABLE_ERROR_REPORTING": "1",
    "DISABLE_FEEDBACK_COMMAND": "1",
    "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
    "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
}

BALANCED_REMOVED_VARS = (
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC",
    "DISABLE_TELEMETRY",
)

ACCOUNT_JSON_KEYS = (
    "oauthAccount",
    "userID",
    "machineID",
    "claudeCodeFirstTokenDate",
    "cachedGrowthBookFeatures",
    "cachedGrowthBookFeaturesAt",
    "cachedExperimentData",
    "cachedExperimentFeatures",
    "cachedExtraUsageDisabledReason",
    "groveConfigCache",
    "passesEligibilityCache",
    "fableOverageConsentV2",
    "hasAvailableSubscription",
    "subscriptionNoticeCount",
    "penguinModeOrgEnabled",
    "claudeAiMcpEverConnected",
)

PRESERVED_MEMORY_ENTRIES = (
    "projects/",
    "history.jsonl",
    "file-history/",
    "paste-cache/",
    "plans/",
    "todos/",
    "CLAUDE.md",
    "settings.json",
    "hooks/",
    "skills/",
    "agents/",
    "plugins/",
)


def configure_stdio() -> None:
    """Force UTF-8 stdout/stderr so emojis and non-ASCII node names never fail on Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def get_clash_config_candidates() -> list[Path]:
    system = platform.system()
    home = Path.home()
    if system == "Darwin":
        candidates = [
            home / "Library/Application Support/io.github.clash-verge-rev.clash-verge-rev",
            home / ".config/clash-verge",
            home / ".config/mihomo",
            home / ".config/clash",
        ]
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", home / "AppData/Roaming"))
        candidates = [
            appdata / "io.github.clash-verge-rev.clash-verge-rev",
            home / ".config/clash-verge",
            home / ".config/mihomo",
            home / ".config/clash",
        ]
    else:
        candidates = [
            home / ".local/share/io.github.clash-verge-rev.clash-verge-rev",
            home / ".config/clash-verge",
            home / ".config/mihomo",
            home / ".config/clash",
        ]
    return [c for c in candidates if c.exists()]


def parse_simple_yaml_value(text: str, key: str) -> str | None:
    pattern = rf"^\s*{re.escape(key)}\s*:\s*([^\r\n#]*)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return None
    raw = match.group(1).strip()
    if raw in ("''", '""', "null", "~", ""):
        return ""
    return raw.strip("'\"")


def read_yaml_header(path: Path, max_lines: int = 80) -> str:
    """Read header lines before large proxies/rules sections for fast metadata parsing."""
    if not path.exists():
        return ""
    lines = []
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for idx, line in enumerate(fh):
            if idx >= max_lines or line.startswith("proxies:"):
                break
            lines.append(line)
    return "".join(lines)


def detect_clash_runtime() -> dict:
    info = {
        "mixed_port": DEFAULT_PROXY_PORT or 7897,
        "controller": CLASH_CONTROLLER,
        "http_controller_enabled": bool(CLASH_CONTROLLER),
        "pipe": CLASH_PIPE if platform.system() == "Windows" else None,
        "secret": CLASH_SECRET or "",
        "config_dir": None,
    }
    for cfg_dir in get_clash_config_candidates():
        info["config_dir"] = str(cfg_dir)
        runtime_header = read_yaml_header(cfg_dir / "clash-verge.yaml", max_lines=60)
        verge_text = (cfg_dir / "verge.yaml").read_text(encoding="utf-8", errors="ignore") if (cfg_dir / "verge.yaml").exists() else ""
        config_text = read_yaml_header(cfg_dir / "config.yaml", max_lines=60)

        if DEFAULT_PROXY_PORT is None:
            for src, key in (
                (runtime_header, "mixed-port"),
                (verge_text, "verge_mixed_port"),
                (config_text, "mixed-port"),
                (config_text, "port"),
            ):
                val = parse_simple_yaml_value(src, key)
                if val and val.isdigit():
                    info["mixed_port"] = int(val)
                    break

        if CLASH_CONTROLLER is None:
            enable_ext = parse_simple_yaml_value(verge_text, "enable_external_controller")
            live_ctrl = parse_simple_yaml_value(runtime_header, "external-controller")
            tmpl_ctrl = parse_simple_yaml_value(config_text, "external-controller")
            if live_ctrl:
                info["controller"] = live_ctrl
                info["http_controller_enabled"] = True
            elif enable_ext == "true" and tmpl_ctrl:
                info["controller"] = tmpl_ctrl
                info["http_controller_enabled"] = True
            elif tmpl_ctrl and not (cfg_dir / "verge.yaml").exists():
                # Non-Clash-Verge Mihomo / Clash configs use config.yaml directly
                info["controller"] = tmpl_ctrl
                info["http_controller_enabled"] = True
            else:
                info["controller"] = tmpl_ctrl
                info["http_controller_enabled"] = False

        if CLASH_PIPE is None and platform.system() == "Windows":
            live_pipe = parse_simple_yaml_value(runtime_header, "external-controller-pipe") or parse_simple_yaml_value(
                config_text, "external-controller-pipe"
            )
            if live_pipe:
                info["pipe"] = live_pipe

        if CLASH_SECRET is None:
            sec = parse_simple_yaml_value(runtime_header, "secret")
            if sec is None:
                sec = parse_simple_yaml_value(config_text, "secret")
            if sec is not None:
                info["secret"] = sec
        break
    return info


def _decode_chunked_body(raw: bytes) -> bytes:
    out = bytearray()
    idx = 0
    length = len(raw)
    while idx < length:
        line_end = raw.find(b"\r\n", idx)
        if line_end == -1:
            break
        size_token = raw[idx:line_end].split(b";", 1)[0].strip()
        if not size_token:
            idx = line_end + 2
            continue
        chunk_size = int(size_token, 16)
        idx = line_end + 2
        if chunk_size == 0:
            break
        out.extend(raw[idx : idx + chunk_size])
        idx += chunk_size + 2
    return bytes(out)


def _read_exact_http_response(fp) -> tuple[int, dict[str, str], bytes]:
    buf = bytearray()
    header_end = -1
    while header_end == -1:
        chunk = fp.read(4096)
        if not chunk:
            break
        buf.extend(chunk)
        header_end = buf.find(b"\r\n\r\n")

    if header_end == -1:
        raise RuntimeError("Clash Named Pipe 返回了不完整的 HTTP 响应头")

    header_block = bytes(buf[:header_end]).decode("utf-8", errors="replace")
    rest = bytearray(buf[header_end + 4 :])
    lines = header_block.split("\r\n")
    status_parts = lines[0].split(" ", 2)
    status_code = int(status_parts[1]) if len(status_parts) >= 2 and status_parts[1].isdigit() else 0

    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()

    if status_code in (204, 304):
        return status_code, headers, b""

    if "chunked" in headers.get("transfer-encoding", "").lower():
        while b"\r\n0\r\n\r\n" not in rest and not rest.startswith(b"0\r\n\r\n"):
            chunk = fp.read(4096)
            if not chunk:
                break
            rest.extend(chunk)
        return status_code, headers, _decode_chunked_body(bytes(rest))

    content_len = headers.get("content-length")
    if content_len and content_len.isdigit():
        target = int(content_len)
        while len(rest) < target:
            chunk = fp.read(target - len(rest))
            if not chunk:
                break
            rest.extend(chunk)
        return status_code, headers, bytes(rest[:target])

    while True:
        chunk = fp.read(4096)
        if not chunk:
            break
        rest.extend(chunk)
    return status_code, headers, bytes(rest)


def _request_named_pipe(pipe_path: str, method: str, req_path: str, secret: str, payload_obj: dict | None = None) -> tuple[int, bytes]:
    body_bytes = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8") if payload_obj is not None else b""
    req_lines = [
        f"{method} {req_path} HTTP/1.1",
        "Host: localhost",
        "Connection: close",
    ]
    if secret:
        req_lines.append(f"Authorization: Bearer {secret}")
    if payload_obj is not None:
        req_lines.append("Content-Type: application/json")
        req_lines.append(f"Content-Length: {len(body_bytes)}")
    raw_req = ("\r\n".join(req_lines) + "\r\n\r\n").encode("utf-8") + body_bytes

    with open(pipe_path, "r+b", buffering=0) as fp:
        fp.write(raw_req)
        fp.flush()
        status_code, _, resp_body = _read_exact_http_response(fp)
    return status_code, resp_body


def _request_http_api(controller: str, method: str, req_path: str, secret: str, payload_obj: dict | None = None) -> tuple[int, bytes]:
    base = controller if controller.startswith("http") else f"http://{controller}"
    url = f"{base}{req_path}"
    body_bytes = json.dumps(payload_obj, ensure_ascii=False).encode("utf-8") if payload_obj is not None else None
    headers = {}
    if payload_obj is not None:
        headers["Content-Type"] = "application/json"
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as err:
        return err.code, err.read()


def clash_api_request(runtime: dict, method: str, req_path: str, payload_obj: dict | None = None) -> tuple[str | None, int, bytes]:
    errors = []
    pipe_path = runtime.get("pipe")
    secret = runtime.get("secret", "")
    if pipe_path and platform.system() == "Windows":
        try:
            code, body = _request_named_pipe(pipe_path, method, req_path, secret, payload_obj)
            if code == 401 and secret:
                code, body = _request_named_pipe(pipe_path, method, req_path, "", payload_obj)
            return "named-pipe", code, body
        except Exception as exc:
            errors.append(f"named-pipe ({exc})")

    if runtime.get("http_controller_enabled") and runtime.get("controller"):
        try:
            code, body = _request_http_api(runtime["controller"], method, req_path, secret, payload_obj)
            return f"http://{runtime['controller']}", code, body
        except Exception as exc:
            errors.append(f"http ({exc})")

    if errors:
        print(f"⚠️  无法连接 Clash 控制接口 [{'; '.join(errors)}]")
    else:
        print("⚠️  未检测到可用的 Clash Named Pipe 或已启用的 HTTP 控制端口。")
    return None, 0, b""


def set_and_verify_group_node(runtime: dict, group: str, node: str) -> tuple[bool, int, str]:
    encoded_group = urllib.parse.quote(group, safe="")
    via, put_code, _ = clash_api_request(runtime, "PUT", f"/proxies/{encoded_group}", {"name": node})
    if via is None:
        return False, 0, "unreachable"
    if put_code == 404:
        return False, 404, via
    if put_code not in (200, 204):
        return False, put_code, via

    _, get_code, get_body = clash_api_request(runtime, "GET", f"/proxies/{encoded_group}")
    if get_code == 200:
        try:
            current_now = json.loads(get_body.decode("utf-8")).get("now", "")
            return current_now == node, put_code, via
        except Exception:
            pass
    return True, put_code, via


def lock_clash_nodes(runtime: dict, group: str, fallback_group: str, node: str, lock_global: bool = True) -> None:
    if not node:
        return
    ok, code, via = set_and_verify_group_node(runtime, group, node)
    if ok:
        print(f"🔒 已通过 {via} 锁定策略组 [{group}] -> {node}")
    elif code == 404:
        print(f"⚠️  策略组 [{group}] 尚未在 Clash 核心生效 (请先在 Clash 客户端刷新/重载配置以应用覆写脚本)")
    else:
        print(f"⚠️  未能锁定策略组 [{group}] -> {node} (HTTP {code})")

    if lock_global and fallback_group and fallback_group != group:
        fb_ok, fb_code, fb_via = set_and_verify_group_node(runtime, fallback_group, node)
        if fb_ok:
            print(f"🔒 已通过 {fb_via} 锁定兜底策略组 [{fallback_group}] -> {node}")
        elif fb_code not in (0, 404):
            print(f"⚠️  未能锁定兜底策略组 [{fallback_group}] -> {node} (HTTP {fb_code})")


def build_proxy_opener(proxy_port: int) -> urllib.request.OpenerDirector:
    proxy_url = f"http://127.0.0.1:{proxy_port}"
    return urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}))


def verify_proxy_exit(proxy_port: int) -> dict:
    """Query general proxy egress metadata (IP, country, ASN, timezone) via ipinfo.io."""
    proxy_url = f"http://127.0.0.1:{proxy_port}"
    opener = build_proxy_opener(proxy_port)
    req = urllib.request.Request(
        "https://ipinfo.io/json",
        headers={"User-Agent": "curl/8.5.0"},
    )
    try:
        with opener.open(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"❌ 代理连通性校验失败 ({proxy_url}): {exc}")
        sys.exit(1)


def probe_claude_edge_trace(proxy_port: int) -> dict[str, str]:
    """Probe Cloudflare cdn-cgi/trace on Claude/Anthropic domains to verify actual edge exit IP and country."""
    opener = build_proxy_opener(proxy_port)
    for url in ("https://claude.ai/cdn-cgi/trace", "https://www.anthropic.com/cdn-cgi/trace"):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
                )
            },
        )
        try:
            with opener.open(req, timeout=6) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            parsed = {}
            for line in body.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    parsed[k.strip()] = v.strip()
            if parsed.get("ip") or parsed.get("loc"):
                parsed["_url"] = url
                return parsed
        except Exception:
            continue
    return {}


def get_os_timezone() -> tuple[str | None, str | None]:
    """Return (raw_os_tz_name, iana_tz_name) for the actual host OS clock (which Chrome uses on Windows)."""
    if platform.system() == "Windows":
        try:
            res = subprocess.run(["tzutil", "/g"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                win_tz = res.stdout.strip()
                return win_tz, WIN_TO_IANA_TZ.get(win_tz)
        except Exception:
            return None, None
        return None, None

    localtime = Path("/etc/localtime")
    if localtime.exists():
        try:
            resolved = str(localtime.resolve())
            if "/zoneinfo/" in resolved:
                iana = resolved.split("/zoneinfo/", 1)[1]
                return iana, iana
        except Exception:
            pass
    return None, None


def verify_os_timezone(proxy_tz: str, sync_if_needed: bool = False) -> None:
    """Verify host OS timezone matches proxy egress timezone; optionally sync via tzutil on Windows."""
    if not proxy_tz or proxy_tz == "UTC":
        return
    os_raw, os_iana = get_os_timezone()
    if not os_raw:
        return

    if os_iana == proxy_tz:
        print(f"🕒 系统时区真实对齐: {os_raw} ({os_iana})")
        return

    if platform.system() == "Windows":
        target_win_tz = IANA_TO_WIN_TZ.get(proxy_tz)
        if sync_if_needed and target_win_tz:
            res = subprocess.run(["tzutil", "/s", target_win_tz], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                print(f"🕒 已自动同步 Windows 系统时区: {os_raw} -> {target_win_tz} ({proxy_tz})")
                return
            print(f"⚠️  tzutil 时区同步失败: {res.stderr.strip() or res.stdout.strip()}")
        print(
            f"⚠️  系统时区未对齐: Windows 当前为 {os_raw} ({os_iana or '未映射'})，代理出口为 {proxy_tz}；"
            "Windows Chrome 会忽略 TZ 环境变量并读取系统时区，建议使用 -SyncSystemTimezone 或 --sync-timezone 对齐。"
        )
        return

    print(f"⚠️  系统时区 ({os_raw}) 与代理出口 ({proxy_tz}) 不一致；CLI 依赖 TZ，但系统级浏览器建议保持一致。")


def is_chrome_profile_locked(profile_dir: Path) -> bool:
    """Detect cleanly if an active Chrome process currently owns this user-data-dir."""
    if platform.system() == "Windows":
        lockfile = profile_dir / "lockfile"
        if not lockfile.exists():
            return False
        try:
            with lockfile.open("r+b"):
                return False
        except PermissionError:
            return True
        except OSError:
            return True

    singleton_lock = profile_dir / "SingletonLock"
    if not singleton_lock.is_symlink():
        return False
    try:
        target = os.readlink(singleton_lock)
        pid_str = target.rsplit("-", 1)[-1]
        if pid_str.isdigit():
            os.kill(int(pid_str), 0)
            return True
    except (ProcessLookupError, OSError, ValueError):
        return False
    return False


def _load_json_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _sync_nested_values(target: dict, desired: dict) -> list[str]:
    """Recursively enforce desired keys inside a Chrome JSON dict and return changed dot-paths."""
    changed = []
    for key, val in desired.items():
        if isinstance(val, dict):
            sub = target.get(key)
            if not isinstance(sub, dict):
                sub = {}
                target[key] = sub
            for sub_key in _sync_nested_values(sub, val):
                changed.append(f"{key}.{sub_key}")
        elif target.get(key) != val:
            target[key] = val
            changed.append(key)
    return changed


def harden_chrome_profile(profile_dir: Path, country_code: str, apply_fix: bool = True) -> dict:
    """Audit and harden Chrome Preferences & Local State for locale, WebRTC, DoH, geolocation, and country metadata."""
    locked = is_chrome_profile_locked(profile_dir)
    prefs_path = profile_dir / "Default" / "Preferences"
    local_state_path = profile_dir / "Local State"

    desired_prefs: dict = {
        "intl": {"accept_languages": "en-US,en", "selected_languages": "en-US,en"},
        "webrtc": {
            "ip_handling_policy": "disable_non_proxied_udp",
            "multiple_routes_enabled": False,
            "nonproxied_udp_enabled": False,
        },
        "profile": {"default_content_setting_values": {"geolocation": 2}},
    }
    if country_code and len(country_code) == 2 and country_code.isalpha() and country_code.upper() not in BANNED_COUNTRIES:
        cc = country_code.upper()
        desired_prefs["countryid_at_install"] = (ord(cc[0]) << 8) | ord(cc[1])

    desired_local_state: dict = {
        "dns_over_https": {"mode": "off"},
        "intl": {"app_locale": "en-US"},
    }

    prefs_data = _load_json_dict(prefs_path)
    prefs_drifts = _sync_nested_values(prefs_data, desired_prefs)

    local_state_data = _load_json_dict(local_state_path)
    ls_drifts = _sync_nested_values(local_state_data, desired_local_state)
    if country_code and len(country_code) == 2 and country_code.isalpha():
        vc = str(local_state_data.get("variations_country", "")).upper()
        if not vc or vc in BANNED_COUNTRIES:
            local_state_data["variations_country"] = country_code.lower()
            ls_drifts.append("variations_country")

    written = False
    if apply_fix and not locked and (prefs_drifts or ls_drifts or not prefs_path.exists()):
        prefs_path.parent.mkdir(parents=True, exist_ok=True)
        prefs_path.write_text(json.dumps(prefs_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        if ls_drifts or local_state_path.exists():
            local_state_path.write_text(
                json.dumps(local_state_data, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
        written = True

    return {
        "locked": locked,
        "prefs_drifts": prefs_drifts,
        "local_state_drifts": ls_drifts,
        "written": written,
    }


def build_chrome_args(chrome_bin: str, profile_dir: Path, proxy_http: str, url: str) -> list[str]:
    """Build clean Chromium launch args without breaking localhost OAuth callbacks or transport."""
    return [
        chrome_bin,
        f"--user-data-dir={profile_dir}",
        f"--proxy-server={proxy_http}",
        "--lang=en-US",
        "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        "--enforce-webrtc-ip-permission-check",
        "--no-first-run",
        url,
    ]


def audit_clash_rule_coverage(runtime: dict, expected_group: str) -> tuple[bool, list[str]]:
    """Verify live Clash core includes critical Anthropic and challenge domains in the pinned group."""
    _, code, body = clash_api_request(runtime, "GET", "/rules")
    if code != 200 or not body:
        return False, []
    try:
        rules = json.loads(body.decode("utf-8", errors="replace")).get("rules", [])
    except Exception:
        return False, []
    pinned = {
        str(r.get("payload", "")).lower()
        for r in rules
        if r.get("proxy") == expected_group
    }
    required = ("anthropic.com", "claude.ai", "withpersona.com", "stripe.com", "hcaptcha.com", "challenges.cloudflare.com")
    missing = [dom for dom in required if dom not in pinned]
    return True, missing


def _append_unique_path(paths: list[Path], candidate: Path) -> None:
    try:
        resolved = candidate.resolve()
    except OSError:
        resolved = candidate
    for existing in paths:
        try:
            if existing.resolve() == resolved:
                return
        except OSError:
            pass
        if str(existing).lower() == str(candidate).lower():
            return
    paths.append(candidate)


def get_claude_config_dirs() -> list[Path]:
    """Return active Claude state directories (CLAUDE_CONFIG_DIR plus ~/.claude), deduplicated."""
    dirs: list[Path] = []
    config_dir_env = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    if config_dir_env:
        _append_unique_path(dirs, Path(config_dir_env).expanduser())
    _append_unique_path(dirs, Path.home() / ".claude")
    return dirs


def get_claude_settings_targets() -> list[Path]:
    return [cfg_dir / "settings.json" for cfg_dir in get_claude_config_dirs()]


def get_claude_json_paths() -> list[Path]:
    """Return all Claude root state JSON paths (~/.claude.json and <config_dir>/.claude.json)."""
    paths: list[Path] = []
    for cfg_dir in get_claude_config_dirs():
        _append_unique_path(paths, cfg_dir / ".claude.json")
    _append_unique_path(paths, Path.home() / ".claude.json")
    return paths


def _collect_account_artifacts(config_dirs: list[Path]) -> tuple[list[Path], list[Path]]:
    """Collect credential/lock files and telemetry feature-gate dirs without touching project memory."""
    files_to_remove: list[Path] = []
    dirs_to_remove: list[Path] = []
    for cfg_dir in config_dirs:
        if not cfg_dir.exists():
            continue
        for name in (".credentials.json", ".oauth_refresh.lock"):
            candidate = cfg_dir / name
            if candidate.is_file():
                _append_unique_path(files_to_remove, candidate)
        for lock_tmp in sorted(cfg_dir.glob(".oauth_refresh.lock.owner.tmp.*")):
            if lock_tmp.is_file():
                _append_unique_path(files_to_remove, lock_tmp)
        statsig_dir = cfg_dir / "statsig"
        if statsig_dir.is_dir():
            _append_unique_path(dirs_to_remove, statsig_dir)
    return files_to_remove, dirs_to_remove


def _handle_os_credentials(dry_run: bool) -> list[dict]:
    """Inspect or remove OS credential-store entries for Claude Code without ever exposing secret values."""
    system = platform.system()
    results: list[dict] = []

    if system == "Windows":
        try:
            res = subprocess.run(["cmdkey", "/list"], capture_output=True, text=True, timeout=5)
            targets: list[str] = []
            for line in res.stdout.splitlines():
                m = re.match(r"^\s*(?:Target|目标)\s*:\s*(.+?)\s*$", line, flags=re.IGNORECASE)
                if not m:
                    continue
                raw_target = m.group(1)
                low = raw_target.lower()
                if "claude code-credentials" in low or "claude.ai" in low or "anthropic" in low:
                    clean_target = raw_target.split("target=", 1)[1] if "target=" in raw_target else raw_target
                    targets.append(clean_target)
            for target in targets:
                status = "would_delete"
                if not dry_run:
                    del_res = subprocess.run(["cmdkey", f"/delete:{target}"], capture_output=True, text=True, timeout=5)
                    status = "deleted" if del_res.returncode == 0 else "error"
                results.append({"store": "Windows Credential Manager", "label": target, "status": status})
        except Exception:
            pass
        return results

    if system == "Darwin":
        services: list[str] = []
        try:
            dump = subprocess.run(["security", "dump-keychain"], capture_output=True, text=True, timeout=8)
            for match in re.finditer(r'"svce"<blob>="(Claude Code-credentials[^"]*)"', dump.stdout):
                svc = match.group(1)
                if svc not in services:
                    services.append(svc)
        except Exception:
            pass
        if not services:
            probe = subprocess.run(
                ["security", "find-generic-password", "-s", "Claude Code-credentials"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if probe.returncode == 0:
                services.append("Claude Code-credentials")
        for svc in services:
            status = "would_delete"
            if not dry_run:
                del_res = subprocess.run(
                    ["security", "delete-generic-password", "-s", svc],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                status = "deleted" if del_res.returncode == 0 else "error"
            results.append({"store": "macOS Keychain", "label": svc, "status": status})
        return results

    if shutil.which("secret-tool"):
        try:
            probe = subprocess.run(
                ["secret-tool", "lookup", "service", "Claude Code-credentials"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if probe.returncode == 0:
                status = "would_delete"
                if not dry_run:
                    del_res = subprocess.run(
                        ["secret-tool", "clear", "service", "Claude Code-credentials"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                    )
                    status = "deleted" if del_res.returncode == 0 else "error"
                results.append({"store": "Linux Secret Service", "label": "Claude Code-credentials", "status": status})
        except Exception:
            pass
    return results


def _is_system_default_chrome_dir(profile_dir: Path) -> bool:
    """Protect the host's personal Chrome User Data directory from accidental session clearing."""
    home = Path.home()
    defaults = [
        home / "AppData/Local/Google/Chrome/User Data",
        home / "Library/Application Support/Google/Chrome",
        home / ".config/google-chrome",
        home / ".config/chromium",
    ]
    try:
        resolved = profile_dir.resolve()
    except OSError:
        resolved = profile_dir
    for default_dir in defaults:
        try:
            if resolved == default_dir.resolve():
                return True
        except OSError:
            pass
        if str(profile_dir).lower() == str(default_dir).lower():
            return True
    return False


def _collect_isolated_web_session_paths(profile_dir: Path) -> list[Path]:
    """Locate auth cookies and web storage inside the isolated Chrome profile without touching Preferences."""
    base = profile_dir / "Default"
    rel_targets = (
        base / "Cookies",
        base / "Cookies-journal",
        base / "Network" / "Cookies",
        base / "Network" / "Cookies-journal",
        base / "Local Storage",
        base / "Session Storage",
        base / "IndexedDB",
        base / "SharedStorage",
    )
    return [p for p in rel_targets if p.exists()]


def _collect_preserved_items(config_dirs: list[Path], json_paths: list[Path]) -> list[str]:
    """Enumerate existing project memory directories and user configs kept intact by account reset."""
    preserved: list[str] = []
    for cfg_dir in config_dirs:
        if not cfg_dir.exists():
            continue
        for entry in PRESERVED_MEMORY_ENTRIES:
            clean_name = entry.rstrip("/")
            target = cfg_dir / clean_name
            if target.exists():
                preserved.append(str(target))
    for jpath in json_paths:
        data = _load_json_dict(jpath)
        kept_keys = [k for k in ("projects", "mcpServers", "githubRepoPaths") if k in data]
        if kept_keys:
            preserved.append(f"{jpath} [{', '.join(kept_keys)}]")
    return preserved


def _backup_json_before_edit(json_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = json_path.with_name(f"{json_path.name}.pre-reset-{stamp}.bak")
    shutil.copy2(json_path, backup_path)
    return backup_path


def reset_claude_account_cache(
    dry_run: bool = False,
    include_web_session: bool = False,
    profile_dir: Path | None = None,
) -> dict:
    """Clear account identity, auth tokens, and cached risk/experiment flags while preserving project memory."""
    config_dirs = get_claude_config_dirs()
    json_paths = get_claude_json_paths()
    artifact_files, artifact_dirs = _collect_account_artifacts(config_dirs)

    json_plans: list[dict] = []
    for jpath in json_paths:
        if not jpath.exists():
            continue
        data = _load_json_dict(jpath)
        matched_keys = [k for k in ACCOUNT_JSON_KEYS if k in data]
        if not matched_keys:
            continue
        plan = {"path": str(jpath), "keys": matched_keys, "backup": None, "status": "would_strip"}
        if not dry_run:
            plan["backup"] = str(_backup_json_before_edit(jpath))
            for key in matched_keys:
                data.pop(key, None)
            jpath.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            plan["status"] = "stripped"
        json_plans.append(plan)

    removed_files: list[str] = []
    for fpath in artifact_files:
        if not dry_run:
            fpath.unlink(missing_ok=True)
        removed_files.append(str(fpath))

    removed_dirs: list[str] = []
    for dpath in artifact_dirs:
        if not dry_run:
            shutil.rmtree(dpath)
        removed_dirs.append(str(dpath))

    os_creds = _handle_os_credentials(dry_run=dry_run)

    web_session_items: list[str] = []
    web_session_warning = ""
    if include_web_session and profile_dir is not None:
        if _is_system_default_chrome_dir(profile_dir):
            web_session_warning = f"已拒绝清理浏览器会话: {profile_dir} 指向系统默认 Chrome User Data，仅允许清理隔离 Profile。"
        elif is_chrome_profile_locked(profile_dir):
            web_session_warning = f"隔离 Chrome 正在运行，已跳过网页会话清理 ({profile_dir})；请先关闭隔离浏览器后再重跑。"
        else:
            for item in _collect_isolated_web_session_paths(profile_dir):
                if not dry_run:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink(missing_ok=True)
                web_session_items.append(str(item))

    preserved = _collect_preserved_items(config_dirs, json_paths)
    has_changes = bool(json_plans or removed_files or removed_dirs or os_creds or web_session_items)
    return {
        "dry_run": dry_run,
        "has_changes": has_changes,
        "json_plans": json_plans,
        "removed_files": removed_files,
        "removed_dirs": removed_dirs,
        "os_credentials": os_creds,
        "web_session_items": web_session_items,
        "web_session_warning": web_session_warning,
        "preserved": preserved,
    }


def print_account_reset_report(report: dict, dry_run: bool) -> None:
    prefix = "🧪 [预览 / Dry-Run] 即将清理以下账号身份与风控缓存" if dry_run else "🧹 已完成 Claude 账号身份与风控缓存清理"
    print(f"{prefix}:")

    for jp in report["json_plans"]:
        backup_note = f" (已备份 -> {jp['backup']})" if jp.get("backup") else ""
        print(f"  - JSON 账号/特征开关字段 ({len(jp['keys'])} 项): {jp['path']}{backup_note}")
        print(f"    字段: {', '.join(jp['keys'])}")

    for fpath in report["removed_files"]:
        print(f"  - 凭据/锁文件: {fpath}")
    for dpath in report["removed_dirs"]:
        print(f"  - 特征实验缓存目录: {dpath}")
    for cred in report["os_credentials"]:
        print(f"  - 系统凭据库 [{cred['store']}]: {cred['label']} ({cred['status']})")
    for witem in report["web_session_items"]:
        print(f"  - 隔离浏览器网页会话数据: {witem}")
    if report["web_session_warning"]:
        print(f"⚠️  {report['web_session_warning']}")

    if not report["has_changes"]:
        print("  (未发现需要清除的账号认证或风控缓存项)")

    if report["preserved"]:
        print("💾 严格保留的项目记忆、会话历史与用户配置:")
        for item in report["preserved"]:
            print(f"  ✓ {item}")

    if not dry_run and report["has_changes"]:
        print("👉 若之前曾在系统默认浏览器或 Claude Desktop 登录过旧账号，后续请仅通过隔离 Chrome / 受控 CLI 登录新账号。")


def sync_claude_settings(mode: str) -> list[tuple[Path, bool]]:
    """Non-destructively sync strict or balanced privacy vars across active Claude settings files."""
    results = []
    for settings_path in get_claude_settings_targets():
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except Exception:
                settings = {}

        before = json.dumps(settings, sort_keys=True, ensure_ascii=False)
        env_cfg = settings.setdefault("env", {})

        if mode == "strict":
            for key, val in STRICT_ENV_VARS.items():
                env_cfg[key] = val
            env_cfg.setdefault("DO_NOT_TRACK", "1")
        else:
            env_cfg["DISABLE_ERROR_REPORTING"] = "1"
            env_cfg["DISABLE_FEEDBACK_COMMAND"] = "1"
            env_cfg["CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY"] = "1"
            env_cfg["CLAUDE_CODE_ATTRIBUTION_HEADER"] = "0"
            for key in BALANCED_REMOVED_VARS:
                env_cfg.pop(key, None)

        after = json.dumps(settings, sort_keys=True, ensure_ascii=False)
        changed = before != after or not settings_path.exists()
        if changed:
            settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        results.append((settings_path, changed))
    return results


def find_chrome_binary() -> str:
    system = platform.system()
    if system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    elif system == "Windows":
        prog_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")
        prog_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
        local_app = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(prog_files, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(prog_x86, r"Google\Chrome\Application\chrome.exe"),
            os.path.join(local_app, r"Google\Chrome\Application\chrome.exe"),
        ]
    else:
        candidates = [
            shutil.which("google-chrome") or "",
            shutil.which("google-chrome-stable") or "",
            shutil.which("chromium") or "",
            shutil.which("chromium-browser") or "",
        ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    raise FileNotFoundError("未找到 Chrome / Chromium 可执行文件，请在脚本中手动指定路径。")


def find_browser_opener() -> Path | None:
    base_dir = Path(__file__).resolve().parent
    opener = base_dir / ("claude-browser-opener.exe" if platform.system() == "Windows" else "claude-browser-opener.sh")
    return opener if opener.exists() else None


def build_child_env(
    proxy_port: int,
    timezone: str,
    telemetry_mode: str,
    profile_dir: Path,
    chrome_bin: str | None,
) -> dict[str, str]:
    child_env = os.environ.copy()
    proxy_http = f"http://127.0.0.1:{proxy_port}"
    proxy_socks = f"socks5://127.0.0.1:{proxy_port}"
    child_env.update({
        "http_proxy": proxy_http,
        "https_proxy": proxy_http,
        "all_proxy": proxy_socks,
        "HTTP_PROXY": proxy_http,
        "HTTPS_PROXY": proxy_http,
        "ALL_PROXY": proxy_socks,
        "TZ": timezone,
        "DISABLE_ERROR_REPORTING": "1",
        "DISABLE_FEEDBACK_COMMAND": "1",
        "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
        "CLAUDE_CODE_ATTRIBUTION_HEADER": "0",
        "CLAUDE_GUARD_PROXY": proxy_http,
        "CLAUDE_GUARD_PROFILE": str(profile_dir),
    })
    if chrome_bin:
        child_env["CLAUDE_GUARD_CHROME"] = chrome_bin
    opener = find_browser_opener()
    if opener:
        child_env["BROWSER"] = str(opener)

    if telemetry_mode == "strict":
        child_env["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"] = "1"
        child_env["DISABLE_TELEMETRY"] = "1"
    else:
        for key in BALANCED_REMOVED_VARS:
            child_env.pop(key, None)
    return child_env


def main() -> None:
    configure_stdio()

    default_profile = DEFAULT_CHROME_PROFILE_DIR or (Path.home() / ".claude-chrome-profile")

    parser = argparse.ArgumentParser(description="Claude Cross-Platform Anti-Risk-Control Environment Launcher")
    parser.add_argument("mode", nargs="?", default="web", choices=["web", "cli", "check", "reset-account"], help="启动模式: web | cli | check | reset-account")
    parser.add_argument("--node", default=DEFAULT_TARGET_NODE, help="指定要锁定的 Clash 节点名称")
    parser.add_argument("--group", default=CLAUDE_GROUP_NAME, help="指定 Claude 策略组名称")
    parser.add_argument("--port", type=int, default=None, help="手动指定本地 Clash 代理端口")
    parser.add_argument("--telemetry", default=TELEMETRY_MODE, choices=["strict", "balanced"], help="遥测阻断级别")
    parser.add_argument("--keep-global", action="store_true", help="仅锁定 Claude 专用策略组，不修改兜底策略组")
    parser.add_argument("--sync-timezone", action="store_true", help="若系统时区与代理出口不一致则尝试同步系统时区")
    parser.add_argument("--no-fix-profile", action="store_true", help="仅检查不写入隔离 Chrome Profile 加固配置")
    parser.add_argument("--profile-dir", default=str(default_profile), help="隔离 Chrome 用户数据目录")
    parser.add_argument("--dry-run", action="store_true", help="配合 reset-account 仅预览将清除的账号缓存与保留的项目记忆")
    parser.add_argument("-y", "--yes", action="store_true", help="直接确认执行 reset-account 账号缓存清理（仍自动创建 .bak 备份）")
    parser.add_argument("--include-web-session", action="store_true", help="配合 reset-account 清理隔离 Chrome Profile 中的网页登录 Cookie/Storage")
    args, unknown_args = parser.parse_known_args()

    if args.mode == "reset-account":
        profile_dir = Path(args.profile_dir)
        preview = reset_claude_account_cache(
            dry_run=True,
            include_web_session=args.include_web_session,
            profile_dir=profile_dir,
        )
        print_account_reset_report(preview, dry_run=True)
        if args.dry_run or not preview["has_changes"]:
            return
        if not args.yes:
            if not sys.stdin.isatty():
                print("ℹ️  当前为非交互终端且未指定 --yes，未修改任何文件；请加 --yes 确认清理（将自动创建 .bak 备份）。")
                sys.exit(2)
            reply = input("⚠️  确认清理以上账号身份与风控缓存？项目记忆与配置将完整保留 [y/N]: ").strip().lower()
            if reply not in {"y", "yes"}:
                print("已取消清理，未改动任何文件。")
                return
        applied = reset_claude_account_cache(
            dry_run=False,
            include_web_session=args.include_web_session,
            profile_dir=profile_dir,
        )
        print_account_reset_report(applied, dry_run=False)
        return

    runtime = detect_clash_runtime()
    proxy_port = args.port or runtime["mixed_port"]
    http_ctrl_status = runtime["controller"] if runtime["http_controller_enabled"] else "已关闭 (优先 Named Pipe)"

    print(f"🔍 Clash 配置目录: {runtime['config_dir'] or '默认配置'} | 本地代理端口: {proxy_port} | HTTP接口: {http_ctrl_status}")

    if args.node:
        lock_clash_nodes(
            runtime,
            group=args.group,
            fallback_group=FALLBACK_GROUP_NAME,
            node=args.node,
            lock_global=not args.keep_global,
        )

    ip_data = verify_proxy_exit(proxy_port)
    ip_addr = ip_data.get("ip", "unknown")
    country = ip_data.get("country", "unknown")
    city = ip_data.get("city", "")
    timezone = ip_data.get("timezone", "UTC")
    org = ip_data.get("org", "unknown")

    if country in BANNED_COUNTRIES:
        print(f"🚨 严重警告: 当前出口位于受限区域 [{country}] (IP: {ip_addr})，已拒绝启动以保护账号安全！")
        sys.exit(2)

    edge_trace = probe_claude_edge_trace(proxy_port)
    edge_loc = edge_trace.get("loc", "")
    if edge_loc.upper() in BANNED_COUNTRIES:
        print(
            f"🚨 严重警告: {edge_trace.get('_url', 'Claude')} 实际边缘出口落在受限区域 [{edge_loc}] "
            f"(IP: {edge_trace.get('ip', 'unknown')})，疑似分流泄漏，已拒绝启动！"
        )
        sys.exit(2)

    loc_label = f"{country}/{city}" if city else country
    print(f"✅ 通用出口校验通过: IP={ip_addr} | 地区={loc_label} | ASN={org} | 代理时区={timezone}")
    if edge_trace:
        print(
            f"🔎 Claude 边缘实际出口: IP={edge_trace.get('ip', '?')} | "
            f"loc={edge_loc or '?'} | colo={edge_trace.get('colo', '?')}"
        )

    verify_os_timezone(timezone, sync_if_needed=args.sync_timezone)

    settings_results = sync_claude_settings(args.telemetry)
    for spath, changed in settings_results:
        tag = "已更新" if changed else "已合规"
        print(f"🛡️  Claude 隐私配置 ({args.telemetry}, {tag}): {spath}")

    profile_dir = Path(args.profile_dir)
    prof_audit = harden_chrome_profile(profile_dir, country, apply_fix=not args.no_fix_profile)
    total_drifts = prof_audit["prefs_drifts"] + prof_audit["local_state_drifts"]
    if prof_audit["locked"] and total_drifts:
        print(f"⚠️  隔离 Chrome Profile 正被运行中实例占用，发现未对齐项 {total_drifts}；请关闭隔离浏览器后重跑即可自动写入加固。")
    elif prof_audit["written"]:
        print(f"🧬 隔离 Chrome Profile 已自动加固 ({len(total_drifts)} 项 -> 语言/WebRTC/DoH关闭/地理禁用/安装国家={country}): {profile_dir}")
    else:
        print(f"🧬 隔离 Chrome Profile 防泄漏配置已合规: {profile_dir}")

    opener = find_browser_opener()

    if args.mode == "check":
        ok_rules, missing_rules = audit_clash_rule_coverage(runtime, args.group)
        if ok_rules:
            if missing_rules:
                print(f"⚠️  Clash 实时规则尚未包含 {missing_rules}，请在 Clash Verge 中点击刷新/重载当前配置使最新覆写生效。")
            else:
                print(f"📜 Clash 实时规则覆盖完整: 核心/KYC/支付/Turnstile 域名均已锁定至 [{args.group}]")
        if opener:
            print(f"🌐 OAuth/链接隔离接管就绪: {opener.name} (Profile: {profile_dir})")
        else:
            print("⚠️  未检测到 claude-browser-opener，CLI 登录时可能会呼起系统默认非隔离浏览器。")
        return

    try:
        chrome_bin = find_chrome_binary()
    except FileNotFoundError:
        if args.mode == "web":
            raise
        chrome_bin = None

    child_env = build_child_env(proxy_port, timezone, args.telemetry, profile_dir, chrome_bin)
    proxy_http = f"http://127.0.0.1:{proxy_port}"

    if args.mode == "web":
        profile_dir.mkdir(parents=True, exist_ok=True)
        cmd = build_chrome_args(chrome_bin, profile_dir, proxy_http, "https://claude.ai")
        print(f"🌐 正在启动强化隔离 Chrome 实例 (Profile: {profile_dir}, Proxy: {proxy_http}, TZ={timezone})...")
        kwargs = {"env": child_env}
        if platform.system() == "Windows":
            kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(cmd, **kwargs)
    elif args.mode == "cli":
        claude_bin = shutil.which("claude")
        if not claude_bin:
            print("❌ 未找到 `claude` CLI 命令，请确认已安装 Claude Code。")
            sys.exit(1)
        if "BROWSER" in child_env:
            print(f"🌐 OAuth/外链隔离浏览器已接管 (BROWSER -> 隔离 Chrome Profile: {profile_dir})")
        else:
            print("⚠️  未检测到 claude-browser-opener，CLI 登录时可能会呼起系统默认非隔离浏览器。")
        print(f"💻 正在启动受控 Claude Code CLI (Proxy: {proxy_http}, TZ={timezone})...")
        completed = subprocess.run([claude_bin, *unknown_args], env=child_env)
        sys.exit(completed.returncode)


if __name__ == "__main__":
    main()

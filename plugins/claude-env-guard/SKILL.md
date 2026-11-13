---
name: claude-env-guard
description: Cross-platform (Windows, macOS, Linux) environment stabilizer and anti-risk-control configurator for Claude (claude.ai and Claude Code CLI) when using Clash / Mihomo proxies. Use when the user wants to configure a stable Claude environment, bind or lock a specific Clash proxy node for Claude, clear prior Claude account/identity/risk-flag caches before initial login while preserving project memory, prevent Claude account bans or Persona KYC verification prompts, align browser/CLI timezone with proxy exit IP, isolate Chrome profiles with WebRTC leak protection, ensure CLI OAuth login opens in the isolated browser instead of default Chrome, or disable Claude Code telemetry across Windows, macOS, or Linux.
---

# Claude Env Guard

Automate and harden a local workstation environment across Windows, macOS, and Linux so that Claude Web (`claude.ai`) and Claude Code CLI operate behind a deterministic, leak-free Clash proxy exit with aligned timezone, isolated browser fingerprint, OAuth browser isolation, and controlled telemetry.

## When to Use

- The user wants to initialize or harden a computer (Windows, macOS, or Linux) to use Claude safely without triggering account bans or Persona KYC prompts.
- The user wants to **clean stale Claude account / identity / risk-flag caches on first-time setup** before logging into a new account, strictly **preserving local project memory (`projects/`, `history.jsonl`, `CLAUDE.md`, `settings.json`, `hooks`, `skills`, `mcpServers`)**.
- The user specifies a Clash proxy node and wants to lock all Claude, Persona KYC, Stripe, and telemetry traffic to that node.
- The user asks to inspect their current Clash configuration and generate tailored launcher scripts for Claude Web or Claude Code CLI.
- The user wants to ensure `claude` CLI OAuth sign-in (`/login` / `claude auth login`) opens inside the isolated Chrome profile instead of leaking into the host's default browser.
- The user wants to synchronize process-level or system-level timezone with their proxy exit IP and disable non-essential Claude telemetry.

## Core Workflow

Follow these phases in order when configuring or updating a machine's environment. Run a **safe account-cache cleanup (`reset-account --dry-run` → confirm → `reset-account --yes`)** on first-time setup whenever the machine previously logged into another or risk-flagged Claude account.

### Phase 1: Inspect Host OS and Clash Configuration

Before generating or writing any scripts, discover the user's operating system and parse their active Clash / Mihomo configuration rather than guessing ports or paths.

1. Identify the OS (`Windows`, `macOS`, or `Linux`) and locate the active Clash configuration directory:

   - **macOS**:
     - `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/`
     - `~/.config/clash-verge/`
     - `~/.config/mihomo/`
     - `~/.config/clash/`
   - **Linux**:
     - `~/.local/share/io.github.clash-verge-rev.clash-verge-rev/`
     - `~/.config/clash-verge/`
     - `~/.config/mihomo/`
     - `~/.config/clash/`
   - **Windows**:
     - `%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\`
     - `%USERPROFILE%\.config\clash-verge\`
     - `%USERPROFILE%\.config\mihomo\`
     - `%USERPROFILE%\.config\clash\`

2. Parse `clash-verge.yaml` (live generated config header if present), `verge.yaml`, `config.yaml`, and `profiles.yaml` (redacting subscription URLs/secrets before reporting):

   - **Local listening port**: Check active `mixed-port`, `verge_mixed_port`, `verge_socks_enabled` / `verge_socks_port`, `verge_http_enabled` / `verge_port` (on Clash Verge Rev, `7898`/`7899` in `config.yaml` may be disabled in `verge.yaml` while only `mixed-port: 7897` is open).
   - **Controller Interface (HTTP API vs Windows Named Pipe)**:
     - Check `enable_external_controller` in `verge.yaml` and live `external-controller` in `clash-verge.yaml`. If `enable_external_controller: false`, HTTP `127.0.0.1:9097` is inactive; on Windows, Clash Verge Rev exposes the live Mihomo REST API via `external-controller-pipe` (`\\.\pipe\verge-mihomo-sidecar-release-...`).
   - **Active Profile & Override Script**: Check `profiles.yaml` for the active profile (`current`) and its linked script (`option.script`, e.g. `profiles\<uid>.js`) vs global `Script.js`.
   - **TUN and DNS status**: Check `tun.enable`, `dns.enable`, `dns.enhanced-mode` (`fake-ip` preferred), and `dns.respect-rules`.
   - **Available proxy nodes & Claude paths**: Match the target proxy node (verify non-`CN`/`HK`/`MO`), locate Chrome binary, `claude` CLI binary, and check `CLAUDE_CONFIG_DIR` if customized.

### Phase 2: Lock Clash Routing and Target Node

Ensure all Anthropic and auxiliary verification domains stay pinned to a single static node and never jump across IPs via `url-test` or `load-balance`.

1. Read `scripts/clash_override_template.js` from this skill's resources.
2. Write the customized override script to the active Clash Verge profile script (e.g. `profiles\<script_uid>.js`) or global override script:
   - Place the user's target node at index `0` of `🔒 Claude-固定出口` (`type: "select"`) and filter out `CN`/`HK`/`MO` and subscription-info nodes.
   - Prepend `DOMAIN-SUFFIX` rules idempotently for all four domain categories:
     - Core: `anthropic.com`, `claude.ai`, `claude.com`, `claudeusercontent.com`
     - KYC: `withpersona.com`, `persona.com`
     - Payment & anti-bot: `stripe.com`, `stripe.network`, `hcaptcha.com`, `challenges.cloudflare.com`, `arkoselabs.com`, `funcaptcha.com`
     - Telemetry & feature flags: `statsig.com`, `statsigapi.net`, `growthbook.io`, `sentry.io`, `intercom.io`, `intercomcdn.com`, `segment.io`
   - Enforce `dns.enable = true`, `dns["respect-rules"] = true`, and `fake-ip`.
3. Remind the user to reload/reactivate the profile in Clash Verge GUI if the running core has not regenerated `clash-verge.yaml` yet (`404` on `🔒 Claude-固定出口`). Meanwhile, lock the fallback selector (`🚀 节点选择` / `Proxy`) via Named Pipe or HTTP `PUT /proxies/<GROUP>` so live traffic and OAuth/Cloudflare challenges use the same exit IP.

### Phase 3: Configure Claude Code Telemetry and Privacy Settings

Non-destructively sync `%USERPROFILE%\.claude\settings.json` (and `%CLAUDE_CONFIG_DIR%\settings.json` if `CLAUDE_CONFIG_DIR` is set) without overwriting user `hooks`, `plugins`, `permissions`, `OTEL_*`, `DISABLE_GROWTHBOOK`, or `attribution` entries:

1. **Strict Mode (Default for anti-ban safety)**: Blocks all telemetry, feedback, error reporting, and non-essential traffic:
   - `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1"`
   - `DISABLE_TELEMETRY: "1"`
   - `DISABLE_ERROR_REPORTING: "1"`
   - `DISABLE_FEEDBACK_COMMAND: "1"`
   - `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY: "1"`
   - `CLAUDE_CODE_ATTRIBUTION_HEADER: "0"`
2. **Balanced Mode (Preserves GrowthBook / Statsig remote feature flags)**: Omit `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` and `DISABLE_TELEMETRY` completely (never set to `"0"`), keep `DISABLE_ERROR_REPORTING: "1"`, and rely on Phase 2 rules to pin `statsig.com` and `growthbook.io`.

### Phase 4: Generate Tailored Environment Guard Scripts & CLI Browser Isolation

Load `scripts/claude_guard_template.py`, `scripts/shell_templates.md`, and `scripts/claude_browser_opener.rs` / `scripts/claude_browser_opener.cs` to generate the workstation's launcher suite:

1. **Tailored `claude_guard.py`** supporting:
   - Live `clash-verge.yaml` / `verge.yaml` / `config.yaml` detection (supporting both **Windows Named Pipe** and **HTTP REST API**).
   - Pre-flight lock verification of both `🔒 Claude-固定出口` (with clear reload hint on `404`) and `🚀 节点选择` fallback (overrideable with `--keep-global`), plus live `/rules` coverage verification.
   - Multi-probe egress validation: `https://ipinfo.io/json` AND `https://claude.ai/cdn-cgi/trace` (blocking `CN`/`HK`/`MO` split-routing leaks on Anthropic edges even when general endpoints differ), and injecting `TZ=<timezone>` + `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`.
   - Real host OS timezone verification (`tzutil /g` on Windows vs `/etc/localtime` on POSIX) so Windows never silently exposes `Asia/Shanghai` behind a `TZ` env var (`--sync-timezone` / `-SyncSystemTimezone` aligns `tzutil /s`).
   - Isolated Chrome `Default/Preferences` and `Local State` hardening (`harden_chrome_profile()`): safely checks `lockfile`/`SingletonLock`, enforces `intl.accept_languages = "en-US,en"` and `intl.app_locale = "en-US"`, persists `webrtc` leak protection (`disable_non_proxied_udp`), blocks HTML5 `geolocation` (`2`), turns off `dns_over_https` (`mode: "off"`), and replaces `CN` `countryid_at_install` (`17230`) / `variations_country` with the verified exit country—without modifying unrelated UX settings (`notifications`, `translate`, `spellcheck`).
   - Clean Chrome launch flags (`--user-data-dir`, `--proxy-server`, `--lang=en-US`, `--force-webrtc-ip-handling-policy=disable_non_proxied_udp`, `--enforce-webrtc-ip-permission-check`, `--no-first-run`) in `web` mode. **Do not** add `--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE 127.0.0.1` or `--proxy-bypass-list=<-loopback>` (these break `http://localhost:<port>/callback` CLI OAuth flows or send loopback into the proxy), and **never** inject JS/canvas/navigator prototype spoofing, `--disable-web-security`, or `--remote-debugging-port`, as Cloudflare Turnstile and Anthropic anti-bot checks flag tampered prototypes or broken loopback/transport.
2. **CLI OAuth & Hyperlink Browser Isolation (`BROWSER` takeover)**:
   - Without `BROWSER`, `claude` CLI on Windows calls `rundll32 url,OpenURL` (opening the default non-isolated Chrome). When `BROWSER` is set, `claude` spawns it directly with `shell: false`.
   - On **Windows**, compile `scripts/claude_browser_opener.rs` (`rustc -O -C strip=symbols`) or `scripts/claude_browser_opener.cs` (`C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:winexe /nologo`) into `claude-browser-opener.exe` alongside `claude_guard.py`.
   - On **macOS / Linux**, install `claude-browser-opener.sh` (`chmod +x`) alongside `claude_guard.py`.
   - `claude_guard.py` injects `BROWSER`, `CLAUDE_GUARD_CHROME`, `CLAUDE_GUARD_PROFILE`, and `CLAUDE_GUARD_PROXY` only into the guarded CLI child process (`cli` mode) so `claude auth login` / `/login` opens inside the exact same isolated Chrome profile without hijacking other desktop tools.
3. **Update durability (`claude update`)**:
   - External wrapper scripts + `BROWSER` env integration never patch the `claude` binary itself (`~/.local/bin/claude.exe` on Windows native installs replaces only its own binary atomically on `claude update`). Note that `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1"` disables background auto-updating, while explicit `claude-cli update` continues to route updates cleanly through the locked proxy.
4. **First-time / Pre-login Account Cache Reset (`reset-account`)**:
   - When setting up this isolated environment on a machine that previously used an older or risk-flagged Claude account (or before signing into a fresh account), run `claude_guard.py reset-account --dry-run` first to inspect what will be cleared vs kept, confirm with the user (never silently wipe an active logged-in session without asking), and then execute `claude_guard.py reset-account --yes` (optionally add `--include-web-session` when resetting cookies inside the **isolated** Chrome profile).
   - **Cleared cleanly (account, identity, credentials, & cached risk/feature flags)**:
     - Every active `.claude.json` (`~/.claude.json` and `%CLAUDE_CONFIG_DIR%/.claude.json`, backed up to `*.pre-reset-<timestamp>.bak` before editing): `oauthAccount`, `userID`, `machineID`, `claudeCodeFirstTokenDate`, `cachedGrowthBookFeatures*`, `cachedExperiment*`, `cachedExtraUsageDisabledReason`, `groveConfigCache`, `passesEligibilityCache`, `fableOverageConsentV2`, `hasAvailableSubscription`, `subscriptionNoticeCount`, `penguinModeOrgEnabled`, `claudeAiMcpEverConnected`.
     - Auth & lock artifacts across active `~/.claude` and `%CLAUDE_CONFIG_DIR%`: `.credentials.json`, `.oauth_refresh.lock`, `.oauth_refresh.lock.owner.tmp.*`, and `statsig/` directories.
     - OS credential entries (`Claude Code-credentials*` in macOS Keychain via `security delete-generic-password`, Linux Secret Service via `secret-tool`, or Windows Credential Manager via `cmdkey /delete`).
     - With `--include-web-session`: auth cookies & site storage (`Cookies`, `Network/Cookies`, `Local Storage`, `Session Storage`, `IndexedDB`, `SharedStorage`) **only** inside the unlocked `--profile-dir` (explicitly refuses system default Chrome `User Data`, and preserves hardened `Preferences` & `Local State`).
   - **Strictly preserved (project memory & local configuration)**:
     - `.claude.json` keys `projects`, `mcpServers`, `githubRepoPaths`, `pluginUsage`, `skillUsage`, `installMethod`, `autoUpdates`, etc.
     - Files & directories under `~/.claude` / `CLAUDE_CONFIG_DIR`: `projects/` (including `memory/*.md` and session `.jsonl` logs), `history.jsonl`, `file-history/`, `paste-cache/`, `plans/`, `todos/`, `CLAUDE.md`, `settings.json`, `hooks/`, `skills/`, `agents/`, `plugins/`, and `backups/`.
5. **Windows ergonomics**:
   - Write `.ps1` wrappers as UTF-8 with a **single** BOM + CRLF for Windows PowerShell 5.1 / 7 compatibility, double-click `.cmd` wrappers with `chcp 65001 >nul` + `if errorlevel 1 pause`, and convenient `PATH` aliases (`claude-web.cmd`, `claude-cli.cmd`, `claude-check.cmd`). Avoid creating unprompted one-click destructive `.cmd` shortcuts for `reset-account` so users do not clear active logins by accident.

### Phase 5: Run Verification Checklist

After generating all scripts and compiling the browser opener, run real checks:

1. If Windows `.exe` opener was compiled, verify with `node -e` `spawnSync(..., { shell: false, windowsHide: true })` that bad schemes (`file://`) exit `1` and missing Chrome exits `1` cleanly without hanging.
2. Run `<launcher> check` (e.g. `claude-check.cmd`) and confirm:
   - Controller lock succeeded (`🔒 Claude-固定出口` and/or fallback group -> target node via Named Pipe or HTTP).
   - `ipinfo.io/json` AND `claude.ai/cdn-cgi/trace` return non-`CN`/`HK`/`MO` countries (`loc`/`colo`), and real host OS timezone aligns with proxy timezone.
   - `Default/Preferences` and `Local State` profile hardening reports compliant (language, WebRTC, DoH off, geolocation deny, non-`CN` `countryid_at_install`) and Clash `/rules` includes core/challenge domains.
   - `settings.json` privacy keys are compliant and existing keys preserved.
   - `claude-browser-opener` isolation check reports ready.
3. Run guarded CLI version pass-through (`claude-cli.cmd --version` or equivalent) to confirm proxy, `TZ`, `BROWSER` takeover, and CLI exit `0`.

## Gotchas

- **Clash Verge Windows Named Pipe vs HTTP `9097`**: `config.yaml` often holds template `external-controller: 127.0.0.1:9097` even when `verge.yaml` has `enable_external_controller: false` (`clash-verge.yaml` `external-controller: ''`). Always inspect `clash-verge.yaml` / `verge.yaml` first and use `external-controller-pipe` on Windows rather than assuming port `9097` is open.
- **CLI OAuth non-isolated browser trap (`shell: false`)**: On Windows, Claude Code CLI spawns `process.env.BROWSER` with `shell: false`, so `.cmd`/`.bat` scripts fail and direct `chrome.exe` cannot accept `--user-data-dir`/`--proxy-server` args. Always compile a detached GUI `.exe` wrapper (`claude-browser-opener.exe`) that opens Chrome with the isolated profile + proxy and exits `0` immediately. (Note: the separate Claude-in-Chrome extension bridge uses Windows App Paths / `rundll32`, which is unrelated to normal CLI OAuth login.)
- **Windows PowerShell UTF-8 single-BOM trap**: Writing a double UTF-8 BOM (`\ufeff\ufeff`) before `param(` causes PowerShell `ParserError` on Chinese/emoji parameters; normalize `.ps1` files to a single UTF-8 BOM.
- **Truthy environment variable trap in Claude Code**: `DISABLE_TELEMETRY="0"` or `"false"` still evaluates as truthy in Claude Code. To restore remote feature flags, delete the key from `settings.json` and unset it in the shell.
- **Process TZ & `--accept-lang` on Windows Chrome**: Chromium on Windows ignores `TZ` env vars and reads Win32 `tzutil /g`, and GUI Windows Chrome does not reliably honor `--accept-lang` if `Default/Preferences` lacks `intl.accept_languages` or carries a `CN` `countryid_at_install` (`17230`). Fix real leaks with `harden_chrome_profile()` + host OS timezone alignment (`-SyncSystemTimezone` / `--sync-timezone`); keep `--proxy-server` standard without `--host-resolver-rules=MAP * ~NOTFOUND` or `--proxy-bypass-list=<-loopback>` so CLI OAuth `http://localhost:<port>/callback` redirects stay intact.
- **Avoid over-hardening & heuristic checker traps (e.g., `checkcc.org`)**: Do not delete Windows system CJK fonts (`Microsoft YaHei`, `SimSun`), block normal UX preferences (`notifications`/`translate`), or install JS/canvas/navigator spoofing extensions to chase a 0% score on third-party checkers. Heuristic sites often score Windows UA, UTC+8 regions like Singapore (`Asia/Singapore`), preinstalled OS CJK fonts, datacenter ASNs, and backend Worker multi-source IP mismatches as "high risk" even when TLS/DNS/WebRTC/Locale/Timezone are clean. Prioritize real IP/DNS/WebRTC/timezone/locale/OAuth consistency, and only switch to an ISP/residential node if Anthropic/Stripe challenges the exit ASN.
- **Persona KYC mobile handoff**: Remind users never to scan a Persona KYC QR code on a phone with a Chinese SIM or mismatched Wi-Fi IP; complete KYC inside the isolated desktop Chrome profile.
- **Partial cache cleanup & multi-root traps (`CLAUDE_CONFIG_DIR` vs `~/.claude`)**: Users who customize `CLAUDE_CONFIG_DIR` often still have `~/.claude.json` (holding an old `userID` / `machineID`) or legacy `~/.claude/.credentials.json`, plus OS keychain entries (`Claude Code-credentials*`). Cleaning only `CLAUDE_CONFIG_DIR` leaves fingerprint/risk caches behind; meanwhile deleting `~/.claude` or `projects/` wholesale destroys user project memory. Always use `--dry-run` → `--yes` on `reset-account` (which inspects **all** active roots, creates `.pre-reset-*.bak`, and preserves `projects/`, `history.jsonl`, `CLAUDE.md`, `settings.json`, `mcpServers`, `hooks/`, and `skills/`). Remember that `--include-web-session` only resets cookies in the isolated `--profile-dir` and never touches the user's personal Chrome browser or Claude Desktop `claude_desktop_config.json`.

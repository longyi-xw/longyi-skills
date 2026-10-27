# Host Memory Protocol (Brain-Body Decoupling)

This protocol governs how `prompt-architect` initializes, reads, and maintains the machine-specific local memory directory on the host computer.

## 1. Anchor Configuration (`~/.prompt-architect.json`)

The skill locates its host memory via a lightweight JSON file in the user's home directory (`~/.prompt-architect.json` on Linux/macOS or `C:\Users\<Username>\.prompt-architect.json` on Windows):

```json
{
  "memory_dir": "D:/.prompt-architect-memory",
  "prompts_dir": "D:/.prompt-architect-memory/prompt-md",
  "initialized_at": "2026-10-14",
  "active_presets": ["dev-habits", "life-preferences"]
}
```

- `memory_dir`: Root directory for host memory files (`index.md`, `projects/`, `domains/`).
- `prompts_dir`: Archive directory where generated prompt markdown files are written (defaults to `<memory_dir>/prompt-md`). Users can customize this to any local path (e.g., a shared docs folder or project prompt directory).

### First-Time Bootstrap (`D-00`)

If `~/.prompt-architect.json` does not exist or `memory_dir` is unreachable:

1. Ask the user in `D-00`:
   - **D-00 [本机记忆库与提示词目录初始化]**: 检测到当前设备尚未绑定本地记忆目录。
     - 默认推荐记忆库目录：`~/.prompt-architect-memory`（或如 `D:\.prompt-architect-memory`）。
     - 默认生成的提示词目录：`<memory_dir>/prompt-md`。
     - 用户可自行决定/指定放置历史提示词的目录（`prompts_dir`）。
2. Once confirmed, automatically create the full directory structure on the host filesystem:
   - `<memory_dir>/index.md`
   - `<memory_dir>/projects/`
   - `<memory_dir>/domains/`
   - `<prompts_dir>/` (defaults to `<memory_dir>/prompt-md/`)
3. Write `~/.prompt-architect.json` with the confirmed `memory_dir` and `prompts_dir`.

## 2. Directory Structure & Token Caps

Keep the host memory strictly structured and bounded to prevent token bloat:

- `<memory_dir>/index.md` (**Hard Cap: <= 50 lines**):
  Routing table mapping project aliases or domain keywords to a single relative file path.
- `<memory_dir>/projects/<project-name>.md` (**Hard Cap: <= 80 lines per file**):
  Hotspot map and permanent constraints for a specific engineering project.
- `<memory_dir>/domains/<domain-name>.md` (**Hard Cap: <= 80 lines per file**):
  Long-term preferences and accumulated insights for non-project domains (e.g., `travel.md`).
- `<prompts_dir>/` (Default: `<memory_dir>/prompt-md/`):
  Central archive for generated prompt markdown files (`.md`). Not subject to line caps, serves as the user's permanent prompt repository.

### Template for `index.md`

```markdown
# Host Memory Routing Index

## Projects
- `RG203` | 医用离心机/三维水箱后端移植 | `projects/RG203.md`
- `ZC802` | 高频电刀分析仪 Electron 前端 | `projects/ZC802.md`
- `ZC811-App` | 中测质控手持端 Tauri App | `projects/ZC811-App.md`

## Domains
- `travel` | 旅行与生活规划偏好 | `domains/travel.md`
```

### Template for `projects/<project-name>.md` (<= 80 lines)

```markdown
# Project Memory: <Project Name>

## 1. Environment & Root Paths (<= 5 lines)
- `$BACKEND_ROOT`: `D:\dev\python\ZCMIT_FLASK_APP`
- `$FRONTEND_ROOT`: `D:\FrontendProjects\RG203_UI`
- Tech Stack: Python (Flask/FastAPI), Modbus, Socket.IO

## 2. Core File Hotspots Top 10 (<= 15 lines)
- `driver/rg203_modbus.py`: Modbus frame parsing, serial reconnect, pointer logic
- `project/rg203_service.py`: Measurement worker threads & Socket.IO state push
- `project/rg203_scan.py`: Continuous/step measurement queue & segment calculation
- `config/RG203_modbus_config.json`: Register address map (74-3064) & read_time config
- `tests/generate_task_test_data.py`: Limit-aware test payload generator

## 3. External Resources & Debug Entrypoints (<= 10 lines)
- Apifox Project ID: `6666769`
- Hardware Debug Doc: `docs/rg203-hardware-debug.md`
- Serial Config: Fixed baud rate `921600` on real hardware

## 4. Permanent Project Redlines (<= 15 lines)
- Unify Socket.IO event names (e.g., `task-measure-state`, `repeat-measure-done`) and distinguish status via payload fields.
- Do not add mock slave logic for newly added hardware commands; test on real hardware.
- Keep user database files in OS user data directory to prevent overwrite during Electron app updates.
```

## 3. The "4 Keep / 4 Skip" Rule (四记四不记)

When updating a memory file in Step 4, apply these filtering rules:

### 4 Keep (必记高价值索引)

1. **Root paths & environment aliases**: Project directories, branch names, and build entrypoints.
2. **Top 10 high-frequency files**: Exact relative paths and a 10-word summary of what logic lives there.
3. **External contracts & debug endpoints**: MCP project IDs, design doc paths, hardware IPs/ports/baud rates.
4. **Verified project redlines**: Architectural decisions, UI constraints (e.g., no page scrolling on Linux touchscreens), and protocol quirks confirmed through debugging.

### 4 Skip (不记一次性噪音)

1. **Raw error stack traces or logs**: Never store traceback text or log dumps.
2. **One-off test parameters**: Do not store temporary task IDs or transient mock payloads.
3. **Deprecated or superseded assumptions**: When a hardware rule changes (e.g., baud rate confirmed as 921600 only), overwrite the old entry instead of keeping historical notes.
4. **Completed one-time todo items**: Once a bug or migration step is finished, do not keep its task description in memory unless it establishes a permanent rule.

## 4. State-Merge Overwrite Strategy

Never blindly append (`>>`) to memory files:

- Read the target `<project>.md` file.
- If a file path or rule already exists, update it in place.
- If the `Core File Hotspots Top 10` list exceeds 10 items, evict the least recently used entry so the file stays compact and under the 80-line limit.

## 5. Prompt File Archiving & Customization (提示词落盘与归档规范)

All generated execution prompts that require file persistence must adhere to these placement rules:

1. **Default Initialization Directory**:
   - During bootstrap or memory mounting, `prompt-architect` automatically ensures the presence of the default archive directory: `<memory_dir>/prompt-md/`.
2. **User Customization (`prompts_dir`)**:
   - Users can freely change where prompts are stored by setting `"prompts_dir"` in `~/.prompt-architect.json`.
   - Examples of valid custom directories:
     - `D:/.prompt-architect-memory/prompt-md` (Standard default)
     - `D:/dev/my-project/docs/prompts` (Project-specific docs)
     - `C:/Users/W/Documents/Prompts` (Central document archive)
   - If `prompts_dir` is not explicitly set, the agent defaults directly to `<memory_dir>/prompt-md`.
3. **Write Discipline**:
   - **Zero Scatter**: Never output or move generated prompt files to temporary or system folders (`Downloads`, `Desktop`, `/tmp/`).
   - **Naming Convention**: `<ProjectOrDomain>_<FeatureOrDefectShortDescription>_提示词.md`.
   - **Clickable Output**: Whenever a prompt file is created or updated, provide a clickable link using forward slashes (`[文件名](file:///<full_path>)`).

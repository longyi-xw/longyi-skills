# 知识库路径与配置

本技能**不假设任何绝对路径**。同一份档案要能在 Windows / macOS / Linux、公司电脑与个人电脑之间迁移，所以位置由用户在首次使用时决定，之后持久化到配置文件，不再重复询问。

## 配置文件

位置固定为用户主目录下的 `~/.project-retrospective.json`（Windows 上即 `%USERPROFILE%\.project-retrospective.json`，PowerShell 里是 `$HOME\.project-retrospective.json`）。选它是因为 `~` 在三个平台的 shell 里都能解析，且不依赖任何特定 agent 的配置目录。

```json
{
  "knowledgeBase": "D:/dev/knowledge",
  "author": {
    "name": "Longyi",
    "emails": ["shawnlong912@gmail.com", "longyi@company.com"],
    "githubLogin": "longyi-xw"
  },
  "defaults": {
    "language": "zh-CN",
    "resumeTarget": "前端 / 可视化"
  },
  "createdAt": "2026-09-03",
  "updatedAt": "2026-09-03"
}
```

- `knowledgeBase` —— **必填**，档案根目录。写正斜杠，Windows 上也能用。
- `author.emails` —— 用于 `git log --author` 识别本人提交。**多个邮箱都要收**（公司邮箱、GitHub noreply 邮箱），否则会漏统计。
- `defaults.resumeTarget` —— 汇总模式生成简历时的默认岗位方向，可留空。

配置文件损坏或字段缺失时，按缺什么问什么补全，不要整个重来。

## 解析顺序

逐级回退，命中即停：

1. **用户本次明确指定**的路径（「存到 X」）—— 用它，并询问是否更新配置
2. `~/.project-retrospective.json` 的 `knowledgeBase` —— **存在就直接用，不要再问**
3. 环境变量 `KNOWLEDGE_HOME`
4. 都没有 → 走下面的首次询问

```bash
# 一次性探测（命中即用）
cat ~/.project-retrospective.json 2>/dev/null
echo "$KNOWLEDGE_HOME"
```

## 首次询问

先探测建议值，把它作为默认选项呈上，别让用户从零想一个路径。

```bash
# 建议值探测，按优先级取第一个非空的
echo "$KNOWLEDGE_HOME"                     # 用户已有约定
echo "${DEV_HOME:+$DEV_HOME/knowledge}"    # 有 DEV_HOME（开发根目录）约定的机器
echo "$HOME/knowledge"                     # 通用回退，三平台都成立
```

Windows 上若 bash 不可用，等价的 PowerShell 探测：

```powershell
$env:KNOWLEDGE_HOME
if ($env:DEV_HOME) { "$env:DEV_HOME\knowledge" }
"$HOME\knowledge"
```

询问话术（一次问清，别分两轮）：

> 这是第一次使用项目复盘技能，需要确定档案存放位置。以后所有项目的复盘档案都会集中放在这里，方便累积和以后一次性生成简历。
>
> 检测到建议位置：`<探测值>`。用这个，还是你指定一个？
>
> 另外确认一下作者身份，用于识别哪些代码是你写的：git 里读到的邮箱是 `<git config user.email>`，还有其他邮箱吗（公司邮箱、GitHub noreply 邮箱）？

用户确认后：创建目录 → 写配置文件 → 回显路径 → 继续正常流程。**不要因为写配置就中断分析。**

```bash
mkdir -p "<知识库>/projects"
cat > ~/.project-retrospective.json <<'JSON'
{ ... }
JSON
```

## 目录布局

```
<知识库>/
├─ projects/
│  ├─ <项目名>/
│  │  ├─ INSIGHTS.md
│  │  ├─ experience.yml
│  │  ├─ RESUME-SNIPPET.md
│  │  └─ INTERVIEW.md
│  └─ <另一个项目>/
├─ PROFILE.md                      # 汇总模式产出：个人技术画像
└─ resume/
   └─ RESUME-<方向>-<日期>.md       # 汇总模式产出：简历初稿
```

**项目名归一化**：取仓库目录名 → 转小写 kebab-case（`MyProject_v2` → `my-project-v2`）。已存在同名目录但明显是另一个项目时，追加区分后缀（`-company`、`-2026`），并在 `experience.yml` 的 `project.repo` 里写清来源。

## 换机器 / 迁移

知识库目录整体可搬。搬完在新机器上第一次运行会因为找不到配置而询问，指到新位置即可——档案本身不含绝对路径，不会失效。

建议把知识库单独做成一个 git 仓库（私有）。档案里可能含公司项目信息，**不要推到公开仓库**；`experience.yml` 里 `project.confidentiality` 标为 `internal` 的项目尤其注意。

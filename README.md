# Kiseki

> 让每天的证据，显现长期的轨迹。

Kiseki 是一个本地优先、AI 辅助的个人日记与轨迹分析项目。它将每天的自然语言记录交给模型分析，生成整体体验分、基础属性向量、摘要、证据和置信度，并把原文与结果保存在本地 SQLite 数据库中。

名称来自日语 `きせき`：既可以是“轨迹”，也可以是“奇迹”。

## 当前状态

目前已经完成可使用的命令行原型：

- 使用 `add` 输入日期和当天感想。
- 使用 `add --file` 读取 UTF-8 的 Markdown 或文本日记。
- 通过环境变量连接一个 OpenAI-compatible API；当前个人配置使用千问兼容接口。
- 使用 Pydantic 校验结构化 JSON。
- 将原文和分析结果保存到本地 SQLite。
- 使用 `analyze <id>` 分析或重新分析已有记录，不会创建重复日记。
- 使用 `review <id>` 接受、修正或否决 AI 分析；Review 全程不调用模型。
- 使用 `list` 对照 AI 分数、最终有效分数和 Review 状态。
- 使用 `show` 查看原文、完整 AI 分析、人工 Review 和有效分数。
- 使用 `route list` 和 `route show <route_id>` 加载、校验并查看个人目标与路线配置。

基础模型分析链路、本地 Review 校准闭环和分析恢复流程已经可用。长期路线本轮只实现配置加载与查看，不生成路线分析、分数、进度或时间线；趋势曲线和图形界面尚未实现。

## 分析结果

每条已分析记录包含：

- 0 到 100 的整体体验分；信息不足时为 `null`。
- 技术成长。
- 人际资本。
- 信息增益。
- 社会参与。
- 身心状态。
- 自主感。
- 摘要、原文证据、置信度和警告。

模型只能根据原文判断，不应把没有写出的经历自动补成事实。输入过于简短时返回 `null` 和较低置信度是正常行为。

人工 Review 与 AI 原始结果分开保存：

- `accepted`：认可当前 AI 分析，最终分数使用 AI 值。
- `adjusted`：只保存人工覆盖的字段；未覆盖字段沿用 AI 值，`null` 表示人工判断证据不足。
- `rejected`：整次分析不参与最终分数。
- `unreviewed`：尚未 Review，暂时使用 AI 值。
- `stale`：旧 Review 对应的分析版本已变化，保留旧 Review 但忽略其覆盖，暂时使用当前 AI 值。

其中前三种写入 Review JSON，后两种由程序根据当前记录派生。Review 不修改日记原文，也不覆盖 `analysis_json`。

## 隐私与数据流

### 保存在本机的内容

- 日记原文。
- 模型名称。
- 模型返回的分析 JSON。
- 提示词版本、分析 revision 和独立的人工 Review JSON。
- 调用失败时的错误信息。
- API Key 和 API 配置。

日记和分析位于：

```text
data/kiseki.db
```

API 配置位于：

```text
.env
```

这些文件均已被 Git 忽略。

### 会发送给外部服务的内容

执行 `add` 或 `analyze` 时，程序会把以下内容发送到你配置的模型服务：

- 记录日期。
- 日记原文。
- Kiseki 的分析提示词和输出结构。

当前个人配置使用千问兼容接口，因此 `add` 和 `analyze` 的分析步骤并不是完全离线完成的。服务商是否以及如何留存请求数据，取决于对应服务的政策和账户设置。`review`、`list` 和 `show` 只读取或更新本地 SQLite，不发送日记内容，也不调用模型 API。

`route list` 和 `route show` 只读取本地目标与路线 YAML，不读取 `.env`、不调用模型，也不读取、初始化或修改日记数据库。个人目标和路线保存在已被 Git 忽略的 `private/` 中。

Kiseki 本身没有账号、云数据库或自动同步功能。

### 本地保护边界

`.gitignore` 可以防止密钥和日记被普通的 `git add .` 意外提交，但它不等于加密。SQLite 数据库目前是本地明文文件，能够读取你 Windows 账户文件的人也可能读取日记。

需要更强保护时，应优先使用系统磁盘加密、受保护的 Windows 账户以及安全的本地备份。

## 环境要求

- Python 3.13 或更高版本。
- [uv](https://docs.astral.sh/uv/)。
- 使用 `add`、`analyze` 时需要可用的 OpenAI-compatible API Key、Base URL 和模型名；本地查看与帮助命令不需要 API 配置。

安装 uv：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 初始化

进入项目目录并同步依赖：

```powershell
cd kiseki
uv sync
```

创建本地配置：

```powershell
Copy-Item .env.example .env
```

编辑 `.env`，填入自己的 API Key：

```dotenv
KISEKI_API_KEY=
KISEKI_BASE_URL=
KISEKI_MODEL=
```

不要把真实 API Key 写入 `.env.example`、README、源码或 Git commit。

## 使用

### 添加并分析记录

```powershell
uv run python app.py add
```

程序会提示：

```text
Date [2026-08-20]:
Text:
```

日期直接回车表示今天，也可以输入 `YYYY-MM-DD`。交互式 `Text` 当前是单行输入，可以在一行中粘贴完整感想。

程序先保存原文，再调用模型。成功时会显示：

```text
Saved record 1.
Analyzing record 1 with <configured model>...
Analysis completed in 14.8 seconds.
Analysis revision: 1
Overall score: 76
Summary: ...
Confidence: 0.82
```

SDK 请求超时设置为 120 秒，并关闭自动重试。等待期间会立即显示正在使用的模型，结束时显示实际耗时。如果模型调用或结果解析失败，原文仍会保存在数据库中，该记录会显示为 `Analysis failed.`，之后可用 `analyze <id>` 原地重试。

### 从 Markdown 或文本文件导入

支持 UTF-8 编码的 `.md` 和 `.txt`：

```powershell
uv run python app.py add --file private\2026-08-25.md
```

文件模式默认使用今天作为记录日期。也可以明确指定：

```powershell
uv run python app.py add --file "C:\path with spaces\journal.txt" --date 2026-08-24
```

程序会读取完整的多行内容，把文本复制到本地数据库，然后进入与交互输入相同的 AI 分析流程。源文件路径不会写入数据库，源文件也不会被修改或删除。

如果日记文件放在项目目录中，建议统一放进已被 Git 忽略的 `private/`，避免误提交。重复导入同一文件会创建新的记录，当前版本不自动去重。

### 分析或重新分析已有记录

```powershell
uv run python app.py analyze 1
```

将 `1` 替换为记录 ID。命令直接读取该记录已有的日期和原文，不要求重新输入，也不插入新记录：

- 尚未分析：立即开始分析。
- 上次分析失败且没有可用结果：原地重试，成功后清除旧错误。
- 已有成功分析：先显示当前模型和 revision，再询问 `Analyze again? [y/N]`；只有输入 `y` 或 `yes` 才继续。

每次成功分析都会原子增加 `analysis_revision`、更新模型与提示词版本，并清除最近错误。已有 Review JSON 会原样保留，但因为 revision 已变化，会派生为 `stale`，旧人工覆盖不会应用到新分析。失败只更新最近错误：原有 AI 分析、revision 和 Review 都保持不变；`show <id>` 会同时展示旧的有效分析和“最近一次重新分析失败”提示。

### 查看最近记录

```powershell
uv run python app.py list
```

默认显示最近 20 条记录的 ID、日期、AI 总分、最终有效总分、Review 状态和摘要。`rejected` 的最终分数显示为 `-`。

### 查看完整记录

```powershell
uv run python app.py show 1
```

将 `1` 替换为 `list` 中显示的实际记录 ID。输出会清楚分开原文、AI Analysis、User Review 和 Effective Scores。

### 校准 AI 分析

```powershell
uv run python app.py review 1
```

命令先显示 AI 摘要、整体分、六维分数及各自置信度，然后提供：

```text
[a] Accept / [e] Edit / [r] Reject / [s] Skip
```

直接回车默认为 Accept。Edit 会依次询问整体分和六个维度：回车沿用 AI 值，输入 `0` 到 `100` 保存人工覆盖，输入 `null` 将该项最终设为未知；如果七项都直接回车，则按 `accepted` 保存。Reject 要求填写原因。Skip 不写数据库；已有 Review 时会先显示旧值并确认是否覆盖。

Review 只操作本地数据，不调用 API，不修改日记原文，也不覆盖 AI 的完整分析结果。

### 查看帮助

```powershell
uv run python app.py --help
```

### 配置并查看长期目标与路线

程序默认读取项目根目录的 `private/goals.yaml` 和 `private/routes/*.yaml`，与启动命令时的工作目录无关。公开模板只用于说明格式，不会作为默认个人配置加载，也不会自动复制或生成目标。

首次配置可在 Windows PowerShell 中主动运行以下步骤。已存在的文件会保留；若已有配置，直接编辑它们即可：

```powershell
Set-Location E:\project\kiseki
New-Item -ItemType Directory -Path private\routes -Force | Out-Null
if (-not (Test-Path -LiteralPath private\goals.yaml)) {
    Copy-Item -LiteralPath docs\templates\goal-definition.example.yaml -Destination private\goals.yaml
}
if (-not (Test-Path -LiteralPath private\routes\agent-project.yaml)) {
    Copy-Item -LiteralPath docs\templates\route-definition.example.yaml -Destination private\routes\agent-project.yaml
}
notepad private\goals.yaml
notepad private\routes\agent-project.yaml
```

模板内容为虚构示例。请改成自己的目标背景、成功标准、约束和路线；路线的 `goal_id` 必须对应目标 `id`。一个目标文件可包含多个目标，每个路线文件定义一条路线。使用以下命令查看；第二条中的 ID 是模板路线 ID，修改配置 ID 后也要替换它：

```powershell
uv run python app.py route list
uv run python app.py route show agent-project-example
```

`route list` 按路线 ID 稳定排序，显示路线名称、所属目标及双方状态，暂停、完成目标或归档路线也可查看。`route show` 显示目标与路线的内容版本、背景、成功标准、约束、假设、关注维度、正向信号、成本和计算配置。这些都是配置定义，不是已产生的分析结果。

目标文件的 `schema_version` 为 `"0.1.0"`，路线为 `"0.2.0"`；每个目标和路线的内容 `version` 必须为正整数。`target_date` 使用带引号的合法 `YYYY-MM-DD` 或 `null`。字段类型、状态、重复 ID、目标引用、六维名称及信号范围均会校验，未知字段或结构版本也会报出文件和问题。`calculation` 当前只接受模板中的固定规则配置，不执行评分计算。

缺少 `private/goals.yaml` 会提示配置方法并以失败状态退出；目标配置有效但路线目录不存在或没有 `.yaml` 文件时，正常提示尚无路线。未知路线 ID 或无效配置会失败退出，不自动修复或迁移文件。

## GitHub 发布前检查

以下内容会被忽略：

- `.env` 和其他本地环境配置。
- `data/` 下的日记数据库及 SQLite 辅助文件。
- `private/`、`exports/` 和 `backups/`。
- 日志、虚拟环境、Python 缓存和常见密钥文件。

提交前运行：

```powershell
git status --short
git check-ignore -v .env data/kiseki.db
```

第二条命令应明确显示这两个文件由 `.gitignore` 排除。随后检查准备提交的文件：

```powershell
git add .
git status
git diff --cached
```

确认列表中没有 `.env`、`data/`、日记、导出文件或真实凭据后再 commit 和 push。

## 项目结构

```text
kiseki/
├── app.py              # argparse、终端输入和输出
├── database.py         # SQLite 建表、兼容升级和普通读写
├── model.py            # OpenAI-compatible API 调用和提示词
├── review.py           # Review 状态与有效分数纯业务函数
├── schema.py           # AI 与 Review 的 Pydantic 结构
├── route_schema.py     # 目标与路线配置的 Pydantic 结构
├── routes.py           # 本地 YAML 加载、校验和关联
├── route_cli.py        # 路线列表、详情和错误展示
├── pyproject.toml      # Python 项目与依赖
├── uv.lock             # 依赖锁定
├── .env.example        # 无密钥的配置模板
├── data/               # 本地日记，不进入 Git
├── private/            # 个人日记文件、目标和路线配置，不进入 Git
└── docs/               # 产品、架构、模板和路线图
```

详细设计见 [文档中心](docs/README.md)，当前实现状态见 [current-status.md](docs/current-status.md)。

## 当前限制

- 交互输入仅支持单行文本；多行内容可以通过 `.md` 或 `.txt` 文件导入。
- 一条记录只保存当前 AI 分析和当前 Review；没有分析历史表或 Review 历史。
- 没有编辑、删除、批量或自动重分析；目前仅支持手动 `analyze <id>`。
- 模型调用是同步前台任务，固定超时 120 秒且没有自动重试。
- 没有校准汇总、自动训练或自动调整提示词。
- 没有趋势曲线和长期路线计算。
- 路线目前只支持配置加载与查看，没有路线分析、独立存储、路线 Review 或时间线。
- 没有数据库加密和云端同步。
- 评分是模型基于有限文本给出的候选判断，不是客观测量。

## 下一步：目标与路线 MVP

日常使用和评分校准继续进行，长期路线 MVP 与数据积累并行开发。目标/路线配置加载与查看已经实现；下一阶段是单篇日记对应单条路线的证据分析与独立存储，之后才是独立人工确认和证据时间线。

详细范围见 [长期目标与路线 MVP 规格](docs/long-term-routes.md)。目标、路线、当日影响与长期积累分别表达不同含义；第一版不把每日分数累加成路线成功概率。

[目标配置样例](docs/templates/goal-definition.example.yaml) 和 [路线配置样例](docs/templates/route-definition.example.yaml) 仅展示支持的格式；个人配置由用户放在被 Git 忽略的 `private/`，与公开样例分开。

本轮没有调用真实模型，也不改动每日分析、Review 或数据库结构。UI 技术尚未定案，后续根据使用体验决定。

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
- 使用 `review <id>` 接受、修正或否决 AI 分析；Review 全程不调用模型。
- 使用 `list` 对照 AI 分数、最终有效分数和 Review 状态。
- 使用 `show` 查看原文、完整 AI 分析、人工 Review 和有效分数。

模型分析链路和本地 Review 校准闭环均已验证。长期路线、趋势曲线和图形界面尚未实现。

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

执行 `add` 时，程序会把以下内容发送到你配置的模型服务：

- 记录日期。
- 日记原文。
- Kiseki 的分析提示词和输出结构。

当前个人配置使用千问兼容接口，因此 `add` 的分析步骤并不是完全离线完成的。服务商是否以及如何留存请求数据，取决于对应服务的政策和账户设置。`review`、`list` 和 `show` 只读取或更新本地 SQLite，不发送日记内容，也不调用模型 API。

Kiseki 本身没有账号、云数据库或自动同步功能。

### 本地保护边界

`.gitignore` 可以防止密钥和日记被普通的 `git add .` 意外提交，但它不等于加密。SQLite 数据库目前是本地明文文件，能够读取你 Windows 账户文件的人也可能读取日记。

需要更强保护时，应优先使用系统磁盘加密、受保护的 Windows 账户以及安全的本地备份。

## 环境要求

- Python 3.13 或更高版本。
- [uv](https://docs.astral.sh/uv/)。
- 可用的 OpenAI-compatible API Key、Base URL 和模型名。

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
Overall score: 76
Summary: ...
Confidence: 0.82
```

如果模型调用失败，原文仍会保存在数据库中，该记录会显示为 `Analysis failed.`。

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
├── pyproject.toml      # Python 项目与依赖
├── uv.lock             # 依赖锁定
├── .env.example        # 无密钥的配置模板
├── data/               # 本地日记，不进入 Git
└── docs/               # 产品、架构、模板和路线图
```

详细设计见 [文档中心](docs/README.md)，当前实现状态见 [current-status.md](docs/current-status.md)。

## 当前限制

- 交互输入仅支持单行文本；多行内容可以通过 `.md` 或 `.txt` 文件导入。
- 一条记录只保存当前 AI 分析和当前 Review；没有分析历史表或 Review 历史。
- 没有编辑、删除和重新分析命令。
- 没有校准汇总、自动训练或自动调整提示词。
- 没有趋势曲线和长期路线计算。
- 没有数据库加密和云端同步。
- 评分是模型基于有限文本给出的候选判断，不是客观测量。

下一阶段应先连续使用一到两周，根据真实体验调整提示词和评分维度，再决定是否开发路线系统或图形界面。

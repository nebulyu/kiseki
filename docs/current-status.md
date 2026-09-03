# 当前状态

最后更新：2026-08-26

## 当前阶段

项目已完成 **Phase 1：可用的 CLI 原型**，进入 **Phase 2：个人试用与评分调整**。本地日记存储、OpenAI-compatible 模型分析、结构化结果保存和人工 Review 校准闭环已经可用；当前个人模型配置使用千问兼容接口。

## 已完成

- 确立 Kiseki 的基本定位：个人轨迹记录与长期选择分析。
- 确立“原文、证据、评分、路线状态分离”的核心数据观念。
- 选定最简原型形态：少量 Python 文件、一个模型 API、Pydantic 和 SQLite 单表存储。
- 明确原型优先，不预先建设 Provider 抽象、重试系统和完整测试套件。
- 设计目标功能、技术架构、路线图和第一批模板原型。
- 检查本地开发环境。
- 使用 uv 初始化 Python 3.13 项目，并安装、锁定 `openai`、`pydantic` 和 `python-dotenv`。
- 创建最小命令行入口，已验证 `uv run python app.py --help` 可以运行。
- 使用 Python 内置 `sqlite3` 在 `data/kiseki.db` 中自动创建 `daily_records` 单表。
- 实现 `add`、`list` 和 `show <id>`，支持保存日期与原文、列出最近记录和查看原文。
- 手动录入一条临时记录，并在两个新进程中通过 `list` 和 `show` 读取，确认记录可以跨进程持久化。
- 根据 `analysis-result.schema.json` 创建简单的 Pydantic 分析结果模型。
- 根据 `analysis-prompt.md` 构造系统提示词和用户提示词，并在 `model.py` 中直接调用一个 OpenAI-compatible Chat Completions API。
- 将 `add` 扩展为“保存原文、调用模型、校验 JSON、回写同一记录、显示结果”的流程；调用或校验失败时保留原文并记录错误。
- `list` 已支持显示总分和摘要，`show` 已支持显示完整分析；旧的未分析记录仍可正常读取。
- 为现有 `daily_records` 原地补充 `model`、`analysis_json` 和 `error_message` 三列，保留原有记录，不引入迁移工具。
- 显式关闭 OpenAI SDK 自动重试，未建立 Provider、工厂、JSON 修复或测试框架。
- 使用兼容性更广的 `json_object` 响应格式，并把完整 Pydantic Schema 放入提示词；当前本地配置已切换到千问兼容接口，配置值不进入文档或数据库。
- 扩展 `.gitignore`，排除 API 配置、个人数据库、SQLite 辅助文件、导出、备份、日志和常见密钥文件。
- 为 `add` 增加 `--file` 和 `--date`，支持读取 UTF-8 的 `.md`/`.txt` 多行日记并进入现有分析流程。
- 增加 `review <id>`，支持 Accept、Edit、Reject 和 Skip；直接回车默认 Accept，Edit 支持数字与显式 `null` 覆盖。
- 在 `schema.py` 中增加独立的 Review、分数字段和有效结果 Pydantic 结构；`accepted`、`adjusted`、`rejected` 为持久化状态，`unreviewed`、`stale` 为派生状态。
- 在 `daily_records` 中兼容增加 `prompt_version`、`analysis_revision` 和 `review_json`；新分析成功保存时 revision 原子加一，旧 Review 保留并在版本变化后派生为 stale。
- 将 SQLite 建表、升级和普通读写拆到 `database.py`，将无终端 I/O 的 Review 状态判断与有效分数计算放到 `review.py`；未引入 ORM、Repository、Service 容器或迁移框架。
- `list` 已显示 AI、FINAL、REVIEW 和摘要；`show` 已分开显示原文、AI Analysis、User Review 和 Effective Scores。
- 使用临时 SQLite 和合成分析验证 accepted、adjusted、显式 null、rejected、stale、旧表升级、revision 增加和旧 Review 保留；Review 路径在模型函数被设为“调用即失败”时仍成功，确认不会调用 API。

## 本地开发环境概况

| 能力 | 当前状态 |
| --- | --- |
| Git | 已安装 |
| Python 3.13 | 已安装，当前默认解释器来自 Anaconda |
| Node.js 与 pnpm | 已安装，暂不用于 CLI 原型 |
| SQLite CLI | 已安装，Python 也自带 `sqlite3` |
| Rust、MSVC、WebView2 | 已安装，可支持未来的 Tauri 阶段 |
| VS Code | 已安装，Python 与 Rust 开发扩展基本齐全 |
| uv | 已安装（0.12.5），用于项目环境、依赖管理和运行 |
| Ollama | 尚未安装，当前不是必需项 |

全局 Python 环境中已经存在部分库，但原型不依赖这些全局 Anaconda 包。项目已使用 uv 创建独立虚拟环境。

## 尚未验证

- 模型对内容丰富的真实日记所给出的分数是否长期符合个人直觉。
- 连续使用一到两周后，各维度是否仍然有区分度和解释价值。
- 积累的 Review 是否足以支持后续校准汇总；本次没有实现汇总命令。

## 当前最近里程碑

最小评分校准闭环已经完成：

```text
输入原文 -> 保存并分析 -> 可选本地 Review -> list/show 显示最终有效分数
```

下一步里程碑仍是连续录入真实记录，通过 accepted、adjusted 和 rejected 观察评分偏差，再决定是否需要校准汇总或界面。

## 已知风险

- 模型可能在相同输入上产生明显不同的评分。
- 百分制容易制造虚假的精确感，需要评分锚点和置信度配合。
- 选定的 API 可能不完全遵循结构化输出要求，需要在实际使用中调整。
- 日记内容可能包含敏感信息，外部 API 调用必须显式配置。
- 分析 revision 变化会使旧 Review 变为 stale；当前需要用户重新确认，不自动迁移人工覆盖。
- 过早加入测试体系、通用抽象、路线、前端和本地模型会拖慢个人原型验证。

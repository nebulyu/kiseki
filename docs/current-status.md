# 当前状态

最后更新：2026-08-20

## 当前阶段

项目已完成 **Phase 1：可用的 CLI 原型**，进入 **Phase 2：个人试用与评分调整**。本地日记存储、DeepSeek 模型分析和结构化结果保存已经真实运行通过。

## 已完成

- 确立 Kiseki 的基本定位：个人轨迹记录与长期选择分析。
- 确立“原文、证据、评分、路线状态分离”的核心数据观念。
- 选定最简原型形态：少量 Python 文件、一个模型 API、Pydantic 和 SQLite 单表存储。
- 明确原型优先，不预先建设 Provider 抽象、重试系统和完整测试套件。
- 设计目标功能、技术架构、路线图和第一批模板原型。
- 检查本地开发环境。
- 使用 uv 初始化 Python 3.13 项目，并安装、锁定 `openai`、`pydantic` 和 `python-dotenv`。
- 创建最小 `app.py` 命令行入口，已验证 `uv run python app.py --help` 可以运行。
- 使用 Python 内置 `sqlite3` 在 `data/kiseki.db` 中自动创建 `daily_records` 单表。
- 实现 `add`、`list` 和 `show <id>`，支持保存日期与原文、列出最近记录和查看原文。
- 手动录入一条临时记录，并在两个新进程中通过 `list` 和 `show` 读取，确认记录可以跨进程持久化。
- 根据 `analysis-result.schema.json` 创建简单的 Pydantic 分析结果模型。
- 根据 `analysis-prompt.md` 构造系统提示词和用户提示词，并在 `model.py` 中直接调用 OpenAI-compatible Chat Completions API。
- 将 `add` 扩展为“保存原文、调用模型、校验 JSON、回写同一记录、显示结果”的流程；调用或校验失败时保留原文并记录错误。
- `list` 已支持显示总分和摘要，`show` 已支持显示完整分析；旧的未分析记录仍可正常读取。
- 为现有 `daily_records` 原地补充 `model`、`analysis_json` 和 `error_message` 三列，保留原有记录，不引入迁移工具。
- 显式关闭 OpenAI SDK 自动重试，未建立 Provider、工厂、JSON 修复或测试框架。
- 将 DeepSeek 不支持的 `json_schema` 响应格式调整为 `json_object`，并把完整 Pydantic Schema 放入提示词。
- 使用 `deepseek-v4-pro` 完成真实 API 调用；信息不足的测试输入得到 `overall_score: null` 和低置信度，符合当前评分规则。
- 扩展 `.gitignore`，排除 API 配置、个人数据库、SQLite 辅助文件、导出、备份、日志和常见密钥文件。

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

## 当前最近里程碑

模型分析与存储闭环已经完成：

```text
输入日期和原文 -> 保存原文 -> 调用模型 -> Pydantic 校验 -> 回写同一记录 -> 终端显示
```

下一步里程碑是连续录入真实记录，根据使用感受调整提示词和评分维度。

## 已知风险

- 模型可能在相同输入上产生明显不同的评分。
- 百分制容易制造虚假的精确感，需要评分锚点和置信度配合。
- 选定的 API 可能不完全遵循结构化输出要求，需要在实际使用中调整。
- 日记内容可能包含敏感信息，外部 API 调用必须显式配置。
- 过早加入测试体系、通用抽象、路线、前端和本地模型会拖慢个人原型验证。

# 技术架构

## 第一版原则

Kiseki 当前是个人原型，不是准备发布的通用平台。架构目标是尽快得到一个自己能连续使用的产品，而不是提前解决扩展性、多人协作和生产级容错。

第一版遵循以下规则：

- 能用少量文件完成，就不增加分层和接口。
- 只接入一个实际使用的模型 API。
- 只使用一个 SQLite 数据库和一张核心表。
- 不建立 Provider 系统、迁移框架、重试队列或测试目录。
- 发现真实需求后再拆分，而不是根据想象提前设计。

## 数据流

```mermaid
flowchart LR
    A["输入当天感想"] --> B["插入 daily_records"]
    B --> C["调用模型 API"]
    C --> D["Pydantic 解析 JSON"]
    D --> E["更新 analysis_json"]
    E --> F["终端显示评分"]
```

保存原文后再调用模型，是第一版唯一必要的失败保护。调用失败时显示错误，并在当前记录中留下错误信息即可，不建设独立状态机和自动重试机制。

## 计划目录

```text
kiseki/
├── app.py          # CLI 与主流程
├── database.py     # SQLite 建表和读写
├── model.py        # 直接调用选定的模型 API
├── schema.py       # Pydantic 输出结构
├── pyproject.toml
├── .env.example
├── data/
└── docs/
```

如果实现时一个文件更清楚，可以继续合并；不要求为了目录整齐创建空层级。

## CLI

第一版只需要三个操作：

```text
python app.py add
python app.py add --file <path> [--date YYYY-MM-DD]
python app.py list
python app.py show <id>
```

- `add`：交互输入日期和单行感想，调用模型并保存结果。
- `add --file`：读取 UTF-8 的 `.md`/`.txt` 完整内容；文件路径不写入数据库。
- `list`：查看最近记录的日期、总分和摘要。
- `show`：查看某条记录的原文和完整分析。

## 数据库

第一版使用 `data/kiseki.db`，启动时执行 `CREATE TABLE IF NOT EXISTS`。

### daily_records

| 字段 | 用途 |
| --- | --- |
| id | 本地自增 ID |
| entry_date | 记录所描述的日期 |
| raw_text | 当天输入的原文 |
| model | 使用的模型名称 |
| analysis_json | 模型返回并解析后的完整 JSON；尚无结果时为空 |
| error_message | 最近一次调用错误；成功时为空 |
| created_at | 创建时间 |

当前数据量很小，列表和详情可以直接读取并解析 `analysis_json`。暂时不拆分证据表、维度表和分析历史表。

## 模型输出

模型按照现有分析模板返回：

- 整体体验分。
- 六个基础维度。
- 摘要。
- 评分依据。
- 置信度。

Pydantic 的作用只是及时发现返回格式不符合预期，不在第一版建设复杂的校验恢复流程。解析失败时显示原始错误，保留日记原文，然后人工调整提示词或重新运行。

## 配置与隐私

- 从 `.env` 读取 `KISEKI_API_KEY`、`KISEKI_BASE_URL` 和 `KISEKI_MODEL`。
- `.env` 与 `data/kiseki.db` 不提交到 Git。
- API Key 不写入数据库。
- 使用外部模型时，日记原文会发送给对应服务商。

## 什么时候再扩展

只有在真实使用中出现明确需求时才增加：

- 需要保留多次分析结果时，再拆出分析历史表。
- 需要切换多个服务商时，再抽象 Model Provider。
- 数据结构频繁变化时，再引入迁移工具。
- CLI 确实影响持续记录时，再构建本地界面。
- 评分逻辑稳定后，再讨论自动化测试和评分评估集。

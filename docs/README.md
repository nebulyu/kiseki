# Kiseki 文档中心

本目录保存 Kiseki 的产品定义、工程约束、当前状态和可演化的模板原型。README 负责提供入口；这里的文档负责记录细节和决策依据。

## 文档地图

| 文档 | 用途 |
| --- | --- |
| [产品愿景](vision.md) | 说明 Kiseki 要解决的问题、产品边界和成功标准 |
| [功能范围](functional-scope.md) | 描述目标总功能和最简原型范围 |
| [当前状态](current-status.md) | 区分已经完成、正在进行和尚未实现的工作 |
| [技术架构](architecture.md) | 记录最简 CLI 原型及未来应用的架构 |
| [路线图](roadmap.md) | 说明从命令行原型到长期轨迹系统的演进顺序 |
| [开发环境](development/setup.md) | 记录 uv 安装、项目初始化和本地运行约定 |

## 模板原型

| 模板 | 用途 |
| --- | --- |
| [每日输入模板](templates/daily-entry.md) | 自然语言日记及可选上下文的输入格式 |
| [分析结果 Schema](templates/analysis-result.schema.json) | 模型结构化输出的 JSON Schema 原型 |
| [评分规则样例](templates/scoring-rubric.example.yaml) | 百分制和基础维度的评分锚点 |
| [路线定义样例](templates/route-definition.example.yaml) | 长期路线的权重、信号和时间窗口原型 |
| [分析提示词](templates/analysis-prompt.md) | 第一版模型调用的提示词契约 |

## 项目元信息

`meta/` 保存构建项目时需要持续维护的事实，而不是面向用户的宣传文案：

- [project.yaml](meta/project.yaml)：机器可读的项目阶段、技术选择和里程碑。
- [decisions.md](meta/decisions.md)：关键产品与工程决策记录。
- [glossary.md](meta/glossary.md)：核心术语及其稳定含义。

## 维护规则

1. 已实现状态只在 `current-status.md` 中声明，不把规划写成现有功能。
2. 修改评分语义时，同时更新评分模板、术语表和决策记录。
3. 修改架构或依赖边界时，更新 `architecture.md` 和 `project.yaml`。
4. 原型阶段优先保持文档与实际功能一致，不为了文档完整度增加实现复杂度。

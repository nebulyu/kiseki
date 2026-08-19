# 开发环境

## 为什么使用 uv

uv 是 Python 项目与依赖管理工具。它负责创建项目虚拟环境、安装依赖和运行命令；它不是 Kiseki 的应用框架，也不会参与模型评分。

使用 uv 的主要原因是隔离本机 Anaconda 全局环境，并让项目依赖能够在其他机器上复现。

## Windows 安装

官方独立安装器：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

如果希望先检查脚本内容：

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | more"
```

安装完成后关闭并重新打开终端，然后验证：

```powershell
uv --version
```

安装与升级方式以 [uv 官方安装文档](https://docs.astral.sh/uv/getting-started/installation/) 为准。使用独立安装器安装后，可通过以下命令升级：

```powershell
uv self update
```

## 计划中的项目初始化

以下命令将在开始实现 CLI 时执行，目前文档阶段不要求仓库已经包含这些文件：

```powershell
uv init --python 3.13
uv add openai pydantic python-dotenv
```

运行命令统一使用项目环境：

```powershell
uv run python app.py --help
```

不要直接向 Anaconda 的全局环境安装 Kiseki 依赖，也不要依赖当前全局环境中恰好存在的包。

## 模型配置约定

开发阶段从本地 `.env` 或进程环境读取：

```dotenv
KISEKI_API_KEY=
KISEKI_BASE_URL=https://api.deepseek.com
KISEKI_MODEL=deepseek-v4-pro
```

`.env` 必须被 Git 忽略。API Key 不得写入源码或数据库。

第一版直接调用一个选定的 OpenAI-compatible API，不设计 Provider 接口。更换模型时修改配置或少量调用代码即可。

## 第一阶段不需要的工具

- FastAPI、React 和 Tauri：CLI 验证完成后再引入。
- Docker：SQLite 和 Python 可以直接本地运行。
- Ollama：仅在验证本地模型时安装。
- PostgreSQL、Redis 和向量数据库：当前数据规模与功能不需要。

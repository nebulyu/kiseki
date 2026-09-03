import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from schema import AnalysisResult


PROMPT_VERSION = "0.1.0"
REQUEST_TIMEOUT_SECONDS = 120.0
SYSTEM_PROMPT = """你是 Kiseki 的每日记录分析器。你的任务是根据用户提供的原始记录，提取可追溯证据，并按照给定评分规则输出结构化候选分析。

约束：
1. 只能使用原文明确提供的信息，不补充背景事实，不进行心理或医疗诊断。
2. 每个判断尽量关联原文片段。无法从原文判断的分数必须为 null。
3. 0 到 100 是带锚点的候选评分，不代表客观真理。
4. 区分人际资本与社会参与，区分整体体验与成长积累。
5. 同时保留互相矛盾的证据，不为了生成单一叙事而删除负面或正面信息。
6. 置信度反映原文是否充分支持判断，不反映分数高低。
7. 输出必须完全符合提供的 JSON Schema，不输出额外字段或说明文字。"""


def build_user_prompt(entry_date: str, raw_text: str) -> str:
    return f"记录日期：{entry_date}\n\n原始记录：\n{raw_text}"


def _load_config() -> dict[str, str]:
    load_dotenv(Path(__file__).resolve().parent / ".env")

    config = {
        "KISEKI_API_KEY": os.getenv("KISEKI_API_KEY", "").strip(),
        "KISEKI_BASE_URL": os.getenv("KISEKI_BASE_URL", "").strip(),
        "KISEKI_MODEL": os.getenv("KISEKI_MODEL", "").strip(),
    }
    missing = [name for name, value in config.items() if not value]
    if missing:
        raise RuntimeError(f"Missing configuration: {', '.join(missing)}")
    return config


def get_model_name() -> str:
    return _load_config()["KISEKI_MODEL"]


def analyze_entry(entry_date: str, raw_text: str) -> tuple[str, AnalysisResult]:
    config = _load_config()

    model_name = config["KISEKI_MODEL"]
    schema_json = json.dumps(AnalysisResult.model_json_schema(), ensure_ascii=False)
    system_prompt = f"{SYSTEM_PROMPT}\n\n完整 JSON Schema：\n{schema_json}"
    with OpenAI(
        api_key=config["KISEKI_API_KEY"],
        base_url=config["KISEKI_BASE_URL"],
        max_retries=0,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ) as client:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": build_user_prompt(entry_date, raw_text)},
            ],
            response_format={"type": "json_object"},
        )

    if not response.choices:
        raise RuntimeError("Model returned no choices.")

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("Model returned no text content.")

    return model_name, AnalysisResult.model_validate_json(content, strict=True)

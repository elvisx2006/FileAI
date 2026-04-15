"""AI classifier — supports DeepSeek / OpenAI / Gemini with automatic fallback."""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from openai import OpenAI

from backend.config import get_config
from backend.models import ClassifyResult, FileInfo

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的macOS文件整理助手。你需要根据文件信息将每个文件精确分类到合适的目录。

## 可用分类目录

Documents/
  Work/ → Reports, Presentations, Spreadsheets, Contracts
  Personal/ → Finance, Medical, Legal, Resumes
  Study/ → Notes, Papers, Ebooks
  PDF/, Word/, Text/, Markdown/

Images/
  Screenshots/{YYYY-MM}, Photos/{YYYY-MM}
  Design/ → UI_Mockups, Icons, Illustrations
  Wallpapers/

Videos/
  Recordings/, Tutorials/, Entertainment/

Code/
  Projects/{项目名}, Scripts/, Configs/
  Data/ → CSV, JSON, SQL

Audio/
  Music/, Podcasts/, Recordings/

Archives/
  Compressed/, Disk_Images/, Backups/

Design/
  Figma/, Sketch/, PSD/, AI_Illustrator/, Fonts/

Installers/

Misc/Needs_Review/  (仅当确实无法分类时使用)

## 分类规则

1. 根据文件名关键词和扩展名综合判断
2. 对截图和照片，在路径末尾加上 YYYY-MM（用 modified_date 字段）
3. 如果文件名暗示某个项目，归入 Code/Projects/{推断的项目名}
4. confidence 取 0.0-1.0，低于 0.7 的归入 Misc/Needs_Review
5. 每个文件必须给出 reason（简短的中文分类理由）

## 输出格式

严格返回 JSON 对象，格式如下，不要包含任何其他文本：
{"files": [
  {
    "original_path": "文件完整路径",
    "target_folder": "目标分类路径",
    "confidence": 0.95,
    "reason": "简短理由"
  }
]}"""

PROVIDER_CONFIG = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "env_key": "DEEPSEEK_API_KEY",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "base_url": None,
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.0-flash",
    },
    "siliconflow": {
        "base_url": "https://api.siliconflow.cn/v1",
        "env_key": "SILICONFLOW_API_KEY",
        "default_model": "deepseek-ai/DeepSeek-V3",
    },
}

_clients: dict[str, OpenAI] = {}


def _get_client(provider: str = None, base_url: str = None) -> tuple[OpenAI, str]:
    """Get or create an OpenAI-compatible client for the given provider.
    Returns (client, model_name)."""
    config = get_config()
    provider = provider or config.ai.provider

    if provider in _clients:
        model = config.ai.model or PROVIDER_CONFIG.get(provider, {}).get("default_model", "deepseek-chat")
        return _clients[provider], model

    pconf = PROVIDER_CONFIG.get(provider, {})
    env_key = pconf.get("env_key", "OPENAI_API_KEY")
    api_key = os.environ.get(env_key, "")

    if not api_key:
        logger.error(f"API key not found for provider '{provider}' (env: {env_key}). Check your .env file.")

    resolved_base_url = base_url or config.ai.base_url or pconf.get("base_url")

    logger.info(f"Creating client: provider={provider}, base_url={resolved_base_url}, key={'SET' if api_key else 'MISSING'}")

    kwargs = {"api_key": api_key, "timeout": 60.0}
    if resolved_base_url:
        kwargs["base_url"] = resolved_base_url

    client = OpenAI(**kwargs)
    _clients[provider] = client

    model = config.ai.model or pconf.get("default_model", "deepseek-chat")
    return client, model


def _parse_response(raw: str, config) -> list[dict]:
    """Parse AI response, handling various JSON formats."""
    parsed = json.loads(raw)

    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("files", "results", "data", "items"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        for v in parsed.values():
            if isinstance(v, list):
                return v
    return []


def classify_with_ai(files: list[FileInfo], model: str = None) -> list[ClassifyResult]:
    if not files:
        return []

    config = get_config()
    client, default_model = _get_client()
    model = model or default_model

    file_data = [
        {
            "path": f.path,
            "name": f.name,
            "extension": f.extension,
            "size": f.size,
            "modified_date": f.modified_date,
        }
        for f in files
    ]

    user_msg = f"请分类以下 {len(file_data)} 个文件:\n{json.dumps(file_data, ensure_ascii=False, indent=2)}"

    try:
        create_kwargs = {
            "model": model,
            "temperature": 0.1,
            "max_tokens": 4096,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        }

        if config.ai.provider not in ("gemini",):
            create_kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**create_kwargs)
        raw = response.choices[0].message.content

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        items = _parse_response(raw, config)

        results = []
        for item in items:
            conf = float(item.get("confidence", 0.5))
            target = item.get("target_folder", "Misc/Needs_Review")
            if conf < config.ai.low_confidence_threshold:
                target = "Misc/Needs_Review"
            results.append(
                ClassifyResult(
                    original_path=item["original_path"],
                    target_folder=target,
                    confidence=conf,
                    reason=item.get("reason", ""),
                    source="ai",
                )
            )
        return results

    except Exception as e:
        logger.error(f"AI classification failed ({config.ai.provider}/{model}): {e}")
        return [
            ClassifyResult(
                original_path=f.path,
                target_folder="Misc/Needs_Review",
                confidence=0.0,
                reason=f"AI分类失败: {str(e)[:80]}",
                source="ai",
            )
            for f in files
        ]


def classify_batch(
    files: list[FileInfo],
    on_progress: "Callable[[int, int], None] | None" = None,
) -> list[ClassifyResult]:
    """Classify files in batches respecting the configured batch size."""
    config = get_config()
    batch_size = config.ai.batch_size
    all_results = []
    total = len(files)

    for i in range(0, total, batch_size):
        batch = files[i : i + batch_size]
        results = classify_with_ai(batch)
        all_results.extend(results)
        if on_progress:
            on_progress(min(i + batch_size, total), total)

    return all_results

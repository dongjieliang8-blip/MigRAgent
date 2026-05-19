"""Schema 对比 Agent - 对比源数据库与目标数据库的 Schema 差异"""

import json
from ..utils import call_llm

SYSTEM_PROMPT = """你是一个数据库 Schema 对比专家。
你的任务是分析源数据库和目标数据库的 Schema 定义，识别出两者之间的差异。
请以 JSON 格式返回分析结果，包含以下字段：
- added_tables: 新增的表列表
- removed_tables: 删除的表列表
- modified_tables: 修改的表列表（每个表包含 added_columns, removed_columns, modified_columns）
- added_indexes: 新增的索引列表
- removed_indexes: 删除的索引列表
- compatibility_score: 兼容性评分 (0-100)
- risk_level: 风险等级 (low/medium/high/critical)
- summary: 差异摘要说明
"""


def analyze(data: dict) -> dict:
    """分析源 Schema 与目标 Schema 的差异。

    Args:
        data: 包含 source_schema 和 target_schema 字典的输入数据

    Returns:
        Schema 对比分析结果的 JSON 字典
    """
    source_schema = data.get("source_schema", {})
    target_schema = data.get("target_schema", {})

    prompt = f"""请对比以下源数据库 Schema 和目标数据库 Schema，找出所有差异：

## 源数据库 Schema
```yaml
{json.dumps(source_schema, ensure_ascii=False, indent=2)}
```

## 目标数据库 Schema
```yaml
{json.dumps(target_schema, ensure_ascii=False, indent=2)}
```

请严格以 JSON 格式返回分析结果，不要添加额外的 markdown 标记。"""

    raw_result = call_llm(prompt, system_prompt=SYSTEM_PROMPT)

    try:
        # 尝试提取 JSON 部分
        result = _extract_json(raw_result)
    except (json.JSONDecodeError, ValueError):
        result = {
            "error": "无法解析 LLM 返回的结果",
            "raw_output": raw_result,
            "added_tables": [],
            "removed_tables": [],
            "modified_tables": [],
            "added_indexes": [],
            "removed_indexes": [],
            "compatibility_score": 0,
            "risk_level": "unknown",
            "summary": "解析失败，请检查输入 Schema 格式",
        }

    result["agent"] = "schema_diff"
    return result


def _extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON 内容。"""
    # 如果文本本身就是 JSON
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)

    # 尝试提取 ```json ... ``` 块
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    # 尝试提取 ``` ... ``` 块
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    # 尝试找到第一个 { 和最后一个 }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        return json.loads(text[first_brace : last_brace + 1])

    raise ValueError("未找到有效的 JSON 内容")

"""数据转换 Agent - 生成数据类型转换映射与转换策略"""

import json
from ..utils import call_llm

SYSTEM_PROMPT = """你是一个数据库数据转换专家。
你的任务是根据 Schema 对比结果，生成数据类型转换映射和转换策略。
请以 JSON 格式返回分析结果，包含以下字段：
- type_mappings: 源类型到目标类型的映射表
- data_conversions: 需要执行的数据转换操作列表（每项包含 table, column, source_type, target_type, conversion_rule）
- default_values: 需要填充默认值的字段
- truncation_warnings: 可能发生数据截断的字段警告
- estimated_duration: 预估转换耗时
- warnings: 转换风险警告列表
- summary: 转换策略摘要说明
"""


def analyze(data: dict) -> dict:
    """根据 Schema 对比结果生成数据转换策略。

    Args:
        data: 包含 schema_diff 结果和源/目标 Schema 的输入数据

    Returns:
        数据转换策略的 JSON 字典
    """
    schema_diff = data.get("schema_diff", {})
    source_schema = data.get("source_schema", {})
    target_schema = data.get("target_schema", {})

    prompt = f"""根据以下 Schema 对比结果，生成详细的数据类型转换策略：

## Schema 对比结果
```json
{json.dumps(schema_diff, ensure_ascii=False, indent=2)}
```

## 源数据库 Schema
```yaml
{json.dumps(source_schema, ensure_ascii=False, indent=2)}
```

## 目标数据库 Schema
```yaml
{json.dumps(target_schema, ensure_ascii=False, indent=2)}
```

请针对每个需要变更的字段，制定精确的类型转换规则，考虑以下因素：
1. 数据精度损失风险
2. 字符编码兼容性
3. NULL 值处理策略
4. 默认值填充规则
5. 外键约束影响

请严格以 JSON 格式返回结果，不要添加额外的 markdown 标记。"""

    raw_result = call_llm(prompt, system_prompt=SYSTEM_PROMPT)

    try:
        result = _extract_json(raw_result)
    except (json.JSONDecodeError, ValueError):
        result = {
            "error": "无法解析 LLM 返回的结果",
            "raw_output": raw_result,
            "type_mappings": {},
            "data_conversions": [],
            "default_values": [],
            "truncation_warnings": [],
            "estimated_duration": "unknown",
            "warnings": ["解析失败，请检查输入数据"],
            "summary": "解析失败",
        }

    result["agent"] = "data_transformer"
    return result


def _extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON 内容。"""
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)

    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return json.loads(text[start:end].strip())

    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1:
        return json.loads(text[first_brace : last_brace + 1])

    raise ValueError("未找到有效的 JSON 内容")

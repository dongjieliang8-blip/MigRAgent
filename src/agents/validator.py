"""一致性验证 Agent - 验证迁移结果的数据一致性和完整性"""

import json
from ..utils import call_llm

SYSTEM_PROMPT = """你是一个数据库迁移验证专家。
你的任务是根据迁移计划和 Schema 定义，生成完整的迁移后验证方案。
请以 JSON 格式返回分析结果，包含以下字段：
- validation_checks: 验证检查项列表（每项包含 check_id, type, description, sql_or_query, expected_result, severity）
- row_count_checks: 行数一致性检查列表
- checksum_checks: 数据校验和检查列表
- index_verification: 索引验证列表
- constraint_verification: 约束验证列表
- performance_baseline: 性能基准检查项
- go_nogo_decision: 是否满足上线标准的判定规则
- summary: 验证方案摘要说明
"""


def analyze(data: dict) -> dict:
    """根据迁移计划生成迁移后验证方案。

    Args:
        data: 包含 migration_plan, schema_diff, source/target Schema 的输入数据

    Returns:
        迁移验证方案的 JSON 字典
    """
    migration_plan = data.get("migration_plan", {})
    schema_diff = data.get("schema_diff", {})
    source_schema = data.get("source_schema", {})
    target_schema = data.get("target_schema", {})

    prompt = f"""根据以下迁移计划和 Schema 信息，生成完整的迁移后验证方案：

## 迁移计划
```json
{json.dumps(migration_plan, ensure_ascii=False, indent=2)}
```

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

请生成全面的验证方案，确保：
1. 数据完整性验证（行数、校验和、采样对比）
2. 结构完整性验证（表、列、索引、约束）
3. 数据一致性验证（外键关系、业务规则）
4. 性能基准验证（查询响应时间对比）
5. Go/No-Go 上线判定标准

请严格以 JSON 格式返回结果，不要添加额外的 markdown 标记。"""

    raw_result = call_llm(prompt, system_prompt=SYSTEM_PROMPT)

    try:
        result = _extract_json(raw_result)
    except (json.JSONDecodeError, ValueError):
        result = {
            "error": "无法解析 LLM 返回的结果",
            "raw_output": raw_result,
            "validation_checks": [],
            "row_count_checks": [],
            "checksum_checks": [],
            "index_verification": [],
            "constraint_verification": [],
            "performance_baseline": [],
            "go_nogo_decision": {"status": "unknown", "rules": []},
            "summary": "解析失败，请检查输入数据",
        }

    result["agent"] = "validator"
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

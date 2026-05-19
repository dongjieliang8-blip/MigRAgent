"""迁移规划 Agent - 生成数据库迁移执行计划"""

import json
from ..utils import call_llm

SYSTEM_PROMPT = """你是一个数据库迁移规划专家。
你的任务是根据 Schema 差异和数据转换策略，生成完整的数据库迁移执行计划。
请以 JSON 格式返回分析结果，包含以下字段：
- migration_steps: 迁移步骤列表（每项包含 step_id, action, target, sql_or_command, dependencies, rollback_plan, estimated_time）
- execution_order: 步骤执行顺序（DAG 拓扑排序）
- total_estimated_time: 总预估时间
- critical_path: 关键路径上的步骤 ID 列表
- rollback_strategy: 整体回滚策略
- prerequisites: 迁移前置条件列表
- post_checks: 迁移后检查项列表
- risk_assessment: 风险评估（overall_risk, high_risk_steps, mitigations）
- summary: 迁移计划摘要说明
"""


def analyze(data: dict) -> dict:
    """根据 Schema 差异和数据转换策略生成迁移执行计划。

    Args:
        data: 包含 schema_diff, data_transformer 结果和 Schema 信息的输入数据

    Returns:
        迁移执行计划的 JSON 字典
    """
    schema_diff = data.get("schema_diff", {})
    data_transformer = data.get("data_transformer", {})
    source_schema = data.get("source_schema", {})
    target_schema = data.get("target_schema", {})

    prompt = f"""根据以下信息，生成完整的数据库迁移执行计划：

## Schema 对比结果
```json
{json.dumps(schema_diff, ensure_ascii=False, indent=2)}
```

## 数据转换策略
```json
{json.dumps(data_transformer, ensure_ascii=False, indent=2)}
```

## 源数据库 Schema
```yaml
{json.dumps(source_schema, ensure_ascii=False, indent=2)}
```

## 目标数据库 Schema
```yaml
{json.dumps(target_schema, ensure_ascii=False, indent=2)}
```

请生成详细的迁移步骤，确保：
1. 步骤间依赖关系正确（先建表后加索引，先加列后填充数据）
2. 每个步骤都有回滚方案
3. 标识出关键路径和高风险步骤
4. 包含数据校验步骤
5. 考虑迁移窗口和停机时间

请严格以 JSON 格式返回结果，不要添加额外的 markdown 标记。"""

    raw_result = call_llm(prompt, system_prompt=SYSTEM_PROMPT)

    try:
        result = _extract_json(raw_result)
    except (json.JSONDecodeError, ValueError):
        result = {
            "error": "无法解析 LLM 返回的结果",
            "raw_output": raw_result,
            "migration_steps": [],
            "execution_order": [],
            "total_estimated_time": "unknown",
            "critical_path": [],
            "rollback_strategy": "unknown",
            "prerequisites": [],
            "post_checks": [],
            "risk_assessment": {
                "overall_risk": "unknown",
                "high_risk_steps": [],
                "mitigations": [],
            },
            "summary": "解析失败，请检查输入数据",
        }

    result["agent"] = "migration_planner"
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

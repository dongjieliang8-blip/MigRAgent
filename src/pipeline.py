"""MigRAgent 流水线编排 - 按顺序执行 4 个 Agent 完成数据库迁移分析"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import yaml

from .agents.schema_diff import analyze as schema_diff_analyze
from .agents.data_transformer import analyze as data_transformer_analyze
from .agents.migration_planner import analyze as migration_planner_analyze
from .agents.validator import analyze as validator_analyze


@dataclass
class PipelineResult:
    """流水线执行结果。"""

    schema_diff: dict = field(default_factory=dict)
    data_transformer: dict = field(default_factory=dict)
    migration_plan: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    errors: list = field(default_factory=list)
    status: str = "pending"

    def to_dict(self) -> dict:
        return {
            "schema_diff": self.schema_diff,
            "data_transformer": self.data_transformer,
            "migration_plan": self.migration_plan,
            "validation": self.validation,
            "elapsed_seconds": self.elapsed_seconds,
            "errors": self.errors,
            "status": self.status,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


class MigRAgentPipeline:
    """数据库迁移多 Agent 流水线。

    按顺序执行以下 4 个 Agent：
    1. Schema Diff Agent - Schema 差异对比
    2. Data Transformer Agent - 数据转换策略
    3. Migration Planner Agent - 迁移执行计划
    4. Validator Agent - 一致性验证方案
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.agents = [
            ("schema_diff", schema_diff_analyze),
            ("data_transformer", data_transformer_analyze),
            ("migration_planner", migration_planner_analyze),
            ("validator", validator_analyze),
        ]

    def run(self, input_path: str) -> PipelineResult:
        """运行迁移分析流水线。

        Args:
            input_path: Schema 配置文件路径 (YAML 或 JSON)

        Returns:
            PipelineResult 包含所有 Agent 的分析结果
        """
        start_time = time.time()
        result = PipelineResult()

        # 加载输入数据
        try:
            input_data = self._load_input(input_path)
        except Exception as e:
            result.errors.append(f"输入文件加载失败: {e}")
            result.status = "failed"
            result.elapsed_seconds = time.time() - start_time
            return result

        self._log(f"已加载输入文件: {input_path}")
        self._log(f"源数据库: {input_data.get('source_schema', {}).get('database', 'unknown')}")
        self._log(f"目标数据库: {input_data.get('target_schema', {}).get('database', 'unknown')}")
        self._log("-" * 50)

        # 逐步执行 Agent
        pipeline_data = dict(input_data)

        for agent_name, agent_func in self.agents:
            self._log(f"正在执行 [{agent_name}] Agent ...")
            try:
                agent_result = agent_func(pipeline_data)
                setattr(result, agent_name, agent_result)
                pipeline_data[agent_name] = agent_result
                self._log(f"[{agent_name}] 完成 - 状态: {agent_result.get('summary', 'N/A')[:80]}")
            except Exception as e:
                error_msg = f"[{agent_name}] 执行失败: {e}"
                self._log(error_msg)
                result.errors.append(error_msg)
                # 即使某个 Agent 失败，也继续执行后续步骤
                pipeline_data[agent_name] = {"error": str(e)}

            self._log("-" * 50)

        # 汇总结果
        result.elapsed_seconds = time.time() - start_time
        if result.errors:
            result.status = "partial_success"
        else:
            result.status = "success"

        self._log(f"流水线执行完成 - 状态: {result.status} - 耗时: {result.elapsed_seconds:.2f}s")
        return result

    def _load_input(self, input_path: str) -> dict:
        """加载输入文件 (YAML 或 JSON)。"""
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"输入文件不存在: {input_path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(content)
        elif path.suffix == ".json":
            return json.loads(content)
        else:
            # 默认尝试 YAML
            return yaml.safe_load(content)

    def _log(self, message: str):
        """日志输出。"""
        if self.verbose:
            print(f"[MigRAgent] {message}")

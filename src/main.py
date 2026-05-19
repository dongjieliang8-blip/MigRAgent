"""MigRAgent CLI 入口 - 数据库迁移 Agent 命令行工具"""

import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from .pipeline import MigRAgentPipeline


console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="MigRAgent")
def cli():
    """MigRAgent - 多 Agent 数据库迁移分析工具

    基于 LLM 的智能数据库迁移流水线，包含 Schema 对比、数据转换、迁移规划和一致性验证。
    """
    pass


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None, help="输出报告文件路径 (JSON)")
@click.option("--verbose", "-v", is_flag=True, default=False, help="显示详细执行日志")
def migrate(input_path: str, output: str, verbose: bool):
    """运行数据库迁移分析流水线。

    读取 Schema 配置文件，按顺序执行 4 个 Agent 完成完整的迁移分析：

    \b
    1. Schema Diff      - 对比源/目标 Schema 差异
    2. Data Transformer  - 生成数据类型转换策略
    3. Migration Planner - 生成迁移执行计划
    4. Validator         - 生成一致性验证方案

    \b
    示例:
        migragent migrate demo/sample_data/sample_schema.yaml
        migragent migrate schema.yaml -o report.json -v
    """
    console.print(
        Panel.fit(
            "[bold cyan]MigRAgent[/bold cyan] - 数据库迁移分析流水线",
            border_style="cyan",
        )
    )

    pipeline = MigRAgentPipeline(verbose=verbose)
    result = pipeline.run(input_path)

    # 打印摘要
    console.print()
    _print_summary(result)

    # 保存输出
    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.to_json())
        console.print(f"\n[green]报告已保存至: {output}[/green]")
    else:
        # 默认保存到输出目录
        default_output = Path("output") / "migration_report.json"
        default_output.parent.mkdir(parents=True, exist_ok=True)
        with open(default_output, "w", encoding="utf-8") as f:
            f.write(result.to_json())
        console.print(f"\n[dim]报告已保存至: {default_output}[/dim]")


@cli.command()
@click.argument("report_path", type=click.Path(exists=True))
@click.option("--format", "-f", "fmt", type=click.Choice(["summary", "detail", "json"]), default="summary", help="显示格式")
def report(report_path: str, fmt: str):
    """查看迁移分析报告。

    \b
    示例:
        migragent report output/migration_report.json
        migragent report output/migration_report.json -f detail
        migragent report output/migration_report.json -f json
    """
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if fmt == "json":
        console.print_json(json.dumps(data, ensure_ascii=False))
        return

    console.print(
        Panel.fit(
            f"[bold]迁移分析报告[/bold] - 状态: {data.get('status', 'unknown')}",
            border_style="blue",
        )
    )

    if fmt == "summary":
        _print_summary_from_dict(data)
    elif fmt == "detail":
        _print_detail_from_dict(data)


def _print_summary(result):
    """打印执行结果摘要。"""
    status_color = "green" if result.status == "success" else "yellow" if result.status == "partial_success" else "red"

    table = Table(title="流水线执行摘要", border_style="blue")
    table.add_column("Agent", style="cyan")
    table.add_column("状态", justify="center")
    table.add_column("摘要")

    agents_info = [
        ("Schema Diff", result.schema_diff),
        ("Data Transformer", result.data_transformer),
        ("Migration Planner", result.migration_plan),
        ("Validator", result.validation),
    ]

    for name, agent_result in agents_info:
        if agent_result.get("error"):
            status = "[red]失败[/red]"
            summary = agent_result["error"][:60]
        else:
            status = "[green]成功[/green]"
            summary = agent_result.get("summary", "N/A")[:60]
        table.add_row(name, status, summary)

    console.print(table)
    console.print(f"\n[bold {status_color}]总状态: {result.status}[/bold {status_color}] | 耗时: {result.elapsed_seconds:.2f}s")

    if result.errors:
        console.print(f"[red]错误数: {len(result.errors)}[/red]")
        for err in result.errors:
            console.print(f"  [red]- {err}[/red]")


def _print_summary_from_dict(data: dict):
    """从字典数据打印摘要。"""
    table = Table(title="流水线执行摘要", border_style="blue")
    table.add_column("Agent", style="cyan")
    table.add_column("摘要")

    for key, name in [
        ("schema_diff", "Schema Diff"),
        ("data_transformer", "Data Transformer"),
        ("migration_plan", "Migration Planner"),
        ("validation", "Validator"),
    ]:
        agent_data = data.get(key, {})
        summary = agent_data.get("summary", "N/A")[:80]
        table.add_row(name, summary)

    console.print(table)


def _print_detail_from_dict(data: dict):
    """从字典数据打印详细信息。"""
    for key, name in [
        ("schema_diff", "Schema Diff"),
        ("data_transformer", "Data Transformer"),
        ("migration_plan", "Migration Planner"),
        ("validation", "Validator"),
    ]:
        agent_data = data.get(key, {})
        if agent_data:
            console.print(f"\n[bold cyan]--- {name} ---[/bold cyan]")
            console.print_json(json.dumps(agent_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()

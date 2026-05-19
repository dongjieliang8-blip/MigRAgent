# MigRAgent — 数据库迁移 Agent

基于多 Agent 长链推理的数据库迁移系统。

## 安装

```bash
pip install -r requirements.txt
```

## 配置

在项目根目录创建 `.env` 文件：

```
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
DEEPSEEK_MODEL=mimo-v2.5
```

## 使用

```bash
# 运行数据库迁移分析
python -m src.main migrate --input ./demo/sample_data/sample_schema.yaml

# 查看报告
python -m src.main report --input ./output/migragent_report.json
```

## 项目结构

```
migragent/
├── src/
│   ├── main.py
│   ├── pipeline.py
│   ├── utils.py
│   └── agents/
│       ├── schema_diff.py
│       ├── data_transformer.py
│       ├── migration_planner.py
│       └── validator.py
├── demo/sample_data/
├── tests/
├── requirements.txt
└── APPLICATION.md
```

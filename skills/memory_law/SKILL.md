---
name: memory-law
description: 麒麟判官记忆检索技能 - 合同审查、合规咨询、风险评估
emoji: 🦄
metadata: {
  "agent": "law",
  "skill_name": "legal",
  "related_skills": ["molt"],
  "keywords": ["\u5408\u540c", "\u5408\u89c4", "\u6cd5\u5f8b", "\u98ce\u9669", "\u5ba1\u67e5"]
}
---

# 🦄 麒麟判官记忆检索

合同审查、合规咨询、风险评估

## 使用方法

### 检索相关记忆
```bash
# 检索与查询相关的记忆
node {baseDir}/scripts/retrieve.mjs "查询内容"

# 示例
node {baseDir}/scripts/retrieve.mjs "数据库方案讨论"
```

### 更新记忆索引
```bash
# 更新当前skill的记忆索引
node {baseDir}/scripts/update_index.mjs
```

## 检索策略

- **对话即检索**: 每次对话自动检索相关记忆
- **skill中心**: 只检索legal相关记忆
- **时间衰减**: 越近的记忆权重越高（7天衰减）
- **极简结果**: 返回最相关的5条记忆

## 相关技能

- 🐉 **德塔龙骑** (`molt`): 总指挥、团队协调、任务分发

## 配置说明

记忆索引配置在 `memory_index_config.json` 中，包含：
- 检索参数: max_results=5, decay_days=7
- 时间衰减: 线性+指数混合衰减
- 缓存策略: 300秒TTL缓存

## 数据来源

- 私有数据仓库: `opc_memory_data`
- 索引位置: `indexes/skills/legal.index.json`
- 记忆文档: `memory/daily/` + `memory/long_term/`

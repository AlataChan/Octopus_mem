---
name: memory-finance
description: 金蟾司库记忆检索技能 - 期权交易、财务管理、成本分析
emoji: 🐸
metadata: {
  "agent": "finance",
  "skill_name": "finance",
  "related_skills": ["molt"],
  "keywords": ["\u8d22\u52a1", "\u4ea4\u6613", "\u6210\u672c", "\u9884\u7b97", "\u5206\u6790"]
}
---

# 🐸 金蟾司库记忆检索

期权交易、财务管理、成本分析

## 使用方法

### 检索相关记忆
```bash
# 检索与查询相关的记忆
octopus-mem retrieve "查询内容" --skill finance

# 示例
octopus-mem retrieve "数据库方案讨论" --skill finance
```

### 更新记忆索引
The on-disk index file is updated automatically by `store_memory`. There is no separate reindex command; see `docs/ARCHITECTURE.md` for the rationale.

## 检索策略

- **对话即检索**: 每次对话自动检索相关记忆
- **skill中心**: 只检索finance相关记忆
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
- 索引位置: `memory/skill_indexes/finance.index.json`
- 记忆文档: `memory/daily/` + `memory/long_term/`

## Migration

The `.mjs` wrappers have been removed. Use `octopus-mem retrieve "..." --skill finance` directly. The existing `memory/skill_indexes/finance.index.json` file is still consumed unchanged by the retrieve command, so no rebuild is needed. See `docs/ARCHITECTURE.md` for the naming contract and why there is no reindex command.

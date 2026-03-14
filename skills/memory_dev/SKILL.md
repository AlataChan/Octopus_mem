---
name: memory-dev
description: 玄武铸甲记忆检索技能 - 代码开发、技术架构、部署运维
emoji: 🐢
metadata: {
  "agent": "dev",
  "skill_name": "development",
  "related_skills": ["molt", "ops"],
  "keywords": ["\u4ee3\u7801", "\u67b6\u6784", "\u90e8\u7f72", "\u6280\u672f", "\u5f00\u53d1"]
}
---

# 🐢 玄武铸甲记忆检索

代码开发、技术架构、部署运维

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
- **skill中心**: 只检索development相关记忆
- **时间衰减**: 越近的记忆权重越高（7天衰减）
- **极简结果**: 返回最相关的5条记忆

## 相关技能

- 🐉 **德塔龙骑** (`molt`): 总指挥、团队协调、任务分发
- 🐯 **白虎破阵** (`ops`): 用户增长、社交媒体、市场推广

## 配置说明

记忆索引配置在 `memory_index_config.json` 中，包含：
- 检索参数: max_results=5, decay_days=7
- 时间衰减: 线性+指数混合衰减
- 缓存策略: 300秒TTL缓存

## 数据来源

- 私有数据仓库: `opc_memory_data`
- 索引位置: `indexes/skills/development.index.json`
- 记忆文档: `memory/daily/` + `memory/long_term/`

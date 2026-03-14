# Octopus_mem

Octopus_mem 是一个面向 AI Agent 的**可解释、可迁移**记忆系统，核心是 **Skill-first 的记忆索引架构**：
先由 skill（能力/任务类型）限定检索范围，再从 memory（文本记忆库）中取回最相关片段，最后把结构化上下文交给 agent。

## 设计原则（默认极简）

- **文件即数据库**：以 `Markdown / JSON / JSONL` 为主（可读、可 diff、可备份）
- **最多 SQLite**：只有在确实需要关系查询/事务时才引入
- **索引可再生**：`indexes/` 可随时重建，`memory/` 才是源数据
- **可追溯**：索引条目必须能回指到具体文件与位置（路径/标题/时间）

## 目录约定（建议）

```
.
├── skills/                    # skill 定义与检索提示（human-written）
│   └── <skill_name>/SKILL.md
├── memory/                    # 记忆源数据（human/agent-written）
│   ├── MEMORY.md              # 长期记忆（汇总/原则/不随日期滚动）
│   └── daily/                 # 每日记忆（工作日志/对话/决策）
│       └── YYYY-MM-DD.md
├── indexes/                   # 由工具生成的索引（machine-written, 可重建）
│   ├── global.jsonl           # 全局索引（可选）
│   └── skills/                # 每个 skill 的局部索引（推荐）
│       └── <skill_name>.jsonl
└── tools/                     # 索引构建/检索工具（计划）
```

## Skill-first 检索流程（概念）

1. **路由到 skill**：根据问题选择 1~N 个可能相关的 `skill`
2. **读取 skill 索引**：优先查询 `indexes/skills/<skill>.jsonl`
3. **回表取原文**：根据索引条目的 `ref` 回到 `memory/` 中抓取片段
4. **必要时兜底**：再查 `indexes/global.jsonl`（或 SQLite）补全

## 索引条目（JSONL）建议字段

> 目标：可追溯、可合并、可增量更新；不强依赖 embedding。

```json
{
  "id": "mem_2026-03-14_0913",
  "ts": "2026-03-14T09:13:00+08:00",
  "skills": ["memory-indexing", "architecture"],
  "tags": ["原则", "检索", "索引"],
  "summary": "强调极简：jsonl+md，最多sqlite；并要求 skill-first 的记忆索引模式。",
  "ref": {
    "path": "memory/daily/2026-03-14.md",
    "anchor": "09:13 - 鑫哥对数据库方案的批评"
  }
}
```

## 灵感来源（参考）

- Anthropic 的 agent harness / repo 级记忆实践
- A-MEM（Zettelkasten 风格的动态链接与索引）
- Mem0（可扩展的记忆中心与检索接口）

## Roadmap（建议）

- v0：目录结构 + 文档（你现在看到的）
- v0.1：`tools/` 索引构建器（扫描 `skills/` 与 `memory/` 生成 JSONL）
- v0.2：skill 路由 + 片段抽取 + 上下文拼装（本地可用）
- v0.3：可选 SQLite 后端（仅在确有需求时）


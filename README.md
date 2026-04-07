# Octopus_mem - AI Agent记忆系统

## 🎯 项目概述

Octopus_mem是一个基于**skill + memory索引架构**的AI agent记忆系统，遵循"jsonl, md, 最多sqlite"的极简原则，采用**框架开源 + 数据私有化**的双仓库架构。

## 🏗️ 双仓库架构

### 1. 框架仓库 (公开)
- **仓库**: [Octopus_mem](https://github.com/AlataChan/Octopus_mem)
- **内容**: 记忆系统框架代码、工具、文档
- **许可证**: MIT
- **目标**: 开源共享，社区贡献

### 2. 数据仓库 (私有)  
- **仓库**: [opc_memory_data](https://github.com/AlataChan/opc_memory_data) (私有)
- **内容**: 实际记忆文档、工作日志、索引数据
- **权限**: 严格访问控制
- **目标**: 保护团队内部工作记忆

## ✨ 核心特性

### 1. 极简存储架构
- **Markdown**：长期记忆、知识库
- **JSON/JSONL**：配置、日志、会话记录
- **SQLite**：结构化数据（仅当需要时）

### 2. Skill + Memory索引
- 每个skill拥有独立的记忆索引
- 分层检索：skill索引 → 每日记忆 → 长期记忆
- 动态记忆链接和演化

### 3. 基于Anthropic研究
- 借鉴Anthropic Agent Harness架构
- 采用A-MEM论文的Zettelkasten方法
- 实现Mem0风格的可扩展记忆中心架构

## 系统架构

当前唯一的 Python 包路径是 `octopus_mem/`。规范目录树见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

- `octopus_mem/`：CLI 和 `MemoryManager`
- `memory/`：daily / long_term / skill_indexes 运行时数据
- `skills/`：6 个 agent 对应的记忆技能
- `tools/`：数据同步等辅助脚本

## 技术栈

- **语言**: Python 3.10+
- **存储**: Markdown, JSON/JSONL, SQLite
- **索引**: 基于关键词和语义的混合索引
- **检索**: 分层检索 + 语义相似度

## 设计原则

1. **简单性优先**: 避免过度设计，用最简单的工具解决问题
2. **渐进式升级**: 先用文件系统，需要时再加SQLite
3. **零成本运维**: 无需额外数据库服务
4. **易维护**: 文件系统最直观，备份迁移简单

## 使用场景

1. **AI Agent记忆管理**: 为OpenClaw等AI agent系统提供记忆能力
2. **Skill记忆索引**: 实现skill-specific的记忆检索
3. **知识库构建**: 构建可演化的知识网络
4. **对话历史管理**: 管理多轮对话的上下文记忆



## 🧠 Agent记忆索引技能

OPC团队每个agent都配备了专用的记忆索引技能：

| Agent | 神兽 | Skill名称 | 描述 | Emoji |
|-------|------|-----------|------|-------|
| molt | 德塔龙骑 | `memory-molt` | 总指挥、团队协调、任务分发 | 🐉 |
| dev | 玄武铸甲 | `memory-dev` | 代码开发、技术架构、部署运维 | 🐢 |
| content | 朱雀羽笔 | `memory-content` | 公众号文章、文案策划、内容创作 | 🔥 |
| ops | 白虎破阵 | `memory-ops` | 用户增长、社交媒体、市场推广 | 🐯 |
| law | 麒麟判官 | `memory-law` | 合同审查、合规咨询、风险评估 | 🦄 |
| finance | 金蟾司库 | `memory-finance` | 期权交易、财务管理、成本分析 | 🐸 |

### 使用示例

```bash
# 使用molt的记忆检索
cd projects/Octopus_mem/skills/memory_molt
node scripts/retrieve.mjs "团队协调任务"

# 使用dev的技术记忆检索  
cd projects/Octopus_mem/skills/memory_dev
node scripts/retrieve.mjs "技术架构设计"

# 更新ops的记忆索引
cd projects/Octopus_mem/skills/memory_ops
node scripts/update_index.mjs
```

### 集成到对话系统

每个agent在对话开始时自动检索相关记忆，遵循**对话即检索 + skill中心 + 时间衰减**原则。

## 🔄 数据同步

### 设置数据仓库
```bash
# 1. 克隆框架仓库
git clone https://github.com/AlataChan/Octopus_mem.git
cd Octopus_mem

# 2. 初始化私有数据仓库（需要访问权限）
git submodule update --init --recursive

# 3. 检查同步状态
./tools/sync_data.sh status
```

### 日常同步命令
```bash
# 拉取最新数据
./tools/sync_data.sh pull

# 推送本地更改
./tools/sync_data.sh push

# 查看状态
./tools/sync_data.sh status
```

## 🚀 快速开始

```bash
# 克隆框架仓库
git clone https://github.com/AlataChan/Octopus_mem.git

# 安装依赖
cd Octopus_mem
pip install -e .

# 查看 CLI
octopus-mem --help

# 存储与检索
octopus-mem store "phase 1 smoke test" --type daily --skill dev
octopus-mem retrieve "phase 1" --skill dev
```

## 开发计划

### 第一阶段（v0.1.0）
- [ ] 基础记忆存储架构
- [ ] Skill记忆索引原型
- [ ] 基础检索功能

### 第二阶段（v0.2.0）
- [ ] 记忆演化机制
- [ ] 跨skill记忆链接
- [ ] 性能优化

### 第三阶段（v0.3.0）
- [ ] 记忆重要性评分
- [ ] 记忆衰减机制
- [ ] 可视化工具

## 贡献指南

欢迎提交Issue和Pull Request。请遵循以下规范：
1. 代码风格遵循PEP 8
2. 添加适当的单元测试
3. 更新相关文档

## 许可证

MIT License

## 致谢

- Anthropic的Agent Harness研究
- A-MEM论文的Zettelkasten方法
- Mem0的可扩展记忆架构

---

**使命**: 让AI agent拥有像章鱼一样灵活、分布式的记忆系统
**口号**: 记忆在，智能在

#!/usr/bin/env node
// 麒麟判官记忆检索脚本

const { execSync } = require('child_process');
const path = require('path');

// 获取查询参数
const query = process.argv[2];
if (!query) {
  console.error('请提供查询内容');
  console.log('用法: node retrieve.mjs "查询内容"');
  process.exit(1);
}

// 构建Python命令
const pythonScript = path.join(__dirname, '../../simple_memory_retriever.py');
const command = `python3 "${pythonScript}" --agent law --query "${query}"`;

try {
  // 执行Python检索
  const output = execSync(command, { encoding: 'utf-8' });
  
  // 解析输出
  const result = JSON.parse(output);
  
  // 格式化输出
  console.log(`🔍 🦄 麒麟判官记忆检索结果:`);
  console.log(`查询: "${query}"`);
  console.log(`找到 ${result.count} 条相关记忆\n`);
  
  if (result.memories && result.memories.length > 0) {
    result.memories.forEach((memory, index) => {
      console.log(`${index + 1}. [${memory.timestamp}] ${memory.content_preview}`);
      console.log(`   分数: ${memory.combined_score.toFixed(2)}, 来源: ${memory.source}`);
      console.log();
    });
  } else {
    console.log('未找到相关记忆');
  }
  
} catch (error) {
  console.error('检索失败:', error.message);
  
  // 返回空结果
  console.log(JSON.stringify({
    agent: 'law',
    query: query,
    count: 0,
    memories: [],
    error: error.message
  }));
}

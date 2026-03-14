#!/usr/bin/env node
// 麒麟判官索引更新脚本

const { execSync } = require('child_process');
const path = require('path');

console.log(`🔄 更新🦄 麒麟判官记忆索引...`);

try {
  // 运行数据同步工具
  const syncScript = path.join(__dirname, '../../tools/data_sync.py');
  const command = `python3 "${syncScript}" --agent law`;
  
  const output = execSync(command, { encoding: 'utf-8' });
  console.log(output);
  
  console.log(`✅ 麒麟判官索引更新完成`);
  
} catch (error) {
  console.error('索引更新失败:', error.message);
  process.exit(1);
}

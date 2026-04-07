#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记忆管理器 - Octopus_mem核心模块
负责记忆的存储、检索和管理
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib


class MemoryManager:
    """记忆管理器"""

    VALID_MEMORY_TYPES = {"daily", "long_term"}
    SKILL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9_\-]{0,62}[A-Za-z0-9])?$")
    
    def __init__(self, base_path: str = "."):
        """
        初始化记忆管理器
        
        Args:
            base_path: 基础路径
        """
        self.base_path = base_path
        self._init_directories()
        
    def _init_directories(self):
        """初始化目录结构"""
        directories = [
            "memory/long_term",
            "memory/daily",
            "memory/skill_indexes",
            "storage/logs",
        ]
        
        for directory in directories:
            os.makedirs(os.path.join(self.base_path, directory), exist_ok=True)
    
    def store_memory(self, content: str, memory_type: str = "daily", 
                    skill_name: Optional[str] = None, 
                    metadata: Optional[Dict] = None) -> str:
        """
        存储记忆
        
        Args:
            content: 记忆内容
            memory_type: 记忆类型 (daily/long_term)
            skill_name: 关联的skill名称
            metadata: 元数据
            
        Returns:
            记忆ID
        """
        self._validate_memory_type(memory_type)
        if skill_name is not None:
            self._validate_skill_name(skill_name)

        memory_id = self._generate_memory_id(content)
        timestamp = datetime.now().isoformat()
        
        # 构建记忆对象
        memory_obj = {
            "id": memory_id,
            "content": content,
            "timestamp": timestamp,
            "type": memory_type,
            "skill": skill_name,
            "metadata": metadata or {}
        }
        
        # 存储到文件系统
        if memory_type == "daily":
            date_str = datetime.now().strftime("%Y-%m-%d")
            file_path = os.path.join(self.base_path, f"memory/daily/{date_str}.md")
            self._append_to_markdown(file_path, content, memory_id, timestamp)
        else:
            file_path = os.path.join(self.base_path, "memory/long_term/MEMORY.md")
            self._append_to_markdown(file_path, content, memory_id, timestamp)
        
        # 如果有关联skill，更新skill索引
        if skill_name:
            self._update_skill_index(skill_name, memory_obj)
        
        # 记录到日志
        self._log_memory_storage(memory_obj)
        
        return memory_id
    
    def _generate_memory_id(self, content: str) -> str:
        """生成记忆ID"""
        hash_obj = hashlib.md5(content.encode())
        return f"mem_{hash_obj.hexdigest()[:8]}"
    
    def _append_to_markdown(self, file_path: str, content: str, 
                           memory_id: str, timestamp: str):
        """追加到Markdown文件"""
        entry = f"\n## {timestamp} [{memory_id}]\n\n{content}\n\n---\n"
        
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(entry)

    def _validate_memory_type(self, memory_type: str):
        """校验记忆类型"""
        if memory_type not in self.VALID_MEMORY_TYPES:
            raise ValueError(f"Invalid memory_type: {memory_type}")

    def _validate_skill_name(self, skill_name: str):
        """校验skill名称"""
        if not self.SKILL_NAME_PATTERN.fullmatch(skill_name):
            raise ValueError(f"Invalid skill_name: {skill_name}")
    
    def _update_skill_index(self, skill_name: str, memory_obj: Dict):
        """更新skill索引"""
        skill_dir = os.path.realpath(os.path.join(self.base_path, "memory/skill_indexes"))
        index_path = os.path.realpath(os.path.join(skill_dir, f"{skill_name}.index.json"))

        if os.path.commonpath([index_path, skill_dir]) != skill_dir:
            raise ValueError(f"Invalid skill_name path: {skill_name}")
        
        # 读取现有索引
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        else:
            index_data = {
                "skill_name": skill_name,
                "last_updated": datetime.now().isoformat(),
                "memory_entries": [],
                "statistics": {
                    "total_memories": 0,
                    "last_memory_id": None
                }
            }
        
        # 添加新记忆条目
        index_entry = {
            "id": memory_obj["id"],
            "timestamp": memory_obj["timestamp"],
            "content_preview": memory_obj["content"][:100] + "..." 
                               if len(memory_obj["content"]) > 100 
                               else memory_obj["content"],
            "search_text": memory_obj["content"].lower(),
            "tags": memory_obj["metadata"].get("tags", []),
            "source": f"memory/{memory_obj['type']}/{memory_obj['id']}"
        }
        
        index_data["memory_entries"].append(index_entry)
        index_data["last_updated"] = datetime.now().isoformat()
        index_data["statistics"]["total_memories"] = len(index_data["memory_entries"])
        index_data["statistics"]["last_memory_id"] = memory_obj["id"]
        
        # 保存索引
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    def _log_memory_storage(self, memory_obj: Dict):
        """记录记忆存储日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "store_memory",
            "memory_id": memory_obj["id"],
            "memory_type": memory_obj["type"],
            "skill": memory_obj.get("skill"),
            "content_length": len(memory_obj["content"])
        }
        
        log_path = os.path.join(self.base_path, "storage/logs/memory_operations.jsonl")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def retrieve_memory(self, query: str, skill_name: Optional[str] = None, 
                       limit: int = 5) -> List[Dict]:
        """
        检索记忆
        
        Args:
            query: 查询字符串
            skill_name: 指定skill名称
            limit: 返回结果数量限制
            
        Returns:
            记忆列表
        """
        results = []
        
        # 1. 如果指定skill，先查skill索引
        if skill_name:
            skill_results = self._search_skill_index(skill_name, query, limit)
            results.extend(skill_results)
        
        # 2. 如果结果不足，搜索每日记忆
        if len(results) < limit:
            daily_results = self._search_daily_memories(query, limit - len(results))
            results.extend(daily_results)
        
        # 3. 如果结果仍不足，搜索长期记忆
        if len(results) < limit:
            long_term_results = self._search_long_term_memories(query, limit - len(results))
            results.extend(long_term_results)
        
        return results[:limit]
    
    def _search_skill_index(self, skill_name: str, query: str, limit: int) -> List[Dict]:
        """搜索skill索引"""
        index_path = os.path.join(self.base_path, 
                                 f"memory/skill_indexes/{skill_name}.index.json")
        
        if not os.path.exists(index_path):
            return []
        
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        
        # 简单文本匹配（可以升级为语义搜索）
        query_words = set(query.lower().split())
        matched_entries = []
        
        for entry in index_data["memory_entries"]:
            search_text = entry.get("search_text", entry.get("content_preview", "").lower())
            tags_text = " ".join(entry.get("tags", [])).lower()
            score = sum(1 for word in query_words if word in search_text or word in tags_text)
            
            if score > 0:
                matched_entries.append({
                    "entry": entry,
                    "score": score,
                    "source": "skill_index"
                })
        
        # 按分数排序
        matched_entries.sort(key=lambda x: x["score"], reverse=True)
        
        return [item["entry"] for item in matched_entries[:limit]]
    
    def _search_daily_memories(self, query: str, limit: int) -> List[Dict]:
        """搜索每日记忆"""
        # 简化实现：搜索最近7天的记忆
        results = []
        query_words = set(query.lower().split())
        
        for i in range(7):
            date_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            file_path = os.path.join(self.base_path, f"memory/daily/{date_str}.md")
            
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 简单文本匹配
                if any(word in content.lower() for word in query_words):
                    results.append({
                        "id": f"daily_{date_str}",
                        "timestamp": date_str,
                        "content_preview": content[:200] + "..." 
                                          if len(content) > 200 else content,
                        "source": f"memory/daily/{date_str}.md"
                    })
                    
                    if len(results) >= limit:
                        break
        
        return results
    
    def _search_long_term_memories(self, query: str, limit: int) -> List[Dict]:
        """搜索长期记忆"""
        file_path = os.path.join(self.base_path, "memory/long_term/MEMORY.md")
        
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 简单实现：返回整个文件的前几段
        paragraphs = content.split("\n\n")
        query_words = set(query.lower().split())
        
        results = []
        seen_ids = set()
        for para in paragraphs:
            if para.strip() and any(word in para.lower() for word in query_words):
                memory_id = self._generate_memory_id(para)
                if memory_id in seen_ids:
                    continue
                seen_ids.add(memory_id)
                results.append({
                    "id": memory_id,
                    "timestamp": "长期记忆",
                    "content_preview": para[:200] + "..." 
                                      if len(para) > 200 else para,
                    "source": "memory/long_term/MEMORY.md"
                })
                
                if len(results) >= limit:
                    break
        
        return results
    
    def get_memory_statistics(self) -> Dict:
        """获取记忆统计信息"""
        stats = {
            "total_memories": 0,
            "by_type": {"daily": 0, "long_term": 0},
            "by_skill": {},
            "storage_size": {}
        }
        
        # 统计每日记忆
        daily_dir = os.path.join(self.base_path, "memory/daily")
        if os.path.exists(daily_dir):
            daily_files = [f for f in os.listdir(daily_dir) if f.endswith(".md")]
            stats["by_type"]["daily"] = len(daily_files)
            
            for file in daily_files:
                file_path = os.path.join(daily_dir, file)
                stats["storage_size"][file] = os.path.getsize(file_path)
        
        # 统计长期记忆
        long_term_file = os.path.join(self.base_path, "memory/long_term/MEMORY.md")
        if os.path.exists(long_term_file):
            stats["by_type"]["long_term"] = 1
            stats["storage_size"]["MEMORY.md"] = os.path.getsize(long_term_file)
        
        # 统计skill索引
        index_dir = os.path.join(self.base_path, "memory/skill_indexes")
        if os.path.exists(index_dir):
            index_files = [f for f in os.listdir(index_dir) if f.endswith(".index.json")]
            for file in index_files:
                skill_name = file.replace(".index.json", "")
                file_path = os.path.join(index_dir, file)
                
                with open(file_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
                
                stats["by_skill"][skill_name] = len(index_data["memory_entries"])
                stats["storage_size"][file] = os.path.getsize(file_path)
        
        stats["total_memories"] = sum(stats["by_type"].values())
        
        return stats


if __name__ == "__main__":
    # 示例用法
    mm = MemoryManager()
    
    # 存储记忆
    memory_id = mm.store_memory(
        content="鑫哥要求构建skill + memory索引的记忆系统",
        memory_type="daily",
        skill_name="memory_system",
        metadata={"tags": ["架构", "记忆系统", "skill索引"]}
    )
    
    print(f"存储的记忆ID: {memory_id}")
    
    # 检索记忆
    results = mm.retrieve_memory("skill memory索引", skill_name="memory_system")
    print(f"检索到 {len(results)} 条相关记忆")
    
    # 获取统计信息
    stats = mm.get_memory_statistics()
    print(f"记忆统计: {stats}")

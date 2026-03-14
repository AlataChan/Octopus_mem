#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据同步工具 - 管理框架仓库和数据仓库的同步
"""

import os
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
import hashlib


class DataSyncManager:
    """数据同步管理器"""
    
    def __init__(self, config_path: str = "data_repo_config.json"):
        """
        初始化同步管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.framework_dir = Path(".")
        self.data_dir = Path("./.data_temp")  # 临时数据目录
        
    def _load_config(self) -> dict:
        """加载配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return {
                "framework": {"name": "Octopus_mem", "type": "public"},
                "data": {"name": "opc_memory_data", "type": "private"},
                "sync": {"enabled": True, "interval": "daily"}
            }
    
    def setup_data_repository(self):
        """设置数据仓库"""
        print("🔧 设置数据仓库...")
        
        # 创建临时数据目录
        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化Git仓库
        self._run_git_command(["init"], cwd=self.data_dir)
        self._run_git_command(["branch", "-m", "main"], cwd=self.data_dir)
        
        # 添加remote
        data_url = self.config["data"]["url"]
        self._run_git_command(["remote", "add", "origin", data_url], cwd=self.data_dir)
        
        print(f"✅ 数据仓库已初始化: {data_url}")
    
    def migrate_existing_data(self):
        """迁移现有数据到私有仓库"""
        print("📦 迁移现有数据...")
        
        # 需要迁移的数据目录
        data_dirs = ["memory", "indexes"]
        
        for dir_name in data_dirs:
            src_dir = self.framework_dir / dir_name
            dst_dir = self.data_dir / dir_name
            
            if src_dir.exists():
                # 复制目录
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                shutil.copytree(src_dir, dst_dir)
                print(f"  ✅ 迁移: {dir_name}/")
                
                # 从框架仓库中删除（保留空目录）
                self._clean_framework_data(dir_name)
            else:
                # 创建空目录
                dst_dir.mkdir(parents=True, exist_ok=True)
                (dst_dir / ".gitkeep").touch()
                print(f"  📁 创建: {dir_name}/ (空)")
        
        # 创建README说明
        readme_content = """# OPC Memory Data

这是 OPC 团队的私有记忆数据存储仓库。

## 目录结构

- `memory/` - 记忆文档 (Markdown)
- `indexes/` - 记忆索引 (JSON/JSONL)

## 同步说明

此仓库与公开框架仓库 [Octopus_mem](https://github.com/AlataChan/Octopus_mem) 协同工作。

框架仓库包含：
- 记忆系统代码
- 工具和库
- 示例配置
- 文档和教程

## 安全说明

此仓库为私有，包含团队内部工作记忆，请勿公开分享。
"""
        
        readme_path = self.data_dir / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")
        
        print("✅ 数据迁移完成")
    
    def _clean_framework_data(self, dir_name: str):
        """清理框架仓库中的数据目录"""
        dir_path = self.framework_dir / dir_name
        
        if dir_path.exists():
            # 删除所有文件，保留目录结构
            for item in dir_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            
            # 创建.gitkeep文件
            (dir_path / ".gitkeep").touch()
    
    def commit_and_push_data(self, message: str = None):
        """提交并推送数据到私有仓库"""
        if message is None:
            message = f"chore: update memory data {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        print(f"📤 提交数据: {message}")
        
        # 添加所有文件
        self._run_git_command(["add", "."], cwd=self.data_dir)
        
        # 提交
        self._run_git_command(["commit", "-m", message], cwd=self.data_dir)
        
        # 推送到私有仓库
        try:
            self._run_git_command(["push", "-u", "origin", "main"], cwd=self.data_dir)
            print("✅ 数据已推送到私有仓库")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  推送失败，可能需要手动设置权限: {e}")
            print(f"   仓库URL: {self.config['data']['url']}")
    
    def update_framework_config(self):
        """更新框架仓库配置指向私有数据仓库"""
        print("⚙️  更新框架配置...")
        
        # 创建配置示例
        config_example = {
            "data_repository": {
                "type": "git",
                "url": self.config["data"]["url"],
                "branch": "main",
                "private": True
            },
            "local_paths": {
                "memory": "./memory",
                "indexes": "./indexes"
            },
            "sync": {
                "auto_pull": True,
                "auto_push": False,  # 手动推送以控制权限
                "encryption_key": "optional"
            }
        }
        
        config_path = self.framework_dir / "config" / "data_repo.example.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_example, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 配置示例已创建: {config_path}")
    
    def create_sync_script(self):
        """创建同步脚本"""
        print("📜 创建同步脚本...")
        
        sync_script = """#!/bin/bash
# 数据同步脚本
# 用法: ./sync_data.sh [pull|push|status]

set -e

DATA_DIR=".data_temp"
CONFIG_FILE="data_repo_config.json"

# 检查配置
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 配置文件 $CONFIG_FILE 不存在"
    exit 1
fi

case "$1" in
    pull)
        echo "从私有仓库拉取数据..."
        if [ -d "$DATA_DIR" ]; then
            cd "$DATA_DIR" && git pull origin main
        else
            echo "错误: 数据目录不存在，请先运行 setup.py"
        fi
        ;;
    push)
        echo "推送到私有仓库..."
        if [ -d "$DATA_DIR" ]; then
            cd "$DATA_DIR" && git add . && git commit -m "更新记忆数据" && git push origin main
        else
            echo "错误: 数据目录不存在，请先运行 setup.py"
        fi
        ;;
    status)
        echo "数据仓库状态:"
        if [ -d "$DATA_DIR" ]; then
            cd "$DATA_DIR" && git status
        else
            echo "数据目录未初始化"
        fi
        ;;
    *)
        echo "用法: $0 [pull|push|status]"
        echo ""
        echo "命令说明:"
        echo "  pull   从私有仓库拉取最新数据"
        echo "  push   推送本地数据到私有仓库"
        echo "  status 查看数据仓库状态"
        exit 1
        ;;
esac
"""
        
        script_path = self.framework_dir / "tools" / "sync_data.sh"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(sync_script)
        
        # 设置执行权限
        os.chmod(script_path, 0o755)
        
        print(f"✅ 同步脚本已创建: {script_path}")
    
    def _run_git_command(self, args, cwd=None):
        """运行Git命令"""
        cmd = ["git"] + args
        result = subprocess.run(
            cmd, 
            cwd=cwd or self.framework_dir,
            capture_output=True, 
            text=True,
            check=True
        )
        return result
    
    def run_full_setup(self):
        """运行完整设置流程"""
        print("=" * 60)
        print("🚀 Octopus_mem 数据私有化设置")
        print("=" * 60)
        
        try:
            self.setup_data_repository()
            self.migrate_existing_data()
            self.commit_and_push_data("chore: initial memory data migration")
            self.update_framework_config()
            self.create_sync_script()
            
            print("\n" + "=" * 60)
            print("✅ 设置完成！")
            print("=" * 60)
            print("\n仓库配置:")
            print(f"  框架仓库 (公开): {self.config['framework']['url']}")
            print(f"  数据仓库 (私有): {self.config['data']['url']}")
            print("\n下一步:")
            print("  1. 检查私有仓库权限设置")
            print("  2. 运行: ./tools/sync_data.sh status")
            print("  3. 根据需要调整同步配置")
            
        except Exception as e:
            print(f"\n❌ 设置失败: {e}")
            raise


if __name__ == "__main__":
    # 运行设置
    sync_manager = DataSyncManager()
    sync_manager.run_full_setup()
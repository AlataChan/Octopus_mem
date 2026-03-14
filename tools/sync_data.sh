#!/bin/bash
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

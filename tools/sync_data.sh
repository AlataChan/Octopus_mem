#!/bin/bash
# 数据同步脚本
# 用法: ./sync_data.sh [init|pull|push|status] [commit_message]

set -e

DATA_DIR=".data_temp"
CONFIG_FILE="data_repo_config.json"

# 检查配置
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 配置文件 $CONFIG_FILE 不存在"
    exit 1
fi

is_data_repo_ready() {
    [ -d "$DATA_DIR/.git" ] || [ -f "$DATA_DIR/.git" ]
}

case "$1" in
    init)
        echo "初始化私有数据仓库（submodule）..."
        git submodule update --init --recursive "$DATA_DIR"
        echo "✅ 完成: $DATA_DIR"
        ;;
    pull)
        echo "从私有仓库拉取数据..."
        if is_data_repo_ready; then
            (cd "$DATA_DIR" && git pull origin main)
        else
            echo "错误: 数据仓库未初始化，请先运行: $0 init"
            exit 1
        fi
        ;;
    push)
        echo "推送到私有仓库..."
        if is_data_repo_ready; then
            msg="${2:-chore: sync memory data $(date '+%Y-%m-%d %H:%M')}"
            cd "$DATA_DIR"
            git add -A
            if git diff --cached --quiet; then
                echo "✅ 无变更，无需推送"
                exit 0
            fi
            git commit -m "$msg"
            git push origin main
        else
            echo "错误: 数据仓库未初始化，请先运行: $0 init"
            exit 1
        fi
        ;;
    status)
        echo "数据仓库状态:"
        if is_data_repo_ready; then
            (cd "$DATA_DIR" && git status)
        else
            echo "数据目录未初始化"
        fi
        ;;
    *)
        echo "用法: $0 [init|pull|push|status] [commit_message]"
        echo ""
        echo "命令说明:"
        echo "  init   初始化私有数据仓库（submodule）"
        echo "  pull   从私有仓库拉取最新数据"
        echo "  push   推送本地数据到私有仓库"
        echo "  status 查看数据仓库状态"
        exit 1
        ;;
esac

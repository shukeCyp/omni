#!/usr/bin/env bash
set -euo pipefail

# 安装前端依赖（首次运行或依赖变更时）
(
  cd frontend
  if [ ! -d node_modules ]; then
    echo "[run.sh] 安装前端依赖..."
    npm install
  fi
  echo "[run.sh] 编译前端..."
  npm run build
)

# 创建虚拟环境并安装依赖（首次运行时）
if [ ! -d .venv ]; then
  echo "[run.sh] 创建虚拟环境..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# 检查是否需要安装/更新 Python 依赖
if [ -f requirements.txt ]; then
  if [ ! -f .venv/.pip_installed ]; then
    echo "[run.sh] 安装 Python 依赖..."
    pip install -r requirements.txt
    touch .venv/.pip_installed
  fi
fi

export GLIN_DEV_UI=1
echo "[run.sh] 启动应用..."
python main.py

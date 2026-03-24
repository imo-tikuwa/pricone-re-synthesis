#!/bin/bash
set -e

# Claude Code のインストール
curl -fsSL https://claude.ai/install.sh | bash -s stable

# 静的解析ツール・型チェック用ライブラリのインストール
# win32gui / pywin32 は Windows 専用のためインストールしない
sudo pip install --break-system-packages --root-user-action=ignore \
  ruff \
  mypy \
  numpy \
  opencv-python-headless \
  PyQt6 \
  pillow

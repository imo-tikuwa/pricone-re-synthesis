# 開発環境セットアップ

このプロジェクトは **2つの環境** を使い分けます。

| 環境 | 用途 |
|---|---|
| DevContainer (Linux) | コード編集・静的解析（ruff / mypy） |
| Windows（ホスト PC） | 実際の動作確認・テンプレート取得 |

---

## DevContainer 側（コード編集・静的解析）

### 前提

- Windows に [Docker Desktop](https://www.docker.com/products/docker-desktop/) がインストール済み
- VS Code に [Dev Containers 拡張機能](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) がインストール済み

### 手順

1. VS Code でこのリポジトリを開く
2. 右下に「Reopen in Container」が表示されたらクリック（または `Ctrl+Shift+P` → `Dev Containers: Reopen in Container`）
3. コンテナのビルドが完了すると自動的に依存パッケージがインストールされる

### 静的解析コマンド

```bash
# フォーマット
python -m ruff format src/ main.py tools/

# Lint チェック
python -m ruff check src/ main.py tools/

# 型チェック
python -m mypy src/ main.py
```

> ファイル保存時に ruff formatter が自動整形されます（Prettier 相当）。

### 注意

DevContainer 内では `win32gui` / `PyQt6` / `opencv-python`（ヘッドフル版）は動作しません。コード編集と静的解析のみに使用してください。

---

## Windows 側（動作確認・テンプレート取得）

### 前提

- Windows 11 / Windows 10
- cmd または PowerShell が使える

### 1. uv のインストール

cmd または PowerShell を開いて実行します。

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

ターミナルを一度閉じて開き直す（PATH を反映させるため）。

### 2. 依存パッケージのセットアップ

```
cd C:\path\to\pricone-re-synthesis

uv sync
```

`uv sync` が `pyproject.toml` を読んで以下をすべて自動で行います。

- Python 3.13 のダウンロード（システムへのインストール不要）
- 仮想環境の作成（`.venv/`）
- 依存パッケージのインストール（PyQt6 / OpenCV / pywin32 等）

### 3. 動作確認

```
uv run python -c "import cv2, PyQt6, win32gui, PIL; print('OK')"
```

`OK` と表示されれば準備完了。

---

## テンプレート素材の取得

テンプレートマッチングに必要な画像素材を取得するツールです。

```
uv run python tools/capture_templates.py --mode snapshot --screen S1
```

```
uv run python tools/capture_templates.py --mode capture --screen S1
```

```
uv run python tools/capture_templates.py --mode verify --screen S1
```

取得後に NPZ へまとめます。

```
uv run python tools/build_templates.py
```

---

## ローカルビルド（exe 生成）

GitHub Actions を使わずにローカルで `ultimate-synthesis.exe` を生成する手順です。

**前提:** `uv sync` 済みの Windows 環境。管理者権限は不要。

### 1. テンプレート NPZ を生成

```
uv run python tools/build_templates.py
```

### 2. Nuitka でビルド

```
uv run --with nuitka python -m nuitka --standalone --windows-console-mode=disable --windows-uac-admin --enable-plugin=pyqt6 --include-package=cv2 --include-data-dir=templates=templates --output-filename=ultimate-synthesis.exe --output-dir=dist main.py
```

`--with nuitka` により Nuitka は一時的にのみ使用され、`pyproject.toml` や `uv.lock` は変更されません。

ビルド完了後、`dist/main.dist/` フォルダが生成されます。配布時はこのフォルダごと zip にまとめてください。`main.dist/main.exe` が実行ファイルです。

> 初回ビルド時は Nuitka のダウンロードと C コンパイルが走るため数分かかります。

---

## プロジェクト構成

```
main.py                    # エントリーポイント
pyproject.toml             # 依存パッケージ・ruff・mypy 設定
src/
  core/
    constants.py           # 状態・ROI・コスト表等の定数
    capture.py             # win32gui スクリーンキャプチャ
    matcher.py             # OpenCV テンプレートマッチング
    evaluator.py           # 錬成結果評価
    automator.py           # win32api マウス操作
    state_machine.py       # QThread ステートマシン
  data/
    models.py              # データモデル（EquipmentData 等）
    equipment_master.py    # 装備マスターデータ
    loader.py              # マスターデータ公開
  gui/
    main_window.py         # PyQt6 メインウィンドウ
    widgets.py             # カスタムウィジェット
config/
  roi.json                 # ROI 座標定義
docs/
  DEVELOPMENT.md           # 本ドキュメント（開発環境セットアップ）
  STATE_DIAGRAM.md         # ステートマシン状態遷移図
snapshots/                 # ROI オーバーレイ付きスナップショット（Git 管理・画面ごとに上書き）
templates/                 # テンプレート画像（取得後に配置）
tools/
  capture_templates.py     # テンプレート素材取得スクリプト
  build_templates.py       # templates/ → templates.npz 生成
```

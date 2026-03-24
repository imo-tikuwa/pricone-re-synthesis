"""テンプレート NPZ ビルドスクリプト.

templates/ ディレクトリを走査し、グレースケール PNG を numpy 配列に変換して
templates/templates.npz として保存する。

カラー管理テンプレート（ui/lock/, ui/buttons/）は NPZ に含めない。
これらは TemplateMatcher.load_color_templates() で個別に読み込む。

Usage:
    python tools/build_templates.py
    python tools/build_templates.py --templates-dir templates --output templates/templates.npz
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def _trim_content(img: np.ndarray, padding: int = 2) -> np.ndarray:
    """輝度閾値でコンテンツ領域を検出し、余白をトリムして返す.

    テキスト系テンプレート（装備名・アクセサリー名・属性文字）の余白削除に使用する。
    コンテンツが検出できない場合は元画像をそのまま返す。

    Args:
        img: グレースケール画像。
        padding: トリム後に残す余白ピクセル数（上下左右）。

    """
    _, thresh = cv2.threshold(img, 30, 255, cv2.THRESH_BINARY)
    coords = cv2.findNonZero(thresh)
    if coords is None:
        return img
    x, y, w, h = cv2.boundingRect(coords)
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(img.shape[1], x + w + padding)
    y2 = min(img.shape[0], y + h + padding)
    return img[y1:y2, x1:x2]


# テキスト余白トリムを適用するテンプレートのプレフィックス
_TRIM_PREFIXES = ("equipment/",)


def build_templates(templates_dir: Path, output_path: Path) -> int:
    """templates/ を走査してグレースケール NPZ を生成する.

    Args:
        templates_dir: テンプレートのルートディレクトリ。
        output_path: 出力 NPZ ファイルのパス。

    Returns:
        格納したテンプレート数。

    """
    arrays: dict[str, np.ndarray] = {}

    # カラー管理ディレクトリ（NPZ に含めない）
    # ui/lock/ 全体と、色で活性/非活性を区別する synthesize ボタンのみ除外する。
    # OK/キャンセル/確定/再錬成/破棄など他のボタンはグレースケール NPZ に含める。
    color_only_prefixes = {"ui/lock", "ui/buttons/s1_synthesize"}

    for png_path in sorted(templates_dir.rglob("*.png")):
        rel = png_path.relative_to(templates_dir)
        key = rel.with_suffix("").as_posix()

        if any(key.startswith(prefix) for prefix in color_only_prefixes):
            print(f"  スキップ（カラー管理）: {key}")
            continue

        img = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"  警告: 読み込み失敗: {png_path}", file=sys.stderr)
            continue

        if any(key.startswith(p) for p in _TRIM_PREFIXES):
            trimmed = _trim_content(img)
            if trimmed.shape != img.shape:
                print(f"  追加: {key} {img.shape} → トリム後 {trimmed.shape}")
                img = trimmed
            else:
                print(f"  追加: {key} {img.shape}")
        else:
            print(f"  追加: {key} {img.shape}")

        arrays[key] = img

    if not arrays:
        print("警告: テンプレート画像が 1 件も見つかりませんでした。", file=sys.stderr)
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, **arrays)  # type: ignore[call-overload]
    print(f"\n{len(arrays)} 件のテンプレートを {output_path} に保存しました。")
    return len(arrays)


def main() -> int:
    parser = argparse.ArgumentParser(description="テンプレート NPZ ビルドスクリプト")
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=Path(__file__).parent.parent / "templates",
        help="テンプレートのルートディレクトリ（デフォルト: templates/）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="出力 NPZ ファイルのパス（デフォルト: <templates-dir>/templates.npz）",
    )
    args = parser.parse_args()

    templates_dir: Path = args.templates_dir
    output_path: Path = args.output or templates_dir / "templates.npz"

    if not templates_dir.exists():
        print(f"エラー: テンプレートディレクトリが存在しません: {templates_dir}", file=sys.stderr)
        return 1

    print(f"テンプレートディレクトリ: {templates_dir}")
    print(f"出力先: {output_path}")
    print()

    count = build_templates(templates_dir, output_path)
    return 0 if count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())

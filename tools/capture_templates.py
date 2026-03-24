"""テンプレート素材取得スクリプト (Windows 専用).

ゲーム画面をキャプチャして ROI を確認・切り出す開発ユーティリティ。

Usage:
    # ROI オーバーレイ確認（スナップショット保存）
    python tools/capture_templates.py --mode snapshot [--screen S1]

    # ROI 枠線なしの生スナップショット保存（数字テンプレート取得用参照）
    python tools/capture_templates.py --mode raw [--screen S1]

    # roi.json で template が定義されている ROI を一括キャプチャ
    python tools/capture_templates.py --mode capture  [--screen S1]

    # 保存済みテンプレートとのマッチングスコア確認
    python tools/capture_templates.py --mode verify   [--screen S1]

    # 装備テンプレートをキャプチャ（武器/防具/特殊アクセサリー: 装備名全体）
    python tools/capture_templates.py --mode equipment --id W0001
    python tools/capture_templates.py --mode equipment --id A0001
    python tools/capture_templates.py --mode equipment --id C1001

    # 属性アクセサリーのカタカナ名テンプレートをキャプチャ（5属性共通）
    python tools/capture_templates.py --mode equipment --id C0001

    # 属性文字テンプレートをキャプチャ（5属性それぞれ取得）
    python tools/capture_templates.py --mode element --element fire
    python tools/capture_templates.py --mode element --element water
    python tools/capture_templates.py --mode element --element wind
    python tools/capture_templates.py --mode element --element light
    python tools/capture_templates.py --mode element --element dark

    # サブステータス効果名テンプレートをキャプチャ（枠 0〜3 のいずれかを指定）
    python tools/capture_templates.py --mode substat --stat hp --slot 0
    python tools/capture_templates.py --mode substat --stat phys_atk --slot 1
    python tools/capture_templates.py --mode substat --stat mag_crit --slot 3

    # S2 錬成結果画面専用の効果名テンプレートをキャプチャ（全ステータス取得推奨）
    # ロックなし枠（--locked なし） → templates/substats/s2/<stat>.png
    # ロックあり枠（--locked あり） → templates/substats/s2/locked/<stat>.png
    python tools/capture_templates.py --mode substat_s2 --stat hp --slot 0
    python tools/capture_templates.py --mode substat_s2 --stat mag_crit --slot 0 --locked

    # サブステータス効果値テンプレートをキャプチャ
    # --category: weapon / armor / charm / weapon_special(pen のみ)
    # --scale:    hpdef / atkcrit / pen / tp
    # weapon の hpdef/atkcrit は weapon_special/ へ自動コピーされる
    python tools/capture_templates.py --mode stat_value \
        --category weapon --scale hpdef --value 0.5% --slot 0
    python tools/capture_templates.py --mode stat_value \
        --category weapon --scale atkcrit --value 0.8% --slot 0
    python tools/capture_templates.py --mode stat_value \
        --category weapon --scale pen --value 1 --slot 0
    python tools/capture_templates.py --mode stat_value \
        --category weapon_special --scale pen --value 4 --slot 0
    python tools/capture_templates.py --mode stat_value \
        --category armor --scale hpdef --value 1% --slot 0
    python tools/capture_templates.py --mode stat_value \
        --category charm --scale hpdef --value 0.25% --slot 0
    python tools/capture_templates.py --mode stat_value \
        --category charm --scale tp --value 1 --slot 0

    # 数字テンプレートをキャプチャ（マナ/EX錬成Pt の数字認識用）
    # --digit:  保存する数字（0〜9）
    # --color:  black（錬成前の黒文字）/ blue（錬成後の青文字）
    # --field:  mana（マナ）/ expt（EX錬成Pt）- デフォルト: mana
    # 実行後、候補画像が snapshots/ に保存されるので番号を確認して入力
    python tools/capture_templates.py --mode digit --digit 0 --color black
    python tools/capture_templates.py --mode digit --digit 5 --color black --field expt
    python tools/capture_templates.py --mode digit --digit 3 --color blue
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# プロジェクトルートを sys.path に追加
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.core.capture import ScreenCapture  # noqa: E402
from src.core.constants import WINDOW_TITLE  # noqa: E402

_CONFIG_PATH = _ROOT / "config" / "roi.json"
_TEMPLATES_DIR = _ROOT / "templates"
_SNAPSHOTS_DIR = _ROOT / "snapshots"

_VALID_ELEMENTS = ("fire", "water", "wind", "light", "dark")
_ELEMENT_KANJI = {"fire": "火", "water": "水", "wind": "風", "light": "光", "dark": "闇"}

# カテゴリ/スケールごとの発現しうる効果値（ゲーム内表示に合わせ末尾ゼロなし）
_STAT_VALUE_MAP: dict[tuple[str, str], tuple[str, ...]] = {
    ("weapon", "hpdef"): ("0.5%", "1%", "1.5%", "2%", "2.5%"),
    ("weapon", "atkcrit"): ("0.8%", "1.6%", "2.4%", "3.2%", "4%"),
    ("weapon", "pen"): ("1", "2", "3"),
    ("weapon_special", "pen"): ("1", "2", "3", "4", "5"),
    ("armor", "hpdef"): ("1%", "2%", "3%", "4%", "5%"),
    ("armor", "atkcrit"): ("0.5%", "1%", "1.5%", "2%", "2.5%"),
    ("armor", "pen"): ("1", "2", "3"),
    ("charm", "hpdef"): ("0.25%", "0.5%", "0.75%", "1%", "1.25%"),
    ("charm", "atkcrit"): ("0.4%", "0.8%", "1.2%", "1.6%", "2%"),
    ("charm", "tp"): ("1", "2", "3"),
}

# 再取得時の自動コピー先（同スケール・同色のカテゴリ）
# weapon/hpdef   → weapon_special/hpdef, armor/atkcrit（同スケール: 0.5%~2.5%）
# weapon/atkcrit → weapon_special/atkcrit（同スケール: 0.8%~4%）
# weapon/pen     → armor/pen（同スケール: 1~3）
_STAT_VALUE_COPY_TO: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("weapon", "hpdef"): [("weapon_special", "hpdef"), ("armor", "atkcrit")],
    ("weapon", "atkcrit"): [("weapon_special", "atkcrit")],
    ("weapon", "pen"): [("armor", "pen")],
}

_STAT_VALUE_CATEGORIES = ("weapon", "weapon_special", "armor", "charm")
_STAT_VALUE_SCALES = ("hpdef", "atkcrit", "pen", "tp")

# argparse choices 用: 全カテゴリの全値の和集合
_ALL_STAT_VALUES = tuple(sorted({v for vals in _STAT_VALUE_MAP.values() for v in vals}))


def _value_to_filename(value: str) -> str:
    """効果値文字列をファイル名に変換する. 例: "0.25%" → "0_25pct.png", "3" → "3.png"."""
    return value.replace(".", "_").replace("%", "pct") + ".png"


_VALID_STATS = (
    "hp",
    "phys_atk",
    "mag_atk",
    "phys_def",
    "mag_def",
    "phys_crit",
    "mag_crit",
    "phys_pen",
    "mag_pen",
    "tp_up",
)
_STAT_LABEL = {
    "hp": "HP",
    "phys_atk": "物理攻撃力",
    "mag_atk": "魔法攻撃力",
    "phys_def": "物理防御力",
    "mag_def": "魔法防御力",
    "phys_crit": "物理クリティカル",
    "mag_crit": "魔法クリティカル",
    "phys_pen": "物理防御貫通",
    "mag_pen": "魔法防御貫通",
    "tp_up": "TP上昇",
}


def load_roi_config(screen_filter: str | None = None) -> list[dict[str, Any]]:
    """config/roi.json から ROI 定義を読み込む."""
    if not _CONFIG_PATH.exists():
        print(f"エラー: ROI 設定ファイルが存在しません: {_CONFIG_PATH}", file=sys.stderr)
        return []

    with _CONFIG_PATH.open(encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    rois: list[dict[str, Any]] = data.get("rois", [])
    if screen_filter:
        rois = [r for r in rois if r.get("screen") == screen_filter]
    return rois


def snapshot_mode(frame: np.ndarray, rois: list[dict[str, Any]], screen_filter: str | None) -> None:
    """キャプチャ画像に ROI を色分けして表示・保存する."""
    overlay = frame.copy()

    # 非クリック可能（赤）→ クリック可能（黄）の順で描画し、黄が必ず最前面になるようにする
    for roi_def in sorted(rois, key=lambda r: r.get("clickable", False)):
        rect = roi_def.get("rect", [0, 0, 0, 0])
        if rect[2] <= 0 or rect[3] <= 0:
            # TBD（未定義 ROI）: グレー点線
            x, y = rect[0], rect[1]
            cv2.rectangle(overlay, (x, y), (x + 40, y + 20), (128, 128, 128), 1)
            continue

        x, y, w, h = rect
        clickable = roi_def.get("clickable", False)
        color = (0, 255, 255) if clickable else (0, 0, 255)  # 黄: クリック可能, 赤: 表示のみ

        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 1)
        label = roi_def.get("id", "?")
        cv2.putText(
            overlay, label, (x, y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA
        )

    _SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    name = screen_filter if screen_filter else "all"
    out_path = _SNAPSHOTS_DIR / f"{name}.png"
    cv2.imwrite(str(out_path), overlay)
    print(f"スナップショット保存: {out_path}")
    print(f"  定義済み ROI: {len(rois)} 件")
    clickable_count = sum(1 for r in rois if r.get("clickable"))
    print(f"  クリック可能: {clickable_count} 件（黄枠）")


def capture_mode(frame: np.ndarray, rois: list[dict[str, Any]]) -> None:
    """各 ROI を切り出して templates/ に PNG 保存する."""
    for roi_def in rois:
        rect = roi_def.get("rect", [0, 0, 0, 0])
        template_path = roi_def.get("template")
        if not template_path or rect[2] <= 0 or rect[3] <= 0:
            print(f"  スキップ（未定義）: {roi_def.get('id', '?')}")
            continue

        x, y, w, h = rect
        cropped = frame[y : y + h, x : x + w]

        rel = template_path.removeprefix("templates/")
        out_path = _TEMPLATES_DIR / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists():
            ans = input(f"  上書きしますか? {out_path} [y/N]: ").strip().lower()
            if ans != "y":
                print(f"  スキップ: {out_path}")
                continue

        cv2.imwrite(str(out_path), cropped)
        print(f"  保存: {out_path} ({w}x{h}px)")


def verify_mode(frame: np.ndarray, rois: list[dict[str, Any]]) -> None:
    """保存済みテンプレートとのマッチングを確認する."""
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    for roi_def in rois:
        template_path_str = roi_def.get("template")
        if not template_path_str:
            continue

        tmpl_path = _TEMPLATES_DIR / template_path_str.removeprefix("templates/")
        if not tmpl_path.exists():
            print(f"  テンプレート未存在: {tmpl_path}")
            continue

        tmpl = cv2.imread(str(tmpl_path), cv2.IMREAD_GRAYSCALE)
        if tmpl is None:
            print(f"  読み込み失敗: {tmpl_path}")
            continue

        rect = roi_def.get("rect", [0, 0, 0, 0])
        if rect[2] > 0 and rect[3] > 0:
            x, y, w, h = rect
            target = gray_frame[y : y + h, x : x + w]
        else:
            target = gray_frame

        if target.shape[0] < tmpl.shape[0] or target.shape[1] < tmpl.shape[1]:
            print(f"  テンプレートが ROI より大きいです: {roi_def.get('id', '?')}")
            continue

        result = cv2.matchTemplate(target, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        ok = "OK" if max_val >= 0.80 else "NG"
        print(f"  [{ok}] {roi_def.get('id', '?')}: score={max_val:.3f} loc={max_loc}")


def _load_roi_rect(roi_id: str) -> tuple[int, int, int, int]:
    """config/roi.json から指定 ID の rect を返す."""
    with _CONFIG_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    for entry in data.get("rois", []):
        if entry.get("id") == roi_id:
            r = entry["rect"]
            return (r[0], r[1], r[2], r[3])
    raise KeyError(f"ROI '{roi_id}' が roi.json に見つかりません")


def _save_crop(
    frame: np.ndarray, roi: tuple[int, int, int, int], out_path: Path, label: str
) -> bool:
    """フレームから ROI を切り出して保存する. 保存成功で True を返す."""
    x, y, w, h = roi
    if w <= 0 or h <= 0:
        print("エラー: ROI が未定義（TBD）です。roi.json を確認してください。")
        return False

    cropped = frame[y : y + h, x : x + w]
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        ans = input(f"  上書きしますか? {out_path} [y/N]: ").strip().lower()
        if ans != "y":
            print(f"  スキップ: {out_path}")
            return False

    cv2.imwrite(str(out_path), cropped)
    print(f"  保存: {out_path} ({w}x{h}px)  [{label}]")
    return True


def equipment_capture_mode(frame: np.ndarray, equipment_id: str) -> int:
    """指定装備 ID のテンプレートをキャプチャして保存する.

    武器/防具/特殊アクセサリー  → s1_equipment_name ROI → templates/equipment/<type>/<ID>.png
    属性アクセサリー (C0001 等)  → s1_equipment_charm_name ROI
                                   → templates/equipment/charm/<BASE_ID>.png
    """
    from src.data.equipment_master import EQUIPMENT_MAP

    eid = equipment_id.upper()

    # 属性アクセサリーのベース ID 検索（C0001 → C0001_fire などを参照）
    eq = EQUIPMENT_MAP.get(eid)
    is_elemental_base = False
    base_id = eid

    if eq is None:
        # "C0001" のように element サフィックスなしで渡された場合の検索
        for full_id, candidate in EQUIPMENT_MAP.items():
            if full_id.startswith(eid + "_") and candidate.element is not None:
                eq = candidate
                is_elemental_base = True
                base_id = eid
                break

    if eq is None:
        print(f"エラー: 装備 ID '{equipment_id}' が見つかりません。")
        print()
        print("有効な装備 ID 一覧:")
        seen_bases: set[str] = set()
        for full_id, e in sorted(EQUIPMENT_MAP.items()):
            if e.element is not None:
                b = full_id.rsplit("_", 1)[0]
                if b not in seen_bases:
                    seen_bases.add(b)
                    suffix = e.display_name[3:]  # "黎明火輪アルファ..." → "火輪アルファ..."
                    print(f"  {b:8s}  {suffix}  (属性アクセサリー)")
            else:
                print(f"  {full_id:8s}  {e.display_name}")
        return 1

    if is_elemental_base or (eq.element is not None):
        # 属性アクセサリー: カタカナ名 ROI を使用
        roi = _load_roi_rect("s1_equipment_charm_name")
        out_path = _TEMPLATES_DIR / "equipment" / "charm" / f"{base_id}.png"
        label = f"属性アクセサリー {base_id} カタカナ名  例: {eq.display_name}"
    else:
        # 武器・防具・特殊アクセサリー: 装備名全体 ROI を使用
        roi = _load_roi_rect("s1_equipment_name")
        type_dir = eq.type.value
        out_path = _TEMPLATES_DIR / "equipment" / type_dir / f"{eid}.png"
        label = eq.display_name

    print(f"対象装備: {label}")
    print(f"保存先  : {out_path}")
    _save_crop(frame, roi, out_path, label)
    return 0


def substat_capture_mode(frame: np.ndarray, stat: str, slot: int) -> int:
    """サブステータス効果名テンプレートをキャプチャして保存する.

    s1_substat_name_<slot> ROI → templates/substats/<stat>.png
    """
    roi = _load_roi_rect(f"s1_substat_name_{slot}")
    out_path = _TEMPLATES_DIR / "substats" / f"{stat}.png"
    label = f"{_STAT_LABEL[stat]}  (枠 {slot})"

    print(f"効果名  : {label}")
    print(f"保存先  : {out_path}")
    print(f"注意    : 枠 {slot} に「{_STAT_LABEL[stat]}」が表示された状態で実行してください。")
    _save_crop(frame, roi, out_path, label)
    return 0


def substat_s2_capture_mode(frame: np.ndarray, stat: str, slot: int, locked: bool) -> int:
    """S2 錬成結果画面専用の効果名テンプレートをキャプチャして保存する.

    ロックなし → S2_SUBSTAT_NAME_ROIS[slot] → templates/substats/s2/<stat>.png
    ロックあり → S2_SUBSTAT_NAME_ROIS[slot] → templates/substats/s2/locked/<stat>.png
    """
    from src.core.constants import S2_SUBSTAT_NAME_ROIS

    roi = S2_SUBSTAT_NAME_ROIS[slot]
    if locked:
        out_path = _TEMPLATES_DIR / "substats" / "s2" / "locked" / f"{stat}.png"
        lock_str = "ロックあり（アイコン込み）"
        note = "ロックアイコンが表示された状態"
    else:
        out_path = _TEMPLATES_DIR / "substats" / "s2" / f"{stat}.png"
        lock_str = "ロックなし"
        note = "ロックアイコンなしの状態"

    label = f"{_STAT_LABEL[stat]}（S2 {lock_str}）  枠 {slot}"

    print(f"効果名  : {label}")
    print(f"保存先  : {out_path}")
    print(f"注意    : S2 錬成結果画面で枠 {slot} に「{_STAT_LABEL[stat]}」が")
    print(f"          {note}で実行してください。")
    _save_crop(frame, roi, out_path, label)
    return 0


def stat_value_capture_mode(
    frame: np.ndarray, category: str, scale: str, value: str, slot: int
) -> int:
    """サブステータス効果値テンプレートをキャプチャして保存する.

    s1_substat_value_<slot> ROI → templates/stat_values/<category>/<scale>/<value>.png
    weapon の hpdef/atkcrit は weapon_special/ にも自動コピーされる。
    """
    key = (category, scale)
    valid_values = _STAT_VALUE_MAP.get(key)
    if valid_values is None:
        print(f"エラー: {category}/{scale} は無効な組み合わせです。")
        print("有効な組み合わせ:")
        for (cat, sc), vals in _STAT_VALUE_MAP.items():
            print(f"  {cat}/{sc}: {', '.join(vals)}")
        return 1

    if value not in valid_values:
        print(f"エラー: '{value}' は {category}/{scale} の有効な値ではありません。")
        print(f"有効な値: {', '.join(valid_values)}")
        return 1

    roi = _load_roi_rect(f"s1_substat_value_{slot}")
    filename = _value_to_filename(value)
    out_path = _TEMPLATES_DIR / "stat_values" / category / scale / filename

    print(f"カテゴリ: {category}/{scale}")
    print(f"効果値  : {value}  (枠 {slot})")
    print(f"保存先  : {out_path}")
    print(f"注意    : 枠 {slot} の効果値が「{value}」の状態で実行してください。")

    saved = _save_crop(frame, roi, out_path, value)

    if saved:
        for copy_cat, copy_scale in _STAT_VALUE_COPY_TO.get(key, []):
            copy_path = _TEMPLATES_DIR / "stat_values" / copy_cat / copy_scale / filename
            copy_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(out_path, copy_path)
            print(f"  コピー: {copy_path}")

    return 0


def raw_mode(frame: np.ndarray, screen_filter: str | None) -> None:
    """ROI 枠線なしの生スナップショットを保存する."""
    _SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"raw_{screen_filter}" if screen_filter else "raw"
    out_path = _SNAPSHOTS_DIR / f"{name}.png"
    cv2.imwrite(str(out_path), frame)
    print(f"生スナップショット保存: {out_path}")
    print(f"  サイズ: {frame.shape[1]}x{frame.shape[0]}px")


def digit_capture_mode(frame: np.ndarray, digit: str, color: str, field: str) -> int:
    """数字テンプレートをキャプチャして保存する.

    マナまたは EX錬成Pt の ROI 内から文字候補を自動検出し、ユーザーが選択した
    候補を templates/digits/<color>/<digit>.png に保存する。

    実行後に snapshots/digit_ref_<field>_<color>.png に候補番号入り参照画像が保存される。
    """
    from src.core.constants import EX_PT_AFTER_ROI, EX_PT_ROI, MANA_AFTER_ROI, MANA_ROI

    if color == "blue":
        roi = MANA_AFTER_ROI if field == "mana" else EX_PT_AFTER_ROI
    else:
        roi = MANA_ROI if field == "mana" else EX_PT_ROI
    x, y, w, h = roi
    if w <= 0 or h <= 0:
        print(f"エラー: {field} の ROI が未定義（TBD）です。roi.json を確認してください。")
        return 1

    region = frame[y : y + h, x : x + w].copy()

    if color == "black":
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    else:  # blue
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        binary = cv2.inRange(hsv, np.array([85, 60, 60]), np.array([135, 255, 255]))

    num_labels, _labels, stats, _ = cv2.connectedComponentsWithStats(binary)

    # 数字らしいサイズでフィルタ（カンマ等の小さい記号は除外）
    candidates: list[tuple[int, int, int, int, np.ndarray]] = []
    for i in range(1, num_labels):
        cx, cy, cw, ch, area = stats[i]
        if ch >= 4 and cw >= 2 and area >= 8 and ch <= h and cw <= w:
            crop = region[cy : cy + ch, cx : cx + cw].copy()
            candidates.append((cx, cy, cw, ch, crop))

    candidates.sort(key=lambda c: c[0])

    if not candidates:
        print("数字候補が見つかりませんでした。")
        print("ヒント: ゲーム画面が正しい状態か、--color が合っているか確認してください。")
        return 1

    # 候補番号入り参照画像を保存
    ref_img = region.copy()
    for idx, (cx, cy, cw, ch, _) in enumerate(candidates):
        cv2.rectangle(ref_img, (cx, cy), (cx + cw, cy + ch), (0, 255, 0), 1)
        cv2.putText(
            ref_img, str(idx), (cx, max(0, cy - 1)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1
        )

    _SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ref_path = _SNAPSHOTS_DIR / f"digit_ref_{field}_{color}.png"
    cv2.imwrite(str(ref_path), ref_img)
    print(f"参照画像保存: {ref_path}")
    print(f"候補数: {len(candidates)}")
    for idx, (cx, cy, cw, ch, _) in enumerate(candidates):
        print(f"  候補 {idx}: x={cx} y={cy} w={cw} h={ch}")
    print()

    ans = input(f"数字「{digit}」は何番目の候補ですか? (0〜{len(candidates) - 1}): ").strip()
    try:
        sel = int(ans)
        if not 0 <= sel < len(candidates):
            raise ValueError
    except ValueError:
        print("無効な入力です。スキップします。")
        return 1

    _, _, cw, ch, crop = candidates[sel]
    out_path = _TEMPLATES_DIR / "digits" / color / f"{digit}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        ans2 = input(f"  上書きしますか? {out_path} [y/N]: ").strip().lower()
        if ans2 != "y":
            print(f"  スキップ: {out_path}")
            return 0

    cv2.imwrite(str(out_path), crop)
    print(f"  保存: {out_path} ({cw}x{ch}px)")
    return 0


def element_capture_mode(frame: np.ndarray, element: str) -> int:
    """属性文字テンプレートをキャプチャして保存する.

    s1_equipment_element ROI → templates/equipment/element/<element>.png
    """
    if element not in _VALID_ELEMENTS:
        print(f"エラー: 属性 '{element}' が無効です。")
        print(f"有効な値: {', '.join(_VALID_ELEMENTS)}")
        return 1

    roi = _load_roi_rect("s1_equipment_element")
    out_path = _TEMPLATES_DIR / "equipment" / "element" / f"{element}.png"
    kanji = _ELEMENT_KANJI[element]

    print(f"属性    : {element} ({kanji})")
    print(f"保存先  : {out_path}")
    print("注意    : ゲーム画面に属性アクセサリーを選択した状態で実行してください。")
    _save_crop(frame, roi, out_path, f"属性文字 {kanji}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="テンプレート素材取得スクリプト")
    parser.add_argument(
        "--mode",
        choices=[
            "snapshot",
            "raw",
            "capture",
            "verify",
            "equipment",
            "element",
            "substat",
            "substat_s2",
            "stat_value",
            "digit",
        ],
        required=True,
        help="動作モード",
    )
    parser.add_argument(
        "--screen",
        type=str,
        default=None,
        help="対象画面 ID でフィルタ（snapshot/capture/verify 用。例: S1, S2）",
    )
    parser.add_argument(
        "--id",
        type=str,
        default=None,
        metavar="EQUIPMENT_ID",
        help="装備 ID（equipment モード用。例: W0001, A0001, C0001, C1001）",
    )
    parser.add_argument(
        "--element",
        type=str,
        default=None,
        choices=list(_VALID_ELEMENTS),
        help="属性キー（element モード用。fire/water/wind/light/dark）",
    )
    parser.add_argument(
        "--stat",
        type=str,
        default=None,
        choices=list(_VALID_STATS),
        metavar="STAT",
        help=f"効果名キー（substat モード用。{'/'.join(_VALID_STATS)}）",
    )
    parser.add_argument(
        "--slot",
        type=int,
        default=None,
        choices=[0, 1, 2, 3],
        help="サブステータス枠番号（substat / stat_value モード用。0〜3）",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=list(_STAT_VALUE_CATEGORIES),
        help="装備カテゴリ（stat_value モード用。weapon/weapon_special/armor/charm）",
    )
    parser.add_argument(
        "--scale",
        type=str,
        default=None,
        choices=list(_STAT_VALUE_SCALES),
        help="効果値スケール（stat_value モード用。hpdef/atkcrit/pen/tp）",
    )
    parser.add_argument(
        "--value",
        type=str,
        default=None,
        choices=list(_ALL_STAT_VALUES),
        metavar="VALUE",
        help="効果値文字列（stat_value モード用。例: 0.25%%, 1%%, 4）",
    )
    parser.add_argument(
        "--locked",
        action="store_true",
        default=False,
        help="ロックアイコンあり版テンプレート（substat_s2 モード用）",
    )
    parser.add_argument(
        "--digit",
        type=str,
        default=None,
        choices=list("0123456789"),
        help="数字テンプレートの数字（digit モード用。0〜9）",
    )
    parser.add_argument(
        "--color",
        type=str,
        default=None,
        choices=["black", "blue"],
        help="数字の文字色（digit モード用。black=錬成前, blue=錬成後）",
    )
    parser.add_argument(
        "--field",
        type=str,
        default="mana",
        choices=["mana", "expt"],
        help="数字読み取り対象フィールド（digit モード用。mana=マナ, expt=EX錬成Pt）",
    )
    args = parser.parse_args()

    # 各モードの必須引数チェック
    if args.mode == "equipment" and not args.id:
        parser.error("--mode equipment には --id が必要です。")
    if args.mode == "element" and not args.element:
        parser.error("--mode element には --element が必要です。")
    if args.mode == "substat" and not args.stat:
        parser.error("--mode substat には --stat が必要です。")
    if args.mode == "substat" and args.slot is None:
        parser.error("--mode substat には --slot が必要です。")
    if args.mode == "substat_s2" and not args.stat:
        parser.error("--mode substat_s2 には --stat が必要です。")
    if args.mode == "substat_s2" and args.slot is None:
        parser.error("--mode substat_s2 には --slot が必要です。")
    if args.mode == "stat_value" and not args.category:
        parser.error("--mode stat_value には --category が必要です。")
    if args.mode == "stat_value" and not args.scale:
        parser.error("--mode stat_value には --scale が必要です。")
    if args.mode == "stat_value" and not args.value:
        parser.error("--mode stat_value には --value が必要です。")
    if args.mode == "stat_value" and args.slot is None:
        parser.error("--mode stat_value には --slot が必要です。")
    if args.mode == "digit" and args.digit is None:
        parser.error("--mode digit には --digit が必要です。")
    if args.mode == "digit" and args.color is None:
        parser.error("--mode digit には --color が必要です。")

    capture = ScreenCapture(WINDOW_TITLE)
    if not capture.find_window():
        print(f"エラー: ゲームウィンドウ「{WINDOW_TITLE}」が見つかりません。", file=sys.stderr)
        print("ゲームを起動して究極錬成画面を開いてから再実行してください。", file=sys.stderr)
        return 1

    frame = capture.capture()
    if frame is None:
        print("エラー: キャプチャに失敗しました。", file=sys.stderr)
        return 1

    if args.mode == "equipment":
        return equipment_capture_mode(frame, args.id)

    if args.mode == "element":
        return element_capture_mode(frame, args.element)

    if args.mode == "substat":
        return substat_capture_mode(frame, args.stat, args.slot)

    if args.mode == "substat_s2":
        return substat_s2_capture_mode(frame, args.stat, args.slot, args.locked)

    if args.mode == "stat_value":
        return stat_value_capture_mode(frame, args.category, args.scale, args.value, args.slot)

    if args.mode == "digit":
        return digit_capture_mode(frame, args.digit, args.color, args.field)

    if args.mode == "raw":
        raw_mode(frame, args.screen)
        return 0

    rois = load_roi_config(args.screen)
    if not rois:
        print("警告: ROI 定義が見つかりませんでした。config/roi.json を確認してください。")

    print(f"モード: {args.mode}" + (f" | 画面: {args.screen}" if args.screen else ""))
    print(f"ROI 定義数: {len(rois)} 件")
    print()

    if args.mode == "snapshot":
        snapshot_mode(frame, rois, args.screen)
    elif args.mode == "capture":
        capture_mode(frame, rois)
    elif args.mode == "verify":
        verify_mode(frame, rois)

    return 0


if __name__ == "__main__":
    sys.exit(main())

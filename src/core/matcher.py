"""テンプレートマッチングモジュール (OpenCV)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt

logger = logging.getLogger(__name__)


def _value_to_key(value: str) -> str:
    """効果値文字列をテンプレートキーの末尾部分に変換する.

    例: "0.5%" → "0_5pct", "1%" → "1pct", "3" → "3"

    """
    if value.endswith("%"):
        return value[:-1].replace(".", "_") + "pct"
    return value


def _templates_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "templates"
    return Path(__file__).resolve().parent.parent.parent / "templates"


class TemplateNotFoundError(Exception):
    """テンプレート画像が見つからない場合の例外."""


class TemplateMatcher:
    """OpenCV テンプレートマッチングのラッパークラス.

    グレースケール TM（大半のテンプレート）とカラー TM（ロックアイコン・非活性ボタン）に対応する。
    テンプレートは NPZ ファイルまたは個別 PNG から読み込む。
    """

    def __init__(self) -> None:
        self._gray_templates: dict[str, np.ndarray] = {}
        self._color_templates: dict[str, np.ndarray] = {}

    def load_from_npz(self, npz_path: Path | None = None) -> None:
        """NPZ ファイルからグレースケールテンプレートを一括読み込みする.

        Args:
            npz_path: NPZ ファイルのパス。None の場合はデフォルトパスを使用。

        """
        path = npz_path if npz_path is not None else _templates_dir() / "templates.npz"
        if not path.exists():
            raise FileNotFoundError(
                f"テンプレート NPZ が見つかりません: {path}\n"
                "先に `python tools/build_templates.py` を実行してください。"
            )

        data = np.load(path, allow_pickle=False)
        for key in data.files:
            self._gray_templates[key] = data[key]
        logger.info("NPZ から %d 件のテンプレートを読み込みました", len(self._gray_templates))

    def load_color_templates(self, templates_dir: Path | None = None) -> None:
        """カラーテンプレートを読み込む.

        ui/lock/ 以下と ui/buttons/ 内のカラー管理テンプレートを対象とする。

        Args:
            templates_dir: templates/ ディレクトリのパス。None の場合はデフォルトを使用。

        """
        base = templates_dir if templates_dir is not None else _templates_dir()

        color_dirs = [
            base / "ui" / "lock",
            base / "ui" / "buttons",
        ]

        for dir_path in color_dirs:
            if not dir_path.exists():
                continue
            for png_path in dir_path.glob("*.png"):
                rel = png_path.relative_to(base)
                key = rel.with_suffix("").as_posix()
                img = cv2.imread(str(png_path), cv2.IMREAD_COLOR)
                if img is not None:
                    self._color_templates[key] = img
                    logger.debug("カラーテンプレート読み込み: %s", key)
                else:
                    logger.warning("カラーテンプレート読み込み失敗: %s", png_path)

    def load_single_png(self, template_id: str, png_path: Path, grayscale: bool = True) -> None:
        """個別 PNG ファイルを読み込む（開発・デバッグ用）.

        Args:
            template_id: テンプレートの識別子。
            png_path: PNG ファイルのパス。
            grayscale: True の場合はグレースケール変換して格納する。

        """
        flags = cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
        img = cv2.imread(str(png_path), flags)
        if img is None:
            raise TemplateNotFoundError(f"PNG 読み込み失敗: {png_path}")
        if grayscale:
            self._gray_templates[template_id] = img
        else:
            self._color_templates[template_id] = img

    def match(
        self,
        frame: npt.NDArray[np.uint8],
        template_id: str,
        roi: tuple[int, int, int, int] | None = None,
        threshold: float = 0.85,
    ) -> tuple[bool, float, tuple[int, int]]:
        """グレースケールテンプレートマッチングを実行する.

        Args:
            frame: BGRまたはグレースケールのキャプチャ画像。
            template_id: テンプレートの識別子。
            roi: (x, y, w, h) の ROI。None の場合は全体を対象とする。
            threshold: マッチング閾値。

        Returns:
            (matched, score, (x, y)):
                matched: 閾値以上の場合 True。
                score: マッチングスコア (0.0〜1.0)。
                (x, y): ROI 内でのマッチング位置（左上座標）。

        """
        if template_id not in self._gray_templates:
            logger.debug("テンプレートが存在しません: %s", template_id)
            return False, 0.0, (0, 0)

        tmpl = self._gray_templates[template_id]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame

        if roi is not None:
            x, y, w, h = roi
            if w <= 0 or h <= 0:
                logger.debug("ROI が未定義（TBD）: %s", template_id)
                return False, 0.0, (0, 0)
            target = gray[y : y + h, x : x + w]
        else:
            x, y = 0, 0
            target = gray

        if target.shape[0] < tmpl.shape[0] or target.shape[1] < tmpl.shape[1]:
            logger.debug("テンプレートが ROI より大きいです: %s", template_id)
            return False, 0.0, (0, 0)

        result = cv2.matchTemplate(target, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        matched = max_val >= threshold
        abs_loc = (max_loc[0] + (x if roi else 0), max_loc[1] + (y if roi else 0))
        return matched, float(max_val), abs_loc

    def match_color(
        self,
        frame: npt.NDArray[np.uint8],
        template_id: str,
        roi: tuple[int, int, int, int] | None = None,
        threshold: float = 0.80,
    ) -> tuple[bool, float, tuple[int, int]]:
        """カラーテンプレートマッチングを実行する.

        Args:
            frame: BGR のキャプチャ画像。
            template_id: カラーテンプレートの識別子。
            roi: (x, y, w, h) の ROI。
            threshold: マッチング閾値。

        Returns:
            (matched, score, (x, y))

        """
        if template_id not in self._color_templates:
            logger.debug("カラーテンプレートが存在しません: %s", template_id)
            return False, 0.0, (0, 0)

        tmpl = self._color_templates[template_id]

        if roi is not None:
            x, y, w, h = roi
            if w <= 0 or h <= 0:
                return False, 0.0, (0, 0)
            target = frame[y : y + h, x : x + w]
        else:
            x, y = 0, 0
            target = frame

        if target.shape[0] < tmpl.shape[0] or target.shape[1] < tmpl.shape[1]:
            return False, 0.0, (0, 0)

        result = cv2.matchTemplate(target, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        matched = max_val >= threshold
        abs_loc = (max_loc[0] + (x if roi else 0), max_loc[1] + (y if roi else 0))
        return matched, float(max_val), abs_loc

    def match_synthesize_button(
        self,
        frame: npt.NDArray[np.uint8],
        roi: tuple[int, int, int, int],
    ) -> tuple[bool, bool]:
        """錬成ボタンの活性・非活性をカラー TM で判定する.

        Returns:
            (is_active, is_disabled):
                is_active: 活性ボタン検出。
                is_disabled: 非活性ボタン検出。

        """
        _, active_score, _ = self.match_color(frame, "ui/buttons/s1_synthesize", roi, threshold=0.0)
        _, disabled_score, _ = self.match_color(
            frame, "ui/buttons/s1_synthesize_disabled", roi, threshold=0.0
        )
        is_active = active_score >= disabled_score and active_score >= 0.75
        is_disabled = disabled_score > active_score and disabled_score >= 0.75
        return is_active, is_disabled

    def detect_lock_state(
        self,
        frame: npt.NDArray[np.uint8],
        roi: tuple[int, int, int, int],
    ) -> bool | None:
        """サブステータス枠のロック状態を検出する.

        青アイコン = 未ロック (False)、黄アイコン = ロック中 (True)。

        Args:
            frame: BGR のキャプチャ画像。
            roi: ロックアイコンの検出対象 ROI (x, y, w, h)。

        Returns:
            True: ロック中、False: 未ロック、None: 検出失敗。

        """
        _, locked_score, _ = self.match_color(frame, "ui/lock/s1_locked", roi, threshold=0.0)
        _, unlocked_score, _ = self.match_color(frame, "ui/lock/s1_unlocked", roi, threshold=0.0)

        if locked_score < 0.5 and unlocked_score < 0.5:
            return self._detect_lock_by_color(frame, roi)

        return locked_score > unlocked_score

    def _detect_lock_by_color(
        self,
        frame: npt.NDArray[np.uint8],
        roi: tuple[int, int, int, int],
    ) -> bool | None:
        """HSV カラーマスクでロックアイコンの色（青/黄）を判定する.

        Returns:
            True: ロック中（黄色）、False: 未ロック（青色）、None: 判定不能。

        """
        x, y, w, h = roi
        if w <= 0 or h <= 0:
            return None
        region = frame[y : y + h, x : x + w]
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)

        yellow_mask = cv2.inRange(hsv, np.array([15, 80, 80]), np.array([40, 255, 255]))
        blue_mask = cv2.inRange(hsv, np.array([85, 60, 60]), np.array([135, 255, 255]))

        yellow_px = int(np.sum(yellow_mask > 0))
        blue_px = int(np.sum(blue_mask > 0))

        if yellow_px == 0 and blue_px == 0:
            return None

        return yellow_px > blue_px

    def read_digits(
        self,
        frame: npt.NDArray[np.uint8],
        roi: tuple[int, int, int, int],
        color: str = "black",
    ) -> int | None:
        """数字テンプレートを使って ROI 内の数値を読み取る.

        Args:
            frame: BGR のキャプチャ画像。
            roi: 数値表示領域の ROI (x, y, w, h)。
            color: 文字色バリアント（"black" / "blue"）。templates/digits/<color>/ を使用。

        Returns:
            読み取った整数値。失敗した場合は None。

        """
        if roi[2] <= 0 or roi[3] <= 0:
            return None

        x, y, w, h = roi
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        region = gray[y : y + h, x : x + w]

        candidates: list[tuple[int, str]] = []
        for digit in "0123456789":
            tmpl_id = f"digits/{color}/{digit}"
            if tmpl_id not in self._gray_templates:
                continue
            tmpl = self._gray_templates[tmpl_id]
            if region.shape[0] < tmpl.shape[0] or region.shape[1] < tmpl.shape[1]:
                continue

            result = cv2.matchTemplate(region, tmpl, cv2.TM_CCOEFF_NORMED)
            locations = np.where(result >= 0.80)
            for px in zip(*locations[::-1], strict=False):
                candidates.append((px[0], digit))

        if not candidates:
            return None

        candidates.sort(key=lambda c: c[0])
        merged: list[tuple[int, str]] = []
        for cand in candidates:
            if not merged or cand[0] - merged[-1][0] > 8:
                merged.append(cand)

        digits_str = "".join(c[1] for c in merged)
        try:
            return int(digits_str)
        except ValueError:
            logger.debug("数値変換失敗: '%s'", digits_str)
            return None

    def read_substat_name(
        self,
        frame: npt.NDArray[np.uint8],
        roi: tuple[int, int, int, int],
        candidate_stats: list[str],
        template_prefix: str = "substats",
    ) -> str | None:
        """効果名テンプレートとマッチングして StatType 文字列を返す.

        Args:
            frame: BGR のキャプチャ画像。
            roi: 効果名表示領域の ROI (x, y, w, h)。
            candidate_stats: 照合対象のステータス ID リスト（装備の stat_pool から取得）。
            template_prefix: テンプレートのパスプレフィックス。
                S1 画面: "substats"
                S2 ロックなし: "substats/s2"
                S2 ロックあり: "substats/s2/locked"

        Returns:
            最もスコアが高かったステータス ID。閾値未満の場合は None。

        """
        if roi[2] <= 0 or roi[3] <= 0:
            return None

        # 縦方向に余白を加えてテンプレートがスライドできるようにする（行ごとの背景差異を吸収）
        search_roi = (roi[0], max(0, roi[1] - 4), roi[2], roi[3] + 8)

        best_stat: str | None = None
        best_score = 0.0
        for stat in candidate_stats:
            tmpl_id = f"{template_prefix}/{stat}"
            if tmpl_id not in self._gray_templates:
                continue
            _, score, _ = self.match(frame, tmpl_id, search_roi, threshold=0.0)
            if score > best_score:
                best_score = score
                best_stat = stat

        threshold = 0.75
        if best_score >= threshold:
            logger.debug("効果名検出: %s (score=%.3f)", best_stat, best_score)
            return best_stat
        logger.debug("効果名検出失敗: best=%s (score=%.3f)", best_stat, best_score)
        return None

    def read_stat_value(
        self,
        frame: npt.NDArray[np.uint8],
        roi: tuple[int, int, int, int],
        category: str,
        scale: str,
        candidate_values: list[str],
    ) -> str | None:
        """効果値テンプレートとマッチングして画面表示値文字列を返す.

        Args:
            frame: BGR のキャプチャ画像。
            roi: 効果値表示領域の ROI (x, y, w, h)。
            category: 装備カテゴリ（"weapon" / "weapon_special" / "armor" / "charm"）。
            scale: 値スケール（"hpdef" / "atkcrit" / "pen" / "tp"）。
            candidate_values: 照合対象の値文字列リスト（装備の StatPoolEntry.values から取得）。

        Returns:
            最もスコアが高かった値文字列。閾値未満の場合は None。

        """
        if roi[2] <= 0 or roi[3] <= 0:
            return None

        # 縦方向に余白を加えてテンプレートがスライドできるようにする
        search_roi = (roi[0], max(0, roi[1] - 4), roi[2], roi[3] + 8)

        best_value: str | None = None
        best_score = 0.0
        for value in candidate_values:
            tmpl_id = f"stat_values/{category}/{scale}/{_value_to_key(value)}"
            _, score, _ = self.match(frame, tmpl_id, search_roi, threshold=0.0)
            if score > best_score:
                best_score = score
                best_value = value

        threshold = 0.70
        if best_score >= threshold:
            logger.debug("効果値検出: %s (score=%.3f)", best_value, best_score)
            return best_value
        logger.debug("効果値検出失敗 (best_score=%.3f)", best_score)
        return None

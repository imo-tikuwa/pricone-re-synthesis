"""装備自動検出モジュール.

S1 画面から現在選択中の装備を特定する。

■ 検出フロー
  1. s1_equipment_charm_name ROI に対し、属性アクセサリー（C0001〜C0010）の
     カタカナ名テンプレートをマッチング
     → 一致あり: 手順 2 へ
     → 一致なし: 手順 3 へ

  2. s1_equipment_element ROI に対し、属性テンプレート（fire/water/wind/light/dark）
     をマッチングして属性を特定
     → 装備 ID = base_id + "_" + element → EquipmentData 返却

  3. s1_equipment_name ROI に対し、武器・防具・特殊アクセサリーテンプレートを
     マッチング
     → 一致あり: EquipmentData 返却
     → 一致なし: None 返却（未登録装備）

■ テンプレートキー体系（templates/ からの相対パス・拡張子なし）
  equipment/charm/C0001   ... 属性アクセサリー カタカナ名（5属性共通）
  equipment/weapon/W0001  ... 武器 装備名全体
  equipment/armor/A0001   ... 防具 装備名全体
  equipment/charm/C1001   ... 特殊アクセサリー 装備名全体
  equipment/element/fire  ... 属性文字テンプレート（全アクセサリー共通）
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.constants import (
    S1_EQUIPMENT_CHARM_NAME_ROI,
    S1_EQUIPMENT_ELEMENT_ROI,
    S1_EQUIPMENT_NAME_ROI,
    TM_THRESHOLD_DEFAULT,
)
from src.data.equipment_master import EQUIPMENT_MAP
from src.data.models import EquipmentData, EquipmentType

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

    from src.core.matcher import TemplateMatcher

logger = logging.getLogger(__name__)

# 属性キー → テンプレートキー
_ELEMENT_TEMPLATE_KEYS: dict[str, str] = {
    "fire": "equipment/element/fire",
    "water": "equipment/element/water",
    "wind": "equipment/element/wind",
    "light": "equipment/element/light",
    "dark": "equipment/element/dark",
}

# threshold: 装備名テンプレートは文字画像なのでやや高めに設定
_TM_EQUIP = TM_THRESHOLD_DEFAULT
_TM_ELEMENT = 0.80


class EquipmentDetector:
    """S1 画面から選択中装備を自動検出する.

    TemplateMatcher と EQUIPMENT_MAP に依存する。
    テンプレート画像は build_templates.py で生成した NPZ に格納されている前提。
    """

    def __init__(self, matcher: TemplateMatcher) -> None:
        self._matcher = matcher
        # base_id → EquipmentData（属性なし代表）: C0001〜C0010 の先頭属性で代表
        self._charm_bases: dict[str, str] = self._build_charm_base_map()

    def _build_charm_base_map(self) -> dict[str, str]:
        """テンプレートキー → base_id のマッピングを構築する.

        C0001_fire〜C0010_dark のうち、base_id ごとに 1 エントリだけ保持する。
        """
        seen: dict[str, str] = {}  # tmpl_key → base_id
        for eq in EQUIPMENT_MAP.values():
            if eq.type == EquipmentType.CHARM and eq.element is not None:
                base_id = eq.id.rsplit("_", 1)[0]  # "C0001_fire" → "C0001"
                tmpl_key = f"equipment/charm/{base_id}"
                if tmpl_key not in seen:
                    seen[tmpl_key] = base_id
        return seen

    def detect(self, frame: npt.NDArray[np.uint8]) -> EquipmentData | None:
        """フレームから選択中装備を特定して EquipmentData を返す.

        Returns:
            一致した EquipmentData。一致なし（未登録装備）の場合は None。

        """
        # --- ステップ 1: 属性アクセサリー検出 ---
        base_id = self._match_charm_name(frame)
        if base_id is not None:
            element = self._match_element(frame)
            if element is not None:
                eq_id = f"{base_id}_{element}"
                eq = EQUIPMENT_MAP.get(eq_id)
                if eq is not None:
                    logger.info(
                        "装備検出: %s (base=%s, element=%s)", eq.display_name, base_id, element
                    )
                    return eq
            # 属性不明: 属性なしで base の最初のバリアントを返す（暫定）
            for suffix in ("fire", "water", "wind", "light", "dark"):
                eq = EQUIPMENT_MAP.get(f"{base_id}_{suffix}")
                if eq is not None:
                    logger.warning(
                        "装備 %s を検出しましたが属性不明のため %s で代替します", base_id, eq.id
                    )
                    return eq

        # --- ステップ 2: 武器・防具・特殊アクセサリー検出 ---
        return self._match_full_name(frame)

    def _match_charm_name(self, frame: npt.NDArray[np.uint8]) -> str | None:
        """s1_equipment_charm_name ROI で属性アクセサリーを特定し base_id を返す."""
        if S1_EQUIPMENT_CHARM_NAME_ROI[2] <= 0 or S1_EQUIPMENT_CHARM_NAME_ROI[3] <= 0:
            # ROI 未定義（TBD）
            return None

        best_score = 0.0
        best_base_id: str | None = None
        for tmpl_key, base_id in self._charm_bases.items():
            matched, score, _ = self._matcher.match(
                frame, tmpl_key, S1_EQUIPMENT_CHARM_NAME_ROI, _TM_EQUIP
            )
            if matched and score > best_score:
                best_score = score
                best_base_id = base_id

        if best_base_id:
            logger.debug("チャーム名マッチ: base=%s score=%.3f", best_base_id, best_score)
        return best_base_id

    def _match_element(self, frame: npt.NDArray[np.uint8]) -> str | None:
        """s1_equipment_element ROI で属性文字を検出し element キーを返す."""
        if S1_EQUIPMENT_ELEMENT_ROI[2] <= 0 or S1_EQUIPMENT_ELEMENT_ROI[3] <= 0:
            return None

        best_score = 0.0
        best_elem: str | None = None
        for elem_key, tmpl_key in _ELEMENT_TEMPLATE_KEYS.items():
            matched, score, _ = self._matcher.match(
                frame, tmpl_key, S1_EQUIPMENT_ELEMENT_ROI, _TM_ELEMENT
            )
            if matched and score > best_score:
                best_score = score
                best_elem = elem_key

        if best_elem:
            logger.debug("属性マッチ: %s score=%.3f", best_elem, best_score)
        return best_elem

    def _match_full_name(self, frame: npt.NDArray[np.uint8]) -> EquipmentData | None:
        """s1_equipment_name ROI で武器・防具・特殊アクセサリーを特定する."""
        if S1_EQUIPMENT_NAME_ROI[2] <= 0 or S1_EQUIPMENT_NAME_ROI[3] <= 0:
            return None

        best_score = 0.0
        best_eq: EquipmentData | None = None

        for eq in EQUIPMENT_MAP.values():
            # 属性アクセサリー（element あり）はここでは検出しない
            if eq.element is not None:
                continue
            tmpl_key = Path(eq.template).with_suffix("").as_posix()
            matched, score, _ = self._matcher.match(
                frame, tmpl_key, S1_EQUIPMENT_NAME_ROI, _TM_EQUIP
            )
            if matched and score > best_score:
                best_score = score
                best_eq = eq

        if best_eq:
            logger.info("装備検出: %s score=%.3f", best_eq.display_name, best_score)
        else:
            logger.debug("装備検出: 一致なし（未登録装備の可能性）")
        return best_eq

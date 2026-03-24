"""錬成結果評価モジュール."""

from __future__ import annotations

import logging

from src.core.constants import COST_TABLE
from src.data.models import (
    DetectionResult,
    EquipmentData,
    EvalResult,
    GoalCondition,
    SubstatSlot,
)

logger = logging.getLogger(__name__)


def _parse_value(value: str) -> float:
    """画面表示値（"1.5%" や "3" など）を数値に変換する."""
    return float(value.rstrip("%"))


class ResultEvaluator:
    """錬成結果と完了条件を照合し、次のアクションを決定する."""

    def __init__(self, equipment: EquipmentData, goal: GoalCondition) -> None:
        self._equipment = equipment
        self._goal = goal
        # S1 でロック済みの枠インデックスセット
        self._locked_slots: set[int] = set()

    @property
    def equipment(self) -> EquipmentData:
        """装備情報を返す."""
        return self._equipment

    def reset_locks(self) -> None:
        """ロック状態をリセットする（新規装備選択時）."""
        self._locked_slots = set()

    def update_locks(self, locked_indices: set[int]) -> None:
        """S1 のロック状態を更新する."""
        self._locked_slots = locked_indices

    @property
    def locked_slots(self) -> set[int]:
        """現在のロック済み枠インデックスセット."""
        return self._locked_slots.copy()

    def evaluate(
        self,
        result_substats: list[SubstatSlot],
    ) -> tuple[EvalResult, list[int]]:
        """S2 の錬成結果を評価する.

        Args:
            result_substats: S2 画面で検出した錬成後の 4 枠分サブステータス。

        Returns:
            (EvalResult, new_match_indices):
                EvalResult: 評価結果。
                new_match_indices: 今回新たに一致した枠インデックスのリスト。

        """
        goal = self._goal
        new_matches: list[int] = []

        for slot in result_substats:
            if slot.slot_index in self._locked_slots:
                # 既ロック枠はスキップ（評価不要）
                continue
            if (
                slot.stat == goal.target_stat
                and slot.value is not None
                and _parse_value(slot.value) >= _parse_value(goal.min_value)
            ):
                new_matches.append(slot.slot_index)

        # 合計一致枠数（ロック済み + 今回の新規）
        total_matches = len(self._locked_slots) + len(new_matches)

        if total_matches >= goal.required_slots:
            return EvalResult.GOAL_ACHIEVED, new_matches

        if new_matches:
            return EvalResult.PARTIAL_MATCH, new_matches

        return EvalResult.NO_MATCH, []

    def get_slots_to_lock(
        self,
        result_substats: list[SubstatSlot],
        new_match_indices: list[int],
    ) -> list[int]:
        """PARTIAL_MATCH 時に S1 でロックすべき枠インデックスを返す.

        既ロック枠は含まない（既にロック済みのため）。

        Args:
            result_substats: S2 錬成後サブステータス。
            new_match_indices: 今回新たに一致した枠インデックス。

        Returns:
            ロックすべき枠インデックスのリスト。

        """
        return [idx for idx in new_match_indices if idx not in self._locked_slots]

    def calculate_cost(self) -> tuple[int, int]:
        """次回錬成のコスト（マナ, EX錬成Pt）を返す.

        ロック済み枠数から錬成枠数を計算してコストテーブルを参照する。

        Returns:
            (mana_cost, ex_pt_cost)

        """
        locked_count = len(self._locked_slots)
        synth_slots = max(1, 4 - locked_count)  # 最低 1 枠
        return COST_TABLE.get(synth_slots, (400_000, 40_000))

    def check_resources(self, mana: int, ex_pt: int) -> bool:
        """リソースが次回錬成コストを満たしているか確認する.

        Args:
            mana: 現在のマナ残数。
            ex_pt: 現在の EX錬成Pt 残数。

        Returns:
            充足している場合 True。

        """
        mana_cost, ex_pt_cost = self.calculate_cost()
        if mana < mana_cost:
            logger.warning("マナ不足: 必要 %d / 現在 %d", mana_cost, mana)
            return False
        if ex_pt < ex_pt_cost:
            logger.warning("EX錬成Pt 不足: 必要 %d / 現在 %d", ex_pt_cost, ex_pt)
            return False
        return True

    def detect_substats_from_frame(
        self,
        detection: DetectionResult,
        is_s2: bool = False,
    ) -> list[SubstatSlot]:
        """DetectionResult からサブステータスリストを取り出す.

        Args:
            detection: フレームの検出結果。
            is_s2: True の場合は S2 の錬成後サブステータスを返す。

        Returns:
            4 枠分の SubstatSlot リスト。

        """
        return detection.substats

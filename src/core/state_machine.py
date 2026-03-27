"""ステートマシン: 自動錬成ループの状態管理."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal

from src.core.constants import (
    CLICK_SETTLE_WAIT,
    LOCK_RETRY_MAX,
    POLL_INTERVAL_DEFAULT,
    RESULT_SCREEN_MIN_WAIT,
    S1_BTN_SYNTHESIZE_ROI,
    S1_SUBSTAT_ROIS,
    S1_ULTIMATE_LABEL_ROI,
    S1A_BTN_OK_ROI,
    S1A_MODAL_TITLE_ROI,
    S2_BTN_CONFIRM_ROI,
    S2_BTN_DISCARD_ROI,
    S2_BTN_RESYNTH_ROI,
    S2_RESULT_LABEL_ROI,
    S2_SUBSTAT_NAME_ROIS,
    S2_SUBSTAT_ROIS,
    S2_SUBSTAT_VALUE_ROIS,
    S2A_BTN_OK_ROI,
    S2A_MODAL_TEXT_ROI,
    S2B_BTN_OK_ROI,
    S2B_MODAL_TITLE_ROI,
    SAFE_CLICK_COORDS,
    SAFE_CLICK_INTERVAL,
    STAT_TO_SCALE,
    STATE_DISPLAY_NAMES,
    TIMEOUT_CHECKING_SCREEN,
    TIMEOUT_CONFIRMING_RESULT,
    TIMEOUT_S1A_CONFIRM,
    TIMEOUT_WAITING_FOR_RESULT,
    TM_THRESHOLD_BUTTON,
    TM_THRESHOLD_DEFAULT,
    TM_THRESHOLD_S2_RESULT,
    WEAPON_SPECIAL_IDS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    State,
)
from src.data.models import DetectionResult, EquipmentType, EvalResult, GoalCondition, SubstatSlot

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt

    from src.core.automator import Automator
    from src.core.capture import ScreenCapture
    from src.core.evaluator import ResultEvaluator
    from src.core.matcher import TemplateMatcher

logger = logging.getLogger(__name__)


class StateMachineWorker(QThread):
    """自動錬成ループを別スレッドで実行する QThread ワーカー.

    シグナルで GUI に状態変化・エラー・完了を通知する。
    """

    # シグナル定義
    state_changed = pyqtSignal(str)  # 状態名
    synthesis_count_changed = pyqtSignal(int)  # 錬成回数
    error_occurred = pyqtSignal(str)  # エラーメッセージ
    aborted = pyqtSignal(str)  # 中断条件到達（正常終了）
    completed = pyqtSignal()  # 完了（GOAL_ACHIEVED 後）
    lock_warning = pyqtSignal(int)  # ロック失敗した枠インデックス
    resources_insufficient = pyqtSignal(int, int)  # (不足マナ, 不足PT)
    resources_updated = pyqtSignal(int, int)  # S1 で読み取ったリソース (マナ, EX錬成Pt)
    game_window_closed = pyqtSignal()  # ゲームウィンドウ消滅通知

    def __init__(
        self,
        capture: ScreenCapture,
        matcher: TemplateMatcher,
        automator: Automator,
        evaluator: ResultEvaluator,
        goal: GoalCondition,
        capture_interval: float = POLL_INTERVAL_DEFAULT,
        initial_state: State = State.CHECKING_SCREEN,
    ) -> None:
        super().__init__()
        self._capture = capture
        self._matcher = matcher
        self._automator = automator
        self._evaluator = evaluator
        self._goal = goal
        self._capture_interval = capture_interval
        self._initial_state = initial_state

        self._state = State.IDLE
        self._running = False
        self._synthesis_count = 0

        # WAITING_FOR_RESULT 用タイマー
        self._wait_start: float = 0.0
        self._last_safe_click: float = 0.0
        self._s1a_confirm_start: float = 0.0

        # CONFIRMING_RESULT 用
        self._confirm_result_start: float = 0.0
        self._after_confirm_next: State = State.S1_EQUIP_SELECT

        # APPLYING_LOCKS で処理待ちの枠インデックスリスト
        self._pending_lock_slots: list[int] = []

        # ロック適用後に完了へ遷移するフラグ（GOAL_ACHIEVED 時に新規枠ロックが必要な場合）
        self._complete_after_locks: bool = False

        # リソース推定値（S1 実測 + 各錬成コスト累積で更新）
        self._est_mana: int | None = None
        self._est_ex_pt: int | None = None

    # ------------------------------------------------------------------
    # 公開メソッド
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """自動錬成ループを停止する."""
        self._running = False

    @property
    def current_state(self) -> State:
        """現在の状態を返す."""
        return self._state

    # ------------------------------------------------------------------
    # QThread 実装
    # ------------------------------------------------------------------

    def run(self) -> None:
        """メインループ."""
        self._running = True
        self._state = self._initial_state
        self._synthesis_count = 0
        self._emit_state()
        logger.info(
            "ステートマシン開始: %s | 目標: %s %s %d枠 | EX錬成Pt下限: %s",
            self._state,
            self._goal.target_stat,
            self._goal.min_value,
            self._goal.required_slots,
            f"{self._goal.min_ex_pt:,}" if self._goal.min_ex_pt > 0 else "なし",
        )

        while self._running:
            try:
                self._step()
            except Exception:
                logger.exception("ステートマシンで予期しないエラーが発生しました")
                self._transition(State.ERROR_WRONG_SCREEN)
                self.error_occurred.emit("予期しないエラーが発生しました。ログを確認してください。")
                break

            if self._state in {
                State.COMPLETED,
                State.ERROR_WRONG_SCREEN,
                State.ERROR_INSUFFICIENT,
                State.ERROR_TIMEOUT,
            }:
                break

            time.sleep(self._capture_interval)

        self._running = False
        logger.info("ステートマシン終了: %s", self._state)

    # ------------------------------------------------------------------
    # 状態遷移ロジック
    # ------------------------------------------------------------------

    def _step(self) -> None:
        """現在の状態に応じた処理を 1 ステップ実行する."""
        frame = self._capture.capture()

        if frame is None:
            if not self._capture.is_window_alive():
                self._transition(State.ERROR_WRONG_SCREEN)
                self.game_window_closed.emit()
            else:
                logger.warning("キャプチャに失敗しました")
            return

        h, w = frame.shape[:2]
        if w != WINDOW_WIDTH or h != WINDOW_HEIGHT:
            self._transition(State.ERROR_WRONG_SCREEN)
            self.error_occurred.emit(
                f"ゲームウィンドウのサイズが正しくありません。\n"
                f"期待: {WINDOW_WIDTH}×{WINDOW_HEIGHT} px\n"
                f"実際: {w}×{h} px\n\n"
                "ウィンドウサイズを元に戻してから再度「開始」を押してください。"
            )
            return

        # ウィンドウハンドルを automator に反映
        hwnd = self._capture.hwnd
        if hwnd is not None:
            self._automator.set_hwnd(hwnd)

        state = self._state

        if state == State.CHECKING_SCREEN:
            self._handle_checking_screen(frame)

        elif state == State.S1_EQUIP_SELECT:
            self._handle_s1(frame)

        elif state == State.APPLYING_LOCKS:
            self._handle_applying_locks(frame)

        elif state == State.CHECKING_RESOURCES:
            self._handle_checking_resources(frame)

        elif state == State.CLICKING_SYNTHESIZE:
            self._handle_clicking_synthesize(frame)

        elif state == State.S1A_CONFIRM:
            self._handle_s1a(frame)

        elif state == State.CLICKING_OK:
            self._handle_clicking_ok(frame)

        elif state == State.WAITING_FOR_RESULT:
            self._handle_waiting_for_result(frame)

        elif state == State.S2_RESULT:
            self._handle_s2(frame)

        elif state == State.EVALUATING_RESULT:
            self._handle_evaluating(frame)

        elif state == State.GOAL_ACHIEVED:
            self._handle_goal_achieved(frame)

        elif state == State.PARTIAL_MATCH:
            self._handle_partial_match(frame)

        elif state == State.NO_MATCH:
            self._handle_no_match(frame)

        elif state == State.CLICKING_RESYNTH:
            self._handle_clicking_resynth(frame)

        elif state == State.S2A_CONFIRM:
            self._handle_s2a(frame)

        elif state == State.CLICKING_OK_RESYNTH:
            self._handle_clicking_ok_resynth(frame)

        elif state == State.CONFIRMING_RESULT:
            self._handle_confirming_result(frame)

        elif state == State.S2B_CONFIRM:
            self._handle_s2b(frame)

    # ------------------------------------------------------------------
    # 各状態ハンドラ
    # ------------------------------------------------------------------

    def _handle_checking_screen(self, frame: npt.NDArray[np.uint8]) -> None:
        """S1「究極錬成」文字を検出して S1_EQUIP_SELECT へ遷移."""
        matched, score, _ = self._matcher.match(
            frame, "ui/s1_ultimate_synthesis_label", S1_ULTIMATE_LABEL_ROI, TM_THRESHOLD_DEFAULT
        )
        if matched:
            logger.info("S1 画面検出 (score=%.3f)", score)
            self._transition(State.S1_EQUIP_SELECT)
        else:
            # タイムアウト判定（CHECKING_SCREEN に入った時刻を記録）
            if not hasattr(self, "_check_screen_start"):
                self._check_screen_start = time.time()
            elif time.time() - self._check_screen_start > TIMEOUT_CHECKING_SCREEN:
                del self._check_screen_start
                self._transition(State.ERROR_WRONG_SCREEN)
                self.error_occurred.emit(
                    "究極錬成画面が検出できませんでした。\n"
                    "ゲームを究極錬成の装備選択画面（S1）にしてから開始してください。"
                )

    def _handle_s1(self, frame: npt.NDArray[np.uint8]) -> None:  # noqa: ARG002
        """S1: ロック適用待ちがあれば APPLYING_LOCKS へ、なければ CHECKING_RESOURCES へ."""
        pending = getattr(self, "_pending_lock_slots", [])
        if pending:
            self._transition(State.APPLYING_LOCKS)
        elif self._complete_after_locks:
            self._complete_after_locks = False
            self._transition(State.COMPLETED)
            self.completed.emit()
        else:
            self._transition(State.CHECKING_RESOURCES)

    def _finish_locks(self) -> None:
        """全ロック適用完了後の遷移: 完了フラグがあれば COMPLETED、なければ CHECKING_RESOURCES."""
        self._pending_lock_slots = []
        if self._complete_after_locks:
            self._complete_after_locks = False
            self._transition(State.COMPLETED)
            self.completed.emit()
        else:
            self._transition(State.CHECKING_RESOURCES)

    def _handle_applying_locks(self, frame: npt.NDArray[np.uint8]) -> None:
        """S1 でロック未適用の枠にロックアイコンをクリックする."""
        pending: list[int] = getattr(self, "_pending_lock_slots", [])
        if not pending:
            self._finish_locks()
            return

        slot_idx = pending[0]
        roi = S1_SUBSTAT_ROIS[slot_idx]
        lock_roi = (roi[0], roi[1], roi[2], roi[3])

        # 現在の状態確認: 既にロック済みなら次へ
        current_locked = self._matcher.detect_lock_state(frame, lock_roi)
        if current_locked is True:
            pending.pop(0)
            self._evaluator.update_locks(self._evaluator.locked_slots | {slot_idx})
            logger.info("枠 %d は既にロック済みです", slot_idx)
            if not pending:
                self._finish_locks()
            return

        # クリックしてロック
        retry_key = f"_lock_retry_{slot_idx}"
        retry_count = getattr(self, retry_key, 0)

        self._automator.click_center(lock_roi)
        time.sleep(CLICK_SETTLE_WAIT + 0.1)

        # 再キャプチャしてロック確認
        new_frame = self._capture.capture()
        if new_frame is not None:
            is_locked = self._matcher.detect_lock_state(new_frame, lock_roi)
            if is_locked is True:
                logger.info("枠 %d のロック成功", slot_idx)
                pending.pop(0)
                setattr(self, retry_key, 0)
                self._evaluator.update_locks(self._evaluator.locked_slots | {slot_idx})
                if not pending:
                    self._finish_locks()
                return
            else:
                retry_count += 1
                setattr(self, retry_key, retry_count)
                if retry_count >= LOCK_RETRY_MAX:
                    logger.warning("枠 %d のロックが %d 回失敗しました", slot_idx, retry_count)
                    self.lock_warning.emit(slot_idx)
                    pending.pop(0)
                    setattr(self, retry_key, 0)
                    if not pending:
                        self._finish_locks()

    def _handle_checking_resources(self, frame: npt.NDArray[np.uint8]) -> None:
        """リソース（マナ・EX錬成Pt）を確認して不足なら ERROR_INSUFFICIENT へ."""
        from src.core.constants import EX_PT_ROI, MANA_ROI

        mana = self._matcher.read_digits(frame, MANA_ROI)
        ex_pt = self._matcher.read_digits(frame, EX_PT_ROI)

        # ROI が未定義 (TBD) の場合はスキップ
        if mana is None or ex_pt is None:
            logger.warning(
                "リソース読み取り失敗 mana=%s ex_pt=%s。ROI 未定義の可能性。スキップします。",
                mana,
                ex_pt,
            )
            self._transition(State.CLICKING_SYNTHESIZE)
            return

        self._est_mana = mana
        self._est_ex_pt = ex_pt
        logger.info("リソース確認: マナ=%d, EX錬成Pt=%d", mana, ex_pt)
        self.resources_updated.emit(mana, ex_pt)

        if not self._evaluator.check_resources(mana, ex_pt):
            mana_cost, ex_pt_cost = self._evaluator.calculate_cost()
            self._transition(State.ERROR_INSUFFICIENT)
            self.resources_insufficient.emit(
                max(0, mana_cost - mana),
                max(0, ex_pt_cost - ex_pt),
            )
            self.aborted.emit(
                f"リソースが不足しています。\n"
                f"マナ: {mana:,} / {mana_cost:,}\n"
                f"EX錬成Pt: {ex_pt:,} / {ex_pt_cost:,}"
            )
        elif self._goal.min_ex_pt > 0 and ex_pt < self._goal.min_ex_pt:
            self._transition(State.ERROR_INSUFFICIENT)
            self.aborted.emit(
                f"EX錬成Pt が残量下限に達しました。\n"
                f"現在: {ex_pt:,} / 下限: {self._goal.min_ex_pt:,}"
            )
        else:
            self._transition(State.CLICKING_SYNTHESIZE)

    def _handle_clicking_synthesize(self, frame: npt.NDArray[np.uint8]) -> None:
        """「錬成」ボタンをカラー TM で確認してクリックする."""
        is_active, is_disabled = self._matcher.match_synthesize_button(frame, S1_BTN_SYNTHESIZE_ROI)
        if is_active:
            self._automator.click_center(S1_BTN_SYNTHESIZE_ROI)
            time.sleep(CLICK_SETTLE_WAIT)
            self._s1a_confirm_start = time.time()
            self._transition(State.S1A_CONFIRM)
        elif is_disabled:
            self._transition(State.ERROR_WRONG_SCREEN)
            self.error_occurred.emit(
                "錬成ボタンが非活性です。\n全枠ロック済みの装備が選択されている可能性があります。"
            )
        else:
            logger.warning("「錬成」ボタンが検出できませんでした（スコア不足）")

    def _handle_s1a(self, frame: npt.NDArray[np.uint8]) -> None:
        """S1a モーダル（初回錬成確認）: 「OK」ボタンをクリックして CLICKING_OK へ."""
        if time.time() - self._s1a_confirm_start > TIMEOUT_S1A_CONFIRM:
            self._transition(State.ERROR_TIMEOUT)
            self.error_occurred.emit(
                f"錬成確認モーダルが {TIMEOUT_S1A_CONFIRM} 秒以内に表示されませんでした。\n"
                "錬成ボタンがクリックされていない可能性があります。"
            )
            return

        matched, score, _ = self._matcher.match(
            frame, "ui/s1a_modal_title", S1A_MODAL_TITLE_ROI, TM_THRESHOLD_DEFAULT
        )
        if matched:
            ok_matched, _, _ = self._matcher.match(
                frame, "ui/buttons/s1a_ok", S1A_BTN_OK_ROI, TM_THRESHOLD_BUTTON
            )
            if ok_matched:
                self._automator.click_center(S1A_BTN_OK_ROI)
                self._transition(State.CLICKING_OK)
            else:
                logger.warning("S1a: OK ボタンが検出できませんでした")
        else:
            logger.debug("S1a モーダル未検出 (score=%.3f)", score)

    def _deduct_resource_cost(self) -> None:
        """錬成コストを推定リソースから差し引いてシグナルを発火する."""
        mana_cost, ex_pt_cost = self._evaluator.calculate_cost()
        if self._est_mana is not None:
            self._est_mana = max(0, self._est_mana - mana_cost)
        if self._est_ex_pt is not None:
            self._est_ex_pt = max(0, self._est_ex_pt - ex_pt_cost)
        if self._est_mana is not None and self._est_ex_pt is not None:
            self.resources_updated.emit(self._est_mana, self._est_ex_pt)

    def _handle_clicking_ok(self, frame: npt.NDArray[np.uint8]) -> None:
        """OK クリック直後: WAITING_FOR_RESULT へ."""
        self._wait_start = time.time()
        self._last_safe_click = time.time()
        self._synthesis_count += 1
        self.synthesis_count_changed.emit(self._synthesis_count)
        self._deduct_resource_cost()
        self._transition(State.WAITING_FOR_RESULT)

    def _handle_waiting_for_result(self, frame: npt.NDArray[np.uint8]) -> None:
        """S2「錬成結果」テキストを検出するまでポーリングする."""
        elapsed = time.time() - self._wait_start

        # タイムアウト
        if elapsed > TIMEOUT_WAITING_FOR_RESULT:
            self._transition(State.ERROR_TIMEOUT)
            self.error_occurred.emit(
                f"錬成結果画面が {TIMEOUT_WAITING_FOR_RESULT} 秒以内に検出できませんでした。"
            )
            return

        # 最低待機時間内は S2 検出をスキップ（高速インターバル時に前回画面を誤検出しないよう抑制）
        if elapsed < RESULT_SCREEN_MIN_WAIT:
            now = time.time()
            if now - self._last_safe_click >= SAFE_CLICK_INTERVAL:
                if SAFE_CLICK_COORDS != (0, 0):
                    self._automator.click(SAFE_CLICK_COORDS[0], SAFE_CLICK_COORDS[1])
                self._last_safe_click = now
            return

        # S2 検出
        matched, score, _ = self._matcher.match(
            frame, "ui/s2_synthesis_result_label", S2_RESULT_LABEL_ROI, TM_THRESHOLD_S2_RESULT
        )
        if matched:
            logger.info("S2 錬成結果画面検出 (score=%.3f)", score)
            self._transition(State.S2_RESULT)
            return

        # 安全クリック（アニメーションスキップ試み）
        now = time.time()
        if now - self._last_safe_click >= SAFE_CLICK_INTERVAL:
            if SAFE_CLICK_COORDS != (0, 0):
                self._automator.click(SAFE_CLICK_COORDS[0], SAFE_CLICK_COORDS[1])
            self._last_safe_click = now

    def _handle_s2(self, frame: npt.NDArray[np.uint8]) -> None:
        """S2: 描画完了を待ってからサブステータス検出・解析に移行する."""
        # S2 結果ラベルは描画序盤に出るため、サブステータス文字描画完了を少し待つ
        time.sleep(0.5)
        self._transition(State.EVALUATING_RESULT)

    def _handle_evaluating(self, frame: npt.NDArray[np.uint8]) -> None:
        """S2 の錬成後サブステータスを評価する."""
        detection = self._detect_frame(frame)
        result_substats = detection.substats

        for slot in result_substats:
            logger.info(
                "  枠 %d: stat=%-12s value=%-8s locked=%s",
                slot.slot_index,
                slot.stat or "(未検出)",
                slot.value or "(未検出)",
                slot.is_locked,
            )

        eval_result, new_matches = self._evaluator.evaluate(result_substats)

        if eval_result == EvalResult.GOAL_ACHIEVED:
            logger.info("目標達成! 一致枠: %s", new_matches)
            slots_to_lock = self._evaluator.get_slots_to_lock(result_substats, new_matches)
            self._pending_lock_slots = slots_to_lock
            self._complete_after_locks = bool(slots_to_lock)
            self._transition(State.GOAL_ACHIEVED)

        elif eval_result == EvalResult.PARTIAL_MATCH:
            logger.info("部分一致: 新規一致枠 %s", new_matches)
            slots_to_lock = self._evaluator.get_slots_to_lock(result_substats, new_matches)
            self._pending_lock_slots = slots_to_lock
            self._transition(State.PARTIAL_MATCH)

        else:
            logger.info("一致なし")
            self._transition(State.NO_MATCH)

    def _handle_goal_achieved(self, frame: npt.NDArray[np.uint8]) -> None:
        """「結果確定」をクリックして CONFIRMING_RESULT へ.

        新規ロック枠がある場合は S1 に戻ってロック適用後に完了する。
        """
        self._click_confirm_button(frame)
        self._transition(State.CLICKING_CONFIRM)
        self._after_confirm_next = (
            State.S1_EQUIP_SELECT if self._complete_after_locks else State.COMPLETED
        )
        self._confirm_result_start = time.time()
        self._transition(State.CONFIRMING_RESULT)

    def _handle_partial_match(self, frame: npt.NDArray[np.uint8]) -> None:
        """「結果確定」をクリックして CONFIRMING_RESULT へ（S1 復帰フラグ付き）."""
        self._click_confirm_button(frame)
        self._transition(State.CLICKING_CONFIRM_PARTIAL)
        self._after_confirm_next = State.S1_EQUIP_SELECT
        self._confirm_result_start = time.time()
        self._transition(State.CONFIRMING_RESULT)

    def _handle_no_match(self, frame: npt.NDArray[np.uint8]) -> None:
        """「再錬成」ボタンをクリックして S2a へ."""
        # EX錬成Pt 残量下限チェック（再錬成ループ中は推定値で判定）
        if (
            self._goal.min_ex_pt > 0
            and self._est_ex_pt is not None
            and self._est_ex_pt < self._goal.min_ex_pt
        ):
            logger.info(
                "EX錬成Pt 残量下限到達: 推定=%d, 下限=%d", self._est_ex_pt, self._goal.min_ex_pt
            )
            self._transition(State.ERROR_INSUFFICIENT)
            self.aborted.emit(
                f"EX錬成Pt が残量下限に達しました。\n"
                f"推定残量: {self._est_ex_pt:,} / 下限: {self._goal.min_ex_pt:,}"
            )
            return

        matched, score, _ = self._matcher.match(
            frame, "ui/buttons/s2_resynth", S2_BTN_RESYNTH_ROI, TM_THRESHOLD_BUTTON
        )
        if matched:
            # 「破棄」と「再錬成」を混同しないよう「破棄」が検出されないことを確認
            discard_matched, _, _ = self._matcher.match(
                frame, "ui/buttons/s2_discard", S2_BTN_DISCARD_ROI, TM_THRESHOLD_BUTTON
            )
            if not discard_matched or score > 0.90:
                self._automator.click_center(S2_BTN_RESYNTH_ROI)
                self._transition(State.CLICKING_RESYNTH)
            else:
                logger.warning("「再錬成」と「破棄」の混同を防ぐため操作を保留しました")
        else:
            logger.warning("「再錬成」ボタンが検出できませんでした (score=%.3f)", score)

    def _handle_clicking_resynth(self, frame: npt.NDArray[np.uint8]) -> None:
        """再錬成クリック後: S2a 検出へ."""
        self._transition(State.S2A_CONFIRM)

    def _handle_s2a(self, frame: npt.NDArray[np.uint8]) -> None:
        """S2a モーダル（再錬成確認）: 「OK」ボタンをクリックして CLICKING_OK_RESYNTH へ."""
        matched, score, _ = self._matcher.match(
            frame, "ui/s2a_modal_text_resynth", S2A_MODAL_TEXT_ROI, TM_THRESHOLD_DEFAULT
        )
        if matched:
            ok_matched, _, _ = self._matcher.match(
                frame, "ui/buttons/s2a_ok", S2A_BTN_OK_ROI, TM_THRESHOLD_BUTTON
            )
            if ok_matched:
                self._automator.click_center(S2A_BTN_OK_ROI)
                self._transition(State.CLICKING_OK_RESYNTH)
            else:
                logger.warning("S2a: OK ボタンが検出できませんでした")
        else:
            logger.debug("S2a モーダル未検出 (score=%.3f)", score)

    def _handle_clicking_ok_resynth(self, frame: npt.NDArray[np.uint8]) -> None:
        """再錬成 OK クリック後: WAITING_FOR_RESULT に戻る."""
        self._wait_start = time.time()
        self._last_safe_click = time.time()
        self._synthesis_count += 1
        self.synthesis_count_changed.emit(self._synthesis_count)
        self._deduct_resource_cost()
        self._transition(State.WAITING_FOR_RESULT)

    def _handle_confirming_result(self, frame: npt.NDArray[np.uint8]) -> None:
        """結果確定クリック後: S2b モーダルまたは S1 画面を検出するまでポーリングする."""
        elapsed = time.time() - self._confirm_result_start
        if elapsed > TIMEOUT_CONFIRMING_RESULT:
            logger.warning("CONFIRMING_RESULT タイムアウト。S1 復帰と見なして続行します。")
            self._finish_confirm()
            return

        # S2b モーダル検出
        matched, score, _ = self._matcher.match(
            frame, "ui/s2b_modal_title", S2B_MODAL_TITLE_ROI, TM_THRESHOLD_DEFAULT
        )
        if matched:
            logger.info("S2b モーダル検出 (score=%.3f)", score)
            self._transition(State.S2B_CONFIRM)
            return

        # S1 復帰検出
        s1_matched, s1_score, _ = self._matcher.match(
            frame, "ui/s1_ultimate_synthesis_label", S1_ULTIMATE_LABEL_ROI, TM_THRESHOLD_DEFAULT
        )
        if s1_matched:
            logger.info("S1 復帰検出 (score=%.3f)", s1_score)
            self._finish_confirm()

    def _handle_s2b(self, frame: npt.NDArray[np.uint8]) -> None:
        """S2b モーダル（錬成結果反映確認）: 「OK」ボタンをクリックして CONFIRMING_RESULT に戻る."""
        matched, score, _ = self._matcher.match(
            frame, "ui/s2b_modal_title", S2B_MODAL_TITLE_ROI, TM_THRESHOLD_DEFAULT
        )
        if matched:
            ok_matched, _, _ = self._matcher.match(
                frame, "ui/buttons/s2b_ok", S2B_BTN_OK_ROI, TM_THRESHOLD_BUTTON
            )
            if ok_matched:
                self._automator.click_center(S2B_BTN_OK_ROI)
                self._confirm_result_start = time.time()
                self._transition(State.CONFIRMING_RESULT)
            else:
                logger.warning("S2b: OK ボタンが検出できませんでした")
        else:
            # モーダルが消えた場合は CONFIRMING_RESULT に戻って S1 検出へ
            logger.debug("S2b: モーダル消失。CONFIRMING_RESULT に戻ります。(score=%.3f)", score)
            self._confirm_result_start = time.time()
            self._transition(State.CONFIRMING_RESULT)

    # ------------------------------------------------------------------
    # ユーティリティ
    # ------------------------------------------------------------------

    def _finish_confirm(self) -> None:
        """CONFIRMING_RESULT 後の遷移を完了する."""
        if self._after_confirm_next == State.COMPLETED:
            self._transition(State.COMPLETED)
            self.completed.emit()
        else:
            self._transition(self._after_confirm_next)

    def _click_confirm_button(self, frame: npt.NDArray[np.uint8]) -> None:
        """「結果確定」ボタンを確認してクリックする."""
        matched, score, _ = self._matcher.match(
            frame, "ui/buttons/s2_confirm", S2_BTN_CONFIRM_ROI, TM_THRESHOLD_BUTTON
        )
        if matched:
            self._automator.click_center(S2_BTN_CONFIRM_ROI)
        else:
            logger.warning("「結果確定」ボタンが検出できませんでした (score=%.3f)", score)

    def _detect_frame(self, frame: npt.NDArray[np.uint8]) -> DetectionResult:
        """フレームから S2 のサブステータスを検出する."""
        equipment = self._evaluator.equipment

        if equipment.type == EquipmentType.WEAPON and equipment.id in WEAPON_SPECIAL_IDS:
            category = "weapon_special"
        else:
            category = str(equipment.type)

        candidate_stats = equipment.get_stat_pool_stats()

        substats: list[SubstatSlot] = []
        for i, slot_roi in enumerate(S2_SUBSTAT_ROIS):
            is_locked = self._matcher.detect_lock_state(frame, slot_roi)

            prefix = "substats/s2/locked" if is_locked else "substats/s2"
            stat = self._matcher.read_substat_name(
                frame, S2_SUBSTAT_NAME_ROIS[i], candidate_stats, template_prefix=prefix
            )

            value: str | None = None
            if stat is not None:
                entry = equipment.get_stat_pool_entry(stat)
                if entry is not None:
                    scale = STAT_TO_SCALE.get(stat, "hpdef")
                    value = self._matcher.read_stat_value(
                        frame, S2_SUBSTAT_VALUE_ROIS[i], category, scale, entry.values
                    )

            substats.append(
                SubstatSlot(
                    slot_index=i,
                    stat=stat,
                    value=value,
                    is_locked=bool(is_locked),
                )
            )

        return DetectionResult(
            screen_id="S2",
            equipment_id=equipment.id,
            substats=substats,
        )

    def _transition(self, new_state: State) -> None:
        """状態を遷移してシグナルを発火する."""
        if self._state != new_state:
            logger.debug("状態遷移: %s → %s", self._state, new_state)
            self._state = new_state
        self._emit_state()

    def _emit_state(self) -> None:
        """現在の状態名シグナルを発火する."""
        self.state_changed.emit(STATE_DISPLAY_NAMES.get(self._state, self._state))

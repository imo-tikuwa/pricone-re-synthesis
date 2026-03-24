"""メインウィンドウ."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from src.core.automator import Automator
from src.core.capture import ScreenCapture
from src.core.constants import (
    EX_PT_ROI,
    MANA_ROI,
    S1_SUBSTAT_LOCK_ROIS,
    S1_SUBSTAT_NAME_ROIS,
    S1_SUBSTAT_VALUE_ROIS,
    STAT_DISPLAY_NAMES,
    STAT_TO_SCALE,
    WEAPON_SPECIAL_IDS,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    State,
)
from src.core.equipment_detector import EquipmentDetector
from src.core.evaluator import ResultEvaluator
from src.core.matcher import TemplateMatcher
from src.core.state_machine import StateMachineWorker
from src.data.models import EquipmentData, EquipmentType, GoalCondition, SubstatSlot
from src.gui.widgets import _PREVIEW_W, CaptureDisplayWidget, InfoPanelWidget

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _generate_ex_pt_thresholds(current: int) -> list[int]:
    """残量下限の候補リストを生成する.

    - 現在ブラケットより 2段階以上下: 100万刻み
    - 現在ブラケットの 1つ下のブラケットから現在値まで: 10万刻み
    """
    current_1m_base = (current // 1_000_000) * 1_000_000
    fine_1m_start = max(0, current_1m_base - 1_000_000)  # 1段下のブラケット起点
    thresholds: list[int] = []

    # 粗い刻み（100万単位）: 1M から fine_1m_start の手前まで
    v = 1_000_000
    while v < fine_1m_start:
        thresholds.append(v)
        v += 1_000_000

    # 細かい刻み（10万単位）: 1段下ブラケット起点から現在値以下まで
    fine_start = max(100_000, fine_1m_start)
    fine_end = (current // 100_000) * 100_000
    v = fine_start
    while v <= fine_end:
        thresholds.append(v)
        v += 100_000

    return thresholds


class MainWindow(QMainWindow):
    """究極錬成ツール メインウィンドウ."""

    def __init__(self, debug: bool = False, initial_state: State | None = None) -> None:
        super().__init__()
        self._debug = debug
        self._initial_state = initial_state

        # コアコンポーネント初期化
        self._capture = ScreenCapture(WINDOW_TITLE)
        self._matcher = TemplateMatcher()
        self._automator = Automator()
        self._detector: EquipmentDetector | None = None  # _load_resources 後に初期化
        self._current_equipment: EquipmentData | None = None
        self._worker: StateMachineWorker | None = None
        self._synthesis_count = 0
        self._total_synthesis_count = 0
        self._all_slots_locked = False
        self._stopping = False
        self._esc_was_down = False

        # テンプレート・装備データ読み込み
        self._load_resources()

        # UI 構築
        self._setup_ui()
        self._apply_dark_theme()

        # キャプチャタイマー（常時動作）
        self._capture_timer = QTimer(self)
        self._capture_timer.timeout.connect(self._on_capture_tick)
        self._capture_timer.start(300)  # 初期値 300ms（0.3秒）

        # ゲームウィンドウ追従タイマー
        self._snap_timer = QTimer(self)
        self._snap_timer.timeout.connect(self._on_snap_tick)
        self._snap_timer.start(500)

        # グローバル Esc 監視タイマー（自動化中のみ動作）
        self._hotkey_timer = QTimer(self)
        self._hotkey_timer.setInterval(150)
        self._hotkey_timer.timeout.connect(self._check_global_esc)

    # ------------------------------------------------------------------
    # 初期化
    # ------------------------------------------------------------------

    def _load_resources(self) -> None:
        """テンプレートを読み込む."""
        self._matcher.load_from_npz()
        self._matcher.load_color_templates()
        self._detector = EquipmentDetector(self._matcher)
        logger.info("リソース読み込み完了")

    def _setup_ui(self) -> None:
        """UI レイアウトを構築する."""
        self.setWindowTitle("PrincessConnectReDive 究極錬成 - 自動化ツール")
        # 最大化ボタンを無効化（Windows では MSWindowsFixedSizeDialogHint も必要）
        self.setWindowFlags(
            (self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)
            | Qt.WindowType.MSWindowsFixedSizeDialogHint
        )

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        # 上部: キャプチャ画像
        self._capture_display = CaptureDisplayWidget()
        root_layout.addWidget(self._capture_display)

        # 中部: 検出情報パネル（プレビュー下）
        self._info_panel = InfoPanelWidget()
        self._info_panel.setFixedWidth(_PREVIEW_W)
        root_layout.addWidget(self._info_panel)

        # 完了・中断条件設定
        goal_group = QGroupBox("完了・中断条件設定")
        goal_outer = QVBoxLayout(goal_group)
        goal_outer.setContentsMargins(8, 6, 8, 6)
        goal_outer.setSpacing(6)

        # 完了条件行
        complete_row = QHBoxLayout()
        complete_row.setSpacing(8)
        _lbl_stat = QLabel("目標ステータス")
        _lbl_stat.setStyleSheet("color: #aaa;")
        complete_row.addWidget(_lbl_stat)
        self._stat_combo = QComboBox()
        self._stat_combo.setMinimumWidth(160)
        self._stat_combo.currentIndexChanged.connect(self._on_stat_changed)
        complete_row.addWidget(self._stat_combo)
        _lbl_min = QLabel("最低値")
        _lbl_min.setStyleSheet("color: #aaa;")
        complete_row.addWidget(_lbl_min)
        self._min_value_combo = QComboBox()
        self._min_value_combo.setMinimumWidth(80)
        complete_row.addWidget(self._min_value_combo)
        _lbl_slots = QLabel("必要枠数")
        _lbl_slots.setStyleSheet("color: #aaa;")
        complete_row.addWidget(_lbl_slots)
        self._required_slots_combo = QComboBox()
        for n in range(1, 5):
            self._required_slots_combo.addItem(f"{n}枠以上", userData=n)
        self._required_slots_combo.setCurrentIndex(0)
        complete_row.addWidget(self._required_slots_combo)
        complete_row.addStretch()
        goal_outer.addLayout(complete_row)

        # 中断条件行
        interrupt_row = QHBoxLayout()
        interrupt_row.setSpacing(8)
        _lbl_ex = QLabel("錬成Ptが次の値を下回ったら中断")
        _lbl_ex.setStyleSheet("color: #aaa;")
        interrupt_row.addWidget(_lbl_ex)
        self._min_ex_pt_combo = QComboBox()
        self._min_ex_pt_combo.setMinimumWidth(100)
        self._min_ex_pt_combo.addItem("制限なし", userData=0)
        self._last_ex_pt_combo_base: int = -1
        interrupt_row.addWidget(self._min_ex_pt_combo)
        interrupt_row.addStretch()
        goal_outer.addLayout(interrupt_row)

        root_layout.addWidget(goal_group)

        # その他設定
        sub_settings_row = QHBoxLayout()
        sub_settings_row.setSpacing(8)

        other_group = QGroupBox("その他設定")
        other_inner = QHBoxLayout(other_group)
        other_inner.setSpacing(8)
        _lbl_interval = QLabel("キャプチャ間隔(秒)")
        _lbl_interval.setStyleSheet("color: #aaa;")
        other_inner.addWidget(_lbl_interval)
        self._interval_combo = QComboBox()
        for v in [0.1, 0.2, 0.3, 0.5, 1.0]:
            self._interval_combo.addItem(f"{v:.1f}", userData=v)
        self._interval_combo.setCurrentIndex(2)  # 0.3
        self._interval_combo.currentIndexChanged.connect(self._on_interval_changed)
        other_inner.addWidget(self._interval_combo)
        self._snap_cb = QCheckBox("ゲームに追従")
        self._snap_cb.setChecked(True)
        self._snap_cb.setToolTip("ゲームウィンドウの横にツールウィンドウを追従させる")
        other_inner.addWidget(self._snap_cb)
        other_inner.addStretch()

        sub_settings_row.addWidget(other_group, stretch=1)
        root_layout.addLayout(sub_settings_row)

        # 開始/停止ボタン → info panel の buttons_layout に配置（交互表示）
        self._start_btn = QPushButton("開始")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start)
        self._start_btn.setStyleSheet(
            "QPushButton { background-color: #2060d0; color: white; font-weight: bold; "
            "border-radius: 4px; padding: 8px 4px; } "
            "QPushButton:hover { background-color: #3070e0; } "
            "QPushButton:disabled { background-color: #333; color: #666; }"
        )

        self._stop_btn = QPushButton("停止  [Esc]")
        self._stop_btn.setEnabled(False)
        self._stop_btn.setVisible(False)
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setStyleSheet(
            "QPushButton { background-color: #883030; color: white; font-weight: bold; "
            "border-radius: 4px; padding: 8px 4px; } "
            "QPushButton:hover { background-color: #aa3030; } "
            "QPushButton:disabled { background-color: #333; color: #666; }"
        )

        bl = self._info_panel.buttons_layout
        bl.addWidget(self._start_btn)
        bl.addWidget(self._stop_btn)

        # ステータスバー
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._state_label = QLabel("待機中")
        self._state_label.setStyleSheet("color: #88ccff; padding-left: 4px;")

        _count_max = "錬成回数 999回"
        self._count_status_label = QLabel("錬成回数   0回")
        self._count_status_label.setStyleSheet("color: #aaa;")
        self._count_status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._count_status_label.setMinimumWidth(
            self._count_status_label.fontMetrics().horizontalAdvance(_count_max) + 8
        )

        _total_max = "総錬成回数 999回"
        self._total_count_label = QLabel("総錬成回数   0回")
        self._total_count_label.setStyleSheet("color: #aaa; padding-right: 4px;")
        self._total_count_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._total_count_label.setMinimumWidth(
            self._total_count_label.fontMetrics().horizontalAdvance(_total_max) + 8
        )

        self._status_bar.addWidget(self._state_label, 1)
        self._status_bar.addPermanentWidget(self._count_status_label)
        self._status_bar.addPermanentWidget(self._total_count_label)

        # Escape キーで停止
        esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        esc_shortcut.activated.connect(self._on_stop)

    def _apply_dark_theme(self) -> None:
        """ダークテーマの基本スタイルを適用する."""
        self.setStyleSheet(
            "QMainWindow, QWidget { background-color: #1e1e1e; color: #eee; } "
            "QGroupBox { border: 1px solid #444; border-radius: 4px; "
            "margin-top: 8px; padding-top: 4px; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #aaa; } "
            "QComboBox { background-color: #2a2a2a; color: #eee; "
            "border: 1px solid #555; border-radius: 3px; padding: 2px 4px; } "
            "QLabel { color: #eee; } "
            "QCheckBox { color: #eee; } "
            "QStatusBar { color: #aaa; border-top: 1px solid #444; } "
            "QStatusBar::item { border: none; }"
        )

    # ------------------------------------------------------------------
    # スロット
    # ------------------------------------------------------------------

    @pyqtSlot()
    def _on_start(self) -> None:
        """開始ボタン押下."""
        # ゲームプロセス確認
        if not self._capture.find_window():
            QMessageBox.critical(
                self,
                "エラー",
                f"ゲームウィンドウ「{WINDOW_TITLE}」が見つかりません。\n"
                "ゲームを起動して究極錬成画面を開いてから再試行してください。",
            )
            return

        goal = self._build_goal()
        if goal is None:
            QMessageBox.warning(self, "設定エラー", "目標ステータスが選択されていません。")
            return

        equipment = self._current_equipment
        if equipment is None:
            QMessageBox.warning(
                self,
                "装備未検出",
                "装備がまだ自動検出されていません。\n"
                "ゲームを究極錬成の装備選択画面にしてください。",
            )
            return

        evaluator = ResultEvaluator(equipment, goal)

        # 開始時点の S1 ロック状態を読み取って evaluator に反映する
        # （既ロック枠を「新規一致」と誤認して不要な S1 復帰が起きるのを防ぐ）
        start_frame = self._capture.capture()
        if start_frame is not None:
            initial_locked: set[int] = set()
            for i in range(4):
                if self._matcher.detect_lock_state(start_frame, S1_SUBSTAT_LOCK_ROIS[i]):
                    initial_locked.add(i)
            if initial_locked:
                evaluator.update_locks(initial_locked)
                logger.info("開始時ロック済み枠: %s", sorted(initial_locked))

        initial = self._initial_state or State.CHECKING_SCREEN
        interval: float = self._interval_combo.currentData()

        self._worker = StateMachineWorker(
            capture=self._capture,
            matcher=self._matcher,
            automator=self._automator,
            evaluator=evaluator,
            goal=goal,
            capture_interval=interval,
            initial_state=initial,
        )
        self._worker.state_changed.connect(self._on_state_changed)
        self._worker.synthesis_count_changed.connect(self._on_synthesis_count)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.completed.connect(self._on_completed)
        self._worker.lock_warning.connect(self._on_lock_warning)
        self._worker.resources_updated.connect(self._on_resources_updated)
        self._worker.finished.connect(self._on_worker_finished)

        self._synthesis_count = 0
        self._count_status_label.setText("錬成回数   0回")
        self._start_btn.setVisible(False)
        self._stop_btn.setEnabled(True)
        self._stop_btn.setVisible(True)
        self._esc_was_down = False
        self._hotkey_timer.start()
        for w in [
            self._stat_combo,
            self._min_value_combo,
            self._required_slots_combo,
            self._min_ex_pt_combo,
            self._interval_combo,
            self._snap_cb,
        ]:
            w.setEnabled(False)
        self._worker.start()

    @pyqtSlot()
    def _on_stop(self) -> None:
        """停止ボタン押下."""
        if self._worker is None:
            return
        self._stopping = True
        self._stop_btn.setEnabled(False)
        self._worker.stop()
        self._state_label.setText("停止中...")
        # クリーンアップは _on_worker_finished で行う

    @pyqtSlot()
    def _on_worker_finished(self) -> None:
        """ワーカースレッド終了時のクリーンアップ."""
        self._worker = None
        for w in [
            self._stat_combo,
            self._min_value_combo,
            self._required_slots_combo,
            self._min_ex_pt_combo,
            self._interval_combo,
            self._snap_cb,
        ]:
            w.setEnabled(True)
        if self._state_label.text() == "停止中...":
            self._state_label.setText("停止しました")
        self._hotkey_timer.stop()
        self._esc_was_down = False
        if self._stopping:
            self._state_label.setText("停止しました")
        self._stopping = False
        self._stop_btn.setVisible(False)
        self._stop_btn.setEnabled(False)
        self._start_btn.setVisible(True)
        self._update_start_button()

    @pyqtSlot(str)
    def _on_state_changed(self, state_name: str) -> None:
        """状態変化シグナル受信."""
        if self._stopping:
            return
        self._state_label.setText(state_name)

    @pyqtSlot(int)
    def _on_synthesis_count(self, count: int) -> None:
        """錬成回数更新."""
        self._synthesis_count = count
        self._total_synthesis_count += 1
        self._count_status_label.setText(f"錬成回数 {count:>3}回")
        self._total_count_label.setText(f"総錬成回数 {self._total_synthesis_count:>3}回")

    @pyqtSlot(str)
    def _on_error(self, message: str) -> None:
        """エラー発生."""
        self._bring_to_front()
        QMessageBox.critical(self, "エラー", message)

    @pyqtSlot()
    def _on_completed(self) -> None:
        """完了シグナル受信."""
        self._state_label.setText(f"完了！ 錬成 {self._synthesis_count} 回で目標を達成しました。")
        self._bring_to_front()
        QMessageBox.information(
            self,
            "完了",
            f"目標ステータスの錬成が完了しました！\n錬成回数: {self._synthesis_count} 回",
        )

    @pyqtSlot(int, int)
    def _on_resources_updated(self, mana: int, ex_pt: int) -> None:
        """ステートマシンが S1 で読み取ったリソース値でパネルを更新する."""
        self._info_panel.update_resources(mana, ex_pt)
        self._refresh_ex_pt_combo(ex_pt)

    @pyqtSlot(int)
    def _on_lock_warning(self, slot_index: int) -> None:
        """ロック失敗警告."""
        self._bring_to_front()
        QMessageBox.warning(
            self,
            "ロック失敗",
            f"枠 {slot_index + 1} のロックに失敗しました。\n"
            "手動でロック状態を確認してから「開始」を押してください。",
        )
        self._on_stop()

    @pyqtSlot()
    def _on_capture_tick(self) -> None:
        """キャプチャタイマーのティック: 画面をキャプチャして GUI を更新する."""
        frame = self._capture.capture(bring_to_front=False)
        if frame is None:
            return

        h, w = frame.shape[:2]
        if w != WINDOW_WIDTH or h != WINDOW_HEIGHT:
            self._capture_display.update_frame(frame)
            self._capture_timer.stop()
            QMessageBox.critical(
                self,
                "ウィンドウサイズエラー",
                f"ゲームウィンドウのサイズが正しくありません。\n"
                f"期待: {WINDOW_WIDTH}×{WINDOW_HEIGHT} px\n"
                f"実際: {w}×{h} px\n\n"
                "ウィンドウサイズを元に戻してからツールを再起動してください。",
            )
            self.close()
            return

        self._capture_display.update_frame(frame)

        # 自動化中に S1 画面にいる場合もサブステータス表示を更新する（部分一致後のロック反映）
        if (
            self._worker is not None
            and self._current_equipment is not None
            and self._worker.current_state
            in {State.S1_EQUIP_SELECT, State.APPLYING_LOCKS, State.CHECKING_RESOURCES}
        ):
            substats = self._read_s1_substats(frame)
            self._info_panel.update_substats(substats)

        # 自動化実行中はステートマシン側で管理するため検出しない
        if self._worker is None and self._detector is not None:
            eq = self._detector.detect(frame)
            equipment_changed = eq is not None and eq != self._current_equipment
            if equipment_changed and eq is not None:
                self.set_detected_equipment(eq)

            if self._current_equipment is not None:
                substats = self._read_s1_substats(frame)
                self._info_panel.update_substats(substats)
                if equipment_changed:
                    self._auto_set_goal_from_locks(substats)
                all_locked = len(substats) == 4 and all(s.is_locked for s in substats)
                if all_locked != self._all_slots_locked:
                    self._all_slots_locked = all_locked
                    self._update_start_button()

            mana = self._matcher.read_digits(frame, MANA_ROI, color="black")
            ex_pt = self._matcher.read_digits(frame, EX_PT_ROI, color="black")
            self._info_panel.update_resources(mana, ex_pt)
            if ex_pt is not None:
                self._refresh_ex_pt_combo(ex_pt)

        # デバッグモード: ROI オーバーレイを描画（TODO: デバッグ ROI 描画実装）
        if self._debug:
            pass

    @pyqtSlot(int)
    def _on_interval_changed(self, _index: int) -> None:
        """キャプチャ間隔変更."""
        value: float = self._interval_combo.currentData()
        self._capture_timer.setInterval(int(value * 1000))

    @pyqtSlot()
    def _check_global_esc(self) -> None:
        """Esc キーのグローバル押下を検知して停止する.

        ゲームウィンドウがフォアグラウンドでも動作するよう GetAsyncKeyState でポーリングする。
        """
        if self._worker is None:
            return
        try:
            import win32api

            is_down = bool(win32api.GetAsyncKeyState(0x1B) & 0x8000)  # VK_ESCAPE
            if is_down and not self._esc_was_down:
                self._on_stop()
            self._esc_was_down = is_down
        except Exception:
            pass

    @pyqtSlot()
    def _on_snap_tick(self) -> None:
        """ゲームウィンドウの横にツールウィンドウを追従させる."""
        if not self._snap_cb.isChecked():
            return

        hwnd = self._capture.hwnd
        if hwnd is None:
            self._capture.find_window()
            hwnd = self._capture.hwnd
        if hwnd is None:
            return

        try:
            import win32gui

            left, top, right, _bottom = win32gui.GetWindowRect(hwnd)
            # ゲームウィンドウが最小化されている場合はスキップ
            if right <= left:
                return
            self.move(right + 4, top)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # ユーティリティ
    # ------------------------------------------------------------------

    def _refresh_stat_combo(self) -> None:
        """選択中装備に応じて目標ステータスコンボを更新する."""
        self._stat_combo.clear()
        if self._current_equipment is None:
            self._min_value_combo.clear()
            return

        for entry in self._current_equipment.stat_pool:
            display = STAT_DISPLAY_NAMES.get(entry.stat, entry.stat)
            self._stat_combo.addItem(display, userData=entry.stat)

        if self._stat_combo.count() > 0:
            self._stat_combo.setCurrentIndex(0)
        self._refresh_min_value_combo()
        self._update_start_button()

    @pyqtSlot(int)
    def _on_stat_changed(self, _index: int) -> None:
        """目標ステータスコンボ変更時に最低値コンボを更新する."""
        self._refresh_min_value_combo()
        self._update_start_button()

    def _refresh_min_value_combo(self) -> None:
        """選択中ステータスに応じて最低値コンボを更新する."""
        self._min_value_combo.clear()
        if self._current_equipment is None:
            return
        stat = self._stat_combo.currentData()
        if stat is None:
            return
        entry = self._current_equipment.get_stat_pool_entry(stat)
        if entry is None:
            return
        for v in entry.values:
            self._min_value_combo.addItem(v, userData=v)
        # デフォルトは最大値（最も要求が厳しい値）を選択
        if self._min_value_combo.count() > 0:
            self._min_value_combo.setCurrentIndex(self._min_value_combo.count() - 1)

    def set_detected_equipment(self, equipment: EquipmentData) -> None:
        """自動検出された装備を反映する（ステートマシンから呼び出す）."""
        self._current_equipment = equipment
        self._all_slots_locked = False
        type_display = {"weapon": "武器", "armor": "防具", "charm": "アクセサリー"}.get(
            equipment.type.value, equipment.type.value
        )
        self._info_panel.update_equipment(equipment.display_name, type_display)
        self._refresh_stat_combo()

    def _auto_set_goal_from_locks(self, substats: list[SubstatSlot]) -> None:
        """ロック済み枠が1種類のみの場合、目標ステータスと必要枠数を自動設定する.

        - ロック枠なし / 2種類以上の場合は何もしない
        - 目標ステータス: ロック枠の効果名
        - 最低値: 変更しない（_refresh_stat_combo の初期値=最大値のまま）
        - 必要枠数: ロック枠数 + 1（最大 4）
        """
        locked = [s for s in substats if s.is_locked and s.stat is not None]
        if not locked:
            return
        locked_stats = {s.stat for s in locked}
        if len(locked_stats) != 1:
            return

        locked_stat = next(iter(locked_stats))
        stat_idx = self._stat_combo.findData(locked_stat)
        if stat_idx >= 0:
            self._stat_combo.setCurrentIndex(stat_idx)

        required = min(len(locked) + 1, 4)
        slots_idx = self._required_slots_combo.findData(required)
        if slots_idx >= 0:
            self._required_slots_combo.setCurrentIndex(slots_idx)

    def _update_start_button(self) -> None:
        """開始ボタンの活性・非活性を設定する."""
        can_start = (
            self._worker is None
            and self._current_equipment is not None
            and self._stat_combo.count() > 0
            and not self._all_slots_locked
        )
        self._start_btn.setEnabled(can_start)
        if self._current_equipment is None:
            self._start_btn.setToolTip("装備が自動検出されていません")
        elif self._all_slots_locked:
            self._start_btn.setToolTip("全枠ロック済みの装備が選択されています")
        elif self._stat_combo.count() == 0:
            self._start_btn.setToolTip("目標ステータスを選択してください")
        else:
            self._start_btn.setToolTip("")

    def _build_goal(self) -> GoalCondition | None:
        """現在の設定から GoalCondition を生成する."""
        stat = self._stat_combo.currentData()
        if stat is None:
            return None
        min_value = self._min_value_combo.currentData()
        if min_value is None:
            return None
        required_slots = self._required_slots_combo.currentData()
        min_ex_pt = self._min_ex_pt_combo.currentData() or 0
        return GoalCondition(
            target_stat=stat,
            min_value=min_value,
            required_slots=required_slots,
            min_ex_pt=min_ex_pt,
        )

    def _read_s1_substats(self, frame: object) -> list[SubstatSlot]:
        """S1 画面からサブステータス 4 枠を読み取る."""
        import numpy as np
        import numpy.typing as npt

        f: npt.NDArray[np.uint8] = frame  # type: ignore[assignment]
        eq = self._current_equipment
        if eq is None:
            return []

        if eq.type == EquipmentType.WEAPON and eq.id in WEAPON_SPECIAL_IDS:
            category = "weapon_special"
        else:
            category = str(eq.type)

        candidate_stats = eq.get_stat_pool_stats()
        substats: list[SubstatSlot] = []

        for i in range(4):
            is_locked = self._matcher.detect_lock_state(f, S1_SUBSTAT_LOCK_ROIS[i])

            stat = self._matcher.read_substat_name(f, S1_SUBSTAT_NAME_ROIS[i], candidate_stats)

            value: str | None = None
            if stat is not None:
                entry = eq.get_stat_pool_entry(stat)
                if entry is not None:
                    scale = STAT_TO_SCALE.get(stat, "hpdef")
                    value = self._matcher.read_stat_value(
                        f, S1_SUBSTAT_VALUE_ROIS[i], category, scale, entry.values
                    )

            substats.append(
                SubstatSlot(slot_index=i, stat=stat, value=value, is_locked=bool(is_locked))
            )

        return substats

    def _refresh_ex_pt_combo(self, current_ex_pt: int) -> None:
        """EX錬成Pt の現在値に基づいて残量下限コンボを再生成する.

        現在値が 10万単位で変化したときだけ再生成する。
        """
        base_key = current_ex_pt // 100_000
        if base_key == self._last_ex_pt_combo_base:
            return
        self._last_ex_pt_combo_base = base_key

        thresholds = _generate_ex_pt_thresholds(current_ex_pt)
        current_val: int = self._min_ex_pt_combo.currentData() or 0
        # 未設定（制限なし）の場合は最大閾値（最も早く中断される値）をデフォルトにする
        if current_val == 0 and thresholds:
            current_val = thresholds[-1]

        self._min_ex_pt_combo.blockSignals(True)
        self._min_ex_pt_combo.clear()
        self._min_ex_pt_combo.addItem("制限なし", userData=0)
        for t in thresholds:
            self._min_ex_pt_combo.addItem(f"{t:,}", userData=t)

        idx = self._min_ex_pt_combo.findData(current_val)
        self._min_ex_pt_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._min_ex_pt_combo.blockSignals(False)

    def _bring_to_front(self) -> None:
        """ウィンドウを最前面に移動する."""
        self.setWindowState(
            self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive
        )
        self.raise_()
        self.activateWindow()

        try:
            import ctypes

            hwnd = int(self.winId())
            ctypes.windll.user32.SetForegroundWindow(hwnd)  # type: ignore[attr-defined]
        except Exception:
            pass  # Windows 以外 / 権限なしは無視

    def showEvent(self, event: object) -> None:
        """表示時にウィンドウサイズを固定する（幅はプレビュー幅基準）."""
        super().showEvent(event)  # type: ignore[arg-type]
        w = _PREVIEW_W + 2 * 8  # プレビュー幅 + root_layout の左右マージン
        self.setFixedSize(w, self.sizeHint().height())

    def closeEvent(self, event: object) -> None:
        """ウィンドウクローズ時に自動錬成を停止する."""
        if self._worker is not None:
            self._worker.stop()
            self._worker.wait(2000)
            self._worker = None
        super().closeEvent(event)  # type: ignore[arg-type]

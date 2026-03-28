"""カスタムウィジェット群."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.constants import STAT_DISPLAY_NAMES
from src.data.models import SubstatSlot

if TYPE_CHECKING:
    import numpy.typing as npt


class SubstatSlotWidget(QFrame):
    """サブステータス 1 枠分の表示ウィジェット.

    効果名・ロックアイコン・値を 1 行で表示する。
    """

    def __init__(self, slot_index: int, parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self._slot_index = slot_index
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self._stat_label = QLabel("―")
        self._stat_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        self._lock_label = QLabel("")
        self._lock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lock_label.setFixedWidth(24)

        self._value_label = QLabel("")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._value_label.setFixedWidth(44)

        layout.addWidget(self._stat_label, 0, 0)
        layout.addWidget(self._lock_label, 0, 1)
        layout.addWidget(self._value_label, 0, 2)
        layout.setColumnStretch(0, 1)  # stat_label が余白を全て取る

        self.setFrameShape(QFrame.Shape.Box)
        self.setStyleSheet("background-color: #2a2a2a; border: 1px solid #444; border-radius: 3px;")

    def update_slot(self, slot: SubstatSlot) -> None:
        """SubstatSlot データを元に表示を更新する."""
        if slot.stat is None:
            self._stat_label.setText("錬成されていません")
            self._stat_label.setStyleSheet("color: #888;")
            self._lock_label.setText("")
            self._value_label.setText("")
        else:
            display_name = STAT_DISPLAY_NAMES.get(slot.stat, slot.stat)
            self._stat_label.setText(display_name)
            self._stat_label.setStyleSheet("color: #eee;")

            if slot.is_locked:
                self._lock_label.setText("🔒")
                self._lock_label.setStyleSheet("color: #f0c040;")
            else:
                self._lock_label.setText("")
                self._lock_label.setStyleSheet("")

            self._value_label.setText(slot.value or "")
            self._value_label.setStyleSheet(
                "color: #f0c040; font-weight: bold;" if slot.is_locked else "color: #eee;"
            )

    def clear(self) -> None:
        """表示をリセットする."""
        self._stat_label.setText("―")
        self._stat_label.setStyleSheet("color: #888;")
        self._lock_label.setText("")
        self._value_label.setText("")


class SubstatGridWidget(QWidget):
    """サブステータス 4 枠（2×2）の表示ウィジェット."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._slots = [SubstatSlotWidget(i) for i in range(4)]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for slot_widget, (row, col) in zip(self._slots, positions, strict=True):
            layout.addWidget(slot_widget, row, col)

    def update_substats(self, substats: list[SubstatSlot]) -> None:
        """4 枠分のサブステータスを更新する."""
        if not substats:
            self.clear()
            return
        for slot_data in substats:
            if 0 <= slot_data.slot_index < 4:
                self._slots[slot_data.slot_index].update_slot(slot_data)

    def clear(self) -> None:
        """全枠をリセットする."""
        for slot in self._slots:
            slot.clear()


_PREVIEW_W = 560
_PREVIEW_H = 315  # 16:9


class CaptureDisplayWidget(QLabel):
    """キャプチャ画像を縮小表示するウィジェット（16:9 固定サイズ）."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(_PREVIEW_W, _PREVIEW_H)
        self.setStyleSheet("background-color: #111; border: 1px solid #333;")
        self.setText("キャプチャ待機中...")

    def update_frame(self, frame: npt.NDArray[np.uint8]) -> None:
        """BGR numpy 配列を QPixmap に変換して表示する."""
        if frame is None:
            return

        h, w, c = frame.shape
        if c == 3:
            # BGR → RGB
            rgb = frame[:, :, ::-1].copy()
            qimage = QImage(bytes(rgb.data), w, h, w * 3, QImage.Format.Format_RGB888)
        else:
            qimage = QImage(bytes(frame.data), w, h, w * c, QImage.Format.Format_BGR888)

        pixmap = QPixmap.fromImage(qimage)
        scaled = pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def clear_display(self) -> None:
        """表示をリセットする."""
        self.clear()
        self.setText("キャプチャ待機中...")


class InfoPanelWidget(QWidget):
    """検出情報パネル."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ── 選択中の装備情報（左3）＋ 消費アイテム情報（右1）────
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        # 選択中の装備情報
        equip_group = QGroupBox("選択中の装備情報")
        equip_inner = QVBoxLayout(equip_group)
        equip_inner.setContentsMargins(6, 6, 6, 6)
        equip_inner.setSpacing(8)

        equip_info_row = QHBoxLayout()
        equip_info_row.setSpacing(4)

        name_title = QLabel("装備")
        name_title.setStyleSheet("color: #aaa;")
        name_title.setFixedWidth(32)
        self._equipment_label = QLabel("―")
        self._equipment_label.setStyleSheet("color: #eee;")
        equip_info_row.addWidget(name_title)
        equip_info_row.addWidget(self._equipment_label)

        equip_info_row.addSpacing(10)

        type_title = QLabel("種類")
        type_title.setStyleSheet("color: #aaa;")
        type_title.setFixedWidth(32)
        self._equipment_type_label = QLabel("―")
        self._equipment_type_label.setStyleSheet("color: #eee;")
        equip_info_row.addWidget(type_title)
        equip_info_row.addWidget(self._equipment_type_label)

        equip_inner.addLayout(equip_info_row)

        self._substat_grid = SubstatGridWidget()
        equip_inner.addWidget(self._substat_grid)

        # 消費アイテム情報
        resource_group = QGroupBox("消費アイテム")
        resource_outer = QVBoxLayout(resource_group)
        resource_outer.setContentsMargins(6, 6, 6, 6)
        resource_outer.setSpacing(0)

        resource_grid = QGridLayout()
        resource_grid.setHorizontalSpacing(4)
        resource_grid.setVerticalSpacing(8)
        resource_grid.setColumnStretch(1, 1)

        ex_pt_title = QLabel("錬成Pt")
        ex_pt_title.setStyleSheet("color: #aaa;")
        self._ex_pt_label = QLabel("―")
        self._ex_pt_label.setStyleSheet("color: #eee; font-weight: bold;")
        self._ex_pt_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        mana_title = QLabel("マナ")
        mana_title.setStyleSheet("color: #aaa;")
        self._mana_label = QLabel("―")
        self._mana_label.setStyleSheet("color: #eee; font-weight: bold;")
        self._mana_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        resource_grid.addWidget(ex_pt_title, 0, 0)
        resource_grid.addWidget(self._ex_pt_label, 0, 1)
        resource_grid.addWidget(mana_title, 1, 0)
        resource_grid.addWidget(self._mana_label, 1, 1)

        resource_outer.addLayout(resource_grid)
        resource_outer.addStretch()

        # 右カラム: 固定幅 QWidget に resource_group + ボタン行を収める
        right_widget = QWidget()
        right_widget.setFixedWidth(140)
        right_col = QVBoxLayout(right_widget)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(4)
        right_col.addWidget(resource_group)

        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout.setSpacing(8)
        right_col.addLayout(self.buttons_layout)

        top_row.addWidget(equip_group, stretch=1)
        top_row.addWidget(right_widget)
        layout.addLayout(top_row)

    def update_equipment(self, name: str, eq_type: str) -> None:
        """装備情報を更新する."""
        self._equipment_label.setText(name)
        self._equipment_type_label.setText(eq_type)

    def update_resources(self, mana: int | None, ex_pt: int | None) -> None:
        """リソース残量表示を更新する."""
        self._mana_label.setText(f"{mana:,}" if mana is not None else "―")
        self._ex_pt_label.setText(f"{ex_pt:,}" if ex_pt is not None else "―")

    def update_substats(self, substats: list[SubstatSlot]) -> None:
        """サブステータスグリッドを更新する."""
        self._substat_grid.update_substats(substats)

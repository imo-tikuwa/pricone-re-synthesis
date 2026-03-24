"""マウス・キーボード自動操作モジュール (Windows 専用)."""

from __future__ import annotations

import logging
import random
import time

import win32api
import win32gui

MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

logger = logging.getLogger(__name__)


class Automator:
    """ゲームウィンドウへのマウスクリック操作を担うクラス (Windows 専用).

    SetForegroundWindow でゲームを前面に出し、ClientToScreen で絶対座標に変換した後、
    SetCursorPos + mouse_event でクリックする。
    ゲームが管理者権限で動作している場合、本スクリプトも管理者権限で実行する必要がある。
    """

    def __init__(self) -> None:
        self._hwnd: int | None = None
        self._settle_wait: float = 0.2

    def set_hwnd(self, hwnd: int) -> None:
        """ウィンドウハンドルを設定する."""
        self._hwnd = hwnd

    def set_settle_wait(self, seconds: float) -> None:
        """クリック後のアニメーション収束待ち時間を設定する."""
        self._settle_wait = seconds

    def click(self, client_x: int, client_y: int) -> bool:
        """ウィンドウクライアント座標をクリックする.

        Args:
            client_x: クライアント座標 X。
            client_y: クライアント座標 Y。

        Returns:
            hwnd が設定されていれば True、未設定なら False。

        """
        if self._hwnd is None:
            logger.warning("クリック失敗: hwnd が未設定です")
            return False

        screen_x, screen_y = win32gui.ClientToScreen(self._hwnd, (client_x, client_y))

        try:
            win32gui.SetForegroundWindow(self._hwnd)
            time.sleep(0.15)
        except Exception:
            logger.debug("SetForegroundWindow に失敗しました（続行）")

        win32api.SetCursorPos((screen_x, screen_y))
        time.sleep(0.05)
        win32api.mouse_event(MOUSEEVENTF_LEFTDOWN, screen_x, screen_y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(MOUSEEVENTF_LEFTUP, screen_x, screen_y, 0, 0)

        logger.debug(
            "クリック: client=(%d,%d) screen=(%d,%d)", client_x, client_y, screen_x, screen_y
        )

        if self._settle_wait > 0:
            time.sleep(self._settle_wait)

        return True

    def click_center(self, roi: tuple[int, int, int, int]) -> bool:
        """ROI の中心付近をクリックする.

        中心座標から ±1px の範囲でランダムオフセットを加えてクリックする。

        Args:
            roi: (x, y, w, h) のクライアント座標 ROI。

        Returns:
            click() の戻り値。

        """
        x, y, w, h = roi
        cx = x + w // 2 + random.randint(-1, 1)
        cy = y + h // 2 + random.randint(-1, 1)
        return self.click(cx, cy)

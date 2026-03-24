"""ゲーム画面キャプチャモジュール (Windows / win32gui + PIL.ImageGrab)."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import numpy.typing as npt

logger = logging.getLogger(__name__)

# win32gui は Windows 専用。DevContainer では存在しない。
try:
    import win32gui

    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False
    logger.warning("win32gui が利用できません。キャプチャ機能は Windows 専用です。")

try:
    from PIL import ImageGrab

    _IMAGEGRAB_AVAILABLE = True
except ImportError:
    _IMAGEGRAB_AVAILABLE = False


class WindowNotFoundError(Exception):
    """ゲームウィンドウが見つからない場合の例外."""


class ScreenCapture:
    """win32gui + PIL.ImageGrab を使ったゲーム画面キャプチャ.

    GPU レンダリングゲームでは PrintWindow が動作しないため、
    SetForegroundWindow でウィンドウを前面に出してから ImageGrab でキャプチャする。

    DevContainer (Linux) では利用不可。Windows 実行時のみ動作する。
    """

    def __init__(self, window_title: str) -> None:
        self._window_title = window_title
        self._hwnd: int | None = None

    @property
    def hwnd(self) -> int | None:
        """キャッシュ済みウィンドウハンドルを返す."""
        return self._hwnd

    def find_window(self) -> bool:
        """ゲームウィンドウを探して HWND を取得する.

        Returns:
            ウィンドウが見つかった場合 True。

        """
        if not _WIN32_AVAILABLE:
            return False

        hwnd = win32gui.FindWindow(None, self._window_title)
        if hwnd == 0:
            self._hwnd = None
            return False
        self._hwnd = hwnd
        return True

    def is_window_alive(self) -> bool:
        """ウィンドウが有効か確認する."""
        if not _WIN32_AVAILABLE or self._hwnd is None:
            return False
        return bool(win32gui.IsWindow(self._hwnd))

    def capture(self, bring_to_front: bool = True) -> npt.NDArray[np.uint8] | None:
        """ゲームウィンドウのクライアント領域をキャプチャして numpy 配列で返す.

        Args:
            bring_to_front: True の場合、キャプチャ前にゲームウィンドウを前面に出す。
                自動化実行中は True、GUI プレビューなど非介入時は False を渡すこと。

        Returns:
            BGR 形式の numpy 配列 (H, W, 3)。失敗した場合は None。

        """
        if not _WIN32_AVAILABLE or not _IMAGEGRAB_AVAILABLE:
            return None

        if (self._hwnd is None or not self.is_window_alive()) and not self.find_window():
            return None

        hwnd = self._hwnd
        assert hwnd is not None  # noqa: S101

        try:
            if bring_to_front:
                # 最小化されていると GetClientRect が 0x0 を返すため先にリストア・前面化する
                if win32gui.IsIconic(hwnd):
                    win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
                    time.sleep(0.3)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)

            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                logger.warning("クライアント領域のサイズが不正です: %dx%d", width, height)
                return None
            left_s, top_s = win32gui.ClientToScreen(hwnd, (0, 0))
            pil_img = ImageGrab.grab(
                bbox=(left_s, top_s, left_s + width, top_s + height), all_screens=True
            )
            # ImageGrab は RGB 順で返す。OpenCV は BGR を期待するため反転する。
            img_rgb = np.array(pil_img)
            return img_rgb[:, :, ::-1].copy()

        except Exception:
            logger.exception("画面キャプチャに失敗しました")
            self._hwnd = None
            return None

    def get_window_position(self) -> tuple[int, int] | None:
        """ウィンドウのクライアント領域の画面座標 (left, top) を返す.

        クリック操作の絶対座標算出に使用する。

        Returns:
            (x, y) のタプル。取得できない場合は None。

        """
        if not _WIN32_AVAILABLE or self._hwnd is None:
            return None
        try:
            point = win32gui.ClientToScreen(self._hwnd, (0, 0))
            return (point[0], point[1])
        except Exception:
            logger.exception("ウィンドウ座標の取得に失敗しました")
            return None

    @staticmethod
    def is_process_running(process_name: str) -> bool:
        """指定プロセス名が実行中かどうかを確認する.

        Args:
            process_name: 確認するプロセス名 (例: "PrincessConnectReDive.exe")

        Returns:
            実行中の場合 True。

        """
        if not _WIN32_AVAILABLE:
            return False
        try:
            import psutil

            return any(proc.info["name"] == process_name for proc in psutil.process_iter(["name"]))
        except ImportError:
            # psutil がない場合は EnumWindows で代用
            found = [False]

            def callback(hwnd: int, _: object) -> bool:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if process_name.replace(".exe", "") in title:
                        found[0] = True
                return True

            win32gui.EnumWindows(callback, None)
            return found[0]
        except Exception:
            logger.exception("プロセス確認に失敗しました")
            return False

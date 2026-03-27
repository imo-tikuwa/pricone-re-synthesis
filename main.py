"""究極錬成ツール エントリーポイント."""

from __future__ import annotations

import argparse
import ctypes
import logging
import sys

# DPI 仮想化を無効にする（これがないと SetCursorPos 等の座標が物理ピクセルと一致しない）
if sys.platform == "win32":
    ctypes.windll.user32.SetProcessDPIAware()

from PyQt6.QtWidgets import QApplication, QMessageBox

from src.core.capture import ScreenCapture
from src.core.constants import WINDOW_TITLE, State

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="プリンセスコネクト Re:Dive 究極錬成自動化ツール")
    parser.add_argument(
        "--state",
        type=str,
        default=None,
        metavar="STATE_ID",
        help=(
            "ステートマシンの開始状態を指定します（開発・デバッグ用）。"
            f"有効な値: {', '.join(s.value for s in State)}"
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="デバッグモードを有効にします（キャプチャ画像に ROI オーバーレイを表示）。",
    )
    return parser.parse_args()


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    args = _parse_args()
    _setup_logging(args.debug)

    app = QApplication(sys.argv)
    app.setApplicationName("究極錬成ツール")
    app.setOrganizationName("pricone-re-synthesis")

    # 管理者権限チェック（ゲームが管理者権限で動作しているため必須）
    if sys.platform == "win32" and not ctypes.windll.shell32.IsUserAnAdmin():
        QMessageBox.critical(
            None,
            "起動エラー",
            "管理者権限で実行してください。\n"
            "コマンドプロンプトを「管理者として実行」してから再起動してください。",
        )
        return 1

    # --state オプションのバリデーション
    initial_state: State | None = None
    if args.state is not None:
        try:
            initial_state = State(args.state)
        except ValueError:
            QMessageBox.critical(
                None,
                "起動エラー",
                f"不正な --state 値: {args.state}\n有効な値: {', '.join(s.value for s in State)}",
            )
            return 1

    # ゲームプロセス確認（--state 指定時は警告のみ）
    capture = ScreenCapture(WINDOW_TITLE)
    if not capture.find_window():
        if initial_state is not None:
            # デバッグ・開発用途: ゲーム未起動でも起動を許可
            logger.warning(
                "ゲームウィンドウが見つかりません。"
                "--state モードで起動します（クリック操作は無効）。"
            )
        else:
            QMessageBox.critical(
                None,
                "起動エラー",
                f"ゲームウィンドウ「{WINDOW_TITLE}」が見つかりません。\n"
                "ゲームを起動して究極錬成画面を開いてから再試行してください。",
            )
            return 1

    # テンプレート NPZ 存在確認
    from src.core.matcher import _templates_dir

    npz_path = _templates_dir() / "templates.npz"
    if not npz_path.exists():
        QMessageBox.critical(
            None,
            "起動エラー",
            "テンプレートファイルが見つかりません。\n\n"
            "以下のコマンドを実行してから再起動してください:\n"
            "  python tools/build_templates.py",
        )
        return 1

    # メインウィンドウ表示
    from src.gui.main_window import MainWindow

    window = MainWindow(debug=args.debug, initial_state=initial_state)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

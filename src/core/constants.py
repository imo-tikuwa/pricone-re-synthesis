"""定数定義: ウィンドウ情報・状態名など."""

from enum import StrEnum

# ゲームウィンドウ
WINDOW_TITLE = "PrincessConnectReDive"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# タイムアウト設定（秒）
TIMEOUT_WAITING_FOR_RESULT = 30  # WAITING_FOR_RESULT → ERROR_TIMEOUT
TIMEOUT_CHECKING_SCREEN = 10  # CHECKING_SCREEN → ERROR_WRONG_SCREEN
TIMEOUT_S1A_CONFIRM = 15  # S1A_CONFIRM → ERROR_TIMEOUT（モーダル未出現）
TIMEOUT_BUTTON_DETECT = 10  # ボタン・モーダル検出待ち共通タイムアウト

# ポーリング間隔（秒）
POLL_INTERVAL_DEFAULT = 1.0  # WAITING_FOR_RESULT でのポーリング間隔

# WAITING_FOR_RESULT 中の安全クリック間隔（秒）
SAFE_CLICK_INTERVAL = 1.0

# 結果確定後、S2b モーダルまたは S1 を待つタイムアウト（秒）
TIMEOUT_CONFIRMING_RESULT = 15

# WAITING_FOR_RESULT に入った直後の S2 検出抑制時間（秒）
# OK クリック後に前回の S2 画面が残っていても誤検出しないよう待つ
RESULT_SCREEN_MIN_WAIT = 1.5

# クリック後のリップルアニメーション収束待ち（秒）
CLICK_SETTLE_WAIT = 0.2

# ロックアイコンクリック後の状態確認リトライ上限
LOCK_RETRY_MAX = 3

# テンプレートマッチング閾値
TM_THRESHOLD_DEFAULT = 0.85
TM_THRESHOLD_S2_RESULT = 0.70  # 錬成結果テキスト（背後アニメーションあり）
TM_THRESHOLD_BUTTON = 0.80

# WAITING_FOR_RESULT 中の安全クリック座標（画面左端・上下中央）
SAFE_CLICK_COORDS: tuple[int, int] = (20, 360)

# ROI ― (x, y, w, h) のクライアント座標。座標の根拠は config/roi.json を参照。
S1_SUBSTAT_ROIS: list[tuple[int, int, int, int]] = [
    (44, 315, 245, 30),
    (300, 315, 245, 30),
    (44, 352, 245, 30),
    (300, 352, 245, 30),
]
# ロックアイコンはスロット左上から (119, 5) の位置に 22×22 で固定
S1_SUBSTAT_LOCK_ROIS: list[tuple[int, int, int, int]] = [
    (r[0] + 119, r[1] + 5, 22, 22) for r in S1_SUBSTAT_ROIS
]
S1_SUBSTAT_NAME_ROIS: list[tuple[int, int, int, int]] = [
    (45, 318, 115, 24),
    (301, 318, 115, 24),
    (45, 355, 115, 24),
    (301, 355, 115, 24),
]
S1_SUBSTAT_VALUE_ROIS: list[tuple[int, int, int, int]] = [
    (220, 318, 67, 24),
    (476, 318, 67, 24),
    (220, 355, 67, 24),
    (476, 355, 67, 24),
]
S2_SUBSTAT_ROIS: list[tuple[int, int, int, int]] = [
    (711, 520, 241, 22),
    (965, 520, 241, 22),
    (711, 556, 241, 22),
    (965, 556, 241, 22),
]
S2_SUBSTAT_NAME_ROIS: list[tuple[int, int, int, int]] = [
    (r[0] + 1, r[1] + 1, 135, r[3] - 2) for r in S2_SUBSTAT_ROIS
]
# ロックアイコン検出専用 ROI: 行全体ではなく左端 30px のみ対象にする
# （行全体を使うと背景・ハイライトの青ピクセルに負けて誤検出になるため）
S2_LOCK_ICON_ROIS: list[tuple[int, int, int, int]] = [
    (r[0], r[1], 30, r[3]) for r in S2_SUBSTAT_ROIS
]
S2_SUBSTAT_VALUE_ROIS: list[tuple[int, int, int, int]] = [
    (r[0] + 175, r[1] + 1, 67, 24)
    for r in S2_SUBSTAT_ROIS  # S1 テンプレートに合わせた固定サイズ
]

S1_EQUIPMENT_NAME_ROI: tuple[int, int, int, int] = (145, 105, 330, 30)
S1_EQUIPMENT_CHARM_NAME_ROI: tuple[int, int, int, int] = (237, 107, 234, 25)
S1_EQUIPMENT_ELEMENT_ROI: tuple[int, int, int, int] = (191, 108, 23, 23)
S1_EQUIPMENT_LIST_ROI: tuple[int, int, int, int] = (557, 191, 636, 241)

S1_ULTIMATE_LABEL_ROI: tuple[int, int, int, int] = (81, 10, 140, 60)
S2_RESULT_LABEL_ROI: tuple[int, int, int, int] = (503, 35, 263, 65)

S1A_MODAL_TITLE_ROI: tuple[int, int, int, int] = (529, 99, 224, 33)
S2A_MODAL_TEXT_ROI: tuple[int, int, int, int] = (471, 179, 326, 26)
S2B_MODAL_TITLE_ROI: tuple[int, int, int, int] = (529, 40, 224, 33)

MANA_ROI: tuple[int, int, int, int] = (870, 496, 160, 24)
EX_PT_ROI: tuple[int, int, int, int] = (870, 460, 160, 24)
MANA_AFTER_ROI: tuple[int, int, int, int] = (1085, 496, 160, 24)
EX_PT_AFTER_ROI: tuple[int, int, int, int] = (1085, 460, 160, 24)

S1_BTN_SYNTHESIZE_ROI: tuple[int, int, int, int] = (920, 543, 214, 60)
S1A_BTN_OK_ROI: tuple[int, int, int, int] = (754, 558, 70, 34)
S1A_BTN_CANCEL_ROI: tuple[int, int, int, int] = (421, 558, 150, 34)
S2A_BTN_OK_ROI: tuple[int, int, int, int] = (754, 558, 70, 34)
S2B_BTN_OK_ROI: tuple[int, int, int, int] = (754, 620, 70, 34)
S2_BTN_CONFIRM_ROI: tuple[int, int, int, int] = (1080, 637, 102, 31)
S2_BTN_RESYNTH_ROI: tuple[int, int, int, int] = (896, 637, 87, 31)
S2_BTN_DISCARD_ROI: tuple[int, int, int, int] = (762, 637, 57, 35)


# 特殊武器 ID（pen スケールが 1〜5 に拡張されている）
WEAPON_SPECIAL_IDS: frozenset[str] = frozenset({"W1001", "W1002", "W1003"})

# サブステータス効果名 → テンプレートフォルダのスケール名
STAT_TO_SCALE: dict[str, str] = {
    "hp": "hpdef",
    "phys_def": "hpdef",
    "mag_def": "hpdef",
    "phys_atk": "atkcrit",
    "mag_atk": "atkcrit",
    "phys_crit": "atkcrit",
    "mag_crit": "atkcrit",
    "phys_pen": "pen",
    "mag_pen": "pen",
    "tp_up": "tp",
}


class State(StrEnum):
    """ステートマシンの状態."""

    IDLE = "IDLE"
    CHECKING_SCREEN = "CHECKING_SCREEN"
    S1_EQUIP_SELECT = "S1_EQUIP_SELECT"
    APPLYING_LOCKS = "APPLYING_LOCKS"
    CHECKING_RESOURCES = "CHECKING_RESOURCES"
    CLICKING_SYNTHESIZE = "CLICKING_SYNTHESIZE"
    S1A_CONFIRM = "S1A_CONFIRM"
    CLICKING_OK = "CLICKING_OK"
    WAITING_FOR_RESULT = "WAITING_FOR_RESULT"
    S2_RESULT = "S2_RESULT"
    EVALUATING_RESULT = "EVALUATING_RESULT"
    GOAL_ACHIEVED = "GOAL_ACHIEVED"
    CLICKING_CONFIRM = "CLICKING_CONFIRM"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    CLICKING_CONFIRM_PARTIAL = "CLICKING_CONFIRM_PARTIAL"
    NO_MATCH = "NO_MATCH"
    CLICKING_RESYNTH = "CLICKING_RESYNTH"
    S2A_CONFIRM = "S2A_CONFIRM"
    CLICKING_OK_RESYNTH = "CLICKING_OK_RESYNTH"
    CONFIRMING_RESULT = "CONFIRMING_RESULT"
    S2B_CONFIRM = "S2B_CONFIRM"
    COMPLETED = "COMPLETED"
    ERROR_WRONG_SCREEN = "ERROR_WRONG_SCREEN"
    ERROR_INSUFFICIENT = "ERROR_INSUFFICIENT"
    ERROR_TIMEOUT = "ERROR_TIMEOUT"


# 状態の表示名（GUI ステータスバー用）
STATE_DISPLAY_NAMES: dict[str, str] = {
    State.IDLE: "待機中",
    State.CHECKING_SCREEN: "画面確認中",
    State.S1_EQUIP_SELECT: "装備選択画面",
    State.APPLYING_LOCKS: "ロック適用中",
    State.CHECKING_RESOURCES: "リソース確認中",
    State.CLICKING_SYNTHESIZE: "錬成ボタンクリック中",
    State.S1A_CONFIRM: "錬成確認（初回）",
    State.CLICKING_OK: "OK クリック中",
    State.WAITING_FOR_RESULT: "結果待機中",
    State.S2_RESULT: "錬成結果画面",
    State.EVALUATING_RESULT: "結果評価中",
    State.GOAL_ACHIEVED: "目標達成",
    State.CLICKING_CONFIRM: "結果確定クリック中",
    State.PARTIAL_MATCH: "部分一致",
    State.CLICKING_CONFIRM_PARTIAL: "結果確定クリック中（部分）",
    State.NO_MATCH: "一致なし",
    State.CLICKING_RESYNTH: "再錬成クリック中",
    State.S2A_CONFIRM: "錬成確認（再錬成）",
    State.CLICKING_OK_RESYNTH: "OK クリック中（再錬成）",
    State.CONFIRMING_RESULT: "結果反映確認中",
    State.S2B_CONFIRM: "錬成結果反映確認（S2b）",
    State.COMPLETED: "完了",
    State.ERROR_WRONG_SCREEN: "エラー: 画面外",
    State.ERROR_INSUFFICIENT: "エラー: リソース不足",
    State.ERROR_TIMEOUT: "エラー: タイムアウト",
}

# コスト表 (錬成枠数) → (マナ消費, EX錬成Pt消費)
COST_TABLE: dict[int, tuple[int, int]] = {
    4: (100_000, 10_000),
    3: (200_000, 20_000),
    2: (300_000, 30_000),
    1: (400_000, 40_000),
}

# ステータス表示名（GUI 用）
STAT_DISPLAY_NAMES: dict[str, str] = {
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

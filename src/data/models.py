"""データモデル定義."""

from dataclasses import dataclass, field
from enum import StrEnum


class EquipmentType(StrEnum):
    """装備種類. ID プレフィックス W / A / C に対応."""

    WEAPON = "weapon"
    ARMOR = "armor"
    CHARM = "charm"  # アクセサリー（C = Charm）


class StatType(StrEnum):
    """サブステータス効果種類.

    値は内部 ID（英語）。GUI 表示名は STAT_DISPLAY_NAMES（constants.py）を参照。
    """

    HP = "hp"  # HP上昇
    PHYS_ATK = "phys_atk"  # 物理攻撃力上昇
    MAG_ATK = "mag_atk"  # 魔法攻撃力上昇
    PHYS_DEF = "phys_def"  # 物理防御力上昇
    MAG_DEF = "mag_def"  # 魔法防御力上昇
    PHYS_CRIT = "phys_crit"  # 物理クリティカル
    MAG_CRIT = "mag_crit"  # 魔法クリティカル
    PHYS_PEN = "phys_pen"  # 物理防御貫通
    MAG_PEN = "mag_pen"  # 魔法防御貫通
    TP_UP = "tp_up"  # TP上昇（アクセサリーのみ）


@dataclass
class StatPoolEntry:
    """装備の抽選対象ステータスと発現しうる実値リスト.

    values はゲーム画面に表示される文字列を昇順で格納する。
    例: HP（武器）→ ["0.5%", "1%", "1.5%", "2%", "2.5%"]
        phys_pen（通常武器）→ ["1", "2", "3"]
        mag_pen（ヴィズ・ラ・リュンヌ）→ ["1", "2", "3", "4", "5"]
    """

    stat: str
    values: list[str]


@dataclass
class EquipmentData:
    """装備データ."""

    id: str
    display_name: str  # GUI 表示名（属性込みのフルネーム）
    # 属性アクセサリーは属性文字を除く部分のテンプレート（2段階マッチング用）
    template: str  # テンプレート画像パス
    type: EquipmentType  # 装備種類
    stat_pool: list[StatPoolEntry]
    element: str | None = None  # "fire"/"water"/"wind"/"light"/"dark"（属性アクセサリーのみ）

    def get_stat_pool_stats(self) -> list[str]:
        """抽選対象ステータスの種類一覧を返す."""
        return [e.stat for e in self.stat_pool]

    def get_stat_pool_entry(self, stat: str) -> StatPoolEntry | None:
        """指定ステータスの StatPoolEntry を返す."""
        return next((e for e in self.stat_pool if e.stat == stat), None)


@dataclass
class SubstatSlot:
    """サブステータス 1 枠分の情報."""

    slot_index: int  # 0〜3
    stat: str | None = None  # None = 錬成されていません
    value: str | None = None  # 画面表示値（例: "1.5%", "3"）
    is_locked: bool = False

    @property
    def is_synthesized(self) -> bool:
        """錬成済みかどうか."""
        return self.stat is not None and self.value is not None


@dataclass
class GoalCondition:
    """自動錬成の完了条件."""

    target_stat: str
    min_value: str  # 最低限必要な画面表示値（例: "1.5%", "3"）
    required_slots: int  # 何枠以上で完了とするか
    min_ex_pt: int = 0  # EX錬成Pt 残量下限（0 = 制限なし）


class EvalResult(StrEnum):
    """錬成結果の評価."""

    GOAL_ACHIEVED = "GOAL_ACHIEVED"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NO_MATCH = "NO_MATCH"


@dataclass
class DetectionResult:
    """1 フレームのテンプレートマッチング検出結果."""

    screen_id: str | None  # "S1" / "S1a" / "S2" / "S2a" / None
    equipment_id: str | None  # 検出した装備 ID (S1 のみ)
    substats: list[SubstatSlot] = field(default_factory=list)  # 4 枠分
    mana: int | None = None
    ex_pt: int | None = None
    confidence: dict[str, float] = field(default_factory=dict)  # template_id → score

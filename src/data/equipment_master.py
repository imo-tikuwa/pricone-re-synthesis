"""装備マスターデータ.

究極錬成対象装備の一覧を Python 定数として管理する。
新装備追加時はこのファイルに EquipmentData エントリを追記する。

■ ID 体系
  W####  : EX★5 武器（通常）   W0001〜W0011
  W1###  : EX★5 特殊武器        W1001〜W1002
  A####  : EX★5 防具            A0001〜A0004
  C####  : EX★5 属性アクセサリー C0001〜C0010
           （各 5 属性 → id サフィックス: _fire/_water/_wind/_light/_dark）
  C1###  : EX★5 特殊アクセサリー C1001〜C1005（属性なし）

  プレフィックス凡例: W = Weapon / A = Armor / C = Charm（装身具の英語総称）

■ template パス
  templates/equipment/<type>/<id>.png
  属性アクセサリー（C0001〜C0010）: カタカナ名部分のみのテンプレート。
    キャプチャ ROI: s1_equipment_charm_name（「黎明{属性}{種別}」4文字後〜）
    5属性で同一テンプレートを参照（element フィールドで区別）。
  武器・防具・特殊アクセサリー: 装備名全体のテンプレート。
    キャプチャ ROI: s1_equipment_name
  属性文字（火/水/風/光/闇）のテンプレートは templates/equipment/element/<element>.png で共通管理。
    キャプチャ ROI: s1_equipment_element

■ StatPoolEntry.values
  ゲーム画面に表示される文字列を昇順で格納する。
  "-"（抽選対象外）は含めない。
  出典: docs/equipments_abilities.md
"""

from src.data.models import EquipmentData, EquipmentType, StatPoolEntry

# ===========================================================================
# 共通値リスト定数
# ===========================================================================

# 武器・アクセサリーで共通の値ステップ
_W_HP = ["0.5%", "1%", "1.5%", "2%", "2.5%"]
_W_ATK = ["0.8%", "1.6%", "2.4%", "3.2%", "4%"]
_W_DEF = ["0.5%", "1%", "1.5%", "2%", "2.5%"]
_W_CRIT = ["0.8%", "1.6%", "2.4%", "3.2%", "4%"]
_PEN_STD = ["1", "2", "3"]  # 通常の防御貫通（Lv3〜5 相当）
_PEN_EXT = ["1", "2", "3", "4", "5"]  # 拡張防御貫通（ヴィズ・ラ・リュンヌ / オーバー・ザ・ムーン）

# 防具固有の値ステップ
_A_HP = ["1%", "2%", "3%", "4%", "5%"]
_A_ATK = ["0.5%", "1%", "1.5%", "2%", "2.5%"]
_A_DEF = ["1%", "2%", "3%", "4%", "5%"]
_A_CRIT = ["0.5%", "1%", "1.5%", "2%", "2.5%"]

# アクセサリー固有の値ステップ
_C_HP = ["0.25%", "0.5%", "0.75%", "1%", "1.25%"]
_C_ATK = ["0.4%", "0.8%", "1.2%", "1.6%", "2%"]
_C_DEF = ["0.25%", "0.5%", "0.75%", "1%", "1.25%"]
_C_CRIT = ["0.4%", "0.8%", "1.2%", "1.6%", "2%"]
_TP_UP = ["1", "2", "3"]  # TP上昇（Lv3〜5 相当）

# ===========================================================================
# 武器 stat_pool
# ===========================================================================

# 物理系武器（W0001, W0003〜W0009, W0011 の 9 種）
# phys_atk 主体、phys_pen（最大値=3）
_POOL_WEAPON_PHYS: list[StatPoolEntry] = [
    StatPoolEntry("hp", _W_HP),
    StatPoolEntry("phys_atk", _W_ATK),
    StatPoolEntry("phys_def", _W_DEF),
    StatPoolEntry("mag_def", _W_DEF),
    StatPoolEntry("phys_crit", _W_CRIT),
    StatPoolEntry("phys_pen", _PEN_STD),
]

# 魔法系武器（W0002 アメノミハシラ, W0010 フルコトフミ の 2 種）
# mag_atk 主体、mag_pen（最大値=3）
_POOL_WEAPON_MAG: list[StatPoolEntry] = [
    StatPoolEntry("hp", _W_HP),
    StatPoolEntry("phys_def", _W_DEF),
    StatPoolEntry("mag_atk", _W_ATK),
    StatPoolEntry("mag_def", _W_DEF),
    StatPoolEntry("mag_crit", _W_CRIT),
    StatPoolEntry("mag_pen", _PEN_STD),
]

# W1001 ヴィズ・ラ・リュンヌ: mag_pen が Lv1〜5 全て抽選対象（通常武器は Lv3〜5 のみ）
_POOL_W1001: list[StatPoolEntry] = [
    StatPoolEntry("hp", _W_HP),
    StatPoolEntry("phys_def", _W_DEF),
    StatPoolEntry("mag_atk", _W_ATK),
    StatPoolEntry("mag_def", _W_DEF),
    StatPoolEntry("mag_crit", _W_CRIT),
    StatPoolEntry("mag_pen", _PEN_EXT),
]

# W1002 オーバー・ザ・ムーン: phys_pen が Lv1〜5 全て抽選対象（通常武器は Lv3〜5 のみ）
_POOL_W1002: list[StatPoolEntry] = [
    StatPoolEntry("hp", _W_HP),
    StatPoolEntry("phys_atk", _W_ATK),
    StatPoolEntry("phys_def", _W_DEF),
    StatPoolEntry("mag_def", _W_DEF),
    StatPoolEntry("phys_crit", _W_CRIT),
    StatPoolEntry("phys_pen", _PEN_EXT),
]

# ===========================================================================
# 防具 stat_pool
# ===========================================================================

# 物理系防具（A0001 エリュシオン, A0002 カリスティア）
_POOL_ARMOR_PHYS: list[StatPoolEntry] = [
    StatPoolEntry("hp", _A_HP),
    StatPoolEntry("phys_atk", _A_ATK),
    StatPoolEntry("phys_def", _A_DEF),
    StatPoolEntry("mag_def", _A_DEF),
    StatPoolEntry("phys_crit", _A_CRIT),
    StatPoolEntry("phys_pen", _PEN_STD),
]

# 魔法系防具（A0003 セレスティア, A0004 アイオニオス）
_POOL_ARMOR_MAG: list[StatPoolEntry] = [
    StatPoolEntry("hp", _A_HP),
    StatPoolEntry("phys_def", _A_DEF),
    StatPoolEntry("mag_atk", _A_ATK),
    StatPoolEntry("mag_def", _A_DEF),
    StatPoolEntry("mag_crit", _A_CRIT),
    StatPoolEntry("mag_pen", _PEN_STD),
]

# ===========================================================================
# アクセサリー stat_pool
#
# 分類は 攻撃寄り/防御寄り ではなく 装備種別（輪/環/装 vs 玉/飾）で決まる:
#   輪/環/装 → 物理攻撃系 (phys_atk + phys_crit)
#   玉/飾   → 魔法攻撃系 (mag_atk + mag_crit)
# ===========================================================================

# 輪/環/装 タイプ（C0001〜C0003, C0006〜C0008 および 魔蜘ノ煌輪/縁環/艷装）
_POOL_CHARM_PHYS: list[StatPoolEntry] = [
    StatPoolEntry("hp", _C_HP),
    StatPoolEntry("phys_atk", _C_ATK),
    StatPoolEntry("phys_def", _C_DEF),
    StatPoolEntry("mag_def", _C_DEF),
    StatPoolEntry("phys_crit", _C_CRIT),
]

# 玉/飾 タイプ（C0004〜C0005, C0009〜C0010 および 魔蜘ノ玲玉/絢飾）
_POOL_CHARM_MAG: list[StatPoolEntry] = [
    StatPoolEntry("hp", _C_HP),
    StatPoolEntry("phys_def", _C_DEF),
    StatPoolEntry("mag_atk", _C_ATK),
    StatPoolEntry("mag_def", _C_DEF),
    StatPoolEntry("mag_crit", _C_CRIT),
]

# 魔蜘ノ系: 上記プールに tp_up を追加
_POOL_MAJIGUMO_PHYS: list[StatPoolEntry] = [
    *_POOL_CHARM_PHYS,
    StatPoolEntry("tp_up", _TP_UP),
]

_POOL_MAJIGUMO_MAG: list[StatPoolEntry] = [
    *_POOL_CHARM_MAG,
    StatPoolEntry("tp_up", _TP_UP),
]

# ===========================================================================
# 属性チャームのバリアント生成ヘルパー
# ===========================================================================

_ELEMENTS: list[tuple[str, str]] = [
    ("fire", "火"),
    ("water", "水"),
    ("wind", "風"),
    ("light", "光"),
    ("dark", "闇"),
]


def _make_element_charms(
    base_id: str,
    name_suffix: str,
    stat_pool: list[StatPoolEntry],
) -> list[EquipmentData]:
    """5 属性分の EquipmentData リストを生成する.

    Args:
        base_id: 属性サフィックスなしのベース ID（例: "C0001"）。
        name_suffix: 属性文字の後に続く装備名部分（例: "輪アルファプレイズ"）。
                     display_name は "黎明{属性漢字}{name_suffix}" となる。
        stat_pool: この装備グループの抽選対象ステータスリスト。

    """
    return [
        EquipmentData(
            id=f"{base_id}_{elem_key}",
            display_name=f"黎明{elem_kanji}{name_suffix}",
            template=f"equipment/charm/{base_id}.png",  # 5 属性で共通テンプレートを参照
            type=EquipmentType.CHARM,
            stat_pool=stat_pool,
            element=elem_key,
        )
        for elem_key, elem_kanji in _ELEMENTS
    ]


# ===========================================================================
# マスターデータ本体
# ===========================================================================

EQUIPMENT_MASTER: list[EquipmentData] = [
    # =========================================================================
    # EX★5 武器（通常）  W0001〜W0011
    # 物理系 (phys_pen): W0001, W0003〜W0009, W0011（9 種）
    # 魔法系 (mag_pen):  W0002, W0010（2 種）
    # =========================================================================
    EquipmentData(
        id="W0001",
        display_name="アルベドの剣",
        template="equipment/weapon/W0001.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_PHYS,
    ),
    EquipmentData(
        id="W0002",
        display_name="覇瞳神杖アメノミハシラ",
        template="equipment/weapon/W0002.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_MAG,
    ),
    EquipmentData(
        id="W0003",
        display_name="残燭の刃リジル・レギオン",
        template="equipment/weapon/W0003.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_PHYS,
    ),
    EquipmentData(
        id="W0004",
        display_name="残懐の大剣ブラウ・イデア",
        template="equipment/weapon/W0004.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_PHYS,
    ),
    EquipmentData(
        id="W0005",
        display_name="覇瞳霊刃フツノミタマ",
        template="equipment/weapon/W0005.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_PHYS,
    ),
    EquipmentData(
        id="W0006",
        display_name="覇瞳神槍アメノヌボコ",
        template="equipment/weapon/W0006.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_PHYS,
    ),
    EquipmentData(
        id="W0007",
        display_name="残壊の斧シュライエン",
        template="equipment/weapon/W0007.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_PHYS,
    ),
    EquipmentData(
        id="W0008",
        display_name="残炎の拳フォイアドラッヘ",
        template="equipment/weapon/W0008.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_PHYS,
    ),
    EquipmentData(
        id="W0009",
        display_name="残痕の盾アブソリュート",
        template="equipment/weapon/W0009.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_PHYS,
    ),
    EquipmentData(
        id="W0010",
        display_name="覇瞳神言フルコトフミ",
        template="equipment/weapon/W0010.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_MAG,
    ),
    EquipmentData(
        id="W0011",
        display_name="覇瞳神弓アメノマカコユミ",
        template="equipment/weapon/W0011.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_WEAPON_PHYS,
    ),
    # =========================================================================
    # EX★5 特殊武器  W1001〜W1002
    # W1001: mag_pen が全レベル抽選対象（値 1〜5）
    # W1002: phys_pen が全レベル抽選対象（値 1〜5）
    # =========================================================================
    EquipmentData(
        id="W1001",
        display_name="ヴィズ・ラ・リュンヌ",
        template="equipment/weapon/W1001.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_W1001,
    ),
    EquipmentData(
        id="W1002",
        display_name="オーバー・ザ・ムーン",
        template="equipment/weapon/W1002.png",
        type=EquipmentType.WEAPON,
        stat_pool=_POOL_W1002,
    ),
    # =========================================================================
    # EX★5 防具  A0001〜A0004
    # A0001〜A0002: 物理系 (phys_atk + phys_pen)
    # A0003〜A0004: 魔法系 (mag_atk + mag_pen)
    # =========================================================================
    EquipmentData(
        id="A0001",
        display_name="薔薇織衣エリュシオン",
        template="equipment/armor/A0001.png",
        type=EquipmentType.ARMOR,
        stat_pool=_POOL_ARMOR_PHYS,
    ),
    EquipmentData(
        id="A0002",
        display_name="薔薇彩鎧カリスティア",
        template="equipment/armor/A0002.png",
        type=EquipmentType.ARMOR,
        stat_pool=_POOL_ARMOR_PHYS,
    ),
    EquipmentData(
        id="A0003",
        display_name="薔薇天装セレスティア",
        template="equipment/armor/A0003.png",
        type=EquipmentType.ARMOR,
        stat_pool=_POOL_ARMOR_MAG,
    ),
    EquipmentData(
        id="A0004",
        display_name="薔薇夜装アイオニオス",
        template="equipment/armor/A0004.png",
        type=EquipmentType.ARMOR,
        stat_pool=_POOL_ARMOR_MAG,
    ),
    # =========================================================================
    # EX★5 属性アクセサリー  C0001〜C0010 × 5 属性
    #
    # プール分類は 攻撃寄り/防御寄り ではなく 装備種別で決まる:
    #   輪/環/装（C0001〜C0003, C0006〜C0008）→ 物理攻撃系プール
    #   玉/飾  （C0004〜C0005, C0009〜C0010）→ 魔法攻撃系プール
    # =========================================================================
    # --- 攻撃寄り（C0001〜C0005） ---
    *_make_element_charms("C0001", "輪アルファプレイズ", _POOL_CHARM_PHYS),
    *_make_element_charms("C0002", "環アルファドミナント", _POOL_CHARM_PHYS),
    *_make_element_charms("C0003", "装アルファハイネス", _POOL_CHARM_PHYS),
    *_make_element_charms("C0004", "玉アルファプレシャス", _POOL_CHARM_MAG),
    *_make_element_charms("C0005", "飾アルファグローリー", _POOL_CHARM_MAG),
    # --- 防御寄り（C0006〜C0010） ---
    *_make_element_charms("C0006", "輪アルファストリクト", _POOL_CHARM_PHYS),
    *_make_element_charms("C0007", "環アルファエミネンス", _POOL_CHARM_PHYS),
    *_make_element_charms("C0008", "装アルファアダマント", _POOL_CHARM_PHYS),
    *_make_element_charms("C0009", "玉アルファプライマル", _POOL_CHARM_MAG),
    *_make_element_charms("C0010", "飾アルファトレランス", _POOL_CHARM_MAG),
    # =========================================================================
    # EX★5 特殊アクセサリー（属性なし）  C1001〜C1005
    # 煌輪/縁環/艷装 → 物理系 + tp_up
    # 玲玉/絢飾     → 魔法系 + tp_up
    # =========================================================================
    EquipmentData(
        id="C1001",
        display_name="魔蜘ノ煌輪",
        template="equipment/charm/C1001.png",
        type=EquipmentType.CHARM,
        stat_pool=_POOL_MAJIGUMO_PHYS,
    ),
    EquipmentData(
        id="C1002",
        display_name="魔蜘ノ縁環",
        template="equipment/charm/C1002.png",
        type=EquipmentType.CHARM,
        stat_pool=_POOL_MAJIGUMO_PHYS,
    ),
    EquipmentData(
        id="C1003",
        display_name="魔蜘ノ艷装",
        template="equipment/charm/C1003.png",
        type=EquipmentType.CHARM,
        stat_pool=_POOL_MAJIGUMO_PHYS,
    ),
    EquipmentData(
        id="C1004",
        display_name="魔蜘ノ玲玉",
        template="equipment/charm/C1004.png",
        type=EquipmentType.CHARM,
        stat_pool=_POOL_MAJIGUMO_MAG,
    ),
    EquipmentData(
        id="C1005",
        display_name="魔蜘ノ絢飾",
        template="equipment/charm/C1005.png",
        type=EquipmentType.CHARM,
        stat_pool=_POOL_MAJIGUMO_MAG,
    ),
]

# ---------------------------------------------------------------------------
# ルックアップ用辞書（id → EquipmentData）
# ---------------------------------------------------------------------------

EQUIPMENT_MAP: dict[str, EquipmentData] = {eq.id: eq for eq in EQUIPMENT_MASTER}

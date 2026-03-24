"""装備データローダー.

equipment_master.py の EQUIPMENT_MAP を公開する薄いラッパー。
"""

from src.data.equipment_master import EQUIPMENT_MAP, EQUIPMENT_MASTER
from src.data.models import EquipmentData

__all__ = ["EQUIPMENT_MAP", "EQUIPMENT_MASTER", "load_equipment"]


def load_equipment() -> dict[str, EquipmentData]:
    """装備マスターデータを id → EquipmentData の辞書で返す."""
    return EQUIPMENT_MAP

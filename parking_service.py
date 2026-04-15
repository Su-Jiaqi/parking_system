from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from db_utils import execute, fetch_one
from ocr_utils import OCRError, recognize_plate

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class ParkingError(Exception):
    pass


@dataclass
class ParkingResult:
    success: bool
    plate_number: str | None
    action: str
    message: str
    entry_time: str | None = None
    exit_time: str | None = None
    duration_minutes: int | None = None
    fee: float | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ParkingService:
    def handle_request(self, image_path: str | Path, action: str) -> Dict[str, Any]:
        try:
            plate_number = recognize_plate(image_path)
        except OCRError as exc:
            raise ParkingError(str(exc)) from exc

        if action == "entry":
            result = self._handle_entry(plate_number, image_path)
        else:
            result = self._handle_exit(plate_number, image_path)
        return result.to_dict()

    def _handle_entry(self, plate_number: str, image_path: str | Path) -> ParkingResult:
        active = fetch_one(
            "SELECT * FROM parking_records WHERE plate_number = ? AND status = 'IN' ORDER BY id DESC LIMIT 1",
            (plate_number,),
        )
        if active is not None:
            raise ParkingError(f"车辆 {plate_number} 已在场，不能重复入场")

        now = datetime.now().strftime(TIME_FORMAT)
        execute(
            """
            INSERT INTO parking_records (plate_number, entry_time, exit_time, duration_minutes, fee, status, image_path)
            VALUES (?, ?, NULL, NULL, NULL, 'IN', ?)
            """,
            (plate_number, now, str(image_path)),
        )
        return ParkingResult(
            success=True,
            plate_number=plate_number,
            action="entry",
            message="入场成功",
            entry_time=now,
        )

    def _handle_exit(self, plate_number: str, image_path: str | Path) -> ParkingResult:
        active = fetch_one(
            "SELECT * FROM parking_records WHERE plate_number = ? AND status = 'IN' ORDER BY id DESC LIMIT 1",
            (plate_number,),
        )
        if active is None:
            raise ParkingError(f"车辆 {plate_number} 没有入场记录，不能出场")

        entry_time_str = active["entry_time"]
        if not entry_time_str:
            raise ParkingError("入场记录异常：缺少入场时间")

        entry_time = datetime.strptime(entry_time_str, TIME_FORMAT)
        exit_time = datetime.now()
        duration_minutes = max(1, math.ceil((exit_time - entry_time).total_seconds() / 60))
        fee = self._calculate_fee(duration_minutes)
        exit_time_str = exit_time.strftime(TIME_FORMAT)

        execute(
            """
            UPDATE parking_records
            SET exit_time = ?, duration_minutes = ?, fee = ?, status = 'OUT', image_path = ?
            WHERE id = ?
            """,
            (exit_time_str, duration_minutes, fee, str(image_path), active["id"]),
        )

        return ParkingResult(
            success=True,
            plate_number=plate_number,
            action="exit",
            message="出场成功",
            entry_time=entry_time_str,
            exit_time=exit_time_str,
            duration_minutes=duration_minutes,
            fee=fee,
        )

    @staticmethod
    def _calculate_fee(duration_minutes: int) -> float:
        if duration_minutes <= 30:
            return 0.0
        chargeable_minutes = duration_minutes - 30
        hours = math.ceil(chargeable_minutes / 60)
        return float(hours * 5)

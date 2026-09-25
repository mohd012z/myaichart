from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    display_timezone: str = "Asia/Kuala_Lumpur"
    canonical_timezone: str = "UTC"
    late_tick_grace_seconds: float = 2.0
    frontend_max_fps: int = 10
    symbol: str = "XAUUSD"

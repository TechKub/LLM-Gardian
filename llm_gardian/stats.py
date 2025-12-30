"""
Session statistics tracking for CLI
"""

import time
from dataclasses import dataclass, field


@dataclass
class SessionStats:
    """Track statistics for interactive session"""
    total_checks: int = 0
    safe_count: int = 0
    blocked_count: int = 0
    start_time: float = field(default_factory=time.time)
    risk_levels: dict = field(default_factory=lambda: {"low": 0, "medium": 0, "high": 0, "critical": 0})

    def add_result(self, allowed: bool, risk_level: str):
        """Add a check result to statistics"""
        self.total_checks += 1
        if allowed:
            self.safe_count += 1
        else:
            self.blocked_count += 1
        if risk_level in self.risk_levels:
            self.risk_levels[risk_level] += 1

    @property
    def elapsed_time(self) -> str:
        """Get formatted elapsed time"""
        elapsed = int(time.time() - self.start_time)
        minutes, seconds = divmod(elapsed, 60)
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    @property
    def block_rate(self) -> float:
        """Calculate block rate percentage"""
        if self.total_checks == 0:
            return 0.0
        return self.blocked_count / self.total_checks

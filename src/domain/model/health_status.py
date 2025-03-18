from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class HealthStatus:
    status: Status
    details: dict = None

    def is_healthy(self) -> bool:
        return self.status == Status.OK

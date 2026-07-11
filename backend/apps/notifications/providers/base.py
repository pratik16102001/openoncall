from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResult:
    success: bool
    provider_message_id: str | None = None
    error_message: str | None = None


class NotificationProvider(ABC):
    @abstractmethod
    def send(self, user, incident, message: str) -> ProviderResult:
        ...

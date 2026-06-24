from functools import lru_cache
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "HealthGuard AI"
    app_version: str = "1.0.0"
    safety_disclaimer: str = (
        "This report is educational and not a medical diagnosis. "
        "Please consult a qualified healthcare professional for medical decisions."
    )
    emergency_message: str = (
        "Please seek emergency medical care immediately or contact local emergency services."
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

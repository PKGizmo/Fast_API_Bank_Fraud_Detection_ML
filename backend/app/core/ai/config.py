from pydantic_settings import BaseSettings, SettingsConfigDict


# BaseSettings from pydantic provides automatic environment variable parsing
class AISettings(BaseSettings):
    # If transaction risk score exceeds this value, it's going to be considered high risk
    RISK_SCORE_TRESHOLD: float = 0.7
    MODEL_VERSION: str = "1.0.0"
    ANALYSIS_MODEL_DAYS: int = 90

    # Sum must add to 1.0 (100%)
    RISK_WEIGHTS: dict[str, float] = {
        "amount": 0.3,
        "time": 0.1,
        "frequency": 0.2,
        "pattern": 0.2,
        "velocity": 0.2,
    }

    # Sum must add to 1.0 (100%)
    PATTERN_WEIGHTS: dict[str, float] = {
        "round_amounts": 0.2,
        "repeated_amounts": 0.2,
        "velocity": 0.6,  # Combination of the amount of the transaction and the frequency
    }

    TIME_RISK_WEIGHTS: dict[str, float] = {
        "time_of_day": 0.7,
        "day_of_week": 0.3,
    }

    # If transaction exceeds this amount, it's going to be considered high risk
    HIGH_AMOUNT_THRESHOLD: float = 10000.0

    VELOCITY_THRESHOLD: float = 50000.0

    FREQUENCY_THRESHOLD: int = 5

    HIGH_RISK_SCORE_THRESHOLD: float = 0.7

    # 24 hours format
    BANKING_HOURS_START: int = 9  # 9 AM
    BANKING_HOURS_END: int = 17  # 5 PM
    BANKING_HOURS_RISK: float = 0.1
    # For transactions done in later hours but not very late
    OFF_HOURS_RISK: float = 0.5
    # For transactions done in very late hours
    LATE_HOURS_RISK: float = 0.9

    model_config = SettingsConfigDict(
        env_file="../../.envs/.env.local",
        env_ignore_empty=True,
        extra="ignore",
        env_prefix="AI_",
    )


ai_settings = AISettings()

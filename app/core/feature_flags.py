import os
from typing import Dict
from functools import lru_cache


class FeatureFlags:
    def __init__(self):
        self._flags: Dict[str, bool] = {
            "enable_monitoring": os.getenv("FF_ENABLE_MONITORING", "true").lower() == "true",
            "enable_ab_testing": os.getenv("FF_ENABLE_AB_TESTING", "true").lower() == "true",
            "enable_notifications": os.getenv("FF_ENABLE_NOTIFICATIONS", "true").lower() == "true",
            "enable_api_keys": os.getenv("FF_ENABLE_API_KEYS", "true").lower() == "true",
            "enable_batch_predictions": os.getenv("FF_ENABLE_BATCH_PREDICTIONS", "true").lower() == "true",
            "enable_model_versioning": os.getenv("FF_ENABLE_MODEL_VERSIONING", "true").lower() == "true",
        }

    def is_enabled(self, flag: str) -> bool:
        return self._flags.get(flag, False)

    def enable(self, flag: str) -> None:
        self._flags[flag] = True

    def disable(self, flag: str) -> None:
        self._flags[flag] = False

    def list_flags(self) -> Dict[str, bool]:
        return self._flags.copy()


@lru_cache()
def get_feature_flags() -> FeatureFlags:
    return FeatureFlags()

from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    default_limit: int = 100
    default_window: int = 60
    custom_limits: dict = None

    def __post_init__(self):
        if self.custom_limits is None:
            self.custom_limits = {
                r"/api/v1/auth/login": (5, 60),
                r"/api/v1/auth/register": (3, 300),
                r"/api/v1/datasets": (10, 60),
                r"/api/v1/models": (20, 60),
                r"/api/v1/models/.*/train": (5, 300),
                r"/api/v1/models/.*/predict": (50, 60),
                r"/api/v1/monitoring/stats": (30, 60),
            }


rate_limit_config = RateLimitConfig()

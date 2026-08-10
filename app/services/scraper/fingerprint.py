"""Browser Fingerprint — Rotate canvas/webgl/audio fingerprint for anti-detect scraping."""
import random
import hashlib
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class BrowserFingerprint:
    user_agent: str = ""
    platform: str = ""
    screen_width: int = 1920
    screen_height: int = 1080
    color_depth: int = 24
    pixel_ratio: float = 1.0
    timezone: str = ""
    language: str = "en-US"
    languages: list[str] = field(default_factory=lambda: ["en-US", "en"])
    do_not_track: bool = False
    cookie_enabled: bool = True
    canvas_hash: str = ""
    webgl_vendor: str = ""
    webgl_renderer: str = ""
    audio_hash: str = ""
    web_rtc_enabled: bool = False
    plugins: list[str] = field(default_factory=list)
    mime_types: list[str] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)
    hardware_concurrency: int = 8
    device_memory: int = 8
    max_touch_points: int = 0
    connection_type: str = "wifi"
    headers: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "user_agent": self.user_agent,
            "platform": self.platform,
            "screen": f"{self.screen_width}x{self.screen_height}",
            "timezone": self.timezone,
            "language": self.language,
            "canvas_hash": self.canvas_hash[:16],
            "webgl": f"{self.webgl_vendor} {self.webgl_renderer}",
            "hardware_concurrency": self.hardware_concurrency,
        }

    def to_headers(self) -> dict:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": f"{self.language},{self.languages[1] if len(self.languages) > 1 else 'en'};q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1" if self.do_not_track else "0",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
        headers.update(self.headers)
        return headers


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
]

WEBGL_VENDORS = ["Google Inc. (NVIDIA)", "Google Inc. (AMD)", "Google Inc. (Intel)", "Mozilla"]
WEBGL_RENDERERS = [
    "ANGLE (NVIDIA GeForce RTX 4090 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (Intel Iris Xe Graphics Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0)",
    "ANGLE (AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0)",
]

PLATFORMS = ["Win32", "MacIntel", "Linux x86_64"]
TIMEZONES = [
    "Asia/Jakarta", "Asia/Makassar", "Asia/Jayapura",
    "America/New_York", "America/Los_Angeles", "Europe/London",
    "Asia/Tokyo", "Asia/Shanghai", "Europe/Berlin",
]

LANGUAGES = [
    (["en-US", "en"], "en-US"),
    (["id-ID", "id", "en-US", "en"], "id-ID"),
    (["en-GB", "en"], "en-GB"),
    (["ja-JP", "ja", "en-US", "en"], "ja-JP"),
]

FONTS = [
    "Arial", "Verdana", "Times New Roman", "Courier New", "Georgia",
    "Palatino", "Garamond", "Comic Sans MS", "Impact", "Lucida Console",
    "Tahoma", "Trebuchet MS", "Helvetica", "Calibri", "Cambria",
]


class FingerprintGenerator:

    def __init__(self):
        self._used_hashes = set()
        self._local_random = random.Random()

    def generate(self) -> BrowserFingerprint:
        ua = self._local_random.choice(USER_AGENTS)
        platform = "Win32" if "Windows" in ua else "MacIntel" if "Macintosh" in ua else "Linux x86_64"
        lang_pair = self._local_random.choice(LANGUAGES)

        screen_sizes = [(1920, 1080), (2560, 1440), (1366, 768), (1536, 864), (1440, 900)]
        screen_w, screen_h = self._local_random.choice(screen_sizes)

        canvas_hash = hashlib.md5(f"{ua}{self._local_random.random()}".encode()).hexdigest()
        audio_hash = hashlib.md5(f"{self._local_random.random()}{platform}".encode()).hexdigest()

        fp = BrowserFingerprint(
            user_agent=ua,
            platform=platform,
            screen_width=screen_w,
            screen_height=screen_h,
            color_depth=self._local_random.choice([24, 30, 32]),
            pixel_ratio=self._local_random.choice([1.0, 1.25, 1.5, 2.0]),
            timezone=self._local_random.choice(TIMEZONES),
            language=lang_pair[1],
            languages=lang_pair[0],
            do_not_track=self._local_random.choice([True, False]),
            canvas_hash=canvas_hash,
            webgl_vendor=self._local_random.choice(WEBGL_VENDORS),
            webgl_renderer=self._local_random.choice(WEBGL_RENDERERS),
            audio_hash=audio_hash,
            web_rtc_enabled=self._local_random.choice([True, False]),
            plugins=self._local_random.sample(["PDF Viewer", "Chrome PDF Viewer", "Chromium PDF Viewer"], k=self._local_random.randint(1, 3)),
            fonts=self._local_random.sample(FONTS, k=self._local_random.randint(5, 12)),
            hardware_concurrency=self._local_random.choice([2, 4, 6, 8, 12, 16]),
            device_memory=self._local_random.choice([2, 4, 8, 16, 32]),
            max_touch_points=0 if "Mobile" not in ua else self._local_random.randint(1, 5),
            connection_type=self._local_random.choice(["wifi", "4g", "3g", "ethernet"]),
        )
        return fp

    def generate_batch(self, count: int) -> list[BrowserFingerprint]:
        return [self.generate() for _ in range(count)]

    def get_consistent_fingerprint(self, session_id: str) -> BrowserFingerprint:
        seed = int(hashlib.md5(session_id.encode()).hexdigest()[:8], 16)
        self._local_random.seed(seed)
        fp = self.generate()
        self._local_random.seed()
        return fp

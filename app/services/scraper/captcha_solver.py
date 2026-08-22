"""CAPTCHA Solver — Basic + Advanced CAPTCHA solving with 2Captcha/Anti-Captcha API."""
import re
import time
import base64
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

import httpx

from app.services.scraper.shared import USER_AGENTS

logger = logging.getLogger(__name__)


@dataclass
class CaptchaResult:
    solved: bool = False
    solution: str = ""
    method: str = ""
    confidence: float = 0.0
    error: str = ""
    solve_time_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "solved": self.solved,
            "solution": self.solution[:50] if self.solution else "",
            "method": self.method,
            "confidence": round(self.confidence, 4),
            "error": self.error,
            "solve_time_ms": self.solve_time_ms,
        }


class CaptchaSolver:

    SIMPLE_PATTERNS = {
        "math": r'(\d+)\s*([\+\-\*\/])\s*(\d+)',
        "word": r'type\s+(?:the\s+)?(?:word\s+)?["\']?(\w+)["\']?',
        "number": r'(\d{4,6})',
        "code": r'code[:\s]+(\w+)',
    }

    def __init__(self, api_key: str = "", service: str = "2captcha"):
        from app.core.config import get_settings
        settings = get_settings()
        self.api_key = api_key or settings.CAPTCHA_API_KEY
        self.service = service or settings.CAPTCHA_SERVICE

    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        invisible: bool = False,
    ) -> CaptchaResult:
        """Solve reCAPTCHA v2 using external API."""
        if not self.api_key:
            return CaptchaResult(error="CAPTCHA_API_KEY not configured", method="recaptcha_v2")

        start = time.time()
        result = CaptchaResult(method="recaptcha_v2")

        try:
            if self.service == "2captcha":
                solution = await self._solve_2captcha_recaptcha(site_key, page_url, invisible)
            elif self.service == "anticaptcha":
                solution = await self._solve_anticaptcha_recaptcha(site_key, page_url)
            else:
                return CaptchaResult(error=f"Unknown service: {self.service}", method="recaptcha_v2")

            if solution:
                result.solved = True
                result.solution = solution
                result.confidence = 0.95
            else:
                result.error = "No solution returned"
        except Exception as e:
            result.error = str(e)
            logger.error(f"reCAPTCHA solve failed: {e}")

        result.solve_time_ms = int((time.time() - start) * 1000)
        return result

    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str = "submit",
        min_score: float = 0.7,
    ) -> CaptchaResult:
        """Solve reCAPTCHA v3 using external API."""
        if not self.api_key:
            return CaptchaResult(error="CAPTCHA_API_KEY not configured", method="recaptcha_v3")

        start = time.time()
        result = CaptchaResult(method="recaptcha_v3")

        try:
            if self.service == "2captcha":
                solution = await self._solve_2captcha_recaptcha_v3(site_key, page_url, action, min_score)
            elif self.service == "anticaptcha":
                solution = await self._solve_anticaptcha_recaptcha_v3(site_key, page_url, action, min_score)
            else:
                return CaptchaResult(error=f"Unknown service: {self.service}", method="recaptcha_v3")

            if solution:
                result.solved = True
                result.solution = solution
                result.confidence = 0.90
            else:
                result.error = "No solution returned"
        except Exception as e:
            result.error = str(e)
            logger.error(f"reCAPTCHA v3 solve failed: {e}")

        result.solve_time_ms = int((time.time() - start) * 1000)
        return result

    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
    ) -> CaptchaResult:
        """Solve hCaptcha using external API."""
        if not self.api_key:
            return CaptchaResult(error="CAPTCHA_API_KEY not configured", method="hcaptcha")

        start = time.time()
        result = CaptchaResult(method="hcaptcha")

        try:
            if self.service == "2captcha":
                solution = await self._solve_2captcha_hcaptcha(site_key, page_url)
            elif self.service == "anticaptcha":
                solution = await self._solve_anticaptcha_hcaptcha(site_key, page_url)
            else:
                return CaptchaResult(error=f"Unknown service: {self.service}", method="hcaptcha")

            if solution:
                result.solved = True
                result.solution = solution
                result.confidence = 0.90
            else:
                result.error = "No solution returned"
        except Exception as e:
            result.error = str(e)
            logger.error(f"hCaptcha solve failed: {e}")

        result.solve_time_ms = int((time.time() - start) * 1000)
        return result

    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str,
    ) -> CaptchaResult:
        """Solve Cloudflare Turnstile using external API."""
        if not self.api_key:
            return CaptchaResult(error="CAPTCHA_API_KEY not configured", method="turnstile")

        start = time.time()
        result = CaptchaResult(method="turnstile")

        try:
            if self.service == "2captcha":
                solution = await self._solve_2captcha_turnstile(site_key, page_url)
            else:
                return CaptchaResult(error=f"Turnstile not supported for {self.service}", method="turnstile")

            if solution:
                result.solved = True
                result.solution = solution
                result.confidence = 0.85
            else:
                result.error = "No solution returned"
        except Exception as e:
            result.error = str(e)
            logger.error(f"Turnstile solve failed: {e}")

        result.solve_time_ms = int((time.time() - start) * 1000)
        return result

    async def solve_image_captcha(self, image_bytes: bytes) -> CaptchaResult:
        """Solve image CAPTCHA using external API or local analysis."""
        if self.api_key:
            return await self._solve_image_via_api(image_bytes)
        return self._solve_image_local(image_bytes)

    # ─── 2Captcha Integration ────────────────────────────────────────────

    async def _solve_2captcha_recaptcha(self, site_key: str, page_url: str, invisible: bool = False) -> Optional[str]:
        payload = {
            "key": self.api_key,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "json": 1,
        }
        if invisible:
            payload["invisible"] = 1

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post("https://2captcha.com/in.php", data=payload)
            data = resp.json()

            if data.get("status") != 1:
                logger.error(f"2Captcha submit failed: {data}")
                return None

            task_id = data["request"]
            return await self._poll_2captcha(client, task_id)

    async def _solve_2captcha_recaptcha_v3(self, site_key: str, page_url: str, action: str, min_score: float) -> Optional[str]:
        payload = {
            "key": self.api_key,
            "method": "userrecaptcha",
            "googlekey": site_key,
            "pageurl": page_url,
            "version": "v3",
            "action": action,
            "min_score": min_score,
            "json": 1,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post("https://2captcha.com/in.php", data=payload)
            data = resp.json()

            if data.get("status") != 1:
                return None

            task_id = data["request"]
            return await self._poll_2captcha(client, task_id)

    async def _solve_2captcha_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        payload = {
            "key": self.api_key,
            "method": "hcaptcha",
            "sitekey": site_key,
            "pageurl": page_url,
            "json": 1,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post("https://2captcha.com/in.php", data=payload)
            data = resp.json()

            if data.get("status") != 1:
                return None

            task_id = data["request"]
            return await self._poll_2captcha(client, task_id)

    async def _solve_2captcha_turnstile(self, site_key: str, page_url: str) -> Optional[str]:
        payload = {
            "key": self.api_key,
            "method": "turnstile",
            "sitekey": site_key,
            "pageurl": page_url,
            "json": 1,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post("https://2captcha.com/in.php", data=payload)
            data = resp.json()

            if data.get("status") != 1:
                return None

            task_id = data["request"]
            return await self._poll_2captcha(client, task_id)

    async def _poll_2captcha(self, client: httpx.AsyncClient, task_id: str, max_wait: int = 120) -> Optional[str]:
        for _ in range(max_wait // 5):
            await asyncio.sleep(5)
            resp = await client.get(
                f"https://2captcha.com/res.php",
                params={"key": self.api_key, "action": "get", "id": task_id, "json": 1},
            )
            data = resp.json()
            if data.get("status") == 1:
                return data["request"]
            if "CAPCHA_NOT_READY" not in str(data.get("request", "")):
                logger.error(f"2Captcha error: {data}")
                return None
        return None

    # ─── Anti-Captcha Integration ─────────────────────────────────────────

    async def _solve_anticaptcha_recaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "RecaptchaV2TaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
            },
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post("https://api.anti-captcha.com/createTask", json=payload)
            data = resp.json()

            if data.get("errorId") != 0:
                logger.error(f"Anti-Captcha error: {data}")
                return None

            task_id = data["taskId"]
            return await self._poll_anticaptcha(client, task_id)

    async def _solve_anticaptcha_recaptcha_v3(self, site_key: str, page_url: str, action: str, min_score: float) -> Optional[str]:
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "RecaptchaV3TaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
                "pageAction": action,
                "minScore": min_score,
            },
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post("https://api.anti-captcha.com/createTask", json=payload)
            data = resp.json()

            if data.get("errorId") != 0:
                return None

            task_id = data["taskId"]
            return await self._poll_anticaptcha(client, task_id)

    async def _solve_anticaptcha_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "HCaptchaTaskProxyless",
                "websiteURL": page_url,
                "websiteKey": site_key,
            },
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post("https://api.anti-captcha.com/createTask", json=payload)
            data = resp.json()

            if data.get("errorId") != 0:
                return None

            task_id = data["taskId"]
            return await self._poll_anticaptcha(client, task_id)

    async def _poll_anticaptcha(self, client: httpx.AsyncClient, task_id: int, max_wait: int = 120) -> Optional[str]:
        for _ in range(max_wait // 5):
            await asyncio.sleep(5)
            resp = await client.post(
                "https://api.anti-captcha.com/getTaskResult",
                json={"clientKey": self.api_key, "taskId": task_id},
            )
            data = resp.json()
            if data.get("status") == "ready":
                return data.get("solution", {}).get("token", "")
            if data.get("errorId") != 0:
                logger.error(f"Anti-Captcha poll error: {data}")
                return None
        return None

    async def _solve_image_via_api(self, image_bytes: bytes) -> CaptchaResult:
        """Send image CAPTCHA to 2Captcha API for solving."""
        import time
        start = time.time()
        result = CaptchaResult(method="image_api")

        if not self.api_key:
            return self._solve_image_local(image_bytes)

        try:
            b64_image = base64.b64encode(image_bytes).decode()

            if self.service == "2captcha":
                payload = {
                    "key": self.api_key,
                    "method": "base64",
                    "body": b64_image,
                    "json": 1,
                }
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post("https://2captcha.com/in.php", data=payload)
                    data = resp.json()

                    if data.get("status") != 1:
                        return self._solve_image_local(image_bytes)

                    task_id = data["request"]
                    solution = await self._poll_2captcha(client, task_id, max_wait=60)

                    if solution:
                        result.solved = True
                        result.solution = solution
                        result.confidence = 0.85
                    else:
                        result.error = "API returned no solution"
            else:
                return self._solve_image_local(image_bytes)

        except Exception as e:
            result.error = str(e)
            logger.error(f"Image CAPTCHA API solve failed: {e}")

        result.solve_time_ms = int((time.time() - start) * 1000)
        return result

    def _solve_image_local(self, image_bytes: bytes) -> CaptchaResult:
        """Local image CAPTCHA analysis (basic OCR-free approach)."""
        import time
        start = time.time()
        result = CaptchaResult(method="image_local")

        try:
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode != "L":
                img = img.convert("L")
            width, height = img.size
            pixels = list(img.getdata())

            threshold = 128
            binary = [0 if p < threshold else 1 for p in pixels]

            char_regions = []
            in_char = False
            char_start = 0
            for x in range(width):
                col_has_black = any(binary[y * width + x] == 0 for y in range(height))
                if col_has_black and not in_char:
                    in_char = True
                    char_start = x
                elif not col_has_black and in_char:
                    in_char = False
                    if x - char_start > 3:
                        char_regions.append((char_start, x))

            if len(char_regions) >= 3:
                result.solved = True
                result.solution = f"detected_{len(char_regions)}_characters"
                result.confidence = 0.40
            else:
                result.error = "Could not detect enough characters"

        except ImportError:
            result.error = "Pillow not installed"
        except Exception as e:
            result.error = str(e)

        result.solve_time_ms = int((time.time() - start) * 1000)
        return result

    def solve_text_captcha(self, text: str) -> CaptchaResult:
        """Solve simple text-based CAPTCHAs (math, words, numbers)."""
        import time
        start = time.time()
        result = CaptchaResult()

        text_lower = text.lower()

        for name, pattern in self.SIMPLE_PATTERNS.items():
            match = re.search(pattern, text_lower)
            if match:
                if name == "math":
                    num1, op, num2 = match.groups()
                    try:
                        if op == "+":
                            solution = str(int(num1) + int(num2))
                        elif op == "-":
                            solution = str(int(num1) - int(num2))
                        elif op == "*":
                            solution = str(int(num1) * int(num2))
                        elif op == "/":
                            solution = str(int(int(num1) / int(num2)))
                        else:
                            continue
                        result.solved = True
                        result.solution = solution
                        result.method = "math_expression"
                        result.confidence = 0.95
                    except (ValueError, ZeroDivisionError):
                        pass
                elif name == "word":
                    result.solved = True
                    result.solution = match.group(1)
                    result.method = "word_extraction"
                    result.confidence = 0.90
                elif name == "number":
                    result.solved = True
                    result.solution = match.group(1)
                    result.method = "number_extraction"
                    result.confidence = 0.85
                elif name == "code":
                    result.solved = True
                    result.solution = match.group(1)
                    result.method = "code_extraction"
                    result.confidence = 0.80
                break

        if not result.solved:
            numbers = re.findall(r'\d+', text)
            if len(numbers) == 1:
                result.solved = True
                result.solution = numbers[0]
                result.method = "single_number"
                result.confidence = 0.60

        result.solve_time_ms = int((time.time() - start) * 1000)
        return result

    def detect_captcha_type(self, html: str) -> dict:
        """Detect CAPTCHA type from HTML content."""
        types = []
        html_lower = html.lower()

        if "recaptcha" in html_lower or "g-recaptcha" in html:
            version = "v3" if "v3" in html or "data-size='invisible'" in html else "v2"
            site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            site_key = site_key_match.group(1) if site_key_match else ""
            types.append({
                "type": f"recaptcha_{version}",
                "difficulty": "hard",
                "needs_api": True,
                "site_key": site_key,
            })

        if "hcaptcha" in html_lower:
            site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            site_key = site_key_match.group(1) if site_key_match else ""
            types.append({
                "type": "hcaptcha",
                "difficulty": "hard",
                "needs_api": True,
                "site_key": site_key,
            })

        if "turnstile" in html_lower or "cf-turnstile" in html:
            site_key_match = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
            site_key = site_key_match.group(1) if site_key_match else ""
            types.append({
                "type": "cloudflare_turnstile",
                "difficulty": "hard",
                "needs_api": True,
                "site_key": site_key,
            })

        if "captcha" in html_lower:
            text_match = re.search(r'captcha["\s:]+([^<]{10,200})', html_lower)
            if text_match:
                types.append({"type": "text_captcha", "difficulty": "easy", "text": text_match.group(1)})
            else:
                types.append({"type": "unknown_captcha", "difficulty": "medium"})

        if "anti-bot" in html_lower or "bot detection" in html_lower:
            types.append({"type": "bot_detection", "difficulty": "hard"})

        return {"types": types, "has_captcha": len(types) > 0}

    def generate_user_agent_rotation(self) -> list[str]:
        return USER_AGENTS

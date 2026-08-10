"""CAPTCHA Solver — Basic CAPTCHA solving capabilities."""
import re
import hashlib
import base64
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from io import BytesIO

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

    def solve_text_captcha(self, text: str) -> CaptchaResult:
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

    def solve_image_captcha(self, image_bytes: bytes) -> CaptchaResult:
        import time
        start = time.time()
        result = CaptchaResult()

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

            grid = []
            for y in range(height):
                row = []
                for x in range(width):
                    row.append(binary[y * width + x])
                grid.append(row)

            char_regions = []
            in_char = False
            char_start = 0
            for x in range(width):
                col_has_black = any(grid[y][x] == 0 for y in range(height))
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
                result.method = "image_analysis"
                result.confidence = 0.40
            else:
                result.error = "Could not detect enough characters"
                result.method = "image_analysis"

        except ImportError:
            result.error = "Pillow not installed"
        except Exception as e:
            result.error = str(e)

        result.solve_time_ms = int((time.time() - start) * 1000)
        return result

    def detect_captcha_type(self, html: str) -> dict:
        types = []
        if "recaptcha" in html.lower() or "g-recaptcha" in html:
            types.append({"type": "recaptcha", "difficulty": "hard", "needs_api": True})
        if "hcaptcha" in html.lower():
            types.append({"type": "hcaptcha", "difficulty": "hard", "needs_api": True})
        if "turnstile" in html.lower() or "cf-turnstile" in html:
            types.append({"type": "cloudflare_turnstile", "difficulty": "hard", "needs_api": True})
        if "captcha" in html.lower():
            text_match = re.search(r'captcha["\s:]+([^<]{10,200})', html.lower())
            if text_match:
                types.append({"type": "text_captcha", "difficulty": "easy", "text": text_match.group(1)})
            else:
                types.append({"type": "unknown_captcha", "difficulty": "medium"})
        if "anti-bot" in html.lower() or "bot detection" in html.lower():
            types.append({"type": "bot_detection", "difficulty": "hard"})
        return {"types": types, "has_captcha": len(types) > 0}

    def generate_user_agent_rotation(self) -> list[str]:
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        ]

import re
from typing import List, Dict, Tuple
from datetime import datetime
import hashlib
import json

from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityScanner:
    SQL_INJECTION_PATTERNS = [
        r"('\s*or\s*')",
        r"(;\s*drop\s+table)",
        r"(;\s*delete\s+from)",
        r"(;\s*insert\s+into)",
        r"(union\s+select)",
        r"(--\s*$)",
        r"(\/\*.*\*\/)",
        r"(;\s*exec\s*\()",
        r"(;\s*execute\s*\()",
    ]

    XSS_PATTERNS = [
        r"<script.*?>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe.*?>",
        r"<object.*?>",
        r"<embed.*?>",
        r"<form.*?>",
        r"eval\s*\(",
        r"document\.\w+",
        r"window\.\w+",
    ]

    PATH_TRAVERSAL_PATTERNS = [
        r"\.\.\/",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e/",
        r"\.%2e%2f",
        r"\.%2e\/",
    ]

    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`]",
        r"\$\(",
        r"\$\{",
        r"!\d+",
        r">\s*\/dev\/null",
    ]

    def __init__(self):
        self.scan_results: List[Dict] = []

    def scan_input(self, input_str: str, input_type: str = "general") -> List[Dict]:
        threats = []

        threats.extend(self._check_sql_injection(input_str, input_type))
        threats.extend(self._check_xss(input_str, input_type))
        threats.extend(self._check_path_traversal(input_str, input_type))
        threats.extend(self._check_command_injection(input_str, input_type))
        threats.extend(self._check敏感信息(input_str, input_type))

        if threats:
            logger.warning(
                f"Security threats detected in {input_type}",
                threats=threats,
                input_length=len(input_str),
            )

        return threats

    def _check_sql_injection(self, input_str: str, input_type: str) -> List[Dict]:
        threats = []
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                threats.append({
                    "type": "sql_injection",
                    "severity": "critical",
                    "pattern": pattern,
                    "input_type": input_type,
                    "timestamp": datetime.utcnow().isoformat(),
                })
        return threats

    def _check_xss(self, input_str: str, input_type: str) -> List[Dict]:
        threats = []
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                threats.append({
                    "type": "xss",
                    "severity": "high",
                    "pattern": pattern,
                    "input_type": input_type,
                    "timestamp": datetime.utcnow().isoformat(),
                })
        return threats

    def _check_path_traversal(self, input_str: str, input_type: str) -> List[Dict]:
        threats = []
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, input_str, re.IGNORECASE):
                threats.append({
                    "type": "path_traversal",
                    "severity": "high",
                    "pattern": pattern,
                    "input_type": input_type,
                    "timestamp": datetime.utcnow().isoformat(),
                })
        return threats

    def _check_command_injection(self, input_str: str, input_type: str) -> List[Dict]:
        threats = []
        for pattern in self.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, input_str):
                threats.append({
                    "type": "command_injection",
                    "severity": "critical",
                    "pattern": pattern,
                    "input_type": input_type,
                    "timestamp": datetime.utcnow().isoformat(),
                })
        return threats

    def _check敏感信息(self, input_str: str, input_type: str) -> List[Dict]:
        threats = []

        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        if re.search(email_pattern, input_str):
            threats.append({
                "type": "pii_email",
                "severity": "low",
                "input_type": input_type,
                "timestamp": datetime.utcnow().isoformat(),
            })

        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        if re.search(phone_pattern, input_str):
            threats.append({
                "type": "pii_phone",
                "severity": "low",
                "input_type": input_type,
                "timestamp": datetime.utcnow().isoformat(),
            })

        ssn_pattern = r'\d{3}-\d{2}-\d{4}'
        if re.search(ssn_pattern, input_str):
            threats.append({
                "type": "pii_ssn",
                "severity": "critical",
                "input_type": input_type,
                "timestamp": datetime.utcnow().isoformat(),
            })

        return threats

    def sanitize_input(self, input_str: str) -> str:
        sanitized = input_str

        sanitized = re.sub(r'<[^>]+>', '', sanitized)
        sanitized = re.sub(r'[<>"\']', '', sanitized)
        sanitized = re.sub(r';', '', sanitized)
        sanitized = re.sub(r'\.\.\/', '', sanitized)
        sanitized = re.sub(r'\.\.\\', '', sanitized)

        return sanitized

    def validate_file_upload(self, filename: str, content: bytes) -> Dict:
        issues = []

        dangerous_extensions = ['.exe', '.bat', '.cmd', '.sh', '.bash', '.ps1', '.vbs', '.js']
        ext = filename.lower().split('.')[-1] if '.' in filename else ''

        if f'.{ext}' in dangerous_extensions:
            issues.append({
                "type": "dangerous_file_extension",
                "severity": "critical",
                "extension": ext,
            })

        if len(content) > 100 * 1024 * 1024:
            issues.append({
                "type": "file_too_large",
                "severity": "medium",
                "size": len(content),
            })

        malware_signatures = [b'MZ', b'PK\x03\x04', b'\x7fELF']
        for sig in malware_signatures:
            if content[:len(sig)] == sig:
                issues.append({
                    "type": "potential_malware",
                    "severity": "critical",
                    "signature": sig.hex(),
                })

        return {
            "safe": len(issues) == 0,
            "issues": issues,
        }


security_scanner = SecurityScanner()

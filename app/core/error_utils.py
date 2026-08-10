import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SENSITIVE_PATTERNS = [
    (r'password[=:]\s*\S+', 'password=***'),
    (r'secret[=:]\s*\S+', 'secret=***'),
    (r'token[=:]\s*\S+', 'token=***'),
    (r'key[=:]\s*\S+', 'key=***'),
    (r'credentials?[=:]\s*\S+', 'credentials=***'),
    (r'authorization[=:]\s*\S+', 'authorization=***'),
    (r'Bearer\s+\S+', 'Bearer ***'),
    (r'postgresql://[^\s]+', 'postgresql://***'),
    (r'redis://[^\s]+', 'redis://***'),
    (r'mysql://[^\s]+', 'mysql://***'),
    (r'mongodb://[^\s]+', 'mongodb://***'),
    (r'\/[a-zA-Z]:\\[^\s]+', '***'),
    (r'\/home\/[^\s]+', '***'),
    (r'\/var\/[^\s]+', '***'),
    (r'\/etc\/[^\s]+', '***'),
    (r'File "([^"]+)"', 'File "***"'),
    (r'line \d+', 'line ***'),
]

SAFE_ERROR_MESSAGES = {
    'ValueError': 'Input yang diberikan tidak valid',
    'KeyError': 'Kolom atau field yang dibutuhkan tidak ada',
    'TypeError': 'Tipe data tidak sesuai',
    'FileNotFoundError': 'File atau resource yang diminta tidak ditemukan',
    'PermissionError': 'Akses ditolak',
    'ConnectionError': 'Layanan sedang tidak tersedia, silakan coba lagi',
    'TimeoutError': 'Operasi melebihi batas waktu, silakan coba lagi',
    'MemoryError': 'Memori tidak mencukupi untuk menyelesaikan operasi',
    'OSError': 'Terjadi kesalahan sistem',
    'ImportError': 'Dependensi yang dibutuhkan tidak terpasang',
    'ModuleNotFoundError': 'Dependensi yang dibutuhkan tidak terpasang',
    'OverflowError': 'Nilai melebihi batas yang didukung',
    'IndexError': 'Data yang diminta berada di luar jangkauan',
    'AttributeError': 'Terjadi kesalahan internal pada data',
    'ZeroDivisionError': 'Perhitungan gagal karena pembagian dengan nol',
    'BrokenPipeError': 'Koneksi terputus, silakan coba lagi',
}

TECHNICAL_ERROR_TRANSLATIONS = [
    (re.compile(r'no module named ["\']?celery["\']?', re.IGNORECASE),
     'Layanan pelatihan background (Celery) tidak tersedia. Pelatihan akan dijalankan langsung secara sinkron.'),
    (re.compile(r'kombu|amqp', re.IGNORECASE),
     'Layanan antrean tugas (Celery) sedang tidak tersedia. Pelatihan akan dijalankan langsung secara sinkron.'),
    (re.compile(r'celery', re.IGNORECASE),
     'Layanan pelatihan background (Celery) sedang tidak tersedia. Pelatihan akan dijalankan langsung secara sinkron jika memungkinkan.'),
    (re.compile(r'redis\.exceptions|redis.*connection refused|connect to redis', re.IGNORECASE),
     'Layanan antrean/cache (Redis) sedang tidak tersedia. Silakan coba lagi sebentar lagi.'),
    (re.compile(r'redis', re.IGNORECASE),
     'Layanan antrean/cache sedang tidak tersedia. Silakan coba lagi sebentar lagi.'),
    (re.compile(r'asyncpg|psycopg2|sqlalchemy\.exc|postgresql', re.IGNORECASE),
     'Terjadi kendala sementara pada database. Silakan coba lagi, atau hubungi admin jika berlanjut.'),
    (re.compile(r'connection refused|connect call failed|timed out', re.IGNORECASE),
     'Layanan yang dituju sedang tidak tersedia. Silakan coba lagi sebentar lagi.'),
    (re.compile(r'no space left|disk quota|out of disk', re.IGNORECASE),
     'Penyimpanan server penuh. Silakan hubungi admin untuk dibersihkan.'),
    (re.compile(r'no module named', re.IGNORECASE),
     'Ada komponen yang belum terpasang di server. Silakan hubungi admin.'),
    (re.compile(r'failed to parse|error parsing|could not convert string to float', re.IGNORECASE),
     'File tidak dapat dibaca. Periksa kembali format dan isi file yang diunggah.'),
    (re.compile(r'permission denied', re.IGNORECASE),
     'Akses ditolak oleh sistem. Silakan hubungi admin.'),
]


def translate_error_message(message: str) -> str:
    for pattern, translated in TECHNICAL_ERROR_TRANSLATIONS:
        if pattern.search(message):
            return translated
    return message


def sanitize_error_message(error: Exception, include_type: bool = False) -> str:
    """
    Sanitize exception message to prevent internal detail leakage.
    
    Args:
        error: The exception to sanitize
        include_type: Whether to include exception type in output
        
    Returns:
        Sanitized error message safe for client response
    """
    error_type = type(error).__name__

    if error_type in SAFE_ERROR_MESSAGES:
        base_message = SAFE_ERROR_MESSAGES[error_type]
    else:
        base_message = "An unexpected error occurred"

    raw_message = str(error)

    if not raw_message:
        return base_message

    translated = translate_error_message(raw_message)
    if translated != raw_message:
        return translated

    sanitized = raw_message

    for pattern, replacement in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    if len(sanitized) > 200:
        sanitized = sanitized[:200] + "..."

    if include_type:
        return f"{base_message} ({error_type})"

    return base_message


def log_error(error: Exception, context: Optional[str] = None, exc_info: bool = True):
    """
    Log error with full details for internal debugging.
    
    Args:
        error: The exception to log
        context: Additional context about where the error occurred
        exc_info: Whether to include stack trace
    """
    if context:
        logger.error(f"{context}: {error}", exc_info=exc_info)
    else:
        logger.error(f"Error: {error}", exc_info=exc_info)


HTTP_STATUS_TRANSLATIONS = {
    400: 'Permintaan tidak valid. Periksa kembali data yang dikirim.',
    401: 'Sesi Anda sudah berakhir atau tidak valid. Silakan masuk kembali.',
    403: 'Anda tidak memiliki izin untuk mengakses sumber daya ini.',
    404: 'Data yang Anda cari tidak ditemukan.',
    405: 'Metode permintaan tidak didukung untuk endpoint ini.',
    408: 'Waktu tunggu permintaan habis. Silakan coba lagi.',
    409: 'Terjadi konflik data. Periksa kembali permintaan Anda.',
    413: 'File yang diunggah terlalu besar.',
    415: 'Format file tidak didukung.',
    422: 'Data yang dikirim tidak valid. Periksa kembali isian Anda.',
    429: 'Terlalu banyak permintaan dalam waktu singkat. Silakan tunggu sebentar lalu coba lagi.',
    500: 'Terjadi kesalahan internal pada sistem. Tim kami telah mendapat notifikasi.',
    501: 'Fitur ini belum tersedia.',
    502: 'Layanan sedang sibuk atau tidak tersedia. Silakan coba lagi.',
    503: 'Layanan sedang tidak tersedia. Silakan coba lagi sebentar lagi.',
    504: 'Waktu tunggu layanan habis. Silakan coba lagi.',
}


def translate_http_status(status_code: int) -> str:
    """Return a human-readable Indonesian message for an HTTP status code."""
    return HTTP_STATUS_TRANSLATIONS.get(
        status_code,
        f'Terjadi kesalahan pada permintaan (kode {status_code}). Silakan coba lagi.',
    )


def humanize_http_detail(detail, status_code: int = 500):
    """
    Translate a raw/technical HTTP error detail into a human-readable message.

    - Non-string details (e.g. validation error arrays) are passed through.
    - Strings that match known technical patterns get translated.
    - Strings that look like raw Python exceptions get replaced by the
      HTTP-status translation instead of leaking internals.
    """
    if not isinstance(detail, str):
        return detail
    if not detail.strip():
        return translate_http_status(status_code)

    translated = translate_error_message(detail)
    if translated != detail:
        return translated

    # Heuristic: raw Python exception text reaching users is never acceptable.
    if re.search(
        r"(Traceback \(most recent call last\)|File \"|\n  File |raise |Exception:|Error:)",
        detail,
    ):
        return translate_http_status(status_code)

    return detail


def sanitize_validation_error(error: Exception) -> str:
    """
    Sanitize validation errors while keeping useful user feedback.
    
    Args:
        error: The validation error to sanitize
        
    Returns:
        Sanitized message with actionable feedback
    """
    error_type = type(error).__name__
    raw_message = str(error)

    if error_type == 'ValidationError':
        return "Invalid input. Please check your data and try again."

    if 'null' in raw_message.lower() or 'none' in raw_message.lower():
        return "A required field is missing. Please fill in all required fields."

    if 'out of range' in raw_message.lower():
        return "One or more values are outside the acceptable range."

    if 'invalid' in raw_message.lower():
        return "One or more fields contain invalid data. Please check your input."

    return "Validation failed. Please check your input and try again."

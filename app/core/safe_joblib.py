"""
Safe joblib deserialization with restricted unpickler.
Prevents arbitrary code execution from untrusted .joblib files.

Approach: monkeypatch pickle.Unpickler during joblib.load() so that
all class resolution goes through our whitelist.
"""
import contextlib
import io
import pickle
import logging
from typing import Any, Generator

import joblib

logger = logging.getLogger(__name__)

ALLOWED_PREFIXES = (
    'sklearn.',
    'numpy.',
    'pandas.',
    'scipy.',
    'builtins.',
    'collections.',
    'datetime.',
    'fractions.',
    'numbers.',
    '_codecs.',
)

ALLOWED_GLOBALS = frozenset({
    'builtins.bytes',
    'builtins.dict',
    'builtins.list',
    'builtins.set',
    'builtins.tuple',
    'builtins.range',
    'builtins.slice',
    'builtins.frozenset',
    'builtins.complex',
    'builtins.property',
    'builtins.memoryview',
    'collections.OrderedDict',
    'collections.defaultdict',
    'numpy.dtype',
    'numpy.ndarray',
    'numpy.ma.core.MaskedArray',
    'numpy.ma.core.MaskedConstant',
})


class RestrictedUnpickler(pickle.Unpickler):
    """Unpickler that only allows safe ML-related types."""

    def find_class(self, module: str, name: str) -> Any:
        full = f"{module}.{name}"

        if full in ALLOWED_GLOBALS:
            return super().find_class(module, name)

        if any(module.startswith(p) for p in ALLOWED_PREFIXES):
            return super().find_class(module, name)

        raise pickle.UnpicklingError(
            f"Blocked deserialization of {full} "
            f"(module={module!r}, name={name!r})"
        )


@contextlib.contextmanager
def _restricted_unpickler() -> Generator[None, None, None]:
    """Temporarily replace pickle.Unpickler with RestrictedUnpickler."""
    original = pickle.Unpickler
    pickle.Unpickler = RestrictedUnpickler
    try:
        yield
    finally:
        pickle.Unpickler = original


def safe_load(filepath: str) -> Any:
    """Load a joblib file with restricted unpickling."""
    try:
        with _restricted_unpickler():
            return joblib.load(filepath)
    except pickle.UnpicklingError:
        logger.error(f"Unsafe or corrupted joblib file blocked: {filepath}")
        raise
    except Exception:
        logger.error(f"Failed to load joblib file: {filepath}")
        raise


def safe_load_buffer(data: bytes) -> Any:
    """Load joblib data from bytes with restricted unpickling."""
    try:
        with _restricted_unpickler():
            buf = io.BytesIO(data)
            return joblib.load(buf)
    except pickle.UnpicklingError:
        logger.error("Unsafe or corrupted joblib buffer blocked")
        raise
    except Exception:
        logger.error("Failed to load joblib buffer")
        raise

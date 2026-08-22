"""Track and verify ML library versions for model compatibility."""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Libraries we track for compatibility
_TRACKED_LIBRARIES = {
    'sklearn': 'scikit-learn',
    'xgboost': 'xgboost',
    'lightgbm': 'lightgbm',
    'catboost': 'catboost',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'joblib': 'joblib',
}


def record_library_versions() -> Dict[str, str]:
    """Record current versions of tracked ML libraries."""
    versions = {}
    for key, package_name in _TRACKED_LIBRARIES.items():
        try:
            mod = __import__(package_name.replace('-', '_'))
            versions[key] = getattr(mod, '__version__', 'unknown')
        except ImportError:
            versions[key] = 'not_installed'
    return versions


def check_version_compatibility(
    model_versions: Dict[str, str],
    current_versions: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Compare model's library versions against current runtime versions.
    Returns list of compatibility warnings.
    """
    warnings = []

    for lib, model_ver in model_versions.items():
        current_ver = current_versions.get(lib, 'unknown')

        if model_ver in ('unknown', 'not_installed', None):
            continue
        if current_ver in ('unknown', 'not_installed', None):
            continue

        try:
            model_major = int(model_ver.split('.')[0])
            current_major = int(current_ver.split('.')[0])

            if model_major != current_major:
                warnings.append({
                    'library': lib,
                    'model_version': model_ver,
                    'current_version': current_ver,
                    'severity': 'critical',
                    'message': (
                        f"Library {lib} versi berbeda mayor: "
                        f"model dibuat dengan v{model_ver}, server pakai v{current_ver}. "
                        f"Prediksi mungkin tidak akurat atau error. "
                        f"Pertimbangkan melatih ulang model."
                    ),
                })
            elif model_ver != current_ver:
                warnings.append({
                    'library': lib,
                    'model_version': model_ver,
                    'current_version': current_ver,
                    'severity': 'info',
                    'message': (
                        f"Library {lib} versi minor berbeda: "
                        f"model v{model_ver} vs server v{current_ver}. "
                        f"Biasanya aman, tapi waspadai perubahan behavior."
                    ),
                })
        except (ValueError, IndexError):
            pass

    return warnings

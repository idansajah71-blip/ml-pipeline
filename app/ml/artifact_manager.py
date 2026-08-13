"""
Artifact Manager — immutable artifact bundles with integrity verification + signing.

Each artifact bundle contains:
- manifest.json: metadata, hashes, versions, lineage
- model.joblib: trained model
- processor.joblib: preprocessing pipeline
- checksums.sha256: file integrity hashes (NOT a digital signature)

Integrity: SHA-256 checksums detect accidental corruption.
Signing: HMAC-SHA256 with a private key detects intentional tampering.
Deployment is blocked if either integrity or signature verification fails.
"""

import os
import json
import hashlib
import hmac
import joblib
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Signing key — in production, load from env var / secrets manager
_SIGNING_KEY: Optional[bytes] = None


def set_signing_key(key: str) -> None:
    """Set the HMAC signing key (call once at startup from config)."""
    global _SIGNING_KEY
    _SIGNING_KEY = key.encode() if key else None


def _get_signing_key() -> Optional[bytes]:
    if _SIGNING_KEY is None:
        import os
        key_str = os.environ.get("ARTIFACT_SIGNING_KEY", "")
        if key_str:
            return key_str.encode()
    return _SIGNING_KEY


def compute_file_hash(filepath: str, algorithm: str = 'sha256') -> str:
    """Compute hash of a file."""
    h = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def compute_dict_hash(data: dict) -> str:
    """Compute deterministic hash of a dictionary."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def sign_manifest(manifest: dict) -> str:
    """Sign manifest with HMAC-SHA256. Returns hex signature."""
    key = _get_signing_key()
    if key is None:
        return ""
    payload = json.dumps(manifest, sort_keys=True, default=str).encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def verify_signature(manifest: dict, signature: str) -> bool:
    """Verify HMAC-SHA256 signature. Returns True if valid."""
    key = _get_signing_key()
    if key is None:
        return True  # no key configured → skip verification
    expected = sign_manifest(manifest)
    return hmac.compare_digest(expected, signature)


class ArtifactManager:
    """Manages immutable artifact bundles with integrity verification + signing."""

    def __init__(self, base_path: str):
        self.base_path = base_path

    def save_bundle(
        self,
        model: Any,
        processor_data: dict,
        metadata: dict,
        model_id: str,
        version: int = 1,
    ) -> Dict[str, str]:
        """
        Save an immutable artifact bundle.

        Returns paths to created files.
        """
        bundle_dir = os.path.join(self.base_path, f"model_{model_id}_v{version}")
        os.makedirs(bundle_dir, exist_ok=True)

        model_path = os.path.join(bundle_dir, 'model.joblib')
        processor_path = os.path.join(bundle_dir, 'processor.joblib')
        metadata_path = os.path.join(bundle_dir, 'metadata.json')
        manifest_path = os.path.join(bundle_dir, 'manifest.json')
        checksums_path = os.path.join(bundle_dir, 'checksums.sha256')

        joblib.dump(model, model_path)
        joblib.dump(processor_data, processor_path)

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        model_hash = compute_file_hash(model_path)
        processor_hash = compute_file_hash(processor_path)
        metadata_hash = compute_file_hash(metadata_path)

        manifest = {
            'model_id': model_id,
            'version': version,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'artifact_hash': compute_dict_hash({
                'model': model_hash,
                'processor': processor_hash,
                'metadata': metadata_hash,
            }),
            'file_hashes': {
                'model.joblib': model_hash,
                'processor.joblib': processor_hash,
                'metadata.json': metadata_hash,
            },
            'metadata_hash': metadata_hash,
            'algorithm': metadata.get('algorithm', 'unknown'),
            'problem_type': metadata.get('problem_type', 'unknown'),
            'n_features': metadata.get('preprocess_metadata', {}).get('n_features', 0),
            'n_samples': metadata.get('data_info', {}).get('rows', 0),
            'metrics_summary': {
                k: v for k, v in metadata.get('metrics', {}).items()
                if k in ('accuracy', 'f1_macro', 'f1_weighted', 'r2', 'rmse', 'mae', 'brier_score')
            },
            'python_version': _get_python_version(),
            'sklearn_version': _get_sklearn_version(),
            'integrity_verified': True,
        }

        # Sign manifest
        signature = sign_manifest(manifest)
        manifest['signature'] = signature
        manifest['signature_algorithm'] = 'hmac-sha256' if signature else 'none'

        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2, default=str)

        checksums_content = f"# Artifact checksums for model {model_id} v{version}\n"
        checksums_content += f"model.joblib  {model_hash}\n"
        checksums_content += f"processor.joblib  {processor_hash}\n"
        checksums_content += f"metadata.json  {metadata_hash}\n"
        checksums_content += f"manifest.json  {compute_file_hash(manifest_path)}\n"

        with open(checksums_path, 'w') as f:
            f.write(checksums_content)

        return {
            'bundle_dir': bundle_dir,
            'model_path': model_path,
            'processor_path': processor_path,
            'metadata_path': metadata_path,
            'manifest_path': manifest_path,
            'checksums_path': checksums_path,
            'artifact_hash': manifest['artifact_hash'],
            'signature': signature,
        }

    def verify_bundle(self, bundle_dir: str, check_signature: bool = True) -> Dict[str, Any]:
        """
        Verify integrity + signature of an artifact bundle.

        Returns:
            Dict with 'valid', 'errors', 'manifest'
        """
        errors = []
        manifest_path = os.path.join(bundle_dir, 'manifest.json')

        if not os.path.exists(manifest_path):
            return {'valid': False, 'errors': ['manifest.json not found'], 'manifest': None}

        with open(manifest_path, 'r') as f:
            manifest = json.load(f)

        # 1. File integrity check (SHA-256 checksums)
        file_hashes = manifest.get('file_hashes', {})
        for filename, expected_hash in file_hashes.items():
            filepath = os.path.join(bundle_dir, filename)
            if not os.path.exists(filepath):
                errors.append(f'{filename} missing')
                continue
            actual_hash = compute_file_hash(filepath)
            if actual_hash != expected_hash:
                errors.append(f'{filename} hash mismatch: expected {expected_hash[:16]}..., got {actual_hash[:16]}...')

        # 2. Signature verification (HMAC-SHA256)
        if check_signature:
            signature = manifest.get('signature', '')
            if signature:
                # Verify against manifest without signature field
                manifest_for_verify = {k: v for k, v in manifest.items() if k not in ('signature', 'signature_algorithm')}
                if not verify_signature(manifest_for_verify, signature):
                    errors.append('Manifest signature verification failed — possible tampering')

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'manifest': manifest,
        }

    def load_bundle(self, bundle_dir: str) -> Dict[str, Any]:
        """
        Load an artifact bundle after verifying integrity + signature.

        Raises ValueError if check fails.
        """
        verification = self.verify_bundle(bundle_dir)
        if not verification['valid']:
            raise ValueError(f"Artifact integrity/signature check failed: {verification['errors']}")

        model_path = os.path.join(bundle_dir, 'model.joblib')
        processor_path = os.path.join(bundle_dir, 'processor.joblib')
        metadata_path = os.path.join(bundle_dir, 'metadata.json')

        model = joblib.load(model_path)
        processor_data = joblib.load(processor_path)

        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        return {
            'model': model,
            'processor': processor_data,
            'metadata': metadata,
            'manifest': verification['manifest'],
        }


def _get_python_version() -> str:
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _get_sklearn_version() -> str:
    try:
        import sklearn
        return sklearn.__version__
    except ImportError:
        return 'unknown'

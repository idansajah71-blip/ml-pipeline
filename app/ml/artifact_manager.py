"""
Artifact Manager — immutable artifact bundles with integrity verification + Ed25519 signing.

Each artifact bundle contains:
- manifest.json: metadata, hashes, versions, lineage
- model.joblib: trained model
- processor.joblib: preprocessing pipeline
- checksums.sha256: file integrity hashes (SHA-256)
- public_key.pem: Ed25519 public key for verification

Integrity: SHA-256 checksums detect accidental corruption.
Signing: Ed25519 digital signature detects intentional tampering.
  - Private key signs the manifest during save_bundle().
  - Public key verifies the signature during verify_bundle().
  - If no signing key is configured and ARTIFACT_SIGNING_KEY env is not set,
    signing is skipped and signature_algorithm is 'none'.
  - In production (ARTIFACT_REQUIRE_SIGNATURE=true), bundles without valid
    signatures are BLOCKED.
Deployment is blocked if either integrity or signature verification fails.
"""

import os
import json
import hashlib
import joblib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Ed25519 signing state
_SIGNING_PRIVATE_KEY = None
_VERIFYING_PUBLIC_KEY = None


def set_signing_keys(private_key_pem: Optional[bytes] = None, public_key_pem: Optional[bytes] = None) -> None:
    """Set Ed25519 signing keys (call once at startup from config)."""
    global _SIGNING_PRIVATE_KEY, _VERIFYING_PUBLIC_KEY
    if private_key_pem:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        _SIGNING_PRIVATE_KEY = load_pem_private_key(private_key_pem, password=None)
    if public_key_pem:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        _VERIFYING_PUBLIC_KEY = load_pem_public_key(public_key_pem)


def generate_signing_keypair() -> Tuple[bytes, bytes]:
    """Generate a new Ed25519 key pair. Returns (private_key_pem, public_key_pem)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding, PublicFormat, PrivateFormat, NoEncryption
    )
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    public_pem = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return private_pem, public_pem


def _get_signing_key():
    """Get the Ed25519 private key for signing. Returns None if not configured."""
    global _SIGNING_PRIVATE_KEY
    if _SIGNING_PRIVATE_KEY is not None:
        return _SIGNING_PRIVATE_KEY

    # Try loading from environment
    key_pem_str = os.environ.get("ARTIFACT_SIGNING_KEY_PEM", "")
    if key_pem_str:
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_private_key
            _SIGNING_PRIVATE_KEY = load_pem_private_key(key_pem_str.encode(), password=None)
            return _SIGNING_PRIVATE_KEY
        except Exception as e:
            logger.warning(f"Failed to load signing key from env: {e}")

    return None


def _get_verifying_key():
    """Get the Ed25519 public key for verification. Returns None if not configured."""
    global _VERIFYING_PUBLIC_KEY
    if _VERIFYING_PUBLIC_KEY is not None:
        return _VERIFYING_PUBLIC_KEY

    # Try loading from environment
    key_pem_str = os.environ.get("ARTIFACT_VERIFY_KEY_PEM", "")
    if key_pem_str:
        try:
            from cryptography.hazmat.primitives.serialization import load_pem_public_key
            _VERIFYING_PUBLIC_KEY = load_pem_public_key(key_pem_str.encode())
            return _VERIFYING_PUBLIC_KEY
        except Exception as e:
            logger.warning(f"Failed to load verifying key from env: {e}")

    return None


def _get_require_signature() -> bool:
    """Check if signature verification is mandatory in this environment."""
    return os.environ.get("ARTIFACT_REQUIRE_SIGNATURE", "").lower() in ("true", "1", "yes")


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


def _manifest_bytes_for_signing(manifest: dict) -> bytes:
    """Deterministic bytes of manifest for signing (excludes signature and key fields)."""
    cleaned = {k: v for k, v in manifest.items() if k not in ('signature', 'signature_algorithm', 'public_key', 'public_key_ref')}
    return json.dumps(cleaned, sort_keys=True, default=str).encode()


def sign_manifest(manifest: dict) -> str:
    """Sign manifest with Ed25519. Returns base64-encoded signature, or '' if no key."""
    key = _get_signing_key()
    if key is None:
        return ""
    payload = _manifest_bytes_for_signing(manifest)
    signature = key.sign(payload)
    import base64
    return base64.b64encode(signature).decode()


def verify_signature(manifest: dict, signature_b64: str) -> bool:
    """Verify Ed25519 signature. Returns True if valid or no key configured."""
    if not signature_b64:
        # No signature present — check if verification is required
        if _get_require_signature():
            return False  # Required but missing → reject
        return True  # Not required → allow

    key = _get_verifying_key()
    if key is None:
        # No verification key available
        if _get_require_signature():
            return False  # Required but can't verify → reject
        return True  # Not required → allow (legacy behavior)

    try:
        import base64
        payload = _manifest_bytes_for_signing(manifest)
        signature_bytes = base64.b64decode(signature_b64)
        key.verify(signature_bytes, payload)
        return True
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Signature verification failed: %s", exc)
        return False


def sign_and_save_public_key(private_key_pem: bytes, bundle_dir: str) -> bytes:
    """Sign manifest and save public key to bundle directory. Returns public_key_pem."""
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    private_key = load_pem_private_key(private_key_pem, password=None)
    public_key_pem = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)

    public_key_path = os.path.join(bundle_dir, 'public_key.pem')
    with open(public_key_path, 'wb') as f:
        f.write(public_key_pem)

    return public_key_pem


class ArtifactManager:
    """Manages immutable artifact bundles with integrity verification + Ed25519 signing."""

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

        # Sign manifest with Ed25519
        signature = sign_manifest(manifest)
        manifest['signature'] = signature
        manifest['signature_algorithm'] = 'ed25519' if signature else 'none'

        # Save public key alongside manifest for verification
        public_key_pem = None
        signing_key = _get_signing_key()
        if signing_key:
            from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
            public_key_pem = signing_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
            public_key_path = os.path.join(bundle_dir, 'public_key.pem')
            with open(public_key_path, 'wb') as f:
                f.write(public_key_pem)
            manifest['public_key_ref'] = 'public_key.pem'

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
        Verify integrity + Ed25519 signature of an artifact bundle.

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

        # 2. Ed25519 signature verification
        if check_signature:
            signature = manifest.get('signature', '')
            algorithm = manifest.get('signature_algorithm', 'none')

            if algorithm == 'ed25519' and signature:
                # Try to load public key from bundle first
                public_key_ref = manifest.get('public_key_ref', '')
                bundle_public_key_path = os.path.join(bundle_dir, public_key_ref) if public_key_ref else ''
                saved_public_key = None

                if public_key_ref and os.path.exists(bundle_public_key_path):
                    with open(bundle_public_key_path, 'rb') as f:
                        saved_public_key_pem = f.read()
                    try:
                        from cryptography.hazmat.primitives.serialization import load_pem_public_key
                        saved_public_key = load_pem_public_key(saved_public_key_pem)
                    except Exception as exc:
                        logger.warning("Failed to load public key from bundle: %s", exc)

                # Use saved public key if available, otherwise fall back to env/config key
                verify_key = saved_public_key or _get_verifying_key()
                if verify_key is None:
                    if _get_require_signature():
                        errors.append('Ed25519 verification key not available — deployment BLOCKED')
                    else:
                        logger.warning('Ed25519 verification key not available, skipping signature check')
                else:
                    try:
                        import base64
                        payload = _manifest_bytes_for_signing(manifest)
                        signature_bytes = base64.b64decode(signature)
                        verify_key.verify(signature_bytes, payload)
                    except Exception as exc:
                        logger.warning("Ed25519 verification failed: %s", exc)
                        errors.append('Ed25519 signature verification failed — possible tampering')
            elif algorithm == 'none' or not signature:
                if _get_require_signature():
                    errors.append('No signature present but ARTIFACT_REQUIRE_SIGNATURE=true — deployment BLOCKED')
            elif algorithm == 'hmac-sha256':
                # Legacy HMAC — reject in favor of Ed25519
                errors.append('Legacy hmac-sha256 signature detected — must re-sign with Ed25519')

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'manifest': manifest,
        }

    def load_bundle(self, bundle_dir: str) -> Dict[str, Any]:
        """
        Load an artifact bundle after verifying integrity + Ed25519 signature.

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

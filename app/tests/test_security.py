import pytest
import json
from app.core.security_scanner import SecurityScanner
from app.core.encryption import EncryptionService


@pytest.fixture
def scanner():
    return SecurityScanner()


@pytest.fixture
def encryption():
    return EncryptionService(master_key="test-master-key-for-unit-tests")


class TestSecurityScanner:
    def test_clean_input(self, scanner):
        threats = scanner.scan_input("hello world")
        assert len(threats) == 0

    def test_sql_injection_or(self, scanner):
        threats = scanner.scan_input("' or '1'='1")
        sql_threats = [t for t in threats if t['type'] == 'sql_injection']
        assert len(sql_threats) > 0
        assert sql_threats[0]['severity'] == 'critical'

    def test_sql_injection_drop_table(self, scanner):
        threats = scanner.scan_input("; drop table users")
        sql_threats = [t for t in threats if t['type'] == 'sql_injection']
        assert len(sql_threats) > 0

    def test_sql_injection_union_select(self, scanner):
        threats = scanner.scan_input("union select * from users")
        sql_threats = [t for t in threats if t['type'] == 'sql_injection']
        assert len(sql_threats) > 0

    def test_xss_script_tag(self, scanner):
        threats = scanner.scan_input("<script>alert('xss')</script>")
        xss_threats = [t for t in threats if t['type'] == 'xss']
        assert len(xss_threats) > 0
        assert xss_threats[0]['severity'] == 'high'

    def test_xss_javascript(self, scanner):
        threats = scanner.scan_input("javascript:alert(1)")
        xss_threats = [t for t in threats if t['type'] == 'xss']
        assert len(xss_threats) > 0

    def test_xss_on_event(self, scanner):
        threats = scanner.scan_input('onload=alert(1)')
        xss_threats = [t for t in threats if t['type'] == 'xss']
        assert len(xss_threats) > 0

    def test_path_traversal(self, scanner):
        threats = scanner.scan_input("../../../etc/passwd")
        path_threats = [t for t in threats if t['type'] == 'path_traversal']
        assert len(path_threats) > 0
        assert path_threats[0]['severity'] == 'high'

    def test_path_traversal_encoded(self, scanner):
        threats = scanner.scan_input("%2e%2e%2f%2e%2e%2f")
        path_threats = [t for t in threats if t['type'] == 'path_traversal']
        assert len(path_threats) > 0

    def test_command_injection_semicolon(self, scanner):
        threats = scanner.scan_input("ls; rm -rf /")
        cmd_threats = [t for t in threats if t['type'] == 'command_injection']
        assert len(cmd_threats) > 0

    def test_command_injection_backtick(self, scanner):
        threats = scanner.scan_input("`whoami`")
        cmd_threats = [t for t in threats if t['type'] == 'command_injection']
        assert len(cmd_threats) > 0

    def test_command_injection_dollar_paren(self, scanner):
        threats = scanner.scan_input("$(whoami)")
        cmd_threats = [t for t in threats if t['type'] == 'command_injection']
        assert len(cmd_threats) > 0

    def test_multiple_threats(self, scanner):
        threats = scanner.scan_input("'; drop table users; <script>alert(1)</script>")
        types = set(t['type'] for t in threats)
        assert 'sql_injection' in types
        assert 'xss' in types

    def test_sanitize_input_removes_html(self, scanner):
        sanitized = scanner.sanitize_input("<script>alert(1)</script>")
        assert "<script>" not in sanitized
        assert "</script>" not in sanitized

    def test_sanitize_input_strips_semicolons(self, scanner):
        sanitized = scanner.sanitize_input("hello; world")
        assert ";" not in sanitized

    def test_validate_file_upload_safe(self, scanner):
        result = scanner.validate_file_upload("data.csv", b"safe content here")
        assert result["safe"] is True

    def test_validate_file_upload_exe(self, scanner):
        result = scanner.validate_file_upload("malware.exe", b"MZ\x90\x00")
        assert result["safe"] is False

    def test_validate_file_upload_bat(self, scanner):
        result = scanner.validate_file_upload("script.bat", b"@echo off")
        assert result["safe"] is False

    def test_validate_file_upload_ps1(self, scanner):
        result = scanner.validate_file_upload("script.ps1", b"Write-Host hello")
        assert result["safe"] is False

    def test_validate_file_upload_too_large(self, scanner):
        result = scanner.validate_file_upload("data.csv", b"x" * (200 * 1024 * 1024))
        assert result["safe"] is False
        assert any('size' in i.get('type', '').lower() or 'large' in str(i).lower() for i in result["issues"])

    def test_validate_file_upload_malware_signature(self, scanner):
        result = scanner.validate_file_upload("file.csv", b"MZ\x90\x00")
        assert result["safe"] is False

    def test_check_sensitive_info_email(self, scanner):
        threats = scanner.scan_input("user@example.com")
        pii_threats = [t for t in threats if t['type'] == 'pii_email']
        assert len(pii_threats) > 0

    def test_check_sensitive_info_phone(self, scanner):
        threats = scanner.scan_input("555-123-4567")
        pii_threats = [t for t in threats if t['type'] == 'pii_phone']
        assert len(pii_threats) > 0

    def test_empty_input(self, scanner):
        threats = scanner.scan_input("")
        assert len(threats) == 0

    def test_normal_text_no_false_positives(self, scanner):
        threats = scanner.scan_input("The quick brown fox jumps over the lazy dog. Price: $100.")
        assert len(threats) == 0


class TestEncryptionService:
    def test_encrypt_decrypt(self, encryption):
        original = "sensitive data here"
        encrypted = encryption.encrypt(original)
        assert encrypted != original
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_dict(self, encryption):
        original = {"key": "value", "number": 42, "nested": {"a": 1}}
        encrypted = encryption.encrypt_dict(original)
        decrypted = encryption.decrypt_dict(encrypted)
        assert decrypted == original

    def test_encrypt_produces_different_output(self, encryption):
        encrypted1 = encryption.encrypt("same input")
        encrypted2 = encryption.encrypt("same input")
        assert encrypted1 != encrypted2

    def test_hash_sensitive_data_deterministic(self, encryption):
        hash1 = encryption.hash_sensitive_data("test data")
        hash2 = encryption.hash_sensitive_data("test data")
        assert hash1 == hash2

    def test_hash_sensitive_data_different_input(self, encryption):
        hash1 = encryption.hash_sensitive_data("data1")
        hash2 = encryption.hash_sensitive_data("data2")
        assert hash1 != hash2

    def test_mask_sensitive_data(self, encryption):
        masked = encryption.mask_sensitive_data("1234567890", visible_chars=4)
        assert masked.endswith("7890")
        assert "*" in masked
        assert len(masked) == 10

    def test_mask_email(self, encryption):
        masked = encryption.mask_email("john.doe@example.com")
        assert "j***" in masked or "jo" in masked
        assert "example.com" in masked
        assert "@" in masked

    def test_mask_phone(self, encryption):
        masked = encryption.mask_phone("5551234567")
        assert masked.endswith("4567")
        assert "***" in masked

    def test_decrypt_invalid_token(self, encryption):
        with pytest.raises(Exception):
            encryption.decrypt("invalid-token")

    def test_different_master_keys(self, encryption):
        enc1 = EncryptionService(master_key="key1")
        enc2 = EncryptionService(master_key="key2")
        encrypted = enc1.encrypt("secret")
        with pytest.raises(Exception):
            enc2.decrypt(encrypted)

    def test_encrypt_empty_string(self, encryption):
        encrypted = encryption.encrypt("")
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == ""

    def test_encrypt_unicode(self, encryption):
        original = "Halo dunia! 你好世界 🌍"
        encrypted = encryption.encrypt(original)
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == original

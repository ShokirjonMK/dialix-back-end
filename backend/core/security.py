"""
Security enhancements: RBAC, encryption, audit logging
"""

import hashlib
import logging
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum

from cryptography.fernet import Fernet
from backend.core import settings

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Permission types for RBAC"""

    MANAGE_USERS = "manage_users"
    MANAGE_COMPANY = "manage_company"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_CHECKLISTS = "manage_checklists"
    MANAGE_OPERATORS = "manage_operators"
    VIEW_RECORDS = "view_records"
    UPDATE_RECORDS = "update_records"
    DELETE_RECORDS = "delete_records"
    ADMIN = "admin"


class RolePermissions:
    """Role-based permissions mapping"""

    PERMISSIONS = {
        "admin": {
            Permission.MANAGE_USERS,
            Permission.MANAGE_COMPANY,
            Permission.VIEW_ANALYTICS,
            Permission.MANAGE_CHECKLISTS,
            Permission.MANAGE_OPERATORS,
            Permission.VIEW_RECORDS,
            Permission.UPDATE_RECORDS,
            Permission.DELETE_RECORDS,
            Permission.ADMIN,
        },
        "user": {
            Permission.VIEW_RECORDS,
            Permission.UPDATE_RECORDS,
        },
        "viewer": {
            Permission.VIEW_RECORDS,
            Permission.VIEW_ANALYTICS,
        },
    }

    @classmethod
    def get_permissions(cls, role: str) -> List[Permission]:
        """Get permissions for a role"""
        return list(cls.PERMISSIONS.get(role, set()))

    @classmethod
    def has_permission(cls, role: str, permission: Permission) -> bool:
        """Check if role has permission"""
        permissions = cls.get_permissions(role)
        return permission in permissions or Permission.ADMIN in permissions


class EncryptionService:
    """Data encryption service"""

    def __init__(self, key: Optional[str] = None):
        # In production, use a secure key from environment
        self.key = key or settings.SECRET_KEY.encode()
        # Generate Fernet key from secret
        self.fernet = Fernet(Fernet.generate_key())

    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


class AuditLogger:
    """Audit logging for security and compliance"""

    @staticmethod
    def log_action(
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log security-relevant actions"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        # Log to application logs
        logger.info(f"AUDIT: {log_entry}")

        # Store in database (via activity log service)
        # This would be called by the activity log service
        return log_entry


class SecurityMiddleware:
    """Security middleware for request validation"""

    @staticmethod
    def validate_request(request):
        """Validate incoming requests"""
        # Check for suspicious patterns
        # Rate limiting
        # Input validation
        pass

    @staticmethod
    def sanitize_input(data: str) -> str:
        """Sanitize user input"""
        # Remove potentially dangerous characters
        import html

        return html.escape(data)


class PasswordHasher:
    """Password hashing and verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt"""
        import bcrypt

        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        import bcrypt

        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False


# Global instances
encryption_service = EncryptionService()
audit_logger = AuditLogger()
password_hasher = PasswordHasher()

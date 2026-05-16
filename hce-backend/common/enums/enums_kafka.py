from enum import Enum


class SeveridadPatologia(str, Enum):
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class TipoCambioPermiso(str, Enum):
    REVOKE_ACCESS = "revoke-access"
    ROLE_CHANGE = "role-change"
    DEACTIVATE_USER = "deactivate-user"

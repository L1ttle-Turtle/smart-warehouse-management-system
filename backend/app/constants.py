RESOURCE_PERMISSIONS = {
    "dashboard.view",
    "delegations.manage",
    "roles.view",
}

ROLE_DELEGATION_ALLOWED_TARGETS = {
    "admin": ["manager", "staff", "accountant", "shipper"],
    "manager": ["staff", "shipper"],
    "accountant": [],
    "staff": [],
    "shipper": [],
}

ROLE_PERMISSION_MAP = {
    "admin": [
        "dashboard.view",
        "delegations.manage",
        "roles.view",
    ],
    "manager": [
        "dashboard.view",
        "delegations.manage",
    ],
    "staff": [
        "dashboard.view",
    ],
    "accountant": [
        "dashboard.view",
    ],
    "shipper": [
        "dashboard.view",
    ],
}

DEFAULT_ROLE_PASSWORDS = {
    "admin": "Admin@123",
    "manager": "Manager@123",
    "staff": "Staff@123",
    "accountant": "Accountant@123",
    "shipper": "Shipper@123",
}

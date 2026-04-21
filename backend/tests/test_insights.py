def test_dashboard_identity_returns_personal_summary(client, auth_headers):
    response = client.get("/dashboard/identity", headers=auth_headers("staff", "Staff@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["profile"]["username"] == "staff"
    assert "management_summary" not in payload
    assert "permission_summary" in payload


def test_dashboard_identity_returns_management_summary_for_admin(client, auth_headers):
    response = client.get("/dashboard/identity", headers=auth_headers("admin", "Admin@123"))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["management_summary"]["total_users"] >= 5
    assert payload["audit_summary"]["total_logs"] >= 1


def test_audit_logs_requires_permission(client, auth_headers):
    response = client.get("/audit-logs", headers=auth_headers("staff", "Staff@123"))

    assert response.status_code == 403


def test_admin_can_filter_audit_logs(client, auth_headers):
    response = client.get(
        "/audit-logs?action=auth.login_success&page=1&page_size=5&sort_by=created_at&sort_order=desc",
        headers=auth_headers("admin", "Admin@123"),
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["page"] == 1
    assert payload["page_size"] == 5
    assert payload["total"] >= 1

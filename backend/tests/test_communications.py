from app.extensions import db
from app.models import AuditLog, InternalTask, Notification, User


def test_manager_can_create_task_and_notify_assignee(client, auth_headers, app):
    with app.app_context():
        staff = User.query.filter_by(username="staff").first()
        staff_id = staff.id

    response = client.post(
        "/tasks",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "title": "Kiem tra don xuat gap",
            "description": "Doi chieu ton kho truoc khi giao hang.",
            "assigned_to_id": staff_id,
            "priority": "high",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["item"]
    assert payload["assigned_to_id"] == staff_id
    assert payload["status"] == "todo"
    assert payload["priority"] == "high"

    staff_tasks = client.get("/tasks", headers=auth_headers("staff", "Staff@123"))
    assert staff_tasks.status_code == 200
    assert any(item["id"] == payload["id"] for item in staff_tasks.get_json()["items"])

    staff_notifications = client.get(
        "/notifications",
        headers=auth_headers("staff", "Staff@123"),
    )
    assert staff_notifications.status_code == 200
    assert any(item["title"].startswith("Công việc mới") for item in staff_notifications.get_json()["items"])

    with app.app_context():
        audit_actions = {
            log.action
            for log in AuditLog.query.filter(
                AuditLog.entity_type == "task",
                AuditLog.entity_id == payload["id"],
            ).all()
        }
        assert audit_actions == {"tasks.created"}


def test_staff_can_update_own_task_status_but_cannot_create_task(client, auth_headers, app):
    with app.app_context():
        task = InternalTask.query.filter_by(task_code="TSK-DEMO-001").first()
        task_id = task.id

    create_response = client.post(
        "/tasks",
        headers=auth_headers("staff", "Staff@123"),
        json={
            "title": "Khong du quyen tao task",
            "assigned_to_id": 1,
        },
    )
    assert create_response.status_code == 403

    update_response = client.patch(
        f"/tasks/{task_id}/status",
        headers=auth_headers("staff", "Staff@123"),
        json={"status": "in_progress"},
    )

    assert update_response.status_code == 200
    assert update_response.get_json()["item"]["status"] == "in_progress"


def test_user_cannot_update_task_assigned_to_someone_else(client, auth_headers, app):
    with app.app_context():
        manager = User.query.filter_by(username="manager").first()
        accountant = User.query.filter_by(username="accountant").first()
        task = InternalTask(
            task_code="TSK-ACCOUNTANT-001",
            title="Doi chieu thanh toan",
            assigned_to_id=accountant.id,
            created_by=manager.id,
            status="todo",
            priority="medium",
        )
        db.session.add(task)
        db.session.commit()
        task_id = task.id

    response = client.patch(
        f"/tasks/{task_id}/status",
        headers=auth_headers("staff", "Staff@123"),
        json={"status": "done"},
    )

    assert response.status_code == 403


def test_broadcast_notification_and_mark_read(client, auth_headers, app):
    with app.app_context():
        accountant = User.query.filter_by(username="accountant").first()
        accountant_id = accountant.id

    response = client.post(
        "/notifications/broadcast",
        headers=auth_headers("manager", "Manager@123"),
        json={
            "title": "Thong bao test",
            "content": "Kiem tra cong no hoa don demo.",
            "type": "payment",
            "receiver_ids": [accountant_id],
        },
    )

    assert response.status_code == 201
    notification = response.get_json()["items"][0]
    assert notification["receiver_id"] == accountant_id
    assert notification["is_read"] is False

    mark_read_response = client.patch(
        f"/notifications/{notification['id']}/read",
        headers=auth_headers("accountant", "Accountant@123"),
    )

    assert mark_read_response.status_code == 200
    assert mark_read_response.get_json()["item"]["is_read"] is True


def test_task_and_notification_permission_matrix(client, auth_headers):
    assert client.get("/tasks", headers=auth_headers("admin", "Admin@123")).status_code == 200
    assert client.get("/tasks", headers=auth_headers("manager", "Manager@123")).status_code == 200
    assert client.get("/tasks", headers=auth_headers("staff", "Staff@123")).status_code == 200
    assert client.get("/notifications", headers=auth_headers("shipper", "Shipper@123")).status_code == 200

    response = client.post(
        "/notifications/broadcast",
        headers=auth_headers("shipper", "Shipper@123"),
        json={
            "title": "Khong du quyen",
            "content": "Shipper khong du quyen broadcast",
            "receiver_ids": [1],
        },
    )

    assert response.status_code == 403

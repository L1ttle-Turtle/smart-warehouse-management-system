from app.extensions import db
from app.models import Conversation, Message, User


def get_user_id(app, username):
    with app.app_context():
        return User.query.filter_by(username=username).first().id


def test_chat_users_excludes_current_user(client, auth_headers):
    response = client.get("/chat/users", headers=auth_headers("manager", "Manager@123"))

    assert response.status_code == 200
    usernames = {item["username"] for item in response.get_json()["items"]}
    assert "manager" not in usernames
    assert {"staff", "accountant", "shipper"}.issubset(usernames)


def test_create_direct_conversation_and_send_message(client, auth_headers, app):
    accountant_id = get_user_id(app, "accountant")

    create_response = client.post(
        "/chat/conversations/direct",
        headers=auth_headers("manager", "Manager@123"),
        json={"user_id": accountant_id},
    )

    assert create_response.status_code == 201
    conversation = create_response.get_json()["item"]
    assert conversation["peer"]["username"] == "accountant"

    duplicate_response = client.post(
        "/chat/conversations/direct",
        headers=auth_headers("manager", "Manager@123"),
        json={"user_id": accountant_id},
    )
    assert duplicate_response.status_code == 200
    assert duplicate_response.get_json()["item"]["id"] == conversation["id"]

    message_response = client.post(
        f"/chat/conversations/{conversation['id']}/messages",
        headers=auth_headers("manager", "Manager@123"),
        json={"content": "  Can doi chieu cong no hoa don demo  "},
    )
    assert message_response.status_code == 201
    assert message_response.get_json()["item"]["content"] == "Can doi chieu cong no hoa don demo"

    messages_response = client.get(
        f"/chat/conversations/{conversation['id']}/messages",
        headers=auth_headers("manager", "Manager@123"),
    )
    assert messages_response.status_code == 200
    assert any(
        item["content"] == "Can doi chieu cong no hoa don demo"
        for item in messages_response.get_json()["items"]
    )

    with app.app_context():
        assert db.session.get(Conversation, conversation["id"]) is not None
        assert Message.query.filter_by(content="Can doi chieu cong no hoa don demo").first() is not None


def test_chat_rejects_self_conversation_and_blank_message(client, auth_headers, app):
    manager_id = get_user_id(app, "manager")

    self_response = client.post(
        "/chat/conversations/direct",
        headers=auth_headers("manager", "Manager@123"),
        json={"user_id": manager_id},
    )
    assert self_response.status_code == 400

    staff_id = get_user_id(app, "staff")
    create_response = client.post(
        "/chat/conversations/direct",
        headers=auth_headers("manager", "Manager@123"),
        json={"user_id": staff_id},
    )
    conversation_id = create_response.get_json()["item"]["id"]

    blank_response = client.post(
        f"/chat/conversations/{conversation_id}/messages",
        headers=auth_headers("manager", "Manager@123"),
        json={"content": "   "},
    )
    assert blank_response.status_code == 400


def test_non_participant_cannot_read_or_send_message(client, auth_headers, app):
    accountant_id = get_user_id(app, "accountant")
    create_response = client.post(
        "/chat/conversations/direct",
        headers=auth_headers("manager", "Manager@123"),
        json={"user_id": accountant_id},
    )
    conversation_id = create_response.get_json()["item"]["id"]

    read_response = client.get(
        f"/chat/conversations/{conversation_id}/messages",
        headers=auth_headers("shipper", "Shipper@123"),
    )
    assert read_response.status_code == 403

    send_response = client.post(
        f"/chat/conversations/{conversation_id}/messages",
        headers=auth_headers("shipper", "Shipper@123"),
        json={"content": "Khong thuoc cuoc tro chuyen"},
    )
    assert send_response.status_code == 403

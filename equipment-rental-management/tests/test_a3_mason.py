"""A3 tests (Member A: Mason).

Overdue-reminder success path (stub + mock) and coverage-directed tests
for checkout_error (line 27) and return_equipment (line 66) in
app/routes/rentals.py.
"""
from datetime import date, timedelta
from unittest.mock import patch

from app import store

RENTER_EMAIL = "sam@example.com"


def make_overdue_rental(client, days_late=3):
    """Create a renter, an item and a rental, then move its due date into the past."""
    item = client.post(
        "/equipment", json={"name": "Kayak", "category": "Water", "total_units": 2}
    ).get_json()
    renter = client.post(
        "/renters", json={"name": "Sam Lee", "email": RENTER_EMAIL}
    ).get_json()
    rental = client.post(
        "/rentals", json={"equipment_id": item["id"], "renter_id": renter["id"]}
    ).get_json()
    store.rentals[rental["id"]].due_date = date.today() - timedelta(days=days_late)
    return rental["id"]


# ---- Notification: success path -------------------------------------------

def test_overdue_reminder_success_with_stub(client, monkeypatch):
    """Stub returns True: response and stored rental both show the reminder was sent."""
    monkeypatch.setattr(
        "app.routes.rentals.send_notification",
        lambda recipient, subject, message: True,
    )
    rental_id = make_overdue_rental(client)

    resp = client.post(f"/rentals/{rental_id}/reminder")

    assert resp.status_code == 200
    assert resp.get_json() == {"rental_id": rental_id, "reminder_sent": True}
    assert store.rentals[rental_id].reminder_sent is True
    listed = client.get("/rentals").get_json()[0]
    assert listed["reminder_sent"] is True


def test_overdue_reminder_sends_expected_recipient_subject_and_message(client):
    """Mock verifies the exact recipient, subject and message passed to the service."""
    rental_id = make_overdue_rental(client, days_late=3)
    due = store.rentals[rental_id].due_date

    with patch("app.routes.rentals.send_notification", return_value=True) as mock_send:
        resp = client.post(f"/rentals/{rental_id}/reminder")

    assert resp.status_code == 200
    assert store.rentals[rental_id].reminder_sent is True
    mock_send.assert_called_once_with(
        RENTER_EMAIL,
        "Overdue rental reminder",
        f"Your rental of Kayak was due on {due} and is 3 day(s) overdue. "
        "Please return it.",
    )


# ---- Coverage-directed tests ----------------------------------------------

def test_checkout_nonexistent_equipment_returns_404(client):
    """rentals.py line 27: unknown equipment is refused and no rental is created."""
    renter = client.post(
        "/renters", json={"name": "Sam Lee", "email": RENTER_EMAIL}
    ).get_json()

    resp = client.post("/rentals", json={"equipment_id": 9999, "renter_id": renter["id"]})

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Equipment not found"
    assert store.rentals == {}


def test_return_nonexistent_rental_returns_404(client):
    """rentals.py line 66: returning an unknown rental is refused and changes nothing."""
    item = client.post(
        "/equipment", json={"name": "Kayak", "category": "Water", "total_units": 2}
    ).get_json()

    resp = client.put("/rentals/9999/return")

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Rental not found"
    assert client.get(f"/equipment/{item['id']}").get_json()["available_units"] == 2

def test_reminder_for_nonexistent_rental_returns_404_and_sends_nothing(client):
    """Reminder for an unknown rental is refused and no notification is sent."""
    with patch("app.routes.rentals.send_notification") as mock_send:
        resp = client.post("/rentals/9999/reminder")

    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Rental not found"
    mock_send.assert_not_called()
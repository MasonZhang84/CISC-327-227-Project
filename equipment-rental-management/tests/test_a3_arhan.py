"""A3 tests (Member B: Arhan).

Overdue-reminder failure and non-trigger paths (stub + mock), and
coverage-directed tests for extend_rental (app/routes/rentals.py) and
home (app/routes/views.py).
"""
from datetime import date, timedelta
from unittest.mock import patch

from app import store

# Creates equipment, a renter and a rental through the API, then sets the due date. It takes the test client and how many days ago the rental was due (0 = due today, negative = not due yet) as parameters.
def makeRentalDue(client, daysAgo):
    item = client.post(
        "/equipment", json={"name": "Drill", "category": "Power", "total_units": 2}
    ).get_json()
    renter = client.post(
        "/renters", json={"name": "Alice", "email": "alice@example.com"}
    ).get_json()
    rental = client.post(
        "/rentals", json={"equipment_id": item["id"], "renter_id": renter["id"]}
    ).get_json()
    store.rentals[rental["id"]].due_date = date.today() - timedelta(days=daysAgo)
    return rental["id"]


# Overdue reminder: failure path (stub)

# Tests that a failed notification is reported and not recorded as sent, while the rental itself is unchanged.
def testOverdueReminderFailureIsReportedAndNotRecorded(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.rentals.send_notification",
        lambda recipient, subject, message: False,
    )
    rentalId = makeRentalDue(client, daysAgo=3)

    response = client.post(f"/rentals/{rentalId}/reminder")

    assert response.status_code == 200
    assert response.get_json() == {"rental_id": rentalId, "reminder_sent": False}
    stored = client.get("/rentals").get_json()[0]
    assert stored["reminder_sent"] is False
    assert stored["return_date"] is None


# Overdue reminder: non-trigger paths (mock)

# Tests that no reminder is sent for a rental that is not yet due.
def testReminderNotSentWhenRentalIsNotOverdue(client):
    rentalId = makeRentalDue(client, daysAgo=-3)

    with patch("app.routes.rentals.send_notification") as mockSend:
        response = client.post(f"/rentals/{rentalId}/reminder")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Rental is not overdue"}
    assert store.rentals[rentalId].reminder_sent is False
    mockSend.assert_not_called()

# Tests the boundary: a rental due today is not overdue yet, so no reminder is sent.
def testReminderNotSentWhenRentalIsDueToday(client):
    rentalId = makeRentalDue(client, daysAgo=0)

    with patch("app.routes.rentals.send_notification") as mockSend:
        response = client.post(f"/rentals/{rentalId}/reminder")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Rental is not overdue"}
    assert store.rentals[rentalId].reminder_sent is False
    mockSend.assert_not_called()

# Tests that no reminder is sent once an overdue rental has been returned.
def testReminderNotSentForReturnedRental(client):
    rentalId = makeRentalDue(client, daysAgo=3)
    client.put(f"/rentals/{rentalId}/return")

    with patch("app.routes.rentals.send_notification") as mockSend:
        response = client.post(f"/rentals/{rentalId}/reminder")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Rental already returned"}
    assert store.rentals[rentalId].reminder_sent is False
    mockSend.assert_not_called()


# Coverage-directed: extend_rental (app/routes/rentals.py)

# Tests that extending a rental that does not exist returns a 404 error and changes no other rental.
def testExtendNonexistentRentalReturns404(client):
    rentalId = makeRentalDue(client, daysAgo=-7)
    dueDate = client.get("/rentals").get_json()[0]["due_date"]

    response = client.put("/rentals/999/extend", json={"days": 1})

    assert response.status_code == 404
    assert response.get_json() == {"error": "Rental not found"}
    stored = client.get("/rentals").get_json()
    assert len(stored) == 1
    assert stored[0]["id"] == rentalId
    assert stored[0]["due_date"] == dueDate


# Coverage-directed: home (app/routes/views.py)

# Tests that the home page loads and links to the equipment, renters and rentals pages.
def testHomePageLinksToEachManagementPage(client):
    response = client.get("/")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Equipment Rental Management" in page
    assert 'href="/ui/equipment"' in page
    assert 'href="/ui/renters"' in page
    assert 'href="/ui/rentals"' in page

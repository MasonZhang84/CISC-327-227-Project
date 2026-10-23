from datetime import date

# Creates a renter through the API and returns it. It takes the test client, the name and the email as parameters.
def makeRenter(client, name="Alice", email="alice@example.com"):
    response = client.post("/renters", json={"name": name, "email": email})
    assert response.status_code == 201
    return response.get_json()

# Creates a piece of equipment through the API and returns it. It takes the test client, the name, the category and the number of units as parameters.
def makeEquipment(client, name="Drill", category="Power", totalUnits=2):
    response = client.post(
        "/equipment",
        json={"name": name, "category": category, "total_units": totalUnits},
    )
    assert response.status_code == 201
    return response.get_json()

# Checks out equipment for a renter and returns the new rental. It takes the test client, the equipment id, the renter id and any extra fields (such as deposit_amount) as parameters.
def checkout(client, equipmentId, renterId, **extra):
    response = client.post(
        "/rentals",
        json={"equipment_id": equipmentId, "renter_id": renterId, **extra},
    )
    assert response.status_code == 201
    return response.get_json()


# List renters (GET /renters, Renters page)

# Tests that the renter list starts empty.
def testListRentersReturnsEmptyListInitially(client):
    response = client.get("/renters")
    assert response.status_code == 200
    assert response.get_json() == []

# Tests that each created renter appears once in the list with its stored fields.
def testListRentersReturnsEveryCreatedRenter(client):
    alice = makeRenter(client, "Alice", "alice@example.com")
    bob = makeRenter(client, "Bob", "bob@example.com")

    renters = client.get("/renters").get_json()

    assert len(renters) == 2
    rentersById = {renter["id"]: renter for renter in renters}
    assert rentersById[alice["id"]]["name"] == "Alice"
    assert rentersById[bob["id"]]["email"] == "bob@example.com"
    assert alice["id"] != bob["id"]

# Tests that a renter added through the UI form is shown in the Renters page table.
def testRentersPageShowsCreatedRenter(client):
    response = client.post(
        "/ui/renters", data={"name": "Carol", "email": "carol@example.com"}
    )
    assert response.status_code == 302

    page = client.get("/ui/renters").get_data(as_text=True)
    assert "Carol" in page
    assert "carol@example.com" in page


# View one renter (GET /renters/<id>)

# Tests that getting a renter returns the same fields it was created with.
def testGetRenterReturnsStoredFields(client):
    created = makeRenter(client, "Alice", "alice@example.com")

    response = client.get(f"/renters/{created['id']}")

    assert response.status_code == 200
    renter = response.get_json()
    assert renter == created
    assert renter["membership_date"] == date.today().isoformat()

# Tests that getting a renter that does not exist returns a 404 error.
def testGetNonexistentRenterReturns404(client):
    response = client.get("/renters/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Renter not found"}


# Update renter (PUT /renters/<id>)

# Tests that updated fields are returned and are still there on a later GET.
def testUpdateRenterPersistsNewValues(client):
    renter = makeRenter(client, "Alice", "alice@example.com")

    response = client.put(
        f"/renters/{renter['id']}",
        json={"name": "Alice Smith", "email": "asmith@example.com"},
    )
    assert response.status_code == 200
    assert response.get_json()["name"] == "Alice Smith"

    stored = client.get(f"/renters/{renter['id']}").get_json()
    assert stored["name"] == "Alice Smith"
    assert stored["email"] == "asmith@example.com"

# Tests that updating only the email keeps the other fields the same.
def testPartialUpdateRenterKeepsOtherFields(client):
    renter = makeRenter(client, "Alice", "alice@example.com")

    client.put(f"/renters/{renter['id']}", json={"email": "new@example.com"})

    stored = client.get(f"/renters/{renter['id']}").get_json()
    assert stored["email"] == "new@example.com"
    assert stored["name"] == "Alice"
    assert stored["membership_date"] == renter["membership_date"]

# Tests that an update with an empty body does not change the renter.
def testUpdateRenterWithEmptyBodyChangesNothing(client):
    renter = makeRenter(client)

    response = client.put(f"/renters/{renter['id']}", json={})

    assert response.status_code == 200
    assert client.get(f"/renters/{renter['id']}").get_json() == renter

# Tests that updating a renter that does not exist returns 404 and creates nothing.
def testUpdateNonexistentRenterReturns404(client):
    response = client.put("/renters/999", json={"name": "Nobody"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Renter not found"}
    assert client.get("/renters").get_json() == []


# Delete renter (DELETE /renters/<id>, Delete button)

# Tests that deleting a renter removes only that renter.
def testDeleteRenterRemovesOnlyThatRenter(client):
    alice = makeRenter(client, "Alice", "alice@example.com")
    bob = makeRenter(client, "Bob", "bob@example.com")

    response = client.delete(f"/renters/{alice['id']}")

    assert response.status_code == 204
    assert client.get(f"/renters/{alice['id']}").status_code == 404
    assert client.get("/renters").get_json() == [bob]

# Tests that deleting the same renter twice returns 404 the second time.
def testDeleteRenterTwiceReturns404SecondTime(client):
    renter = makeRenter(client)

    assert client.delete(f"/renters/{renter['id']}").status_code == 204
    secondResponse = client.delete(f"/renters/{renter['id']}")

    assert secondResponse.status_code == 404
    assert secondResponse.get_json() == {"error": "Renter not found"}

# Tests that deleting a renter that does not exist returns a 404 error.
def testDeleteNonexistentRenterReturns404(client):
    response = client.delete("/renters/999")
    assert response.status_code == 404

# Tests that the Delete button on the Renters page removes the renter.
def testRentersPageDeleteButtonRemovesRenter(client):
    renter = makeRenter(client, "Dave", "dave@example.com")

    response = client.post(f"/ui/renters/{renter['id']}/delete")

    assert response.status_code == 302
    assert client.get("/renters").get_json() == []

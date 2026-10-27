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
    assert "Dave" not in client.get("/ui/renters").get_data(as_text=True)


# Update equipment (PUT /equipment/<id>)

# Tests that updated equipment fields are still there on a later GET.
def testUpdateEquipmentPersistsNewValues(client):
    item = makeEquipment(client, "Drill", "Power", totalUnits=2)

    response = client.put(
        f"/equipment/{item['id']}",
        json={"name": "Hammer Drill", "category": "Tools", "total_units": 4},
    )
    assert response.status_code == 200

    stored = client.get(f"/equipment/{item['id']}").get_json()
    assert stored["name"] == "Hammer Drill"
    assert stored["category"] == "Tools"
    assert stored["total_units"] == 4

# Tests that updating only the name keeps the other equipment fields the same.
def testPartialUpdateEquipmentKeepsOtherFields(client):
    item = makeEquipment(client, "Drill", "Power", totalUnits=2)

    client.put(f"/equipment/{item['id']}", json={"name": "Cordless Drill"})

    stored = client.get(f"/equipment/{item['id']}").get_json()
    assert stored == {**item, "name": "Cordless Drill"}

# Tests that updating equipment that does not exist returns 404 and creates nothing.
def testUpdateNonexistentEquipmentReturns404(client):
    response = client.put("/equipment/999", json={"name": "Ghost"})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}
    assert client.get("/equipment").get_json() == []


# Set equipment status (PATCH /equipment/<id>/status)

# Tests that marking equipment out of service is stored and shown on later reads (R10).
def testMarkEquipmentOutOfServicePersists(client):
    item = makeEquipment(client)

    response = client.patch(
        f"/equipment/{item['id']}/status", json={"is_available": False}
    )
    assert response.status_code == 200
    assert response.get_json()["is_available"] is False

    assert client.get(f"/equipment/{item['id']}").get_json()["is_available"] is False
    availability = client.get(f"/equipment/{item['id']}/availability").get_json()
    assert availability["is_available"] is False

# Tests that equipment can be put back into service after being taken out.
def testEquipmentCanBeReturnedToService(client):
    item = makeEquipment(client)
    client.patch(f"/equipment/{item['id']}/status", json={"is_available": False})

    client.patch(f"/equipment/{item['id']}/status", json={"is_available": True})

    assert client.get(f"/equipment/{item['id']}").get_json()["is_available"] is True

# Tests that changing the status does not change the unit counts.
def testStatusChangeDoesNotAlterUnitCounts(client):
    item = makeEquipment(client, totalUnits=3)

    client.patch(f"/equipment/{item['id']}/status", json={"is_available": False})

    stored = client.get(f"/equipment/{item['id']}").get_json()
    assert stored["total_units"] == 3
    assert stored["available_units"] == 3

# Tests that setting the status of equipment that does not exist returns a 404 error.
def testSetStatusOnNonexistentEquipmentReturns404(client):
    response = client.patch("/equipment/999/status", json={"is_available": False})
    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}

# Tests that gear marked out of service cannot be rented (R10, R11).
# Expected: checkout is rejected (400) and no units are deducted.
# Known defect: checkout_equipment() never checks is_available.
def testOutOfServiceEquipmentCannotBeCheckedOut(client):
    item = makeEquipment(client, totalUnits=2)
    renter = makeRenter(client)
    client.patch(f"/equipment/{item['id']}/status", json={"is_available": False})

    response = client.post(
        "/rentals", json={"equipment_id": item["id"], "renter_id": renter["id"]}
    )

    assert response.status_code == 400
    assert client.get(f"/equipment/{item['id']}/availability").get_json()["available_units"] == 2
    assert client.get("/rentals").get_json() == []


# View equipment availability (GET /equipment/<id>/availability)

# Tests that availability drops by one per checkout and is restored on return.
def testAvailabilityTracksCheckoutAndReturn(client):
    item = makeEquipment(client, totalUnits=2)
    renter = makeRenter(client)
    availabilityUrl = f"/equipment/{item['id']}/availability"

    rental = checkout(client, item["id"], renter["id"])
    assert client.get(availabilityUrl).get_json()["available_units"] == 1

    client.put(f"/rentals/{rental['id']}/return")
    assert client.get(availabilityUrl).get_json() == {
        "equipment_id": item["id"],
        "is_available": True,
        "available_units": 2,
        "total_units": 2,
    }

# Tests that availability reaches zero when every unit is rented.
def testAvailabilityReachesZeroWhenAllUnitsRented(client):
    item = makeEquipment(client, totalUnits=2)
    renter = makeRenter(client)

    checkout(client, item["id"], renter["id"])
    checkout(client, item["id"], renter["id"])

    availability = client.get(f"/equipment/{item['id']}/availability").get_json()
    assert availability["available_units"] == 0
    assert availability["total_units"] == 2

# Tests that the clerk can tell whether gear is available (R11).
# Expected: once every unit is rented, a further checkout is refused and available_units stays at 0.
# Known defect: checkout does not check stock, so available_units becomes -1.
def testAvailabilityNeverGoesBelowZero(client):
    item = makeEquipment(client, totalUnits=1)
    renter = makeRenter(client)
    checkout(client, item["id"], renter["id"])

    response = client.post(
        "/rentals", json={"equipment_id": item["id"], "renter_id": renter["id"]}
    )

    assert response.status_code == 400
    assert client.get(f"/equipment/{item['id']}/availability").get_json()["available_units"] == 0

# Tests that the availability of equipment that does not exist returns a 404 error.
def testAvailabilityOfNonexistentEquipmentReturns404(client):
    response = client.get("/equipment/999/availability")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}


# Look up rentals (GET /rentals?renter_id=&equipment_id=, Rentals page)

# Creates two renters who each rent the other's numbered equipment and returns the rentals.
# Renter 1 rents equipment 2 and renter 2 rents equipment 1, so a filter that confuses
# renter_id with equipment_id returns the wrong rental. It takes the test client as a parameter.
def makeCrossedRentals(client):
    drill = makeEquipment(client, "Drill")
    saw = makeEquipment(client, "Saw")
    alice = makeRenter(client, "Alice", "alice@example.com")
    bob = makeRenter(client, "Bob", "bob@example.com")
    aliceRental = checkout(client, saw["id"], alice["id"])
    checkout(client, drill["id"], bob["id"])
    return {"alice": alice, "saw": saw, "alice_rental": aliceRental}

# Tests that each rental records the renter, the equipment, and a due date 7 days out (R4).
def testListRentalsReturnsEveryRentalWithDueDate(client):
    makeCrossedRentals(client)

    rentals = client.get("/rentals").get_json()

    assert len(rentals) == 2
    for rental in rentals:
        rentalDate = date.fromisoformat(rental["rental_date"])
        dueDate = date.fromisoformat(rental["due_date"])
        assert rentalDate == date.today()
        assert (dueDate - rentalDate).days == 7
        assert rental["return_date"] is None

# Tests that looking up rentals by equipment id returns only that equipment's rentals.
def testLookupRentalsByEquipmentId(client):
    rentals = makeCrossedRentals(client)

    response = client.get(f"/rentals?equipment_id={rentals['saw']['id']}")

    assert response.status_code == 200
    assert response.get_json() == [rentals["alice_rental"]]

# Tests that the clerk can look up rental information for a renter (R7).
# Expected: only Alice's rental (equipment = Saw) is returned.
# Known defect: the renter_id filter compares against equipment_id, so it returns Bob's rental of equipment #1 instead.
def testLookupRentalsByRenterId(client):
    rentals = makeCrossedRentals(client)

    response = client.get(f"/rentals?renter_id={rentals['alice']['id']}")

    assert response.status_code == 200
    assert response.get_json() == [rentals["alice_rental"]]

# Tests that a lookup with no matching rentals returns an empty list.
def testLookupRentalsWithNoMatchesReturnsEmptyList(client):
    makeCrossedRentals(client)

    response = client.get("/rentals?equipment_id=999")

    assert response.status_code == 200
    assert response.get_json() == []

# Tests that returned rentals stay in the equipment's rental history (R6).
def testLookupKeepsReturnedRentalInHistory(client):
    item = makeEquipment(client)
    renter = makeRenter(client)
    firstRental = checkout(client, item["id"], renter["id"])
    client.put(f"/rentals/{firstRental['id']}/return")
    secondRental = checkout(client, item["id"], renter["id"])

    history = client.get(f"/rentals?equipment_id={item['id']}").get_json()

    assert [rental["id"] for rental in history] == [firstRental["id"], secondRental["id"]]
    assert history[0]["return_date"] == date.today().isoformat()
    assert history[1]["return_date"] is None

# Tests that deleting a piece of equipment does not erase its rental history (R6).
def testLookupKeepsHistoryAfterEquipmentIsDeleted(client):
    item = makeEquipment(client)
    renter = makeRenter(client)
    rental = checkout(client, item["id"], renter["id"])

    client.delete(f"/equipment/{item['id']}")

    assert client.get(f"/rentals?equipment_id={item['id']}").get_json() == [rental]

# Tests that the Rentals page lists a rental and only shows its Return button until it is returned.
def testRentalsPageListsRentalAndReturnButton(client):
    item = makeEquipment(client)
    renter = makeRenter(client)
    rental = checkout(client, item["id"], renter["id"])

    page = client.get("/ui/rentals").get_data(as_text=True)
    assert rental["due_date"] in page
    assert f"/ui/rentals/{rental['id']}/return" in page

    client.put(f"/rentals/{rental['id']}/return")
    page = client.get("/ui/rentals").get_data(as_text=True)
    assert f"/ui/rentals/{rental['id']}/return" not in page


# Release a deposit (PUT /rentals/<id>/deposit/release)

# Creates a rental with a deposit, returns the equipment, and returns the rental. It takes the test client and the deposit amount as parameters.
def makeReturnedRentalWithDeposit(client, depositAmount=100.0):
    item = makeEquipment(client)
    renter = makeRenter(client)
    rental = checkout(client, item["id"], renter["id"], deposit_amount=depositAmount)
    client.put(f"/rentals/{rental['id']}/return")
    return rental

# Tests that the deposit amount is stored on the rental and starts unreleased (R13).
def testCheckoutRecordsDepositAsHeld(client):
    item = makeEquipment(client)
    renter = makeRenter(client)
    rental = checkout(client, item["id"], renter["id"], deposit_amount=75.5)

    stored = client.get(f"/rentals?equipment_id={item['id']}").get_json()[0]

    assert stored["id"] == rental["id"]
    assert stored["deposit_amount"] == 75.5
    assert stored["deposit_released"] is False

# Tests that releasing a deposit after the return reports it as released.
def testReleaseDepositAfterReturnReportsReleased(client):
    rental = makeReturnedRentalWithDeposit(client)

    response = client.put(f"/rentals/{rental['id']}/deposit/release")

    assert response.status_code == 200
    assert response.get_json() == {"rental_id": rental["id"], "deposit_released": True}

# Tests that once released, the rental record shows the deposit as released (R13).
# Expected: a later lookup shows deposit_released == True.
# Known defect: release_deposit() returns True in its response but never sets rental.deposit_released, so the stored value stays False.
def testReleaseDepositIsPersistedOnRental(client):
    rental = makeReturnedRentalWithDeposit(client)

    client.put(f"/rentals/{rental['id']}/deposit/release")

    stored = client.get(f"/rentals?equipment_id={rental['equipment_id']}").get_json()[0]
    assert stored["deposit_released"] is True

# Tests that a deposit cannot be released before the equipment is returned.
def testReleaseDepositBeforeReturnIsRejected(client):
    item = makeEquipment(client)
    renter = makeRenter(client)
    rental = checkout(client, item["id"], renter["id"], deposit_amount=100.0)

    response = client.put(f"/rentals/{rental['id']}/deposit/release")

    assert response.status_code == 400
    assert response.get_json() == {"error": "Equipment has not been returned yet"}
    stored = client.get(f"/rentals?equipment_id={item['id']}").get_json()[0]
    assert stored["deposit_released"] is False

# Tests that releasing the deposit of a rental that does not exist returns a 404 error.
def testReleaseDepositForNonexistentRentalReturns404(client):
    response = client.put("/rentals/999/deposit/release")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Rental not found"}
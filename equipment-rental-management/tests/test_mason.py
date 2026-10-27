"""
Test includes:
    Add equipment	
    List equipment
    View one equipment
    Delete equipment
    Add renter
    Check out equipment
    Return equipment
    Extend a rental
"""
import re
from datetime import date, timedelta

import pytest

from app import store

TODAY = date.today().isoformat()
DUE = (date.today() + timedelta(days=7)).isoformat()

# helpers
def add_equipment(client, name="Kayak", category="Water", total_units=1):
    r = client.post("/equipment", json={"name": name, "category": category, "total_units": total_units})
    return r.get_json()


def add_renter(client, name="Sam Lee", email="sam@example.com"):
    return client.post("/renters", json={"name": name, "email": email}).get_json()


def check_out(client, equipment_id, renter_id):
    return client.post("/rentals", json={"equipment_id": equipment_id, "renter_id": renter_id})


def units(client, equipment_id):
    return client.get(f"/equipment/{equipment_id}").get_json()["available_units"]


def rent(client, total_units=2):
    item = add_equipment(client, "Tent", total_units=total_units)
    return check_out(client, item["id"], add_renter(client)["id"]).get_json()


def rows(client, path):
    html = client.get(path).get_data(as_text=True)
    cells = [re.findall(r"<td>(.*?)</td>", tr, re.S) for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S)]
    return [[" ".join(re.sub(r"<.*?>", "", c).split()) for c in row] for row in cells if row]


#Add equipment (POST /equipment, Add Equipment form)

def test_add_equipment_returns_201_and_expected_fields(client):
    r = client.post("/equipment", json={"name": "Ladder", "category": "Climbing", "total_units": 3})

    assert r.status_code == 201
    assert r.get_json() == {"id": 1, "name": "Ladder", "category": "Climbing",
                            "total_units": 3, "available_units": 3, "is_available": True}


def test_added_equipment_can_be_fetched_and_is_in_the_list(client):
    item = add_equipment(client, total_units=2)

    assert client.get(f"/equipment/{item['id']}").get_json() == item
    assert client.get("/equipment").get_json() == [item]


@pytest.mark.parametrize("missing", ["name", "category"])
def test_add_equipment_missing_a_required_field_is_an_error_and_adds_nothing(client, missing):
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    payload = {"name": "Kayak", "category": "Water", "total_units": 1}
    del payload[missing]

    assert client.post("/equipment", json=payload).status_code >= 400
    assert client.get("/equipment").get_json() == []


def test_add_equipment_form_adds_the_item_to_the_equipment_page(client):
    r = client.post("/ui/equipment", data={"name": "Tent", "category": "Camping", "total_units": "3"})

    assert r.status_code == 302
    assert [row[:5] for row in rows(client, "/ui/equipment")] == [["1", "Tent", "Camping", "3", "3"]]


#List equipment (GET /equipment, Equipment page)

def test_list_equipment_returns_item_with_all_fields(client):
    kayak = add_equipment(client, "Kayak", "Water", 2)
    tent = add_equipment(client, "Tent", "Camping", 4)

    assert client.get("/equipment").get_json() == [kayak, tent]


def test_checkout_only_changes_the_rented_item_in_the_list(client):
    """R11"""
    kayak = add_equipment(client, "Kayak", total_units=2)
    add_equipment(client, "Tent", total_units=2)
    check_out(client, kayak["id"], add_renter(client)["id"])

    counts = {i["name"]: i["available_units"] for i in client.get("/equipment").get_json()}
    assert counts == {"Kayak": 1, "Tent": 2}


def test_list_shows_fully_rented_item_as_not_available(client):
    """R10, R11: with 0 units left the item must not be listed as available."""
    item = add_equipment(client, total_units=1)
    check_out(client, item["id"], add_renter(client)["id"])

    listed = client.get("/equipment").get_json()[0]
    assert listed["available_units"] == 0
    assert listed["is_available"] is False


def test_equipment_page_shows_out_of_service_item_as_out_of_service(client):
    """R10: the Equipment page must show that an item is out of service."""
    item = add_equipment(client)
    client.patch(f"/equipment/{item['id']}/status", json={"is_available": False})

    html = client.get("/ui/equipment").get_data(as_text=True).lower()
    assert any(w in html for w in ("out of service", "unavailable", "not available"))


#View one equipment item (GET /equipment/<id>)

def test_view_equipment_returns_expected_fields(client):
    add_equipment(client, "Kayak")
    ladder = add_equipment(client, "Ladder", "Climbing", 3)

    r = client.get(f"/equipment/{ladder['id']}")

    assert r.status_code == 200
    assert r.get_json() == ladder


def test_view_equipment_shows_one_fewer_available_unit_after_checkout(client):
    item = add_equipment(client, total_units=3)
    check_out(client, item["id"], add_renter(client)["id"])

    assert units(client, item["id"]) == 2


def test_view_equipment_that_does_not_exist_returns_404_with_message(client):
    r = client.get("/equipment/999")

    assert r.status_code == 404
    assert r.get_json() == {"error": "Equipment not found"}


def test_view_equipment_after_it_was_deleted_returns_404(client):
    item = add_equipment(client)
    client.delete(f"/equipment/{item['id']}")

    assert client.get(f"/equipment/{item['id']}").status_code == 404


#Delete equipment (DELETE /equipment/<id>, Delete button)

def test_delete_equipment_returns_204_and_removes_the_item(client):
    item = add_equipment(client)

    r = client.delete(f"/equipment/{item['id']}")

    assert r.status_code == 204
    assert client.get("/equipment").get_json() == []


def test_delete_equipment_keeps_the_other_items(client):
    kayak, tent, ladder = (add_equipment(client, n) for n in ("Kayak", "Tent", "Ladder"))
    client.delete(f"/equipment/{tent['id']}")

    assert client.get("/equipment").get_json() == [kayak, ladder]


def test_delete_equipment_that_does_not_exist_returns_404_and_changes_nothing(client):
    item = add_equipment(client)

    r = client.delete("/equipment/999")

    assert r.status_code == 404
    assert client.get("/equipment").get_json() == [item]


def test_delete_button_removes_the_item_from_the_equipment_page(client):
    client.post("/ui/equipment", data={"name": "Kayak", "category": "Water", "total_units": "2"})
    client.post("/ui/equipment", data={"name": "Tent", "category": "Camping", "total_units": "3"})

    r = client.post("/ui/equipment/1/delete")

    assert r.status_code == 302
    assert [row[:5] for row in rows(client, "/ui/equipment")] == [["2", "Tent", "Camping", "3", "3"]]


#Add renter (POST /renters, Add a Renter form)

def test_add_renter_returns_201_and_expected_fields(client):
    r = client.post("/renters", json={"name": "Sam Lee", "email": "sam@example.com"})

    assert r.status_code == 201
    assert r.get_json() == {"id": 1, "name": "Sam Lee", "email": "sam@example.com", "membership_date": TODAY}
    assert client.get("/renters/1").get_json() == r.get_json()


@pytest.mark.parametrize("missing", ["name", "email"])
def test_add_renter_missing_a_required_field_is_an_error_and_adds_nothing(client, missing):
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    payload = {"name": "Sam Lee", "email": "sam@example.com"}
    del payload[missing]

    assert client.post("/renters", json=payload).status_code >= 400
    assert client.get("/renters").get_json() == []


def test_add_a_renter_form_adds_the_renter_to_the_renters_page(client):
    r = client.post("/ui/renters", data={"name": "Sam Lee", "email": "sam@example.com"})

    assert r.status_code == 302
    assert [row[:4] for row in rows(client, "/ui/renters")] == [["1", "Sam Lee", "sam@example.com", TODAY]]


def test_added_renter_keeps_the_phone_number(client):
    """R1, R2, R23: a phone number sent with a renter must be stored and returned."""
    r = client.post("/renters", json={"name": "Sam Lee", "email": "sam@example.com", "phone": "613-555-0101"})
    renter = r.get_json()

    assert renter.get("phone") == "613-555-0101"
    assert client.get(f"/renters/{renter['id']}").get_json().get("phone") == "613-555-0101"


#Check out equipment (POST /rentals, Check Out Equipment form)

def test_checkout_returns_201_and_the_rental_details(client):
    """R4, R21"""
    item = add_equipment(client, total_units=2)
    add_renter(client, "Pat Doe", "pat@example.com")
    renter = add_renter(client)

    r = check_out(client, item["id"], renter["id"])

    assert r.status_code == 201
    rental = r.get_json()
    assert (rental["id"], rental["equipment_id"], rental["renter_id"]) == (1, item["id"], renter["id"])
    assert (rental["rental_date"], rental["due_date"], rental["return_date"]) == (TODAY, DUE, None)
    assert client.get("/rentals").get_json() == [rental]
    assert units(client, item["id"]) == 1


def test_checkout_for_an_unknown_renter_is_refused(client):
    """R1, R2: the renter must exist before equipment is rented."""
    item = add_equipment(client)

    assert check_out(client, item["id"], 999).status_code >= 400
    assert client.get("/rentals").get_json() == []


def test_checkout_of_out_of_service_equipment_is_refused(client):
    """R10, R11"""
    item = add_equipment(client)
    renter = add_renter(client)
    client.patch(f"/equipment/{item['id']}/status", json={"is_available": False})

    assert check_out(client, item["id"], renter["id"]).status_code >= 400
    assert client.get("/rentals").get_json() == []


def test_checkout_fails_when_no_units_are_available(client):
    """R11"""
    item = add_equipment(client, total_units=1)
    renter = add_renter(client)
    check_out(client, item["id"], renter["id"])

    assert check_out(client, item["id"], renter["id"]).status_code >= 400
    assert units(client, item["id"]) == 0


def test_failed_checkout_does_not_use_up_a_unit(client):
    """R11: a checkout with no renter_id fails and must not change the count."""
    client.application.config["PROPAGATE_EXCEPTIONS"] = False
    item = add_equipment(client, total_units=2)

    assert client.post("/rentals", json={"equipment_id": item["id"]}).status_code >= 400
    assert units(client, item["id"]) == 2

def test_check_out_form_adds_a_rental_to_the_rentals_page(client):
    client.post("/ui/equipment", data={"name": "Tent", "category": "Camping", "total_units": "2"})
    client.post("/ui/renters", data={"name": "Sam Lee", "email": "sam@example.com"})

    r = client.post("/ui/rentals", data={"equipment_id": "1", "renter_id": "1"})

    assert r.status_code == 302
    assert rows(client, "/ui/rentals") == [["1", "1", "1", TODAY, DUE, "-", "Return"]]

#Return equipment (PUT /rentals/<id>/return, Return button)

def test_return_sets_the_return_date_and_makes_the_unit_available_again(client):
    """R11"""
    rental = rent(client)

    r = client.put(f"/rentals/{rental['id']}/return")

    assert r.status_code == 200
    assert r.get_json()["return_date"] == TODAY
    assert units(client, rental["equipment_id"]) == 2


def test_returned_rental_stays_in_the_rental_history(client):
    """R6"""
    rental = rent(client)
    client.put(f"/rentals/{rental['id']}/return")

    history = client.get(f"/rentals?equipment_id={rental['equipment_id']}").get_json()
    assert history == [{**rental, "return_date": TODAY}]


def test_returning_the_same_rental_twice_is_refused_and_adds_no_second_unit(client):
    rental = rent(client)
    client.put(f"/rentals/{rental['id']}/return")

    r = client.put(f"/rentals/{rental['id']}/return")

    assert r.status_code == 400
    assert r.get_json() == {"error": "Rental already returned"}
    assert units(client, rental["equipment_id"]) == 2


def test_return_button_marks_the_rental_returned_on_the_rentals_page(client):
    """R6, R11"""
    client.post("/ui/equipment", data={"name": "Tent", "category": "Camping", "total_units": "2"})
    client.post("/ui/renters", data={"name": "Sam Lee", "email": "sam@example.com"})
    client.post("/ui/rentals", data={"equipment_id": "1", "renter_id": "1"})

    r = client.post("/ui/rentals/1/return")

    assert r.status_code == 302
    assert rows(client, "/ui/rentals") == [["1", "1", "1", TODAY, DUE, TODAY, ""]]
    assert rows(client, "/ui/equipment")[0][3:5] == ["2", "2"]


#Extend a rental (PUT /rentals/<id>/extend)

def test_extend_adds_the_days_to_the_due_date_and_saves_it(client):
    """R20, R22"""
    rental = rent(client)

    r = client.put(f"/rentals/{rental['id']}/extend", json={"days": 2})

    new_due = (date.today() + timedelta(days=9)).isoformat()
    assert r.status_code == 200
    assert r.get_json()["due_date"] == new_due
    assert client.get("/rentals").get_json()[0]["due_date"] == new_due


def test_extend_a_returned_rental_is_refused_and_keeps_the_due_date(client):
    rental = rent(client)
    client.put(f"/rentals/{rental['id']}/return")

    r = client.put(f"/rentals/{rental['id']}/extend", json={"days": 2})

    assert r.status_code == 400
    assert r.get_json() == {"error": "Rental already returned"}
    assert client.get("/rentals").get_json()[0]["due_date"] == DUE


def test_extension_of_more_than_two_days_is_refused(client):
    """R22: an extension is limited to 2 days."""
    rental = rent(client)

    assert client.put(f"/rentals/{rental['id']}/extend", json={"days": 5}).status_code >= 400
    assert client.get("/rentals").get_json()[0]["due_date"] == DUE


def test_extension_less_than_three_days_before_the_due_date_is_refused(client):
    """R22: must be requested at least 3 days before the due date (due date set to tomorrow)."""
    rental = rent(client)
    tomorrow = date.today() + timedelta(days=1)
    store.rentals[rental["id"]].due_date = tomorrow

    assert client.put(f"/rentals/{rental['id']}/extend", json={"days": 1}).status_code >= 400
    assert client.get("/rentals").get_json()[0]["due_date"] == tomorrow.isoformat()

#enhancement test
#Enhancement: check out availability enforcement (R10, R11, R1, R2)

def test_refused_checkout_creates_no_rental_and_keeps_the_unit_count(client):
    item = add_equipment(client, total_units=1)
    renter = add_renter(client)
    check_out(client, item["id"], renter["id"])

    r = check_out(client, item["id"], renter["id"])

    assert r.status_code == 400
    assert r.get_json() == {"error": "No units available"}
    assert len(client.get("/rentals").get_json()) == 1
    assert units(client, item["id"]) == 0


def test_out_of_service_item_is_refused_with_a_message_and_not_rented(client):
    item = add_equipment(client, total_units=2)
    renter = add_renter(client)
    client.patch(f"/equipment/{item['id']}/status", json={"is_available": False})

    r = check_out(client, item["id"], renter["id"])

    assert r.status_code == 400
    assert r.get_json() == {"error": "Equipment is out of service"}
    assert units(client, item["id"]) == 2


def test_unknown_renter_is_refused_with_404_and_the_unit_is_kept(client):
    item = add_equipment(client, total_units=2)

    r = check_out(client, item["id"], 999)

    assert r.status_code == 404
    assert r.get_json() == {"error": "Renter not found"}
    assert units(client, item["id"]) == 2


def test_checkout_without_ids_is_a_400_not_a_server_error(client):
    assert client.post("/rentals", json={}).status_code == 400
    assert client.post("/rentals", json={"equipment_id": 1}).status_code == 400


def test_item_can_be_rented_again_after_the_last_unit_is_returned(client):
    item = add_equipment(client, total_units=1)
    renter = add_renter(client)
    first = check_out(client, item["id"], renter["id"]).get_json()
    assert check_out(client, item["id"], renter["id"]).status_code == 400

    client.put(f"/rentals/{first['id']}/return")

    assert check_out(client, item["id"], renter["id"]).status_code == 201
    assert units(client, item["id"]) == 0


def test_check_out_form_does_not_rent_an_item_with_no_units_left(client):
    item = add_equipment(client, total_units=1)
    renter = add_renter(client)
    check_out(client, item["id"], renter["id"])

    client.post("/ui/rentals", data={"equipment_id": "1", "renter_id": "1"})

    assert len(rows(client, "/ui/rentals")) == 1
    assert units(client, item["id"]) == 0

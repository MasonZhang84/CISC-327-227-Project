"""Mason Zhang's tests.

Features covered:
    1. List equipment          GET /equipment, Equipment page (/ui/equipment)
                               Requirements: R10, R11
    2. View one equipment item GET /equipment/<id>
                               Requirements: No match
    3. Delete equipment        DELETE /equipment/<id>, Delete button on the
                               Equipment page (POST /ui/equipment/<id>/delete)
                               Requirements: No match
    4. Add equipment           POST /equipment, "Add Equipment" form on the
                               Equipment page (POST /ui/equipment)
                               Requirements: No match

Tests marked "Requirement-based" can fail: they check what a requirement asks
for, so a failure points to a defect in the application (see the report).

Run from the project folder with:  python -m pytest tests/test_mason.py -v
"""
import re

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_equipment(client, name="Kayak", category="Water", total_units=1):
    response = client.post(
        "/equipment",
        json={"name": name, "category": category, "total_units": total_units},
    )
    assert response.status_code == 201
    return response.get_json()


def add_renter(client, name="Sam Lee", email="sam@example.com"):
    response = client.post("/renters", json={"name": name, "email": email})
    assert response.status_code == 201
    return response.get_json()


def check_out(client, equipment_id, renter_id):
    return client.post(
        "/rentals", json={"equipment_id": equipment_id, "renter_id": renter_id}
    )


def list_equipment(client):
    response = client.get("/equipment")
    assert response.status_code == 200
    return response.get_json()


def equipment_rows(html):
    """Return the Equipment page table as rows of cell text (header skipped)."""
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        cells = [
            " ".join(re.sub(r"<.*?>", "", cell).split())
            for cell in re.findall(r"<td>(.*?)</td>", tr, re.S)
        ]
        if cells:
            rows.append(cells)
    return rows


# ===========================================================================
# Feature 1: List equipment  (GET /equipment and the Equipment page)
# Requirements: R10, R11
# ===========================================================================

def test_list_equipment_is_empty_when_nothing_added(client):
    """Response data: with no equipment, the list is an empty JSON list."""
    response = client.get("/equipment")

    assert response.status_code == 200
    assert response.get_json() == []


def test_list_equipment_returns_item_with_all_fields(client):
    """Response data: an added item comes back with every field correct."""
    add_equipment(client, name="Extension Ladder", category="Climbing", total_units=3)

    assert list_equipment(client) == [
        {
            "id": 1,
            "name": "Extension Ladder",
            "category": "Climbing",
            "total_units": 3,
            "available_units": 3,
            "is_available": True,
        }
    ]


def test_checkout_only_changes_the_rented_item_in_the_list(client):
    """R11 workflow: add two items, rent one, and only that item's count drops."""
    kayak = add_equipment(client, name="Kayak", total_units=2)
    add_equipment(client, name="Tent", total_units=2)
    renter = add_renter(client)

    assert check_out(client, kayak["id"], renter["id"]).status_code == 201

    by_name = {item["name"]: item for item in list_equipment(client)}
    assert by_name["Kayak"]["available_units"] == 1
    assert by_name["Tent"]["available_units"] == 2


def test_list_shows_item_marked_out_of_service(client):
    """R10 workflow: an item taken out of service is listed as not available."""
    item = add_equipment(client, name="Kayak")

    response = client.patch(f"/equipment/{item['id']}/status", json={"is_available": False})
    assert response.status_code == 200

    assert list_equipment(client)[0]["is_available"] is False


def test_checkout_of_unknown_equipment_does_not_change_the_list(client):
    """Error case: renting an id that does not exist is rejected and changes nothing."""
    add_equipment(client, name="Kayak", total_units=2)
    renter = add_renter(client)
    before = list_equipment(client)

    response = check_out(client, 999, renter["id"])

    assert response.status_code == 404
    assert list_equipment(client) == before


def test_equipment_page_shows_available_count_after_checkout(client):
    """R11 workflow (page): the Available column drops from 3 to 2 after a checkout."""
    client.post("/ui/equipment", data={"name": "Tent", "category": "Camping", "total_units": "3"})
    client.post("/ui/renters", data={"name": "Sam Lee", "email": "sam@example.com"})

    before = equipment_rows(client.get("/ui/equipment").get_data(as_text=True))[0]
    client.post("/ui/rentals", data={"equipment_id": "1", "renter_id": "1"})
    after = equipment_rows(client.get("/ui/equipment").get_data(as_text=True))[0]

    assert before[:5] == ["1", "Tent", "Camping", "3", "3"]  # id, name, category, total, available
    assert after[:5] == ["1", "Tent", "Camping", "3", "2"]


def test_list_shows_fully_rented_item_as_not_available(client):
    """Requirement-based (R10, R11): a single-unit item that is rented out must
    not be listed as available. Once the only unit is rented, available_units is
    0, so the item's status should say it is not available."""
    item = add_equipment(client, name="Kayak", total_units=1)
    renter = add_renter(client)
    check_out(client, item["id"], renter["id"])

    listed = list_equipment(client)[0]

    assert listed["available_units"] == 0
    assert listed["is_available"] is False


def test_list_never_shows_negative_available_units(client):
    """Requirement-based (R11): renting the same single unit twice must not show
    -1 available. A clerk needs to see whether gear is currently available, so
    the count should never go below zero (the second checkout should be refused)."""
    item = add_equipment(client, name="Kayak", total_units=1)
    renter = add_renter(client)

    check_out(client, item["id"], renter["id"])
    check_out(client, item["id"], renter["id"])

    assert list_equipment(client)[0]["available_units"] >= 0


def test_equipment_page_shows_out_of_service_item_as_out_of_service(client):
    """Requirement-based (R10): after an item is taken out of service, a clerk
    looking at the Equipment page should be able to see that."""
    item = add_equipment(client, name="Kayak")
    client.patch(f"/equipment/{item['id']}/status", json={"is_available": False})

    html = client.get("/ui/equipment").get_data(as_text=True).lower()

    wording = ("out of service", "unavailable", "not available")
    assert any(text in html for text in wording), (
        "Equipment page does not show that the item is out of service"
    )


# ===========================================================================
# Feature 2: View one equipment item  (GET /equipment/<id>)
# Requirements: No match
# ===========================================================================

def test_view_equipment_returns_expected_fields(client):
    """Response data: an added item is returned with the values it was created with."""
    created = add_equipment(client, name="Extension Ladder", category="Climbing", total_units=3)

    response = client.get(f"/equipment/{created['id']}")

    assert response.status_code == 200
    assert response.get_json() == {
        "id": created["id"],
        "name": "Extension Ladder",
        "category": "Climbing",
        "total_units": 3,
        "available_units": 3,
        "is_available": True,
    }


def test_view_equipment_returns_only_the_requested_item(client):
    """Response data: with several items, the id in the path picks the right one."""
    add_equipment(client, name="Kayak", category="Water")
    tent = add_equipment(client, name="Tent", category="Camping")
    add_equipment(client, name="Ladder", category="Climbing")

    item = client.get(f"/equipment/{tent['id']}").get_json()

    assert item["id"] == tent["id"]
    assert item["name"] == "Tent"
    assert item["category"] == "Camping"


def test_view_equipment_shows_one_fewer_available_unit_after_checkout(client):
    """Workflow: create, check out one unit, then view the item."""
    item = add_equipment(client, name="Tent", total_units=3)
    renter = add_renter(client)

    check_out(client, item["id"], renter["id"])
    viewed = client.get(f"/equipment/{item['id']}").get_json()

    assert viewed["total_units"] == 3
    assert viewed["available_units"] == 2


def test_view_equipment_shows_values_changed_by_an_update(client):
    """Workflow: update the name and category, then view the item."""
    item = add_equipment(client, name="Kayak", category="Water", total_units=2)

    response = client.put(
        f"/equipment/{item['id']}", json={"name": "Sea Kayak", "category": "Boats"}
    )
    assert response.status_code == 200

    viewed = client.get(f"/equipment/{item['id']}").get_json()
    assert viewed["name"] == "Sea Kayak"
    assert viewed["category"] == "Boats"
    assert viewed["total_units"] == 2  # fields not sent are unchanged


def test_view_equipment_that_does_not_exist_returns_404_with_message(client):
    """Error case: an id nobody has gives 404 and an error message."""
    add_equipment(client, name="Kayak")

    response = client.get("/equipment/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}


def test_view_equipment_after_it_was_deleted_returns_404(client):
    """Workflow: once an item is deleted, viewing it is not found."""
    item = add_equipment(client, name="Kayak")
    assert client.get(f"/equipment/{item['id']}").status_code == 200

    assert client.delete(f"/equipment/{item['id']}").status_code == 204

    assert client.get(f"/equipment/{item['id']}").status_code == 404


def test_view_equipment_twice_returns_the_same_data(client):
    """Repeated action: viewing an item does not change it."""
    item = add_equipment(client, name="Kayak", total_units=2)

    first = client.get(f"/equipment/{item['id']}").get_json()
    second = client.get(f"/equipment/{item['id']}").get_json()

    assert first == second


# ===========================================================================
# Feature 3: Delete equipment
#     - API:  DELETE /equipment/<id>
#     - Page: Delete button on /ui/equipment (POST /ui/equipment/<id>/delete)
# Requirements: No match
# ===========================================================================

def test_delete_equipment_returns_204_and_removes_the_item(client):
    """State check: a delete succeeds with no body, and the item is gone afterwards."""
    item = add_equipment(client, name="Kayak")

    response = client.delete(f"/equipment/{item['id']}")

    assert response.status_code == 204
    assert response.get_data() == b""
    assert client.get(f"/equipment/{item['id']}").status_code == 404
    assert list_equipment(client) == []


def test_delete_equipment_keeps_the_other_items(client):
    """Workflow: deleting one of three items leaves the other two unchanged."""
    kayak = add_equipment(client, name="Kayak", category="Water", total_units=2)
    tent = add_equipment(client, name="Tent", category="Camping", total_units=4)
    ladder = add_equipment(client, name="Ladder", category="Climbing", total_units=1)

    assert client.delete(f"/equipment/{tent['id']}").status_code == 204

    assert list_equipment(client) == [kayak, ladder]


def test_delete_equipment_that_does_not_exist_returns_404_and_changes_nothing(client):
    """Error case: an id nobody has gives 404 with a message, and the list is untouched."""
    add_equipment(client, name="Kayak")
    before = list_equipment(client)

    response = client.delete("/equipment/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Equipment not found"}
    assert list_equipment(client) == before


def test_delete_equipment_twice_returns_404_the_second_time(client):
    """Repeated action: the second delete of the same id is not found."""
    item = add_equipment(client, name="Kayak")

    first = client.delete(f"/equipment/{item['id']}")
    second = client.delete(f"/equipment/{item['id']}")

    assert first.status_code == 204
    assert second.status_code == 404


def test_equipment_added_after_a_delete_gets_a_new_id(client):
    """Boundary: a deleted id is not reused, so ids stay unique."""
    add_equipment(client, name="Kayak")
    tent = add_equipment(client, name="Tent")
    client.delete(f"/equipment/{tent['id']}")

    ladder = add_equipment(client, name="Ladder")

    assert ladder["id"] == 3


def test_delete_button_removes_the_item_from_the_equipment_page(client):
    """Page workflow: add two items with the form, delete one with its Delete button."""
    client.post("/ui/equipment", data={"name": "Kayak", "category": "Water", "total_units": "2"})
    client.post("/ui/equipment", data={"name": "Tent", "category": "Camping", "total_units": "3"})

    response = client.post("/ui/equipment/1/delete")

    assert response.status_code == 302  # redirected back to the Equipment page
    rows = equipment_rows(client.get("/ui/equipment").get_data(as_text=True))
    assert [row[:5] for row in rows] == [["2", "Tent", "Camping", "3", "3"]]
    assert [item["name"] for item in list_equipment(client)] == ["Tent"]


def test_delete_button_for_an_unknown_id_changes_nothing(client):
    """Page error case: deleting an id that does not exist leaves the table as it was."""
    client.post("/ui/equipment", data={"name": "Kayak", "category": "Water", "total_units": "2"})
    before = equipment_rows(client.get("/ui/equipment").get_data(as_text=True))

    response = client.post("/ui/equipment/999/delete")

    assert response.status_code == 302
    assert equipment_rows(client.get("/ui/equipment").get_data(as_text=True)) == before


# ===========================================================================
# Feature 4: Add equipment
#     - API:  POST /equipment
#     - Page: "Add Equipment" form on /ui/equipment (POST /ui/equipment)
# Requirements: No match
# ===========================================================================

def test_add_equipment_returns_201_and_expected_fields(client):
    """Response data: a new item comes back with the values sent, id 1, and
    every unit available."""
    response = client.post(
        "/equipment",
        json={"name": "Extension Ladder", "category": "Climbing", "total_units": 3},
    )

    assert response.status_code == 201
    assert response.get_json() == {
        "id": 1,
        "name": "Extension Ladder",
        "category": "Climbing",
        "total_units": 3,
        "available_units": 3,
        "is_available": True,
    }


def test_added_equipment_can_be_fetched_and_is_in_the_list(client):
    """State check: after the add, GET /equipment/<id> and GET /equipment both show it."""
    created = add_equipment(client, name="Kayak", category="Water", total_units=2)

    assert client.get(f"/equipment/{created['id']}").get_json() == created
    assert list_equipment(client) == [created]


def test_add_equipment_without_total_units_defaults_to_one_unit(client):
    """Boundary: with no total_units, the item has 1 unit, all available."""
    response = client.post("/equipment", json={"name": "Kayak", "category": "Water"})

    assert response.status_code == 201
    item = response.get_json()
    assert item["total_units"] == 1
    assert item["available_units"] == 1


def test_add_equipment_with_the_same_details_twice_creates_two_items(client):
    """Repeated action: sending the same item twice gives two separate items."""
    first = add_equipment(client, name="Kayak", category="Water", total_units=1)
    second = add_equipment(client, name="Kayak", category="Water", total_units=1)

    assert first["id"] != second["id"]
    assert len(list_equipment(client)) == 2


@pytest.mark.parametrize("missing", ["name", "category"])
def test_add_equipment_missing_a_required_field_is_an_error_and_adds_nothing(client, missing):
    """Error case: a request without a name or category fails and adds nothing."""
    client.application.config["PROPAGATE_EXCEPTIONS"] = False  # get the error response
    payload = {"name": "Kayak", "category": "Water", "total_units": 1}
    del payload[missing]

    response = client.post("/equipment", json=payload)

    assert response.status_code >= 400
    assert list_equipment(client) == []


def test_add_form_adds_the_item_to_the_equipment_page_and_the_api(client):
    """Page workflow: fill in the Add Equipment form, then see the item on the
    page (with every unit available) and in the API list."""
    response = client.post(
        "/ui/equipment",
        data={"name": "Tent", "category": "Camping", "total_units": "3"},
    )

    assert response.status_code == 302  # redirected back to the Equipment page
    rows = equipment_rows(client.get("/ui/equipment").get_data(as_text=True))
    assert [row[:5] for row in rows] == [["1", "Tent", "Camping", "3", "3"]]
    assert list_equipment(client)[0]["name"] == "Tent"

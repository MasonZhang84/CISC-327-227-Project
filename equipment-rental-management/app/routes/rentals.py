from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from app import store
from app.models.rental import Rental
from notification_service import send_notification

rentals_bp = Blueprint("rentals", __name__, url_prefix="/rentals")


@rentals_bp.route("", methods=["GET"])
def list_rentals():
    results = list(store.rentals.values())
    renter_id = request.args.get("renter_id", type=int)
    equipment_id = request.args.get("equipment_id", type=int)
    if renter_id is not None:
        results = [r for r in results if r.renter_id == renter_id]
    if equipment_id is not None:
        results = [r for r in results if r.equipment_id == equipment_id]
    return jsonify([r.to_dict() for r in results])


def checkout_error(equipment_id, renter_id):
    """Return (message, status) if the check-out must be refused, else None."""
    item = store.equipment.get(equipment_id)
    if item is None:
        return "Equipment not found", 404
    if renter_id not in store.renters:
        return "Renter not found", 404
    if not item.is_available:
        return "Equipment is out of service", 400
    if item.available_units < 1:
        return "No units available", 400
    return None


@rentals_bp.route("", methods=["POST"])
def checkout_equipment():
    data = request.get_json(silent=True) or {}
    equipment_id = data.get("equipment_id")
    renter_id = data.get("renter_id")
    if equipment_id is None or renter_id is None:
        return jsonify({"error": "equipment_id and renter_id are required"}), 400

    error = checkout_error(equipment_id, renter_id)
    if error is not None:
        return jsonify({"error": error[0]}), error[1]

    store.equipment[equipment_id].available_units -= 1
    rental_id = store.next_id("rental")
    rental = Rental(
        id=rental_id,
        equipment_id=equipment_id,
        renter_id=renter_id,
        due_date=Rental.default_due_date(),
        deposit_amount=data.get("deposit_amount", 0.0),
    )
    store.rentals[rental_id] = rental
    return jsonify(rental.to_dict()), 201


@rentals_bp.route("/<int:rental_id>/return", methods=["PUT"])
def return_equipment(rental_id):
    rental = store.rentals.get(rental_id)
    if rental is None:
        return jsonify({"error": "Rental not found"}), 404
    if rental.return_date is not None:
        return jsonify({"error": "Rental already returned"}), 400

    rental.return_date = date.today()
    item = store.equipment.get(rental.equipment_id)
    if item is not None:
        item.available_units += 1

    return jsonify(rental.to_dict())


@rentals_bp.route("/<int:rental_id>/extend", methods=["PUT"])
def extend_rental(rental_id):
    """Extend a rental's due date by the given number of days."""
    rental = store.rentals.get(rental_id)
    if rental is None:
        return jsonify({"error": "Rental not found"}), 404
    if rental.return_date is not None:
        return jsonify({"error": "Rental already returned"}), 400

    data = request.get_json()
    days = data.get("days", 1)
    rental.due_date = rental.due_date + timedelta(days=days)
    return jsonify(rental.to_dict())


@rentals_bp.route("/<int:rental_id>/deposit/release", methods=["PUT"])
def release_deposit(rental_id):
    """Release the damage deposit hold for a returned rental."""
    rental = store.rentals.get(rental_id)
    if rental is None:
        return jsonify({"error": "Rental not found"}), 404
    if rental.return_date is None:
        return jsonify({"error": "Equipment has not been returned yet"}), 400

    rental.deposit_released = True
    return jsonify({"rental_id": rental_id, "deposit_released": True})

@rentals_bp.route("/<int:rental_id>/reminder", methods=["POST"])
def send_overdue_reminder(rental_id):
    """Send an overdue-return reminder to the renter of an overdue rental."""
    rental = store.rentals.get(rental_id)
    if rental is None:
        return jsonify({"error": "Rental not found"}), 404
    if rental.return_date is not None:
        return jsonify({"error": "Rental already returned"}), 400
    if not rental.is_overdue():
        return jsonify({"error": "Rental is not overdue"}), 400

    renter = store.renters[rental.renter_id]
    item = store.equipment[rental.equipment_id]
    sent = send_notification(
        renter.email,
        "Overdue rental reminder",
        f"Your rental of {item.name} was due on {rental.due_date} "
        f"and is {rental.days_overdue()} day(s) overdue. Please return it.",
    )
    rental.reminder_sent = sent
    return jsonify({"rental_id": rental_id, "reminder_sent": sent}), 200

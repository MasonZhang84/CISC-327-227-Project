from datetime import date

from flask import Blueprint, jsonify

from app import store

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/rented", methods=["GET"])
def rented_report():
    """List every rental whose equipment has not been returned yet."""
    results = [r for r in store.rentals.values() if r.return_date is None]
    return jsonify([r.to_dict() for r in results])


@reports_bp.route("/overdue", methods=["GET"])
def overdue_report():
    """List unreturned rentals past their due date, most overdue first."""
    today = date.today()
    results = [r for r in store.rentals.values() if r.is_overdue(today)]
    results.sort(key=lambda r: r.due_date)
    return jsonify(
        [{**r.to_dict(), "days_overdue": r.days_overdue(today)} for r in results]
    )

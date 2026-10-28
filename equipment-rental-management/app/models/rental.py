from datetime import date, timedelta

RENTAL_PERIOD_DAYS = 7


class Rental:
    def __init__(
        self,
        id,
        equipment_id,
        renter_id,
        due_date,
        rental_date=None,
        return_date=None,
        deposit_amount=0.0,
        deposit_released=False,
    ):
        self.id = id
        self.equipment_id = equipment_id
        self.renter_id = renter_id
        self.rental_date = rental_date or date.today()
        self.due_date = due_date
        self.return_date = return_date
        self.deposit_amount = deposit_amount
        self.deposit_released = deposit_released

    def to_dict(self):
        return {
            "id": self.id,
            "equipment_id": self.equipment_id,
            "renter_id": self.renter_id,
            "rental_date": self.rental_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "return_date": self.return_date.isoformat() if self.return_date else None,
            "deposit_amount": self.deposit_amount,
            "deposit_released": self.deposit_released,
        }

    @staticmethod
    def default_due_date():
        return date.today() + timedelta(days=RENTAL_PERIOD_DAYS)

    def is_overdue(self, today=None):
        """True if the equipment is still out and its due date has passed."""
        today = today or date.today()
        return self.return_date is None and self.due_date < today

    def days_overdue(self, today=None):
        today = today or date.today()
        return (today - self.due_date).days if self.is_overdue(today) else 0

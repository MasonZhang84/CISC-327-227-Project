# Equipment Rental Management (ERM)

A small Flask REST API for tracking equipment, renters, and rentals. Data is
stored **in memory** (plain Python objects, no database) and is reset every
time the app restarts — this project is meant to run before you've covered
databases.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

The API runs at `http://127.0.0.1:5000`.

## Web UI

Open `http://127.0.0.1:5000/` in a browser for a basic HTML front end (plain
forms and tables, no JavaScript) to add/delete equipment and renters, and
check equipment in/out:

| Page | Path |
|---|---|
| Home | `/` |
| Equipment | `/ui/equipment` |
| Renters | `/ui/renters` |
| Rentals | `/ui/rentals` |

This UI is separate from the JSON API below — it's there so you can see the
app working without a REST client, and calls the same in-memory store.

## Entities

- **Equipment**: `id, name, category, total_units, available_units`
- **Renter**: `id, name, email, membership_date`
- **Rental**: `id, equipment_id, renter_id, rental_date, due_date, return_date`

## JSON API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/equipment` | List all equipment |
| POST | `/equipment` | Add an equipment item |
| GET | `/equipment/<id>` | Get one equipment item |
| PUT | `/equipment/<id>` | Update an equipment item |
| DELETE | `/equipment/<id>` | Delete an equipment item |
| GET | `/renters` | List all renters |
| POST | `/renters` | Create a renter |
| GET | `/renters/<id>` | Get one renter |
| PUT | `/renters/<id>` | Update a renter |
| DELETE | `/renters/<id>` | Delete a renter |
| POST | `/rentals` | Check out equipment (`equipment_id`, `renter_id`) |
| PUT | `/rentals/<id>/return` | Return rented equipment |
| GET | `/rentals?renter_id=&equipment_id=` | Look up rentals |
| GET | `/reports/rented` | Report of currently rented (unreturned) equipment |
| GET | `/reports/overdue` | Report of unreturned rentals past their due date, with `days_overdue` |

## Tests

```bash
pytest
```


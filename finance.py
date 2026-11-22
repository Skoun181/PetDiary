"""Money is stored as integer EUR cents, never floating point."""
import re

COST_CATEGORIES = {
    "vet": "Tierarzt", "medicine": "Medikamente", "food": "Futter",
    "vaccine": "Impfungen", "insurance": "Versicherung", "care": "Pflege",
    "other": "Sonstiges",
}

COST_SCHEMA = """
CREATE TABLE IF NOT EXISTS costs (
 id INTEGER PRIMARY KEY,
 pet_id INTEGER NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
 record_id INTEGER REFERENCES records(id) ON DELETE SET NULL,
 day TEXT NOT NULL,
 category TEXT NOT NULL CHECK(category IN ('vet','medicine','food','vaccine','insurance','care','other')),
 title TEXT NOT NULL,
 cents INTEGER NOT NULL CHECK(typeof(cents)='integer' AND cents BETWEEN 1 AND 999999999),
 reimbursed INTEGER NOT NULL DEFAULT 0 CHECK(typeof(reimbursed)='integer' AND reimbursed BETWEEN 0 AND cents),
 notes TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS costs_pet_day ON costs(pet_id,day);
"""

def parse_cents(value, optional=False):
    value = value.strip()
    if optional and not value:
        return 0
    if not re.fullmatch(r"[0-9]{1,7}(?:[.,][0-9]{1,2})?", value):
        raise ValueError("Bitte einen gültigen Eurobetrag mit höchstens zwei Nachkommastellen eingeben.")
    whole, _, frac = value.replace(",", ".").partition(".")
    return int(whole)*100 + int(frac.ljust(2,"0"))

def euro(cents):
    return f"{cents//100:,}".replace(",", ".") + f",{cents%100:02d} €"

def input_euro(cents):
    return f"{cents//100},{cents%100:02d}"

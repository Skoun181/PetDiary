"""Additive migrations for existing PetDiary databases."""

SCHEMA_VERSION = 4
PLAN_COLUMNS = {
    "records": {"schedule_from": "TEXT NOT NULL DEFAULT ''"},
    "dose_checks": {"product": "TEXT", "dose": "TEXT", "dose_unit": "TEXT"},
}


def migrate(con):
    version = con.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError("Die Datenbank gehört zu einer neueren PetDiary-Version.")
    for table, additions in (
        ("pets", ("features", "tattoo_location")),
        ("records", ("dose", "dose_unit", "duration", "dose_times")),
    ):
        known = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
        for column in additions:
            if column not in known:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT NOT NULL DEFAULT ''")
    columns = {row[1] for row in con.execute("PRAGMA table_info(records)")}
    if "parent_id" not in columns:
        con.execute("ALTER TABLE records ADD COLUMN parent_id INTEGER REFERENCES records(id) ON DELETE CASCADE")
    con.execute("CREATE INDEX IF NOT EXISTS records_parent ON records(parent_id)")
    if version < 3:
        con.execute("INSERT OR IGNORE INTO cost_records(cost_id,record_id) SELECT id,record_id FROM costs WHERE record_id IS NOT NULL")
        con.execute("UPDATE costs SET record_id=NULL WHERE record_id IS NOT NULL")
    if version < 4:
        for table, additions in PLAN_COLUMNS.items():
            known = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
            for column, definition in additions.items():
                if column not in known:
                    con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        hydrate_dose_history(con)
    con.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def hydrate_dose_history(con):
    con.execute("""UPDATE dose_checks SET
        product=(SELECT product FROM records WHERE id=record_id),
        dose=(SELECT dose FROM records WHERE id=record_id),
        dose_unit=(SELECT dose_unit FROM records WHERE id=record_id)
        WHERE product IS NULL AND dose IS NULL AND dose_unit IS NULL""")

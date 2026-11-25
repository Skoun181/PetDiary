"""Calendar projections and the history of documented administrations."""

from datetime import date, datetime, timedelta


def effective_start(con, previous, proposed, today):
    current = previous.get("schedule_from", "")
    changed = any(previous.get(field, "") != proposed[field] for field in (
        "kind", "day", "duration", "dose_times", "product", "dose", "dose_unit",
    ))
    if not changed:
        return current
    last_check = con.execute("SELECT MAX(day) FROM dose_checks WHERE record_id=?", (previous["id"],)).fetchone()[0]
    if not last_check:
        return ""
    last_date = date.fromisoformat(last_check)
    if last_date == date.max:
        return last_date.isoformat()
    return max(today, last_date + timedelta(days=1)).isoformat()


def calendar_rows(con, start, end, tz, pet_id=None):
    args = [end.isoformat(), start.isoformat(), end.isoformat()]
    sql = """SELECT r.*, p.name AS pet FROM records r JOIN pets p ON p.id=r.pet_id
             WHERE ((r.kind='med' AND r.duration!='' AND r.day<=?)
                 OR EXISTS (SELECT 1 FROM dose_checks d WHERE d.record_id=r.id AND d.day BETWEEN ? AND ?))"""
    if pet_id is not None:
        sql += " AND r.pet_id=?"
        args.append(pet_id)
    history = {}
    for row in con.execute("SELECT * FROM dose_checks WHERE day BETWEEN ? AND ?", (start.isoformat(), end.isoformat())):
        history.setdefault(row["record_id"], {})[(row["day"], row["clock"])] = row
    result = []

    def add(record, day, clock, check):
        moment = datetime.fromisoformat(day + "T" + clock).replace(tzinfo=tz) if clock else None
        entry = {key: check[key] if check is not None and check[key] is not None else record[key]
                 for key in ("product", "dose", "dose_unit")}
        result.append(dict(id=f'{record["id"]}:{day}:{clock}', record_id=record["id"],
                           entry_id=record["parent_id"] or record["id"], pet_id=record["pet_id"],
                           pet=record["pet"], title=record["title"], product=entry["product"],
                           dose=entry["dose"], unit=entry["dose_unit"], day=day, time=clock,
                           scheduled_at=moment.isoformat() if moment else None, done=check is not None))

    for record in con.execute(sql, args):
        checked = history.get(record["id"], {})
        for (day, clock), check in checked.items():
            add(record, day, clock, check)
        if record["kind"] != "med" or not record["duration"]:
            continue
        first = date.fromisoformat(record["day"])
        last = min(end, first + timedelta(days=int(record["duration"]) - 1))
        current = max(first, start, date.fromisoformat(record["schedule_from"] or record["day"]))
        while current <= last:
            day = current.isoformat()
            for clock in record["dose_times"].split(","):
                if (day, clock) not in checked:
                    add(record, day, clock, None)
            if current == last:
                break
            current += timedelta(days=1)
    return sorted(result, key=lambda row: (row["day"], row["time"], row["pet"], row["record_id"]))

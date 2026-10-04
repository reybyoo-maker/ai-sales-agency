from .discovery import discover
from .sheets import get_sheet, rows_as_dicts, append_rows

rows = discover(50)
ws = get_sheet()
existing = rows_as_dicts(ws)
keys = set()
for r in existing:
    for field in ("website", "instagram", "email"):
        v = str(r.get(field, "")).strip().lower()
        if v:
            keys.add((field, v))
new_rows = []
for r in rows:
    duplicate = False
    for field in ("website", "instagram", "email"):
        v = str(r.get(field, "")).strip().lower()
        if v and (field, v) in keys:
            duplicate = True
    if not duplicate:
        new_rows.append(r)
        for field in ("website", "instagram", "email"):
            v = str(r.get(field, "")).strip().lower()
            if v:
                keys.add((field, v))
append_rows(ws, new_rows)
print(f'Discovered={len(rows)} New={len(new_rows)}')

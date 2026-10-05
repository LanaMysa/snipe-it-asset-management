"""
Конвертер Access (Ausleihe.accdb) → Snipe-IT CSV
=======================================================
Создаёт готовые к импорту CSV-файлы для:
  1. Locations         (из Ortsverzeichnis)
  2. Manufacturers     (распознаны из моделей)
  3. Categories        (3 категории: Notebook, Technik, Zubehör)
  4. Assets (Hardware) (Notebook + Technik из Geräte)
  5. Accessories       (Zubehör из Geräte)
  6. Users             (из Ausleihe.Entleiher_Name + Ausgeber_Entgegennehmer)

Подход:
  - UTF-8 без BOM (как требует Snipe-IT).
  - Snipe-IT при импорте САМ создаёт Manufacturer, Category, Location, Model
    если они не существуют. Поэтому ОТДЕЛЬНЫЕ файлы справочников НЕ обязательны,
    но мы их генерируем для предварительной ручной проверки в UI.
  - Главный файл assets.csv содержит все обязательные поля.
"""

import csv
import os
import re
from collections import OrderedDict

SRC = "/home/claude/access_analysis"
OUT = "/home/claude/snipeit_import"
os.makedirs(OUT, exist_ok=True)


def load(name):
    with open(f"{SRC}/{name}.csv", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(name, rows, headers):
    """Пишем CSV в UTF-8 без BOM, c CRLF — как любит Snipe-IT."""
    with open(f"{OUT}/{name}.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in headers})
    print(f"  → {name}.csv ({len(rows)} строк)")


# ============================================================
# 1. LOCATIONS — из Ortsverzeichnis
# ============================================================
print("\n[1/6] Locations …")
orts = load("Ortsverzeichnis")
# Уникальные непустые имена локаций
loc_names = OrderedDict()
for r in orts:
    name = r["Lagerort"].strip()
    if name and name != "N.N." and name not in loc_names:
        loc_names[name] = True

# Добавим локации из Geräte (могут быть локации, которых нет в Ortsverzeichnis)
geraete = load("Geräte")
for r in geraete:
    loc = r["Lagerort"].strip()
    if loc and loc not in loc_names and loc != "N.N.":
        loc_names[loc] = True

loc_rows = [{"Name": n} for n in loc_names]
write("01_locations", loc_rows, ["Name"])

# ============================================================
# 2. MANUFACTURERS — распознаём из моделей
# ============================================================
print("\n[2/6] Manufacturers …")
# Маппинг "ключевое слово в названии модели" → "канонический бренд"
brand_rules = [
    ("HP ", "HP"),
    ("MacBook", "Apple"),
    ("Apple", "Apple"),
    ("iPad", "Apple"),
    ("iPhone", "Apple"),
    ("Compaq", "HP"),
    ("Surface", "Microsoft"),
    ("Yoga", "Lenovo"),
    ("Raspberry", "Raspberry Pi Foundation"),
    ("Arduino", "Arduino"),
    ("Fischer Technik", "Fischertechnik"),
    ("LEGO", "LEGO"),
    ("Sandisk", "SanDisk"),
    ("Logitech", "Logitech"),
    ("Brother", "Brother"),
    ("Canon", "Canon"),
    ("Samsung", "Samsung"),
    ("Kingston", "Kingston"),
    ("Freenove", "Freenove"),
    ("SunFounder", "SunFounder"),
    ("GeeekPi", "GeeekPi"),
    ("UGREEN", "UGREEN"),
    ("Ozobot", "Ozobot"),
    ("Banana Pi", "Banana Pi"),
]


def detect_brand(model_name):
    if not model_name:
        return "Unknown"
    for keyword, brand in brand_rules:
        if keyword.lower() in model_name.lower():
            return brand
    return "Unknown"


modell_spec = load("ModellSpezifikation")
brands_set = OrderedDict()
for r in modell_spec:
    b = detect_brand(r["Modell"])
    brands_set[b] = True

mfr_rows = [{"Name": b} for b in brands_set if b != "Unknown"]
# Unknown добавим в конец, иначе устройства без бренда упадут на импорте
mfr_rows.append({"Name": "Unknown"})
write("02_manufacturers", mfr_rows, ["Name"])

# ============================================================
# 3. CATEGORIES — 3 типа из TypSpezifikation
# ============================================================
print("\n[3/6] Categories …")
# Snipe-IT требует поле Category Type: asset / accessory / consumable / component / license
cat_rows = [
    {"Name": "Notebook", "Category Type": "asset"},
    {"Name": "Technik", "Category Type": "asset"},
    {"Name": "Zubehör", "Category Type": "accessory"},
]
write("03_categories", cat_rows, ["Name", "Category Type"])

# ============================================================
# 4. ASSETS — Notebook + Technik (это полноценные активы со своим asset tag)
# ============================================================
print("\n[4/6] Assets (Notebook + Technik) …")
# Загружаем NotebookInstall, чтобы добавить информацию о ПО
nb_install = {r["InstallID"]: r["Aktuelle_Installation"] for r in load("NotebookInstall")}
nb_extra = {}  # GeräteID → {Aktuelle_Installation, WIN_Office_aktuell}
for r in load("Notebooks"):
    nb_extra[r["GeräteID"]] = {
        "OS_Install": r.get("Aktuelle_Installation", ""),
        "WIN_Office_aktuell": "Ja" if r.get("WIN_Office_aktuell") == "1" else "Nein",
    }


def map_status(row):
    """Маппинг булевых флагов Access в Snipe-IT Status Label."""
    if row["Ausgesondert"] == "1":
        return "Retired"
    if row["Auszusondern"] == "1":
        return "Pending Disposal"
    if row["Dauerleihe"] == "1":
        return "Deployed (Permanent Loan)"
    if row["Vorhanden"] == "1":
        return "Ready to Deploy"
    return "Lost / Missing"


asset_rows = []
for r in geraete:
    if r["Typ"] not in ("Notebook", "Technik"):
        continue
    gid = r["GeräteID"]
    extras = nb_extra.get(gid, {})
    asset_rows.append({
        "Asset Tag": r["Gerätename"],            # WIINF-PB-01, raspberry_winf1, 100605, …
        "Category": r["Typ"],                    # Notebook | Technik
        "Manufacturer": detect_brand(r["Modell"]),
        "Model Name": r["Modell"] or r["Gerät"] or "N/A",
        "Serial": r["Seriennummer"],
        "Status": map_status(r),
        "Location": r["Lagerort"] if r["Lagerort"] != "N.N." else "",
        "Purchase Date": r["Kaufdatum"],         # уже в формате YYYY-MM-DD
        "Notes": r["Bemerkung"],
        "Assigned To Name": r.get("Dauerleihe (Name)", "") if r["Dauerleihe"] == "1" else "",
        # Custom Fields префиксуются именем, как в Snipe-IT UI
        "OS Installation": extras.get("OS_Install", ""),
        "Office Aktuell": extras.get("WIN_Office_aktuell", ""),
        "Inventarnummer (Altsystem)": gid,       # сохраняем оригинальный ID из Access
        "Gerätetyp (Subtyp)": r["Gerät"],
    })

asset_headers = [
    "Asset Tag", "Category", "Manufacturer", "Model Name", "Serial",
    "Status", "Location", "Purchase Date", "Notes",
    "Assigned To Name",
    "OS Installation", "Office Aktuell",
    "Inventarnummer (Altsystem)", "Gerätetyp (Subtyp)",
]
write("04_assets", asset_rows, asset_headers)

# ============================================================
# 5. ACCESSORIES — Zubehör с агрегацией по модели
# ============================================================
print("\n[5/6] Accessories …")
# В Snipe-IT Accessories не имеют индивидуальных tags — это пул штук.
# Поэтому агрегируем Zubehör из Geräte по полю Modell и складываем Stück из Zubehör.csv.
zubehoer_stueck = {r["GeräteID"]: int(r["Stück"]) for r in load("Zubehör") if r["Stück"]}

# Группируем по модели
acc_groups = {}
for r in geraete:
    if r["Typ"] != "Zubehör":
        continue
    key = (r["Modell"] or r["Gerät"], r["Lagerort"])
    if key not in acc_groups:
        acc_groups[key] = {
            "Name": r["Modell"] or r["Gerät"],
            "Manufacturer": detect_brand(r["Modell"]),
            "Category": "Zubehör",
            "Location": r["Lagerort"] if r["Lagerort"] != "N.N." else "",
            "Qty": 0,
            "Notes": [],
        }
    qty = zubehoer_stueck.get(r["GeräteID"], 1)
    acc_groups[key]["Qty"] += qty
    if r["Bemerkung"]:
        acc_groups[key]["Notes"].append(r["Bemerkung"])

acc_rows = []
for g in acc_groups.values():
    acc_rows.append({
        "Name": g["Name"],
        "Manufacturer": g["Manufacturer"],
        "Category": g["Category"],
        "Location": g["Location"],
        "Quantity": g["Qty"],
        "Notes": " | ".join(g["Notes"][:3]),
    })

write("05_accessories", acc_rows, ["Name", "Manufacturer", "Category", "Location", "Quantity", "Notes"])

# ============================================================
# 6. USERS — извлекаем уникальные имена
# ============================================================
print("\n[6/6] Users …")
# Из Ausgeber_Entgegennehmer (выдающие/принимающие — это сотрудники IT-Labor)
users = OrderedDict()


def add_user(full_name, role=""):
    if not full_name or full_name in ("N.N.", "N.N. (Altlast)", "k.A."):
        return
    # Формат "Nachname, Vorname" → first=Vorname last=Nachname
    if "," in full_name:
        parts = [p.strip() for p in full_name.split(",", 1)]
        last, first = parts[0], parts[1]
    else:
        parts = full_name.strip().split()
        if len(parts) >= 2:
            first = parts[0]
            last = " ".join(parts[1:])
        else:
            first = full_name.strip()
            last = ""
    # username = first.last в нижнем регистре, без не-ASCII
    def slug(s):
        s = s.lower()
        s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        s = re.sub(r"[^a-z0-9]+", "", s)
        return s
    uname = f"{slug(first)}.{slug(last)}".strip(".")
    if not uname or uname in users:
        return
    users[uname] = {
        "Username": uname,
        "First Name": first,
        "Last Name": last,
        "Email": f"{uname}@example.local",  # placeholder, заменить на реальный домен!
        "Department": role or "IT-Labor",
    }


for r in load("Ausgeber_Entgegennehmer"):
    add_user(r["Name"], "IT-Labor (Mitarbeiter)")

# Из Ausleihe.Entleiher_Name (заёмщики)
for r in load("Ausleihe"):
    add_user(r["Entleiher_Name"], "Entleiher")

write("06_users", list(users.values()),
      ["Username", "First Name", "Last Name", "Email", "Department"])

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 50)
print("ГОТОВО. Файлы в:", OUT)
print("=" * 50)
for f in sorted(os.listdir(OUT)):
    if f.endswith(".csv"):
        size = os.path.getsize(f"{OUT}/{f}")
        print(f"  {f}  ({size:,} bytes)")

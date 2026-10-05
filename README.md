# Snipe-IT – Inventarverwaltungssystem für ein Hochschul-IT-Labor

> **Hinweis:** Dies ist eine anonymisierte Fassung für mein Portfolio. IP-Adressen, Benutzernamen,
> Namen von Personen und interne Bezeichnungen wurden ersetzt (z. B. `192.0.2.10` = Beispieladresse nach RFC 5737).

Dokumentation der Installation von **Snipe-IT** und der Migration des Labor-Inventars
aus der bisherigen Access-Datenbank (`Ausleihe.accdb`) in einem Hochschul-IT-Labor.

| | |
|---|---|
| **Erstellt von** | Lana M. (Umschülerin Fachinformatikerin für Systemintegration) |
| **Zeitraum** | Mai 2026 (Installation ab 18.05.2026, Datenimport 21.05.2026), Nacharbeiten bis Juni 2026 |
| **Stand der Doku** | Oktober 2026 |

## Kurzüberblick

```
Unraid-Host ──► Debian-13-VM ──► Docker Engine + Compose ──► Snipe-IT 8.5.0
                                                              ├─ snipeit-app (Webanwendung, Port 8080)
                                                              └─ snipeit-db  (MariaDB)
```

| Komponente | Wert |
|---|---|
| Virtualisierung | Unraid 7.2.8, VM `SnipeIT` (3 vCPU, 4 GB RAM, 40 GB) |
| Betriebssystem | Debian GNU/Linux 13 (GNOME), Hostname `Snipe-IT` |
| Container-Laufzeit | Docker Engine 29.4.3 + Docker Compose v5.1.3 |
| Anwendung | Snipe-IT 8.5.0 |
| Datenbank | MariaDB (Container `snipeit-db`) |
| Web-Oberfläche | `http://192.0.2.10:8080` (nur im internen Netz) |
| Linux-Benutzer | `itadmin` |
| Quelldaten | `Ausleihe.accdb` (MS Access) |

### Migrierte Datensätze

| Typ | Anzahl |
|---|---|
| Assets (Geräte) | 411 (408 importiert + 3 manuell) |
| Zubehör | 113 Positionen (537 Stück) |
| Benutzer | 296 (davon 3 Admin-Konten) |
| Standorte | 80 |
| Hersteller | 21 aus Access (+ 10 Beispieldaten) |

## Inhalt

| Nr. | Kapitel | Datei |
|---|---|---|
| 1 | Einrichtung der virtuellen Maschine (Unraid, Debian 13) | [docs/01_vm-einrichtung.md](docs/01_vm-einrichtung.md) |
| 2 | Installation von Docker | [docs/02_docker-installation.md](docs/02_docker-installation.md) |
| 3 | Installation von Snipe-IT | [docs/03_snipe-it-installation.md](docs/03_snipe-it-installation.md) |
| 4 | Datenmigration aus MS Access | [docs/04_datenmigration.md](docs/04_datenmigration.md) |
| 5 | Konfiguration in Snipe-IT | [docs/05_konfiguration.md](docs/05_konfiguration.md) |
| 6 | Backup und Wartung | [docs/06_backup-wartung.md](docs/06_backup-wartung.md) |
| – | Screenshot-Plan | [SCREENSHOTS.md](SCREENSHOTS.md) |

## Repository-Struktur

```
snipe-it-doku/
├── README.md                  ← diese Datei
├── SCREENSHOTS.md             ← Liste aller Screenshots (Name, Ordner, Inhalt)
├── .gitignore                 ← schließt .env, Backups und Access-Datei aus
├── tools/
│   ├── make-portfolio.sh       ← erzeugt anonymisierte Kopie
│   └── migration/convert_access_to_snipeit.py  ← Access → Snipe-IT CSV
├── config/
│   ├── docker-compose.yml.example
│   └── env.example            ← Vorlage ohne Passwörter/APP_KEY
├── docs/                      ← Kapitel 1–6
└── screenshots/               ← Bilder, nach Kapiteln sortiert
```

## Datenschutz / Sicherheit

In diesem Repository befinden sich **keine** Passwörter, kein `APP_KEY`, keine Backups
und keine personenbezogenen Daten. Echte `.env`-Dateien, `*.zip`-Backups und die
Access-Datenbank sind per `.gitignore` ausgeschlossen. Auf Screenshots sind Passwörter,
Schlüssel sowie Namen/E-Mail-Adressen von Benutzern unkenntlich gemacht.

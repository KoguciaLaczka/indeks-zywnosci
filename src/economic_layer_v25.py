from __future__ import annotations

import csv
import html
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]

CORE_RANKING = ROOT / "data/results/ranking-v23-30.csv"
PORTION_RANKING = ROOT / "data/results/portion-ranking-v24.csv"

REFERENCE_PRICES = ROOT / "data/prices/reference-prices-v25.csv"
USER_PRICES = ROOT / "data/prices/user-prices.csv"
PRICE_README = ROOT / "data/prices/README.md"

ALL_RESULTS = ROOT / "data/results/economy-all-v25.csv"
QUALIFIED_RESULTS = ROOT / "data/results/economy-ranking-v25.csv"
EXCEPTIONS = ROOT / "data/results/economy-exceptions-v25.csv"
JSON_OUTPUT = ROOT / "public/data/economy-ranking-v25.json"
HTML_OUTPUT = ROOT / "public/economy.html"
SUMMARY_OUTPUT = ROOT / "artifacts/economy-summary-v25.json"

VERSION = "2.5.0-economy-pilot"

USER_PRICE_MAX_AGE_DAYS = 45
REFERENCE_PRICE_MAX_AGE_DAYS = 90

LEGACY_PRICE_SOURCE = (
    "https://docs.google.com/spreadsheets/d/"
    "1qk2fmRIPISVUrciSM2iPEm-hvuf0X17yBb62kTSQzcM/"
    "gviz/tq?tqx=out:csv&sheet="
    "Warto%C5%9B%C4%87%20za%201%20z%C5%82"
)

# Ceny odzyskane ze starego publicznego rankingu.
# Nie są automatycznie przypisywane produktom podobnym.
LEGACY_REFERENCE_PRICES: dict[str, dict[str, str]] = {
    "BEEF-LIVER-RAW": {
        "price_pln_per_kg": "22.00",
        "observed_at": "2026-09-26",
        "source_label": "Publiczny ranking legacy v1.2",
        "source_url": LEGACY_PRICE_SOURCE,
        "confidence": "Średnia",
        "note": "Cena odzyskana ze starego publicznego rankingu.",
    },
    "BEEF-KIDNEY-RAW": {
        "price_pln_per_kg": "19.00",
        "observed_at": "2026-09-26",
        "source_label": "Publiczny ranking legacy v1.2",
        "source_url": LEGACY_PRICE_SOURCE,
        "confidence": "Wysoka",
        "note": "Cena odzyskana ze starego publicznego rankingu.",
    },
    "BEEF-HEART-RAW": {
        "price_pln_per_kg": "33.00",
        "observed_at": "2026-09-26",
        "source_label": "Publiczny ranking legacy v1.2",
        "source_url": LEGACY_PRICE_SOURCE,
        "confidence": "Średnia",
        "note": "Cena odzyskana ze starego publicznego rankingu.",
    },
    "BEEF-GROUND-9010-RAW": {
        "price_pln_per_kg": "70.00",
        "observed_at": "2026-09-26",
        "source_label": "Publiczny ranking legacy v1.2",
        "source_url": LEGACY_PRICE_SOURCE,
        "confidence": "Średnia",
        "note": "Cena odzyskana ze starego publicznego rankingu.",
    },
}

PRICE_COLUMNS = [
    "product_id",
    "name_pl",
    "price_pln_per_kg",
    "observed_at",
    "source_label",
    "source_url",
    "confidence",
    "note",
    "active",
]

ALL_RESULT_COLUMNS = [
    "economic_place",
    "product_id",
    "name_pl",
    "category",
    "state",
    "core_place",
    "core_score",
    "portion_place",
    "portion_g",
    "portion_score",
    "price_pln_per_kg",
    "cost_100g_pln",
    "cost_portion_pln",
    "core_points_per_pln_100g",
    "portion_points_per_pln",
    "price_type",
    "price_date",
    "price_age_days",
    "price_confidence",
    "price_source_label",
    "price_source_url",
    "price_note",
    "price_status",
    "qualified",
    "methodology_version",
]

EXCEPTION_COLUMNS = [
    "product_id",
    "name_pl",
    "severity",
    "code",
    "message",
]


@dataclass
class PriceCandidate:
    product_id: str
    price_type: str
    price_pln_per_kg: float | None
    observed_at: date | None
    source_label: str
    source_url: str
    confidence: str
    note: str
    active: bool
    max_age_days: int
    validation_status: str = ""
    validation_message: str = ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Brakuje pliku: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {
                str(key).lstrip("\ufeff"): (
                    "" if value is None else str(value).strip()
                )
                for key, value in row.items()
            }
            for row in csv.DictReader(handle)
        ]


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    columns: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    column: format_output(row.get(column, ""))
                    for column in columns
                }
            )


def format_output(value: Any) -> Any:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "TAK" if value else "NIE"

    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.6f}".rstrip("0").rstrip(".")

    return value


def parse_float(value: Any) -> float | None:
    text = str(value or "").strip().replace(",", ".")

    if not text:
        return None

    try:
        number = float(text)
    except ValueError:
        return None

    if not math.isfinite(number):
        return None

    return number


def parse_date(value: Any) -> date | None:
    text = str(value or "").strip()

    if not text:
        return None

    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_bool(value: Any, default: bool = True) -> bool:
    text = str(value or "").strip().lower()

    if not text:
        return default

    return text in {
        "1",
        "true",
        "tak",
        "yes",
        "y",
        "active",
        "aktywny",
    }


def validate_unique(
    rows: list[dict[str, str]],
    key: str,
    label: str,
) -> None:
    values = [row.get(key, "").strip() for row in rows]

    if any(not value for value in values):
        raise RuntimeError(
            f"{label}: wykryto pustą wartość pola {key}."
        )

    duplicates = sorted(
        {
            value
            for value in values
            if values.count(value) > 1
        }
    )

    if duplicates:
        raise RuntimeError(
            f"{label}: duplikaty {key}: {duplicates}"
        )


def validate_url(url: str) -> bool:
    if not url:
        return False

    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def build_reference_prices(
    products: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for product in products:
        product_id = product["product_id"]
        source = LEGACY_REFERENCE_PRICES.get(product_id, {})

        rows.append(
            {
                "product_id": product_id,
                "name_pl": product["name_pl"],
                "price_pln_per_kg": source.get(
                    "price_pln_per_kg", ""
                ),
                "observed_at": source.get("observed_at", ""),
                "source_label": source.get("source_label", ""),
                "source_url": source.get("source_url", ""),
                "confidence": source.get("confidence", ""),
                "note": source.get(
                    "note",
                    "Brak zatwierdzonej ceny referencyjnej.",
                ),
                "active": (
                    "TAK"
                    if source.get("price_pln_per_kg")
                    else "NIE"
                ),
            }
        )

    write_csv(REFERENCE_PRICES, rows, PRICE_COLUMNS)
    return rows


def ensure_user_price_template(
    products: list[dict[str, str]],
) -> None:
    if USER_PRICES.exists():
        return

    rows = []

    for product in products:
        rows.append(
            {
                "product_id": product["product_id"],
                "name_pl": product["name_pl"],
                "price_pln_per_kg": "",
                "observed_at": "",
                "source_label": "",
                "source_url": "",
                "confidence": "",
                "note": "",
                "active": "NIE",
            }
        )

    write_csv(USER_PRICES, rows, PRICE_COLUMNS)


def validate_user_catalog(
    rows: list[dict[str, str]],
    product_ids: set[str],
) -> None:
    validate_unique(rows, "product_id", "Ceny użytkownika")

    row_ids = {row["product_id"] for row in rows}

    unknown = sorted(row_ids - product_ids)
    missing = sorted(product_ids - row_ids)

    if unknown:
        raise RuntimeError(
            f"Ceny użytkownika zawierają obce produkty: {unknown}"
        )

    if missing:
        raise RuntimeError(
            f"W cenach użytkownika brakuje produktów: {missing}"
        )


def make_candidate(
    row: dict[str, str],
    price_type: str,
) -> PriceCandidate:
    if price_type == "USER":
        max_age = USER_PRICE_MAX_AGE_DAYS
    else:
        max_age = REFERENCE_PRICE_MAX_AGE_DAYS

    return PriceCandidate(
        product_id=row.get("product_id", ""),
        price_type=price_type,
        price_pln_per_kg=parse_float(
            row.get("price_pln_per_kg")
        ),
        observed_at=parse_date(row.get("observed_at")),
        source_label=row.get("source_label", "").strip(),
        source_url=row.get("source_url", "").strip(),
        confidence=row.get("confidence", "").strip(),
        note=row.get("note", "").strip(),
        active=parse_bool(row.get("active"), default=False),
        max_age_days=max_age,
    )


def assess_candidate(
    candidate: PriceCandidate,
    today: date,
) -> PriceCandidate:
    if not candidate.active:
        candidate.validation_status = "INACTIVE"
        candidate.validation_message = "Cena jest nieaktywna."
        return candidate

    if candidate.price_pln_per_kg is None:
        candidate.validation_status = "MISSING_PRICE"
        candidate.validation_message = "Brak poprawnej ceny."
        return candidate

    if candidate.price_pln_per_kg <= 0:
        candidate.validation_status = "INVALID_PRICE"
        candidate.validation_message = (
            "Cena musi być większa od zera."
        )
        return candidate

    if candidate.price_pln_per_kg > 10000:
        candidate.validation_status = "INVALID_PRICE"
        candidate.validation_message = (
            "Cena przekracza limit kontrolny 10 000 zł/kg."
        )
        return candidate

    if candidate.observed_at is None:
        candidate.validation_status = "MISSING_DATE"
        candidate.validation_message = (
            "Brak poprawnej daty YYYY-MM-DD."
        )
        return candidate

    age = (today - candidate.observed_at).days

    if age < 0:
        candidate.validation_status = "FUTURE_PRICE"
        candidate.validation_message = (
            "Data ceny znajduje się w przyszłości."
        )
        return candidate

    if age > candidate.max_age_days:
        candidate.validation_status = "STALE_PRICE"
        candidate.validation_message = (
            f"Cena ma {age} dni; limit wynosi "
            f"{candidate.max_age_days} dni."
        )
        return candidate

    if not candidate.source_label:
        candidate.validation_status = "MISSING_SOURCE"
        candidate.validation_message = (
            "Brak nazwy źródła ceny."
        )
        return candidate

    if (
        candidate.price_type == "REFERENCE"
        and not validate_url(candidate.source_url)
    ):
        candidate.validation_status = "MISSING_SOURCE_URL"
        candidate.validation_message = (
            "Cena referencyjna wymaga publicznego adresu źródła."
        )
        return candidate

    candidate.validation_status = "CURRENT"
    candidate.validation_message = "Cena aktualna."
    return candidate


def select_price(
    user_row: dict[str, str],
    reference_row: dict[str, str],
    today: date,
) -> tuple[PriceCandidate | None, list[PriceCandidate]]:
    checked: list[PriceCandidate] = []

    for row, price_type in (
        (user_row, "USER"),
        (reference_row, "REFERENCE"),
    ):
        candidate = assess_candidate(
            make_candidate(row, price_type),
            today,
        )
        checked.append(candidate)

        if candidate.validation_status == "CURRENT":
            return candidate, checked

    return None, checked


def candidate_age(
    candidate: PriceCandidate,
    today: date,
) -> int | None:
    if candidate.observed_at is None:
        return None
    return (today - candidate.observed_at).days


def fallback_status(
    candidates: list[PriceCandidate],
) -> tuple[str, str]:
    active = [
        candidate
        for candidate in candidates
        if candidate.active
    ]

    if not active:
        return (
            "MISSING_PRICE",
            "Brak aktywnej ceny użytkownika i ceny referencyjnej.",
        )

    priority = [
        "FUTURE_PRICE",
        "STALE_PRICE",
        "MISSING_DATE",
        "MISSING_SOURCE_URL",
        "MISSING_SOURCE",
        "INVALID_PRICE",
        "MISSING_PRICE",
    ]

    for status in priority:
        matching = [
            candidate
            for candidate in active
            if candidate.validation_status == status
        ]

        if matching:
            return status, matching[0].validation_message

    return "MISSING_PRICE", "Brak ceny kwalifikującej się."


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        raise RuntimeError(
            "Próba dzielenia przez koszt mniejszy lub równy zero."
        )

    result = numerator / denominator

    if not math.isfinite(result):
        raise RuntimeError("Wynik ekonomiczny nie jest skończony.")

    return result


def build_price_readme() -> None:
    content = f"""# Rejestr cen — metodologia v2.5

## Kolejność wyboru ceny

1. Aktywna i aktualna cena użytkownika.
2. Aktywna i aktualna cena referencyjna.
3. Brak kwalifikacji do rankingu ekonomicznego.

Brak ceny nigdy nie jest zamieniany na zero.

## Ważność

- cena użytkownika: {USER_PRICE_MAX_AGE_DAYS} dni,
- cena referencyjna: {REFERENCE_PRICE_MAX_AGE_DAYS} dni.

## Format ceny użytkownika

Plik `data/prices/user-prices.csv` zawiera jeden wiersz dla każdego
produktu. Cena podawana jest w PLN za kilogram jadalnego produktu
odpowiadającego stanowi opisanemu w rankingu.

Aby aktywować cenę, należy podać:

- `price_pln_per_kg`,
- `observed_at` w formacie `YYYY-MM-DD`,
- `source_label`,
- opcjonalnie `source_url`,
- `active` ustawione na `TAK`.

Cena użytkownika nie jest automatycznie uznawana za cenę rynkową.
Może oznaczać paragon, lokalny sklep albo koszt własnej produkcji,
jeżeli zostanie to jasno opisane w polu `source_label` i `note`.

## Wzory

- koszt 100 g = cena za kg / 10,
- koszt porcji = cena za kg × porcja w gramach / 1000,
- punkty bazowe za 1 zł = wynik bazowy / koszt 100 g,
- punkty porcji za 1 zł = wynik porcji / koszt porcji.

Wersja: `{VERSION}`.
"""

    PRICE_README.write_text(
        content.strip() + "\n",
        encoding="utf-8",
    )


def build_html(
    all_rows: list[dict[str, Any]],
    qualified: list[dict[str, Any]],
    today: date,
) -> None:
    qualified_table = []

    for row in qualified:
        source_url = html.escape(
            str(row.get("price_source_url", ""))
        )

        if source_url:
            source_cell = (
                f'<a href="{source_url}" '
                f'target="_blank" rel="noopener">źródło</a>'
            )
        else:
            source_cell = html.escape(
                str(row.get("price_source_label", ""))
            )

        qualified_table.append(
            "<tr>"
            f"<td>{row['economic_place']}</td>"
            f"<td>{html.escape(str(row['name_pl']))}</td>"
            f"<td>{row['price_pln_per_kg']:.2f}</td>"
            f"<td>{row['portion_g']:.0f}</td>"
            f"<td>{row['cost_portion_pln']:.2f}</td>"
            f"<td>{row['portion_score']:.2f}</td>"
            f"<td><strong>{row['portion_points_per_pln']:.2f}</strong></td>"
            f"<td>{html.escape(str(row['price_type']))}</td>"
            f"<td>{html.escape(str(row['price_date']))}</td>"
            f"<td>{source_cell}</td>"
            "</tr>"
        )

    status_counts: dict[str, int] = {}

    for row in all_rows:
        status = str(row["price_status"])
        status_counts[status] = status_counts.get(status, 0) + 1

    status_items = "".join(
        f"<li><strong>{html.escape(status)}</strong>: {count}</li>"
        for status, count in sorted(status_counts.items())
    )

    if qualified_table:
        table_body = "\n".join(qualified_table)
    else:
        table_body = (
            '<tr><td colspan="10">'
            "Brak produktów z aktualną ceną."
            "</td></tr>"
        )

    page = f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Indeks żywności — wartość za 1 zł</title>
  <style>
    :root {{
      color-scheme: light;
      --green: #275d38;
      --light: #eef5ed;
      --border: #d7dfd5;
      --warning: #fff4d6;
    }}
    body {{
      max-width: 1500px;
      margin: 30px auto;
      padding: 18px;
      font-family: system-ui, sans-serif;
      color: #20251f;
      background: #f3f5ef;
    }}
    h1, h2 {{
      color: var(--green);
    }}
    .box {{
      margin: 20px 0;
      padding: 20px;
      background: white;
      border-radius: 14px;
      box-shadow: 0 4px 18px #0001;
      overflow-x: auto;
    }}
    .warning {{
      padding: 16px;
      border-left: 5px solid #c58b00;
      background: var(--warning);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 1100px;
    }}
    th, td {{
      padding: 10px;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }}
    th {{
      background: var(--light);
      position: sticky;
      top: 0;
    }}
    a {{
      color: var(--green);
    }}
    .metric {{
      display: inline-block;
      margin: 6px;
      padding: 12px 16px;
      border-radius: 10px;
      background: var(--light);
    }}
    code {{
      background: #eef0ec;
      padding: 2px 5px;
      border-radius: 4px;
    }}
  </style>
</head>
<body>
  <h1>Wartość odżywcza za 1 zł</h1>

  <section class="warning">
    <strong>Pilot ekonomiczny.</strong>
    Wynik zależy od ceny, daty, gramatury porcji i stanu produktu.
    Brak ceny nie jest traktowany jako cena zerowa. Ranking cenowy
    nie oznacza automatycznie najlepszego produktu dla konkretnej osoby.
  </section>

  <section class="box">
    <span class="metric">
      Produkty ogółem: <strong>{len(all_rows)}</strong>
    </span>
    <span class="metric">
      Z aktualną ceną: <strong>{len(qualified)}</strong>
    </span>
    <span class="metric">
      Bez kwalifikacji cenowej:
      <strong>{len(all_rows) - len(qualified)}</strong>
    </span>
    <p>Data obliczenia: <strong>{today.isoformat()}</strong></p>
    <p>Metodologia: <strong>{VERSION}</strong></p>
  </section>

  <section class="box">
    <h2>Ranking porcji za 1 zł</h2>
    <table>
      <thead>
        <tr>
          <th>Miejsce</th>
          <th>Produkt</th>
          <th>Cena zł/kg</th>
          <th>Porcja g</th>
          <th>Koszt porcji</th>
          <th>Punkty porcji</th>
          <th>Punkty za 1 zł</th>
          <th>Typ ceny</th>
          <th>Data ceny</th>
          <th>Źródło</th>
        </tr>
      </thead>
      <tbody>
        {table_body}
      </tbody>
    </table>
  </section>

  <section class="box">
    <h2>Status cen</h2>
    <ul>{status_items}</ul>
    <p>
      Ceny użytkownika są ważne przez
      <strong>{USER_PRICE_MAX_AGE_DAYS} dni</strong>,
      a referencyjne przez
      <strong>{REFERENCE_PRICE_MAX_AGE_DAYS} dni</strong>.
    </p>
  </section>

  <section class="box">
    <h2>Jak czytać wynik?</h2>
    <ul>
      <li>Wynik bazowy pozostaje niezależny od ceny.</li>
      <li>Cena nie wpływa na ocenę odżywczą produktu.</li>
      <li>
        Ranking ekonomiczny jest jedynie ilorazem punktów i kosztu.
      </li>
      <li>
        Produkty bez aktualnej ceny pozostają widoczne w raporcie,
        ale nie otrzymują miejsca ekonomicznego.
      </li>
    </ul>
    <p>
      <a href="portion.html">Ranking praktycznej porcji</a>
      ·
      <a href="index.html">Ranking składu odżywczego</a>
    </p>
  </section>
</body>
</html>
"""

    HTML_OUTPUT.write_text(page, encoding="utf-8")


def main() -> None:
    today_text = os.environ.get("ECONOMY_TODAY", "").strip()
    today = parse_date(today_text) if today_text else date.today()

    if today is None:
        raise RuntimeError(
            "ECONOMY_TODAY musi mieć format YYYY-MM-DD."
        )

    core_rows = read_csv(CORE_RANKING)
    portion_rows = read_csv(PORTION_RANKING)

    if len(core_rows) != 30:
        raise RuntimeError(
            f"Ranking bazowy ma {len(core_rows)}/30 produktów."
        )

    if len(portion_rows) != 30:
        raise RuntimeError(
            f"Ranking porcji ma {len(portion_rows)}/30 produktów."
        )

    validate_unique(
        core_rows,
        "product_id",
        "Ranking bazowy",
    )
    validate_unique(
        portion_rows,
        "product_id",
        "Ranking porcji",
    )

    core_by_id = {
        row["product_id"]: row
        for row in core_rows
    }
    portion_by_id = {
        row["product_id"]: row
        for row in portion_rows
    }

    if set(core_by_id) != set(portion_by_id):
        raise RuntimeError(
            "Lista produktów rankingu bazowego i porcji jest różna."
        )

    reference_rows = build_reference_prices(core_rows)
    ensure_user_price_template(core_rows)
    build_price_readme()

    user_rows = read_csv(USER_PRICES)
    validate_user_catalog(user_rows, set(core_by_id))

    reference_by_id = {
        row["product_id"]: row
        for row in reference_rows
    }
    user_by_id = {
        row["product_id"]: row
        for row in user_rows
    }

    all_results: list[dict[str, Any]] = []
    exceptions: list[dict[str, str]] = []

    for product_id, core in core_by_id.items():
        portion = portion_by_id[product_id]

        selected, checked = select_price(
            user_by_id[product_id],
            reference_by_id[product_id],
            today,
        )

        core_score = parse_float(
            core.get("score_cautious")
        )
        portion_score = parse_float(
            portion.get("portion_score_cautious")
        )
        portion_g = parse_float(portion.get("portion_g"))

        if core_score is None or core_score < 0:
            raise RuntimeError(
                f"{product_id}: niepoprawny wynik bazowy."
            )

        if portion_score is None or portion_score < 0:
            raise RuntimeError(
                f"{product_id}: niepoprawny wynik porcji."
            )

        if portion_g is None or portion_g <= 0:
            raise RuntimeError(
                f"{product_id}: niepoprawna wielkość porcji."
            )

        result: dict[str, Any] = {
            "economic_place": "",
            "product_id": product_id,
            "name_pl": core["name_pl"],
            "category": core["category"],
            "state": core["state"],
            "core_place": core["place"],
            "core_score": core_score,
            "portion_place": portion["portion_place"],
            "portion_g": portion_g,
            "portion_score": portion_score,
            "price_pln_per_kg": None,
            "cost_100g_pln": None,
            "cost_portion_pln": None,
            "core_points_per_pln_100g": None,
            "portion_points_per_pln": None,
            "price_type": "",
            "price_date": "",
            "price_age_days": None,
            "price_confidence": "",
            "price_source_label": "",
            "price_source_url": "",
            "price_note": "",
            "price_status": "",
            "qualified": False,
            "methodology_version": VERSION,
        }

        if selected is None:
            status, message = fallback_status(checked)
            result["price_status"] = status

            exceptions.append(
                {
                    "product_id": product_id,
                    "name_pl": core["name_pl"],
                    "severity": "info",
                    "code": status,
                    "message": message,
                }
            )
        else:
            assert selected.price_pln_per_kg is not None
            assert selected.observed_at is not None

            price = selected.price_pln_per_kg
            cost_100g = price / 10.0
            cost_portion = price * portion_g / 1000.0

            result.update(
                {
                    "price_pln_per_kg": price,
                    "cost_100g_pln": cost_100g,
                    "cost_portion_pln": cost_portion,
                    "core_points_per_pln_100g": safe_divide(
                        core_score,
                        cost_100g,
                    ),
                    "portion_points_per_pln": safe_divide(
                        portion_score,
                        cost_portion,
                    ),
                    "price_type": selected.price_type,
                    "price_date": selected.observed_at.isoformat(),
                    "price_age_days": candidate_age(
                        selected,
                        today,
                    ),
                    "price_confidence": selected.confidence,
                    "price_source_label": selected.source_label,
                    "price_source_url": selected.source_url,
                    "price_note": selected.note,
                    "price_status": "CURRENT",
                    "qualified": True,
                }
            )

        all_results.append(result)

    qualified = [
        row
        for row in all_results
        if row["qualified"]
    ]

    qualified.sort(
        key=lambda row: (
            -float(row["portion_points_per_pln"]),
            -float(row["core_points_per_pln_100g"]),
            str(row["product_id"]),
        )
    )

    for place, row in enumerate(qualified, start=1):
        row["economic_place"] = place

    place_by_id = {
        row["product_id"]: row["economic_place"]
        for row in qualified
    }

    for row in all_results:
        row["economic_place"] = place_by_id.get(
            row["product_id"],
            "",
        )

    all_results.sort(
        key=lambda row: (
            0 if row["qualified"] else 1,
            (
                row["economic_place"]
                if row["economic_place"] != ""
                else 9999
            ),
            str(row["name_pl"]),
        )
    )

    write_csv(
        ALL_RESULTS,
        all_results,
        ALL_RESULT_COLUMNS,
    )
    write_csv(
        QUALIFIED_RESULTS,
        qualified,
        ALL_RESULT_COLUMNS,
    )
    write_csv(
        EXCEPTIONS,
        exceptions,
        EXCEPTION_COLUMNS,
    )

    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT.write_text(
        json.dumps(
            {
                "methodology_version": VERSION,
                "calculation_date": today.isoformat(),
                "currency": "PLN",
                "price_unit": "kg",
                "products_total": len(all_results),
                "products_qualified": len(qualified),
                "products_without_current_price": (
                    len(all_results) - len(qualified)
                ),
                "ranking": qualified,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    build_html(all_results, qualified, today)

    summary = {
        "methodology_version": VERSION,
        "calculation_date": today.isoformat(),
        "products_total": len(all_results),
        "products_qualified": len(qualified),
        "products_without_current_price": (
            len(all_results) - len(qualified)
        ),
        "user_prices_used": sum(
            1
            for row in qualified
            if row["price_type"] == "USER"
        ),
        "reference_prices_used": sum(
            1
            for row in qualified
            if row["price_type"] == "REFERENCE"
        ),
        "exceptions": len(exceptions),
    }

    SUMMARY_OUTPUT.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if len(all_results) != 30:
        raise RuntimeError(
            f"Raport ekonomiczny ma {len(all_results)}/30 produktów."
        )

    if len(reference_rows) != 30:
        raise RuntimeError(
            f"Rejestr referencyjny ma {len(reference_rows)}/30 produktów."
        )

    if len(user_rows) != 30:
        raise RuntimeError(
            f"Rejestr użytkownika ma {len(user_rows)}/30 produktów."
        )

    for row in qualified:
        if float(row["price_pln_per_kg"]) <= 0:
            raise RuntimeError(
                f"{row['product_id']}: cena nie jest dodatnia."
            )

        if float(row["cost_portion_pln"]) <= 0:
            raise RuntimeError(
                f"{row['product_id']}: koszt porcji nie jest dodatni."
            )

        if float(row["portion_points_per_pln"]) < 0:
            raise RuntimeError(
                f"{row['product_id']}: ujemny wynik ekonomiczny."
            )

    print(
        "ETAP 60 ZAKOŃCZONY — "
        f"produkty: {len(all_results)}; "
        f"aktualne ceny: {len(qualified)}; "
        f"brak aktualnej ceny: "
        f"{len(all_results) - len(qualified)}."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"BŁĄD ETAPU 60: {exc}", file=sys.stderr)
        raise

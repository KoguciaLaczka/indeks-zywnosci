from __future__ import annotations

import csv
import html
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "public"

API_URL = "https://api.nal.usda.gov/fdc/v1/food"

NUTRIENT_CAP = 120.0
WEIGHT_100G = 0.60
WEIGHT_100KCAL = 0.40

GROUP_WEIGHTS = {
    "minerals": 0.30,
    "vitamins": 0.30,
    "protein_and_amino_acids": 0.20,
    "fatty_acids": 0.10,
    "fiber_and_functional": 0.10,
}

# NRV UE 1169/2011, o ile nie opisano inaczej.
# Wartości pilotażowe dla choliny, błonnika i kwasów
# tłuszczowych pozostają jawnie oznaczone jako dodatkowe.
NUTRIENTS = [
    {
        "key": "protein",
        "name_pl": "Białko",
        "group": "protein_and_amino_acids",
        "fdc_ids": [1003],
        "reference": 50.0,
        "unit": "g",
        "reference_source": "UE RI",
    },
    {
        "key": "vitamin_a_rae",
        "name_pl": "Witamina A (RAE)",
        "group": "vitamins",
        "fdc_ids": [1106],
        "reference": 800.0,
        "unit": "ug",
        "reference_source": "UE NRV",
    },
    {
        "key": "vitamin_c",
        "name_pl": "Witamina C",
        "group": "vitamins",
        "fdc_ids": [1162],
        "reference": 80.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "vitamin_d",
        "name_pl": "Witamina D",
        "group": "vitamins",
        "fdc_ids": [1114],
        "reference": 5.0,
        "unit": "ug",
        "reference_source": "UE NRV",
    },
    {
        "key": "vitamin_e",
        "name_pl": "Witamina E",
        "group": "vitamins",
        "fdc_ids": [1109],
        "reference": 12.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "vitamin_k",
        "name_pl": "Witamina K",
        "group": "vitamins",
        "fdc_ids": [1185],
        "reference": 75.0,
        "unit": "ug",
        "reference_source": "UE NRV",
    },
    {
        "key": "thiamin",
        "name_pl": "Tiamina B1",
        "group": "vitamins",
        "fdc_ids": [1165],
        "reference": 1.1,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "riboflavin",
        "name_pl": "Ryboflawina B2",
        "group": "vitamins",
        "fdc_ids": [1166],
        "reference": 1.4,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "niacin",
        "name_pl": "Niacyna B3",
        "group": "vitamins",
        "fdc_ids": [1167],
        "reference": 16.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "pantothenic_acid",
        "name_pl": "Kwas pantotenowy B5",
        "group": "vitamins",
        "fdc_ids": [1170],
        "reference": 6.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "vitamin_b6",
        "name_pl": "Witamina B6",
        "group": "vitamins",
        "fdc_ids": [1175],
        "reference": 1.4,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "folate",
        "name_pl": "Foliany",
        "group": "vitamins",
        "fdc_ids": [1177],
        "reference": 200.0,
        "unit": "ug",
        "reference_source": "UE NRV",
    },
    {
        "key": "vitamin_b12",
        "name_pl": "Witamina B12",
        "group": "vitamins",
        "fdc_ids": [1178],
        "reference": 2.5,
        "unit": "ug",
        "reference_source": "UE NRV",
    },
    {
        "key": "choline",
        "name_pl": "Cholina",
        "group": "vitamins",
        "fdc_ids": [1180],
        "reference": 400.0,
        "unit": "mg",
        "reference_source": "EFSA AI — warstwa dodatkowa",
    },
    {
        "key": "calcium",
        "name_pl": "Wapń",
        "group": "minerals",
        "fdc_ids": [1087],
        "reference": 800.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "iron",
        "name_pl": "Żelazo",
        "group": "minerals",
        "fdc_ids": [1089],
        "reference": 14.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "magnesium",
        "name_pl": "Magnez",
        "group": "minerals",
        "fdc_ids": [1090],
        "reference": 375.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "phosphorus",
        "name_pl": "Fosfor",
        "group": "minerals",
        "fdc_ids": [1091],
        "reference": 700.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "potassium",
        "name_pl": "Potas",
        "group": "minerals",
        "fdc_ids": [1092],
        "reference": 2000.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "zinc",
        "name_pl": "Cynk",
        "group": "minerals",
        "fdc_ids": [1095],
        "reference": 10.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "copper",
        "name_pl": "Miedź",
        "group": "minerals",
        "fdc_ids": [1098],
        "reference": 1.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "manganese",
        "name_pl": "Mangan",
        "group": "minerals",
        "fdc_ids": [1101],
        "reference": 2.0,
        "unit": "mg",
        "reference_source": "UE NRV",
    },
    {
        "key": "selenium",
        "name_pl": "Selen",
        "group": "minerals",
        "fdc_ids": [1103],
        "reference": 55.0,
        "unit": "ug",
        "reference_source": "UE NRV",
    },
    {
        "key": "fiber",
        "name_pl": "Błonnik",
        "group": "fiber_and_functional",
        "fdc_ids": [1079],
        "reference": 25.0,
        "unit": "g",
        "reference_source": "wartość referencyjna pilota",
    },
    {
        "key": "ala",
        "name_pl": "ALA omega-3",
        "group": "fatty_acids",
        "fdc_ids": [1404],
        "reference": 2.0,
        "unit": "g",
        "reference_source": "wartość referencyjna pilota",
    },
    {
        "key": "linoleic_acid",
        "name_pl": "LA omega-6",
        "group": "fatty_acids",
        "fdc_ids": [1269],
        "reference": 10.0,
        "unit": "g",
        "reference_source": "wartość referencyjna pilota",
    },
]

AMINO_ACIDS = {
    "histidine": [1221],
    "isoleucine": [1212],
    "leucine": [1213],
    "lysine": [1214],
    "methionine": [1215],
    "cystine": [1216],
    "phenylalanine": [1217],
    "tyrosine": [1218],
    "threonine": [1211],
    "tryptophan": [1210],
    "valine": [1219],
}

# Wzorzec FAO dla dorosłych, mg/g białka.
AMINO_REFERENCE = {
    "histidine": 15.0,
    "isoleucine": 30.0,
    "leucine": 59.0,
    "lysine": 45.0,
    "sulfur": 22.0,
    "aromatic": 38.0,
    "threonine": 23.0,
    "tryptophan": 6.0,
    "valine": 39.0,
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            value,
            handle,
            ensure_ascii=False,
            indent=2,
        )


def read_catalog() -> list[dict[str, str]]:
    path = DATA_DIR / "catalog" / "pilot-products.csv"

    with path.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as handle:
        return list(csv.DictReader(handle))


def normalize_unit(value: str | None) -> str:
    unit = str(value or "").strip().lower()

    replacements = {
        "µg": "ug",
        "μg": "ug",
        "mcg": "ug",
        "kcal": "kcal",
    }

    return replacements.get(unit, unit)


def convert_unit(
    amount: float,
    source_unit: str,
    target_unit: str,
) -> float:
    source = normalize_unit(source_unit)
    target = normalize_unit(target_unit)

    if source == target:
        return amount

    to_grams = {
        "g": 1.0,
        "mg": 0.001,
        "ug": 0.000001,
    }

    if source not in to_grams or target not in to_grams:
        raise ValueError(
            f"Nieobsługiwana konwersja: "
            f"{source_unit} → {target_unit}"
        )

    grams = amount * to_grams[source]
    return grams / to_grams[target]


def nutrient_rows(food: dict[str, Any]) -> list[dict[str, Any]]:
    result = []

    for row in food.get("foodNutrients", []):
        nutrient = row.get("nutrient") or {}

        nutrient_id = (
            nutrient.get("id")
            or row.get("nutrientId")
        )

        amount = row.get("amount")

        if amount is None:
            continue

        result.append(
            {
                "id": int(nutrient_id),
                "name": nutrient.get("name")
                    or row.get("nutrientName")
                    or "",
                "unit": nutrient.get("unitName")
                    or row.get("unitName")
                    or "",
                "amount": float(amount),
            }
        )

    return result


def find_nutrient(
    rows: list[dict[str, Any]],
    ids: list[int],
    target_unit: str,
) -> dict[str, Any] | None:
    by_id = {
        int(row["id"]): row
        for row in rows
    }

    for nutrient_id in ids:
        row = by_id.get(int(nutrient_id))

        if not row:
            continue

        value = convert_unit(
            row["amount"],
            row["unit"],
            target_unit,
        )

        return {
            "value": value,
            "source_unit": row["unit"],
            "source_name": row["name"],
            "fdc_nutrient_id": nutrient_id,
        }

    return None


def find_energy(
    rows: list[dict[str, Any]]
) -> dict[str, Any] | None:
    preferred_ids = [1008, 2047, 2048]

    for nutrient_id in preferred_ids:
        for row in rows:
            if int(row["id"]) != nutrient_id:
                continue

            if normalize_unit(row["unit"]) != "kcal":
                continue

            value = float(row["amount"])

            if 1.0 <= value <= 900.0:
                return {
                    "value": value,
                    "fdc_nutrient_id": nutrient_id,
                    "source_name": row["name"],
                    "source": "USDA direct",
                }

    return None


def amino_acid_score(
    rows: list[dict[str, Any]],
    protein_g: float | None,
) -> dict[str, Any] | None:
    if not protein_g or protein_g <= 0:
        return None

    amounts = {}

    for key, ids in AMINO_ACIDS.items():
        nutrient = find_nutrient(
            rows,
            ids,
            "g"
        )

        if nutrient is None:
            return None

        amounts[key] = nutrient["value"]

    actual = {
        "histidine":
            amounts["histidine"] * 1000 / protein_g,
        "isoleucine":
            amounts["isoleucine"] * 1000 / protein_g,
        "leucine":
            amounts["leucine"] * 1000 / protein_g,
        "lysine":
            amounts["lysine"] * 1000 / protein_g,
        "sulfur":
            (
                amounts["methionine"]
                + amounts["cystine"]
            )
            * 1000
            / protein_g,
        "aromatic":
            (
                amounts["phenylalanine"]
                + amounts["tyrosine"]
            )
            * 1000
            / protein_g,
        "threonine":
            amounts["threonine"] * 1000 / protein_g,
        "tryptophan":
            amounts["tryptophan"] * 1000 / protein_g,
        "valine":
            amounts["valine"] * 1000 / protein_g,
    }

    ratios = {
        key: actual[key] / AMINO_REFERENCE[key] * 100
        for key in AMINO_REFERENCE
    }

    limiting = min(
        ratios,
        key=ratios.get
    )

    score = ratios[limiting]

    return {
        "score": score,
        "capped_score": min(score, NUTRIENT_CAP),
        "limiting": limiting,
        "actual_mg_g_protein": actual,
        "ratios": ratios,
        "method":
            "AAS wg wzorca FAO dla dorosłych; nie DIAAS",
    }


def fetch_food(
    session: requests.Session,
    api_key: str,
    fdc_id: str,
) -> dict[str, Any]:
    response = session.get(
        f"{API_URL}/{fdc_id}",
        params={"api_key": api_key},
        timeout=45,
    )

    response.raise_for_status()
    return response.json()


def score_component(
    value: float,
    reference: float,
    energy: float,
) -> tuple[float, float, float]:
    per_100g = min(
        value / reference * 100.0,
        NUTRIENT_CAP,
    )

    per_100kcal_value = value / energy * 100.0

    per_100kcal = min(
        per_100kcal_value
        / reference
        * 100.0,
        NUTRIENT_CAP,
    )

    combined = (
        WEIGHT_100G * per_100g
        + WEIGHT_100KCAL * per_100kcal
    )

    return per_100g, per_100kcal, combined


def product_status(completeness: float) -> str:
    if completeness >= 0.80:
        return "Pełny profil pilotażowy"

    if completeness >= 0.60:
        return "Profil warunkowy"

    return "Profil eksperymentalny"


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(rows)


def security_check(api_key: str) -> None:
    forbidden = []

    for root_name in [
        "config",
        "data",
        "public",
        "src",
        "tests",
    ]:
        root = ROOT / root_name

        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            try:
                content = path.read_text(
                    encoding="utf-8"
                )
            except UnicodeDecodeError:
                continue

            if api_key and api_key in content:
                forbidden.append(
                    str(path.relative_to(ROOT))
                )

    if forbidden:
        raise RuntimeError(
            "Klucz USDA wykryto w plikach: "
            + ", ".join(forbidden)
        )


def build_html(
    ranking: list[dict[str, Any]],
    components: list[dict[str, Any]],
    exceptions: list[dict[str, Any]],
    methodology: dict[str, Any],
) -> str:
    ranking_rows = []

    for row in ranking:
        ranking_rows.append(
            "<tr>"
            f"<td>{row['place']}</td>"
            f"<td>{html.escape(row['name_pl'])}</td>"
            f"<td>{row['score_cautious']:.2f}</td>"
            f"<td>{row['completeness_percent']:.1f}%</td>"
            f"<td>{html.escape(row['status'])}</td>"
            "</tr>"
        )

    component_rows = []

    for row in components:
        value = (
            ""
            if row["value"] == ""
            else f"{float(row['value']):.4g}"
        )

        weighted = (
            ""
            if row["weighted_score"] == ""
            else f"{float(row['weighted_score']):.2f}"
        )

        component_rows.append(
            "<tr>"
            f"<td>{html.escape(row['name_pl'])}</td>"
            f"<td>{html.escape(row['nutrient_name'])}</td>"
            f"<td>{value}</td>"
            f"<td>{html.escape(row['unit'])}</td>"
            f"<td>{weighted}</td>"
            f"<td>{html.escape(row['data_status'])}</td>"
            "</tr>"
        )

    exception_text = (
        "Brak wyjątków krytycznych."
        if not exceptions
        else f"Liczba wyjątków: {len(exceptions)}."
    )

    return f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport"
        content="width=device-width, initial-scale=1">
  <title>Indeks żywności — pilot v2</title>
  <style>
    body {{
      max-width: 1200px;
      margin: 40px auto;
      padding: 20px;
      font-family: system-ui, sans-serif;
      color: #20251f;
      background: #f6f7f2;
    }}
    h1, h2 {{ color: #274e13; }}
    .box {{
      background: white;
      padding: 24px;
      margin: 20px 0;
      border-radius: 14px;
      box-shadow: 0 4px 18px #0001;
      overflow-x: auto;
    }}
    .pilot {{
      display: inline-block;
      padding: 7px 12px;
      border-radius: 999px;
      background: #fff2cc;
      font-weight: 700;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 9px;
      border-bottom: 1px solid #ddd;
      text-align: left;
    }}
    th {{
      background: #d9ead3;
    }}
    .warning {{
      border-left: 5px solid #bf9000;
      padding: 15px;
      background: #fff8dd;
    }}
  </style>
</head>
<body>
  <span class="pilot">PILOT v2.0</span>
  <h1>Indeks żywności Kogucia Łączka</h1>

  <div class="warning">
    Wyniki testowe. Metodologia nie została jeszcze
    zatwierdzona jako wersja produkcyjna.
  </div>

  <section class="box">
    <h2>Ranking pilotażowy</h2>
    <table>
      <thead>
        <tr>
          <th>Miejsce</th>
          <th>Produkt</th>
          <th>Wynik ostrożnościowy</th>
          <th>Kompletność</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {''.join(ranking_rows)}
      </tbody>
    </table>
  </section>

  <section class="box">
    <h2>Rozkład punktów</h2>
    <table>
      <thead>
        <tr>
          <th>Produkt</th>
          <th>Składnik</th>
          <th>Wartość/100 g</th>
          <th>Jednostka</th>
          <th>Wynik składnika</th>
          <th>Status danych</th>
        </tr>
      </thead>
      <tbody>
        {''.join(component_rows)}
      </tbody>
    </table>
  </section>

  <section class="box">
    <h2>Kontrola</h2>
    <p>{html.escape(exception_text)}</p>
    <p>
      Metodologia:
      {html.escape(methodology['version'])}.
    </p>
    <p>
      60% wyniku na 100 g oraz 40% na 100 kcal.
      Limit pojedynczego składnika: 120 punktów.
    </p>
  </section>
</body>
</html>
"""


def main() -> None:
    api_key = os.environ.get(
        "USDA_API_KEY",
        ""
    ).strip()

    if not api_key:
        raise SystemExit(
            "Brakuje sekretu USDA_API_KEY."
        )

    methodology = read_json(
        CONFIG_DIR / "methodology-v2.json"
    )

    catalog = read_catalog()

    if len(catalog) != 3:
        raise RuntimeError(
            "Pilot musi zawierać dokładnie 3 produkty."
        )

    product_ids = [
        row["product_id"]
        for row in catalog
    ]

    if len(product_ids) != len(set(product_ids)):
        raise RuntimeError(
            "Wykryto duplikaty product_id."
        )

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent":
                "KoguciaLaczka-IndeksZywnosci/2.0"
        }
    )

    normalized = []
    components = []
    ranking = []
    exceptions = []

    total_components = len(NUTRIENTS) + 1

    for catalog_row in catalog:
        fdc_id = catalog_row["fdc_id"]

        print(
            "Pobieranie:",
            catalog_row["product_id"],
            fdc_id,
        )

        food = fetch_food(
            session,
            api_key,
            fdc_id,
        )

        raw_path = (
            DATA_DIR
            / "raw"
            / f"{fdc_id}.json"
        )

        write_json(raw_path, food)

        rows = nutrient_rows(food)
        energy_info = find_energy(rows)

        if energy_info is None:
            exceptions.append(
                {
                    "product_id":
                        catalog_row["product_id"],
                    "severity": "critical",
                    "code": "missing_energy",
                    "message":
                        "Brak wiarygodnej energii kcal/100 g.",
                }
            )
            continue

        energy = energy_info["value"]

        if not 1.0 <= energy <= 900.0:
            raise RuntimeError(
                f"Podejrzana energia dla "
                f"{catalog_row['product_id']}: "
                f"{energy}"
            )

        values = {}
        available = 0

        for definition in NUTRIENTS:
            found = find_nutrient(
                rows,
                definition["fdc_ids"],
                definition["unit"],
            )

            if found is None:
                components.append(
                    {
                        "product_id":
                            catalog_row["product_id"],
                        "name_pl":
                            catalog_row["name_pl"],
                        "nutrient_key":
                            definition["key"],
                        "nutrient_name":
                            definition["name_pl"],
                        "group":
                            definition["group"],
                        "value": "",
                        "unit":
                            definition["unit"],
                        "reference":
                            definition["reference"],
                        "reference_source":
                            definition[
                                "reference_source"
                            ],
                        "points_100g": "",
                        "points_100kcal": "",
                        "weighted_score": "",
                        "data_status":
                            "Brak danych — nie zero",
                        "source": "USDA FDC",
                    }
                )
                continue

            value = float(found["value"])

            if value < 0:
                raise RuntimeError(
                    f"Ujemna wartość: "
                    f"{catalog_row['product_id']} "
                    f"{definition['key']}"
                )

            points_100g, points_100kcal, combined = (
                score_component(
                    value,
                    float(definition["reference"]),
                    energy,
                )
            )

            available += 1
            values[definition["key"]] = value

            components.append(
                {
                    "product_id":
                        catalog_row["product_id"],
                    "name_pl":
                        catalog_row["name_pl"],
                    "nutrient_key":
                        definition["key"],
                    "nutrient_name":
                        definition["name_pl"],
                    "group":
                        definition["group"],
                    "value": value,
                    "unit":
                        definition["unit"],
                    "reference":
                        definition["reference"],
                    "reference_source":
                        definition[
                            "reference_source"
                        ],
                    "points_100g": points_100g,
                    "points_100kcal":
                        points_100kcal,
                    "weighted_score": combined,
                    "data_status":
                        "USDA — wartość bezpośrednia",
                    "source": "USDA FDC",
                }
            )

        protein = values.get("protein")

        aas = amino_acid_score(
            rows,
            protein
        )

        if aas is None:
            components.append(
                {
                    "product_id":
                        catalog_row["product_id"],
                    "name_pl":
                        catalog_row["name_pl"],
                    "nutrient_key":
                        "amino_acid_score",
                    "nutrient_name":
                        "Amino Acid Score",
                    "group":
                        "protein_and_amino_acids",
                    "value": "",
                    "unit": "pkt",
                    "reference": 100.0,
                    "reference_source":
                        "FAO adult pattern",
                    "points_100g": "",
                    "points_100kcal": "",
                    "weighted_score": "",
                    "data_status":
                        "Brak pełnego profilu aminokwasów",
                    "source": "USDA FDC / FAO",
                }
            )
        else:
            available += 1

            components.append(
                {
                    "product_id":
                        catalog_row["product_id"],
                    "name_pl":
                        catalog_row["name_pl"],
                    "nutrient_key":
                        "amino_acid_score",
                    "nutrient_name":
                        "Amino Acid Score",
                    "group":
                        "protein_and_amino_acids",
                    "value": aas["score"],
                    "unit": "pkt",
                    "reference": 100.0,
                    "reference_source":
                        "FAO adult pattern",
                    "points_100g":
                        aas["capped_score"],
                    "points_100kcal":
                        aas["capped_score"],
                    "weighted_score":
                        aas["capped_score"],
                    "data_status":
                        "Obliczono; to nie DIAAS",
                    "source": "USDA FDC / FAO",
                }
            )

        own_components = [
            row
            for row in components
            if row["product_id"]
            == catalog_row["product_id"]
        ]

        group_values = defaultdict(list)

        for component in own_components:
            score = component["weighted_score"]

            if score == "":
                continue

            group_values[
                component["group"]
            ].append(float(score))

        group_scores = {}

        for group, weight in GROUP_WEIGHTS.items():
            scores = group_values.get(group, [])

            if scores:
                group_scores[group] = (
                    sum(scores) / len(scores)
                )
            else:
                group_scores[group] = 0.0

        raw_score = sum(
            group_scores[group]
            * GROUP_WEIGHTS[group]
            for group in GROUP_WEIGHTS
        )

        completeness = (
            available / total_components
        )

        cautious_score = (
            raw_score * completeness
        )

        normalized.append(
            {
                "product_id":
                    catalog_row["product_id"],
                "name_pl":
                    catalog_row["name_pl"],
                "fdc_id": fdc_id,
                "fdc_description":
                    food.get("description", ""),
                "data_type":
                    food.get("dataType", ""),
                "category":
                    catalog_row["category"],
                "state":
                    catalog_row["state"],
                "energy_kcal_100g": energy,
                "energy_source":
                    energy_info["source"],
                "available_components":
                    available,
                "all_components":
                    total_components,
                "completeness":
                    completeness,
                "amino_acid_score":
                    "" if aas is None else aas["score"],
                "limiting_amino_acid":
                    "" if aas is None
                    else aas["limiting"],
            }
        )

        ranking.append(
            {
                "product_id":
                    catalog_row["product_id"],
                "name_pl":
                    catalog_row["name_pl"],
                "category":
                    catalog_row["category"],
                "energy_kcal_100g": energy,
                "available_components":
                    available,
                "all_components":
                    total_components,
                "completeness":
                    completeness,
                "completeness_percent":
                    completeness * 100.0,
                "score_raw": raw_score,
                "score_cautious":
                    cautious_score,
                "status":
                    product_status(completeness),
                "methodology_version":
                    methodology["version"],
            }
        )

        time.sleep(0.25)

    if len(ranking) != 3:
        raise RuntimeError(
            f"Ranking zawiera {len(ranking)}/3 produktów."
        )

    ranking.sort(
        key=lambda row: row["score_cautious"],
        reverse=True,
    )

    for index, row in enumerate(
        ranking,
        start=1
    ):
        row["place"] = index

    normalized_fields = [
        "product_id",
        "name_pl",
        "fdc_id",
        "fdc_description",
        "data_type",
        "category",
        "state",
        "energy_kcal_100g",
        "energy_source",
        "available_components",
        "all_components",
        "completeness",
        "amino_acid_score",
        "limiting_amino_acid",
    ]

    component_fields = [
        "product_id",
        "name_pl",
        "nutrient_key",
        "nutrient_name",
        "group",
        "value",
        "unit",
        "reference",
        "reference_source",
        "points_100g",
        "points_100kcal",
        "weighted_score",
        "data_status",
        "source",
    ]

    ranking_fields = [
        "place",
        "product_id",
        "name_pl",
        "category",
        "energy_kcal_100g",
        "available_components",
        "all_components",
        "completeness_percent",
        "score_raw",
        "score_cautious",
        "status",
        "methodology_version",
    ]

    exception_fields = [
        "product_id",
        "severity",
        "code",
        "message",
    ]

    write_csv(
        DATA_DIR
        / "normalized"
        / "pilot-products.csv",
        normalized,
        normalized_fields,
    )

    write_csv(
        DATA_DIR
        / "results"
        / "component-scores.csv",
        components,
        component_fields,
    )

    write_csv(
        DATA_DIR
        / "results"
        / "ranking-v2-pilot.csv",
        ranking,
        ranking_fields,
    )

    write_csv(
        DATA_DIR
        / "results"
        / "exceptions.csv",
        exceptions,
        exception_fields,
    )

    write_json(
        PUBLIC_DIR / "data" / "ranking.json",
        ranking,
    )

    write_json(
        PUBLIC_DIR
        / "data"
        / "components.json",
        components,
    )

    write_json(
        PUBLIC_DIR
        / "data"
        / "exceptions.json",
        exceptions,
    )

    PUBLIC_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    index_html = build_html(
        ranking,
        components,
        exceptions,
        methodology,
    )

    (
        PUBLIC_DIR / "index.html"
    ).write_text(
        index_html,
        encoding="utf-8",
    )

    security_check(api_key)

    for row in ranking:
        score = float(row["score_cautious"])

        if not math.isfinite(score):
            raise RuntimeError(
                "Wynik nie jest liczbą skończoną."
            )

        if not 0.0 <= score <= 120.0:
            raise RuntimeError(
                f"Wynik poza zakresem: {score}"
            )

    print("")
    print("====================================")
    print("PILOT SILNIKA V2 ZAKOŃCZONY")
    print("Produkty:", len(ranking))
    print("Komponenty:", len(components))
    print("Wyjątki:", len(exceptions))
    print("Klucz USDA w plikach: 0")
    print("====================================")

    for row in ranking:
        print(
            row["place"],
            row["name_pl"],
            round(row["score_cautious"], 2),
            round(row["completeness_percent"], 1),
        )


if __name__ == "__main__":
    main()

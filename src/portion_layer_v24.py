from __future__ import annotations

import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PUBLIC = ROOT / "public"

VERSION = "2.4.0-portion-pilot"
CAP = 120.0

GROUP_WEIGHTS = {
    "minerals": 0.30,
    "vitamins": 0.30,
    "protein_and_amino_acids": 0.20,
    "fatty_acids": 0.10,
    "fiber_and_functional": 0.10,
}

# Porcje analityczne służą do porównania.
# Nie są indywidualnym zaleceniem żywieniowym.
PORTIONS = {
    "BEEF-LIVER-RAW": {
        "grams": 100,
        "basis": "porcja podrobów",
    },
    "BEEF-HEART-RAW": {
        "grams": 150,
        "basis": "porcja mięsa",
    },
    "BEEF-KIDNEY-RAW": {
        "grams": 100,
        "basis": "porcja podrobów",
    },
    "BEEF-GROUND-9010-RAW": {
        "grams": 150,
        "basis": "porcja mięsa",
    },
    "EGG-WHOLE-RAW": {
        "grams": 50,
        "basis": "jedno średnie jajo bez skorupy",
    },
    "MILK-WHOLE": {
        "grams": 250,
        "basis": "jedna szklanka",
    },
    "YOGURT-PLAIN-WHOLE": {
        "grams": 200,
        "basis": "jedno opakowanie lub miseczka",
    },
    "CHEESE-CHEDDAR": {
        "grams": 30,
        "basis": "porcja sera",
    },
    "SALMON-ATLANTIC-RAW": {
        "grams": 150,
        "basis": "porcja ryby",
    },
    "SARDINE-CANNED": {
        "grams": 100,
        "basis": "porcja po odsączeniu",
    },
    "COD-PACIFIC-RAW": {
        "grams": 150,
        "basis": "porcja ryby",
    },
    "LENTILS-COOKED": {
        "grams": 180,
        "basis": "miseczka ugotowanej soczewicy",
    },
    "CHICKPEAS-COOKED": {
        "grams": 180,
        "basis": "miseczka ugotowanej ciecierzycy",
    },
    "KIDNEY-BEANS-COOKED": {
        "grams": 180,
        "basis": "miseczka ugotowanej fasoli",
    },
    "OATMEAL-COOKED": {
        "grams": 250,
        "basis": "miska ugotowanej owsianki",
    },
    "BROCCOLI-RAW": {
        "grams": 150,
        "basis": "duża porcja warzyw",
    },
    "CARROT-RAW": {
        "grams": 150,
        "basis": "około dwie średnie marchewki",
    },
    "CAULIFLOWER-RAW": {
        "grams": 200,
        "basis": "porcja warzyw",
    },
    "SPINACH-RAW": {
        "grams": 75,
        "basis": "duża porcja świeżych liści",
    },
    "KALE-RAW": {
        "grams": 100,
        "basis": "porcja świeżych liści",
    },
    "POTATO-BAKED": {
        "grams": 200,
        "basis": "jeden duży ziemniak",
    },
    "APPLE-RAW-SKIN": {
        "grams": 180,
        "basis": "jedno średnie jabłko",
    },
    "BANANA-RAW": {
        "grams": 120,
        "basis": "jeden średni banan bez skórki",
    },
    "BLUEBERRIES-RAW": {
        "grams": 125,
        "basis": "mała miseczka",
    },
    "AVOCADO-RAW": {
        "grams": 100,
        "basis": "około pół dużego awokado",
    },
    "ALMONDS-RAW": {
        "grams": 30,
        "basis": "garść",
    },
    "WALNUTS-RAW": {
        "grams": 30,
        "basis": "garść",
    },
    "SUNFLOWER-SEEDS": {
        "grams": 30,
        "basis": "mała garść",
    },
    "FLAXSEED": {
        "grams": 10,
        "basis": "około jedna łyżka",
    },
    "PUMPKIN-SEEDS": {
        "grams": 30,
        "basis": "mała garść",
    },
}

FLAGS = {
    "BEEF-LIVER-RAW": {
        "flag": "HIGH_RETINOL_COPPER",
        "level": "uwaga",
        "note":
            "Bardzo dużo retinolu i miedzi. "
            "Wynik nie oznacza, że duża porcja "
            "powinna być spożywana codziennie.",
        "preparation":
            "Częstotliwość i wielkość porcji "
            "wymagają osobnej oceny.",
    },
    "BEEF-KIDNEY-RAW": {
        "flag": "HIGH_MICRONUTRIENT_DENSITY",
        "level": "informacja",
        "note":
            "Podroby mogą dostarczać wysokich "
            "ilości wybranych mikroelementów.",
        "preparation":
            "Oceniać w kontekście częstotliwości.",
    },
    "SARDINE-CANNED": {
        "flag": "CANNED_SODIUM",
        "level": "informacja",
        "note":
            "Produkt konserwowany może zawierać "
            "więcej sodu; sód nie podnosi wyniku.",
        "preparation":
            "Uwzględniać zalewę i odsączenie.",
    },
    "SPINACH-RAW": {
        "flag": "OXALATES",
        "level": "uwaga",
        "note":
            "Szczawiany mogą ograniczać "
            "wykorzystanie części minerałów.",
        "preparation":
            "Gotowanie i odlanie wody może "
            "zmniejszać część rozpuszczalnych "
            "szczawianów.",
    },
    "ALMONDS-RAW": {
        "flag": "PHYTATES",
        "level": "informacja",
        "note":
            "Fityniany mogą ograniczać "
            "wchłanianie części minerałów.",
        "preparation":
            "Moczenie, kiełkowanie lub fermentacja "
            "mogą zmieniać profil antyodżywczy.",
    },
    "WALNUTS-RAW": {
        "flag": "PHYTATES",
        "level": "informacja",
        "note":
            "Fityniany mogą ograniczać "
            "wchłanianie części minerałów.",
        "preparation":
            "Nie stosuje się automatycznej "
            "korekty liczbowej.",
    },
    "SUNFLOWER-SEEDS": {
        "flag": "PHYTATES",
        "level": "informacja",
        "note":
            "Fityniany mogą ograniczać "
            "wchłanianie części minerałów.",
        "preparation":
            "Wynik składu nie jest wynikiem "
            "wchłoniętej ilości.",
    },
    "FLAXSEED": {
        "flag": "PHYTATES_AND_FORM",
        "level": "informacja",
        "note":
            "Forma całych nasion może ograniczać "
            "dostępność części składników.",
        "preparation":
            "Rozdrobnienie zmienia dostępność, "
            "ale również trwałość tłuszczów.",
    },
    "PUMPKIN-SEEDS": {
        "flag": "PHYTATES",
        "level": "informacja",
        "note":
            "Fityniany mogą ograniczać "
            "wchłanianie części minerałów.",
        "preparation":
            "Nie stosuje się arbitralnej kary.",
    },
    "LENTILS-COOKED": {
        "flag": "PHYTATES",
        "level": "informacja",
        "note":
            "Strączki zawierają związki mogące "
            "ograniczać dostępność minerałów.",
        "preparation":
            "Moczenie i prawidłowe gotowanie "
            "zmieniają profil antyodżywczy.",
    },
    "CHICKPEAS-COOKED": {
        "flag": "PHYTATES",
        "level": "informacja",
        "note":
            "Strączki zawierają związki mogące "
            "ograniczać dostępność minerałów.",
        "preparation":
            "Moczenie i gotowanie uwzględnić "
            "w osobnym porównaniu technologii.",
    },
    "KIDNEY-BEANS-COOKED": {
        "flag": "LECTINS_AND_PHYTATES",
        "level": "ważne",
        "note":
            "Surowa lub niedogotowana czerwona "
            "fasola nie jest odpowiednikiem "
            "prawidłowo ugotowanej.",
        "preparation":
            "Wymaga prawidłowego gotowania; "
            "ranking dotyczy produktu ugotowanego.",
    },
    "OATMEAL-COOKED": {
        "flag": "PHYTATES",
        "level": "informacja",
        "note":
            "Fityniany mogą wpływać na "
            "wykorzystanie części minerałów.",
        "preparation":
            "Fermentacja lub dłuższe przygotowanie "
            "może zmieniać ich ilość.",
    },
}

DEFAULT_FLAG = {
    "flag": "NO_SPECIFIC_FLAG",
    "level": "brak szczególnej flagi",
    "note":
        "Nie zastosowano liczbowej korekty "
        "biodostępności.",
    "preparation":
        "Stan produktu musi odpowiadać rekordowi USDA.",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        return list(csv.DictReader(handle))


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    columns: list[str],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    ranking = read_csv(
        DATA
        / "results"
        / "ranking-v23-30.csv"
    )

    components = read_csv(
        DATA
        / "results"
        / "components-v23-30.csv"
    )

    if len(ranking) != 30:
        raise RuntimeError(
            f"Ranking wejściowy ma "
            f"{len(ranking)}/30 produktów."
        )

    ranking_ids = {
        row["product_id"]
        for row in ranking
    }

    portion_ids = set(PORTIONS)

    missing_portions = sorted(
        ranking_ids - portion_ids
    )

    surplus_portions = sorted(
        portion_ids - ranking_ids
    )

    if missing_portions:
        raise RuntimeError(
            "Brak porcji dla: "
            + ", ".join(missing_portions)
        )

    if surplus_portions:
        raise RuntimeError(
            "Nieznane porcje dla: "
            + ", ".join(surplus_portions)
        )

    by_product = defaultdict(list)

    for row in components:
        by_product[
            row["product_id"]
        ].append(row)

    expected_by_group = defaultdict(set)

    for row in components:
        expected_by_group[
            row["group"]
        ].add(row["nutrient_key"])

    results = []
    portion_components = []
    assumptions = []

    for product in ranking:
        product_id = product["product_id"]
        portion = PORTIONS[product_id]
        portion_g = float(portion["grams"])
        flag = FLAGS.get(
            product_id,
            DEFAULT_FLAG,
        )

        group_scores = defaultdict(list)
        group_available = defaultdict(int)
        protein_quantity = None
        amino_score = None

        for component in by_product[product_id]:
            value_text = component["value"]
            reference_text = component["reference"]

            output = {
                "product_id": product_id,
                "name_pl": product["name_pl"],
                "nutrient_key":
                    component["nutrient_key"],
                "nutrient_name":
                    component["nutrient_name"],
                "group": component["group"],
                "portion_g": portion_g,
                "value_per_100g": value_text,
                "value_per_portion": "",
                "unit": component["unit"],
                "reference": reference_text,
                "portion_points": "",
                "data_status":
                    component["data_status"],
            }

            if (
                value_text == ""
                or reference_text == ""
            ):
                portion_components.append(output)
                continue

            value = float(value_text)
            reference = float(reference_text)

            if not (
                math.isfinite(value)
                and math.isfinite(reference)
                and reference > 0
            ):
                raise RuntimeError(
                    "Nieprawidłowa wartość: "
                    + product_id
                    + "/"
                    + component["nutrient_key"]
                )

            value_per_portion = (
                value * portion_g / 100.0
            )

            portion_points = min(
                value_per_portion
                / reference
                * 100.0,
                CAP,
            )

            output["value_per_portion"] = (
                value_per_portion
            )
            output["portion_points"] = (
                portion_points
            )

            key = component["nutrient_key"]
            group = component["group"]

            if key == "protein":
                protein_quantity = portion_points
                group_available[group] += 1

            elif key == "amino_acid_score":
                amino_score = value
                group_available[group] += 1

            else:
                group_scores[group].append(
                    portion_points
                )
                group_available[group] += 1

            portion_components.append(output)

        product_group_rows = []

        for group, weight in GROUP_WEIGHTS.items():
            expected = len(
                expected_by_group[group]
            )

            available = group_available[group]

            completeness = (
                available / expected
                if expected
                else 0.0
            )

            if group == "protein_and_amino_acids":
                quantity = (
                    protein_quantity
                    if protein_quantity is not None
                    else 0.0
                )

                quality_factor = (
                    min(amino_score / 100.0, 1.0)
                    if amino_score is not None
                    else 1.0
                )

                raw = quantity * quality_factor
            else:
                scores = group_scores[group]

                raw = (
                    sum(scores) / len(scores)
                    if scores
                    else 0.0
                )

            cautious = raw * completeness

            product_group_rows.append(
                {
                    "group": group,
                    "weight": weight,
                    "raw": raw,
                    "cautious": cautious,
                    "completeness": completeness,
                }
            )

        portion_score_raw = sum(
            row["raw"] * row["weight"]
            for row in product_group_rows
        )

        portion_score_cautious = sum(
            row["cautious"] * row["weight"]
            for row in product_group_rows
        )

        if not (
            math.isfinite(portion_score_raw)
            and math.isfinite(
                portion_score_cautious
            )
        ):
            raise RuntimeError(
                "Nieskończony wynik porcji: "
                + product_id
            )

        results.append(
            {
                "portion_place": "",
                "product_id": product_id,
                "name_pl": product["name_pl"],
                "category": product["category"],
                "portion_g": portion_g,
                "portion_basis": portion["basis"],
                "core_place": product["place"],
                "core_score":
                    float(
                        product["score_cautious"]
                    ),
                "portion_score_raw":
                    portion_score_raw,
                "portion_score_cautious":
                    portion_score_cautious,
                "bioavailability_flag":
                    flag["flag"],
                "flag_level":
                    flag["level"],
                "bioavailability_note":
                    flag["note"],
                "preparation_note":
                    flag["preparation"],
                "numeric_bioavailability_penalty":
                    "NIE",
                "methodology_version": VERSION,
            }
        )

        assumptions.append(
            {
                "product_id": product_id,
                "name_pl": product["name_pl"],
                "portion_g": portion_g,
                "portion_basis": portion["basis"],
                "assumption_type":
                    "analityczna porcja porównawcza",
                "is_medical_recommendation": "NIE",
                "version": VERSION,
            }
        )

    results.sort(
        key=lambda row:
            row["portion_score_cautious"],
        reverse=True,
    )

    for place, row in enumerate(
        results,
        start=1,
    ):
        row["portion_place"] = place

    result_columns = [
        "portion_place",
        "product_id",
        "name_pl",
        "category",
        "portion_g",
        "portion_basis",
        "core_place",
        "core_score",
        "portion_score_raw",
        "portion_score_cautious",
        "bioavailability_flag",
        "flag_level",
        "bioavailability_note",
        "preparation_note",
        "numeric_bioavailability_penalty",
        "methodology_version",
    ]

    component_columns = [
        "product_id",
        "name_pl",
        "nutrient_key",
        "nutrient_name",
        "group",
        "portion_g",
        "value_per_100g",
        "value_per_portion",
        "unit",
        "reference",
        "portion_points",
        "data_status",
    ]

    assumption_columns = [
        "product_id",
        "name_pl",
        "portion_g",
        "portion_basis",
        "assumption_type",
        "is_medical_recommendation",
        "version",
    ]

    write_csv(
        DATA
        / "results"
        / "portion-ranking-v24.csv",
        results,
        result_columns,
    )

    write_csv(
        DATA
        / "results"
        / "portion-components-v24.csv",
        portion_components,
        component_columns,
    )

    write_csv(
        DATA
        / "catalog"
        / "portion-assumptions-v24.csv",
        assumptions,
        assumption_columns,
    )

    write_json(
        PUBLIC
        / "data"
        / "portion-ranking-v24.json",
        results,
    )

    table_rows = []

    for row in results:
        difference = (
            int(row["core_place"])
            - int(row["portion_place"])
        )

        if difference > 0:
            movement = f"↑ {difference}"
        elif difference < 0:
            movement = f"↓ {abs(difference)}"
        else:
            movement = "—"

        table_rows.append(
            "<tr>"
            f"<td>{row['portion_place']}</td>"
            f"<td>{html.escape(row['name_pl'])}</td>"
            f"<td>{row['portion_g']:.0f} g</td>"
            f"<td>{row['portion_score_cautious']:.2f}</td>"
            f"<td>{row['core_place']}</td>"
            f"<td>{movement}</td>"
            f"<td>{html.escape(row['flag_level'])}</td>"
            "</tr>"
        )

    flag_rows = []

    for row in results:
        if (
            row["bioavailability_flag"]
            == "NO_SPECIFIC_FLAG"
        ):
            continue

        flag_rows.append(
            "<tr>"
            f"<td>{html.escape(row['name_pl'])}</td>"
            f"<td>{html.escape(row['bioavailability_flag'])}</td>"
            f"<td>{html.escape(row['bioavailability_note'])}</td>"
            f"<td>{html.escape(row['preparation_note'])}</td>"
            "</tr>"
        )

    page = f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <meta name="viewport"
        content="width=device-width, initial-scale=1">
  <title>Indeks żywności — porcje</title>
  <style>
    body {{
      max-width: 1400px;
      margin: 30px auto;
      padding: 18px;
      font-family: system-ui, sans-serif;
      color: #20251f;
      background: #f3f5ef;
    }}
    h1, h2 {{ color: #274e13; }}
    .box {{
      margin: 22px 0;
      padding: 22px;
      overflow-x: auto;
      background: white;
      border-radius: 14px;
      box-shadow: 0 4px 18px #0001;
    }}
    .warning {{
      padding: 15px;
      border-left: 5px solid #bf9000;
      background: #fff8dd;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 8px;
      text-align: left;
      border-bottom: 1px solid #ddd;
      vertical-align: top;
    }}
    th {{ background: #d9ead3; }}
    a {{ color: #274e13; }}
  </style>
</head>
<body>
  <h1>Praktyczna porcja — pilot v2.4</h1>

  <div class="warning">
    Porcje służą do analitycznego porównania.
    Nie są indywidualnym zaleceniem medycznym.
    Flagi biodostępności nie zmieniają wyniku
    liczbowego bez zweryfikowanych współczynników.
  </div>

  <section class="box">
    <h2>Ranking według porcji</h2>
    <table>
      <thead>
        <tr>
          <th>Miejsce</th>
          <th>Produkt</th>
          <th>Porcja</th>
          <th>Wynik porcji</th>
          <th>Miejsce składu</th>
          <th>Zmiana</th>
          <th>Flaga</th>
        </tr>
      </thead>
      <tbody>
        {''.join(table_rows)}
      </tbody>
    </table>
  </section>

  <section class="box">
    <h2>Biodostępność i przygotowanie</h2>
    <table>
      <thead>
        <tr>
          <th>Produkt</th>
          <th>Flaga</th>
          <th>Ograniczenie</th>
          <th>Przygotowanie</th>
        </tr>
      </thead>
      <tbody>
        {''.join(flag_rows)}
      </tbody>
    </table>
  </section>

  <section class="box">
    <h2>Zasady</h2>
    <ul>
      <li>
        Ranking składu na 100 g i 100 kcal
        pozostaje niezmieniony.
      </li>
      <li>
        Wynik porcji oblicza ilość składników
        w zadanej masie porcji.
      </li>
      <li>
        Brak danych nadal nie jest zerem.
      </li>
      <li>
        Nie zastosowano arbitralnej kary
        za fityniany lub szczawiany.
      </li>
      <li>
        AAS nie jest DIAAS.
      </li>
    </ul>
    <p>
      <a href="index.html">
        Powrót do rankingu składu
      </a>
    </p>
  </section>
</body>
</html>
"""

    (
        PUBLIC / "portion.html"
    ).write_text(
        page,
        encoding="utf-8",
    )

    print("====================================")
    print("WARSTWA PORCJI V2.4 ZAKOŃCZONA")
    print("Produkty:", len(results))
    print("Założenia porcji:", len(assumptions))
    print(
        "Flagi szczególne:",
        sum(
            1
            for row in results
            if row["bioavailability_flag"]
            != "NO_SPECIFIC_FLAG"
        ),
    )
    print(
        "Korekty biodostępności liczbowe: 0"
    )
    print("====================================")

    for row in results[:10]:
        print(
            row["portion_place"],
            row["name_pl"],
            round(
                row[
                    "portion_score_cautious"
                ],
                2,
            ),
            f"{row['portion_g']:.0f} g",
        )


if __name__ == "__main__":
    main()

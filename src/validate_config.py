from decimal import Decimal

from src.settings import (
    load_methodology,
    load_project_config,
)


def validate() -> dict:
    project = load_project_config()
    methodology = load_methodology()

    scoring = methodology["scoring"]
    groups = methodology["group_weights"]

    mass_weight = Decimal(
        str(scoring["per_100g_weight"])
    )

    energy_weight = Decimal(
        str(scoring["per_100kcal_weight"])
    )

    if (
        mass_weight + energy_weight
        != Decimal("1.0")
    ):
        raise ValueError(
            "Wagi 100 g i 100 kcal "
            "nie sumują się do 1."
        )

    group_sum = sum(
        (
            Decimal(str(value))
            for value in groups.values()
        ),
        Decimal("0")
    )

    if group_sum != Decimal("1.0"):
        raise ValueError(
            "Wagi grup składników "
            "nie sumują się do 1."
        )

    full = Decimal(
        str(
            scoring[
                "full_completeness_minimum"
            ]
        )
    )

    conditional = Decimal(
        str(
            scoring[
                "conditional_completeness_minimum"
            ]
        )
    )

    if not (
        Decimal("0")
        < conditional
        < full
        <= Decimal("1")
    ):
        raise ValueError(
            "Nieprawidłowe progi kompletności."
        )

    publication = project["publication"]

    if publication[
        "publish_incomplete_results"
    ]:
        raise ValueError(
            "Publikowanie niepełnych wyników "
            "musi być wyłączone."
        )

    if not publication[
        "show_component_scores"
    ]:
        raise ValueError(
            "Punkty cząstkowe muszą być jawne."
        )

    if not publication["show_sources"]:
        raise ValueError(
            "Źródła muszą być jawne."
        )

    return {
        "project":
            project["project"]["name"],
        "project_version":
            project["project"]["version"],
        "methodology_version":
            methodology[
                "methodology"
            ]["version"],
        "status": "OK",
    }


if __name__ == "__main__":
    print(validate())

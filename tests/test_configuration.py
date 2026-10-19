from decimal import Decimal

from src.settings import (
    load_methodology,
    load_project_config,
)
from src.validate_config import validate


def test_configuration_is_valid():
    result = validate()

    assert result["status"] == "OK"
    assert (
        result["methodology_version"]
        == "2.0.0-dev"
    )


def test_scoring_weights_sum_to_one():
    methodology = load_methodology()
    scoring = methodology["scoring"]

    total = (
        Decimal(
            str(scoring["per_100g_weight"])
        )
        + Decimal(
            str(
                scoring[
                    "per_100kcal_weight"
                ]
            )
        )
    )

    assert total == Decimal("1.0")


def test_group_weights_sum_to_one():
    methodology = load_methodology()
    groups = methodology["group_weights"]

    total = sum(
        (
            Decimal(str(value))
            for value in groups.values()
        ),
        Decimal("0")
    )

    assert total == Decimal("1.0")


def test_incomplete_results_not_published():
    project = load_project_config()

    assert (
        project["publication"][
            "publish_incomplete_results"
        ]
        is False
    )


def test_component_scores_are_public():
    project = load_project_config()

    assert (
        project["publication"][
            "show_component_scores"
        ]
        is True
    )


def test_sources_are_public():
    project = load_project_config()

    assert (
        project["publication"][
            "show_sources"
        ]
        is True
    )

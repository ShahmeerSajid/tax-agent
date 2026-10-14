

import pytest

from backend.calculator import bracket_tax, calculate_tax, load_rules

# Made-up brackets, easy to check by hand:
# first 50,000 at 10%, next 50,000 at 20%, everything above at 30%
SIMPLE = [
    {"up_to": 50000, "rate": 0.10},
    {"up_to": 100000, "rate": 0.20},
    {"up_to": None, "rate": 0.30},
]


def test_zero_income():
    assert bracket_tax(0, SIMPLE) == 0


def test_inside_first_bracket():
    assert bracket_tax(40000, SIMPLE) == 4000  # 40,000 x 10%


def test_exactly_at_bracket_edge():
    assert bracket_tax(50000, SIMPLE) == 5000  # 50,000 x 10%


def test_two_brackets():
    # 5,000 + (30,000 x 20% = 6,000)
    assert bracket_tax(80000, SIMPLE) == 11000


def test_all_three_brackets():
    # 5,000 + 10,000 + (50,000 x 30% = 15,000)
    assert bracket_tax(150000, SIMPLE) == 30000


def test_real_federal_first_bracket_edge():
    rules = load_rules()
    # 58,523 x 14% = 8,193.22
    assert bracket_tax(58523, rules["jurisdictions"]["federal"]["brackets"]) == 8193.22



def test_unknown_province_rejected():
    with pytest.raises(ValueError):
        calculate_tax(50000, "XX", load_rules())


def test_negative_income_rejected():
    with pytest.raises(ValueError):
        calculate_tax(-1, "ON", load_rules())


def test_total_is_federal_plus_provincial_and_cites_sources():
    result = calculate_tax(85000, "ON", load_rules())
    assert result["total_tax"] == pytest.approx(
        result["federal_tax"] + result["provincial_tax"], abs=0.01
    )
    assert len(result["sources"]) == 2


def test_every_province_runs():
    rules = load_rules()
    for key in rules["jurisdictions"]:
        if key != "federal":
            assert calculate_tax(85000, key, rules)["total_tax"] > 0
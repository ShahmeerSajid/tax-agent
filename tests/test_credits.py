from backend.credits import federal_bpa, load_credits, tax_after_basic_personal_credit


def test_federal_bpa_phase_down():
    f = load_credits()["federal"]
    assert federal_bpa(100000, f) == 16452
    assert federal_bpa(300000, f) == 14829
    assert 14829 < federal_bpa(220000, f) < 16452


def test_credit_cannot_make_tax_negative():
    r = tax_after_basic_personal_credit(10000, "BC")
    assert r["total_tax_after_basic_personal_credit"] == 0.0


def test_newfoundland_flagged_incomplete():
    r = tax_after_basic_personal_credit(60000, "NL")
    assert r["incomplete"] and r["provincial_bpa_credit"] == 0.0


def test_ontario_85000():
    r = tax_after_basic_personal_credit(85000, "ON")
    assert r["total_tax_after_basic_personal_credit"] == 16229.76

from decimal import Decimal
from src.rules.validators import r3_amount_balance, r4_vat_plausibility, r0_overall_status

def test_r3_pass():
    v = r3_amount_balance(1000, 190, 1190)
    assert v["status"] == "PASS"

def test_r3_fail():
    v = r3_amount_balance(500, 95, 620)
    assert v["status"] == "FAIL"

def test_r4_pass():
    v = r4_vat_plausibility(1000, 19, 190)
    assert v["status"] == "PASS"

def test_r4_fail():
    v = r4_vat_plausibility(1000, 19, 200)
    assert v["status"] == "FAIL"

def test_r0_precedence():
    red_fail = {"severity": "RED", "status": "FAIL"}
    yellow_warn = {"severity": "YELLOW", "status": "WARN"}
    green_pass = {"severity": "GREEN", "status": "PASS"}
    assert r0_overall_status((green_pass, yellow_warn)) == "YELLOW"
    assert r0_overall_status((green_pass, red_fail)) == "RED"

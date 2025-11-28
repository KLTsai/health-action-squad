"""驗證 _check_completeness 正確處理空字串"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.parsers.health_report_parser import HealthReportParser

def test_empty_string_not_counted():
    parser = HealthReportParser()
    data = {
        "blood_pressure": "",     # 空字串 - 不應計數
        "cholesterol": "200",     # 有效 - 應計數
        "glucose": "",            # 空字串 - 不應計數
        "bmi": "25.5",            # 有效 - 應計數
        "heart_rate": None,       # None - 不應計數
        "temperature": "37.0",    # 有效 - 應計數
        "oxygen_saturation": ""   # 空字串 - 不應計數
    }

    expected = 3 / 7  # cholesterol, bmi, temperature
    actual = parser._check_completeness(data)

    print(f"Expected: {expected:.3f} (3/7), Actual: {actual:.3f}")
    assert abs(actual - expected) < 0.001, \
        f"Expected {expected:.3f}, got {actual:.3f}"
    print("[OK] Empty strings correctly excluded")

def test_all_empty():
    parser = HealthReportParser()
    data = {field: "" for field in parser.REQUIRED_FIELDS}
    actual = parser._check_completeness(data)
    print(f"\nAll empty - Expected: 0.0, Actual: {actual}")
    assert actual == 0.0, f"Expected 0.0, got {actual}"
    print("[OK] All empty strings = 0.0 completeness")

def test_all_valid():
    parser = HealthReportParser()
    data = {
        "blood_pressure": "120/80", "cholesterol": "200",
        "glucose": "100", "bmi": "25.5", "heart_rate": "72",
        "temperature": "37.0", "oxygen_saturation": "98"
    }
    actual = parser._check_completeness(data)
    print(f"\nAll valid - Expected: 1.0, Actual: {actual}")
    assert actual == 1.0, f"Expected 1.0, got {actual}"
    print("[OK] All valid values = 1.0 completeness")

if __name__ == "__main__":
    print("Testing _check_completeness empty string handling\n")
    try:
        test_empty_string_not_counted()
        test_all_empty()
        test_all_valid()
        print("\n[SUCCESS] All completeness tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

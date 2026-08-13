from ml.preprocessing.text_preprocessing import normalize_description


def test_lowercases_and_strips_reference_numbers():
    result = normalize_description("UPI/SWIGGY/123456")
    assert "123456" not in result
    assert "swiggy" in result
    assert "upi" not in result  # noise token removed


def test_strips_punctuation():
    result = normalize_description("NETFLIX*8899 -SUBSCRIPTION")
    assert "*" not in result
    assert "-" not in result
    assert "netflix" in result
    assert "subscription" in result


def test_collapses_whitespace():
    result = normalize_description("  AMAZON   PAY   ")
    assert result == "amazon pay"


def test_short_numbers_are_kept():
    # Only 4+ digit runs are treated as reference codes; short numbers
    # (e.g. a store number) are meaningful signal and kept.
    result = normalize_description("STORE 42 PURCHASE")
    assert "42" in result

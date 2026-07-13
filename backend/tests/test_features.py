from detection.features import ALL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES, SEVERITY_BY_CATEGORY


def test_all_features_is_categorical_plus_numeric():
    assert set(ALL_FEATURES) == set(NUMERIC_FEATURES) | set(CATEGORICAL_FEATURES)
    assert len(ALL_FEATURES) == len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES)


def test_normal_traffic_has_no_severity():
    assert SEVERITY_BY_CATEGORY["Normal"] == "none"


def test_every_severity_is_one_of_the_three_dashboard_tiers():
    valid = {"none", "critical", "high", "medium"}
    for category, severity in SEVERITY_BY_CATEGORY.items():
        assert severity in valid, f"{category} maps to unexpected severity {severity!r}"


def test_worms_and_dos_are_critical():
    # These are the most dangerous UNSW-NB15 categories — regression guard
    # against an accidental severity downgrade.
    assert SEVERITY_BY_CATEGORY["Worms"] == "critical"
    assert SEVERITY_BY_CATEGORY["DoS"] == "critical"

from interview_pipeline.catalog import load_catalog, shows, watched_people

LOCKED = (
    "Sam Altman",
    "Dario Amodei",
    "Demis Hassabis",
    "Elon Musk",
    "Satya Nadella",
    "Sundar Pichai",
    "Mark Zuckerberg",
    "Jensen Huang",
    "Ilya Sutskever",
    "Andrej Karpathy",
)


def test_watched_people_are_exactly_the_locked_list():
    assert watched_people() == LOCKED


def test_core_shows_are_enabled_and_have_feeds():
    core = shows(tier="core", enabled_only=True)
    ids = {show.id for show in core}
    assert ids == {
        "dwarkesh",
        "cheeky_pint",
        "no_priors",
        "bg2",
        "big_technology",
        "invest_like_the_best",
        "semianalysis_weekly",
        "latent_space",
        "pragmatic_engineer",
        "lennys",
    }
    assert all(show.feed_url for show in core)


def test_secondary_shows_are_off_by_default():
    catalog = load_catalog()
    secondary = [row for row in catalog["shows"] if row["tier"] == "secondary"]
    assert secondary
    assert all(row["enabled"] is False for row in secondary)

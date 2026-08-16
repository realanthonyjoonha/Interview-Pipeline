from interview_pipeline.filters import decide, extract_guest_hint
from interview_pipeline.models import Episode, Show


def _show(filter_name: str, show_id: str = "test", hosts: tuple[str, ...] = ()) -> Show:
    return Show(
        id=show_id,
        name="Test show",
        tier="core",
        enabled=True,
        feed_url="https://example.test/feed",
        site="",
        transcript="none_known",
        filter=filter_name,
        hosts=hosts,
    )


def _ep(title: str, seconds: int | None, description: str = "") -> Episode:
    return Episode(
        show_id="test",
        show_name="Test show",
        title=title,
        published="2026-08-01",
        url="https://example.test/ep",
        guid=title,
        duration_seconds=seconds,
        description=description,
    )


def test_guest_hint_from_with_and_dash():
    assert extract_guest_hint("What Chess.com Teaches Us, with CEO Erik Allebest") == "CEO Erik Allebest"
    assert extract_guest_hint("Ryan Greenblatt – What happens once AI can automate AI research?") == "Ryan Greenblatt"
    assert extract_guest_hint("How Ozempic Changes Our Bodies — With Johann Hari") == "Johann Hari"


def test_dwarkesh_skips_sub_20_min_essays():
    essay = _ep("8 Predictions for the Era of Continual Learning", 517, "An audio version of my blog post.")
    decision = decide(essay, _show("dwarkesh"))
    assert decision.matched is False
    assert any("sub-20" in reason for reason in decision.reasons)


def test_dwarkesh_keeps_long_interview():
    interview = _ep("Ryan Greenblatt – What happens once AI can automate AI research?", 7952)
    decision = decide(interview, _show("dwarkesh"))
    assert decision.matched is True
    assert decision.guest_hint == "Ryan Greenblatt"


def test_no_priors_skips_host_only_under_20():
    hosts = ("Sarah Guo", "Elad Gil", "Sarah", "Elad")
    host_only = _ep("Chasing Trillion-Dollar Companies, Founder Ambition, Token Budgets", 15 * 60)
    decision = decide(host_only, _show("no_priors", hosts=hosts))
    assert decision.matched is False
    assert any("host-only under 20" in reason for reason in decision.reasons)
    named_hosts = _ep(
        "Chasing Trillion-Dollar Companies, Founder Ambition, Token Budgets, and Regulatory Capture with Sarah & Elad",
        15 * 60,
    )
    decision = decide(named_hosts, _show("no_priors", hosts=hosts))
    assert decision.matched is False
    assert decision.guest_hint is None


def test_no_priors_keeps_guest_sit():
    guest = _ep("Building an Autonomous Enterprise with Netic Founder Melisa Tokmak", 2069)
    decision = decide(guest, _show("no_priors"))
    assert decision.matched is True
    assert decision.guest_hint and "Melisa" in decision.guest_hint


def test_no_priors_keeps_host_only_over_20():
    mid_host = _ep("Chasing Trillion-Dollar Companies, Founder Ambition, Token Budgets", 2369)
    decision = decide(mid_host, _show("no_priors"))
    assert decision.matched is True
    long_host = _ep("Host conversation about markets and regulation", 25 * 60)
    decision = decide(long_host, _show("no_priors"))
    assert decision.matched is True


def test_big_technology_skips_roundtables_and_requires_named_guest():
    news = _ep("This week in AI: OpenAI, Google, and Apple news roundtable", 3600)
    assert decide(news, _show("big_technology")).matched is False
    unnamed = _ep("Apple raises iPhone prices and other notes", 3600)
    assert decide(unnamed, _show("big_technology")).matched is False
    guest = _ep("How Ozempic Changes Our Bodies — With Johann Hari", 3145)
    assert decide(guest, _show("big_technology")).matched is True


def test_iltb_requires_ai_infra_chip_or_lab():
    consumer = _ep("Jane Founder - Building a consumer subscription brand - [Invest Like the Best, EP.1]", 4000)
    assert decide(consumer, _show("iltb")).matched is False
    chips = _ep("Lisa Su - The chip cycle and AI accelerators - [Invest Like the Best, EP.2]", 4000)
    assert decide(chips, _show("iltb")).matched is True
    lab = _ep("A lab director on foundation model evaluation", 4000, "We walked through the laboratory eval harness.")
    assert decide(lab, _show("iltb")).matched is True


def test_semianalysis_allows_short_china_or_teardown():
    short_generic = _ep("Ep. 001 - Weekly notes | Jordan Nanos", 19 * 60)
    assert decide(short_generic, _show("semianalysis")).matched is False
    numbered_20_plus = _ep("Ep. 018 - Weekly notes | Jordan Nanos", 25 * 60)
    assert decide(numbered_20_plus, _show("semianalysis")).matched is True
    short_china = _ep("Emergency: China silicon export controls", 18 * 60)
    assert decide(short_china, _show("semianalysis")).matched is True
    short_teardown = _ep("Named teardown of InferenceX cluster economics", 15 * 60)
    assert decide(short_teardown, _show("semianalysis")).matched is True
    long_staff = _ep("Ep. 024 - SpaceX 10GW plan | Reyk Knuhtsen, Jordan Nanos", 50 * 60)
    assert decide(long_staff, _show("semianalysis")).matched is True


def test_latent_space_ignores_ainews_and_shorts():
    news = _ep("AINews: Friday paper pile", 12 * 60)
    assert decide(news, _show("latent_space")).matched is False
    short = _ep("The Inference Engineering Masterclass — Philip Kiely & Ali Taha, Baseten", 15 * 60)
    assert decide(short, _show("latent_space")).matched is False
    mid_interview = _ep("The Inference Engineering Masterclass — Philip Kiely & Ali Taha, Baseten", 25 * 60)
    assert decide(mid_interview, _show("latent_space")).matched is True
    long_interview = _ep("The Inference Engineering Masterclass — Philip Kiely & Ali Taha, Baseten", 6089)
    # 6089 seconds is over the 20-minute bar; guest hint from dash may be the left side.
    decision = decide(long_interview, _show("latent_space"))
    assert decision.matched is True


def test_pragmatic_engineer_skips_host_ama():
    ama = _ep("The Pragmatic Engineer AMA", 4701)
    assert decide(ama, _show("pragmatic_engineer")).matched is False
    interview = _ep("Stop being skeptical about AI for development with Charity Majors", 5132)
    assert decide(interview, _show("pragmatic_engineer")).matched is True


def test_lennys_requires_ai_product():
    marketplace = _ep("This CPO regrets that product management exists | Tom Verrilli (CPO of Whatnot)", 5098)
    assert decide(marketplace, _show("lennys")).matched is False
    cursor = _ep("The playbook for building high-talent-density teams | Adam Ward, Head of Talent at Cursor", 5446)
    assert decide(cursor, _show("lennys")).matched is True
    anthropic = _ep("Anthropic’s first technical PM on token maxing", 5630)
    assert decide(anthropic, _show("lennys")).matched is True


def test_cheeky_pint_requires_founder_sit_and_length():
    no_guest = _ep("A quiet week at the pub", 70 * 60)
    assert decide(no_guest, _show("cheeky_pint")).matched is False
    short = _ep("The world of voice AI, with Mati Staniszewski of ElevenLabs", 15 * 60)
    assert decide(short, _show("cheeky_pint")).matched is False
    mid_sit = _ep("The world of voice AI, with Mati Staniszewski of ElevenLabs", 25 * 60)
    assert decide(mid_sit, _show("cheeky_pint")).matched is True
    founder = _ep("The history and future of AI at Google, with Sundar Pichai", 4163)
    decision = decide(founder, _show("cheeky_pint"))
    assert decision.matched is True
    assert decision.guest_hint == "Sundar Pichai"


def test_bg2_uses_length_bar():
    short = _ep("Quick market check w/ Gavin Baker", 15 * 60)
    assert decide(short, _show("bg2")).matched is False
    mid_ep = _ep("Quick market check w/ Gavin Baker", 25 * 60)
    assert decide(mid_ep, _show("bg2")).matched is True
    long_ep = _ep("The SpaceX IPO, Fable 5, AI Capex Update w/ Gavin Baker", 80 * 60)
    assert decide(long_ep, _show("bg2")).matched is True


def test_twenty_five_minute_in_scope_sit_is_a_match():
    sit = _ep("The history and future of AI at Google, with Sundar Pichai", 25 * 60)
    decision = decide(sit, _show("cheeky_pint"))
    assert decision.matched is True
    assert decision.guest_hint == "Sundar Pichai"


def test_dylan_patel_sit_always_in_scope_at_20_plus():
    sit = _ep("Dylan Patel - How he built the research firm", 25 * 60)
    iltb = decide(sit, _show("iltb"))
    assert iltb.matched is True
    assert any("always in-scope" in reason for reason in iltb.reasons)
    training_data = decide(sit, _show("length_only", show_id="training_data"))
    assert training_data.matched is True
    dwarkesh = decide(_ep("Dylan Patel – GPU supply and capex", 25 * 60), _show("dwarkesh"))
    assert dwarkesh.matched is True
    weekly = decide(
        _ep("Ep. 030 - Memory pricing with Dylan Patel | Jordan Nanos", 25 * 60),
        _show("semianalysis"),
    )
    assert weekly.matched is True
    short = decide(_ep("Dylan Patel - How he built the research firm", 15 * 60), _show("iltb"))
    assert short.matched is False

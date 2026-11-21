import pytest

from pinpoint.extract import extract_profile, profile_links, is_profile_url


@pytest.mark.parametrize("suffix", [".vcf", ".pdf", ".png"])
def test_downloads_are_not_discovered_as_lawyer_profiles(suffix):
    assert not is_profile_url("sullivan", "https://www.sullcrom.com/Lawyers/Jane-Example" + suffix)


def html(bio, title="Jane Example", role="Partner"):
    return f"""<html><head><title>{title}</title></head><body>
    <nav>Partner Corporate London</nav><main><h1>{title}</h1><h2>{role}</h2>
    <p>{bio}</p><div class="office">New York</div></main>
    <footer>Mergers &amp; Acquisitions</footer></body></html>"""


def test_extracts_partner_with_corporate_evidence_and_known_office():
    p = extract_profile(
        "milbank",
        "https://www.milbank.com/en/professionals/jane.html",
        html("Jane Example is a partner advising on mergers and acquisitions."),
        "2026-11-21T12:00:00Z",
    )
    assert p["name"] == "Jane Example"
    assert p["title"] == "Partner"
    assert p["practices"] == ["Mergers & Acquisitions"]
    assert p["offices"] == ["New York"]
    assert len(p["content_hash"]) == 64
    assert "London" not in p["evidence"]


@pytest.mark.parametrize(
    "bio,role",
    [
        ("Jane works on mergers and acquisitions.", "Associate"),
        ("Jane is a partner in patent litigation.", "Partner"),
        ("Jane is a former partner working as senior counsel in corporate law.", "Senior Counsel"),
    ],
)
def test_rejects_out_of_scope_and_navigation_false_positives(bio, role):
    assert (
        extract_profile(
            "milbank",
            "https://www.milbank.com/en/professionals/jane.html",
            html(bio, role=role),
            "2026-11-21T12:00:00Z",
        )
        is None
    )


def test_rejects_challenge_page():
    assert (
        extract_profile(
            "milbank",
            "https://www.milbank.com/en/professionals/jane.html",
            html("Verify you are human. Access denied."),
            "2026-11-21",
        )
        is None
    )


def test_discovers_only_official_profile_links_and_removes_fragments():
    source = """<a href="/en/professionals/jane-example.html#bio">Jane</a>
      <a href="https://evil.example/en/professionals/fake.html">Fake</a>
      <a href="/en/professionals/">Directory</a><a href="mailto:a@example.com">Email</a>"""
    assert profile_links("milbank", "https://www.milbank.com/en/professionals/", source) == [
        "https://www.milbank.com/en/professionals/jane-example.html"
    ]


def test_profile_header_is_not_removed_with_global_navigation():
    source = '<main><header class="profile-heading__main"><h1>Jane Example</h1><span>Partner</span></header><p>Jane Example advises on mergers and acquisitions.</p></main>'
    assert (
        extract_profile(
            "kirkland", "https://www.kirkland.com/lawyers/e/example-jane", source, "2026-11-21"
        )["name"]
        == "Jane Example"
    )


def test_simpson_profile_uses_actual_h2_name_selector():
    source = '<main><h2 class="stb-article-block__heading">Jane Example</h2><span>Partner</span><p>Jane Example is a partner in the Corporate Department.</p></main>'
    assert (
        extract_profile(
            "simpson",
            "https://www.stblaw.com/our-team/partners/jane-example/",
            source,
            "2026-11-21",
        )["name"]
        == "Jane Example"
    )


def test_street_address_does_not_become_office():
    source = html("Jane Example is a partner in the Corporate/M&A Group.").replace(
        '<div class="office">New York</div>',
        '<div class="attorney-office"><a href="/en/offices/washington-dc.html">Washington, DC</a></div><div class="contact-address">1101 New York Avenue NW</div>',
    )
    p = extract_profile(
        "milbank", "https://www.milbank.com/en/professionals/jane.html", source, "2026-11-21"
    )
    assert p["offices"] == ["Washington, D.C."]


def test_corporate_dispute_mention_is_not_corporate_practice_membership():
    source = html(
        "Jane Example is a partner in arbitration. She has advised on disputes involving complex contractual, corporate, investment and regulatory issues."
    )
    assert (
        extract_profile(
            "quinn", "https://www.quinnemanuel.com/attorneys/example-jane/", source, "2026-11-21"
        )
        is None
    )


def test_explicit_ma_litigation_is_labelled_adjacent():
    source = html(
        "Jane Example is a partner and Chair of M&A Litigation. She represents clients in corporate governance disputes."
    )
    p = extract_profile(
        "quinn", "https://www.quinnemanuel.com/attorneys/example-jane/", source, "2026-11-21"
    )
    assert p["practices"] == ["M&A Litigation (adjacent)"]


def test_colleague_cards_do_not_supply_offices_or_practices():
    source = '<main><div class="wp-profile-wrapper"><h2 class="stb-article-block__heading">Jane Example</h2><p>Partner</p><a href="/offices/new-york/">New York</a></div><p>Jane is a partner in the Corporate Department.</p><div class="wp-card"><span class="office">London</span><a href="/client-services/practices/corporate/mergers-and-acquisitions/">Mergers and Acquisitions</a></div></main>'
    p = extract_profile(
        "simpson", "https://www.stblaw.com/our-team/partners/jane-example/", source, "2026-11-21"
    )
    assert p["offices"] == ["New York"]
    assert p["practices"] == ["Corporate"]


def test_html_comments_do_not_hide_role_after_heading():
    source = html("Jane Example is a partner in corporate finance.").replace(
        "<h2>Partner</h2>", "<!--" + "layout comment " * 100 + "--><h2>Partner</h2>"
    )
    assert (
        extract_profile(
            "paulweiss",
            "https://www.paulweiss.com/professionals/partners-and-counsel/jane-example",
            source,
            "2026-11-21",
        )
        is not None
    )


def test_profile_subheader_with_role_is_preserved():
    source = '<main><h1>Jane Example</h1><header class="person-details">Partner <span class="office">New York</span></header><p>Jane Example is co-chair of the Corporate Department.</p></main>'
    assert (
        extract_profile("weil", "https://www.weil.com/people/jane-example", source, "2026-11-21")
        is not None
    )


def test_tax_only_structured_practice_is_not_promoted_by_deal_mentions():
    source = html(
        "Jane Example is a partner in the Tax Group. She advises on tax aspects of mergers and acquisitions."
    ).replace(
        "</head>",
        '<script type="application/ld+json">{"@graph":[{"@type":"Person","name":"Jane Example","knowsAbout":["Tax","United States"]}]}</script></head>',
    )
    assert (
        extract_profile(
            "milbank", "https://www.milbank.com/en/professionals/jane.html", source, "2026-11-21"
        )
        is None
    )


def test_weil_contact_header_supplies_office():
    source = '<main><header class="header-b"><h1>Jane Example</h1><span>Partner</span><span>New York</span></header><p>Jane Example is co-chair of the Corporate Department.</p></main>'
    assert extract_profile(
        "weil", "https://www.weil.com/people/jane-example", source, "2026-11-21"
    )["offices"] == ["New York"]


def test_corporate_tax_label_does_not_mean_corporate_partner():
    source = html(
        "Jane Example is a Partner in the Tax Practice. She advises on tax aspects of corporate transactions."
    ).replace(
        "</main>", '<a href="/client-services/practices/corporate/tax/">Corporate Tax</a></main>'
    )
    assert (
        extract_profile(
            "simpson",
            "https://www.stblaw.com/our-team/partners/jane-example/",
            source,
            "2026-11-21",
        )
        is None
    )


@pytest.mark.parametrize(
    "primary",
    [
        "Tax",
        "Litigation Antitrust",
        "Securities Litigation",
        "Appellate and Constitutional Law",
        "Administrative Law",
    ],
)
def test_primary_nontransactional_practice_is_not_promoted_by_ma_mentions(primary):
    source = html(
        "Jane Example advises on corporate governance disputes and mergers and acquisitions."
    ).replace(
        "</main>",
        f'<a href="/practices/primary">{primary}</a><a href="/practices/ma">Mergers and Acquisitions</a></main>',
    )
    assert (
        extract_profile(
            "gibson", "https://www.gibsondunn.com/lawyer/jane-example/", source, "2026-11-21"
        )
        is None
    )


def test_primary_white_collar_bio_is_not_promoted_by_ma_service_link():
    source = html(
        "Jane Example is a partner in the White Collar Defense and Investigations Practice Group."
    ).replace("</main>", '<a href="/practice/ma">Mergers and Acquisitions</a></main>')
    assert (
        extract_profile(
            "gibson", "https://www.gibsondunn.com/lawyer/jane-example/", source, "2026-11-21"
        )
        is None
    )

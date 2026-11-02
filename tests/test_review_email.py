from nzhem.core.agent.review_email import render_review_email


def test_multipart_review_email_has_readable_facts_and_buttons():
    subject, plain, html = render_review_email(
        "M7.8 Kaikōura, 14 Nov 2016 — 78,564 buildings in MMI 6+ shaking",
        {
            "key_figures": [
                {"label": "Buildings in MMI 6+ shaking", "display": "78,564"},
                {"label": "Maximum MMI", "display": "8.4"},
            ],
            "situation": [{"text": "Marlborough Region has the largest exposure."}],
        },
        "https://example.invalid/review?token=approve",
        "https://example.invalid/review?token=reject",
    )
    assert subject == "[NZHEM] Approval needed: M7.8 Kaikōura, 14 Nov 2016"
    assert "78,564" in plain and "78,564" in html
    assert "Marlborough Region" in plain and "Marlborough Region" in html
    assert "# " not in plain and "**" not in plain
    assert "Approve (opens a confirmation page)" in plain
    assert "role='presentation'" in html
    assert "<a href='https://example.invalid/review?token=approve'" in html
    assert "<a href='https://example.invalid/review?token=reject'" in html

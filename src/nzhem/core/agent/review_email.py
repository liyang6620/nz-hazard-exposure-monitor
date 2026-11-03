from __future__ import annotations

from collections.abc import Mapping
from html import escape
from typing import Any


def render_review_email(
    title: str,
    payload: Mapping[str, Any] | None,
    approve_url: str,
    reject_url: str,
    *,
    needs_manual_review: bool = False,
    test_only: bool = False,
) -> tuple[str, str, str]:
    event_title = title.split(" — ", 1)[0]
    subject = f"[NZHEM] {'TEST: ' if test_only else ''}Approval needed: {event_title}"
    figures = list(payload.get("key_figures", [])) if payload else []
    situation = [str(item["text"]) for item in payload.get("situation", [])] if payload else []
    warning = "TEST message. Reject this draft; it cannot be published. " if test_only else ""
    if needs_manual_review:
        warning += "Manual fact review required. "
    approve_button = (
        ""
        if test_only
        else "<a href='"
        + escape(approve_url, quote=True)
        + "' style='display:inline-block;padding:12px 20px;margin:0 10px 10px 0;"
        "background:#171815;color:#faf7ee;text-decoration:none;font-weight:bold'>Approve</a>"
    )
    rows = "".join(
        "<tr><th align='left' style='padding:9px 12px;border-bottom:1px solid #aaa28f'>"
        + escape(str(item["label"]))
        + "</th><td style='padding:9px 12px;border-bottom:1px solid #aaa28f;"
        "font-family:monospace;text-align:right'>" + escape(str(item["display"])) + "</td></tr>"
        for item in figures
    )
    situation_html = " ".join(escape(sentence) for sentence in situation)
    html = (
        "<!doctype html><html lang='en-NZ'><head><meta charset='utf-8'>"
        "<meta name='referrer' content='no-referrer'></head>"
        "<body style='margin:0;padding:24px;background:#f2eddf;color:#171815;"
        "font-family:Arial,Helvetica,sans-serif'>"
        "<table role='presentation' width='100%' cellpadding='0' cellspacing='0'>"
        "<tr><td align='center'><table role='presentation' width='600' cellpadding='0'"
        " cellspacing='0' style='max-width:600px;width:100%;border-top:3px solid #171815'>"
        "<tr><td style='padding:20px 12px 8px;font-size:15px;font-weight:bold'>"
        "NZ Hazard Exposure Monitor</td></tr>"
        "<tr><td style='padding:8px 12px 20px'><h1 style='font-size:25px;line-height:1.2;"
        "font-weight:600;margin:0'>"
        + escape(event_title)
        + "</h1><p style='margin:12px 0 0;font-size:15px'>"
        + escape(warning + "Review the event briefing before publication.")
        + "</p></td></tr>"
        "<tr><td><table role='presentation' width='100%' cellpadding='0' cellspacing='0'"
        " style='border-top:1px solid #aaa28f;border-collapse:collapse'>"
        + rows
        + "</table></td></tr>"
        "<tr><td style='padding:22px 12px 8px'><h2 style='font-size:18px;margin:0 0 8px'>"
        "Situation</h2><p style='line-height:1.5;margin:0'>" + situation_html + "</p></td></tr>"
        "<tr><td style='padding:22px 12px'>"
        + approve_button
        + "<a href='"
        + escape(reject_url, quote=True)
        + "' style='display:inline-block;padding:11px 19px;margin:0 0 10px;"
        "border:1px solid #171815;color:#171815;text-decoration:none;"
        "font-weight:bold'>Reject</a>"
        "<p style='font-size:13px;line-height:1.5'>Each link opens a confirmation page."
        " No decision is made until you select Confirm.</p></td></tr>"
        "</table></td></tr></table></body></html>"
    )
    figure_lines = "\n".join(f"{item['label']}: {item['display']}" for item in figures)
    plain = (
        "NZ Hazard Exposure Monitor\n"
        + event_title
        + "\n\n"
        + warning
        + "Review the event briefing before publication.\n\n"
        + figure_lines
        + "\n\nSituation\n"
        + " ".join(situation)
        + ("\n\nApprove (opens a confirmation page): " + approve_url if not test_only else "")
        + "\nReject (opens a confirmation page): "
        + reject_url
        + "\nNo decision is made until you select Confirm.\n"
    )
    return subject, plain, html

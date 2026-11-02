# Approval email and populated-shaking trigger

2 Nov 2026 implementation record. The change sends multipart HTML and plain
text review mail, links to the static `/review` page, retries only GET while a
Flex host wakes, and requires an explicit click for one POST. The token stays
in the page URL fragment and crosses to the Function in a request header, not
in the new page's HTTP request URL. Old direct Function links remain compatible.
The page has a no-referrer policy and loads no third-party resources. The
Function CORS origin is limited to the public NZHEM website.

D8 now requires a populated exposure cell with raw MMI at least 5.0 before a
new briefing request can call the LLM or send mail. Published MMI values remain
rounded to one decimal; a separate boolean preserves the unrounded threshold.
The local and Azure entry points both enforce the gate.

The saved production Terraform plan in ignored `tmp/` has one in-place Function
App update, zero creations and zero deletions. Its only application-setting
change is `REVIEW_BASE_URL`; its only site-config change adds this website as
the sole CORS origin with credentials disabled. No role, resource type or other
network setting changes. This is the project-manager-approved review-page
scope. The plan itself contains secrets and is not committed.

Verification before PR: 159 Python tests passed with 80.78% coverage; Ruff
checks and Terraform validation passed; 23 frontend unit tests passed; the
new review Playwright test passed in desktop and mobile Chromium. A subsequent
serial full Playwright run passed 13 tests, with one existing conditional test
skipped. The public
test briefing `2026p824047` is absent from the public briefing index and its
HTML returns 404. The owner reported completing the reject confirmation and
POST. The owner account lacks direct `briefings` Table read permission, so
the stored `rejected` value has not been independently inspected.

The [Mailpit screenshot](mailpit-html.png) is a synthetic local multipart send
using public Kaikōura summary figures. Addresses were redacted in the capture;
its buttons contain dummy tokens. It checks rendering only, not ACS delivery.
The owner's real 163-inbox screenshot remains to be captured after a fresh
cloud HTML message is sent. It must hide full links, tokens and addresses.

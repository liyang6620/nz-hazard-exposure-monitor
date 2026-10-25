# M6 local LLM evaluation

`openai-evaluation.json` records the budgeted local evaluation using
`gpt-5-mini`. It contains estimated and actual token costs for every attempted
call and the Mailpit delivery status. The hard cumulative cap is US$1.00.

The evaluation uses the OpenAI Responses API with minimal reasoning and a
450-token output ceiling. The API key is read only from the ignored root
`.env`; it is never written to evidence, logs, prompts, or screenshots. The
approval draft is sent to the local Mailpit SMTP listener only.

On 2026-10-25 the saved successful drafts were delivered without another
OpenAI call. Mailpit reported one message with subject
`NZHEM M6 local approval draft`, and the evidence status is
`sent_to_local_mailpit`. Both SMTP port 1025 and Web UI port 8025 are exposed
only on `127.0.0.1` by Compose.

If Docker Desktop was unavailable during evaluation, start the local Compose
Mailpit service and run `python scripts/run_m6_evaluation.py --mailpit-only`.
That retry sends saved drafts and makes no additional OpenAI call.

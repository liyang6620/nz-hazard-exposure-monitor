# M6 local LLM evaluation

`openai-evaluation.json` records the budgeted local evaluation using
`gpt-5-mini`. It contains estimated and actual token costs for every attempted
call and the Mailpit delivery status. The hard cumulative cap is US$1.00.

The evaluation uses the OpenAI Responses API with minimal reasoning and a
450-token output ceiling. The API key is read only from the ignored root
`.env`; it is never written to evidence, logs, prompts, or screenshots. The
approval draft is sent to the local Mailpit SMTP listener only.

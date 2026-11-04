# M5 redesign evidence

The prior five-page PDF and screenshots were rejected as default tables with
implicit aggregations. They are retained under `rejected-v1/` as historical
evidence only and do not demonstrate acceptance of the redesigned report.

The replacement PBIP contains five specified pages, 61 visual definitions,
11 data tables and 20 explicit measures. The model disables implicit measures,
hides source keys and numeric columns, and uses the paper/ink/MMI theme. The
MMI threshold selects 4–8 with 6 as the default. `check_powerbi_project.py`
passed, including PBIR JSON schema validation. `check_powerbi_snapshot.py`
reconciled all ten events' MMI 6+ buildings and population to M3 gold and found
no orphan region keys. The local snapshot was built with DuckDB limited to
512 MB and one thread; C-drive free space remained above 20 GiB.

Power BI Desktop was launched for validation, but Windows displayed its lock
screen. The redesigned pages have **not yet been refreshed or visually
validated** in Desktop; replacement screenshots, PDF, and model-size report
are still required. No Microsoft account login, licence acceptance or Service
publish was performed. The old screenshot and PDF filenames must not be used
as proof of the new design.

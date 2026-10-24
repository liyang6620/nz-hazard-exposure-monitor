from pathlib import Path

from scripts.run_m6_evaluation import estimate_cost, estimate_tokens, load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def test_m6_cost_estimate_uses_approved_gpt5_mini_rates() -> None:
    assert estimate_tokens("abcd") == 1
    assert estimate_cost(1_000_000, 0) == 0.25
    assert estimate_cost(0, 1_000_000) == 2.0


def test_m6_dotenv_loader_does_not_require_or_print_secrets() -> None:
    values = load_dotenv(ROOT / ".env.example")
    assert values["OPENAI_API_KEY"] == ""
    assert values["ARCGIS_API_KEY"] == ""

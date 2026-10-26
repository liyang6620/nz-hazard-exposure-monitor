from pathlib import Path

from scripts.check_pbip_portability import find_local_paths


def test_committed_pbip_contains_no_machine_local_paths() -> None:
    assert find_local_paths() == []


def test_portability_scan_finds_windows_unc_macos_and_linux_paths(tmp_path: Path) -> None:
    examples = {
        "windows.tmdl": 'Value = "C:\\Users\\owner\\project"',
        "windows-json.json": '{"root": "D:\\\\Users\\\\owner\\\\project"}',
        "unc.pbir": 'Value = "\\\\server\\share\\project"',
        "mac.pbism": 'Value = "/Users/owner/project"',
        "linux.platform": 'Value = "/home/owner/project"',
    }
    for name, content in examples.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    (tmp_path / "portable.tmdl").write_text('Value = "..\\\\.."', encoding="utf-8")
    (tmp_path / "repo-root.tmdl").write_text(
        'Source = File.Contents(RepoRoot & "\\\\.local\\\\data\\\\file.parquet")',
        encoding="utf-8",
    )

    findings = find_local_paths(tmp_path)

    assert {finding.path.name for finding in findings} == set(examples)
    assert all(finding.line_number == 1 for finding in findings)

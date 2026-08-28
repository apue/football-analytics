import json
import subprocess
import sys
from pathlib import Path

SCRIPT = (
    Path(__file__).parents[1]
    / ".codex/skills/academy-conversion-research/scripts/validate_study_config.py"
)
TEMPLATE = (
    Path(__file__).parents[1]
    / ".codex/skills/academy-conversion-research/assets/study-config.template.json"
)


def test_study_template_has_a_valid_reusable_contract():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(TEMPLATE)],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout)
    assert summary["exit_seasons"] == [2015, 2019]
    assert summary["primary_threshold"] == 15
    assert summary["thresholds"] == [10, 15, 20]


def test_live_acquisition_requires_both_sources_to_be_approved(tmp_path):
    config = json.loads(TEMPLATE.read_text())
    config["roster_source"]["policy_status"] = "approved"
    path = tmp_path / "study.json"
    path.write_text(json.dumps(config))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--require-approved"],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "adult_source.policy_status must be approved" in result.stderr


def test_named_academy_and_interval_form_a_runnable_study(tmp_path):
    config = json.loads(TEMPLATE.read_text())
    config["study_id"] = "real-madrid-u19-2015-2020"
    config["academy"] = {
        "academy_id": "real-madrid-u19",
        "display_name": "Real Madrid",
        "squad_name": "Real Madrid U19",
    }
    config["cohorts"]["exit_season_end"] = 2020
    config["cohorts"]["roster_season_end"] = 2022
    config["roster_source"]["policy_status"] = "approved"
    config["adult_source"]["policy_status"] = "approved"
    path = tmp_path / "study.json"
    path.write_text(json.dumps(config))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path), "--require-approved"],
        check=True,
        capture_output=True,
        text=True,
    )

    summary = json.loads(result.stdout)
    assert summary["study_id"] == "real-madrid-u19-2015-2020"
    assert summary["squad_name"] == "Real Madrid U19"
    assert summary["exit_seasons"] == [2015, 2020]


def test_template_rejects_an_unsupported_report_language(tmp_path):
    config = json.loads(TEMPLATE.read_text())
    config["outputs"]["language"] = "en"
    path = tmp_path / "study.json"
    path.write_text(json.dumps(config))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "currently supports only zh-CN" in result.stderr

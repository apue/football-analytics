import json
from pathlib import Path

import pytest

from football_analytics.academy_study import load_academy_study_config

ROOT = Path(__file__).resolve().parents[1]


def test_committed_barcelona_study_uses_artifact_based_sources():
    study = load_academy_study_config(
        ROOT / "config/academy_conversion/studies/barcelona-juvenil-a-2015-2019.json"
    )

    assert study.academy_id == "fc-barcelona-juvenil-a"
    assert study.sensitivity_thresholds == (10, 15, 20)
    assert study.adult_source_scope_id == "public-career-v1-partial"


def test_study_rejects_unknown_source_fields(tmp_path):
    value = json.loads(
        (
            ROOT
            / "config/academy_conversion/studies/barcelona-juvenil-a-2015-2019.json"
        ).read_text()
    )
    value["roster_source"]["unexpected"] = "value"
    path = tmp_path / "study.json"
    path.write_text(json.dumps(value))

    with pytest.raises(ValueError, match="roster_source has unsupported fields"):
        load_academy_study_config(path)


def test_study_requires_approved_sources(tmp_path):
    value = json.loads(
        (
            ROOT
            / "config/academy_conversion/studies/barcelona-juvenil-a-2015-2019.json"
        ).read_text()
    )
    value["adult_source"]["policy_status"] = "pending"
    path = tmp_path / "study.json"
    path.write_text(json.dumps(value))

    with pytest.raises(ValueError, match="adult_source.policy_status must be approved"):
        load_academy_study_config(path)

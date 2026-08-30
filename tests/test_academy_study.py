import json
from pathlib import Path

import pytest

from football_analytics.academy_study import load_academy_study_config

ROOT = Path(__file__).resolve().parents[1]


def test_committed_barcelona_study_uses_artifact_based_sources():
    study = load_academy_study_config(
        ROOT / "config/academy_conversion/studies/barcelona-juvenil-a-2015-2019.json",
        require_approved=True,
    )

    assert study.academy_id == "fc-barcelona-juvenil-a"
    assert study.sensitivity_thresholds == (10, 15, 20)
    assert study.adult_source_scope_id == "public-career-v1-partial"


def test_study_rejects_deprecated_source_adapter(tmp_path):
    value = json.loads(
        (
            ROOT
            / "config/academy_conversion/studies/barcelona-juvenil-a-2015-2019.json"
        ).read_text()
    )
    value["roster_source"]["adapter"] = "legacy"
    path = tmp_path / "study.json"
    path.write_text(json.dumps(value))

    with pytest.raises(ValueError, match="adapter is obsolete"):
        load_academy_study_config(path)

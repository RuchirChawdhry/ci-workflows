import json
from scripts.compat_report import summarize, markdown

def test_collects_missing_versions_as_infrastructure(tmp_path):
    (tmp_path / "3.10.json").write_text(json.dumps({"version":"3.10","status":"PASS","reason":"Checks passed"}))
    (tmp_path / "3.8.json").write_text(json.dumps({"version":"3.8","status":"DEPENDENCY","reason":"foo requires >=3.9"}))
    report = summarize(tmp_path, ["3.8","3.9","3.10"])
    assert report["counts"] == {"DEPENDENCY":1,"INFRA":1,"PASS":1}
    assert report["lowest_passing"] == "3.10"
    assert "| 3.9 | INFRA |" in markdown(report)

def test_numeric_version_order_and_support_caveat(tmp_path):
    for version,status in [("3.10","PASS"),("3.9","PASS"),("3.11","TEST")]:
        (tmp_path / f"{version}.json").write_text(json.dumps({"version":version,"status":status,"reason":"x"}))
    report = summarize(tmp_path, ["3.10","3.9","3.11"])
    assert [r["version"] for r in report["results"]] == ["3.9","3.10","3.11"]
    assert report["lowest_passing"] == "3.9"
    assert "not an official support guarantee" in markdown(report)

def test_all_missing(tmp_path):
    assert summarize(tmp_path / "absent", ["3.14"])["results"][0]["status"] == "INFRA"

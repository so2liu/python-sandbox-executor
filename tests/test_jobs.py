import json
import time

from fastapi.testclient import TestClient

from job_runner.api import app


def test_job_execution_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("JOB_DATA_DIR", str(tmp_path / "jobs"))

    client = TestClient(app)
    with client:
        spec = {
            "entry": "main.py",
            "timeout_sec": 10,
        }
        code = """
import os
import pandas as pd

print("hello from job")
df = pd.DataFrame({"x": [1, 2, 3]})
out_dir = os.environ["JOB_OUTPUT_DIR"]
df.to_csv(os.path.join(out_dir, "result.csv"), index=False)
print("rows", len(df))
"""
        files = [
            ("code_files", ("main.py", code.encode(), "text/x-python")),
        ]
        resp = client.post("/jobs", data={"spec": json.dumps(spec)}, files=files)
        assert resp.status_code == 200, resp.text
        job_id = resp.json()["job_id"]

        status = ""
        for _ in range(200):
            detail = client.get(f"/jobs/{job_id}").json()
            status = detail["job"]["status"]
            if status in {"succeeded", "failed"}:
                break
            time.sleep(0.05)

        assert status == "succeeded"

        log_resp = client.get(f"/jobs/{job_id}/logs")
        assert "hello from job" in log_resp.text
        assert "rows 3" in log_resp.text

        sse_resp = client.get(f"/jobs/{job_id}/logs/stream")
        assert "data: hello from job" in sse_resp.text
        assert "event: end" in sse_resp.text

        art_resp = client.get(f"/jobs/{job_id}/artifacts/result.csv")
        assert art_resp.status_code == 200
        content = art_resp.text.strip().splitlines()
        assert content[0] == "x"
        assert content[1:] == ["1", "2", "3"]

import json

from fastapi.testclient import TestClient

from job_runner.api import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_index():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Python Code Runner" in resp.text


def test_run_simple_code(tmp_job_dir):
    client = TestClient(app)
    spec = {"entry": "main.py", "timeout_sec": 10}
    code = 'print("hello world")'
    files = [("code_files", ("main.py", code.encode(), "text/x-python"))]

    resp = client.post("/run", data={"spec": json.dumps(spec)}, files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["exit_code"] == 0
    assert "hello world" in data["logs"]


def test_run_with_artifacts(tmp_job_dir):
    client = TestClient(app)
    spec = {"entry": "main.py", "timeout_sec": 10}
    code = """
import os
out_dir = os.environ["JOB_OUTPUT_DIR"]
with open(os.path.join(out_dir, "result.txt"), "w") as f:
    f.write("output data")
print("done")
"""
    files = [("code_files", ("main.py", code.encode(), "text/x-python"))]

    resp = client.post("/run", data={"spec": json.dumps(spec)}, files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "succeeded"
    assert "result.txt" in data["artifacts"]
    assert "done" in data["logs"]

    art_resp = client.get(f"/jobs/{data['job_id']}/artifacts/result.txt")
    assert art_resp.status_code == 200
    assert art_resp.text == "output data"


def test_run_with_input_files(tmp_job_dir):
    client = TestClient(app)
    spec = {"entry": "main.py", "timeout_sec": 10}
    code = """
import os
input_dir = os.environ["JOB_INPUT_DIR"]
with open(os.path.join(input_dir, "data.txt")) as f:
    content = f.read()
print(f"read: {content}")
"""
    files = [
        ("code_files", ("main.py", code.encode(), "text/x-python")),
        ("input_files", ("data.txt", b"test input", "text/plain")),
    ]

    resp = client.post("/run", data={"spec": json.dumps(spec)}, files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "succeeded"
    assert "read: test input" in data["logs"]


def test_run_timeout(tmp_job_dir):
    client = TestClient(app)
    spec = {"entry": "main.py", "timeout_sec": 1}
    code = """
import time
print("starting")
time.sleep(10)
print("done")
"""
    files = [("code_files", ("main.py", code.encode(), "text/x-python"))]

    resp = client.post("/run", data={"spec": json.dumps(spec)}, files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "failed"
    assert data["error"] == "timeout"
    assert "timeout exceeded" in data["logs"]


def test_run_error(tmp_job_dir):
    client = TestClient(app)
    spec = {"entry": "main.py", "timeout_sec": 10}
    code = """
print("before error")
raise ValueError("test error")
"""
    files = [("code_files", ("main.py", code.encode(), "text/x-python"))]

    resp = client.post("/run", data={"spec": json.dumps(spec)}, files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "failed"
    assert data["exit_code"] != 0
    assert "before error" in data["logs"]


def test_run_missing_entry(tmp_job_dir):
    client = TestClient(app)
    spec = {"entry": "nonexistent.py", "timeout_sec": 10}
    code = 'print("hello")'
    files = [("code_files", ("main.py", code.encode(), "text/x-python"))]

    resp = client.post("/run", data={"spec": json.dumps(spec)}, files=files)
    assert resp.status_code == 200

    data = resp.json()
    assert data["status"] == "failed"
    assert data["error"] == "missing entry file"


def test_run_invalid_spec(tmp_job_dir):
    client = TestClient(app)
    files = [("code_files", ("main.py", b'print("hi")', "text/x-python"))]

    resp = client.post("/run", data={"spec": "not json"}, files=files)
    assert resp.status_code in (400, 422)  # 400 for invalid JSON, 422 for validation error


def test_artifact_not_found(tmp_job_dir):
    client = TestClient(app)
    resp = client.get("/jobs/nonexistent/artifacts/file.txt")
    assert resp.status_code == 404

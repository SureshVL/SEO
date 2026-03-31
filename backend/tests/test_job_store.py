from app.services.job_store import SQLiteJobStore


def test_job_store_lifecycle(tmp_path):
    store = SQLiteJobStore(str(tmp_path / "jobs.db"))
    job = store.create_job({"research_request": {"client_url": "https://example.com", "primary_keyword": "seo"}})

    assert job.status == "pending"

    store.mark_running(job.job_id)
    store.append_log(job.job_id, "running")

    fetched = store.get_job(job.job_id)
    assert fetched is not None
    assert fetched.status == "running"
    assert fetched.logs
    assert fetched.logs[0]["seq"] == 1

    new_logs = store.logs_since(job.job_id, last_seq=0)
    assert len(new_logs) == 1

    store.mark_failed(job.job_id, "boom")
    fetched2 = store.get_job(job.job_id)
    assert fetched2 is not None
    assert fetched2.status == "failed"
    assert fetched2.error == "boom"

from types import SimpleNamespace

from scripts import daily_ops_pipeline


def test_run_public_crawl_with_retry_recovers_after_transient_failure(monkeypatch):
    calls = []

    def fake_run_public_crawl(db, keyword):
        calls.append(keyword)
        if len(calls) == 1:
            return SimpleNamespace(
                id=1,
                status="failed",
                total_found=0,
                total_saved=0,
                error_message="temporary ssl eof",
            )
        return SimpleNamespace(
            id=2,
            status="success",
            total_found=11,
            total_saved=3,
            error_message=None,
        )

    monkeypatch.setattr(daily_ops_pipeline, "run_public_crawl", fake_run_public_crawl)
    monkeypatch.setattr(daily_ops_pipeline.time, "sleep", lambda _seconds: None)

    task, attempts = daily_ops_pipeline._run_public_crawl_with_retry(
        db=SimpleNamespace(rollback=lambda: None),
        keyword="废钢",
        attempts=3,
        backoff_seconds=0,
    )

    assert attempts == 2
    assert task.status == "success"
    assert calls == ["废钢", "废钢"]


def test_run_public_crawl_with_retry_reports_final_failure(monkeypatch):
    def fake_run_public_crawl(db, keyword):
        return SimpleNamespace(
            id=3,
            status="failed",
            total_found=0,
            total_saved=0,
            error_message=f"{keyword} source unavailable",
        )

    monkeypatch.setattr(daily_ops_pipeline, "run_public_crawl", fake_run_public_crawl)
    monkeypatch.setattr(daily_ops_pipeline.time, "sleep", lambda _seconds: None)

    task, attempts = daily_ops_pipeline._run_public_crawl_with_retry(
        db=SimpleNamespace(rollback=lambda: None),
        keyword="钢材",
        attempts=2,
        backoff_seconds=0,
    )

    assert attempts == 2
    assert task.status == "failed"
    assert task.error_message == "钢材 source unavailable"

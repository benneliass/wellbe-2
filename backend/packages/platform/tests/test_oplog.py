from wellbe_platform.oplog import format_op, log_op


def test_format_op_stable_tokens() -> None:
    line = format_op(
        "op.fail",
        "outbox.dispatch",
        fields={"reason": "vault_404", "event_id": "abc"},
    )
    assert line == "event=op.fail op=outbox.dispatch reason=vault_404 event_id=abc"


def test_log_op_fail_is_error(caplog) -> None:
    import logging

    logger = logging.getLogger("wellbe.test.oplog")
    with caplog.at_level(logging.INFO, logger="wellbe.test.oplog"):
        log_op(logger, "op.retry", "outbox.dispatch", fields={"reason": "vault_status"})
    rec = caplog.records[0]
    assert rec.levelno == logging.WARNING
    assert "event=op.retry op=outbox.dispatch" in rec.getMessage()

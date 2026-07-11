from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, BrowserSession, BrowserTab, ExecutionTask, ReplyTask, SubmissionLog, SubmissionTask, WorkerNode
from app.response import ok
from app.serializers import serialize_model
from app.services.submission_runtime import SubmissionRuntime


router = APIRouter(prefix="/submission", tags=["submission"])
task_router = APIRouter(prefix="/submission-tasks", tags=["submission"])
stats_router = APIRouter(tags=["submission"])


def serialize_submission_task(task: SubmissionTask, db: Session) -> dict:
    item = serialize_model(task)
    reply_task = db.get(ReplyTask, task.reply_task_id) if task.reply_task_id else None
    execution = db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
    account = db.get(Account, task.account_id) if task.account_id else None
    worker = db.get(WorkerNode, task.worker_id) if task.worker_id else None
    session = db.get(BrowserSession, task.browser_session_id) if task.browser_session_id else None
    tab = db.get(BrowserTab, task.browser_tab_id) if task.browser_tab_id else None
    item["reply_content"] = reply_task.reply_content if reply_task else None
    item["reply_content_preview"] = (reply_task.reply_content[:240] if reply_task else None)
    item["reply_task_status"] = reply_task.status if reply_task else None
    item["execution_status"] = execution.status if execution else None
    item["account"] = account.username if account else None
    item["worker"] = worker.name if worker else None
    item["browser_session_status"] = session.status if session else None
    item["browser_tab_url"] = tab.url if tab else None
    item["contract"] = SubmissionRuntime(db).contract(task)
    item["retryable"] = SubmissionRuntime(db).recovery.decision(task, task.error_code or task.failure_reason)["retryable"]
    item["retry_blocked_reason"] = item.get("retry_blocked_reason") or SubmissionRuntime(db).recovery.decision(task, task.error_code or task.failure_reason)["reason"]
    return item


@router.get("/dashboard")
def submission_dashboard(request: Request, db: Session = Depends(get_db)):
    return ok(SubmissionRuntime(db).dashboard_counts(), request.state.trace_id)


@router.get("/tasks")
def list_submission_tasks(request: Request, db: Session = Depends(get_db)):
    tasks = db.scalars(select(SubmissionTask).order_by(SubmissionTask.created_at.desc())).all()
    return ok([serialize_submission_task(task, db) for task in tasks], request.state.trace_id)


@router.get("/tasks/{task_id}")
def get_submission_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(SubmissionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="submission task not found")
    return ok(serialize_submission_task(task, db), request.state.trace_id)


@router.post("/tasks/{task_id}/submit")
def submit_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        task = SubmissionRuntime(db, trace_id=request.state.trace_id).submit_reply(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_submission_task(task, db), request.state.trace_id, "submission policy evaluated")


@router.post("/tasks/{task_id}/record-manual-result")
def record_manual_result(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(SubmissionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="submission task not found")
    reply_task = db.get(ReplyTask, task.reply_task_id) if task.reply_task_id else None
    if not reply_task:
        raise HTTPException(status_code=409, detail="submission task has no reply task")
    execution = db.get(ExecutionTask, task.execution_task_id) if task.execution_task_id else None
    scheduler = None
    if execution and execution.scheduler_task_id:
        from app.models import SchedulerTask

        scheduler = db.get(SchedulerTask, execution.scheduler_task_id)
    task = SubmissionRuntime(db, trace_id=request.state.trace_id).record_manual_result(
        reply_task=reply_task,
        execution=execution,
        scheduler=scheduler,
    )
    db.commit()
    db.refresh(task)
    return ok(serialize_submission_task(task, db), request.state.trace_id, "manual result recorded")


@router.post("/tasks/{task_id}/cancel")
def cancel_submission_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(SubmissionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="submission task not found")
    runtime = SubmissionRuntime(db, trace_id=request.state.trace_id)
    old = task.status
    runtime.set_status(task, "CANCELLED", reason="Submission task cancelled by operator.")
    runtime.log(
        task,
        "CANCELLED",
        "Submission task cancelled by operator.",
        metadata={"old_status": old},
    )
    db.commit()
    db.refresh(task)
    return ok(serialize_submission_task(task, db), request.state.trace_id, "submission task cancelled")


@router.post("/tasks/{task_id}/mark-failed")
def mark_failed_submission_task(task_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    reason = str(payload.get("failure_reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=422, detail="failure_reason is required")
    try:
        task = SubmissionRuntime(db, trace_id=request.state.trace_id).mark_failed(task_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_submission_task(task, db), request.state.trace_id, "submission task marked failed")


@router.post("/tasks/{task_id}/retry")
def retry_submission_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        task = SubmissionRuntime(db, trace_id=request.state.trace_id).retry(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_submission_task(task, db), request.state.trace_id, "submission retry evaluated")


@router.get("/tasks/{task_id}/logs")
def get_submission_task_logs(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(SubmissionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="submission task not found")
    logs = db.scalars(
        select(SubmissionLog)
        .where(SubmissionLog.submission_task_id == task.id)
        .order_by(SubmissionLog.created_at.desc())
    ).all()
    return ok([serialize_model(log) for log in logs], request.state.trace_id)


@router.get("/logs")
def list_submission_logs(request: Request, db: Session = Depends(get_db)):
    logs = db.scalars(select(SubmissionLog).order_by(SubmissionLog.created_at.desc()).limit(100)).all()
    return ok([serialize_model(log) for log in logs], request.state.trace_id)


@router.post("/reply-tasks/{reply_task_id}/prepare-submission")
def prepare_submission_for_reply(reply_task_id: int, request: Request, db: Session = Depends(get_db)):
    reply_task = db.get(ReplyTask, reply_task_id)
    if not reply_task:
        raise HTTPException(status_code=404, detail="reply task not found")
    execution = db.get(ExecutionTask, reply_task.execution_task_id) if reply_task.execution_task_id else None
    task = SubmissionRuntime(db, trace_id=request.state.trace_id).prepare_submission(
        reply_task=reply_task,
        execution=execution,
    )
    db.commit()
    db.refresh(task)
    return ok(serialize_submission_task(task, db), request.state.trace_id, "submission prepared")


@task_router.get("")
def alias_list_submission_tasks(request: Request, db: Session = Depends(get_db)):
    return list_submission_tasks(request, db)


@task_router.get("/{task_id}")
def alias_get_submission_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    return get_submission_task(task_id, request, db)


@task_router.post("/{task_id}/confirm")
def alias_confirm_submission_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    return record_manual_result(task_id, request, db)


@task_router.post("/{task_id}/mark-failed")
def alias_mark_failed_submission_task(task_id: int, payload: dict, request: Request, db: Session = Depends(get_db)):
    return mark_failed_submission_task(task_id, payload, request, db)


@task_router.post("/{task_id}/retry")
def alias_retry_submission_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    return retry_submission_task(task_id, request, db)


@task_router.post("/{task_id}/cancel")
def alias_cancel_submission_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    return cancel_submission_task(task_id, request, db)


@stats_router.get("/submission-stats")
def submission_stats(request: Request, db: Session = Depends(get_db)):
    return ok(SubmissionRuntime(db).submission_statistics(), request.state.trace_id)


@stats_router.get("/submission-failures")
def submission_failures(request: Request, db: Session = Depends(get_db)):
    return ok(SubmissionRuntime(db).failures(), request.state.trace_id)

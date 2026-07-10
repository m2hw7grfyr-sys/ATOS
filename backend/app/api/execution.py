from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Account, ExecutionLog, ExecutionQueue, ExecutionTask, ReplayFile, ReplayIndex, SchedulerTask, TGEProfile, WorkerNode
from app.response import ok
from app.serializers import serialize_model
from app.services.execution import ExecutionRuntime, run_precheck, set_execution_status
from app.services.playwright_runner import close_execution_tab, mark_submitted, prepare_reply, run_open_page


router = APIRouter(prefix="/execution", tags=["execution"])


def serialize_execution_task(task: ExecutionTask, db: Session) -> dict:
    item = serialize_model(task)
    scheduler_task = db.get(SchedulerTask, task.scheduler_task_id) if task.scheduler_task_id else None
    account = db.get(Account, task.account_id) if task.account_id else None
    profile = db.get(TGEProfile, task.tge_profile_id) if task.tge_profile_id else None
    item["task_id"] = task.id
    item["scheduler_status"] = scheduler_task.status if scheduler_task else None
    item["execution_status"] = task.status
    item["account"] = account.username if account else None
    item["reply_content_preview"] = (task.payload_json or {}).get("reply_content_preview") or (task.payload_json or {}).get("reply_content")
    item["fill_status"] = (task.payload_json or {}).get("fill_status")
    item["manual_confirmed"] = (task.payload_json or {}).get("manual_confirmed")
    item["queue_status"] = task.queue_status
    item["retry_count"] = task.retry_count
    item["claimed_at"] = task.claimed_at.isoformat() if task.claimed_at else None
    item["last_heartbeat_at"] = task.last_heartbeat_at.isoformat() if task.last_heartbeat_at else None
    item["tge_environment_id"] = (
        profile.tge_environment_id or profile.environment_id if profile else None
    )
    return item


@router.get("/runtime")
def get_runtime(request: Request, db: Session = Depends(get_db)):
    runtime = ExecutionRuntime(db)
    worker = runtime.register_worker()
    runtime.heartbeat(worker)
    db.commit()
    return ok(runtime.runtime_status(), request.state.trace_id)


@router.get("/workers")
def list_workers(request: Request, db: Session = Depends(get_db)):
    workers = db.scalars(select(WorkerNode).order_by(WorkerNode.updated_at.desc())).all()
    return ok([serialize_model(worker) for worker in workers], request.state.trace_id)


@router.get("/tasks")
def list_execution_tasks(request: Request, db: Session = Depends(get_db)):
    tasks = db.scalars(select(ExecutionTask).order_by(ExecutionTask.created_at.desc())).all()
    return ok([serialize_execution_task(task, db) for task in tasks], request.state.trace_id)


@router.get("/queue")
def list_execution_queue(request: Request, db: Session = Depends(get_db)):
    rows = db.scalars(select(ExecutionQueue).order_by(ExecutionQueue.queued_at.desc())).all()
    return ok([serialize_model(row) for row in rows], request.state.trace_id)


@router.get("/tasks/{task_id}")
def get_execution_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    return ok(serialize_execution_task(task, db), request.state.trace_id)


@router.post("/claim-next")
def claim_next(request: Request, db: Session = Depends(get_db)):
    runtime = ExecutionRuntime(db)
    task = runtime.claim_next()
    db.commit()
    return ok(serialize_execution_task(task, db) if task else None, request.state.trace_id, "claim completed")


@router.post("/tasks/{task_id}/run-runtime")
def run_runtime_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    ExecutionRuntime(db).run_claimed(task)
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "runtime task running")


@router.post("/tasks/{task_id}/resume")
def resume_manual_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        task = ExecutionRuntime(db).resume_manual(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "manual task resumed")


@router.post("/retry")
def retry_execution(payload: dict, request: Request, db: Session = Depends(get_db)):
    try:
        task = ExecutionRuntime(db).retry(int(payload.get("task_id")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "execution task retried")


@router.post("/cancel")
def cancel_execution(payload: dict, request: Request, db: Session = Depends(get_db)):
    try:
        task = ExecutionRuntime(db).cancel(int(payload.get("task_id")))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "execution task cancelled")


@router.post("/tasks/{task_id}/precheck")
def precheck_execution_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    run_precheck(db, task)
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "precheck completed")


@router.post("/tasks/{task_id}/attach")
def attach_execution_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    set_execution_status(db, task, "ATTACHING", "ATTACH_STARTED", message="Attach scaffold started")
    set_execution_status(db, task, "ATTACHED", "ATTACH_SUCCESS", message="Attach scaffold completed")
    db.commit()
    return ok(serialize_execution_task(task, db), request.state.trace_id, "attach completed")


@router.post("/tasks/{task_id}/run-open-page")
def run_open_page_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    if task.precheck_status != "SUCCESS":
        run_precheck(db, task)
        if task.status == "FAILED":
            db.commit()
            return ok(serialize_execution_task(task, db), request.state.trace_id, "precheck failed")
    run_open_page(db, task)
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "open page flow completed")


@router.post("/tasks/{task_id}/prepare-reply")
def prepare_reply_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    task.action_type = "PREPARE_REPLY"
    if task.precheck_status != "SUCCESS":
        run_precheck(db, task)
        if task.status == "FAILED":
            db.commit()
            return ok(serialize_execution_task(task, db), request.state.trace_id, "precheck failed")
    prepare_reply(db, task)
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "reply prepared")


@router.post("/tasks/{task_id}/retry-fill")
def retry_fill_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    task.error_code = None
    task.error_message = None
    task.status = "ENVIRONMENT_READY"
    prepare_reply(db, task)
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "reply fill retried")


@router.post("/tasks/{task_id}/mark-submitted")
def mark_submitted_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    mark_submitted(db, task)
    db.commit()
    db.refresh(task)
    return ok(serialize_execution_task(task, db), request.state.trace_id, "manual submission confirmed")


@router.post("/tasks/{task_id}/close-tab")
def close_tab_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    close_execution_tab(db, task)
    db.commit()
    return ok(serialize_execution_task(task, db), request.state.trace_id, "tab closed")


@router.post("/tasks/{task_id}/mark-success")
def mark_success(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    set_execution_status(db, task, "SUCCESS", "MARK_SUCCESS", message="Marked success manually")
    db.commit()
    return ok(serialize_execution_task(task, db), request.state.trace_id, "execution marked success")


@router.post("/tasks/{task_id}/mark-failed")
def mark_failed(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    set_execution_status(db, task, "FAILED", "MARK_FAILED", error_code="MANUAL_FAILED", error_message="Marked failed manually")
    db.commit()
    return ok(serialize_execution_task(task, db), request.state.trace_id, "execution marked failed")


@router.get("/tasks/{task_id}/replay")
def get_replay(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    replay = db.scalar(select(ReplayFile).where(ReplayFile.execution_task_id == task.id))
    index = db.scalar(select(ReplayIndex).where(ReplayIndex.execution_task_id == task.id))
    return ok(
        {
            "files": serialize_model(replay) if replay else None,
            "index": serialize_model(index) if index else None,
        },
        request.state.trace_id,
    )


@router.get("/tasks/{task_id}/logs")
def get_execution_logs(task_id: int, request: Request, db: Session = Depends(get_db)):
    task = db.get(ExecutionTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="execution task not found")
    logs = db.scalars(
        select(ExecutionLog).where(ExecutionLog.execution_task_id == task.id).order_by(ExecutionLog.created_at.desc())
    ).all()
    return ok([serialize_model(log) for log in logs], request.state.trace_id)

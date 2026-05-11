import logging
from fastapi import APIRouter, HTTPException, Request
from Coder.server.schemas import SOPCreateRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_orchestrator(request: Request):
    sop_context = request.app.state.sop_context
    if not sop_context:
        raise HTTPException(status_code=503, detail="SOP 系统未初始化")
    orch = sop_context.get("orchestrator")
    if not orch:
        raise HTTPException(status_code=503, detail="SOP 编排器未初始化")
    return orch


def _get_checkpoint_mgr(request: Request):
    sop_context = request.app.state.sop_context
    if not sop_context:
        return None
    return sop_context.get("checkpoint_mgr")


@router.get("/checkpoints/list")
async def list_checkpoints(request: Request):
    mgr = _get_checkpoint_mgr(request)
    if not mgr:
        return {"checkpoints": []}
    checkpoints = mgr.list_checkpoints()
    return {"checkpoints": checkpoints}


@router.get("/list")
async def list_sops(request: Request):
    try:
        orch = _get_orchestrator(request)
    except HTTPException:
        return {"sop_names": [], "count": 0}
    sop_names = orch.list_sops()
    return {"sop_names": sop_names, "count": len(sop_names)}


@router.get("/status")
async def sop_status(request: Request):
    sop_context = request.app.state.sop_context
    retriever = sop_context.get("retriever") if sop_context else None
    orch = sop_context.get("orchestrator") if sop_context else None
    return {
        "knowledge_connected": retriever is not None and retriever.is_available(),
        "sop_count": len(orch.list_sops()) if orch else 0,
    }


@router.post("/create")
async def create_sop(req: SOPCreateRequest, request: Request):
    orch = _get_orchestrator(request)

    from Coder.sop.validator import SOPValidator
    validator = SOPValidator()

    sop_data = {
        "name": req.name,
        "description": req.description or "",
        "steps": req.steps,
    }

    validation = validator.validate_sop_structure(sop_data)
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail={"issues": validation["issues"]},
        )

    orch.save_sop(req.name, sop_data)
    return {"status": "created", "name": req.name, "steps_count": len(req.steps)}


@router.get("/{sop_name}")
async def get_sop(sop_name: str, request: Request):
    orch = _get_orchestrator(request)
    sop = orch.get_sop(sop_name)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP not found")
    return sop


@router.delete("/{sop_name}")
async def delete_sop(sop_name: str, request: Request):
    orch = _get_orchestrator(request)
    ok = orch.delete_sop(sop_name)
    if not ok:
        raise HTTPException(status_code=404, detail="SOP not found")
    return {"status": "deleted"}


@router.post("/{sop_name}/execute")
async def execute_sop(sop_name: str, request: Request):
    orch = _get_orchestrator(request)
    result = orch.start_execution(sop_name)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to start execution")
    return result

import logging
from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse
from Coder.server.schemas import SkillUploadRequest, SkillToggleRequest
from Coder.tools.skill_store import SkillDefinition

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_skill_store(request: Request):
    return request.app.state.skill_store


@router.get("/")
async def list_skills(request: Request):
    store = _get_skill_store(request)
    metas = await store.list_skills_meta(enabled_only=False)
    return {
        "skills": [
            {
                "name": m.name,
                "display_name": m.display_name,
                "description": m.description,
                "category": m.category,
                "tags": m.tags,
                "version": m.version,
                "enabled": m.enabled,
                "author": m.author,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            }
            for m in metas
        ]
    }


@router.get("/{skill_name}")
async def get_skill(request: Request, skill_name: str):
    store = _get_skill_store(request)
    skill = await store.load_skill(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.to_dict()


@router.post("/upload")
async def upload_skill_json(request: Request, req: SkillUploadRequest):
    store = _get_skill_store(request)
    skill_def = SkillDefinition.from_dict(req.skill_json)
    ok = await store.save_skill(skill_def)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to save skill")
    return {"status": "saved", "name": skill_def.name}


@router.post("/upload-file")
async def upload_skill_file(request: Request, file: UploadFile = File(...)):
    store = _get_skill_store(request)

    raw_name = file.filename or "unknown"

    if not raw_name.lower().endswith(".md"):
        raise HTTPException(
            status_code=400,
            detail="仅支持 .md 格式的文件",
        )

    name_no_ext = raw_name.rsplit(".", 1)[0].lower()
    if "skill" not in name_no_ext:
        raise HTTPException(
            status_code=400,
            detail="文件名需包含 'skill' 关键词",
        )

    content_bytes = await file.read()
    file_size_mb = len(content_bytes) / (1024 * 1024)
    if file_size_mb > 5:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大 ({file_size_mb:.1f}MB)，最大允许 5MB",
        )

    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="文件编码错误，请使用 UTF-8 编码",
        )

    from Coder.tools.skill_parser import SkillParser
    skill_def = SkillParser.parse_markdown(content, name_hint=name_no_ext)
    if skill_def is None:
        return JSONResponse(
            status_code=422,
            content={
                "detail": "解析失败：无法从文件中提取有效的 Skill 定义",
                "content_preview": content[:2000],
            },
        )

    code_ok = True
    code_msg = ""
    if skill_def.code:
        from Coder.tools.skill_compiler import SkillCompiler
        code_ok, code_msg = SkillCompiler.validate(skill_def.code)

    is_overwrite = await store.exists(skill_def.name)

    if not await store.save_skill(skill_def):
        raise HTTPException(status_code=500, detail="保存 Skill 失败")

    from Coder.tools.skill_registry import SkillRegistry
    registry = SkillRegistry()
    if registry._initialized:
        registry.reload_skill(skill_def.name)

    return {
        "status": "updated" if is_overwrite else "created",
        "name": skill_def.name,
        "display_name": skill_def.display_name,
        "description": skill_def.description,
        "category": skill_def.category,
        "version": skill_def.version,
        "tags": skill_def.tags,
        "parameters": skill_def.parameters,
        "code_ok": code_ok,
        "code_msg": code_msg,
        "has_code": bool(skill_def.code),
    }


@router.put("/{skill_name}/toggle")
async def toggle_skill(request: Request, skill_name: str, req: SkillToggleRequest):
    store = _get_skill_store(request)
    ok = await store.toggle_skill(skill_name, req.enabled)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "toggled", "enabled": req.enabled}


@router.delete("/{skill_name}")
async def delete_skill(request: Request, skill_name: str):
    store = _get_skill_store(request)
    ok = await store.delete_skill(skill_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "deleted"}

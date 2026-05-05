import os
import logging
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from Coder.server.schemas import SkillUploadRequest, SkillToggleRequest
from Coder.tools.skill_store import SkillStore, SkillDefinition

logger = logging.getLogger(__name__)
router = APIRouter()
store = SkillStore()


@router.get("/")
async def list_skills():
    skills_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "skills"
    )
    skills_path = os.path.normpath(skills_path)

    if not os.path.exists(skills_path):
        return {"skills": []}

    skill_files = [f for f in os.listdir(skills_path) if f.endswith(".json")]
    skills = []
    for f in skill_files:
        name = f[:-5]
        meta = store.load_skill_meta(name)
        if meta:
            skills.append({
                "name": meta.name,
                "display_name": meta.display_name,
                "description": meta.description,
                "category": meta.category,
                "tags": meta.tags,
                "version": meta.version,
                "enabled": meta.enabled,
                "author": meta.author,
                "created_at": meta.created_at,
                "updated_at": meta.updated_at,
            })
    return {"skills": skills}


@router.get("/{skill_name}")
async def get_skill(skill_name: str):
    skill = store.load_skill(skill_name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.to_dict()


@router.post("/upload")
async def upload_skill_json(req: SkillUploadRequest):
    skill_def = SkillDefinition.from_dict(req.skill_json)
    ok = store.save_skill(skill_def)
    if not ok:
        raise HTTPException(status_code=400, detail="Failed to save skill")
    return {"status": "saved", "name": skill_def.name}


@router.post("/upload-file")
async def upload_skill_file(file: UploadFile = File(...)):
    raw_name = file.filename or "unknown"

    if not raw_name.lower().endswith(".md"):
        raise HTTPException(
            status_code=400,
            detail="仅支持 .md 格式的文件",
        )

    name_no_ext = os.path.splitext(raw_name)[0].lower()
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
            content={"detail": "解析失败：无法从文件中提取有效的 Skill 定义", "content_preview": content[:2000]},
        )

    code_ok = True
    code_msg = ""
    if skill_def.code:
        from Coder.tools.skill_compiler import SkillCompiler
        code_ok, code_msg = SkillCompiler.validate(skill_def.code)

    is_overwrite = store.exists(skill_def.name)

    if not store.save_skill(skill_def):
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
async def toggle_skill(skill_name: str, req: SkillToggleRequest):
    ok = store.toggle_skill(skill_name, req.enabled)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "toggled", "enabled": req.enabled}


@router.delete("/{skill_name}")
async def delete_skill(skill_name: str):
    ok = store.delete_skill(skill_name)
    if not ok:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "deleted"}

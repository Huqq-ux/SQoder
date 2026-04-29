import os
import sys
import shutil
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_temp_dir():
    return tempfile.mkdtemp(prefix="skill_test_")


def test_skill_store_save_and_load():
    from Coder.tools.skill_store import SkillStore, SkillDefinition

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        skill = SkillDefinition(
            name="test_skill",
            display_name="测试技能",
            description="用于测试的技能",
            category="测试",
            parameters=[
                {"name": "param1", "type": "str", "required": True, "description": "参数1"},
            ],
            code="",
        )

        assert store.save_skill(skill)
        assert store.exists("test_skill")

        loaded = store.load_skill("test_skill")
        assert loaded is not None
        assert loaded.name == "test_skill"
        assert loaded.display_name == "测试技能"
        assert loaded.category == "测试"
        assert len(loaded.parameters) == 1

        print("PASS: test_skill_store_save_and_load")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_store_list_and_delete():
    from Coder.tools.skill_store import SkillStore, SkillDefinition

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        for i in range(3):
            skill = SkillDefinition(
                name=f"skill_{i}",
                display_name=f"技能{i}",
                description=f"描述{i}",
                category="测试",
            )
            store.save_skill(skill)

        skills = store.list_skills()
        assert len(skills) == 3

        categories = store.get_categories()
        assert "测试" in categories

        assert store.delete_skill("skill_0")
        assert not store.exists("skill_0")
        assert len(store.list_skills()) == 2

        print("PASS: test_skill_store_list_and_delete")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_store_toggle():
    from Coder.tools.skill_store import SkillStore, SkillDefinition

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        skill = SkillDefinition(name="toggle_skill", display_name="切换技能", description="", category="测试")
        store.save_skill(skill)

        assert len(store.list_skills(enabled_only=True)) == 1

        store.toggle_skill("toggle_skill", False)
        assert len(store.list_skills(enabled_only=True)) == 0

        store.toggle_skill("toggle_skill", True)
        assert len(store.list_skills(enabled_only=True)) == 1

        print("PASS: test_skill_store_toggle")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_parser_markdown():
    from Coder.tools.skill_parser import SkillParser

    md_content = """# 文件检查技能

## 描述
检查指定路径的文件是否存在

## 分类
文件操作

## 参数
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| path   | str  | 是   | 文件路径 |
| check_content | str | 否 | 检查内容 |

## 代码
```python
import os
def execute(path, check_content=None):
    return os.path.exists(path)
```
"""

    skill = SkillParser.parse_markdown(md_content)
    assert skill is not None
    assert skill.display_name == "文件检查技能"
    assert skill.category == "文件操作"
    assert len(skill.parameters) == 2
    assert skill.parameters[0]["name"] == "path"
    assert skill.parameters[0]["required"] is True
    assert skill.parameters[1]["required"] is False
    assert "os.path.exists" in skill.code

    print("PASS: test_skill_parser_markdown")


def test_skill_parser_json():
    from Coder.tools.skill_parser import SkillParser

    json_data = {
        "name": "json_skill",
        "display_name": "JSON技能",
        "description": "从JSON创建的技能",
        "category": "工具",
        "parameters": [{"name": "input", "type": "str", "required": True, "description": "输入"}],
        "code": "def execute(input):\n    return input.upper()",
    }

    skill = SkillParser.parse_json(json_data)
    assert skill is not None
    assert skill.name == "json_skill"
    assert skill.display_name == "JSON技能"

    print("PASS: test_skill_parser_json")


def test_skill_compiler_validate():
    from Coder.tools.skill_compiler import SkillCompiler

    valid_code = "def execute(x):\n    return x * 2"
    valid, error = SkillCompiler.validate(valid_code)
    assert valid
    assert error == ""

    invalid_code = "def execute(x)\n    return x * 2"
    valid, error = SkillCompiler.validate(invalid_code)
    assert not valid
    assert "SyntaxError" in error or "第" in error

    empty_code = ""
    valid, error = SkillCompiler.validate(empty_code)
    assert not valid

    print("PASS: test_skill_compiler_validate")


def test_skill_compiler_compile():
    from Coder.tools.skill_compiler import SkillCompiler
    from Coder.tools.skill_store import SkillDefinition

    skill = SkillDefinition(
        name="math_skill",
        display_name="数学计算",
        description="执行数学运算",
        category="计算",
        code="def execute(a, b):\n    return a + b",
    )

    func = SkillCompiler.compile(skill)
    assert func is not None
    result = func(a=3, b=4)
    assert result == 7

    print("PASS: test_skill_compiler_compile")


def test_skill_compiler_security():
    from Coder.tools.skill_compiler import SkillCompiler, SkillCompileError

    unsafe_code = "import os\ndef execute():\n    os.system('ls')"
    skill = type("obj", (object,), {
        "name": "unsafe",
        "display_name": "",
        "description": "",
        "category": "",
        "code": unsafe_code,
        "parameters": [],
        "tags": [],
        "version": "1.0.0",
    })()

    try:
        SkillCompiler.compile(skill)
        assert False, "Should have raised SkillCompileError"
    except SkillCompileError as e:
        assert "os" in str(e).lower() or "禁止" in str(e)

    print("PASS: test_skill_compiler_security")


def test_skill_compiler_allowed_libs():
    from Coder.tools.skill_compiler import SkillCompiler
    from Coder.tools.skill_store import SkillDefinition

    skill = SkillDefinition(
        name="json_skill",
        display_name="JSON操作",
        description="使用json库",
        category="工具",
        code="""import json
def execute(data_str):
    return json.loads(data_str)""",
    )

    func = SkillCompiler.compile(skill)
    assert func is not None
    result = func(data_str='{"key": "value"}')
    assert result == {"key": "value"}

    print("PASS: test_skill_compiler_allowed_libs")


def test_skill_executor_basic():
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    from Coder.tools.skill_registry import SkillRegistry, RegisteredSkill
    from Coder.sop.skill_executor import SkillExecutor, ExecutionContext, SkillExecStatus

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        skill = SkillDefinition(
            name="greet_skill",
            display_name="问候技能",
            description="返回问候语",
            category="测试",
            code="def execute(name):\n    return f'Hello, {name}!'",
        )
        store.save_skill(skill)

        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._initialized = False
        registry.initialize()

        executor = SkillExecutor(registry=registry)

        step = {
            "name": "问候步骤",
            "skill": "greet_skill",
            "params": {"name": "World"},
        }
        context = ExecutionContext(sop_name="test_sop", step_index=0)

        result = executor.execute(step, context)
        assert result.status == SkillExecStatus.SUCCESS
        assert result.result == "Hello, World!"
        assert result.retry_count == 0

        print("PASS: test_skill_executor_basic")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_executor_not_found():
    from Coder.tools.skill_registry import SkillRegistry
    from Coder.sop.skill_executor import SkillExecutor, ExecutionContext, SkillExecStatus

    registry = SkillRegistry()
    registry._skills = {}
    registry._initialized = False
    registry.initialize()

    executor = SkillExecutor(registry=registry)

    step = {
        "name": "不存在步骤",
        "skill": "nonexistent_skill",
        "params": {},
    }
    context = ExecutionContext(sop_name="test_sop")

    result = executor.execute(step, context)
    assert result.status == SkillExecStatus.NOT_FOUND

    print("PASS: test_skill_executor_not_found")


def test_skill_executor_retry():
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    from Coder.tools.skill_registry import SkillRegistry
    from Coder.sop.skill_executor import SkillExecutor, ExecutionContext, SkillExecStatus

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        call_count = [0]

        code = """def execute():
    raise ValueError("总是失败")"""

        skill = SkillDefinition(
            name="fail_skill",
            display_name="失败技能",
            description="",
            category="测试",
            code=code,
        )
        store.save_skill(skill)

        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._initialized = False
        registry.initialize()

        executor = SkillExecutor(registry=registry)

        step = {
            "name": "失败步骤",
            "skill": "fail_skill",
            "params": {},
        }
        context = ExecutionContext(
            sop_name="test_sop", max_retries=2
        )

        result = executor.execute(step, context)
        assert result.status == SkillExecStatus.FAILED
        assert result.retry_count == 2

        print("PASS: test_skill_executor_retry")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_executor_fallback():
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    from Coder.tools.skill_registry import SkillRegistry
    from Coder.sop.skill_executor import SkillExecutor, ExecutionContext, SkillExecStatus

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        failing = SkillDefinition(
            name="failing",
            display_name="会失败",
            description="",
            category="测试",
            code="def execute():\n    raise RuntimeError('失败')",
        )
        fallback = SkillDefinition(
            name="fallback",
            display_name="备用",
            description="",
            category="测试",
            code="def execute():\n    return 'fallback_result'",
        )
        store.save_skill(failing)
        store.save_skill(fallback)

        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._initialized = False
        registry.initialize()

        executor = SkillExecutor(registry=registry)

        step = {
            "name": "失败则回退",
            "skill": "failing",
            "params": {},
            "fallback_skill": "fallback",
            "fallback_params": {},
        }
        context = ExecutionContext(
            sop_name="test_sop", max_retries=0
        )

        result = executor.execute(step, context)
        assert result.status == SkillExecStatus.FALLBACK
        assert result.fallback_used
        assert result.fallback_skill == "fallback"
        assert result.result == "fallback_result"

        print("PASS: test_skill_executor_fallback")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_execution_context_variables():
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    from Coder.tools.skill_registry import SkillRegistry
    from Coder.sop.skill_executor import SkillExecutor, ExecutionContext, SkillExecStatus

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        setter = SkillDefinition(
            name="set_var",
            display_name="设置变量",
            description="",
            category="测试",
            code="def execute(value):\n    return value",
        )
        getter = SkillDefinition(
            name="get_var",
            display_name="获取变量",
            description="",
            category="测试",
            code="def execute(prev):\n    return f'got_{prev}'",
        )
        store.save_skill(setter)
        store.save_skill(getter)

        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._initialized = False
        registry.initialize()

        executor = SkillExecutor(registry=registry)

        context = ExecutionContext(sop_name="test_sop")

        step1 = {"name": "步骤1", "skill": "set_var", "params": {"value": "hello"}}
        context.step_index = 0
        r1 = executor.execute(step1, context)
        assert r1.status == SkillExecStatus.SUCCESS
        assert context.variables["步骤1"] == "hello"
        assert context.variables["step_0_result"] == "hello"

        step2 = {"name": "步骤2", "skill": "get_var", "params": {"prev": "${步骤1}"}}
        context.step_index = 1
        r2 = executor.execute(step2, context)
        assert r2.status == SkillExecStatus.SUCCESS
        assert r2.result == "got_hello"

        summary = executor.get_execution_summary(context)
        assert summary["total_steps"] == 2
        assert summary["succeeded"] == 2
        assert summary["failed"] == 0

        print("PASS: test_execution_context_variables")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_registry_search():
    from Coder.tools.skill_registry import SkillRegistry, RegisteredSkill

    registry = SkillRegistry()
    registry._skills = {}

    def dummy_func(**kwargs):
        return kwargs

    registry.register(RegisteredSkill(
        name="file_search",
        display_name="文件搜索",
        description="搜索文件系统中的文件",
        category="文件操作",
        func=dummy_func,
        tags=["文件", "搜索"],
    ))
    registry.register(RegisteredSkill(
        name="web_search",
        display_name="网页搜索",
        description="在互联网上搜索信息",
        category="搜索",
        func=dummy_func,
        tags=["搜索", "网页"],
    ))
    registry.register(RegisteredSkill(
        name="db_query",
        display_name="数据库查询",
        description="查询数据库",
        category="数据库",
        func=dummy_func,
        tags=["数据库", "查询"],
    ))

    results = registry.search("搜索")
    assert len(results) == 2

    results = registry.search("文件")
    assert len(results) == 1

    results = registry.search("数据库")
    assert len(results) == 1

    results = registry.search("不存在的")
    assert len(results) == 0

    print("PASS: test_skill_registry_search")


def test_skill_registry_match_for_step():
    from Coder.tools.skill_registry import SkillRegistry, RegisteredSkill

    registry = SkillRegistry()
    registry._skills = {}

    def dummy(**kwargs):
        return kwargs

    registry.register(RegisteredSkill(
        name="file_write",
        display_name="写入文件",
        description="将内容写入文件",
        category="文件操作",
        func=dummy,
        tags=["文件", "写入"],
    ))

    matched = registry.match_for_step("写入配置", "将配置写入文件")
    assert len(matched) >= 1
    assert matched[0].name == "file_write"

    print("PASS: test_skill_registry_match_for_step")


def test_flow_orchestrator_skill_binding():
    from Coder.sop.flow_orchestrator import FlowOrchestrator

    tmp = _make_temp_dir()
    try:
        controller = FlowOrchestrator(sop_dir=tmp)

        sop_data = {
            "name": "部署流程",
            "description": "标准部署流程",
            "steps": [
                {
                    "index": 0,
                    "name": "检查环境",
                    "description": "检查目标环境",
                    "skill": "file_read",
                    "fallback_skill": "file_list",
                    "on_failure": "stop",
                },
                {
                    "index": 1,
                    "name": "复制文件",
                    "description": "复制部署文件",
                    "skill": "",
                },
                {
                    "index": 2,
                    "name": "验证部署",
                    "description": "验证部署结果",
                    "skill": "file_read",
                    "on_failure": "execute",
                },
            ],
        }

        path = controller.save_sop("部署流程", sop_data)

        loaded = controller.get_sop("部署流程")
        assert loaded is not None
        assert len(loaded["steps"]) == 3

        skill_steps = controller.get_skill_bound_steps("部署流程")
        assert len(skill_steps) == 2

        adaptive = controller.get_adaptive_next_steps(
            "部署流程", 0, {"success": True, "step": "检查环境"}
        )
        assert len(adaptive) == 2

        adaptive_fail = controller.get_adaptive_next_steps(
            "部署流程", 0, {"success": False, "step": "检查环境"}
        )
        assert len(adaptive_fail) >= 1
        assert adaptive_fail[0]["name"] in ("验证部署", "复制文件", "验证部署")

        controller.delete_sop("部署流程")
        assert controller.get_sop("部署流程") is None

        print("PASS: test_flow_orchestrator_skill_binding")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_flow_orchestrator_text_sop_with_skill():
    from Coder.sop.flow_orchestrator import FlowOrchestrator

    tmp = _make_temp_dir()
    try:
        controller = FlowOrchestrator(sop_dir=tmp)

        content = """# 文件处理流程

步骤1 [技能: file_read]: 读取输入文件
步骤2: 处理文件内容
步骤3 [技能: file_write]: 写入处理结果
"""
        path = os.path.join(tmp, "文件处理.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        sop = controller.get_sop("文件处理")
        assert sop is not None
        assert len(sop["steps"]) == 3

        skill_steps = controller.get_skill_bound_steps("文件处理")
        assert len(skill_steps) == 2
        assert skill_steps[0]["skill"] == "file_read"
        assert skill_steps[1]["skill"] == "file_write"

        print("PASS: test_flow_orchestrator_text_sop_with_skill")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_sop_executor_integration():
    from Coder.sop.flow_orchestrator import FlowOrchestrator
    from Coder.sop.executor import SOPExecutor
    from Coder.sop.skill_executor import SkillExecStatus

    tmp = _make_temp_dir()
    try:
        controller = FlowOrchestrator(sop_dir=tmp)

        sop_data = {
            "name": "测试集成",
            "description": "测试SOP-Skill集成",
            "steps": [
                {
                    "index": 0,
                    "name": "测试步骤",
                    "description": "测试",
                    "skill": "file_read",
                },
            ],
        }
        controller.save_sop("测试集成", sop_data)

        executor = SOPExecutor(orchestrator=controller)

        context = executor._get_or_create_context("测试集成")

        assert context.sop_name == "测试集成"

        executor.reset_execution("测试集成")
        assert executor.get_execution_context("测试集成") is None

        print("PASS: test_sop_executor_integration")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_parser_auto():
    from Coder.tools.skill_parser import SkillParser

    content = """# 自动检测技能

## 描述
自动检测文件类型

## 分类
工具

## 参数
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| file_path | str | 是 | 文件路径 |

## 代码
```python
def execute(file_path):
    import re
    if file_path.endswith('.py'):
        return 'python'
    return 'unknown'
```
"""
    skill = SkillParser.parse(content, fmt="auto")
    assert skill is not None
    assert skill.display_name == "自动检测技能"
    assert len(skill.parameters) == 1
    assert "python" in skill.code or "py" in skill.code

    print("PASS: test_skill_parser_auto")


def test_skill_definition_to_dict():
    from Coder.tools.skill_store import SkillDefinition

    skill = SkillDefinition(
        name="test",
        display_name="测试",
        description="描述",
        category="分类",
        parameters=[{"name": "p", "type": "str", "required": True, "description": "参数"}],
        code="def execute(): pass",
        tags=["tag1", "tag2"],
    )

    d = skill.to_dict()
    assert d["name"] == "test"
    assert d["tags"] == ["tag1", "tag2"]

    restored = SkillDefinition.from_dict(d)
    assert restored.name == "test"
    assert restored.tags == ["tag1", "tag2"]

    print("PASS: test_skill_definition_to_dict")


def test_skill_compiler_extract_signature():
    from Coder.tools.skill_compiler import SkillCompiler

    code = "def execute(name: str, count: int = 0):\n    return name * count"
    sig = SkillCompiler.extract_signature(code)
    assert sig is not None
    assert sig["name"] == "execute"
    assert len(sig["parameters"]) == 2
    assert sig["parameters"][0]["name"] == "name"
    assert sig["parameters"][1]["name"] == "count"

    print("PASS: test_skill_compiler_extract_signature")


def test_skill_registry_reload():
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    from Coder.tools.skill_registry import SkillRegistry

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        skill = SkillDefinition(
            name="reload_test",
            display_name="重载测试",
            description="",
            category="测试",
            code="def execute():\n    return 42",
        )
        store.save_skill(skill)

        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._initialized = False

        loaded = registry.load_skill_from_store("reload_test")
        assert loaded is not None
        assert loaded.func() == 42

        loaded2 = registry.reload_skill("reload_test")
        assert loaded2 is not None

        registry.unregister("reload_test")
        assert registry.get("reload_test") is None

        store.delete_skill("reload_test")

        print("PASS: test_skill_registry_reload")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_skill_store_save_and_load,
        test_skill_store_list_and_delete,
        test_skill_store_toggle,
        test_skill_parser_markdown,
        test_skill_parser_json,
        test_skill_parser_auto,
        test_skill_compiler_validate,
        test_skill_compiler_compile,
        test_skill_compiler_security,
        test_skill_compiler_allowed_libs,
        test_skill_compiler_extract_signature,
        test_skill_executor_basic,
        test_skill_executor_not_found,
        test_skill_executor_retry,
        test_skill_executor_fallback,
        test_execution_context_variables,
        test_skill_registry_search,
        test_skill_registry_match_for_step,
        test_skill_registry_reload,
        test_flow_orchestrator_skill_binding,
        test_flow_orchestrator_text_sop_with_skill,
        test_sop_executor_integration,
        test_skill_definition_to_dict,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            import traceback
            print(f"FAIL: {test.__name__}: {e}")
            traceback.print_exc()

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed == 0:
        print("ALL TESTS PASSED!")

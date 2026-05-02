import os
import sys
import shutil
import tempfile
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_temp_dir():
    return tempfile.mkdtemp(prefix="skill_nl_test_")


def test_skill_nl_invoker_detect():
    from Coder.sop.skill_nl_invoker import SkillNLInvoker
    from Coder.sop.intent_classifier import classify_intent, IntentType
    from Coder.tools.skill_store import SkillStore, SkillDefinition

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        skill = SkillDefinition(
            name="simple_text_skill",
            display_name="文本反转技能",
            description="将输入的文本反转返回，支持可选转大写",
            category="文本处理",
            parameters=[
                {"name": "text", "type": "str", "required": True, "description": "要处理的文本"},
                {"name": "uppercase", "type": "str", "required": False, "description": "是否大写"},
            ],
            code="def execute(text, uppercase='否'):\n    result = text[::-1]\n    if uppercase == '是':\n        result = result.upper()\n    return result",
            tags=["测试", "文本", "示例"],
        )
        store.save_skill(skill)

        from Coder.tools.skill_registry import SkillRegistry
        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._meta = {}
        registry._initialized = False
        registry.initialize()

        invoker = SkillNLInvoker(registry=registry)

        found, meta, score = invoker.detect_skill_call("帮我反转文本 hello")
        assert found, f"Should detect skill, got score={score}"
        assert meta.name == "simple_text_skill"
        assert score > 0

        found, meta, score = invoker.detect_skill_call("今天天气怎么样")
        assert not found

        print("PASS: test_skill_nl_invoker_detect")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_nl_invoker_params():
    from Coder.sop.skill_nl_invoker import SkillNLInvoker
    from Coder.tools.skill_store import SkillStore, SkillDefinition, SkillMeta

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        skill = SkillDefinition(
            name="simple_text_skill",
            display_name="文本反转技能",
            description="将输入的文本反转返回",
            category="文本处理",
            parameters=[
                {"name": "text", "type": "str", "required": True, "description": "要处理的文本"},
                {"name": "uppercase", "type": "str", "required": False, "description": "是否大写"},
            ],
            code="",
            tags=["测试"],
        )
        store.save_skill(skill)

        meta = skill.to_meta()

        from Coder.tools.skill_registry import SkillRegistry
        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._meta = {}
        registry._initialized = False
        registry.initialize()

        invoker = SkillNLInvoker(registry=registry)

        params, missing = invoker.extract_params(
            'text=helloWorld uppercase=是', meta
        )
        assert params.get("text") == "helloWorld"
        assert len(missing) == 0

        params, missing = invoker.extract_params(
            'text: world', meta
        )
        assert params.get("text") == "world"

        params, missing = invoker.extract_params(
            "", meta
        )
        assert "text" in missing

        params, missing = invoker.extract_params(
            '"text"="你好世界"', meta
        )
        assert params.get("text") == "你好世界"

        print("PASS: test_skill_nl_invoker_params")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_nl_invoker_confirmation():
    from Coder.sop.skill_nl_invoker import SkillNLInvoker
    from Coder.tools.skill_store import SkillStore, SkillDefinition

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        safe_skill = SkillDefinition(
            name="safe_skill",
            display_name="安全技能",
            description="普通文本处理",
            category="工具",
            tags=["文本"],
        )
        dangerous_skill = SkillDefinition(
            name="danger_skill",
            display_name="文件删除",
            description="删除指定文件",
            category="文件操作",
            tags=["删除", "危险操作"],
        )

        from Coder.tools.skill_registry import SkillRegistry
        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._meta = {}
        registry._initialized = False
        registry.initialize()

        invoker = SkillNLInvoker(registry=registry)

        assert not invoker.needs_confirmation(safe_skill.to_meta())
        assert invoker.needs_confirmation(dangerous_skill.to_meta())

        print("PASS: test_skill_nl_invoker_confirmation")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_nl_invoker_execute():
    from Coder.sop.skill_nl_invoker import SkillNLInvoker, SkillInvocationState, InvokeStage
    from Coder.tools.skill_store import SkillStore, SkillDefinition

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)

        skill = SkillDefinition(
            name="add_skill",
            display_name="加法计算",
            description="执行加法运算",
            category="计算",
            parameters=[
                {"name": "a", "type": "int", "required": True, "description": "第一个数"},
                {"name": "b", "type": "int", "required": True, "description": "第二个数"},
            ],
            code="def execute(a, b):\n    return a + b",
            tags=["计算"],
        )
        store.save_skill(skill)

        from Coder.tools.skill_registry import SkillRegistry
        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._meta = {}
        registry._initialized = False
        registry.initialize()

        registered = registry.get("add_skill")
        assert registered is not None
        result = registered.func(a=3, b=4)
        assert result == 7

        print("PASS: test_skill_nl_invoker_execute")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_intent_classifier_skill_invoke():
    from Coder.sop.intent_classifier import classify_intent, IntentType

    r1 = classify_intent("使用技能帮我反转文本")
    assert r1.intent == IntentType.SKILL_INVOKE, f"Got {r1.intent}"

    r2 = classify_intent("调用技能反转 hello world")
    assert r2.intent == IntentType.SKILL_INVOKE, f"Got {r2.intent}"

    r3 = classify_intent("帮我处理这个文本文件")
    assert r3.intent == IntentType.SKILL_INVOKE, f"Got {r3.intent}"

    r4 = classify_intent("今天天气怎么样")
    assert r4.intent == IntentType.GENERAL_CHAT, f"Got {r4.intent}"

    r5 = classify_intent("执行SOP部署Python应用")
    assert r5.intent == IntentType.EXECUTE_SOP, f"Got {r5.intent}"

    print("PASS: test_intent_classifier_skill_invoke")


def test_chinese_name_explicit_section():
    from Coder.tools.skill_parser import SkillParser
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    import shutil

    md = """# 文本反转技能

## 名称
reverse_text_skill

## 描述
将输入的文本反转返回

## 分类
文本处理

## 参数
| 参数名 | 类型 | 必填 | 说明 |
| ------ | ---- | ---- | ---- |
| text   | str  | 是   | 文本 |

## 代码
```python
def execute(text):
    return text[::-1]
```
"""
    skill_def = SkillParser.parse_markdown(md)
    assert skill_def is not None
    assert skill_def.name == "reverse_text_skill", f"Got {skill_def.name}"
    assert skill_def.display_name == "文本反转技能"

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)
        result = store.save_skill(skill_def)
        assert result, "Save should succeed"
        assert os.path.exists(os.path.join(tmp, "reverse_text_skill.json"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("PASS: test_chinese_name_explicit_section")


def test_chinese_name_with_filename_hint():
    from Coder.tools.skill_parser import SkillParser
    from Coder.tools.skill_store import SkillStore
    import shutil

    md = """# 文本反转技能

## 描述
将输入的文本反转返回

## 分类
文本处理

## 参数
| 参数名 | 类型 | 必填 | 说明 |
| ------ | ---- | ---- | ---- |
| text   | str  | 是   | 文本 |

## 代码
```python
def execute(text):
    return text[::-1]
```
"""
    skill_def = SkillParser.parse_markdown(md, name_hint="simple_text_skill.md")
    assert skill_def is not None
    assert skill_def.name == "simple_text_skill", f"Got {skill_def.name}"
    assert skill_def.display_name == "文本反转技能"

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)
        result = store.save_skill(skill_def)
        assert result
        assert os.path.exists(os.path.join(tmp, "simple_text_skill.json"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("PASS: test_chinese_name_with_filename_hint")


def test_chinese_name_pure_no_hint():
    from Coder.tools.skill_parser import SkillParser
    from Coder.tools.skill_store import SkillStore
    import shutil

    md = """# 纯中文技能测试

## 描述
测试纯中文标题

## 参数
| 参数名 | 类型 | 必填 | 说明 |
| ------ | ---- | ---- | ---- |
| input  | str  | 是   | 输入 |

## 代码
```python
def execute(input):
    return input
```
"""
    skill_def = SkillParser.parse_markdown(md)
    assert skill_def is not None
    assert skill_def.name.startswith("skill_"), f"Got {skill_def.name}"
    assert skill_def.display_name == "纯中文技能测试"

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)
        result = store.save_skill(skill_def)
        assert result
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("PASS: test_chinese_name_pure_no_hint")


def test_mixed_cn_en_name():
    from Coder.tools.skill_parser import SkillParser
    from Coder.tools.skill_store import SkillStore
    import shutil

    md = """# My测试Skill 123

## 描述
中英混合标题

## 参数
| 参数名 | 类型 | 必填 | 说明 |
| ------ | ---- | ---- | ---- |
| input  | str  | 是   | 输入 |

## 代码
```python
def execute(input):
    return input
```
"""
    skill_def = SkillParser.parse_markdown(md)
    assert skill_def is not None
    assert skill_def.name == "my_skill_123", f"Got {skill_def.name}"
    assert skill_def.display_name == "My测试Skill 123"

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)
        result = store.save_skill(skill_def)
        assert result
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("PASS: test_mixed_cn_en_name")


def test_chinese_name_end_to_end():
    from Coder.tools.skill_parser import SkillParser
    from Coder.tools.skill_store import SkillStore
    from Coder.tools.skill_registry import SkillRegistry
    import shutil

    md = """# 文本反转技能

## 名称
reverse_text_skill

## 描述
将输入的文本反转返回，支持可选转大写

## 分类
文本处理

## 参数
| 参数名    | 类型 | 必填 | 说明                   |
| --------- | ---- | ---- | ---------------------- |
| text      | str  | 是   | 要处理的文本           |
| uppercase | str  | 否   | 是否大写，填"是"或"否" |

## 代码
```python
def execute(text, uppercase="否"):
    result = text[::-1]
    if uppercase == "是":
        result = result.upper()
    return result
```
"""
    skill_def = SkillParser.parse_markdown(md)
    assert skill_def is not None
    assert skill_def.name == "reverse_text_skill"
    assert skill_def.display_name == "文本反转技能"

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)
        result = store.save_skill(skill_def)
        assert result

        from Coder.tools.skill_registry import SkillRegistry
        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._meta = {}
        registry._initialized = False
        registry.initialize()

        registered = registry.get("reverse_text_skill")
        assert registered is not None
        result_val = registered.func(text="hello")
        assert result_val == "olleh"

        result_val2 = registered.func(text="hello", uppercase="是")
        assert result_val2 == "OLLEH"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("PASS: test_chinese_name_end_to_end")


def test_skill_detect_with_skill_keyword():
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    from Coder.tools.skill_registry import SkillRegistry
    from Coder.sop.skill_nl_invoker import SkillNLInvoker

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)
        skill = SkillDefinition(
            name="reverse_text_skill",
            display_name="文本反转技能",
            description="将输入的文本反转返回，支持可选转大写",
            category="文本处理",
            parameters=[
                {"name": "text", "type": "str", "required": True, "description": "要处理的文本"},
                {"name": "uppercase", "type": "str", "required": False, "description": "是否大写"},
            ],
            code='def execute(text, uppercase="否"):\n    result = text[::-1]\n    if uppercase == "是":\n        result = result.upper()\n    return result',
            tags=["测试", "文本", "示例"],
        )
        store.save_skill(skill)

        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._meta = {}
        registry._initialized = False
        registry.initialize()

        invoker = SkillNLInvoker(registry=registry)

        test_input = '我要求你调用skill完成对"湖南科技大学"的反转'
        found, meta, score = invoker.detect_skill_call(test_input)
        assert found, f"Should detect skill, got score={score}"
        assert meta.name == "reverse_text_skill"

        params, missing = invoker.extract_params(test_input, meta)
        assert "text" in params, f"Should extract text param, got params={params}"
        assert "湖南科技大学" == str(params["text"]), f"Got text={params.get('text')}"

        print("PASS: test_skill_detect_with_skill_keyword")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_detect_chinese_reverse_keyword():
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    from Coder.tools.skill_registry import SkillRegistry
    from Coder.sop.skill_nl_invoker import SkillNLInvoker

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)
        skill = SkillDefinition(
            name="reverse_text_skill",
            display_name="文本反转技能",
            description="将输入的文本反转返回",
            category="文本处理",
            parameters=[
                {"name": "text", "type": "str", "required": True, "description": "要处理的文本"},
            ],
            code="def execute(text):\n    return text[::-1]",
            tags=["文本"],
        )
        store.save_skill(skill)

        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._meta = {}
        registry._initialized = False
        registry.initialize()

        invoker = SkillNLInvoker(registry=registry)

        found, meta, score = invoker.detect_skill_call("反转湖南科技大学")
        assert found, f"Should detect via '反转' + Chinese chars, got score={score}"

        found2, meta2, score2 = invoker.detect_skill_call("用技能反转我的名字")
        assert found2, f"Should detect via '用技能' + '反转', got score={score2}"

        found3, meta3, score3 = invoker.detect_skill_call("帮我处理这段文本")
        assert found3, f"Should detect via '处理' + '文本', got score={score3}"

        print("PASS: test_skill_detect_chinese_reverse_keyword")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_detect_fallback_list_skills():
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    from Coder.tools.skill_registry import SkillRegistry
    from Coder.sop.skill_nl_invoker import SkillNLInvoker
    from Coder.sop.intent_classifier import classify_intent, IntentType

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)
        skill = SkillDefinition(
            name="add_math",
            display_name="加法计算器",
            description="计算两个数的和",
            category="数学",
            parameters=[
                {"name": "a", "type": "int", "required": True, "description": "第一个数"},
            ],
            code="def execute(a, b=0):\n    return a + b",
            tags=["数学"],
        )
        store.save_skill(skill)

        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._meta = {}
        registry._initialized = False
        registry.initialize()

        invoker = SkillNLInvoker(registry=registry)

        intent = classify_intent("调用skill做点事情")
        assert intent.intent == IntentType.SKILL_INVOKE

        found, meta, score = invoker.detect_skill_call("调用skill做点事情")
        assert not found

        print("PASS: test_skill_detect_fallback_list_skills")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_detect_full_workflow():
    from Coder.tools.skill_store import SkillStore, SkillDefinition
    from Coder.tools.skill_registry import SkillRegistry
    from Coder.sop.skill_nl_invoker import SkillNLInvoker

    tmp = _make_temp_dir()
    try:
        store = SkillStore(base_path=tmp)
        skill = SkillDefinition(
            name="reverse_text_skill",
            display_name="文本反转技能",
            description="将输入的文本反转返回，支持可选转大写",
            category="文本处理",
            parameters=[
                {"name": "text", "type": "str", "required": True, "description": "要处理的文本"},
                {"name": "uppercase", "type": "str", "required": False, "description": "是否大写"},
            ],
            code='def execute(text, uppercase="否"):\n    result = text[::-1]\n    if uppercase == "是":\n        result = result.upper()\n    return result',
            tags=["测试", "文本", "示例"],
        )
        store.save_skill(skill)

        registry = SkillRegistry()
        registry._store = store
        registry._skills = {}
        registry._meta = {}
        registry._initialized = False
        registry.initialize()

        invoker = SkillNLInvoker(registry=registry)

        found, meta, score = invoker.detect_skill_call(
            '我要求你调用skill完成对"湖南科技大学"的反转'
        )
        assert found

        registered = registry.get(meta.name)
        assert registered is not None

        params, missing = invoker.extract_params(
            '我要求你调用skill完成对"湖南科技大学"的反转', meta
        )
        assert "text" in params
        assert "湖南科技大学" == params["text"]

        result = registered.func(**params)
        assert result == "学大技科南湖"

        params2, missing2 = invoker.extract_params(
            'text="你好世界" uppercase=是', meta
        )
        result2 = registered.func(**params2)
        assert result2 == "界世好你".upper()

        found3, meta3, score3 = invoker.detect_skill_call("今天天气怎么样")
        assert not found3

        print("PASS: test_skill_detect_full_workflow")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)



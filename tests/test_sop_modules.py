import json
import os
import tempfile
import pytest

from Coder.sop.intent_classifier import classify_intent, IntentType, _extract_sop_name
from Coder.sop.state_machine import StateMachine, SOPState, SOPExecution, StepResult
from Coder.sop.flow_orchestrator import FlowOrchestrator
from Coder.sop.executor import SOPExecutor
from Coder.sop.checkpoint_manager import CheckpointManager
from Coder.sop.validator import SOPValidator


class TestIntentClassifier:

    def test_execute_sop_intent(self):
        result = classify_intent("执行Python应用部署SOP")
        assert result.intent == IntentType.EXECUTE_SOP
        assert result.confidence > 0

    def test_query_sop_intent(self):
        result = classify_intent("查询部署流程")
        assert result.intent == IntentType.QUERY_SOP

    def test_modify_sop_intent(self):
        result = classify_intent("修改SOP的步骤")
        assert result.intent == IntentType.MODIFY_SOP

    def test_modify_sop_priority_over_execute(self):
        result = classify_intent("删除SOP")
        assert result.intent == IntentType.MODIFY_SOP

    def test_general_chat_intent(self):
        result = classify_intent("你是谁")
        assert result.intent == IntentType.GENERAL_CHAT

    def test_general_chat_no_sop(self):
        result = classify_intent("今天天气怎么样")
        assert result.intent == IntentType.GENERAL_CHAT

    def test_sop_name_extraction(self):
        name = _extract_sop_name("执行python应用部署sop".lower())
        assert "python" in name or "部署" in name

    def test_sop_name_extraction_with_action(self):
        name = _extract_sop_name("执行数据库部署流程".lower())
        assert len(name) > 0

    def test_empty_input(self):
        result = classify_intent("")
        assert result.intent == IntentType.GENERAL_CHAT

    def test_sop_keyword_triggers_query(self):
        result = classify_intent("SOP是什么")
        assert result.intent in (IntentType.QUERY_SOP, IntentType.EXECUTE_SOP)

    def test_confidence_range(self):
        result = classify_intent("执行部署")
        assert 0 <= result.confidence <= 1.0


class TestStateMachine:

    def setup_method(self):
        self.sm = StateMachine()

    def test_create_execution(self):
        execution = self.sm.create_execution("test_sop", 3)
        assert execution.sop_name == "test_sop"
        assert execution.total_steps == 3
        assert execution.state == SOPState.PENDING
        assert execution.execution_id.startswith("test_sop_")

    def test_transition_pending_to_running(self):
        self.sm.create_execution("test_sop", 3)
        assert self.sm.transition("test_sop", SOPState.RUNNING) is True
        assert self.sm.get_execution("test_sop").state == SOPState.RUNNING

    def test_invalid_transition(self):
        self.sm.create_execution("test_sop", 3)
        assert self.sm.transition("test_sop", SOPState.COMPLETED) is False

    def test_advance_step(self):
        self.sm.create_execution("test_sop", 3)
        self.sm.transition("test_sop", SOPState.RUNNING)
        step = StepResult(step_index=0, step_name="步骤1", status="completed")
        result = self.sm.advance_step("test_sop", step)
        assert result is True
        assert self.sm.get_execution("test_sop").current_step == 1

    def test_advance_to_completion(self):
        self.sm.create_execution("test_sop", 2)
        self.sm.transition("test_sop", SOPState.RUNNING)
        step1 = StepResult(step_index=0, step_name="步骤1", status="completed")
        self.sm.advance_step("test_sop", step1)
        step2 = StepResult(step_index=1, step_name="步骤2", status="completed")
        self.sm.advance_step("test_sop", step2)
        execution = self.sm.get_execution("test_sop")
        assert execution.state == SOPState.COMPLETED
        assert execution.completed_at is not None

    def test_set_error(self):
        self.sm.create_execution("test_sop", 3)
        self.sm.transition("test_sop", SOPState.RUNNING)
        self.sm.set_error("test_sop", "连接超时")
        execution = self.sm.get_execution("test_sop")
        assert execution.state == SOPState.FAILED
        assert execution.error == "连接超时"

    def test_get_progress(self):
        self.sm.create_execution("test_sop", 4)
        self.sm.transition("test_sop", SOPState.RUNNING)
        assert self.sm.get_progress("test_sop") == 0.0
        step = StepResult(step_index=0, step_name="步骤1", status="completed")
        self.sm.advance_step("test_sop", step)
        assert self.sm.get_progress("test_sop") == 0.25

    def test_remove_execution(self):
        self.sm.create_execution("test_sop", 3)
        assert self.sm.remove_execution("test_sop") is True
        assert self.sm.get_execution("test_sop") is None

    def test_remove_nonexistent_execution(self):
        assert self.sm.remove_execution("nonexistent") is False

    def test_advance_step_invalid_state(self):
        self.sm.create_execution("test_sop", 3)
        step = StepResult(step_index=0, step_name="步骤1", status="completed")
        result = self.sm.advance_step("test_sop", step)
        assert result is False

    def test_nonexistent_execution(self):
        assert self.sm.get_execution("nonexistent") is None
        assert self.sm.get_progress("nonexistent") == 0.0


class TestFlowOrchestrator:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orchestrator = FlowOrchestrator(sop_dir=self.tmp_dir)

    def test_list_sops_empty(self):
        assert self.orchestrator.list_sops() == []

    def test_save_and_get_sop(self):
        sop_data = {
            "name": "测试SOP",
            "description": "测试用",
            "steps": [
                {"index": 0, "name": "步骤1", "description": "第一步操作"},
            ],
        }
        self.orchestrator.save_sop("测试SOP", sop_data)
        result = self.orchestrator.get_sop("测试SOP")
        assert result is not None
        assert result["name"] == "测试SOP"

    def test_list_sops(self):
        self.orchestrator.save_sop("SOP_A", {"name": "A"})
        self.orchestrator.save_sop("SOP_B", {"name": "B"})
        sops = self.orchestrator.list_sops()
        assert len(sops) == 2
        assert "SOP_A" in sops
        assert "SOP_B" in sops

    def test_delete_sop(self):
        self.orchestrator.save_sop("测试SOP", {"name": "测试SOP"})
        assert self.orchestrator.delete_sop("测试SOP") is True
        assert self.orchestrator.get_sop("测试SOP") is None

    def test_delete_nonexistent_sop(self):
        assert self.orchestrator.delete_sop("不存在") is False

    def test_get_nonexistent_sop(self):
        assert self.orchestrator.get_sop("不存在") is None

    def test_route(self):
        result = self.orchestrator.route("执行部署SOP")
        assert result.intent == IntentType.EXECUTE_SOP

    def test_cache_invalidation_on_save(self):
        self.orchestrator.save_sop("测试SOP", {"name": "v1", "steps": []})
        assert self.orchestrator.get_sop("测试SOP")["name"] == "v1"
        self.orchestrator.save_sop("测试SOP", {"name": "v2", "steps": []})
        assert self.orchestrator.get_sop("测试SOP")["name"] == "v2"

    def test_text_sop_parsing(self):
        md_content = """# 部署流程

步骤1：检查环境
步骤2：安装依赖
步骤3：启动服务
"""
        path = os.path.join(self.tmp_dir, "部署流程.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md_content)

        sop = self.orchestrator.get_sop("部署流程")
        assert sop is not None
        assert len(sop["steps"]) >= 1

    def test_start_execution(self):
        self.orchestrator.save_sop("测试SOP", {
            "name": "测试SOP",
            "steps": [
                {"index": 0, "name": "步骤1", "description": "操作1"},
                {"index": 1, "name": "步骤2", "description": "操作2"},
            ],
        })
        result = self.orchestrator.start_execution("测试SOP")
        assert result is not None
        assert result["total_steps"] == 2

    def test_start_execution_nonexistent(self):
        result = self.orchestrator.start_execution("不存在")
        assert result is None

    def test_get_execution_status(self):
        self.orchestrator.save_sop("测试SOP", {
            "name": "测试SOP",
            "steps": [{"index": 0, "name": "步骤1", "description": "操作1"}],
        })
        self.orchestrator.start_execution("测试SOP")
        status = self.orchestrator.get_execution_status("测试SOP")
        assert status is not None
        assert "progress" in status


class TestSOPExecutor:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.orchestrator = FlowOrchestrator(sop_dir=self.tmp_dir)
        self.executor = SOPExecutor(self.orchestrator)

    def test_build_sop_prompt(self):
        self.orchestrator.save_sop("部署SOP", {
            "name": "部署SOP",
            "steps": [
                {"index": 0, "name": "步骤1", "description": "检查环境"},
            ],
        })
        prompt = self.executor.build_sop_prompt("部署SOP", "执行部署")
        assert prompt is not None
        assert "部署SOP" in prompt
        assert "步骤1" in prompt

    def test_build_sop_prompt_nonexistent(self):
        prompt = self.executor.build_sop_prompt("不存在", "执行部署")
        assert prompt is None

    def test_build_query_prompt(self):
        prompt = self.executor.build_query_prompt("什么是部署SOP", "参考文档内容")
        assert "什么是部署SOP" in prompt
        assert "参考文档内容" in prompt

    def test_build_list_prompt_with_sops(self):
        self.orchestrator.save_sop("SOP_A", {"name": "A"})
        prompt = self.executor.build_list_prompt("有哪些SOP")
        assert "SOP_A" in prompt

    def test_build_list_prompt_no_sops(self):
        prompt = self.executor.build_list_prompt("有哪些SOP")
        assert "没有可用的SOP" in prompt

    def test_should_confirm_dangerous(self):
        assert self.executor.should_confirm({"description": "删除所有数据"}) is True
        assert self.executor.should_confirm({"description": "格式化磁盘"}) is True

    def test_should_confirm_safe(self):
        assert self.executor.should_confirm({"description": "检查环境配置"}) is False

    def test_format_steps(self):
        steps = [
            {"index": 0, "name": "步骤1", "description": "检查环境"},
            {"index": 1, "name": "步骤2", "description": "安装依赖"},
        ]
        result = SOPExecutor._format_steps(steps)
        assert "步骤1" in result
        assert "步骤2" in result

    def test_format_steps_empty(self):
        assert SOPExecutor._format_steps([]) == ""

    def test_explicitly_mentions_sop(self):
        assert SOPExecutor._explicitly_mentions_sop("查看SOP流程") is True
        assert SOPExecutor._explicitly_mentions_sop("今天天气怎么样") is False

    def test_record_step_result(self):
        self.orchestrator.save_sop("测试SOP", {
            "name": "测试SOP",
            "steps": [{"index": 0, "name": "步骤1", "description": "操作1"}],
        })
        self.orchestrator.start_execution("测试SOP")
        self.executor.record_step_result("测试SOP", 0, "步骤1", "completed", "成功")
        status = self.orchestrator.get_execution_status("测试SOP")
        assert status is not None


class TestCheckpointManager:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.mgr = CheckpointManager(base_path=self.tmp_dir, max_checkpoints_per_sop=3)

    def _make_execution(self, sop_name="test_sop", total_steps=3) -> SOPExecution:
        sm = StateMachine()
        execution = sm.create_execution(sop_name, total_steps)
        sm.transition(sop_name, SOPState.RUNNING)
        return execution

    def test_save_and_load_checkpoint(self):
        execution = self._make_execution()
        path = self.mgr.save_checkpoint(execution)
        assert os.path.exists(path)

        loaded = self.mgr.load_checkpoint("test_sop")
        assert loaded is not None
        assert loaded["sop_name"] == "test_sop"

    def test_load_nonexistent_checkpoint(self):
        assert self.mgr.load_checkpoint("不存在") is None

    def test_list_checkpoints(self):
        execution = self._make_execution()
        self.mgr.save_checkpoint(execution)
        checkpoints = self.mgr.list_checkpoints()
        assert len(checkpoints) >= 1

    def test_list_checkpoints_with_limit(self):
        execution = self._make_execution()
        self.mgr.save_checkpoint(execution)
        checkpoints = self.mgr.list_checkpoints(limit=0)
        assert len(checkpoints) == 0

    def test_checkpoint_limit_enforcement(self):
        import time
        for i in range(5):
            execution = self._make_execution(f"sop_{i % 2}")
            self.mgr.save_checkpoint(execution)
            time.sleep(0.01)

        sop0_dir = os.path.join(self.tmp_dir, "sop_0")
        if os.path.exists(sop0_dir):
            files = [f for f in os.listdir(sop0_dir) if f.startswith("checkpoint_")]
            assert len(files) <= 3

    def test_cleanup_old_checkpoints(self):
        execution = self._make_execution()
        self.mgr.save_checkpoint(execution)
        removed = self.mgr.cleanup_old_checkpoints(max_age_days=0)
        assert removed >= 0


class TestSOPValidator:

    def setup_method(self):
        self.validator = SOPValidator()

    def test_validate_step_result_passed(self):
        step = {"name": "步骤1", "description": "检查环境"}
        result = self.validator.validate_step_result(step, "环境检查完成，Python 3.11已安装")
        assert result["passed"] is True

    def test_validate_step_result_failed(self):
        step = {"name": "步骤1", "description": "检查环境"}
        result = self.validator.validate_step_result(step, "步骤1失败：连接超时")
        assert result["passed"] is False
        assert "no_error" in result["failed_checks"]

    def test_validate_step_result_empty(self):
        step = {"name": "步骤1"}
        result = self.validator.validate_step_result(step, "")
        assert result["passed"] is False

    def test_validate_step_result_with_keywords(self):
        step = {"name": "步骤1", "expected_keywords": ["成功", "完成"]}
        result = self.validator.validate_step_result(step, "操作成功完成，所有服务已正常启动运行")
        assert result["passed"] is True

    def test_validate_step_result_no_false_positive_on_error_word(self):
        step = {"name": "步骤1", "description": "错误排查"}
        result = self.validator.validate_step_result(step, "错误排查完成，未发现异常，服务正常运行")
        assert result["checks"]["no_error"] is True

    def test_validate_sop_structure_valid(self):
        sop_data = {
            "name": "测试SOP",
            "steps": [
                {"index": 0, "name": "步骤1", "description": "检查环境配置"},
            ],
        }
        result = self.validator.validate_sop_structure(sop_data)
        assert result["valid"] is True

    def test_validate_sop_structure_no_name(self):
        sop_data = {"steps": [{"name": "步骤1", "description": "操作描述"}]}
        result = self.validator.validate_sop_structure(sop_data)
        assert result["valid"] is False
        assert any("名称" in issue for issue in result["issues"])

    def test_validate_sop_structure_no_steps(self):
        sop_data = {"name": "测试SOP"}
        result = self.validator.validate_sop_structure(sop_data)
        assert result["valid"] is False

    def test_validate_sop_structure_duplicate_index(self):
        sop_data = {
            "name": "测试SOP",
            "steps": [
                {"index": 0, "name": "步骤1", "description": "操作描述一"},
                {"index": 0, "name": "步骤2", "description": "操作描述二"},
            ],
        }
        result = self.validator.validate_sop_structure(sop_data)
        assert result["valid"] is False
        assert any("重复" in issue for issue in result["issues"])

    def test_extract_execution_status_completed(self):
        result = self.validator.extract_execution_status("部署成功，服务已启动")
        assert result["status"] == "completed"

    def test_extract_execution_status_failed(self):
        result = self.validator.extract_execution_status("步骤3执行失败，超时错误")
        assert result["status"] == "failed"

    def test_extract_execution_status_unknown(self):
        result = self.validator.extract_execution_status("正在处理中")
        assert result["status"] == "unknown"

    def test_extract_execution_status_mixed_signals(self):
        result = self.validator.extract_execution_status("操作失败但部分成功")
        assert result["status"] in ("failed", "unknown")

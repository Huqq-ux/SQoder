import re
from typing import Optional


_ERROR_INDICATORS = [
    re.compile(r"(?:执行|操作|运行).*(?:失败|出错|异常)"),
    re.compile(r"(?:error|failed|exception)", re.IGNORECASE),
    re.compile(r"超时"),
    re.compile(r"权限不足|拒绝访问"),
]

_SUCCESS_INDICATORS = [
    re.compile(r"(?:成功|完成|已安装|已创建|已启动|已配置|正常运行)"),
    re.compile(r"(?:completed|success|done|ok)", re.IGNORECASE),
]

_FAILURE_STRONG_INDICATORS = [
    re.compile(r"步骤.*失败"),
    re.compile(r"执行失败"),
    re.compile(r"操作失败"),
    re.compile(r"step.*failed", re.IGNORECASE),
]


class SOPValidator:
    def validate_step_result(self, step: dict, result_text: str) -> dict:
        checks = {
            "has_output": len(result_text.strip()) > 0,
            "has_content": len(result_text.strip()) > 10,
        }

        has_strong_failure = any(
            p.search(result_text) for p in _FAILURE_STRONG_INDICATORS
        )
        has_error_indicator = any(
            p.search(result_text) for p in _ERROR_INDICATORS
        )
        checks["no_error"] = not has_strong_failure and not has_error_indicator

        expected_keywords = step.get("expected_keywords", [])
        if expected_keywords:
            keyword_matches = sum(
                1 for kw in expected_keywords if kw in result_text
            )
            checks["keyword_coverage"] = keyword_matches / len(expected_keywords) >= 0.5

        passed = all(checks.values())
        failed_checks = [k for k, v in checks.items() if not v]

        return {
            "passed": passed,
            "checks": checks,
            "failed_checks": failed_checks,
            "reason": f"未通过检查: {', '.join(failed_checks)}" if failed_checks else "验证通过",
        }

    def validate_sop_structure(self, sop_data: dict) -> dict:
        issues = []

        if not sop_data.get("name"):
            issues.append("缺少SOP名称")

        steps = sop_data.get("steps", [])
        if not steps:
            issues.append("SOP没有定义任何步骤")
        else:
            seen_indices = set()
            for i, step in enumerate(steps):
                if not step.get("name") and not step.get("description"):
                    issues.append(f"步骤{i + 1}缺少名称和描述")

                desc = step.get("description", "")
                if len(desc) < 5:
                    issues.append(f"步骤{i + 1}描述过短")

                step_idx = step.get("index")
                if step_idx is not None:
                    if step_idx in seen_indices:
                        issues.append(f"步骤索引 {step_idx} 重复")
                    seen_indices.add(step_idx)

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }

    def extract_execution_status(self, result_text: str) -> dict:
        has_failure = any(p.search(result_text) for p in _FAILURE_STRONG_INDICATORS)
        if has_failure:
            return {"status": "failed", "confidence": 0.9}

        has_error = any(p.search(result_text) for p in _ERROR_INDICATORS)
        has_success = any(p.search(result_text) for p in _SUCCESS_INDICATORS)

        if has_error and not has_success:
            return {"status": "failed", "confidence": 0.7}
        elif has_success and not has_error:
            return {"status": "completed", "confidence": 0.8}
        elif has_error and has_success:
            return {"status": "unknown", "confidence": 0.4}
        else:
            return {"status": "unknown", "confidence": 0.3}

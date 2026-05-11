import os
import json
import logging
from typing import Optional
from datetime import datetime

from Coder.sop.state_machine import SOPExecution

logger = logging.getLogger(__name__)


class CheckpointManager:
    def __init__(self, base_path: Optional[str] = None, max_checkpoints_per_sop: int = 10):
        if base_path is None:
            base_path = os.path.join(
                os.path.dirname(__file__), "..", "checkpoints", "sop"
            )
        self.base_path = base_path
        self.max_checkpoints_per_sop = max_checkpoints_per_sop
        os.makedirs(self.base_path, exist_ok=True)

    def save_checkpoint(self, execution: SOPExecution) -> str:
        sop_dir = os.path.join(self.base_path, execution.sop_name)
        os.makedirs(sop_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"checkpoint_{timestamp}.json"
        path = os.path.join(sop_dir, filename)

        data = self._serialize_execution(execution)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self._enforce_checkpoint_limit(sop_dir)

        logger.info(f"保存SOP检查点: {execution.sop_name} @ 步骤 {execution.current_step}")
        return path

    def load_checkpoint(self, sop_name: str) -> Optional[dict]:
        sop_dir = os.path.join(self.base_path, sop_name)
        if not os.path.exists(sop_dir):
            return None

        checkpoints = sorted(
            [f for f in os.listdir(sop_dir) if f.startswith("checkpoint_")],
            reverse=True,
        )

        if not checkpoints:
            return None

        path = os.path.join(sop_dir, checkpoints[0])
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"加载检查点失败 {path}: {e}")
            return None

    def list_checkpoints(self, sop_name: Optional[str] = None, limit: int = 50) -> list[dict]:
        results = []

        if limit <= 0:
            return results

        if sop_name:
            dirs = [os.path.join(self.base_path, sop_name)]
        else:
            if not os.path.exists(self.base_path):
                return []
            dirs = [
                os.path.join(self.base_path, d)
                for d in os.listdir(self.base_path)
                if os.path.isdir(os.path.join(self.base_path, d))
            ]

        for sop_dir in dirs:
            if not os.path.exists(sop_dir):
                continue
            name = os.path.basename(sop_dir)
            for f in sorted(os.listdir(sop_dir), reverse=True):
                if f.startswith("checkpoint_"):
                    path = os.path.join(sop_dir, f)
                    try:
                        with open(path, "r", encoding="utf-8") as fh:
                            data = json.load(fh)
                        results.append({
                            "sop_name": name,
                            "filename": f,
                            "state": data.get("state"),
                            "current_step": data.get("current_step"),
                            "total_steps": data.get("total_steps"),
                            "saved_at": data.get("saved_at"),
                        })
                    except (json.JSONDecodeError, OSError) as e:
                        logger.error(f"加载检查点失败 {path}: {e}")

                    if len(results) >= limit:
                        return results

        return results

    def cleanup_old_checkpoints(self, max_age_days: int = 30) -> int:
        removed = 0
        cutoff = datetime.now().timestamp() - (max_age_days * 86400)

        if not os.path.exists(self.base_path):
            return 0

        for sop_name in os.listdir(self.base_path):
            sop_dir = os.path.join(self.base_path, sop_name)
            if not os.path.isdir(sop_dir):
                continue

            for f in os.listdir(sop_dir):
                if not f.startswith("checkpoint_"):
                    continue
                path = os.path.join(sop_dir, f)
                try:
                    if os.path.getmtime(path) < cutoff:
                        os.remove(path)
                        removed += 1
                except OSError:
                    pass

        if removed > 0:
            logger.info(f"清理了 {removed} 个过期检查点（超过 {max_age_days} 天）")
        return removed

    @staticmethod
    def _serialize_execution(execution: SOPExecution) -> dict:
        return {
            "sop_name": execution.sop_name,
            "state": execution.state.value,
            "current_step": execution.current_step,
            "total_steps": execution.total_steps,
            "step_results": [
                {
                    "step_index": r.step_index,
                    "step_name": r.step_name,
                    "status": r.status,
                    "result": r.result,
                    "error": r.error,
                    "tool_calls": r.tool_calls,
                    "timestamp": r.timestamp,
                }
                for r in execution.step_results
            ],
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "error": execution.error,
            "saved_at": datetime.now().isoformat(),
        }

    def _enforce_checkpoint_limit(self, sop_dir: str):
        try:
            files = sorted(
                [f for f in os.listdir(sop_dir) if f.startswith("checkpoint_")],
            )
            while len(files) > self.max_checkpoints_per_sop:
                oldest = files.pop(0)
                os.remove(os.path.join(sop_dir, oldest))
        except OSError:
            pass

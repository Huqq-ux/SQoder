import os
import json
import logging
import base64
from pathlib import Path
from typing import Any, Iterator, Sequence

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.base import get_checkpoint_id
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

_serde = JsonPlusSerializer()
_logger = logging.getLogger(__name__)


def _deserialize_checkpoint(data: str):
    if ":" in data:
        tag, payload = data.split(":", 1)
        decoded = base64.b64decode(payload)
        return _serde.loads_typed((tag, decoded))
    import pickle
    try:
        decoded = base64.b64decode(data)
        return pickle.loads(decoded)
    except Exception as e:
        _logger.warning(f"旧格式 checkpoint 反序列化失败: {e}，返回空数据")
        return {}


def _serialize_checkpoint(data) -> str:
    tag, payload = _serde.dumps_typed(data)
    return tag + ":" + base64.b64encode(payload).decode("utf-8")


class FileSaver(BaseCheckpointSaver[str]):
    def __init__(self, base_path: str | None = None):
        super().__init__()
        if base_path is None:
            base_path = os.path.join(os.path.dirname(__file__), "..", "checkpoints")
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _get_checkpoint_path(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> str:
        ns_dir = checkpoint_ns.replace("|", "_ns_") if checkpoint_ns else "_root"
        dir_path = os.path.join(self.base_path, thread_id, ns_dir)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, checkpoint_id + ".json")

    def _get_writes_path(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str, task_id: str) -> str:
        ns_dir = checkpoint_ns.replace("|", "_ns_") if checkpoint_ns else "_root"
        writes_dir = os.path.join(self.base_path, thread_id, ns_dir, "writes")
        os.makedirs(writes_dir, exist_ok=True)
        return os.path.join(writes_dir, f"{checkpoint_id}_{task_id}.json")

    def _load_pending_writes(self, thread_id: str, checkpoint_ns: str, checkpoint_id: str) -> list[tuple[str, str, Any]]:
        ns_dir = checkpoint_ns.replace("|", "_ns_") if checkpoint_ns else "_root"
        writes_dir = os.path.join(self.base_path, thread_id, ns_dir, "writes")
        if not os.path.exists(writes_dir):
            return []
        pending_writes = []
        for write_file in Path(writes_dir).glob(f"{checkpoint_id}_*.json"):
            with open(write_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            writes = _deserialize_checkpoint(data["writes"])
            task_id = data["task_id"]
            for channel, value in writes:
                pending_writes.append((task_id, channel, value))
        return pending_writes

    def _find_latest_checkpoint_id(self, thread_id: str, checkpoint_ns: str) -> str | None:
        ns_dir = checkpoint_ns.replace("|", "_ns_") if checkpoint_ns else "_root"
        dir_path = os.path.join(self.base_path, thread_id, ns_dir)
        if not os.path.exists(dir_path):
            return None
        checkpoint_files = list(Path(dir_path).glob("*.json"))
        if not checkpoint_files:
            return None
        checkpoint_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return checkpoint_files[0].stem

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        checkpoint_id = get_checkpoint_id(config)
        if not checkpoint_id:
            checkpoint_id = self._find_latest_checkpoint_id(thread_id, checkpoint_ns)
        if not checkpoint_id:
            return None

        checkpoint_file_path = self._get_checkpoint_path(thread_id, checkpoint_ns, checkpoint_id)
        if not os.path.exists(checkpoint_file_path):
            return None

        with open(checkpoint_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        checkpoint = _deserialize_checkpoint(data["checkpoint"])
        metadata = _deserialize_checkpoint(data["metadata"])
        parent_checkpoint_id = data.get("parent_checkpoint_id")
        pending_writes = self._load_pending_writes(thread_id, checkpoint_ns, checkpoint_id)

        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                }
            },
            checkpoint=checkpoint,
            metadata=metadata,
            pending_writes=pending_writes if pending_writes else None,
            parent_config=(
                {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": parent_checkpoint_id,
                    }
                }
                if parent_checkpoint_id
                else None
            ),
        )

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self.get_tuple(config)

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = checkpoint["id"]
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        file_path = self._get_checkpoint_path(thread_id, checkpoint_ns, checkpoint_id)
        checkpoint_dict = {
            "checkpoint": _serialize_checkpoint(checkpoint),
            "metadata": _serialize_checkpoint(metadata),
            "parent_checkpoint_id": parent_checkpoint_id,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_dict, f, ensure_ascii=False, indent=2)

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return self.put(config, checkpoint, metadata, new_versions)

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")
        if not checkpoint_id:
            return

        file_path = self._get_writes_path(thread_id, checkpoint_ns, checkpoint_id, task_id)
        writes_data = {
            "writes": _serialize_checkpoint(writes),
            "task_id": task_id,
            "task_path": task_path,
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(writes_data, f, ensure_ascii=False, indent=2)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self.put_writes(config, writes, task_id, task_path)

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if config is None:
            return
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        ns_dir = checkpoint_ns.replace("|", "_ns_") if checkpoint_ns else "_root"
        dir_path = os.path.join(self.base_path, thread_id, ns_dir)
        if not os.path.exists(dir_path):
            return

        checkpoint_files = sorted(Path(dir_path).glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        if before:
            before_id = get_checkpoint_id(before)
            if before_id:
                checkpoint_files = [f for f in checkpoint_files if f.stem < before_id]

        count = 0
        for cp_file in checkpoint_files:
            cp_id = cp_file.stem
            if filter:
                pass

            cp_file_path = self._get_checkpoint_path(thread_id, checkpoint_ns, cp_id)
            with open(cp_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            checkpoint = _deserialize_checkpoint(data["checkpoint"])
            metadata = _deserialize_checkpoint(data["metadata"])
            parent_checkpoint_id = data.get("parent_checkpoint_id")
            pending_writes = self._load_pending_writes(thread_id, checkpoint_ns, cp_id)

            yield CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": cp_id,
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                pending_writes=pending_writes if pending_writes else None,
                parent_config=(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent_checkpoint_id,
                        }
                    }
                    if parent_checkpoint_id
                    else None
                ),
            )
            count += 1
            if limit is not None and count >= limit:
                break


if __name__ == "__main__":
    from langchain.agents import create_agent
    from langchain_core.messages import HumanMessage
    from Coder.model import llm
    from Coder.tools.file_tools import file_management_toolkit

    memory = FileSaver()
    agent = create_agent(
        model=llm,
        tools=file_management_toolkit,
        checkpointer=memory,
        debug=False,
    )
    config = RunnableConfig(configurable={"thread_id": "1"})
    while True:
        try:
            user_input = input("用户: ")
            if user_input.lower() in ("exit", "quit"):
                break
            print("助手:", end=" ", flush=True)
            input_data = {"messages": [HumanMessage(content=user_input)]}
            for chunk in agent.stream(
                input=input_data,
                config=config,
                stream_mode="messages",
            ):
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    msg_chunk, metadata = chunk
                    if hasattr(msg_chunk, "content") and msg_chunk.content:
                        print(msg_chunk.content, end="", flush=True)
            print()
        except KeyboardInterrupt:
            print("\n程序已中断")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            import traceback
            traceback.print_exc()
            continue
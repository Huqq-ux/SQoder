import uuid
import logging
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
from collections import defaultdict

from Coder.multi_agent.types import (
    CommunicationMessage,
    MessageType,
    AgentRole,
    CrewTask,
    CrewTaskStatus,
)

logger = logging.getLogger(__name__)


class CommunicationProtocol:
    def __init__(self):
        self._messages: Dict[str, CommunicationMessage] = {}
        self._conversation_threads: Dict[str, List[str]] = defaultdict(list)
        self._handlers: Dict[MessageType, List[Callable]] = defaultdict(list)
        self._agent_mailboxes: Dict[str, List[str]] = defaultdict(list)

    def send(
        self,
        sender: str,
        receiver: str,
        content: str,
        msg_type: MessageType = MessageType.TASK_ASSIGN,
        task_id: str = "",
        context: Dict[str, Any] = None,
        reply_to: str = "",
    ) -> str:
        msg_id = str(uuid.uuid4())[:8]
        msg = CommunicationMessage(
            msg_id=msg_id,
            msg_type=msg_type,
            sender=sender,
            receiver=receiver,
            content=content,
            task_id=task_id,
            context=context or {},
            reply_to=reply_to,
        )
        self._messages[msg_id] = msg

        thread_key = task_id if task_id else f"conv_{sender}_{receiver}"
        self._conversation_threads[thread_key].append(msg_id)
        self._agent_mailboxes[receiver].append(msg_id)

        for handler in self._handlers.get(msg_type, []):
            try:
                handler(msg)
            except Exception as e:
                logger.warning(f"消息处理器异常: {e}")

        logger.debug(
            f"[{msg_type.value}] {sender} → {receiver}: {content[:100]}"
        )
        return msg_id

    def receive(self, receiver: str) -> List[CommunicationMessage]:
        msg_ids = self._agent_mailboxes.get(receiver, [])
        messages = []
        for mid in msg_ids:
            msg = self._messages.get(mid)
            if msg:
                messages.append(msg)
        return messages

    def receive_by_task(
        self, task_id: str, receiver: str = ""
    ) -> List[CommunicationMessage]:
        thread_ids = self._conversation_threads.get(task_id, [])
        messages = []
        for mid in thread_ids:
            msg = self._messages.get(mid)
            if msg and (not receiver or msg.receiver == receiver):
                messages.append(msg)
        return messages

    def reply(
        self,
        original_msg_id: str,
        content: str,
        sender: str = "",
    ) -> Optional[str]:
        original = self._messages.get(original_msg_id)
        if not original:
            return None

        actual_sender = sender or original.receiver
        return self.send(
            sender=actual_sender,
            receiver=original.sender,
            content=content,
            msg_type=MessageType.TASK_RESULT,
            task_id=original.task_id,
            reply_to=original_msg_id,
        )

    def broadcast(
        self,
        sender: str,
        receivers: List[str],
        content: str,
        msg_type: MessageType = MessageType.SUPERVISOR_INSTRUCTION,
        task_id: str = "",
    ) -> List[str]:
        msg_ids = []
        for receiver in receivers:
            mid = self.send(
                sender=sender,
                receiver=receiver,
                content=content,
                msg_type=msg_type,
                task_id=task_id,
            )
            msg_ids.append(mid)
        return msg_ids

    def dispatch_task(
        self,
        supervisor: str,
        task: CrewTask,
        agent_name: str,
    ) -> str:
        content = (
            f"[任务ID: {task.task_id}]\n"
            f"[优先级: {task.priority}]\n\n"
            f"{task.description}"
        )
        return self.send(
            sender=supervisor,
            receiver=agent_name,
            content=content,
            msg_type=MessageType.TASK_ASSIGN,
            task_id=task.task_id,
            context=task.context,
        )

    def query_agent(
        self,
        sender: str,
        receiver: str,
        query: str,
        task_id: str = "",
    ) -> str:
        return self.send(
            sender=sender,
            receiver=receiver,
            content=query,
            msg_type=MessageType.TASK_QUERY,
            task_id=task_id,
        )

    def request_clarification(
        self,
        sender: str,
        receiver: str,
        question: str,
        task_id: str = "",
    ) -> str:
        return self.send(
            sender=sender,
            receiver=receiver,
            content=question,
            msg_type=MessageType.TASK_CLARIFY,
            task_id=task_id,
        )

    def send_status_update(
        self,
        sender: str,
        receiver: str,
        status: str,
        task_id: str = "",
    ) -> str:
        return self.send(
            sender=sender,
            receiver=receiver,
            content=status,
            msg_type=MessageType.STATUS_UPDATE,
            task_id=task_id,
        )

    def delegate_to_agent(
        self,
        sender: str,
        target_agent: str,
        task_description: str,
        task_id: str = "",
    ) -> str:
        return self.send(
            sender=sender,
            receiver=target_agent,
            content=task_description,
            msg_type=MessageType.DELEGATE,
            task_id=task_id,
        )

    def on_message(
        self, msg_type: MessageType, handler: Callable
    ) -> Callable:
        self._handlers[msg_type].append(handler)
        return handler

    def get_thread_history(self, task_id: str) -> List[CommunicationMessage]:
        thread_ids = self._conversation_threads.get(task_id, [])
        return [
            self._messages[mid]
            for mid in thread_ids
            if mid in self._messages
        ]

    def get_message(self, msg_id: str) -> Optional[CommunicationMessage]:
        return self._messages.get(msg_id)

    def clear_task_messages(self, task_id: str):
        thread_ids = self._conversation_threads.get(task_id, [])
        for mid in thread_ids:
            if mid in self._messages:
                msg = self._messages[mid]
                if msg.receiver in self._agent_mailboxes:
                    self._agent_mailboxes[msg.receiver] = [
                        x for x in self._agent_mailboxes[msg.receiver]
                        if x != mid
                    ]
                del self._messages[mid]
        self._conversation_threads.pop(task_id, None)

    def clear_agent_mailbox(self, agent_name: str):
        self._agent_mailboxes.pop(agent_name, None)

    def get_conversation_summary(self, task_id: str) -> str:
        messages = self.get_thread_history(task_id)
        if not messages:
            return ""

        lines = []
        for msg in messages:
            lines.append(
                f"[{msg.sender} → {msg.receiver}] "
                f"({msg.msg_type.value}) {msg.content[:200]}"
            )
        return "\n".join(lines)

    def reset(self):
        self._messages.clear()
        self._conversation_threads.clear()
        self._handlers.clear()
        self._agent_mailboxes.clear()

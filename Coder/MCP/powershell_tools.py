import logging
import os
import re
import subprocess
import time
from typing import Any

import psutil
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Annotated

logger = logging.getLogger(__name__)

mcp = FastMCP()

_launched_pids: set[int] = set()

DANGEROUS_PATTERNS = [
    r"\bRemove-Item\s",
    r"\bDel\s",
    r"\brm\s",
    r"\bFormat-\w+\s",
    r"\bStop-Computer\b",
    r"\bRestart-Computer\b",
    r"\bRemove-Service\b",
    r"\bSet-ExecutionPolicy\b",
    r"\bInvoke-WebRequest\b",
    r"\bInvoke-RestMethod\b",
    r"\bStart-Process\b",
    r"\bnet\s+user\b",
    r"\bnet\s+localgroup\b",
    r"\breg\s+add\b",
    r"\breg\s+delete\b",
    r"\bschtasks\b",
    r"\bbitsadmin\b",
    r"\bcertutil\b",
    r"\biex\b",
    r"\bInvoke-Expression\b",
    r"\bNew-Object\s+Net\.WebClient\b",
    r"\bSystem\.Diagnostics\.Process\b",
    r"\|.*\bOut-File\b",
    r"\|.*\bSet-Content\b",
    r"\|.*\bAdd-Content\b",
]

ALLOWED_WORK_DIR_PATTERN = re.compile(r'^[a-zA-Z]:[\\/][\w\\/. -]+$')


def _validate_script_safety(script: str) -> str | None:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, script, re.IGNORECASE):
            return pattern
    return None


@mcp.tool(name="get_powershell_processes", description="获取所有PowerShell进程")
def get_powershell_processes() -> list[dict[str, Any]]:
    processes = []
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = process.info.get('cmdline')
            if process.info['name'] and cmdline and 'powershell' in ' '.join(cmdline).lower():
                processes.append({
                    'pid': process.info['pid'],
                    'name': process.info['name'],
                    'cmdline': process.info['cmdline'],
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes


@mcp.tool(name="close_powershell_processes", description="关闭PowerShell进程")
def close_powershell_processes(close_all: Annotated[bool, Field(description="是否关闭所有PowerShell进程，默认仅关闭本工具启动的进程", default=False)]) -> str:
    try:
        if close_all:
            processes = get_powershell_processes()
            if not processes:
                return "没有PowerShell进程"
            closed_count = 0
            for process in processes:
                try:
                    p = psutil.Process(process['pid'])
                    p.terminate()
                    p.wait(timeout=5)
                    closed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, psutil.TimeoutExpired):
                    try:
                        psutil.Process(process['pid']).kill()
                        closed_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            _launched_pids.clear()
            return f"关闭了{closed_count}个PowerShell进程"
        else:
            if not _launched_pids:
                return "没有本工具启动的PowerShell进程"
            closed_count = 0
            for pid in list(_launched_pids):
                try:
                    p = psutil.Process(pid)
                    p.terminate()
                    p.wait(timeout=5)
                    closed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, psutil.TimeoutExpired):
                    try:
                        psutil.Process(pid).kill()
                        closed_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            _launched_pids.difference_update(_launched_pids)
            return f"关闭了{closed_count}个本工具启动的PowerShell进程"
    except Exception as e:
        logger.error(f"关闭PowerShell进程失败: {e}")
        return f"关闭PowerShell进程失败: {str(e)}"


@mcp.tool(name="open_new_powershell", description="打开新的PowerShell窗口")
def open_new_powershell(working_directory: Annotated[str, Field(description="可选的工作目录，默认为空时使用当前目录", default="")]) -> str:
    try:
        if working_directory:
            if not ALLOWED_WORK_DIR_PATTERN.match(working_directory):
                return f"工作目录路径格式不合法: {working_directory}"
            if not os.path.isdir(working_directory):
                return f"工作目录不存在: {working_directory}"
            cmd = ["powershell", "-NoLogo", "-NoProfile", "-Command",
                   "Start-Process", "powershell", "-WorkingDirectory", working_directory]
        else:
            cmd = ["powershell", "-NoLogo", "-NoProfile", "-Command", "Start-Process", "powershell"]

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 and res.stderr:
            return f"打开PowerShell窗口失败: {res.stderr.strip()}"

        time.sleep(3)

        new_processes = get_powershell_processes()
        for proc in new_processes:
            _launched_pids.add(proc['pid'])

        return f"成功打开PowerShell窗口，当前系统共有{len(new_processes)}个PowerShell进程"
    except Exception as e:
        logger.error(f"打开PowerShell窗口失败: {e}")
        return f"打开PowerShell窗口失败: {str(e)}"


@mcp.tool(name="run_powershell_script", description="执行PowerShell命令并返回结果")
def run_powershell_script(script: Annotated[str, Field(description="要运行的PowerShell命令")]) -> str:
    try:
        logger.info(f"准备执行脚本: {script}")

        dangerous = _validate_script_safety(script)
        if dangerous:
            return f"脚本包含不允许的命令模式({dangerous})，已被安全策略拦截"

        cmd = ["powershell", "-NoLogo", "-NoProfile", "-Command", script]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        output_parts = []
        if result.stdout.strip():
            output_parts.append(result.stdout.strip())
        if result.stderr.strip():
            output_parts.append(f"[STDERR] {result.stderr.strip()}")

        if result.returncode != 0:
            output_parts.append(f"[退出码: {result.returncode}]")

        if not output_parts:
            return f"命令执行成功（无输出）"

        return "\n".join(output_parts)

    except subprocess.TimeoutExpired:
        return "命令执行超时（120秒），请检查命令是否需要交互输入"
    except FileNotFoundError:
        return "找不到PowerShell，请确认系统已安装PowerShell"
    except Exception as e:
        logger.error(f"执行脚本失败: {e}")
        return f"执行脚本失败: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")

import subprocess
import shlex

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from typing import Annotated


mcp = FastMCP()

@mcp.tool(name="run_shell_command",description="run shell command")
def run_shell_command(command: Annotated[str,Field(description="shell command to run")]) -> str:
    try:
        shell_command = shlex.split(command)
        if "rm" in shell_command:
            raise Exception("rm命令不允许执行")
        res = subprocess.run(command, capture_output=True, text=True, shell=True)
        if res.returncode != 0:
            return res.stderr
        else:
            return res.stdout
    except Exception as e:
        return str(e)

def run_command_by_popen(command: str) -> str:
    try:
        with subprocess.Popen(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE,text = True) as proc:
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                return stderr
            else:
                return stdout
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    mcp.run(transport="stdio")

from langchain_community.agent_toolkits import FileManagementToolkit
import os

workspace_dir = os.path.join(os.path.dirname(__file__), "..", "workspace")
os.makedirs(workspace_dir, exist_ok=True)

file_management_toolkit = FileManagementToolkit(root_dir=workspace_dir).get_tools()

__all__ = ["file_management_toolkit"]
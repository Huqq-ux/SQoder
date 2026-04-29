import ast
import logging
from typing import Callable, Optional, Tuple
from Coder.tools.skill_store import SkillDefinition

logger = logging.getLogger(__name__)

_BANNED_MODULES = {
    "os", "subprocess", "shutil", "sys", "ctypes",
    "socket", "requests", "urllib", "http",
    "pickle", "marshal", "code", "codeop",
    "compileall", "py_compile", "importlib",
    "threading", "multiprocessing",
    "signal", "atexit",
}

_ALLOWED_BUILTINS = {
    "abs", "all", "any", "ascii", "bin", "bool", "bytes",
    "chr", "complex", "dict", "divmod", "enumerate", "filter",
    "float", "format", "frozenset", "hash", "hex", "int",
    "isinstance", "issubclass", "iter", "len", "list", "map",
    "max", "min", "oct", "ord", "pow", "print", "range",
    "repr", "reversed", "round", "set", "slice", "sorted",
    "str", "sum", "tuple", "type", "zip",
    "True", "False", "None", "Exception", "ValueError",
    "TypeError", "KeyError", "IndexError", "RuntimeError",
    "ImportError", "AttributeError", "StopIteration", "OSError",
    "__import__",
}


class SkillCompileError(Exception):
    pass


class SkillCompiler:

    @staticmethod
    def compile(skill: SkillDefinition) -> Optional[Callable]:
        if not skill.code.strip():
            logger.warning(f"技能 {skill.name} 没有实现代码")
            return None

        valid, error = SkillCompiler.validate(skill.code)
        if not valid:
            raise SkillCompileError(f"代码验证失败: {error}")

        safe, reason = SkillCompiler._security_check(skill.code)
        if not safe:
            raise SkillCompileError(f"安全检查失败: {reason}")

        try:
            tree = ast.parse(skill.code)

            func_def = None
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_def = node
                    break

            if func_def is None:
                raise SkillCompileError("代码中未找到函数定义")

            module = ast.Module(body=tree.body, type_ignores=[])
            compiled = compile(module, f"<skill_{skill.name}>", "exec")

            import builtins as _builtins_module
            _raw_builtins = (
                _builtins_module.__dict__
                if hasattr(_builtins_module, '__dict__')
                else vars(_builtins_module)
            )
            namespace = {"__builtins__": {
                k: _raw_builtins[k]
                for k in _ALLOWED_BUILTINS
                if k in _raw_builtins
            }}

            import json as _json
            import re as _re
            import math as _math
            import datetime as _datetime
            import collections as _collections
            import itertools as _itertools
            import functools as _functools
            import hashlib as _hashlib

            namespace.update({
                "json": _json,
                "re": _re,
                "math": _math,
                "datetime": _datetime,
                "collections": _collections,
                "itertools": _itertools,
                "functools": _functools,
                "hashlib": _hashlib,
            })

            exec(compiled, namespace)

            func = namespace.get(func_def.name)
            if func and callable(func):
                logger.info(f"技能编译成功: {skill.name}")
                return func
            else:
                raise SkillCompileError(
                    f"编译后未找到可调用函数: {func_def.name}"
                )

        except SyntaxError as e:
            raise SkillCompileError(f"语法错误 第{e.lineno}行: {e.msg}")
        except SkillCompileError:
            raise
        except Exception as e:
            raise SkillCompileError(f"编译异常: {e}")

    @staticmethod
    def validate(code: str) -> Tuple[bool, str]:
        if not code or not code.strip():
            return False, "代码为空"
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as e:
            return False, f"第{e.lineno}行: {e.msg}"

    @staticmethod
    def _security_check(code: str) -> Tuple[bool, str]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False, "语法解析失败"

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in _BANNED_MODULES:
                        return False, f"禁止导入模块: {alias.name}"

            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in _BANNED_MODULES:
                    return False, f"禁止导入模块: {node.module}"

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("exec", "eval", "compile", "__import__"):
                        return False, f"禁止调用: {node.func.id}"

                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in ("os", "subprocess", "sys", "shutil"):
                            return False, f"禁止调用: {node.func.value.id}.{node.func.attr}"

        return True, ""

    @staticmethod
    def extract_signature(code: str) -> Optional[dict]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return None

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                params = []
                for arg in node.args.args:
                    info = {"name": arg.arg}
                    if arg.annotation:
                        if isinstance(arg.annotation, ast.Name):
                            info["type"] = arg.annotation.id
                    params.append(info)
                return {
                    "name": node.name,
                    "parameters": params,
                }
        return None

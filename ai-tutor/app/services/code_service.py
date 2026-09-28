"""代码沙箱服务 - Phase 5

对照 ai_architecture_plan.md Agent 6：
- Judge0 Docker沙箱（Python，5秒超时，256MB内存限制）
- 安全策略（禁止文件/网络访问）
- 降级方案：无Judge0时用subprocess本地执行（受限环境）
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
import os
import signal
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Judge0 配置
JUDGE0_URL = os.getenv("JUDGE0_URL", "")
JUDGE0_TIMEOUT = 5  # 秒
JUDGE0_MEMORY = 256 * 1024  # 256MB in KB


@dataclass
class ExecutionResult:
    """代码执行结果"""
    success: bool
    output: str
    error: str
    exit_code: int
    time_ms: int
    memory_kb: int
    test_results: list[dict]  # 每个测试用例的结果


class CodeSandbox:
    """代码沙箱 - 安全执行学生代码"""

    def __init__(self):
        self.judge0_available = bool(JUDGE0_URL)
        if self.judge0_available:
            logger.info("代码沙箱: Judge0模式")
        else:
            logger.info("代码沙箱: 本地subprocess模式（降级）")

    def execute(
        self,
        code: str,
        test_cases: list[dict],
        language: str = "python",
        timeout: int = JUDGE0_TIMEOUT,
    ) -> ExecutionResult:
        """执行代码并验证测试用例

        Args:
            code: Python代码
            test_cases: [{input: str, expected: str}]
            language: 编程语言
            timeout: 超时秒数

        Returns:
            ExecutionResult
        """
        if self.judge0_available:
            return self._execute_judge0(code, test_cases, timeout)
        else:
            # 对照规范 B6：Judge0不可用时必须明确报错，不允许降级为subprocess
            return ExecutionResult(
                success=False,
                output="",
                error="代码沙箱服务（Judge0）不可用，请联系管理员配置。不允许在服务器上直接执行学生代码。",
                exit_code=-1,
                time_ms=0,
                memory_kb=0,
                test_results=[],
            )

    def _execute_judge0(
        self,
        code: str,
        test_cases: list[dict],
        timeout: int,
    ) -> ExecutionResult:
        """Judge0 沙箱执行"""
        import requests

        test_results = []
        all_output = []
        all_errors = []

        for tc in test_cases:
            try:
                payload = {
                    "source_code": code,
                    "language_id": 71,  # Python 3
                    "stdin": tc.get("input", ""),
                    "cpu_time_limit": timeout,
                    "memory_limit": JUDGE0_MEMORY,
                    "enable_network": False,
                }

                resp = requests.post(
                    f"{JUDGE0_URL}/submissions?wait=true",
                    json=payload,
                    timeout=timeout + 5,
                )
                data = resp.json()

                status = data.get("status", {}).get("id", 0)
                output = (data.get("stdout") or "").strip()
                expected = str(tc.get("expected", "")).strip()
                error = (data.get("stderr") or data.get("compile_output") or "").strip()

                passed = (status == 3) and (output == expected)  # 3 = Accepted
                test_results.append({
                    "input": tc.get("input", ""),
                    "expected": expected,
                    "output": output,
                    "passed": passed,
                    "status": "accepted" if status == 3 else "wrong_answer" if status == 4 else "error",
                })
                all_output.append(output)
                if error:
                    all_errors.append(error)

            except Exception as e:
                test_results.append({
                    "input": tc.get("input", ""),
                    "expected": str(tc.get("expected", "")),
                    "output": "",
                    "passed": False,
                    "status": "execution_error",
                    "error": str(e),
                })
                all_errors.append(str(e))

        success = all(r["passed"] for r in test_results) if test_results else False
        return ExecutionResult(
            success=success,
            output="\n".join(all_output),
            error="\n".join(all_errors),
            exit_code=0 if success else 1,
            time_ms=0,
            memory_kb=0,
            test_results=test_results,
        )

    def _execute_local(
        self,
        code: str,
        test_cases: list[dict],
        timeout: int,
    ) -> ExecutionResult:
        """本地subprocess执行（降级方案）

        安全措施：
        - 临时文件执行，执行后删除
        - 超时强制终止
        - 捕获所有输出
        """
        test_results = []
        all_output = []
        all_errors = []

        # 如果没有测试用例，直接执行代码
        if not test_cases:
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False, encoding="utf-8"
                ) as f:
                    f.write(code)
                    tmp_path = f.name

                proc = subprocess.run(
                    ["python", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tempfile.gettempdir(),
                )

                output = proc.stdout.strip()
                error = proc.stderr.strip()

                if output:
                    all_output.append(output)
                if error:
                    all_errors.append(error)

                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

            except subprocess.TimeoutExpired:
                all_errors.append(f"超时（{timeout}秒）")
            except Exception as e:
                all_errors.append(str(e))

            success = len(all_errors) == 0 and len(all_output) > 0
            return ExecutionResult(
                success=success,
                output="\n".join(all_output),
                error="\n".join(all_errors),
                exit_code=0 if success else 1,
                time_ms=0,
                memory_kb=0,
                test_results=test_results,
            )

        for tc in test_cases:
            stdin_data = tc.get("input", "")
            expected = str(tc.get("expected", "")).strip()

            # 构建执行代码：用户代码 + 测试断言
            exec_code = code + "\n"

            # 如果test_cases有input/expected格式，生成断言
            if stdin_data:
                exec_code += f"\n# === 测试 ===\n_test_input = {repr(stdin_data)}\n"

            try:
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False, encoding="utf-8"
                ) as f:
                    f.write(exec_code)
                    tmp_path = f.name

                proc = subprocess.run(
                    ["python", tmp_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tempfile.gettempdir(),
                )

                output = proc.stdout.strip()
                error = proc.stderr.strip()

                # 简单匹配：输出包含expected即通过
                passed = expected in output if expected else bool(output and not error)

                test_results.append({
                    "input": stdin_data,
                    "expected": expected,
                    "output": output[:500],  # 截断
                    "passed": passed,
                    "status": "accepted" if passed else ("runtime_error" if error else "wrong_answer"),
                })
                all_output.append(output)
                if error:
                    all_errors.append(error)

            except subprocess.TimeoutExpired:
                test_results.append({
                    "input": stdin_data,
                    "expected": expected,
                    "output": "",
                    "passed": False,
                    "status": "time_limit_exceeded",
                })
                all_errors.append(f"超时（{timeout}秒）")

            except Exception as e:
                test_results.append({
                    "input": stdin_data,
                    "expected": expected,
                    "output": "",
                    "passed": False,
                    "status": "execution_error",
                    "error": str(e),
                })
                all_errors.append(str(e))

            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

        success = all(r["passed"] for r in test_results) if test_results else False
        return ExecutionResult(
            success=success,
            output="\n".join(all_output),
            error="\n".join(all_errors),
            exit_code=0 if success else 1,
            time_ms=0,
            memory_kb=0,
            test_results=test_results,
        )


# 全局单例
code_sandbox = CodeSandbox()

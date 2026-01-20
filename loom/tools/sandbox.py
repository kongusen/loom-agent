"""
Sandbox - 沙箱环境管理

提供安全的文件系统隔离和 Python 代码执行隔离。

核心功能：
1. 路径验证 - 防止路径遍历攻击
2. 边界检查 - 确保操作不越界
3. 安全包装 - 提供安全的文件操作接口
4. Python 代码执行 - 使用 RestrictedPython 安全执行代码

设计原则：
- 默认拒绝 - 只允许明确在沙箱内的操作
- 路径规范化 - 解析所有符号链接和相对路径
- 清晰错误 - 提供明确的安全错误信息
"""

import asyncio
from pathlib import Path
from typing import Any

try:
    from RestrictedPython import compile_restricted, safe_globals
    RESTRICTED_PYTHON_AVAILABLE = True
except ImportError:
    RESTRICTED_PYTHON_AVAILABLE = False


class SandboxViolation(Exception):
    """沙箱违规异常"""

    pass


class Sandbox:
    """
    沙箱环境管理器

    管理一个隔离的文件系统环境和 Python 代码执行环境。

    功能：
    - 文件系统隔离：确保所有文件操作都在指定目录内
    - Python 代码执行：使用 RestrictedPython 安全执行用户代码
    """

    def __init__(
        self,
        root_dir: str | Path,
        auto_create: bool = True,
        python_timeout: int = 30,
        allowed_modules: list[str] | None = None
    ):
        """
        初始化沙箱

        Args:
            root_dir: 沙箱根目录
            auto_create: 如果目录不存在，是否自动创建
            python_timeout: Python 代码执行超时时间（秒）
            allowed_modules: 允许导入的 Python 模块列表

        Raises:
            ValueError: 如果根目录无效
        """
        self.root_dir = Path(root_dir).resolve()
        self.python_timeout = python_timeout
        self.allowed_modules = allowed_modules or ['math', 'json', 'datetime']

        # 确保根目录存在
        if not self.root_dir.exists():
            if auto_create:
                self.root_dir.mkdir(parents=True, exist_ok=True)
            else:
                raise ValueError(f"Sandbox root directory does not exist: {self.root_dir}")

        if not self.root_dir.is_dir():
            raise ValueError(f"Sandbox root must be a directory: {self.root_dir}")

    def validate_path(self, path: str | Path) -> Path:
        """
        验证路径是否在沙箱内

        Args:
            path: 要验证的路径（可以是相对或绝对路径）

        Returns:
            规范化后的绝对路径

        Raises:
            SandboxViolation: 如果路径在沙箱外
        """
        # 转换为 Path 对象
        target_path = Path(path)

        # 如果是相对路径，相对于沙箱根目录解析
        if not target_path.is_absolute():
            target_path = self.root_dir / target_path

        # 规范化路径（解析 .., ., 符号链接等）
        try:
            resolved_path = target_path.resolve()
        except (OSError, RuntimeError) as e:
            raise SandboxViolation(f"Cannot resolve path: {path}") from e

        # 检查是否在沙箱内
        try:
            resolved_path.relative_to(self.root_dir)
        except ValueError:
            raise SandboxViolation(
                f"Path outside sandbox: {path} -> {resolved_path} "
                f"(sandbox root: {self.root_dir})"
            ) from None

        return resolved_path

    def safe_read(self, path: str | Path) -> str:
        """
        安全读取文件

        Args:
            path: 文件路径

        Returns:
            文件内容

        Raises:
            SandboxViolation: 如果路径在沙箱外
            FileNotFoundError: 如果文件不存在
        """
        validated_path = self.validate_path(path)

        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not validated_path.is_file():
            raise ValueError(f"Not a file: {path}")

        return validated_path.read_text(encoding="utf-8")

    def safe_write(self, path: str | Path, content: str, create_dirs: bool = True) -> None:
        """
        安全写入文件

        Args:
            path: 文件路径
            content: 文件内容
            create_dirs: 是否自动创建父目录

        Raises:
            SandboxViolation: 如果路径在沙箱外
        """
        validated_path = self.validate_path(path)

        # 创建父目录
        if create_dirs:
            validated_path.parent.mkdir(parents=True, exist_ok=True)

        validated_path.write_text(content, encoding="utf-8")

    def safe_exists(self, path: str | Path) -> bool:
        """
        安全检查路径是否存在

        Args:
            path: 路径

        Returns:
            是否存在

        Raises:
            SandboxViolation: 如果路径在沙箱外
        """
        validated_path = self.validate_path(path)
        return validated_path.exists()

    def safe_list_dir(self, path: str | Path = ".") -> list[str]:
        """
        安全列出目录内容

        Args:
            path: 目录路径（默认为沙箱根目录）

        Returns:
            文件和目录名称列表

        Raises:
            SandboxViolation: 如果路径在沙箱外
            NotADirectoryError: 如果路径不是目录
        """
        validated_path = self.validate_path(path)

        if not validated_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")

        if not validated_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {path}")

        return [item.name for item in validated_path.iterdir()]

    def get_relative_path(self, path: str | Path) -> str:
        """
        获取相对于沙箱根目录的相对路径

        Args:
            path: 路径

        Returns:
            相对路径字符串

        Raises:
            SandboxViolation: 如果路径在沙箱外
        """
        validated_path = self.validate_path(path)
        return str(validated_path.relative_to(self.root_dir))

    def get_absolute_path(self, path: str | Path) -> str:
        """
        获取绝对路径

        Args:
            path: 路径

        Returns:
            绝对路径字符串

        Raises:
            SandboxViolation: 如果路径在沙箱外
        """
        return str(self.validate_path(path))

    async def execute_python(
        self,
        code: str,
        params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        在沙箱中执行 Python 代码

        Args:
            code: Python 代码
            params: 输入参数

        Returns:
            执行结果字典，包含 success, result, error 等字段

        Raises:
            SandboxViolation: 如果代码包含不安全操作
        """
        if not RESTRICTED_PYTHON_AVAILABLE:
            return {
                "success": False,
                "error": "RestrictedPython not installed. Install with: pip install RestrictedPython"
            }

        try:
            # 编译受限代码
            byte_code = compile_restricted(code, '<sandbox>', 'exec')

            if byte_code.errors:
                raise SandboxViolation(f"Code compilation errors: {byte_code.errors}")

            # 创建安全环境
            safe_env = self._create_safe_environment(params or {})

            # 执行代码（带超时）
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, exec, byte_code.code, safe_env),
                timeout=self.python_timeout
            )

            # 提取结果
            result = safe_env.get('result', None)

            return {
                "success": True,
                "result": result
            }

        except TimeoutError:
            return {
                "success": False,
                "error": f"Execution timeout after {self.python_timeout} seconds"
            }
        except SandboxViolation:
            raise
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _create_safe_environment(self, params: dict[str, Any]) -> dict[str, Any]:
        """创建安全的执行环境"""
        safe_env: dict[str, Any] = safe_globals.copy()

        # 添加输入参数
        safe_env.update(params)

        # 添加允许的模块
        for module_name in self.allowed_modules:
            try:
                module = __import__(module_name)
                safe_env[module_name] = module
            except ImportError:
                pass

        # 添加安全的内置函数
        safe_env['_print_'] = lambda x: print(x)
        safe_env['_getattr_'] = getattr

        return safe_env

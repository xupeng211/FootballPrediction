import sys
import types
from pathlib import Path

# os.environ.setdefault("MINIMAL_API_MODE", "true")  # 移除最小API模式限制以启用完整测试

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if "src" not in sys.modules:
    src_module = types.ModuleType("src")
    src_module.__path__ = [str(PROJECT_ROOT / "src")]
    sys.modules["src"] = src_module

if "src.domain" not in sys.modules:
    domain_module = types.ModuleType("src.domain")
    domain_module.__path__ = [str(PROJECT_ROOT / "src" / "domain")]
    sys.modules["src.domain"] = domain_module

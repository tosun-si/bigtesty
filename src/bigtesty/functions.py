"""Loading of the Python functions of a project: the assertion functions and the SQL renderer."""

import hashlib
import importlib.util
from collections.abc import Callable
from functools import cache
from pathlib import Path
from typing import Any

from bigtesty.exceptions import SpecError


@cache
def load_function(module_path: Path, function_name: str) -> Callable[..., Any]:
    # A unique module name per file, two modules can have the same name in different folders.
    module_name = f"bigtesty_functions_{hashlib.sha1(str(module_path).encode()).hexdigest()[:12]}"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)

    if module_spec is None or module_spec.loader is None:
        raise SpecError(f"Cannot load the Python module {module_path}")

    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    if not callable(function := getattr(module, function_name, None)):
        raise SpecError(f"The function {function_name} doesn't exist in {module_path}")

    return function

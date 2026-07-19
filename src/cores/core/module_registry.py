from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional, Set

from cores.interfaces.module import Module


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: List[Module] = []
        self._by_name: Dict[str, Module] = {}

    def register(self, module: Module, runtime: Any = None) -> None:
        if module.name in self._by_name:
            raise ValueError(
                f"Module '{module.name}' is already registered"
            )
        deps = module.dependencies
        missing = [d for d in deps if d not in self._by_name]
        if missing:
            raise ValueError(
                f"Module '{module.name}' has unmet dependencies: {missing}"
            )
        self._modules.append(module)
        self._by_name[module.name] = module
        module.on_register(runtime)

    def unregister(self, name: str) -> None:
        if name not in self._by_name:
            raise KeyError(f"Module '{name}' is not registered")
        module = self._by_name[name]
        dependents = [m.name for m in self._modules if name in m.dependencies]
        if dependents:
            raise ValueError(
                f"Cannot unregister '{name}': required by {dependents}"
            )
        self._modules.remove(module)
        del self._by_name[name]

    def get(self, name: str) -> Optional[Module]:
        return self._by_name.get(name)

    def get_all(self) -> List[Module]:
        return list(self._modules)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def __len__(self) -> int:
        return len(self._modules)

    def __iter__(self):
        return iter(self._modules)

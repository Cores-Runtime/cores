import pytest
from cores.interfaces.module import Module, ModuleResult, ModuleProfile, ModuleLifecycleStage
from cores.core.module_registry import ModuleRegistry
from cores.core.robot_state import RobotState
from cores.core.runtime_context import RuntimeContext


class SimpleModule(Module):
    def execute(self, state: RobotState, context: RuntimeContext) -> ModuleResult:
        return ModuleResult(module_name=self.name)


def test_registry_register_and_get() -> None:
    registry = ModuleRegistry()
    m = SimpleModule("test_mod")
    registry.register(m)
    assert registry.get("test_mod") is m
    assert len(registry) == 1


def test_registry_register_duplicate_raises() -> None:
    registry = ModuleRegistry()
    m = SimpleModule("test_mod")
    registry.register(m)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(SimpleModule("test_mod"))


def test_registry_unregister() -> None:
    registry = ModuleRegistry()
    m = SimpleModule("test_mod")
    registry.register(m)
    registry.unregister("test_mod")
    assert registry.get("test_mod") is None
    assert len(registry) == 0


def test_registry_unregister_missing_raises() -> None:
    registry = ModuleRegistry()
    with pytest.raises(KeyError):
        registry.unregister("nonexistent")


def test_registry_unregister_with_dependents_raises() -> None:
    registry = ModuleRegistry()
    parent = SimpleModule("parent", profile=ModuleProfile())
    child = SimpleModule("child", profile=ModuleProfile(dependencies=frozenset(["parent"])))
    registry.register(parent)
    registry.register(child)
    with pytest.raises(ValueError, match="required by"):
        registry.unregister("parent")


def test_registry_dependency_validation() -> None:
    registry = ModuleRegistry()
    m = SimpleModule("mod", profile=ModuleProfile(dependencies=frozenset(["missing_dep"])))
    with pytest.raises(ValueError, match="unmet dependencies"):
        registry.register(m)


def test_registry_get_all() -> None:
    registry = ModuleRegistry()
    m1 = SimpleModule("m1")
    m2 = SimpleModule("m2")
    registry.register(m1)
    registry.register(m2)
    all_mods = registry.get_all()
    assert len(all_mods) == 2
    assert m1 in all_mods
    assert m2 in all_mods


def test_registry_contains() -> None:
    registry = ModuleRegistry()
    m = SimpleModule("test_mod")
    registry.register(m)
    assert "test_mod" in registry
    assert "nonexistent" not in registry


def test_registry_iter() -> None:
    registry = ModuleRegistry()
    names = ["a", "b", "c"]
    for name in names:
        registry.register(SimpleModule(name))
    assert [m.name for m in registry] == names


def test_lifecycle_on_register_called() -> None:
    registry = ModuleRegistry()
    recorded = []

    class TrackingModule(Module):
        def execute(self, state, context):
            return ModuleResult(module_name=self.name)
        def on_register(self, runtime):
            super().on_register(runtime)
            recorded.append(("register", self.name, runtime))

    m = TrackingModule("tracked")
    registry.register(m, runtime="fake_runtime")
    assert recorded == [("register", "tracked", "fake_runtime")]
    assert m.lifecycle_stage == ModuleLifecycleStage.REGISTERED


def test_lifecycle_on_startup_called() -> None:
    recorded = []

    class StartupModule(Module):
        def execute(self, state, context):
            return ModuleResult(module_name=self.name)
        def on_startup(self):
            super().on_startup()
            recorded.append(("startup", self.name))

    m = StartupModule("startup_test")
    assert m.lifecycle_stage == ModuleLifecycleStage.CREATED
    m.on_startup()
    assert recorded == [("startup", "startup_test")]
    assert m.lifecycle_stage == ModuleLifecycleStage.STARTED


def test_lifecycle_on_shutdown_called() -> None:
    recorded = []

    class ShutdownModule(Module):
        def execute(self, state, context):
            return ModuleResult(module_name=self.name)
        def on_shutdown(self):
            super().on_shutdown()
            recorded.append(("shutdown", self.name))

    m = ShutdownModule("shutdown_test")
    m.on_shutdown()
    assert recorded == [("shutdown", "shutdown_test")]
    assert m.lifecycle_stage == ModuleLifecycleStage.STOPPED


def test_module_display_name() -> None:
    m = SimpleModule("collision_avoidance")
    assert m.display_name == "Collision Avoidance"


def test_module_profile_with_metadata() -> None:
    profile = ModuleProfile(
        version="2.0.0",
        description="Test module",
        author="CORES",
        tags=frozenset(["perception", "lidar"]),
        dependencies=frozenset(["localization"]),
    )
    assert profile.version == "2.0.0"
    assert profile.description == "Test module"
    assert profile.author == "CORES"
    assert "perception" in profile.tags
    assert "localization" in profile.dependencies

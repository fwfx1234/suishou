from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_icon_generator():
    spec = importlib.util.spec_from_file_location("gen_qta_icons", ROOT / "tools" / "gen_qta_icons.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_icon_generator_collects_plain_qml_icon_names(tmp_path) -> None:
    module = _load_icon_generator()
    sample = tmp_path / "Sample.qml"
    sample.write_text(
        'import QtQuick\n'
        'Item { property string iconName: "mdi6.magic-staff"; property string manifestIcon: "qta:fa5s.rocket" }\n',
        encoding="utf-8",
    )
    old_src = module.SRC
    try:
        module.SRC = tmp_path
        assert module.collect_icon_names() == {"mdi6.magic-staff", "fa5s.rocket"}
    finally:
        module.SRC = old_src


def test_baked_qta_icons_cover_referenced_runtime_icons() -> None:
    module = _load_icon_generator()
    referenced = module.collect_icon_names()
    baked = {path.stem for path in (ROOT / "assets" / "qta_icons").glob("*.png")}
    assert referenced - baked == set()

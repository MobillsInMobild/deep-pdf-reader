from __future__ import annotations

from pathlib import Path

from deep_pdf_reader.rendering.renderer import PageRenderer


def test_page_renderer_is_lazy_and_writes_pngs(sample_pdf: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "pages"
    renderer = PageRenderer(dpi=96)

    paths = renderer.render(sample_pdf, [2, 4], output_dir)

    assert [path.name for path in paths] == ["page-0002.png", "page-0004.png"]
    assert all(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for path in paths)
    assert not (output_dir / "page-0001.png").exists()
    first_mtime = paths[0].stat().st_mtime_ns
    assert renderer.render(sample_pdf, [2], output_dir)[0].stat().st_mtime_ns == first_mtime

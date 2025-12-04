"""Matplotlib configuration for CJK font support."""

from __future__ import annotations

import platform


def get_cjk_font() -> str | None:
    """Get available CJK font name based on platform."""
    system = platform.system()

    if system == "Darwin":  # macOS
        fonts = ["PingFang SC", "Hiragino Sans GB", "STHeiti", "Arial Unicode MS"]
    elif system == "Windows":
        fonts = ["Microsoft YaHei", "SimHei", "SimSun", "NSimSun"]
    else:  # Linux
        fonts = [
            "Noto Sans CJK SC",
            "Noto Sans CJK TC",
            "WenQuanYi Micro Hei",
            "WenQuanYi Zen Hei",
            "Droid Sans Fallback",
        ]

    try:
        import matplotlib.font_manager as fm

        available = {f.name for f in fm.fontManager.ttflist}
        for font in fonts:
            if font in available:
                return font
    except Exception:
        pass

    return None


def configure_matplotlib() -> None:
    """Configure matplotlib with CJK font support."""
    try:
        import matplotlib.pyplot as plt

        font = get_cjk_font()
        if font:
            plt.rcParams["font.sans-serif"] = [font] + plt.rcParams.get(
                "font.sans-serif", []
            )
        plt.rcParams["axes.unicode_minus"] = False
    except ImportError:
        pass


# Auto-configure when module is imported
configure_matplotlib()

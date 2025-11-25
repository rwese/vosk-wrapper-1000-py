#!/usr/bin/env python3
"""Test script to validate TUI rendering and export screenshot."""

import asyncio
from pathlib import Path

from vosk_wrapper_1000.settings_tui import SettingsTUI


async def test_tui():
    """Run TUI and export screenshot."""
    # Create test config
    test_config = Path("/tmp/test-vosk-config.yaml")
    test_config.write_text(
        """
audio:
  noise_reduction_enabled: true
  noise_reduction_level: 0.05
  stationary_noise: false
  silence_threshold: 50.0
  normalize_audio: false
  normalization_target_level: 0.3
  vad_hysteresis_chunks: 10
  pre_roll_duration: 2.0
  noise_reduction_min_rms_ratio: 0.5
"""
    )

    app = SettingsTUI(config_path=test_config)

    # Run app in headless mode and capture screenshot
    async with app.run_test() as pilot:
        # Wait for app to mount
        await pilot.pause(0.5)

        # Export screenshot (save_screenshot creates a directory)
        svg_dir = Path("/tmp")
        app.save_screenshot(path=str(svg_dir))
        print(f"Screenshot saved to: {svg_dir}")

        # Print widget tree
        print("\n=== Widget Tree ===")
        from vosk_wrapper_1000.settings_tui import SettingsPanel

        settings_panel = app.query_one(SettingsPanel)
        print(f"SettingsPanel children count: {len(list(settings_panel.children))}")

        for i, child in enumerate(settings_panel.children):
            print(
                f"{i}: {child.__class__.__name__} - {child.id or '(no id)'} - classes: {child.classes}"
            )
            if hasattr(child, "children"):
                for j, subchild in enumerate(child.children):
                    print(
                        f"  {i}.{j}: {subchild.__class__.__name__} - {subchild.id or '(no id)'}"
                    )

        # Check if settings are visible
        from textual.widgets import Checkbox, Input

        print("\n=== Settings Inputs ===")
        try:
            nr_level = app.query_one("#noise_reduction_level", Input)
            print(f"noise_reduction_level: {nr_level.value}")
        except Exception as e:
            print(f"ERROR: Could not find noise_reduction_level: {e}")

        try:
            silence_threshold = app.query_one("#silence_threshold", Input)
            print(f"silence_threshold: {silence_threshold.value}")
        except Exception as e:
            print(f"ERROR: Could not find silence_threshold: {e}")

        try:
            nr_enabled = app.query_one("#noise_reduction_enabled", Checkbox)
            print(f"noise_reduction_enabled: {nr_enabled.value}")
        except Exception as e:
            print(f"ERROR: Could not find noise_reduction_enabled: {e}")


if __name__ == "__main__":
    asyncio.run(test_tui())

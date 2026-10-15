"""Smoke tests for the VK menu-card artwork."""
from pathlib import Path
import tempfile
import unittest

import cairosvg

CARD_DIR = Path(__file__).resolve().parent / "assets" / "cards"


class MenuCardTests(unittest.TestCase):
    def test_every_svg_card_renders_to_png(self):
        cards = sorted(CARD_DIR.glob("*.svg"))
        self.assertGreaterEqual(len(cards), 10, "Expected a full set of menu cards")
        with tempfile.TemporaryDirectory() as tmp:
            for svg in cards:
                with self.subTest(card=svg.name):
                    target = Path(tmp) / (svg.stem + ".png")
                    cairosvg.svg2png(
                        url=str(svg),
                        write_to=str(target),
                        output_width=1200,
                        output_height=630,
                    )
                    self.assertTrue(target.exists())
                    self.assertGreater(target.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)

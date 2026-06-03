import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from config import SHUTTER_MAP
from utils import (
    parse_shutter,
    calculate_moon_phase,
    moon_phase_info,
    calculate_nd,
    evaluate_exposure,
    calculate_dof,
    calculate_golden_hour,
    calculate_flash,
    milky_way_score,
)


class TestParseShutter(unittest.TestCase):
    def test_known_shutter(self):
        self.assertEqual(parse_shutter("1/125"), 1 / 125)

    def test_unknown_shutter_fallback(self):
        self.assertEqual(parse_shutter("1/xyz"), 1 / 125)

    def test_full_seconds(self):
        self.assertEqual(parse_shutter("1"), 1.0)
        self.assertEqual(parse_shutter("30"), 30.0)

    def test_fast_shutter(self):
        self.assertEqual(parse_shutter("1/8000"), 1 / 8000)


class TestCalculateMoonPhase(unittest.TestCase):
    def test_new_moon_boundary(self):
        phase = calculate_moon_phase(2024, 1, 11)
        self.assertAlmostEqual(phase, 0.0, delta=0.03)

    def test_full_moon_boundary(self):
        phase = calculate_moon_phase(2024, 1, 25)
        self.assertAlmostEqual(phase, 0.5, delta=0.03)

    def test_phase_in_range(self):
        for y in range(2023, 2026):
            phase = calculate_moon_phase(y, 6, 15)
            self.assertGreaterEqual(phase, 0.0)
            self.assertLessEqual(phase, 1.0)


class TestMoonPhaseInfo(unittest.TestCase):
    def test_new_moon(self):
        name, illum, _ = moon_phase_info(0.0)
        self.assertIn("Neumond", name)

    def test_full_moon(self):
        name, illum, _ = moon_phase_info(0.5)
        self.assertIn("Vollmond", name)

    def test_illumination_bounds(self):
        for phase in [0.0, 0.25, 0.5, 0.75, 1.0]:
            _, illum, _ = moon_phase_info(phase)
            self.assertGreaterEqual(illum, 0)
            self.assertLessEqual(illum, 100)

    def test_quarter_phases(self):
        name, _, _ = moon_phase_info(0.25)
        self.assertIn("Viertel", name)
        name, _, _ = moon_phase_info(0.75)
        self.assertIn("Viertel", name)


class TestCalculateND(unittest.TestCase):
    def test_three_stops(self):
        self.assertAlmostEqual(calculate_nd(1 / 125, 3), 1 / 125 * 8)

    def test_ten_stops(self):
        self.assertAlmostEqual(calculate_nd(1 / 60, 10), 1 / 60 * 1024)

    def test_zero_stops(self):
        self.assertEqual(calculate_nd(1.0, 0), 1.0)

    def test_one_stop(self):
        self.assertAlmostEqual(calculate_nd(1 / 250, 1), 1 / 125)


class TestEvaluateExposure(unittest.TestCase):
    def test_optimal_exposure(self):
        _, label = evaluate_exposure(100, 5.6, 1 / 125)
        self.assertIn("Optimal", label)

    def test_dark_scene(self):
        _, label = evaluate_exposure(100, 1.4, 1 / 30)
        self.assertIn("dunkel", label.lower())

    def test_overexposed(self):
        _, label = evaluate_exposure(100, 16, 1 / 250)
        self.assertIn("Überbelichtet", label)

    def test_ev_calculation(self):
        ev, _ = evaluate_exposure(100, 1.0, 1.0)
        self.assertAlmostEqual(ev, 0.0, places=1)


class TestCalculateDof(unittest.TestCase):
    def test_positive_values(self):
        near, far, total, hyper = calculate_dof(50, 2.8, 10)
        self.assertGreater(near, 0)
        self.assertGreater(far, near)
        self.assertGreater(hyper, 0)

    def test_hyperfocal(self):
        _, _, _, hyper = calculate_dof(50, 8, 10, 0.03)
        self.assertAlmostEqual(hyper, 50**2 / (8 * 0.03 * 1000), places=1)

    def test_infinite_dof(self):
        near, far, total, hyper = calculate_dof(50, 8, 100, 0.03)
        self.assertIsNotNone(total)


class TestCalculateGoldenHour(unittest.TestCase):
    def test_morning_golden_hour(self):
        result = calculate_golden_hour("06:00", "20:00")
        self.assertIn("golden_morning", result)
        self.assertEqual(result["golden_morning"][0], "06:00")

    def test_evening_golden_hour(self):
        result = calculate_golden_hour("06:00", "20:00")
        self.assertIn("golden_evening", result)
        self.assertEqual(result["golden_evening"][1], "20:00")

    def test_blue_hours(self):
        result = calculate_golden_hour("07:00", "19:00")
        self.assertIn("blue_morning", result)
        self.assertIn("blue_evening", result)


class TestCalculateFlash(unittest.TestCase):
    def test_known_gn_distance(self):
        self.assertAlmostEqual(calculate_flash(58, 5, 100), 11.6, places=0)

    def test_higher_iso_increases_aperture(self):
        val_100 = calculate_flash(58, 5, 100)
        val_400 = calculate_flash(58, 5, 400)
        self.assertGreater(val_400, val_100)

    def test_closer_distance_brighter(self):
        near = calculate_flash(58, 2, 100)
        far = calculate_flash(58, 10, 100)
        self.assertGreater(near, far)


class TestMilkyWayScore(unittest.TestCase):
    def test_excellent_conditions(self):
        score = milky_way_score(0.0, 6)
        self.assertGreater(score, 80)

    def test_full_moon_zero(self):
        score = milky_way_score(0.5, 6)
        self.assertLessEqual(score, 0)

    def test_winter_month_reduced(self):
        score = milky_way_score(0.0, 1)
        self.assertLess(score, 60)

    def test_score_range(self):
        for phase in [0.1, 0.3, 0.7, 0.9]:
            for month in range(1, 13):
                score = milky_way_score(phase, month)
                self.assertGreaterEqual(score, 0)
                self.assertLessEqual(score, 100)


if __name__ == "__main__":
    unittest.main()

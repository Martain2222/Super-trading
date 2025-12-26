#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test.py

High-level test runner for the Super-trading Python scripts.

Goals
-----
1) Automatically discover Python strategy scripts in ../scripts
   whose filenames start with 'Super-trading-bot-' and end with '.py'.

2) Dynamically import each script and check that it exposes:
      - a callable named 'backtest'
      - optionally, a callable named 'generate_signals'

3) Run a lightweight synthetic backtest on each script to make sure:
      - backtest() executes without exception
      - backtest() returns a finite float (PnL or equity)

4) When executed directly (python Tests/Test.py), print a
   human-friendly summary of all strategies and their PnL.

This file is intentionally verbose and well-commented so it can serve
as a template for future testing of additional strategies.
"""

import os
import sys
import math
import random
import importlib.util
import unittest
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Directory of this Test.py file
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to the scripts directory (../scripts)
SCRIPTS_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "scripts"))

# File name pattern we consider to be "strategy scripts"
SCRIPT_PREFIX = "Super-trading-bot-"
SCRIPT_SUFFIX = ".py"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def discover_strategy_files() -> List[str]:
    """
    Return a list of full paths to Python strategy scripts found in SCRIPTS_DIR.

    Only files that match 'Super-trading-bot-*.py' are returned.
    """
    if not os.path.isdir(SCRIPTS_DIR):
        return []

    files: List[str] = []
    for name in os.listdir(SCRIPTS_DIR):
        if not name.startswith(SCRIPT_PREFIX):
            continue
        if not name.endswith(SCRIPT_SUFFIX):
            continue
        full = os.path.join(SCRIPTS_DIR, name)
        if os.path.isfile(full):
            files.append(full)
    return sorted(files)


def load_module_from_path(path: str):
    """
    Dynamically import a module from a given file path.

    We generate a unique module name based on the file name.
    """
    module_name = os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create import spec for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def generate_dummy_prices(n: int = 300, start_price: float = 100.0) -> List[float]:
    """
    Generate a simple synthetic price series (random walk with drift).
    """
    random.seed(123)
    prices: List[float] = []
    price = start_price
    for _ in range(n):
        # small random change
        shock = random.gauss(0.0003, 0.01)
        price *= (1.0 + shock)
        prices.append(price)
    return prices


def generate_dummy_ohlc(n: int = 300, start_price: float = 100.0):
    """
    Generate simple synthetic OHLC series for scripts that expect
    high/low/close arrays (like breakout / ATR strategies).
    """
    random.seed(456)
    close = generate_dummy_prices(n, start_price)
    high = [c * (1.0 + abs(random.gauss(0, 0.002))) for c in close]
    low = [c * (1.0 - abs(random.gauss(0, 0.002))) for c in close]
    return high, low, close


# ---------------------------------------------------------------------------
# Low-level functional tests
# ---------------------------------------------------------------------------

class StrategyModuleWrapper:
    """
    Small helper to encapsulate a loaded strategy module and its metadata.
    """

    def __init__(self, path: str):
        self.path = path
        self.name = os.path.basename(path)
        self.module = None

    def load(self):
        """Load the Python module from the path."""
        if self.module is None:
            self.module = load_module_from_path(self.path)
        return self.module

    def has_attr(self, attr: str) -> bool:
        """Check if the underlying module exposes a given attribute."""
        if self.module is None:
            self.load()
        return hasattr(self.module, attr)

    def get_attr(self, attr: str) -> Any:
        """Get an attribute from the module (after ensuring it's loaded)."""
        if self.module is None:
            self.load()
        return getattr(self.module, attr, None)


# Discover strategy files once, reuse in tests and main
_DISCOVERED_FILES = discover_strategy_files()
_WRAPPERS = [StrategyModuleWrapper(path) for path in _DISCOVERED_FILES]


# ---------------------------------------------------------------------------
# Unit tests (unittest)
# ---------------------------------------------------------------------------

class TestInfrastructure(unittest.TestCase):
    """
    Basic checks: discovery, import, and interface of modules.
    """

    def test_scripts_directory_exists(self):
        """The scripts directory should exist in the repo."""
        self.assertTrue(
            os.path.isdir(SCRIPTS_DIR),
            f"Scripts directory does not exist: {SCRIPTS_DIR}",
        )

    def test_discovery_finds_files(self):
        """We should find at least one strategy file (if repo is populated)."""
        # It's OK if there are zero (for a fresh repo), but we still log.
        # In a real CI use, you could assert >= 1.
        self.assertIsInstance(_DISCOVERED_FILES, list)
        # For debug:
        if not _DISCOVERED_FILES:
            print("WARNING: no Super-trading-bot-*.py files found in scripts/")

    def test_each_module_imports_cleanly(self):
        """Each discovered file should import without throwing an exception."""
        for wrapper in _WRAPPERS:
            with self.subTest(module=wrapper.name):
                try:
                    mod = wrapper.load()
                except Exception as exc:
                    self.fail(f"Failed to import {wrapper.name}: {exc}")
                self.assertIsNotNone(mod, "Imported module is None")


class TestStrategies(unittest.TestCase):
    """
    Run a very small functional test on each strategy module.
    """

    def test_backtest_interface(self):
        """
        For each discovered module:
          - 'backtest' must exist and be callable,
          - calling it with dummy data must return a finite float.
        """
        dummy_prices = generate_dummy_prices()

        for wrapper in _WRAPPERS:
            with self.subTest(module=wrapper.name):
                mod = wrapper.load()

                # Check backtest presence
                if not hasattr(mod, "backtest"):
                    self.skipTest(f"{wrapper.name} has no 'backtest' function")
                backtest = getattr(mod, "backtest")

                self.assertTrue(callable(backtest), "'backtest' must be callable")

                # Try to inspect the function signature and decide how to call it.
                # Many of your Super-trading-bot scripts accept:
                #   - backtest(prices: List[float])
                #   - or backtest(high, low, close)
                # We'll try high/low/close first, then fallback to prices.
                high, low, close = generate_dummy_ohlc()

                result: Optional[float] = None
                try:
                    # Try OHLC style
                    result = backtest(high, low, close)
                except TypeError:
                    # Fallback: close-only
                    result = backtest(dummy_prices)
                except Exception as exc:
                    self.fail(f"{wrapper.name} backtest raised: {exc}")

                # checks on result
                self.assertIsInstance(
                    result, (int, float),
                    f"{wrapper.name} backtest() did not return a number",
                )
                self.assertFalse(
                    math.isnan(float(result)),
                    f"{wrapper.name} backtest() returned NaN",
                )

    def test_generate_signals_length(self):
        """
        If a module provides 'generate_signals', verify that the
        signals array has the same length as the input data.
        """
        dummy_prices = generate_dummy_prices()

        for wrapper in _WRAPPERS:
            with self.subTest(module=wrapper.name):
                mod = wrapper.load()
                if not hasattr(mod, "generate_signals"):
                    self.skipTest(f"{wrapper.name} has no 'generate_signals'")
                gen = getattr(mod, "generate_signals")
                self.assertTrue(callable(gen), "'generate_signals' must be callable")

                try:
                    signals = gen(dummy_prices)
                except Exception as exc:
                    self.fail(f"{wrapper.name} generate_signals raised: {exc}")

                self.assertEqual(
                    len(signals),
                    len(dummy_prices),
                    "signals length must match price series length",
                )


# ---------------------------------------------------------------------------
# Manual runner / pretty report
# ---------------------------------------------------------------------------

def run_manual_report() -> None:
    """
    Run a quick backtest for every discovered strategy and print a table
    in the console. This is not part of the unit tests – it's for you
    to quickly compare strategies.
    """
    if not _WRAPPERS:
        print("No strategy scripts found in:", SCRIPTS_DIR)
        return

    print("\n" + "=" * 72)
    print(" SUPER-TRADING STRATEGY QUICK REPORT")
    print("=" * 72)

    dummy_prices = generate_dummy_prices()
    high, low, close = generate_dummy_ohlc()

    for wrapper in _WRAPPERS:
        mod = wrapper.load()
        backtest = getattr(mod, "backtest", None)
        if backtest is None or not callable(backtest):
            print(f"- {wrapper.name:<40} SKIPPED (no backtest)")
            continue

        try:
            # Try OHLC signature first
            try:
                pnl = backtest(high, low, close)
            except TypeError:
                pnl = backtest(dummy_prices)
        except Exception as exc:
            print(f"- {wrapper.name:<40} ERROR: {exc}")
            continue

        print(f"- {wrapper.name:<40} PnL: {pnl:>12.2f}")

    print("=" * 72)
    print("Report finished.\n")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1) Run unittest suite
    print("Running unittest suite for Super-trading strategies...\n")
    unittest.main(exit=False)

    # 2) Run manual PnL report
    run_manual_report()

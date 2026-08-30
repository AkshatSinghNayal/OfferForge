"""Tests for deployment-safe application startup migrations."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.main import _run_database_migrations


class StartupMigrationTests(unittest.TestCase):
    def test_alembic_is_upgraded_to_head(self) -> None:
        with patch("app.main.command.upgrade") as upgrade:
            _run_database_migrations()
        config, revision = upgrade.call_args.args
        self.assertEqual(revision, "head")
        self.assertTrue(config.config_file_name.endswith("alembic.ini"))


if __name__ == "__main__":
    unittest.main()

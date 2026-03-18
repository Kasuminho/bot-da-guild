import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from services.feature_service import FeatureService

ROOT = Path(__file__).resolve().parents[1]


class FakeStringSaasRepo:
    def get_guild(self, guild_id):
        return (guild_id, "Guild", "pro", "active", None, True, "{}")

    def get_plan(self, plan_id):
        return (plan_id, plan_id, 0, "USD", json.dumps({"dkp_enabled": True}), True)


class SQLiteBackendTests(unittest.TestCase):
    def test_feature_service_parses_json_string(self):
        service = FeatureService(FakeStringSaasRepo())
        self.assertTrue(service.can_use_feature(1, "dkp_enabled"))

    def test_db_boots_with_sqlite_and_seeds_plans(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sqlite_path = Path(tmpdir) / "bot.db"
            env = os.environ.copy()
            env.pop("DATABASE_URL", None)
            env["SQLITE_PATH"] = str(sqlite_path)
            env["DEFAULT_GUILD_ID"] = "123"

            cmd = [
                sys.executable,
                "-c",
                (
                    "import db; "
                    "db.add_player(42, 'mano', 'pt-BR', 99); "
                    "print(db.get_player_language(42)); "
                    "print(db.execute('SELECT COUNT(*) FROM plans', fetchone=True)[0]); "
                    "print(db.execute('SELECT config_json FROM guilds WHERE guild_id = %s', (123,), fetchone=True)[0])"
                ),
            ]
            result = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, check=True)
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            self.assertEqual(lines[0], "pt-BR")
            self.assertEqual(lines[1], "3")
            self.assertIn('loot_mode', lines[2])
            self.assertTrue(sqlite_path.exists())


if __name__ == "__main__":
    unittest.main()

import unittest

from core.context import TenantContext
from services.dkp_service import DKPService
from services.feature_service import FeatureService


class FakeDKPRepo:
    def __init__(self):
        self.rows = []

    def add_transaction(self, guild_id, user_id, amount, reason, created_by_user_id, event_id=None):
        self.rows.append((guild_id, user_id, amount, reason, created_by_user_id, event_id, len(self.rows) + 1))

    def get_balance(self, guild_id, user_id):
        return sum(r[2] for r in self.rows if r[0] == guild_id and r[1] == user_id)

    def get_leaderboard(self, guild_id, limit):
        balances = {}
        for g, u, amt, *_ in self.rows:
            if g != guild_id:
                continue
            balances[u] = balances.get(u, 0) + amt
        return sorted(balances.items(), key=lambda x: (-x[1], x[0]))[:limit]

    def get_history(self, guild_id, user_id, limit):
        rows = [(r[2], r[3], r[4], r[6]) for r in self.rows if r[0] == guild_id and r[1] == user_id]
        return list(reversed(rows))[:limit]

    def list_user_balances(self, guild_id):
        balances = {}
        for g, u, amt, *_ in self.rows:
            if g != guild_id:
                continue
            balances[u] = balances.get(u, 0) + amt
        return list(balances.items())

    def clear_guild(self, guild_id, actor_id):
        for user_id, bal in self.list_user_balances(guild_id):
            if bal:
                self.add_transaction(guild_id, user_id, -bal, "DKP reset", actor_id, "dkp_reset")


class FakeAuditRepo:
    def __init__(self):
        self.logs = []

    def log(self, *args, **kwargs):
        self.logs.append((args, kwargs))


class FakeSaasRepo:
    def __init__(self, features):
        self.features = features

    def get_guild(self, guild_id):
        return (guild_id, "Guild", "pro", "active", None, True, {})

    def get_plan(self, plan_id):
        return (plan_id, plan_id, 0, "USD", self.features, True)


class ServiceTests(unittest.TestCase):
    def test_add_and_balance(self):
        svc = DKPService(FakeDKPRepo(), FakeAuditRepo())
        ctx = TenantContext(guild_id=1, channel_id=10, actor_user_id=100)
        svc.add_points(ctx, 200, 15, "raid")
        self.assertEqual(svc.get_balance(ctx, 200), 15)

    def test_tenant_isolation(self):
        repo = FakeDKPRepo()
        svc = DKPService(repo, FakeAuditRepo())
        svc.add_points(TenantContext(1, 1, 9), 50, 10, "a")
        svc.add_points(TenantContext(2, 1, 9), 50, 99, "b")
        self.assertEqual(svc.get_balance(TenantContext(1, 1, 9), 50), 10)
        self.assertEqual(svc.get_balance(TenantContext(2, 1, 9), 50), 99)

    def test_decay_writes_transactions(self):
        repo = FakeDKPRepo()
        svc = DKPService(repo, FakeAuditRepo())
        ctx = TenantContext(1, 1, 999)
        svc.add_points(ctx, 10, 100, "seed")
        svc.apply_decay(ctx, 10)
        self.assertEqual(svc.get_balance(ctx, 10), 90)

    def test_reset_zeroes_balances(self):
        svc = DKPService(FakeDKPRepo(), FakeAuditRepo())
        ctx = TenantContext(1, 1, 999)
        svc.add_points(ctx, 10, 50, "seed")
        svc.reset(ctx)
        self.assertEqual(svc.get_balance(ctx, 10), 0)

    def test_feature_gate_positive(self):
        fs = FeatureService(FakeSaasRepo({"dkp_enabled": True}))
        self.assertTrue(fs.can_use_feature(1, "dkp_enabled"))


if __name__ == "__main__":
    unittest.main()


class FakeConfigRepo:
    def __init__(self):
        self.store = {}

    def get(self, guild_id):
        return dict(self.store.get(guild_id, {}))

    def set(self, guild_id, key, value):
        cfg = dict(self.store.get(guild_id, {}))
        cfg[key] = value
        self.store[guild_id] = cfg


class LootModeServiceTests(unittest.TestCase):
    def test_default_mode_is_legacy(self):
        from services.guild_config_service import GuildConfigService
        from services.loot_mode_service import LootModeService

        config_service = GuildConfigService(FakeConfigRepo(), FakeAuditRepo())
        mode_service = LootModeService(config_service)
        self.assertEqual(mode_service.get_mode(1), "legacy")

    def test_set_and_get_mode(self):
        from services.guild_config_service import GuildConfigService
        from services.loot_mode_service import LootModeService

        config_service = GuildConfigService(FakeConfigRepo(), FakeAuditRepo())
        mode_service = LootModeService(config_service)
        mode_service.set_mode(1, 999, "dkp")
        self.assertEqual(mode_service.get_mode(1), "dkp")

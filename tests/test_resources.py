"""Wire-shape parity with broadcast-ruby, operation by operation.

Every assertion is method + path + body, because those are what the API sees.
The .json suffixes on subscribers/segments/transactionals are not cosmetic —
they are what the Ruby gem sends, and the coverage report matches on path.
"""

import unittest
from urllib.parse import parse_qs, urlparse

from support import make_client


def path_of(url):
    return urlparse(url).path


def query_of(url):
    return parse_qs(urlparse(url).query)


class TestDiscovery(unittest.TestCase):
    def test_whoami_status_prime(self):
        client, opener, _ = make_client()
        client.discovery.whoami()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/whoami")
        client.discovery.status()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/status")
        client.discovery.prime()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/prime")

    def test_skill_is_raw_text(self):
        client, opener, _ = make_client(
            {"status": 200, "text": "# Skill", "headers": {"content-type": "text/plain; charset=utf-8"}}
        )
        result = client.discovery.skill()
        self.assertIsInstance(result, str)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/skill")

    def test_client_shims(self):
        client, opener, _ = make_client()
        client.whoami()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/whoami")
        client.status()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/status")
        client.prime()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/prime")


class TestSubscribers(unittest.TestCase):
    def test_list_and_find(self):
        client, opener, _ = make_client()
        client.subscribers.list(page=2, tags=["vip", "beta"])
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/subscribers.json")
        self.assertEqual(query_of(opener.last["url"])["tags[]"], ["vip", "beta"])

        client.subscribers.find("a@b.com")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/subscribers/find.json")
        self.assertEqual(query_of(opener.last["url"])["email"], ["a@b.com"])

    def test_create_wraps_under_subscriber(self):
        client, opener, _ = make_client()
        client.subscribers.create(email="a@b.com", first_name="Ada", tags=["vip"])

        self.assertEqual(opener.last["method"], "POST")
        self.assertEqual(
            opener.last["body"], {"subscriber": {"email": "a@b.com", "first_name": "Ada", "tags": ["vip"]}}
        )

    def test_create_lifts_double_opt_in_to_top_level(self):
        client, opener, _ = make_client()
        client.subscribers.create(email="a@b.com", double_opt_in=True, confirmation_template_id=7)

        self.assertEqual(
            opener.last["body"],
            {"subscriber": {"email": "a@b.com"}, "double_opt_in": True, "confirmation_template_id": 7},
        )

    def test_update(self):
        client, opener, _ = make_client()
        client.subscribers.update("a@b.com", first_name="Grace")

        self.assertEqual(opener.last["method"], "PATCH")
        self.assertEqual(opener.last["body"], {"email": "a@b.com", "subscriber": {"first_name": "Grace"}})

    def test_tag_operations(self):
        client, opener, _ = make_client()
        client.subscribers.add_tags("a@b.com", ["vip"])
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/subscribers/add_tag.json")
        self.assertEqual(opener.last["body"], {"email": "a@b.com", "tags": ["vip"]})

        client.subscribers.remove_tags("a@b.com", ["vip"])
        self.assertEqual(opener.last["method"], "DELETE")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/subscribers/remove_tag.json")

    def test_lifecycle_actions(self):
        client, opener, _ = make_client()
        for action in ("activate", "deactivate", "unsubscribe", "resubscribe", "redact"):
            getattr(client.subscribers, action)("a@b.com")
            self.assertEqual(opener.last["method"], "POST", action)
            self.assertEqual(path_of(opener.last["url"]), "/api/v1/subscribers/{}.json".format(action))
            self.assertEqual(opener.last["body"], {"email": "a@b.com"})


class TestBroadcasts(unittest.TestCase):
    def test_crud_unwrapped(self):
        client, opener, _ = make_client()
        client.broadcasts.list()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/broadcasts")

        client.broadcasts.get(5)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/broadcasts/5")

        client.broadcasts.create(subject="Hello")
        self.assertEqual(opener.last["body"], {"subject": "Hello"})

        client.broadcasts.update(5, subject="Edited")
        self.assertEqual(opener.last["method"], "PATCH")
        self.assertEqual(opener.last["body"], {"subject": "Edited"})

        client.broadcasts.delete(5)
        self.assertEqual(opener.last["method"], "DELETE")

    def test_send_schedule_cancel(self):
        client, opener, _ = make_client()
        client.broadcasts.send(5)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/broadcasts/5/send_broadcast")

        client.broadcasts.schedule(5, scheduled_send_at="2026-08-01T09:00:00Z", scheduled_timezone="UTC")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/broadcasts/5/schedule_broadcast")
        self.assertEqual(
            opener.last["body"], {"scheduled_send_at": "2026-08-01T09:00:00Z", "scheduled_timezone": "UTC"}
        )

        client.broadcasts.cancel_schedule(5)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/broadcasts/5/cancel_schedule")

    def test_statistics(self):
        client, opener, _ = make_client()
        client.broadcasts.statistics(5)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/broadcasts/5/statistics")
        client.broadcasts.statistics_timeline(5, interval="hour")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/broadcasts/5/statistics/timeline")
        client.broadcasts.statistics_links(5)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/broadcasts/5/statistics/links")


class TestSequences(unittest.TestCase):
    def test_crud(self):
        client, opener, _ = make_client()
        client.sequences.list()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/sequences")

        client.sequences.get(3)
        self.assertNotIn("include_steps", query_of(opener.last["url"]))

        client.sequences.get(3, include_steps=True)
        self.assertEqual(query_of(opener.last["url"])["include_steps"], ["true"])

        client.sequences.create(name="Onboarding")
        self.assertEqual(opener.last["body"], {"name": "Onboarding"})

        client.sequences.delete(3)
        self.assertEqual(opener.last["method"], "DELETE")

    def test_enrollment(self):
        client, opener, _ = make_client()
        client.sequences.add_subscriber(3, email="a@b.com")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/sequences/3/add_subscriber")

        client.sequences.remove_subscriber(3, "a@b.com")
        self.assertEqual(opener.last["method"], "DELETE")
        self.assertEqual(opener.last["body"], {"email": "a@b.com"})

        client.sequences.list_subscribers(3, page=2)
        self.assertEqual(query_of(opener.last["url"])["page"], ["2"])

    def test_steps(self):
        client, opener, _ = make_client()
        client.sequences.list_steps(3)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/sequences/3/steps")

        client.sequences.get_step(3, 9)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/sequences/3/steps/9")

        client.sequences.create_step(3, subject="Day 1")
        self.assertEqual(opener.last["method"], "POST")

        client.sequences.update_step(3, 9, subject="Day 2")
        self.assertEqual(opener.last["method"], "PATCH")

        client.sequences.move_step(3, 9, 4)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/sequences/3/steps/9/move")
        self.assertEqual(opener.last["body"], {"under_id": 4})

        client.sequences.delete_step(3, 9)
        self.assertEqual(opener.last["method"], "DELETE")


class TestSegmentsTemplatesForms(unittest.TestCase):
    def test_segments(self):
        client, opener, _ = make_client()
        client.segments.list()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/segments.json")

        client.segments.get(2)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/segments/2.json")

        client.segments.create(name="VIPs")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/segments")
        self.assertEqual(opener.last["body"], {"segment": {"name": "VIPs"}})

        client.segments.update(2, name="Renamed")
        self.assertEqual(opener.last["body"], {"segment": {"name": "Renamed"}})

    def test_templates(self):
        client, opener, _ = make_client()
        client.templates.create(label="Welcome", subject="Hi")
        self.assertEqual(opener.last["body"], {"template": {"label": "Welcome", "subject": "Hi"}})

        settings = {"confirmed": {"heading": "You're in", "body": "Thanks."}}
        client.templates.create(label="C", confirmation_page_settings=settings)
        self.assertEqual(opener.last["body"]["template"]["confirmation_page_settings"], settings)

    def test_opt_in_forms(self):
        client, opener, _ = make_client()
        client.opt_in_forms.create(label="Footer")
        self.assertEqual(opener.last["body"], {"opt_in_form": {"label": "Footer"}})

        client.opt_in_forms.analytics(6, start_date="2026-01-01", end_date="2026-02-01")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/opt_in_forms/6/analytics")
        self.assertEqual(query_of(opener.last["url"])["start_date"], ["2026-01-01"])

        client.opt_in_forms.analytics(6)
        self.assertEqual(query_of(opener.last["url"]), {})

        client.opt_in_forms.create_variant(6, name="B", weight=50)
        self.assertEqual(opener.last["body"], {"name": "B", "weight": 50})

        client.opt_in_forms.duplicate(6, label="Copy")
        self.assertEqual(opener.last["body"], {"label": "Copy"})

    def test_analytics_coerces_a_date_object(self):
        from datetime import date

        client, opener, _ = make_client()
        client.opt_in_forms.analytics(6, start_date=date(2026, 1, 1))
        self.assertEqual(query_of(opener.last["url"])["start_date"], ["2026-01-01"])


class TestEmailServers(unittest.TestCase):
    def test_crud_and_actions(self):
        client, opener, _ = make_client()
        client.email_servers.list(limit=10, offset=5)
        self.assertEqual(query_of(opener.last["url"])["limit"], ["10"])

        client.email_servers.create(name="SES")
        self.assertEqual(opener.last["body"], {"email_server": {"name": "SES"}})

        client.email_servers.test_connection(8)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/email_servers/8/test_connection")

        client.email_servers.copy_to_channel(8, 42)
        self.assertEqual(opener.last["body"], {"target_channel_id": 42})

    def test_update_strips_bullet_masked_credentials(self):
        messages = []
        logger = type("L", (), {"warning": lambda self, m: messages.append(m)})()
        client, opener, _ = make_client(logger=logger)

        client.email_servers.update(
            8, name="Renamed", smtp_password="••••••••", aws_secret_access_key="AKIA••••••••WXYZ"
        )

        self.assertEqual(opener.last["body"], {"email_server": {"name": "Renamed"}})
        self.assertEqual(len(messages), 2)

    def test_a_real_credential_is_sent(self):
        client, opener, _ = make_client()
        client.email_servers.update(8, smtp_password="genuinely-new-password")
        self.assertEqual(opener.last["body"], {"email_server": {"smtp_password": "genuinely-new-password"}})

    def test_only_known_credential_fields_are_scrubbed(self):
        client, opener, _ = make_client()
        client.email_servers.update(8, name="••••••••")
        self.assertEqual(opener.last["body"], {"email_server": {"name": "••••••••"}})


class TestWebhookEndpointsAndTransactionals(unittest.TestCase):
    def test_webhook_endpoints(self):
        client, opener, _ = make_client()
        client.webhook_endpoints.create(url="https://x.com/hook")
        self.assertEqual(opener.last["body"], {"webhook_endpoint": {"url": "https://x.com/hook"}})

        client.webhook_endpoints.test(1)
        self.assertEqual(opener.last["body"], {"event_type": "test.webhook"})

        client.webhook_endpoints.test(1, "email.sent")
        self.assertEqual(opener.last["body"], {"event_type": "email.sent"})

        client.webhook_endpoints.deliveries(1, page=2)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/webhook_endpoints/1/deliveries")

    def test_transactional_create_is_flat(self):
        client, opener, _ = make_client()
        client.transactionals.create(to="a@b.com", subject="Receipt", body="<p>T</p>", reply_to="s@b.com")

        self.assertEqual(path_of(opener.last["url"]), "/api/v1/transactionals.json")
        self.assertEqual(
            opener.last["body"],
            {"to": "a@b.com", "subject": "Receipt", "body": "<p>T</p>", "reply_to": "s@b.com"},
        )

    def test_omits_unprovided_keys(self):
        client, opener, _ = make_client()
        client.transactionals.create(to="a@b.com", subject="Hi", body="x")
        self.assertEqual(sorted(opener.last["body"].keys()), ["body", "subject", "to"])

    def test_idempotency_key_is_a_header_not_a_body_field(self):
        client, opener, _ = make_client()
        client.transactionals.create(to="a@b.com", subject="S", body="B", idempotency_key="order-42")

        self.assertEqual(opener.last["headers"]["idempotency-key"], "order-42")
        self.assertNotIn("idempotency_key", opener.last["body"])

    def test_blank_idempotency_key_sends_no_header(self):
        client, opener, _ = make_client()
        client.transactionals.create(to="a@b.com", subject="S", body="B", idempotency_key="   ")
        self.assertNotIn("idempotency-key", opener.last["headers"])

    def test_rejects_an_over_long_idempotency_key_before_sending(self):
        client, opener, _ = make_client()
        with self.assertRaises(ValueError) as ctx:
            client.transactionals.create(to="a@b.com", subject="S", body="B", idempotency_key="x" * 256)
        self.assertIn("255 characters or fewer", str(ctx.exception))
        self.assertEqual(len(opener.calls), 0)

    def test_accepts_exactly_255(self):
        client, opener, _ = make_client()
        client.transactionals.create(to="a@b.com", subject="S", body="B", idempotency_key="x" * 255)
        self.assertEqual(len(opener.last["headers"]["idempotency-key"]), 255)

    def test_get_transactional(self):
        client, opener, _ = make_client()
        client.transactionals.get(11)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/transactionals/11.json")

    def test_send_email_shim(self):
        client, opener, _ = make_client()
        client.send_email(to="a@b.com", subject="S", body="B")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/transactionals.json")


class TestAutopilots(unittest.TestCase):
    def test_crud(self):
        client, opener, _ = make_client()
        client.autopilots.list()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/autopilots")

        client.autopilots.create(name="Weekly", ai_model="openai/gpt-4o")
        self.assertEqual(opener.last["body"], {"autopilot": {"name": "Weekly", "ai_model": "openai/gpt-4o"}})

        client.autopilots.update(2, copies_to_generate=5)
        self.assertEqual(opener.last["body"], {"autopilot": {"copies_to_generate": 5}})

        client.autopilots.delete(2)
        self.assertEqual(opener.last["method"], "DELETE")

    def test_lifecycle_and_runs(self):
        client, opener, _ = make_client()
        for action in ("activate", "pause", "deactivate"):
            getattr(client.autopilots, action)(2)
            self.assertEqual(path_of(opener.last["url"]), "/api/v1/autopilots/2/{}".format(action))

        client.autopilots.trigger_run(2)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/autopilots/2/trigger_run")

        client.autopilots.runs(2, limit=10)
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/autopilots/2/runs")

    def test_update_strips_a_masked_key(self):
        messages = []
        logger = type("L", (), {"warning": lambda self, m: messages.append(m)})()
        client, opener, _ = make_client(logger=logger)

        client.autopilots.update(2, openrouter_api_key="••••••••", ai_model="openai/gpt-4o")
        self.assertEqual(opener.last["body"], {"autopilot": {"ai_model": "openai/gpt-4o"}})
        self.assertEqual(len(messages), 1)

    def test_a_real_key_is_sent(self):
        client, opener, _ = make_client()
        client.autopilots.update(2, openrouter_api_key="sk-or-v1-realkey")
        self.assertEqual(opener.last["body"], {"autopilot": {"openrouter_api_key": "sk-or-v1-realkey"}})


class TestMigration(unittest.TestCase):
    COLLECTIONS = (
        "channels", "subscribers", "templates", "segments", "sequences", "email_servers",
        "opt_in_forms", "broadcasts", "outbound_receipts", "webhook_endpoints", "tokens",
        "suppressions", "tags", "users", "link_redirects", "link_clicks",
        "subscriber_histories", "file_assets",
    )

    def test_all_eighteen_collections(self):
        client, opener, _ = make_client({"body": {"data": [], "pagination": {"has_more": False}}})
        for collection in self.COLLECTIONS:
            getattr(client.migration, collection)(limit=10)
            self.assertEqual(
                path_of(opener.last["url"]), "/api/migration/v1/{}".format(collection), collection
            )

    def test_manifest(self):
        client, opener, _ = make_client()
        client.migration.manifest(days_history=30)
        self.assertEqual(path_of(opener.last["url"]), "/api/migration/v1/manifest")
        self.assertEqual(query_of(opener.last["url"])["days_history"], ["30"])

    def test_download_file_asset_returns_bytes(self):
        client, _, _ = make_client(
            {"status": 200, "text": b"\x89PNG", "headers": {"content-type": "image/png"}}
        )
        self.assertEqual(client.migration.download_file_asset(3), b"\x89PNG")

    def test_each_record_pages_until_has_more_is_false(self):
        client, opener, _ = make_client(
            [
                {"body": {"data": [{"id": 1}, {"id": 2}], "pagination": {"has_more": True, "limit": 2}}},
                {"body": {"data": [{"id": 3}], "pagination": {"has_more": False, "limit": 2}}},
            ]
        )
        seen = [r["id"] for r in client.migration.each_record("subscribers", limit=2)]

        self.assertEqual(seen, [1, 2, 3])
        self.assertEqual(query_of(opener.calls[0]["url"])["offset"], ["0"])
        self.assertEqual(query_of(opener.calls[1]["url"])["offset"], ["2"])

    def test_each_record_advances_by_the_server_reported_limit(self):
        # The server clamps limit to 250; advancing by the requested 1000 would skip records.
        client, opener, _ = make_client(
            [
                {"body": {"data": [{"id": i} for i in range(250)], "pagination": {"has_more": True, "limit": 250}}},
                {"body": {"data": [{"id": 250}], "pagination": {"has_more": False, "limit": 250}}},
            ]
        )
        seen = list(client.migration.each_record("subscribers", limit=1000))

        self.assertEqual(len(seen), 251)
        self.assertEqual(query_of(opener.calls[1]["url"])["offset"], ["250"])

    def test_each_record_stops_on_a_zero_advance(self):
        client, opener, _ = make_client({"body": {"data": [{"id": 1}], "pagination": {"has_more": True, "limit": 0}}})
        seen = list(client.migration.each_record("subscribers"))

        self.assertEqual(len(seen), 1)
        self.assertEqual(len(opener.calls), 1)


class TestChannelScoping(unittest.TestCase):
    def test_injected_into_query_params(self):
        client, opener, _ = make_client(broadcast_channel_id=42)
        client.migration.subscribers()
        self.assertEqual(query_of(opener.last["url"])["broadcast_channel_id"], ["42"])

    def test_injected_into_bodies(self):
        client, opener, _ = make_client(broadcast_channel_id=42)
        client.broadcasts.create(subject="Hi")
        self.assertEqual(opener.last["body"], {"subject": "Hi", "broadcast_channel_id": 42})

    def test_explicit_wins(self):
        client, opener, _ = make_client(broadcast_channel_id=42)
        client.migration.subscribers(broadcast_channel_id=7)
        self.assertEqual(query_of(opener.last["url"])["broadcast_channel_id"], ["7"])

    def test_with_channel_scopes_only_its_block(self):
        client, opener, _ = make_client()
        with client.with_channel(99):
            client.migration.subscribers()
        self.assertEqual(query_of(opener.last["url"])["broadcast_channel_id"], ["99"])

        client.migration.subscribers()
        self.assertNotIn("broadcast_channel_id", query_of(opener.last["url"]))

    def test_with_channel_restores_on_exception(self):
        client, opener, _ = make_client(broadcast_channel_id=42)
        try:
            with client.with_channel(99):
                raise RuntimeError("boom")
        except RuntimeError:
            pass

        client.migration.subscribers()
        self.assertEqual(query_of(opener.last["url"])["broadcast_channel_id"], ["42"])


class TestSuppressions(unittest.TestCase):
    def test_channel_list_add_remove(self):
        client, opener, _ = make_client()

        client.suppressions.list(page=2, email="example.com")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/suppressions.json")
        self.assertEqual(query_of(opener.last["url"])["page"], ["2"])
        self.assertEqual(query_of(opener.last["url"])["email"], ["example.com"])

        client.suppressions.add("blocked@example.com")
        self.assertEqual(opener.last["method"], "POST")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/suppressions.json")
        self.assertEqual(opener.last["body"], {"email": "blocked@example.com"})

        client.suppressions.remove("blocked@example.com")
        self.assertEqual(opener.last["method"], "DELETE")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/suppressions.json")
        self.assertEqual(opener.last["body"], {"email": "blocked@example.com"})

    def test_channel_bulk(self):
        client, opener, _ = make_client()

        client.suppressions.bulk_add(["a@example.com", "b@example.com"])
        self.assertEqual(opener.last["method"], "POST")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/suppressions/bulk.json")
        self.assertEqual(opener.last["body"], {"emails": ["a@example.com", "b@example.com"]})

        client.suppressions.bulk_remove(["a@example.com"])
        self.assertEqual(opener.last["method"], "DELETE")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/suppressions/bulk.json")
        self.assertEqual(opener.last["body"], {"emails": ["a@example.com"]})

    def test_check(self):
        client, opener, _ = make_client(
            {"body": {"email": "blocked@example.com", "suppressed": True, "scope": "global"}}
        )

        result = client.suppressions.check("blocked@example.com")
        self.assertEqual(opener.last["method"], "GET")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/suppressions/check.json")
        self.assertEqual(query_of(opener.last["url"])["email"], ["blocked@example.com"])
        self.assertTrue(result["suppressed"])
        self.assertEqual(result["scope"], "global")

    def test_global_list_add_remove_bulk(self):
        client, opener, _ = make_client()

        client.global_suppressions.list()
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/global_suppressions.json")

        client.global_suppressions.add("blocked@example.com")
        self.assertEqual(opener.last["method"], "POST")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/global_suppressions.json")
        self.assertEqual(opener.last["body"], {"email": "blocked@example.com"})

        client.global_suppressions.remove("blocked@example.com")
        self.assertEqual(opener.last["method"], "DELETE")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/global_suppressions.json")

        client.global_suppressions.bulk_add(["a@example.com"])
        self.assertEqual(opener.last["method"], "POST")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/global_suppressions/bulk.json")

        client.global_suppressions.bulk_remove(["a@example.com"])
        self.assertEqual(opener.last["method"], "DELETE")
        self.assertEqual(path_of(opener.last["url"]), "/api/v1/global_suppressions/bulk.json")
        self.assertEqual(opener.last["body"], {"emails": ["a@example.com"]})

    def test_global_has_no_check(self):
        client, _, _ = make_client()
        self.assertFalse(hasattr(client.global_suppressions, "check"))


if __name__ == "__main__":
    unittest.main()

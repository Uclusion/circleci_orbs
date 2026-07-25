import unittest

from scripts.cleanup_test_users_utils import (
    get_capability_cleanup_payloads,
    recover_orphan_capabilities,
)


class RecoverOrphanCapabilitiesTest(unittest.TestCase):

    def setUp(self):
        self.calls = []
        self.orphan_market_ids = ['market-a', 'market-b']
        self.orphan_capability_keys = [
            ('user-1', 'market_market-a'),
            ('user-2', 'market_market-b'),
        ]

    def wait_for_cleanup(self, market_ids, capability_keys):
        self.calls.append(('wait', market_ids, capability_keys))

    def invoke_cleanup(self, payload):
        self.calls.append(('invoke', payload))

    def delete_orphan_versions(self, market_ids):
        self.calls.append(('delete_versions', list(market_ids)))

    def test_defer_makes_no_calls_even_with_orphans(self):
        recover_orphan_capabilities(
            self.orphan_market_ids,
            self.orphan_capability_keys,
            self.wait_for_cleanup,
            self.invoke_cleanup,
            delete_orphan_versions=self.delete_orphan_versions,
            defer=True
        )

        self.assertEqual(self.calls, [])

    def test_no_orphans_makes_no_calls(self):
        recover_orphan_capabilities(
            [],
            [],
            self.wait_for_cleanup,
            self.invoke_cleanup,
            delete_orphan_versions=self.delete_orphan_versions
        )

        self.assertEqual(self.calls, [])

    def test_recovery_orders_versions_waits_and_invokes(self):
        recover_orphan_capabilities(
            self.orphan_market_ids,
            self.orphan_capability_keys,
            self.wait_for_cleanup,
            self.invoke_cleanup,
            delete_orphan_versions=self.delete_orphan_versions
        )

        self.assertEqual(
            self.calls,
            [
                ('delete_versions', ['market-a', 'market-b']),
                ('wait', {'market-a', 'market-b'}, set()),
                ('invoke', {'market_id_list': ['market-a', 'market-b']}),
                (
                    'wait',
                    set(),
                    {
                        ('user-1', 'market_market-a'),
                        ('user-2', 'market_market-b'),
                    }
                ),
            ]
        )


class CapabilityCleanupPayloadTest(unittest.TestCase):

    def test_payloads_are_single_typed_and_chunked(self):
        keys = [
            ('user-1', 'group_g1'),
            ('user-1', 'market_m1'),
            ('user-2', 'investible_i1'),
        ]

        payloads = get_capability_cleanup_payloads(keys, chunk_size=1)

        self.assertEqual(
            payloads,
            [
                {'group_id_list': ['g1']},
                {'investible_id_list': ['i1']},
                {'market_id_list': ['m1']},
            ]
        )

    def test_rejects_unsupported_capability_key(self):
        with self.assertRaisesRegex(RuntimeError, 'Unsupported orphan'):
            get_capability_cleanup_payloads([('user-1', 'account')])

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from utils import git_utils
from utils.constants import rest_api_backend_repos


class DeploymentOrderingTests(unittest.TestCase):
    def test_markets_is_first_backend_release(self):
        self.assertEqual(
            [
                'uclusion_markets',
                'uclusion_async',
                'uclusion_investible_api',
            ],
            rest_api_backend_repos[:3],
        )

    def test_waits_for_matching_release_workflow_success(self):
        created_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
        queued = SimpleNamespace(
            conclusion=None,
            created_at=created_at,
            display_title='stage_backend.v1',
            head_branch='master',
            html_url='https://example.test/queued',
            status='queued',
        )
        succeeded = SimpleNamespace(
            conclusion='success',
            created_at=created_at,
            display_title='stage_backend.v1',
            head_branch='master',
            html_url='https://example.test/succeeded',
            status='completed',
        )
        workflow = mock.Mock()
        workflow.get_runs.side_effect = [[queued], [succeeded]]
        repo = mock.Mock(name='repo')
        repo.name = 'uclusion_markets'
        repo.get_workflow.return_value = workflow

        with (
            mock.patch.object(
                git_utils.time,
                'monotonic',
                side_effect=[0, 1],
            ),
            mock.patch.object(git_utils.time, 'sleep') as sleep,
        ):
            git_utils.wait_for_release_deployment(
                repo,
                'stage_backend.v1',
                'markets-sha',
                created_at,
                timeout_seconds=60,
                poll_seconds=2,
            )

        repo.get_workflow.assert_called_once_with('stage.yml')
        self.assertEqual(
            [
                mock.call(event='release', head_sha='markets-sha'),
                mock.call(event='release', head_sha='markets-sha'),
            ],
            workflow.get_runs.call_args_list,
        )
        sleep.assert_called_once_with(2)

    def test_failed_markets_deployment_stops_release_sequence(self):
        created_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
        failed = SimpleNamespace(
            conclusion='failure',
            created_at=created_at,
            display_title='production_backend.v1',
            head_branch='master',
            html_url='https://example.test/failed',
            status='completed',
        )
        workflow = mock.Mock()
        workflow.get_runs.return_value = [failed]
        repo = mock.Mock(name='repo')
        repo.name = 'uclusion_markets'
        repo.get_workflow.return_value = workflow

        with self.assertRaisesRegex(
            RuntimeError,
            'finished with failure',
        ):
            git_utils.wait_for_release_deployment(
                repo,
                'production_backend.v1',
                'markets-sha',
                created_at,
            )

    def test_same_sha_run_for_another_tag_does_not_unlock_release(self):
        created_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
        wrong_tag = SimpleNamespace(
            conclusion='success',
            created_at=created_at,
            display_title='stage_backend.other',
            head_branch='master',
            html_url='https://example.test/wrong-tag',
            status='completed',
        )
        exact_tag = SimpleNamespace(
            conclusion='success',
            created_at=created_at,
            display_title='stage_backend.v1',
            head_branch='master',
            html_url='https://example.test/exact-tag',
            status='completed',
        )
        workflow = mock.Mock()
        workflow.get_runs.side_effect = [
            [wrong_tag],
            [wrong_tag, exact_tag],
        ]
        repo = mock.Mock(name='repo')
        repo.name = 'uclusion_markets'
        repo.get_workflow.return_value = workflow

        with (
            mock.patch.object(
                git_utils.time,
                'monotonic',
                side_effect=[0, 1],
            ),
            mock.patch.object(git_utils.time, 'sleep') as sleep,
        ):
            git_utils.wait_for_release_deployment(
                repo,
                'stage_backend.v1',
                'shared-sha',
                created_at,
                timeout_seconds=60,
                poll_seconds=2,
            )

        self.assertEqual(workflow.get_runs.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_aggregate_release_waits_before_publishing_consumers(self):
        created_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
        repositories = {}
        for name in ('uclusion_markets', 'uclusion_async'):
            repo = mock.Mock()
            repo.name = name
            repo.get_git_ref.return_value = SimpleNamespace(
                object=SimpleNamespace(sha=f'{name}-sha')
            )
            repositories[name] = repo
        github = mock.Mock()
        github.get_repo.side_effect = (
            lambda full_name: repositories[full_name.split('/')[-1]]
        )
        events = []

        def create_release(repo, *_args):
            events.append(('release', repo.name))
            return SimpleNamespace(created_at=created_at)

        def wait_for_deployment(repo, *_args):
            events.append(('wait', repo.name))

        with (
            mock.patch.object(
                git_utils,
                'rest_api_backend_repos',
                ['uclusion_markets', 'uclusion_async'],
            ),
            mock.patch.object(
                git_utils,
                'create_tag_and_release',
                side_effect=create_release,
            ),
            mock.patch.object(
                git_utils,
                'wait_for_release_deployment',
                side_effect=wait_for_deployment,
            ),
        ):
            git_utils.release_head(
                github,
                'stage_backend.v1',
                [],
            )

        self.assertEqual(
            [
                ('release', 'uclusion_markets'),
                ('wait', 'uclusion_markets'),
                ('release', 'uclusion_async'),
            ],
            events,
        )

    def test_resumed_release_waits_for_matching_prebuilt_markets(self):
        created_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
        markets = mock.Mock()
        markets.name = 'uclusion_markets'
        markets.get_git_ref.return_value = SimpleNamespace(
            object=SimpleNamespace(sha='markets-sha')
        )
        async_repo = mock.Mock()
        async_repo.name = 'uclusion_async'
        async_repo.get_git_ref.return_value = SimpleNamespace(
            object=SimpleNamespace(sha='new-async-sha')
        )
        github = mock.Mock()
        github.get_repo.side_effect = (
            lambda full_name: {
                'uclusion_markets': markets,
                'uclusion_async': async_repo,
            }[full_name.split('/')[-1]]
        )
        prebuilt_markets = SimpleNamespace(
            created_at=created_at,
            tag_name='dev_backend.previous',
        )
        events = []

        def get_release_sha(repo, _release):
            self.assertIs(repo, markets)
            return 'markets-sha'

        def wait_for_deployment(repo, tag_name, *_args):
            events.append(('wait', repo.name, tag_name))

        def create_release(repo, *_args):
            events.append(('release', repo.name))
            return SimpleNamespace(created_at=created_at)

        with (
            mock.patch.object(
                git_utils,
                'rest_api_backend_repos',
                ['uclusion_markets', 'uclusion_async'],
            ),
            mock.patch.object(
                git_utils,
                'get_commit_sha_for_release',
                side_effect=get_release_sha,
            ),
            mock.patch.object(
                git_utils,
                'wait_for_release_deployment',
                side_effect=wait_for_deployment,
            ),
            mock.patch.object(
                git_utils,
                'create_tag_and_release',
                side_effect=create_release,
            ),
        ):
            git_utils.release_head(
                github,
                'dev_backend.next',
                [[markets, prebuilt_markets]],
            )

        self.assertEqual(
            [
                ('wait', 'uclusion_markets', 'dev_backend.previous'),
                ('release', 'uclusion_async'),
            ],
            events,
        )

    def test_clone_release_waits_for_markets_before_cloning_consumers(self):
        created_at = datetime(2026, 7, 30, tzinfo=timezone.utc)
        markets = mock.Mock()
        markets.name = 'uclusion_markets'
        async_repo = mock.Mock()
        async_repo.name = 'uclusion_async'
        candidates = [
            [
                markets,
                SimpleNamespace(tag_name='stage_backend.markets'),
            ],
            [
                async_repo,
                SimpleNamespace(tag_name='stage_backend.async'),
            ],
        ]
        events = []

        def clone_release(repo, _release, _dest_tag):
            events.append(('clone', repo.name))
            return SimpleNamespace(created_at=created_at)

        def wait_for_deployment(repo, *_args):
            events.append(('wait', repo.name))

        with (
            mock.patch.object(
                git_utils,
                'get_latest_releases_with_prefix',
                return_value=candidates,
            ),
            mock.patch.object(
                git_utils,
                'clone_release',
                side_effect=clone_release,
            ),
            mock.patch.object(
                git_utils,
                'get_commit_sha_for_release',
                return_value='markets-sha',
            ),
            mock.patch.object(
                git_utils,
                'wait_for_release_deployment',
                side_effect=wait_for_deployment,
            ),
        ):
            git_utils.clone_latest_releases_with_prefix(
                mock.Mock(),
                'stage_backend',
                'production_backend.v1',
            )

        self.assertEqual(
            [
                ('clone', 'uclusion_markets'),
                ('wait', 'uclusion_markets'),
                ('clone', 'uclusion_async'),
            ],
            events,
        )


if __name__ == '__main__':
    unittest.main()

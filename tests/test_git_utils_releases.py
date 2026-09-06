import unittest
from types import SimpleNamespace
from unittest import mock

from utils import git_utils


class BackendReleaseTests(unittest.TestCase):
    def setUp(self):
        self.repositories = {}
        for name in ('uclusion_markets', 'uclusion_async', 'uclusion_common'):
            repo = mock.Mock()
            repo.name = name
            repo.get_git_ref.return_value = SimpleNamespace(
                object=SimpleNamespace(sha=f'{name}-sha', type='commit')
            )
            repo.get_workflow.side_effect = AssertionError(
                'Release publication must not depend on deployment workflow access'
            )
            self.repositories[name] = repo
        self.github = mock.Mock()
        self.github.get_repo.side_effect = (
            lambda name: self.repositories[name.split('/')[-1]]
        )
        self.repo_list = mock.patch.object(
            git_utils, 'rest_api_backend_repos', list(self.repositories)
        )
        self.repo_list.start()
        self.addCleanup(self.repo_list.stop)

    def test_publishes_all_changed_heads_without_waiting_for_deployment(self):
        git_utils.release_head(self.github, 'dev_backend.next', [])

        for name, repo in self.repositories.items():
            repo.create_git_tag_and_release.assert_called_once_with(
                'dev_backend.next', 'Head Build', 'dev_backend.next',
                'Head', f'{name}-sha', 'commit'
            )

    def test_unchanged_markets_does_not_block_other_releases(self):
        markets = self.repositories['uclusion_markets']
        previous = SimpleNamespace(tag_name='dev_backend.previous')

        git_utils.release_head(
            self.github, 'dev_backend.next', [[markets, previous]]
        )

        markets.create_git_tag_and_release.assert_not_called()
        self.repositories['uclusion_async'].create_git_tag_and_release.assert_called_once()

    def test_layer_refresh_releases_unchanged_backends_but_not_layer_sources(self):
        previous = SimpleNamespace(tag_name='dev_backend.previous')
        prebuilt = [[repo, previous] for repo in self.repositories.values()]

        git_utils.release_head(
            self.github, 'dev_backend.next', prebuilt, layers_changed=True
        )

        for name in ('uclusion_markets', 'uclusion_async'):
            self.repositories[name].create_git_tag_and_release.assert_called_once_with(
                'dev_backend.next', 'Layer refresh', 'dev_backend.next',
                'Layer refresh', f'{name}-sha', 'commit'
            )
        self.repositories['uclusion_common'].create_git_tag_and_release.assert_not_called()

    def test_promotes_every_release_without_waiting_for_deployment(self):
        previous = SimpleNamespace(tag_name='stage_blessed.previous')
        candidates = [[repo, previous] for repo in self.repositories.values()]
        with mock.patch.object(
            git_utils, 'get_latest_releases_with_prefix', return_value=candidates
        ):
            result = git_utils.clone_latest_releases_with_prefix(
                self.github, 'stage_blessed', 'stage_backend.next'
            )

        self.assertEqual(
            [[name, 'stage_blessed.previous', 'stage_backend.next']
             for name in self.repositories],
            result,
        )
        for name, repo in self.repositories.items():
            repo.create_git_tag_and_release.assert_called_once_with(
                'stage_backend.next', 'Blessed build tag', 'stage_backend.next',
                'Blessed', f'{name}-sha', 'commit'
            )


if __name__ == '__main__':
    unittest.main()

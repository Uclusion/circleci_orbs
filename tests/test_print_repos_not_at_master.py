import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

from scripts import print_repos_not_at_master as report


def ref(sha):
    return SimpleNamespace(object=SimpleNamespace(sha=sha, type='commit'))


def run(branch, sha, conclusion):
    return SimpleNamespace(head_branch=branch, head_sha=sha, conclusion=conclusion)


def release(tag):
    return SimpleNamespace(
        tag_name=tag,
        created_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
    )


class RepoNotAtMasterTests(unittest.TestCase):
    def repo(self, name, master, runs=None, releases=None):
        repo = mock.Mock()
        repo.name = name
        def git_ref(path):
            if path == 'heads/master':
                return ref(master)
            if path.startswith('tags/'):
                return ref('deployed-sha')
            raise AssertionError(path)

        repo.get_git_ref.side_effect = git_ref
        workflow = mock.Mock()
        workflow.get_runs.return_value = runs or []
        repo.get_workflow.return_value = workflow
        repo.get_releases.return_value = releases or []
        repo.compare.return_value = SimpleNamespace(status='ahead', ahead_by=2, behind_by=0)
        return repo

    def test_successful_stage_deploy_at_master_is_current(self):
        repo = self.repo('uclusion_markets', 'abc', [
            run('dev_backend.v1', 'other', 'success'),
            run('stage_backend.v9', 'abc', 'success'),
        ])

        result = report.inspect_repo(repo, 'stage')

        self.assertEqual('current', result['status'])
        self.assertEqual('stage_backend.v9', result['deployed_ref'])
        repo.compare.assert_not_called()
        repo.get_workflow.return_value.get_runs.assert_called_once_with()

    def test_failed_newer_deploy_keeps_the_last_success(self):
        repo = self.repo('uclusion_markets', 'master-sha', [
            run('stage_blessed_newer', 'master-sha', 'success'),
            run('stage_backend.v2', 'master-sha', 'failure'),
            run('stage_backend.v1', 'deployed-sha', 'success'),
        ])

        result = report.inspect_repo(repo, 'stage')

        self.assertEqual('ahead', result['status'])
        self.assertEqual('deployed-sha', result['deployed_sha'])
        self.assertEqual(2, result['ahead_by'])
        self.assertIn('latest stage_backend run failure: stage_backend.v2', result['note'])
        repo.compare.assert_called_once_with('deployed-sha', 'master-sha')

    def test_no_successful_deploy_is_reported(self):
        repo = self.repo('uclusion_user_api', 'master-sha', [
            run('stage_backend.v2', 'master-sha', 'failure'),
        ])

        result = report.inspect_repo(repo, 'stage')

        self.assertEqual('not_deployed', result['status'])
        self.assertIsNone(result['deployed_sha'])

    def test_layer_repo_uses_the_environment_release(self):
        repo = self.repo(
            'uclusion_common', 'master-sha',
            releases=[release('dev_backend.v1'), release('stage_backend.v3')],
        )
        result = report.inspect_repo(repo, 'stage')

        self.assertEqual('ahead', result['status'])
        self.assertEqual('deployed-sha', result['deployed_sha'])
        self.assertEqual('stage_backend.v3', result['deployed_ref'])
        repo.get_workflow.assert_not_called()

    def test_production_ui_uses_its_workflow_file(self):
        self.assertEqual('production.yml', report.workflow_file('uclusion_web_ui', 'production'))
        self.assertEqual('prod.yml', report.workflow_file('uclusion_markets', 'production'))
        self.assertIsNone(report.workflow_file('common_lambda_dependencies', 'production'))


if __name__ == '__main__':
    unittest.main()

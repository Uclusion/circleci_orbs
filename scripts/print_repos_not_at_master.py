import logging
import os
import subprocess
import sys
import getopt
from github import Auth, Github, UnknownObjectException
from utils.constants import (
    env_to_build_tag_prefix,
    layer_source_repos,
    rest_api_backend_repos,
)
from utils.git_utils import get_commit_sha_for_release

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()

UI_REPO = 'uclusion_web_ui'
WORKFLOW_FILES = {
    'stage': 'stage.yml',
    'production': 'prod.yml',
}
UI_WORKFLOW_FILES = {
    'stage': 'stage.yml',
    'production': 'production.yml',
}


def repos_for_env():
    return list(rest_api_backend_repos) + [UI_REPO]


def workflow_file(repo_name, env_name):
    if repo_name in layer_source_repos:
        return None
    files = UI_WORKFLOW_FILES if repo_name == UI_REPO else WORKFLOW_FILES
    return files[env_name]


def resolve_github_token(github_token):
    if github_token:
        return github_token
    for key in ('GITHUB_TOKEN', 'GH_TOKEN'):
        value = os.environ.get(key)
        if value:
            return value
    try:
        completed = subprocess.run(
            ['gh', 'auth', 'token'], check=True, capture_output=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    token = completed.stdout.strip()
    return token or None


def latest_release_with_prefix(repo, prefix):
    for release in repo.get_releases():
        if release.tag_name.startswith(prefix):
            return release
    return None


def _relation(repo, deployed_sha, master_sha):
    if deployed_sha == master_sha:
        return 'current', 0, 0
    comparison = repo.compare(deployed_sha, master_sha)
    return comparison.status, comparison.ahead_by, comparison.behind_by


def _result(repo_name, master_sha, deployed_sha, deployed_ref, status, ahead_by, behind_by, note):
    return {
        'repo': repo_name,
        'master_sha': master_sha,
        'deployed_sha': deployed_sha,
        'deployed_ref': deployed_ref,
        'status': status,
        'ahead_by': ahead_by,
        'behind_by': behind_by,
        'note': note,
    }


def inspect_workflow_repo(repo, env_name, master_sha, filename):
    prefix = env_to_build_tag_prefix[env_name]
    try:
        workflow = repo.get_workflow(filename)
    except UnknownObjectException:
        return _result(
            repo.name, master_sha, None, None, 'not_deployed', 0, 0,
            'missing workflow ' + filename,
        )
    successful = None
    latest_attempt = None
    # Do not pass event='release'. That filter omits the newest runs.
    for run in workflow.get_runs():
        if not (run.head_branch or '').startswith(prefix):
            continue
        if latest_attempt is None:
            latest_attempt = run
        if run.conclusion == 'success':
            successful = run
            break
    note = None
    if latest_attempt is not None and latest_attempt.conclusion != 'success':
        state = latest_attempt.conclusion or 'in progress'
        note = f'latest {prefix} run {state}: {latest_attempt.head_branch}'
    if successful is None:
        return _result(repo.name, master_sha, None, None, 'not_deployed', 0, 0, note)
    status, ahead_by, behind_by = _relation(repo, successful.head_sha, master_sha)
    return _result(
        repo.name, master_sha, successful.head_sha, successful.head_branch,
        status, ahead_by, behind_by, note,
    )


def inspect_layer_repo(repo, env_name, master_sha):
    prefix = env_to_build_tag_prefix[env_name]
    release = latest_release_with_prefix(repo, prefix)
    if release is None:
        return _result(
            repo.name, master_sha, None, None, 'not_deployed', 0, 0,
            'no ' + prefix + ' release',
        )
    deployed_sha = get_commit_sha_for_release(repo, release)
    if not deployed_sha:
        return _result(
            repo.name, master_sha, None, release.tag_name, 'not_deployed', 0, 0,
            'release tag does not resolve',
        )
    status, ahead_by, behind_by = _relation(repo, deployed_sha, master_sha)
    return _result(
        repo.name, master_sha, deployed_sha, release.tag_name,
        status, ahead_by, behind_by, None,
    )


def inspect_repo(repo, env_name):
    master_sha = repo.get_git_ref('heads/master').object.sha
    filename = workflow_file(repo.name, env_name)
    if filename is None:
        return inspect_layer_repo(repo, env_name, master_sha)
    return inspect_workflow_repo(repo, env_name, master_sha, filename)


def short_sha(sha):
    if not sha:
        return '-'
    return sha[:12]


def display_status(result):
    if result['status'] == 'current':
        return 'current'
    if result['status'] == 'not_deployed':
        return 'missing'
    return 'not at master'


def describe(result):
    name = result['repo']
    if result['status'] == 'not_deployed':
        detail = 'no successful deploy'
    elif result['status'] == 'current':
        detail = f"at master {short_sha(result['master_sha'])} ({result['deployed_ref']})"
    else:
        pieces = []
        if result['ahead_by']:
            commits = 'commit' if result['ahead_by'] == 1 else 'commits'
            pieces.append(f"master is {result['ahead_by']} {commits} ahead")
        if result['behind_by']:
            commits = 'commit' if result['behind_by'] == 1 else 'commits'
            pieces.append(f"deployed is {result['behind_by']} {commits} ahead of master")
        relation = ', '.join(pieces) if pieces else result['status']
        detail = (
            f"deployed {short_sha(result['deployed_sha'])} ({result['deployed_ref']})"
            f"  master {short_sha(result['master_sha'])}  {relation}"
        )
    line = f"{display_status(result):14} {name:28} {detail}"
    if result['note']:
        line += ' [' + result['note'] + ']'
    return line


def report(github, env_name):
    results = []
    for repo_name in repos_for_env():
        repo = github.get_repo(f'Uclusion/{repo_name}')
        results.append(inspect_repo(repo, env_name))
    differing = [item for item in results if item['status'] != 'current']
    lines = [describe(item) for item in results]
    if differing:
        names = ', '.join(item['repo'] for item in differing)
        noun = 'repo' if len(differing) == 1 else 'repos'
        lines.append(f'{len(differing)} {noun} on {env_name} are not at master: {names}')
    else:
        lines.append(f'All {len(results)} repos on {env_name} are at master.')
    return results, '\n'.join(lines)


def main(argv):
    usage = 'python -m scripts.print_repos_not_at_master -e stage|production [-a github_token]'
    try:
        opts, args = getopt.getopt(argv, 'he:a:', ['env=', 'gtoken='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    env_name = None
    github_token = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-e', '--env'):
            env_name = arg
        elif opt in ('-a', '--gtoken'):
            github_token = arg
    if env_name not in WORKFLOW_FILES:
        logger.info(usage)
        sys.exit(2)
    github_token = resolve_github_token(github_token)
    if github_token is None:
        logger.info(usage)
        sys.exit(2)
    github = Github(auth=Auth.Token(github_token))
    results, text = report(github, env_name)
    print(text)
    if any(item['status'] != 'current' for item in results):
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])

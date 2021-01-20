import logging
import sys
import getopt
import subprocess
import os
from utils.constants import env_to_blessed_tag_prefixes, env_to_candidate_tag_prefixes
from github import Github
from datetime import datetime, timezone
from utils.git_utils import clone_latest_releases_with_prefix, get_latest_releases_with_prefix

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def cleanup_releases(prefix, latest_releases):
    for latest in latest_releases:
        repo = latest[0]
        release = latest[1]
        repo_releases = repo.get_releases()
        for repo_release in repo_releases:
            if repo_release.tag_name != release.tag_name and repo_release.tag_name.startswith(prefix):
                print("Deleting release " + repo_release.tag_name + " in repo " + repo.name)
                repo_release.delete_release()


def cleanup_build_releases(github, env_name):
    prefix = env_to_candidate_tag_prefixes[env_name]
    latest_releases = get_latest_releases_with_prefix(github, prefix, None, False, True)
    cleanup_releases(prefix, latest_releases)


def cleanup_bless_releases(github, env_name):
    prefix = env_to_blessed_tag_prefixes[env_name]
    latest_releases = get_latest_releases_with_prefix(github, prefix, None, False, True)
    cleanup_releases(prefix, latest_releases)


def main(argv):
    usage = 'python -m scripts.test_and_bless -e env_name -a github_token'
    try:
        opts, args = getopt.getopt(argv, 'h:e:t:a:u:', ['env=', 'test-dir=', 'gtoken=', 'ui='])
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
    if env_name is None or github_token is None:
        logger.info(usage)
        sys.exit(2)
    #if not is_ui:
    #    run_tests(env_name, test_dir)
    logger.info("Using token")
    github = Github(github_token)
    logger.info("Starting cleanup")
    cleanup_build_releases(github, env_name)
    cleanup_bless_releases(github, env_name)
    print("Done cleaning")
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])

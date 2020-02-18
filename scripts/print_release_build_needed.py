import logging
import sys
import getopt
from utils.constants import env_to_buildable_tag_prefixes, env_to_build_tag_prefix
from github import Github
from utils.git_utils import get_latest_releases_with_prefix, get_master_sha, get_tag_for_release_by_repo_name

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def print_release(github, env_name, repo_name):
    prefix = env_to_buildable_tag_prefixes[env_name]
    releases = get_latest_releases_with_prefix(github, prefix, repo_name)
    release = releases[0][1]  # only a single repo and release name pair
    release_tag = get_tag_for_release_by_repo_name(github, repo_name, release)
    built_prefix = env_to_build_tag_prefix[env_name]
    if prefix == built_prefix:
        # We are on dev
        latest = get_master_sha(github, repo_name)
    else:
        built_releases = get_latest_releases_with_prefix(github, built_prefix, repo_name)
        built_release = built_releases[0][1]
        built_tag = get_tag_for_release_by_repo_name(github, repo_name, built_release)
        latest = built_tag.commit.sha
    if release_tag.commit.sha == latest:
        print("skip")
    else:
        if env_name == 'dev':
            print('master')
        else:
            print(release.tag_name)


def main(argv):
    usage = 'python -m scripts.test_and_bless -e env_name -g github_user -p github_pass -r repo-name'
    try:
        opts, args = getopt.getopt(argv, 'h:e:g:p:r:', ['env=','guser=', 'gpass=', 'repo-name='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    env_name = None
    github_user = None
    github_password = None
    repo_name = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-e', '--env'):
            env_name = arg
        elif opt in ('-g', '--guser'):
            github_user = arg
        elif opt in ('-p', '--gpass'):
            github_password = arg
        elif opt in ('-r', '--repo-name'):
            repo_name = arg
    if env_name is None or github_user is None or github_password is None or repo_name is None:
        logger.info(usage)
        sys.exit(2)

    github = Github(github_user, github_password)
    print_release(github, env_name, repo_name)


if __name__ == "__main__":
    main(sys.argv[1:])
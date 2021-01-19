import logging
import sys
import getopt
from utils.constants import env_to_buildable_tag_prefixes, env_to_build_tag_prefix
from github import Github
from utils.git_utils import get_latest_releases_with_prefix, get_master_sha

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def print_release(github, env_name, repo_name):
    prefix = env_to_buildable_tag_prefixes[env_name]
    releases = get_latest_releases_with_prefix(github, prefix, repo_name)
    release_tag = releases[0][1]  # only a single repo and tag name pair
    built_prefix = env_to_build_tag_prefix[env_name]
    if prefix == built_prefix:
        # We are on dev
        latest = get_master_sha(github, repo_name)
    else:
        built_releases = get_latest_releases_with_prefix(github, built_prefix, repo_name)
        built_tag = built_releases[0][1]
        latest = built_tag.commit.sha
    if release_tag.commit.sha == latest:
        print("skip")
    else:
        if env_name == 'dev':
            print('master')
        else:
            print(release_tag.name)


def main(argv):
    usage = 'python -m scripts.print_release_build_needed -e env_name -a github_token -r repo-name'
    try:
        opts, args = getopt.getopt(argv, 'h:e:a:r:', ['env=', 'gtoken=', 'repo-name='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    env_name = None
    github_token = None
    repo_name = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-e', '--env'):
            env_name = arg
        elif opt in ('-a', '--gtoken'):
            github_token = arg
        elif opt in ('-r', '--repo-name'):
            repo_name = arg
    if env_name is None or github_token is None or repo_name is None:
        logger.info(usage)
        sys.exit(2)

    github = Github(github_token)
    print_release(github, env_name, repo_name)


if __name__ == "__main__":
    main(sys.argv[1:])
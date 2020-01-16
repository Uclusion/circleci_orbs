import logging
import sys
import getopt
from utils.constants import env_to_buildable_tag_prefixes
from github import Github
from utils.git_utils import get_latest_releases_with_prefix

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def print_release(github, env_name, repo_name):
    if env_name == 'dev':
        # dev only goes to master
        print('master')
    else:
        prefix = env_to_buildable_tag_prefixes[env_name]
        releases = get_latest_releases_with_prefix(github, prefix, repo_name)
        release = releases[0][1] # only a single repo and release name pair
        print(release.tag_name)


def main(argv):
    usage = 'python -m scripts.test_and_bless -e env_name -t test-dir'
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
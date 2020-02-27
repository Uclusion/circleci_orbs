import logging
import sys
import getopt
from utils.constants import env_to_build_tag_prefix, env_to_buildable_tag_prefixes
from github import Github
from datetime import datetime, timezone
from utils.git_utils import clone_latest_releases_with_prefix, release_head, get_latest_releases_with_prefix

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()

def get_build_tag(env_name):
    build_prefix = env_to_build_tag_prefix[env_name]
    now = datetime.now(timezone.utc)
    build_tag_suffix = now.strftime("%Y_%m_%d_%H_%M_%S")
    build_tag = build_prefix + ".v" + build_tag_suffix
    return build_tag


def build_blessed(github, env_name, repo_name=None, is_ui=False):
    build_tag = get_build_tag(env_name)
    blessed_prefix = env_to_buildable_tag_prefixes[env_name]
    # dev does not build off of a blessed previous release
    # it builds off of head
    if env_name == 'dev' or (env_name == 'stage' and is_ui):
        prebuilt_releases = get_latest_releases_with_prefix(github, blessed_prefix, repo_name, is_ui)
        release_head(github, build_tag, prebuilt_releases, repo_name, is_ui)
    else:
        clone_latest_releases_with_prefix(github, blessed_prefix, build_tag, repo_name, is_ui)


def main(argv):
    usage = 'python -m scripts.test_and_bless -e env_name -g github_user -p github_pass -r repo_name -u is_ui'
    try:
        opts, args = getopt.getopt(argv, 'h:e:g:p:r:u:', ['env=','guser=', 'gpass=', 'repo-name=', 'ui='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    env_name = None
    github_user = None
    github_password = None
    repo_name = None
    is_ui = False
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
        elif opt in ('-u', '--ui'):
            is_ui = arg.lower() == 'true'
    if env_name is None or github_user is None or github_password is None:
        logger.info(usage)
        sys.exit(2)

    github = Github(github_user, github_password)
    build_blessed(github, env_name, repo_name, is_ui)


if __name__ == "__main__":
    main(sys.argv[1:])
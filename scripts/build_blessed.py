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


def build_blessed(github, env_name, repo_name=None, is_ui=False, is_backend_all=False):
    build_tag = get_build_tag(env_name)
    blessed_prefix = env_to_buildable_tag_prefixes[env_name]
    # dev does not build off of a blessed previous release
    # it builds off of head
    if not is_backend_all and (env_name == 'dev' or (env_name == 'stage' and is_ui)):
        # For UI we are specifically told to build so not much point in checking old releases for duplicate
        prebuilt_releases = get_latest_releases_with_prefix(github, blessed_prefix, repo_name, is_ui) \
            if not is_ui else None
        release_head(github, build_tag, prebuilt_releases, repo_name, is_ui)
    else:
        clone_latest_releases_with_prefix(github, blessed_prefix, build_tag, repo_name, is_ui)


def main(argv):
    usage = 'python -m scripts.test_and_bless -e env_name -a github_access_token -r repo_name -u is_ui -b backend_all'
    try:
        opts, args = getopt.getopt(argv, 'h:e:a:r:u:b:',
                                   ['env=','gtoken=', 'repo-name=', 'ui=', 'backend-all'])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    env_name = None
    github_token = None
    repo_name = None
    is_ui = False
    is_backend_all = False
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
        elif opt in ('-u', '--ui'):
            is_ui = arg.lower() == 'true'
        elif opt in ('-b', '--backend-all'):
            is_backend_all = arg.lower() == 'true'
    if env_name is None or github_token is None:
        logger.info(usage)
        sys.exit(2)

    logger.info("Using token")
    github = Github(github_token)
    logger.info("Starting build blessed")
    build_blessed(github, env_name, repo_name, is_ui, is_backend_all)


if __name__ == "__main__":
    main(sys.argv[1:])
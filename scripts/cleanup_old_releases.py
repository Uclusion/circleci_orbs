import logging
import sys
import getopt
from utils.constants import env_to_blessed_tag_prefixes, env_to_candidate_tag_prefixes
from github import Github
from utils.git_utils import get_latest_releases_with_prefix


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def cleanup_releases(prefix, latest_releases):
    for latest in latest_releases:
        repo = latest[0]
        release = latest[1]
        latest_tag = release.tag_name
        print(f'Will ignore latest {latest_tag}')
        repo_releases = repo.get_releases()
        tags = repo.get_tags()
        for repo_release in repo_releases:
            if repo_release.tag_name != latest_tag and repo_release.tag_name.startswith(prefix):
                print("Deleting release " + repo_release.tag_name + " in repo " + repo.name)
                repo_release.delete_release()
        # Delete all tags in dev, stage, or prod respectively
        for tag in tags:
            if tag.name == latest_tag or not tag.name.startswith(prefix):
                continue
            ref = repo.get_git_ref(f"tags/{tag.name}")
            ref.delete()
            print(f"Deleted tag: {tag.name}")


def cleanup_build_releases(github, env_name, is_ui=False):
    prefix = env_to_candidate_tag_prefixes[env_name]
    if prefix:
        latest_releases = get_latest_releases_with_prefix(github, prefix, None, is_ui, True)
        cleanup_releases(prefix, latest_releases)


def cleanup_bless_releases(github, env_name, is_ui=False):
    prefix = env_to_blessed_tag_prefixes[env_name]
    latest_releases = get_latest_releases_with_prefix(github, prefix, None, is_ui, True)
    cleanup_releases(prefix, latest_releases)


def main(argv):
    usage = 'python -m scripts.cleanup_old_releases -e env_name -a github_token'
    try:
        opts, args = getopt.getopt(argv, 'h:e:t:a:u:', ['env=', 'test-dir=', 'gtoken='])
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
    logger.info("Using token")
    github = Github(github_token)
    logger.info("Starting cleanup")
    cleanup_build_releases(github, env_name, True)
    cleanup_bless_releases(github, env_name, True)
    cleanup_build_releases(github, env_name, False)
    cleanup_bless_releases(github, env_name, False)
    print("Done cleaning")
    sys.exit(0)


if __name__ == "__main__":
    main(sys.argv[1:])

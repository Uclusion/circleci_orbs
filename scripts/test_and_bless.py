import logging
import sys
import getopt
import subprocess
import os
from utils.constants import env_to_candidate_tag_prefixes
from github import Github
from utils.git_utils import clone_latest_releases_with_prefix, get_bless_tag


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def run_tests(env_name, test_dir):
    if env_name == 'dev':
        test_args = ['npm', 'run-script', 'test']
    else:
        test_name = 'test' + env_name.capitalize()
        test_args = ['npm', 'run-script', test_name]
    print(test_dir)
    subprocess.run(test_args, cwd=test_dir, check=True)




def bless_build(github, env_name, is_ui=False):
    if env_name == 'production':
        # production doesn't bless anything
        return
    # we just deployed, so get the latest tag prefix matching
    # our env prefix and make a new tag with the blessed prefix
    source_prefix = env_to_candidate_tag_prefixes[env_name]
    bless_tag = get_bless_tag(env_name)
    logger.info("Got bless tag " + bless_tag)
    clones = clone_latest_releases_with_prefix(github, source_prefix, bless_tag, None, is_ui, True)
    print("Done blessing")
    return clones

def main(argv):
    usage = 'python -m scripts.test_and_bless -e env_name -a github_token -t test-dir'
    try:
        opts, args = getopt.getopt(argv, 'h:e:t:a:u:', ['env=', 'test-dir=', 'gtoken=', 'ui='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    env_name = None
    test_dir = None
    github_token = None
    is_ui = False
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-e', '--env'):
            env_name = arg
        elif opt in ('-t', '--test-dir'):
            if arg:
                test_dir = os.path.abspath(arg)
        elif opt in ('-a', '--gtoken'):
            github_token = arg
        elif opt in ('-u', '--ui'):
            is_ui = arg.lower() == 'true'
    if env_name is None or github_token is None:
        logger.info(usage)
        sys.exit(2)
    if not is_ui:
        if test_dir is None:
            logger.info(usage)
            sys.exit(2)
        run_tests(env_name, test_dir)
    logger.info("Using token")
    github = Github(github_token)
    logger.info("Starting build blessed")
    clones = bless_build(github, env_name, is_ui)
    for clone in clones:
        print("Cloned repo " + clone[0] + " tag " + clone[1] + " to " + clone[2])
    print("Done blessing")
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])

import sys
import getopt
import logging
from github import Github

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


usage = 'python -m utils.github_update_file -f file_path -i file_in_repo -r repo -u user -p some_password'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:u:p:f:i:r:', ['user=', 'password=', 'file=', 'fname', 'repo='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    user = None
    password = None
    repo = None
    file = None
    repo_file = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-u', '--user'):
            user = arg
        elif opt in ('-p', '--password'):
            password = arg
        elif opt in ('-r', '--repo'):
            repo = arg
        elif opt in ('-f', '--file'):
            file = arg
        elif opt in ('-i', '--fname'):
            repo_file = arg
    if user is None or password is None or repo is None or file is None or repo_file is None:
        logger.info(usage)
        sys.exit(2)
    g = Github(user, password)
    repo = f"Uclusion/{repo}"
    repo = g.get_repo(repo, lazy=False)
    # https://pygithub.readthedocs.io/en/latest/examples/Repository.html#update-a-file-in-the-repository
    contents = repo.get_contents(repo_file)
    f = open(file, 'r')
    repo.update_file(contents.path, "latest", f.read(), contents.sha)


if __name__ == "__main__":
    main(sys.argv[1:])

import base64
import sys
import getopt
import logging
from github import Github

logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


usage = 'python -m utils.github_update_file -f file_path -i file_in_repo -r repo -a github_token'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:a:f:i:r:', ['gtoken=', 'file=', 'fname', 'repo='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    github_token = None
    repo = None
    file = None
    repo_file = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-a', '--gtoken'):
            github_token = arg
        elif opt in ('-r', '--repo'):
            repo = arg
        elif opt in ('-f', '--file'):
            file = arg
        elif opt in ('-i', '--fname'):
            repo_file = arg
    if github_token is None or repo is None or file is None or repo_file is None:
        logger.error(usage)
        sys.exit(2)
    g = Github(github_token)
    repo = f"Uclusion/{repo}"
    repo = g.get_repo(repo, lazy=False)
    # https://pygithub.readthedocs.io/en/latest/examples/Repository.html#update-a-file-in-the-repository
    contents = repo.get_contents(repo_file)
    content =  base64.b64decode(contents.content).decode('UTF-8')
    with open(file, 'r') as f:
        new_file = f.read()
        if content != new_file:
            logger.info('Updating')
            repo.update_file(contents.path, "latest", new_file, contents.sha)


if __name__ == "__main__":
    main(sys.argv[1:])

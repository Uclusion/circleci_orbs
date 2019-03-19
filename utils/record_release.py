import logging
import sys
import getopt
from models.releases_model import ReleasesModel
from datetime import datetime


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def create_record(env_name, tag_name, repo_name):
    release = ReleasesModel(repo_name=repo_name, tag_name=tag_name)
    actions = [ReleasesModel.env_name.set(env_name),
               ReleasesModel.created_at.set(datetime.now())]
    release.update(actions=actions)


usage = 'python -m utils.record_release -e env_name -t tag_name -r repo_name'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:e:t:r:', ['env=', 'tag=', 'repo='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    env_name = None
    tag_name = None
    repo_name = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-e', '--env'):
            env_name = arg
        elif opt in ('-t', '--tag'):
            tag_name = arg
        elif opt in ('-r', '--repo'):
            repo_name = arg
    if env_name is None or tag_name is None or repo_name is None:
        logger.info(usage)
        sys.exit(2)
    create_record(env_name, tag_name, repo_name)


if __name__ == "__main__":
    main(sys.argv[1:])

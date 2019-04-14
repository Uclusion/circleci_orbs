import logging
import sys
import getopt

from models.deployment_group_version_model import DeploymentGroupVersionModel
from models.releases_model import ReleasesModel
from datetime import datetime


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def create_record(env_name, tag_name, repo_name):
    release = ReleasesModel(repo_name=repo_name, tag_name=tag_name)
    actions = [ReleasesModel.env_name.set(env_name),
               ReleasesModel.created_at.set(datetime.now())]
    release.update(actions=actions)


def create_release(app_version):
    # TODO for now we don't have custom sub domains so just bump everyone up
    groups = DeploymentGroupVersionModel.scan()
    for group in groups:
        group.update(actions=[DeploymentGroupVersionModel.app_version.set(app_version)])


usage = 'python -m utils.record_release -e env_name -t tag_name -r repo_name [-a app_version]'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:e:t:r:a:', ['env=', 'tag=', 'repo=', 'version='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    env_name = None
    tag_name = None
    repo_name = None
    app_version = None
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
        elif opt in ('-a', '--version'):
            app_version = arg
    if app_version is not None:
        create_release(app_version)
    else:
        if env_name is None or tag_name is None or repo_name is None:
            logger.info(usage)
            sys.exit(2)
        create_record(env_name, tag_name, repo_name)


if __name__ == "__main__":
    main(sys.argv[1:])

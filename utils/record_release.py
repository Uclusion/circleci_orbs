import logging
import sys
import getopt
from models.deployment_group_version_model import DeploymentGroupVersionModel


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def create_release(app_version, requires_cache_clear):
    # Just bump everyone up
    groups = DeploymentGroupVersionModel.scan()
    actions=[DeploymentGroupVersionModel.app_version.set(app_version),
             DeploymentGroupVersionModel.requires_cache_clear.set(requires_cache_clear)]
    for group in groups:
        group.update(actions=actions)


usage = 'python -m utils.record_release -e env_name -t tag_name -r repo_name [-a app_version -c requires_cache_clear]'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:a:c:', ['version=', 'cache='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    app_version = None
    requires_cache_clear = False
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-a', '--version'):
            app_version = arg
        elif opt in ('-c', '--cache'):
            requires_cache_clear = arg.lower() == 'true'
    if app_version is not None:
        create_release(app_version, requires_cache_clear)


if __name__ == "__main__":
    main(sys.argv[1:])

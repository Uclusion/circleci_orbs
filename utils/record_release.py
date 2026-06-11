import logging
import sys
import getopt
from models.deployment_group_version_model import DeploymentGroupVersionModel


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()


def create_release(app_version, requires_cache_clear, requires_script_reinstall):
    # Just bump everyone up
    groups = DeploymentGroupVersionModel.scan()
    actions=[DeploymentGroupVersionModel.app_version.set(app_version)]
    # J-all-314 stamp the version that last required each action and leave it in place on
    # later releases so users who skip this release still get notified when they return
    if requires_cache_clear:
        actions.append(DeploymentGroupVersionModel.cache_clear_version.set(app_version))
    if requires_script_reinstall:
        actions.append(DeploymentGroupVersionModel.script_reinstall_version.set(app_version))
    for group in groups:
        group.update(actions=actions)


usage = 'python -m utils.record_release -e env_name -t tag_name -r repo_name [-a app_version -c requires_cache_clear -s requires_script_reinstall]'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:a:c:s:', ['version=', 'cache=', 'script='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    app_version = None
    requires_cache_clear = False
    requires_script_reinstall = False
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-a', '--version'):
            app_version = arg
        elif opt in ('-c', '--cache'):
            requires_cache_clear = arg.lower() == 'true'
        elif opt in ('-s', '--script'):
            requires_script_reinstall = arg.lower() == 'true'
    if app_version is not None:
        create_release(app_version, requires_cache_clear, requires_script_reinstall)


if __name__ == "__main__":
    main(sys.argv[1:])

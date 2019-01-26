import sys
import getopt
import logging
from github import Github


logging.basicConfig(level=logging.INFO, format='')
logger = logging.getLogger()

rest_api_backend_non_layer_repos = ['uclusion_async', 'uclusion_investibles', 'uclusion_investible_api',
                                    'uclusion_markets', 'uclusion_market_api', 'uclusion_shared_resources',
                                    'uclusion_sso', 'uclusion_team_api', 'uclusion_users', 'uclusion_user_api',
                                    'uclusion_webhooks']


def tag_all_repos(user, password):
    g = Github(user, password)
    developer_stuff = g.get_repo('Uclusion/developer_stuff', lazy=False)
    release = developer_stuff.get_latest_release()
    for repo in g.get_user().get_repos():
        if repo.name in rest_api_backend_non_layer_repos:
            ref = repo.get_git_ref('heads/master')
            # See https://github.com/PyGithub/PyGithub/blob/master/github/Repository.py
            logger.info('Creating release for ' + repo.name)
            repo.create_git_tag_and_release(release.tag_name, 'Across repos tag', release.title, release.body,
                                            ref.object.sha, ref.object.type)


usage = 'github_utils.py -u user -p some_password'


def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'h:u:p:', ['user=', 'password='])
    except getopt.GetoptError:
        logger.info(usage)
        sys.exit(2)
    user = None
    password = None
    for opt, arg in opts:
        if opt == '-h':
            logger.info(usage)
            sys.exit()
        elif opt in ('-u', '--user'):
            user = arg
        elif opt in ('-p', '--password'):
            password = arg
    if user is None:
        logger.info(usage)
        sys.exit(2)
    return tag_all_repos(user, password)


if __name__ == "__main__":
    main(sys.argv[1:])

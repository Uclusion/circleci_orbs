from utils.constants import rest_api_backend_repos
import sys


def get_latest_release_with_prefix(repo, prefix):
    tags = repo.get_tags()
    latest = None
    latest_date = None
    for tag in tags:
        if tag.name.startswith(prefix):
            git_tag = repo.get_git_tag(tag.commit.sha)
            created_at = git_tag.tagger.date
            if latest is None or created_at > latest_date:
                latest = tag
                latest_date = created_at
    return latest


def find_latest_release_with_prefix(repo, prefix):
    latest_release = get_latest_release_with_prefix(repo, prefix)
    if not latest_release:
        print("Couldn't get a release with prefix " + prefix + " for " + repo.name)
        sys.exit(3)
    return latest_release


def get_latest_releases_with_prefix(github, prefix, repo_name=None, is_ui=False):
    if repo_name:
        repos_to_search = [repo_name]
    else:
        repos_to_search = rest_api_backend_repos if not is_ui else ['uclusion_web_ui']
    candidates = []
    for repo in github.get_user().get_repos():
        if repo.name in repos_to_search:
            latest_release = find_latest_release_with_prefix(repo, prefix)
            candidates.append([repo, latest_release])
    if len(candidates) != len(repos_to_search):
        print("Some repos are missing tags")
        sys.exit(5)
    return candidates


def clone_release(repo, tag, new_name):
    if not tag:
        sys.exit(4)
    sha = tag.commit.sha
    repo.create_git_tag_and_release(new_name, 'Blessed build tag', new_name, 'Blessed', sha, 'commit')


def get_master_sha(github, repo_name):
    for repo in github.get_user().get_repos():
        if repo.name == repo_name:
            head = repo.get_git_ref('heads/master')
            return head.object.sha
    return None


def release_head(github,dest_tag_name, prebuilt_releases, repo_name=None, is_ui=False):
    sha_map = {}
    for entry in prebuilt_releases:
        repo = entry[0]
        tag = entry[1]
        if tag:
            sha_map[repo.name] = tag.commit.sha

    if repo_name:
        repos_to_search = [repo_name]
    else:
        repos_to_search = rest_api_backend_repos if not is_ui else ['uclusion_web_ui']

    for repo in github.get_user().get_repos():
        if repo.name in repos_to_search:
            head = repo.get_git_ref('heads/master')
            sha = head.object.sha
            if sha != sha_map[repo.name]:
                print("Will clone head of " + repo.name + " to " + dest_tag_name)
                repo.create_git_tag_and_release(dest_tag_name, 'Head Build', dest_tag_name, 'Head', sha, 'commit')
            else:
                print("Skipping " + repo.name + " because head has already built")


def clone_latest_releases_with_prefix(github, source_prefix, dest_tag_name, repo_name=None, is_ui=False):
    print("Cloning releases")
    candidates = get_latest_releases_with_prefix(github, source_prefix, repo_name, is_ui)
    for candidate in candidates:
        repo = candidate[0]
        tag = candidate[1]
        print("Will clone " + tag.name + " in repo " + repo.name + " to " + dest_tag_name)
        clone_release(repo, tag, dest_tag_name)

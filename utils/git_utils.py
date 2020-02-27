from utils.constants import rest_api_backend_repos
import sys


def get_latest_release_with_prefix(releases, prefix):
    latest = None
    latest_date = None
    for release in releases:
        if release.tag_name.startswith(prefix):
            created_at = release.created_at
            if latest is None or created_at > latest_date:
                latest = release
                latest_date = created_at
    return latest


def find_latest_release_with_prefix(repo, prefix):
    releases = repo.get_releases()
    latest_release = get_latest_release_with_prefix(releases, prefix)
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


def get_tag_for_release(repo, release):
    for candidate in repo.get_tags():
        if candidate.name == release.tag_name:
            return candidate
    return None


def get_tag_for_release_by_repo_name(github, repo_name, release):
    for repo in github.get_user().get_repos():
        if repo.name == repo_name:
            return get_tag_for_release(repo, release)
    return None


def clone_release(repo, old_release, new_name):
    # get the tag for the release
    tag = get_tag_for_release(repo, old_release)
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


def release_head(github,dest_tag_name, prebuilt_releases, repo_name=None):
    sha_map = {}
    for entry in prebuilt_releases:
        repo = entry[0]
        release = entry[1]
        tag = get_tag_for_release(repo, release)
        if tag:
            sha_map[repo.name] = tag.commit.sha

    if repo_name:
        repos_to_search = [repo_name]
    else:
        repos_to_search = rest_api_backend_repos

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
        release = candidate[1]
        print("Will clone " + release.tag_name + " in repo " + repo.name + " to " + dest_tag_name)
        clone_release(repo, release, dest_tag_name)

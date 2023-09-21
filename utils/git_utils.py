from datetime import datetime, timezone
from github import UnknownObjectException

from utils.constants import rest_api_backend_repos, env_to_blessed_tag_prefixes
import sys


def get_bless_tag(env_name):
    bless_tag_prefix = env_to_blessed_tag_prefixes[env_name]
    now = datetime.now(timezone.utc)
    bless_tag_suffix = now.strftime("%Y_%m_%d_%H_%M_%S")
    bless_tag = bless_tag_prefix + '_' + bless_tag_suffix
    return bless_tag


def get_dev_build_tag(prefix):
    now = datetime.now(timezone.utc)
    build_tag_suffix = now.strftime("%Y_%m_%d_%H_%M_%S")
    build_tag = prefix + build_tag_suffix
    return build_tag


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


def find_latest_release_with_prefix(github, repo, prefix):
    latest_release_any_prefix = repo.get_latest_release()
    if latest_release_any_prefix is not None and latest_release_any_prefix.tag_name.startswith(prefix):
        latest_release = latest_release_any_prefix
    else:
        releases = repo.get_releases()
        latest_release = get_latest_release_with_prefix(releases, prefix)
    if not latest_release:
        # if on dev first try cloning head, because github likes to delete our releases on us
        if prefix.startswith("dev") or (repo.name == 'uclusion_web_ui' and prefix.startswith("stage")):
            build_prefix = "stage_blessed.v" if repo.name == 'uclusion_web_ui' else "dev_backend.v"
            build_tag = get_dev_build_tag(build_prefix)
            release_head(github, build_tag, [], repo.name, repo.name == 'uclusion_web_ui')
            releases = repo.get_releases()
            latest_release = get_latest_release_with_prefix(releases, prefix)
            if not latest_release:
                print("Couldn't get a release with prefix " + prefix + " for " + repo.name +
                      " even after releasing dev head")
                sys.exit(3)
        else:
            print("Couldn't get a release with prefix " + prefix + " for " + repo.name)
            sys.exit(3)
    return latest_release


def get_latest_releases_with_prefix(github, prefix, repo_name=None, is_ui=False, output_intermediate=False):
    if repo_name:
        repos_to_search = [repo_name]
    else:
        repos_to_search = rest_api_backend_repos if not is_ui else ['uclusion_web_ui']
    candidates = []
    for a_name in repos_to_search:
        if output_intermediate:
            print("Considering " + a_name)
        repo = github.get_repo(f"Uclusion/{a_name}")
        latest_release = find_latest_release_with_prefix(github, repo, prefix)
        if output_intermediate:
            print("Found release " + latest_release.tag_name)
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
    repo = github.get_repo(f"Uclusion/{repo_name}")
    return get_tag_for_release(repo, release)


def clone_release(repo, old_release, new_name):
    # get the tag for the release
    tag = get_tag_for_release(repo, old_release)
    if not tag:
        sys.exit(4)
    sha = tag.commit.sha
    repo.create_git_tag_and_release(new_name, 'Blessed build tag', new_name, 'Blessed', sha, 'commit')


def get_master_sha(github, repo_name):
    repo = github.get_repo(f"Uclusion/{repo_name}")
    head = repo.get_git_ref('heads/master')
    return head.object.sha


def release_head(github, dest_tag_name, prebuilt_releases, repo_name=None, is_ui=False):
    sha_map = {}
    if prebuilt_releases is not None:
        for entry in prebuilt_releases:
            repo = entry[0]
            release = entry[1]
            tag = get_tag_for_release(repo, release)
            if tag:
                sha_map[repo.name] = tag.commit.sha

    if repo_name:
        repos_to_search = [repo_name]
    else:
        repos_to_search = rest_api_backend_repos if not is_ui else ['uclusion_web_ui']

    for a_name in repos_to_search:
        try:
            repo = github.get_repo(f"Uclusion/{a_name}")
            head = repo.get_git_ref('heads/master')
        except UnknownObjectException:
            print(f"Error accessing {a_name}")
            continue
        sha = head.object.sha
        if sha != sha_map.get(repo.name):
            repo.create_git_tag_and_release(dest_tag_name, 'Head Build', dest_tag_name, 'Head', sha, 'commit')


def clone_latest_releases_with_prefix(github, source_prefix, dest_tag_name, repo_name=None, is_ui=False, output_intermediate=False):
    if output_intermediate:
        print("Cloning releases")
    candidates = get_latest_releases_with_prefix(github, source_prefix, repo_name, is_ui, output_intermediate)
    clones = []
    for candidate in candidates:
        repo = candidate[0]
        release = candidate[1]
        if output_intermediate:
            print("Will clone " + release.tag_name + " in repo " + repo.name + " to " + dest_tag_name)
        clone_release(repo, release, dest_tag_name)
        clones.append([repo.name, release.tag_name, dest_tag_name])
    return clones
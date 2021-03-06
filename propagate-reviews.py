import json
import os
import subprocess
from subprocess import Popen, PIPE

from gerrit import Commit, Patchset, query_open_commits, GitCommander

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = os.environ['GERRIT_SERVER_URL']


def main():
    commits = query_open_commits()
    for commit in commits:
        if not commit.is_reviewed() and len(commit.patchsets) > 1 and commit.patchsets[-2].review == 2:
            if test_if_last_patchet_is_cherry_pick(commit):
                commit.review(+2, "Propagating review value from previous commit.")
                if previous_patchset_was_submitted(commit):
                    commit.submit("Propagating SUBMIT from previous commit.")


def test_if_last_patchet_is_cherry_pick(commit):
    git_commander = GitCommander(SERVER_URL)
    os.chdir(os.path.join(BASE_DIR, "tmp"))
    assert(0 == subprocess.call("git reset -q --hard".split()))
    project_url =  "ssh://%s:29418/%s" % (SERVER_URL, commit.project)
    last_patchset = commit.patchsets[-1]
    previous_patchset = commit.patchsets[-2]
    last_patchset.get_commander(git_commander).checkout()
    assert(0 == subprocess.call(["git", "checkout", "-q", "HEAD~"]))
    assert(0 == subprocess.call((['git', 'fetch', project_url, previous_patchset.ref])))
    status = subprocess.call(["git", "cherry-pick", previous_patchset.commitid])
    if status != 0:
        return False
    process = Popen(['git', 'diff', 'HEAD', last_patchset.commitid], stdout=PIPE)
    os.waitpid(process.pid, 0)
    output = process.communicate()[0]
    return output == ''

def previous_patchset_was_submitted(commit):
    previous_patchset = commit.patchsets[-2]
    return previous_patchset.is_submitted()

if __name__ == '__main__':
    main()

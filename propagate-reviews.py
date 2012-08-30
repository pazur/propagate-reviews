import json
import os
import subprocess
from subprocess import Popen, PIPE


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = os.environ['GERRIT_SERVER_URL']


def main():
    commits = query_open_commits()
    for commit in commits:
        if not commit.is_reviewed() and len(commit.patchsets) > 1 and commit.patchsets[-2].review == 2:
            if test_if_last_patchet_is_cherry_pick(commit):
                commit.review(+2, "Propagating review value from previous commit.")


class Commit(object):
    def __init__(self, json_data):
        self.id = json_data['id']
        self.project = json_data['project']
        self.patchsets = []
        for patchset_data in json_data['patchSets']:
            self.patchsets.append(Patchset(patchset_data, self)) 
    
    def is_reviewed(self):
        return self.patchsets[-1].is_reviewed()

    def review(self, value, message):
        args = ['ssh', '-p', '29418', SERVER_URL,
               'gerrit', 'review', 
               '--code-review', str(value),
               '--message', '"%s"' % message,
               str(self.patchsets[-1].commitid)]
        assert(0 == subprocess.call(args))


class Patchset(object):
    def __init__(self, json_data, parent_commit):
        self.data = json_data
        self.ref = json_data['ref']
        self.commitid = json_data['revision']
        self.review = self.interpret_review_values(self.get_review_values())

    def get_review_values(self):
        for approval in self.data.get('approvals', []):
            if approval['type'] == 'CRVW':
                yield int(approval['value'])

    def is_reviewed(self):
        return bool(list(self.get_review_values()))


    def interpret_review_values(self, values):
        values = list(values)
        if not values:
            return None
        for value in [-2, 2, -1, 1]:
            if value in values:
                return value
        raise ValueError()


def test_if_last_patchet_is_cherry_pick(commit):
    os.chdir(os.path.join(BASE_DIR, "tmp"))
    assert(0 == subprocess.call("git reset -q --hard".split()))
    project_url =  "ssh://%s:29418/%s" % (SERVER_URL, commit.project)
    last_patchset = commit.patchsets[-1]
    previous_patchset = commit.patchsets[-2]
    assert(0 == subprocess.call((['git', 'fetch', project_url, last_patchset.ref])))
    assert(0 == subprocess.call(["git", "checkout", "-q", last_patchset.commitid]))
    assert(0 == subprocess.call(["git", "checkout", "-q", "HEAD~"]))
    status = subprocess.call(["git", "cherry-pick", "-q", previous_patchset.commitid])
    if status != 0:
        return False
    process = Popen(['git', 'diff', 'HEAD', last_patchset.commitid], stdout=PIPE)
    os.waitpid(process.pid, 0)
    output = process.communicate()[0]
    return output == ''


def query_open_commits():
    process = Popen(['ssh', '-p', '29418', SERVER_URL, 'gerrit', 'query',
                     'is:open', '--all-approvals', '--format', 'json'],
                    stdout=PIPE)
    os.waitpid(process.pid, 0)
    output = process.communicate()[0]
    for json_data in output.split("\n"):
        if json_data:
            data = json.loads(json_data)
            if not 'type' in data:
                yield Commit(data) 


if __name__ == '__main__':
    main()

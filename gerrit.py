import json
import subprocess
from subprocess import Popen, PIPE
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_URL = os.environ['GERRIT_SERVER_URL']


class Branch(object):
    def __init__(self, name, project):
        self.name = name
        self.project = project
        self.project_url = "ssh://%s:29418/%s" % (SERVER_URL, self.project)

    def push_for(self):
        assert(0 == subprocess.call((['git', 'push', self.project_url, 'HEAD:refs/for/%s' % self.name])))


class Commit(object):
    def __init__(self, json_data):
        self.has_current_parent = (not 'dependsOn' in json_data or
                                   json_data['dependsOn'][0]['isCurrentPatchSet'])
        if 'dependsOn' in json_data:
            self.parent_id = json_data['dependsOn'][0]['id']
        else:
            self.parent_id = None
        self.id = json_data['id']
        self.project = json_data['project']
        self.branch = json_data['branch']
        self.number = json_data['number']
        self.patchsets = []
        self.project_url = "ssh://%s:29418/%s" % (SERVER_URL, self.project)
        for patchset_data in json_data['patchSets']:
            self.patchsets.append(Patchset(patchset_data, self))

    def get_branch(self):
        return Branch(self.branch, self.project)

    def is_reviewed(self):
        return self.patchsets[-1].is_reviewed()

    def review(self, value, message):
        args = ['ssh', '-p', '29418', SERVER_URL,
               'gerrit', 'review',
               '--code-review', str(value),
               '--message', '"%s"' % message,
               str(self.patchsets[-1].commitid)]
        assert(0 == subprocess.call(args))

    def get_parent(self):
        return query_commits(self.parent_id).next()

    def get(self):
        return query_commits(self.id).next()

class Patchset(object):
    def __init__(self, json_data, parent_commit):
        self.commit = parent_commit
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

    def checkout(self):
        assert(0 == subprocess.call((['git', 'fetch', self.commit.project_url, self.ref])))
        assert(0 == subprocess.call(["git", "checkout", "-q", self.commitid]))

    def cherry_pick(self):
        assert(0 == subprocess.call((['git', 'fetch', self.commit.project_url, self.ref])))
        assert(0 == subprocess.call(["git", "cherry-pick", self.commitid]))


def query_open_commits():
    return query_commits("is:open")

def query_commits(query):
    process = Popen(['ssh', '-p', '29418', SERVER_URL, 'gerrit', 'query',
                     query, '--all-approvals', '--dependencies', '--format', 'json'],
                    stdout=PIPE)
    os.waitpid(process.pid, 0)
    output = process.communicate()[0]
    for json_data in output.split("\n"):
        if json_data:
            data = json.loads(json_data)
            if not 'type' in data:
                yield Commit(data)

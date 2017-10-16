#!/usr/bin/env python
import argparse
import json
import os
import re
import subprocess
import sys

DRAFT_PATTERN="(draft-[a-zA-Z0-9-\._\+]+)-([0-9][0-9])$"
DBNAME = "drafts.db"
DRAFTS_SUBDIR = "ids"
GIT_REPO = "ietf-review"
GIT_UPLOAD_BRANCH = "upload"
NEW = []

def debug(msg):
    global args
    if args.verbose:
        print msg

def die(msg):
    print msg
    sys.exit(1)


# The database is just a JSON file of all the drafts and
# the associated phabricator revision ID, i.e.,
#
# {
#   "draft-ietf-blah" : {"version" : "XX", "revision_id: "DXXX"} },
#   "draft-ietf-mumble" : {"version" : "YY", "revision_id: "DYYY"} }
# }
# 
def read_db(dbname):
    try:
        fp = open(dbname)
    except:
        return {}
    return json.load(fp)

def save_db(dbname, data):
    fp = open(dbname, "w")
    json.dump(data, fp, indent=1)



# Manage the drafts clone
def sync_repo():
    subprocess.check_call(["rsync", "-avz", "rsync.ietf.org::internet-drafts", DRAFTS_SUBDIR])
    
def read_id_manifest():
    fp = open(DRAFTS_SUBDIR + "/all_id2.txt")
    drafts = {}
    for l in fp:
        if l.startswith('#'):
            continue
        dat = l.split("\t")
        if dat[2] != "Active":
            continue
        draft = dat[0]
        m = re.match(DRAFT_PATTERN, draft)
        if m is None:
            die("Draft name doesn't match pattern: %s"%draft)
        drafts[m.group(1)] = m.group(2)
    return drafts

def is_newer_version(a, b):
    return int(a) > int(b)

# Routines to upload drafts
def run_sub(cmd, ignore_errors = False):
    cwd = os.getcwd()
    os.chdir(GIT_REPO)
    output = ""
    if ignore_errors:
        subprocess.call(cmd)
    else:
        output = subprocess.check_output(cmd)
    os.chdir(cwd)
    return output
    
def run_git(command, ignore_errors = False):
    cmd = command[:]
    cmd.insert(0, "git")
    return run_sub(cmd, ignore_errors)

def strip_file(infile, outfile):
    stripped = subprocess.check_output(["awk", "-f", sys.path[0] + "/strip.awk", infile])
    o = open(outfile, "w")
    o.write(stripped)
    o.close()

def get_revision(output):
    ll = output.split("\n")
    for l in ll:
        debug(l)
        m = re.search("Revision URI:.*(D\d+)$", l)
        if m is not None:
            return m.group(1)
    raise "Couldn't parse arcanist output"

    
def upload_revision(draftname, version, revision_id):
    debug("Uploading draft %s-%s, current revision=%s"%(draftname, version, revision_id))
    run_git(["checkout", "master"])
    run_git(["branch", "-D", GIT_UPLOAD_BRANCH], True)
    run_git(["checkout", "-b", GIT_UPLOAD_BRANCH])
    dst = "%s/%s.txt"%(GIT_REPO, draftname)
    strip_file("%s/%s-%s.txt"%(DRAFTS_SUBDIR, draftname, version), dst)
    run_git(["add", "%s.txt"%draftname])
    run_git(["commit", "-m", "%s-%s"%(draftname, version)])
    args = ["arc","diff","--verbatim","--allow-untracked","master"]
    if revision_id != None:
        args.append("--update")
        args.append(revision_id)
    output = run_sub(args)
    return get_revision(output)

# Master function
def update():
    sync_repo()
    man = read_id_manifest()
    db = read_db(DBNAME)
    for draft in man:
        version = man[draft]
        debug("Draft %s-%s"%(draft, version))
        revision = None
        if draft in db:
            debug("Already uploaded %s->%s"%(db[draft]["version"], db[draft]["revision_id"]))
            revision = db[draft]["revision_id"]
            if not is_newer_version(version, db[draft]["version"]):
                continue
        # Either this is new or it's updated, so upload
        revision = upload_revision(draft, version, revision)
        debug("Uploaded as revision=%s"%revision)
        NEW.append("%s-%s: %s"%(draft, version, revision))
        db[draft] = { "version" : version, "revision_id" : revision}
    save_db(DBNAME, db)

    print "New drafts"
    for n in NEW:
        print "   ", n
                   
    
parser = argparse.ArgumentParser(description='Git for review')
parser.add_argument('--verbose', dest='verbose', action='store_true')
args = parser.parse_args()

update()        

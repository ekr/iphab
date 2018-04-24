#!/usr/bin/env python
import argparse
import json
import os
import re
import subprocess
import sys
import textwrap
import urllib
import urllib2

DRAFT_PATTERN="(draft-[a-zA-Z0-9-\._\+]+)-([0-9][0-9])$"
DBNAME = "drafts.db"
DRAFTS_SUBDIR = "ids"
GIT_REPO = "ietf-review"
GIT_UPLOAD_BRANCH = "upload"
NEW = []
DATATRACKER = "https://datatracker.ietf.org"
RC = None

def debug(msg):
    global args
    if args.verbose:
        print msg

def warn(msg):
    print "Warning: %s"%msg
    
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
    try:
        output = ""
        if ignore_errors:
            subprocess.call(cmd)
        else:
            output = subprocess.check_output(cmd)
    except e:
        os.chdir(cwd)
        raise e
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
    args = ["arc","diff","--allow-untracked","master"]
    if revision_id != None:
        args.append("--update")
        args.append(revision_id)
        args.append("--message")
        args.append("Update")
    else:
        args.append("--verbatim")
    output = run_sub(args)
    return get_revision(output)


# Assign reviewers to a draft
def run_call_conduit(command, js):
    cwd = os.getcwd()
    val = json.dumps(js)
    debug("Running: %s"%val)
    os.chdir(GIT_REPO)
    p = subprocess.Popen(["arc", "call-conduit", command],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out, err) = p.communicate(json.dumps(js))
    os.chdir(cwd)
    if err != "":
        print err
        raise "Error doing call-conduit: %s"%err
    debug(out)
    jj = json.loads(out)
    if jj["error"] != None:
        raise "Error doing call-conduit: %s"%err
    return jj

def lookup_user(reviewer):
    j = run_call_conduit("user.query", {"usernames":[reviewer]})
    if len(j["response"]) == 0:
        return None
    return j["response"][0]['phid']

def add_reviewer(reviewer, revision, blocking):
    u = lookup_user(reviewer)
    if u == None:
        die("Unknown user %s"%reviewer)
    if blocking:
        rev = "blocking(%s)"%u
    else:
        rev = u
    r = run_call_conduit("differential.revision.edit",
                         {
                             "transactions" :
                             [{"type":"reviewers.add", "value":[rev]}],
                             "objectIdentifier":revision
                         }
                         )

# Assign reviewers based on the IESG Agenda
def download_agenda():
    u = urllib2.urlopen("https://datatracker.ietf.org/iesg/agenda/agenda.json")
    js = u.read()
    return json.loads(js)

def assign_reviewers_from_agenda(agenda, reviewers):
    debug("Agenda: %s"%agenda)
    db = read_db(DBNAME)
    for sn, sec in agenda["sections"].iteritems():
        if "docs" in sec:
            for doc in sec["docs"]:
                docname = doc["docname"]
                if not docname.startswith("draft-"):
                    warn("Invalid draft name %s"%docname)
                    continue
                blocking = False
                if doc["intended-std-level"].find("Standard") > -1:
                    blocking = True
                # Find the revision
                if not docname in db:
                    warn("No Differential revision found for %s"%docname)
                revision = db[docname]["revision_id"]
                debug("Adding reviewers for %s, revision=%s, blocking=%s"%(docname, revision, blocking))
                for rev in reviewers:
                    add_reviewer(rev, revision, blocking)
                

def update_agenda(reviewer):
    agenda = download_agenda()
    assign_reviewers_from_agenda(agenda, [reviewer])
    


# Ballot on a draft
def reflow(txt):
    reflowed = ["\n".join(textwrap.wrap(l)) for l in txt.split("\n")]
    return "\n".join(reflowed)

def clean_diff(js):
    lines = js["response"].split("\n")
    if not lines[0].startswith("diff"):
        raise ValueError("Malformed")
    if not lines[1].startswith("new file"):
        raise ValueError("Malformed")        
    if not lines[2].startswith("---"):
        raise ValueError("Malformed")        
    if not lines[3].startswith("+++"):
        raise ValueError("Malformed")
    
    return [">   " + l[1:] for l in lines[6:]]

def find_section(diff, line):
    for x in range(line, 0, -1):
        m = re.match(">   (\d\S+)", diff[x])
        if m is not None:
            return "S %s"%m.group(1)
    return ""
                     
def format_comment(diff, comment):
    context = 6
    important = False
    last_line = comment["fields"]["line"] - 1
    first_line = max(0, last_line - context)
    txt = find_section(diff, last_line)
    txt += "\n"
    txt += "\n".join(diff[first_line:last_line])
    txt += "\n"
    for c in comment["comments"]:
        raw = c["content"]["raw"]
        m = re.match("IMPORTANT:\s*(.*)", raw)
        if m is not None:
            raw = m.group(1)
            important = True
            
        txt += "\n"
        txt += reflow(raw)
    
    comment = [
        last_line,
        important,
        txt
    ]
    return comment


def format_comments(comments):
    c2 = sorted(comments, key = lambda x: x[0])
    l = ""
    first = True
    for c in c2:
        if not first:
            l += "\n\n\n"
        first = False
        l += c[2]

    return l

def format_overall(event):
    return "\n".join([reflow(c["content"]["raw"]) for c in event["comments"] if c["content"]["raw"] != "Update"])

def retrieve_comments(docname, reviewer):
    # Get my PHID
    username = lookup_user(reviewer)

    # Find the revision
    db = read_db(DBNAME)
    if not docname in db:
        warn("No Differential revision found for %s"%docname)

    # Now get all the events
    j = run_call_conduit("transaction.search", {"objectIdentifier":db[docname]["revision_id"]})
    result = j["response"]["data"]

    last_diff = 0
    for event in result:
        if event["type"] != "inline":
            continue
        if last_diff < event["fields"]["diff"]["id"]:
            last_diff = event["fields"]["diff"]["id"]

    # Now get the diff
    diff = run_call_conduit("differential.getrawdiff", {"diffID":last_diff})
    diff = clean_diff(diff)

    # Now interpolate the comments into the diff.
    important = []
    comments = []
    overall = "Rich version of this review at:\nhttps://mozphab-ietf.devsvcdev.mozaws.net/" + db[docname]["revision_id"] + "\n"
    status = None
    
    for event in result:
        if event["type"] == "comment":
            if event["authorPHID"] != username:
                continue
            overall += "\n" + format_overall(event)

        if event["type"] == "status":
            if status == None:
                status = event["fields"]["new"]
                overall += "\n" + format_overall(event)
            
        if event["type"] != "inline":
            continue

        if event["authorPHID"] != username:
            continue
        
        c = format_comment(diff, event)
        if c[1]:
            important.append(c)
        else:
            comments.append(c)

    debug("Status = %s"%status)
    
    return status, overall, important, comments
    
def ballot_draft(docname):
    status, overall, important, comments = retrieve_comments(docname)
    
    output = []

    if status == "accepted":
        debug("Accepted, balloting no-objection")
        output.append(overall)
        if len(important) > 0:
            output.append("IMPORTANT\n"+format_comments(important))
        if len(comments) > 0 :
            output.append("COMMENTS\n"+format_comments(comments))
        post_ballot(RC["apikey"], docname, "noobj", None, "\n\n".join(output))
    elif status == "needs-revision":
        debug("needs-revision balloting DISCUSS")
        output.append(overall)        
        if len(important) > 0:
            output.append("DETAIL\n"+format_comments(important))
        post_ballot(RC["apikey"], docname, "discuss", "\n\n".join(output), format_comments(comments))
    else:
        die("No or unknown status recorded. Cannot ballot")
    
def post_ballot(apikey, draft, position, discuss, comment):
    api = "/api/iesg/position"
    
    submit = {
        "apikey" : RC["apikey"],
        "doc" : draft,
        "position" : position,
    }
    if discuss is not None:
       submit["discuss"] = discuss
    if comment is not None:
        submit["comment"] = comment

    u = DATATRACKER + api
    debug("URL = %s"%u)
    sub = urllib.urlencode(submit)
    debug("SUB = %s"%sub)
    req = urllib2.Request(u, sub)
    url = None
    try:
        url = urllib2.urlopen(req)
    except Exception as e:
        die("Error posting ballot. %s --> %s"%(str(e), e.read()))
    resp = url.read()
    debug(resp)
        

def download_review(docname, out):
    status, overall, important, comments = retrieve_comments(docname, RC["reviewer"])

    output = []

    output.append(overall)
    if len(important) > 0:
        output.append("IMPORTANT\n"+format_comments(important))
    if len(comments) > 0 :
        output.append("COMMENTS\n"+format_comments(comments))

    if out is None:
        of = sys.stdout
    else:
        of = open("%s/%s-rev.txt"%(out,docname), "w")
    of.write("\n".join(output))
    of.write("\n")

def find_revision(docname):
    db = read_db(DBNAME)
    if not docname in db:
        die("No Differential revision found for %s"%docname)
    print db[docname]


def clear_requests(reviewer):
    u = lookup_user(reviewer)
    if u == None:
        die("Unknown user %s"%reviewer)
    debug("User %s -> PHID %s"%(reviewer, u))

    r = run_call_conduit("differential.revision.search",
                         {
                             "constraints": {"reviewerPHIDs" : [ u ] }
                         }
                         )
    debug(r)

    for rev in r["response"]["data"]:
        if rev["fields"]["status"]["value"] != "needs-review":
            continue
        debug("Clearing request for %s"%rev["phid"])
        r = run_call_conduit("differential.revision.edit",
                             {
                                 "transactions" :
                                 [{"type":"reviewers.remove", "value":[u]}],
                                 "objectIdentifier":rev["phid"]
                             }
        )

        
# Master function
def update_drafts():
    sync_repo()
    man = read_id_manifest()
    db = read_db(DBNAME)
    try:
        update_drafts_inner(man, db)
    except:
        print "Error doing update"

def update_drafts_inner(man, db):    
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
        try:
            revision = upload_revision(draft, version, revision)
            debug("Uploaded as revision=%s"%revision)
            NEW.append("%s-%s: %s"%(draft, version, revision))
            db[draft] = { "version" : version, "revision_id" : revision}
        except e:
            print "Error: %s"%e
        save_db(DBNAME, db)

    print "New drafts"
    for n in NEW:
        print "   ", n


def read_config_file():
    global RC
    rcf = open(".iphab.json", "r")
    RC = json.load(rcf)

def ensure_config(k):
    if not k in RC:
        die("Value %s not configured"%k)
    return RC[k]
        
read_config_file()

parser = argparse.ArgumentParser(description='Git for review')
parser.add_argument('--verbose', dest='verbose', action='store_true')
subparsers = parser.add_subparsers(help="operation", dest="operation")
subparser_update_drafts = subparsers.add_parser("update-drafts", help="Update the drafts")
subparser_update_agenda = subparsers.add_parser("update-agenda", help="Update the agenda")
subparser_add_reviewer = subparsers.add_parser("add-reviewer", help="Add a reviewer")
subparser_ballot = subparsers.add_parser("ballot", help="Generate a ballot")
subparser_ballot.add_argument("draft", nargs=1, help="draft-name")
subparser_download = subparsers.add_parser("download-review", help="Download a review")
subparser_download.add_argument("draft", nargs=1, help="draft-name")
subparser_download.add_argument("--stdout", dest="stdout", action="store_true")
subparser_find = subparsers.add_parser("find-revision", help="Find a revision")
subparser_find.add_argument("draft", nargs=1, help="draft-name")
subparser_clear = subparsers.add_parser("clear-requests")

args = parser.parse_args()


if args.operation ==  "update-drafts":
    update_drafts()
elif args.operation == "update-agenda":
    ensure_config("reviewer")
    update_drafts()
    update_agenda(RC["reviewer"])
elif args.operation == "ballot":
    ballot_draft(args.draft[0])
elif args.operation == "download-review":
    ensure_config("reviewer")
    to = None
    if args.stdout is False:
        to = ensure_config("review-dir")
    download_review(args.draft[0], to)
elif args.operation == "find-revision":
    find_revision(args.draft[0])
elif args.operation == "clear-requests":
    ensure_config("reviewer")
    clear_requests(RC["reviewer"])

    


#!/usr/bin/env python
import sys
import subprocess
import argparse
import re
import os
import shutil
import datetime
import urllib2

DRAFT_PATTERN="(draft-[a-zA-Z0-9-]+-[0-9][0-9])(\.txt)?"
FILENAME_PATTERN="(draft-[a-zA-Z0-9-]+)\.txt$"
DOWNLOAD_TEMPLATE="https://www.ietf.org/id/%s.txt"

def debug(msg):
    global args
    if args.verbose:
        print msg

def die(msg):
    print msg
    sys.exit(1)
    
def checkout_branch(bname):
    debug("Checking out branch %s"%bname)
    c = subprocess.call(["git", "checkout", bname])
    if c != 0:
        subprocess.check_call(["git", "checkout", "--track", "-b", bname, "master"])
        return True
    return False

def strip_file(infile, outfile):
    stripped = subprocess.check_output(["awk", "-f", sys.path[0] + "/strip.awk", infile])
    o = open(outfile, "w")
    o.write(stripped)
    o.close()
    
def add_file(fname):
    global args
    # Reduce the file to the basic name
    draft_name = os.path.split(fname)[1]
    m = re.match(FILENAME_PATTERN, draft_name)
    if m == None:
        die("Bogus filename: %s"%draft_name)
    f = m.group(1)
    base = f
    m = re.match("(.*)-[0-9][0-9]$", f)
    if m != None:
        base = m.group(1)

    branch = "branch-%s"%base
    # Delete branch if asked
    if args.new:
        subprocess.call(["git", "branch", "-D", branch])
        
    # Check out a branch named after this basename
    created = checkout_branch(branch)
    
    base += ".txt"
    debug("Draft basename: %s"%base)

    # Copy it here, stripping headers and footers
    strip_file(fname, base)

    # Now git add it
    subprocess.check_call(["git", "add", base])
    message = "%s: %s"%(draft_name, str(datetime.datetime.now()))
    debug(message)
    subprocess.check_call(["git", "commit", "-m", message])

    # Finally, upload it.
    args = ["arc","diff","--verbatim","--allow-untracked","master"]
    if created:
        args.append("--reviewers")
        args.append("ekr")
    
    subprocess.check_call(args)    

def download_draft(draft):
    debug("Downloading draft %s"%draft)
    to_fetch = DOWNLOAD_TEMPLATE%draft
    to_save = "%s.txt"%draft
    u = urllib2.urlopen(to_fetch)
    f = open(to_save, "w")
    f.write(u.read())
    f.close()
    return to_save
    
parser = argparse.ArgumentParser(description='Git for review')
parser.add_argument("--file", dest="file", help="filename for draft", default=None)
parser.add_argument("--draft", dest="draft", help="draft name (to be downloaded)", default=None)
parser.add_argument('--verbose', dest='verbose', action='store_true')
parser.add_argument('--new', dest="new", action='store_true')
args = parser.parse_args()


if args.draft != None:
    m = re.match(DRAFT_PATTERN, args.draft)
    if m is None:
        die("Bogus draft name: %s"%args.draft)
    file = download_draft(m.group(1))
    debug("Saved draft in %s"%file)
    add_file(file)
    
if args.file != None:
    add_file(args.file)
    

        

iphab -- tools to integrate Phabricator into the IETF workflow
==================================================================
IETF involves a lot of document review, and this is doubly true for
being an Area Director. iphab merges the IETF workflow with the
popular [Phabricator](https://phacility.com/phabricator/) platform.

Major features:

- Automatically maintain Phabricator "revisions" (Phab's term
  for change lists/pull requests/etc.) for each Internet-Draft,
  with a new version for each draft that's published.

- Assign reviewers to revisions based on the IESG agenda.

- Format reviews so they are suitable for mailing.

- Post reviewed revisions on the IETF Ballot tool.

The intent is that eventually much of this will run on a server and
keep Phabricator in sync, but at the moment it's kind of manual and
needs one person to drive it, though multiple people can review.
Email me if you want to share the existing instance.


## Setup


### Prerequisites

1. Install the Phabricator [Arcanist tool](https://secure.phabricator.com/book/phabricator/article/arcanist/).

1. Check out the dummy IETF review at https://github.com/ekr/ietf-review

1. Create the .arcconfig in the repo. I use:

   ```
   {
     "phabricator.uri" : "https://mozphab-ietf.devsvcdev.mozaws.net/"
   }
   ```
   
1. Initialize arcanist in the repo. You'll want a daemon account other than the one you use for
   actual review, because you can't really review your own revisions. I use "ekr-moz" for this.
   Anyway ```arc install-certificate```.

1. Create the iphab config file. It lives in the working directory (the parent of ```ietf-review```)
and is called ```.iphab.json``` and looks like:

   ```
   {
    "review-dir" : "<where you want downloaded reviews to go>",
    "reviewer": "<your phabricator username>",
    "apikey": "<your datatracker API key>"
   }
   ```

If you're not an AD you won't need the datatracker API key.


## Keeping Phabricator in Sync

Once you have things set up, you need to periodically update
Phabricator with the current drafts. iphab will make a local copy of
all drafts with rscync and then will create a new revision for each
draft it doesn't know about and otherwise update the revision for each
new draft.

This is done with:

```
iphab update-drafts
```

It will take hours the first time, as it creates revisions for every
ID, and minutes thereafter. You might want to disable email notifications
(Settings -> Email Delivery) before running this the first time, or you will
lots of emails! Reenable this after the first run...


## Managing the IESG Agenda

If you are an AD, iphab can automatically assign you reviews
based on the current agenda. This is done with:

```
iphab update-agenda
```

Any draft on the agenda will be assigned to the "reviewer" value in your
config file. You will be assigned as a "Blocking" reviewer for
standards track and as a regular reviewer for non-standards
track. This way you can see a dashboard in Phabricator.


## Reviewing

You review in the usual way on Phabricator, filing inline comments
and overall comments. 

You can download a formatted review to mail to somebody using:

```
iphab download-review <draft-name>
```

The review gets stuffed in ```CONFIG["review-dir"]/<draft-name>-rev.txt```.


## IESG Balloting

You can also auto-ballot. iphab will take your review of the latest
revision, turn it into an IESG ballot, and upload.  You will first
need to have a datatracker API key
(https://datatracker.ietf.org/accounts/apikey), which goes in the
config file. For AD balloting, the two states: "Needs-revision" and
"Accepted" have the special meaning of DISCUSS and NO-OBJECTION. Any
other state will be kicked out.

For DISCUSS ballots, the top comment and any comment marked
"IMPORTANT:" will be turned into the Discuss portion of the ballot,
with every other inline comment turned into the Comment portion.

For NO-OBJECTION, the top comment, IMPORTANT comments, and other
comments each get their own sections in a single text field.


## Clearing your Review Queue

If you occasionally don't review things you are supposed to, your
review queue can get cluttered. ```iphab clear-requests``` will
clear anything you haven't reviewed.




















   












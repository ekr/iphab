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
  This is comparatively simple in that it just takes a list
  of ADs and assigns you as a "Blocking" reviewer for
  standards track and as a regular reviewer for non-standards
  track. This way you can see a dashboard.

- Format reviews so they are suitable for mailing.

- Post reviewed revisions on the IETF Ballot tool.

The intent is that eventually much of this will run on a server
and keep Phabricator in sync, but at the moment it's kind of
manual and really only set up for one person to use. Contact
@ekr if you want to share the existing instance, and I'll
make the minor updates.


## Setup


### Prerequisites

1. Install the Phabricator [Arcanist tool](https://secure.phabricator.com/book/phabricator/article/arcanist/).

2. Check out the dummy IETF review at https://github.com/ekr/ietf-review

3. Create the arcconfig in the repo. I use:

   ```
   {
     "phabricator.uri" : "https://mozphab-ietf.devsvcdev.mozaws.net/"
   }
   ```
   
3. Initialize arcanist in the repo. You'll want a daaemon account other than the one you use for
   actual review, because you can't really review your own revisions. I use "ekr-moz" for this.
   Anyway ```arc install-certificate```.
   












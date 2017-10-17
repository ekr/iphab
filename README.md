iphab -- tools to integrate Phabricator into the IETF workflow
==================================================================
IETF involves a lot of document review, and this is doubly true for
being an Area Director. iphab merges the IETF workflow with the
popular [Phabricator](https://phacility.com/phabricator/) platform.

Currently, it will do:

- Automatically maintain Phabricator "revisions" (Phab's term
  for change lists/pull requests/etc.) for each Internet-Draft,
  with a new version for each draft that's published.

- Assign reviewers to revisions based on the IESG agenda.
  This is comparatively simple in that it just takes a list
  of ADs and assigns you as a "Blocking" reviewer for
  standards track and as a regular reviewer for non-standards
  track. This way you can see a dashboard.

I have it running live (but with the refresh steps run on
my laptop) at: https://mozphab-ietf.devsvcdev.mozaws.net/.


The next steps are:

- Run this on some server somewhere
- Automate the step of having reviews fed into the IESG ballot tool
- Integrate with the datatracker so that AD reviews show up.


  

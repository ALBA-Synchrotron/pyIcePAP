# Guidelines for Contributing to pyIcePAP

The pyIcePAP repository uses [Github Flow][]. For the contributions, we use 
the [Fork & Pull Model][]:

1. the contributor first [forks][] the official pyIcePAP repository.
2. the contributor commits changes to a branch based on the. 
   `master` branch and pushes it to the forked repository.
3. the contributor creates a [Pull Request][] against the `master` 
   branch of the official pyIcePAP repository.
4. anybody interested may review and comment on the Pull Request, and 
   suggest changes to it (even doing Pull Requests against the Pull
   Request branch). At this point more changes can be committed on the 
   requestor's branch until the result is satisfactory.
5. once the proposed code is considered ready by an appointed pyIcePAP 
   integrator, the integrator merges the pull request into `master`, 
   updates the changelog file and the version according to the pull request 
   type (feature or patch).
   
   
## Important considerations:

In general, the contributions to pyIcePAP should consider following:

- The code must comply with the next conventions:
    * In general, we try to follow the standard Python style conventions as
      described in [Style Guide for Python Code].
    * Code **must** be python 2.6 compatible.
    * Use 4 spaces for indentation.
    * In the same file, different classes should be separated by 2 lines.
    * use ``lowercase`` for module names. 
    * use ``CamelCase`` for class names.
    * python module first line should be: ``#!/usr/bin/env python``.
    * python module should contain license information (see template below).
    * avoid poluting namespace by making private definitions private (``__`` 
      prefix) or/and implementing ``__all__`` (see template below).
    * whenever a python module can be executed from the command line, it 
      should contain a ``main`` function and a call to it in a 
      ``if __name__ == "__main__"`` like statement (see template below).
    * document all code using Sphinx_ extension to reStructuredText_.

The following code can serve as a template for writing new python modules to
pyIcePAP:

``` 
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------------------------------------------
# This file is part of pyIcePAP (https://github.com/ALBA-Synchrotron/pyIcePAP)
#
# Copyright 2008 CELLS / ALBA Synchrotron, Bellaterra, Spain
#
# Distributed under the terms of the GNU General Public License,
# either version 3 of the License, or (at your option) any later version.
# See LICENSE.txt for more info.
#
# You should have received a copy of the GNU General Public License
# along with pyIcePAP. If not, see <http://www.gnu.org/licenses/>.
# -----------------------------------------------------------------------------

"""A :mod:`pyIcePAP` module written for template purposes only"""

__all__ = ["IcePAPDemo"]

__docformat__ = "restructuredtext"

class IcePAPDemo(object):
    """This class is written for template purposes only"""
    
def main():
    print "IcePAPDemo"

if __name__ == "__main__":
    main()
    
```
- [pyIcePAP travis-ci][] will check it for each Pull Request (PR) using
  the latest version of [flake8 available on PyPI]travis[]. 
  
  In case the check fails, please correct the errors and commit
  to the PR branch again. You may consider running the check locally
  using the flake8 script in order to avoid unnecessary commits.  If you 
  find problems with fixing these errors do not hesitate to ask for
  help in the PR conversation! We will not reject any contribution due
  to these errors. The purpose of this check is just to maintain the code
  base clean.

- The contributor must be clearly identified. The commit author 
  email should be valid and usable for contacting him/her.

- Commit messages  should follow the [commit message guidelines][]. 
  Contributions may be rejected if their commit messages are poor.
  
- The licensing terms for the contributed code must be compatible 
  with (and preferably the same as) the license chosen for the Sardana 
  project (at the time of writing this file, it is the [LGPL][], 
  version 3 *or later*).

## Notes:

- If the contributor wants to explicitly bring the attention of some 
  specific person to the review process, [mentions][] can be used
  
- If a pull request (or a specific commit) fixes an open issue, the pull
  request (or commit) message may contain a `Fixes #N` tag (N being 
  the number of the issue) which will automatically [close the related 
  Issue][tag_issue_closingtag_issue_closing]


[Github Flow]: https://guides.github.com/introduction/flow/index.html 
[Fork & Pull Model]: https://en.wikipedia.org/wiki/Fork_and_pull_model
[forks]: https://help.github.com/articles/fork-a-repo/
[Pull Request]: https://help.github.com/articles/creating-a-pull-request/
[commit message guidelines]: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
[mentions]: https://github.com/blog/821-mention-somebody-they-re-notified
[tag_issue_closing]: https://help.github.com/articles/closing-issues-via-commit-messages/
[Sardana coding conventions]: http://www.sardana-controls.org/devel/guide_coding.html
[LGPL]: http://www.gnu.org/licenses/lgpl.html
[pyIcePAP travis-ci]: https://travis-ci.org/ALBA-Synchrotron/pyIcePAP
[flake8 available on PyPI]: https://pypi.org/project/flake8
[Style Guide for Python Code]: http://www.python.org/peps/pep-0008.html
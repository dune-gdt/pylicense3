pylicense3
=========

[![image](https://img.shields.io/pypi/v/pylicense3.svg)](https://pypi.python.org/pypi/pylicense3)

[![image](https://github.com/WWU-AMM/pylicense3/workflows/pytest/badge.svg)](https://github.com/WWU-AMM/pylicense3/actions)

[![Documentation Status](https://readthedocs.org/projects/pylicense3/badge/?version=latest)](https://pylicense3.readthedocs.io/en/latest/?badge=latest)


Apply license information to a git project.

-   Free software: BSD license
-   Documentation: <https://pylicense3.readthedocs.io>.
-   [![Live examples](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/WWU-AMM/pylicense3/HEAD?filepath=docs%2Fexamples%2F)


Features
--------

-   TODO

After generating your project
-----------------------------

- Setup github secrets for pypi [github project settings](https://github.com/WWU-AMM/pylicense3/settings/secrets/actions/new):
   - `PYPI_TOKEN` for "real" deploys on git tags
   - `TEST_PYPI_TOKEN` for deploys to test.pypi.org
- enable project on [readthedocs.org](https://readthedocs.org/dashboard/import/?)
- setup branch protection+automerge in [github project settings](https://github.com/WWU-AMM/pylicense3/settings/branches)
- Fix `Live examples` link above


Credits
-------

This package was created with
[Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[WWU-AMM/python_cookiecutter](https://github.com/WWU-AMM/python_cookiecutter)
project template.

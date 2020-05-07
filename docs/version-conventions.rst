===================
Version conventions
===================

This package is being developed continuously. Branch protection is turned on for the master branch. Useful new features and bugfixes can be developed in a separate branch or fork. Pull requests can be made to integrate updates into the master branch. To keep track of versions, every change to the master branch will receive a version tag. This page outlines the version tags' naming convention.

Each change to the master branch is stamped with a unique version identifier. We use sequence based version identifiers, that consist of a sequence of three numbers: the first number is a major change identifier, followed by a minor change idenfier and finally a maintenance identifier. This leads to version identifiers of the form:

major.minor.maintenance (example: 1.2.2)

The following guideline gives an idea what types of changes are considered major changes, minor changes and maintenance:

- Major changes (typically breaking changes)  -> major + 1
- Minor changes (typically adding of new features) -> minor + 1
- Maintenance (typically bug fixes and updates in documentation -> maintenance + 1


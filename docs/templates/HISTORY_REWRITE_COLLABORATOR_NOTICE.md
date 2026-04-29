# Git History Rewrite Notice

## Summary

We plan to rewrite the Git history of `xupeng211/FootballPrediction` to remove large generated/data/model artifacts from repository history.

## Why

The repository history contains large generated artifacts that slow down clone/fetch operations.

## Impact

After the rewrite:

- Old clones should not be used for normal push/pull.
- Developers should fresh clone the repository.
- Pushing from old clones can reintroduce removed objects.

## Required Action

Before the maintenance window:

1. Commit or stash your work.
2. Push any important branches.
3. Stop merging during the maintenance window.

After the rewrite:

1. Move your old clone aside.
2. Fresh clone the repository.
3. Re-apply local work carefully if needed.

## Suggested Commands

```bash
mv FootballPrediction FootballPrediction.pre-history-rewrite-backup
git clone git@github.com:xupeng211/FootballPrediction.git
```

## Do Not

Do not run `git pull` in an old clone and then push.

## Contact

Owner:
Maintenance window:
Status:

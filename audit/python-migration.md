# Python hook migration

Old `.sh` scripts retained only in the comparison-test source archive, not in the active hook directories.

Improvements:
- Initial baseline independent of Maven.
- Unique external review-state directory; no overwriting baseline.
- State path normalized and validated before creation.
- Full branch/ref/tag/local-config snapshot included in tracked-state comparison.
- Final checks run regardless of Maven result in Python runner.
- Source repo remains unmodified by hooks; ignored build outputs remain allowed.

Python hooks do not magically enforce command/network policies; actual harness must apply sandbox restrictions. Git snapshot comparisons do not prove the absence of temporary changes between snapshots.

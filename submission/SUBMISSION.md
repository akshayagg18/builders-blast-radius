# Submission operations

The official Dockerfile is at the repository root, as required.

## Build

```bash
docker build --platform linux/amd64 -t blast-radius-entry .
```

The image does not clone SQLGlot, install packages, or access the network. It copies
only `src/selector.py` and `src/coverage_map.json.gz`, then runs as UID/GID 65534.

## Runtime contract

- Input mounts: `/data/tests.json`, `/data/commits/*.patch`
- Output: one compact JSON object per commit on stdout
- Diagnostics: stderr only
- Writes: none
- Network: none
- Maximum workers emitted: eight

## Exact sample validation

```bash
make sample
```

Expected result for the committed sample and map:

```text
Simulated: 153.396 s
Misses:    0 (0.000 s of the simulated time)
```

## Submission fields

- Repository: https://github.com/akshayagg18/builders-blast-radius
- Commit: `aad38e3e63a5216ba60bf439de38ec8527206db1`
- Receipt: `BB-B53E1F14`
- Official practice score: 733.1 s (732.728 s simulated + 0.36 s median
  CPU; 2 missed commits)
- Final status: automatically entered as the team's current best
- Scorer version: `blast-radius-1`
- Track page: https://www.joinbuilders.org/buildathon/tracks/blast-radius

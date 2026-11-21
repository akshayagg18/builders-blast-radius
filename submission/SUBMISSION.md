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

- Repository: filled after public GitHub publication
- Commit: filled after publication
- Scorer version: `blast-radius-1`
- Track page: https://www.joinbuilders.org/buildathon/tracks/blast-radius

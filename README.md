# Cutest cat entry

Python 3.13 program for the make.fun **cutest-cat-01** bounty. It ships an
orange tabby kitten JPEG as `entry.png` and copies the validated bytes to
`$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output/entry.png`).

## Run

```bash
python3 main.py --check
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py --json
```

## Rules met

- PNG or JPEG payload under the name `entry.png`, at most 1 MiB and 1024×1024
- No network; two runs write identical bytes
- Stdlib only

## Credit

The emitter is adapted from the MIT-licensed cutest-dog entry
[Quixyl-eng/makefun-cutest-dog-02](https://github.com/Quixyl-eng/makefun-cutest-dog-02),
which follows the official make.fun cutest-cat-01 kit starter (MIT).

## License

MIT

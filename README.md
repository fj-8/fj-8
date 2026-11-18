# fj-8

Fixed-memory data structures and command-line tools, written in whatever the
problem actually needs. Three code repositories, no third-party dependency in
any of them, and a measured number wherever a README makes a claim.

| | What it answers | Proof in the repo |
| --- | --- | --- |
| [**karg**](https://github.com/fj-8/karg) | *Rust* — parse argv into typed values, with help and errors that name the nearest real flag | 48 tests, MSRV 1.74, `unsafe_code = forbid`, zero dependencies including dev |
| [**bitlane**](https://github.com/fj-8/bitlane) | *C++20* — a compressed bitmap index over `uint32_t` sets: intersection, union, rank, a versioned wire format | 31 `ctest` cases, five headers, CRC32C'd serialisation, built and measured with MSVC 19.51 |
| [**sift**](https://github.com/fj-8/sift) | *Python 3.11+* — cardinality, frequencies, quantiles and moments over a stream you cannot hold in RAM, plus a CLI | 231 `unittest` cases, stdlib only, a 150 s benchmark suite whose output is committed |

## How the work is done

- **The standard library is the whole dependency list.** `karg` has no crates,
  `bitlane` includes nothing but its own headers, `sift` imports `hashlib`,
  `array`, `zlib` and `math` — no NumPy, no `pytest`, no `mmh3`. Adding a
  dependency is a design decision, so the default is not to.
- **Every claim is a test or a measurement.** Each repo ships the exact command
  that produced the numbers in its README, and `sift` commits
  [`bench/bench-full.txt`](https://github.com/fj-8/sift/blob/main/bench/bench-full.txt)
  — the transcript itself — and has a test that executes its own README so the
  docs cannot rot silently.
- **The loss is printed next to the win.** `sift` is 7.9×–65.7× slower per
  operation than the C container it replaces, and says so in a section called
  *The honest part: speed*, because the reason to use it is 4,201 bytes instead
  of 92 MB.
- **Persisted formats are hostile-input territory.** Both `bitlane` and `sift`
  put a checksum and a version in front of every payload, reject a frame whose
  declared size disagrees with the bytes present, and test a one-byte edit at
  every offset.
- **`main` is the release.** No `develop`, no history rewriting, no force-pushes
  after a tag is public.

## Not shown here

There is no CI running on GitHub yet. The workflow files exist and are correct,
but pushing `.github/workflows` needs a token scope the current credential does
not have, so the suites run locally and each README quotes the command. The
profile deliberately has no star counts, language bars or contribution graphs:
they describe the account's first days, not the code.

## Reach me

Issues on whichever repository the thing belongs to —
[karg](https://github.com/fj-8/karg/issues),
[bitlane](https://github.com/fj-8/bitlane/issues),
[sift](https://github.com/fj-8/sift/issues). Each has a `SECURITY.md` that says
what counts as a vulnerability (spoiler: a sketch overestimating is not one, a
frame that makes a process allocate 16 GB is).

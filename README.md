# fj-8

Fixed-memory data structures and command-line tools, written in whatever the
problem actually needs. Four code repositories, no third-party dependency in
any of them, and a measured number wherever a README makes a claim.

| | What it answers | Proof in the repo |
| --- | --- | --- |
| [**karg**](https://github.com/fj-8/karg) | *Rust* — parse argv into typed values, with help and errors that name the nearest real flag | 48 tests, MSRV 1.74, `unsafe_code = forbid`, zero dependencies including dev |
| [**bitlane**](https://github.com/fj-8/bitlane) | *C++20* — a compressed bitmap index over `uint32_t` sets: intersection, union, rank, a versioned wire format | 32 `ctest` cases, five headers, an FNV-1a-64-checked frame format, built and measured with MSVC 19.51 |
| [**sift**](https://github.com/fj-8/sift) | *Python 3.11+* — cardinality, frequencies, quantiles and moments over a stream you cannot hold in RAM, plus a CLI | 231 `unittest` cases, stdlib only, a 150 s benchmark suite whose output is committed |
| [**turnstile**](https://github.com/fj-8/turnstile) | *Java 17+* — a bounded MPMC queue over a fixed ring: turn-based slots, `offer` returns `false` instead of growing or blocking | 18 cases on a stdlib-only harness, ten CI jobs on plain `javac`, five committed transcripts — three bench launches and two of the padding A/B |

## How the work is done

- **The standard library is the whole dependency list.** `karg`'s
  `[dependencies]` and `[dev-dependencies]` tables are both empty; `bitlane`'s
  five headers include the C++ standard library plus `<emmintrin.h>` for the one
  SSE2 lane;
  `sift` imports only stdlib modules — `hashlib`, `array`, `zlib`, `math`,
  `bisect`, `heapq`, `random`, `struct`, `argparse`, `contextlib`, `sys` — and
  `tests/test_package.py` fails if any of them stops being stdlib; `turnstile`
  imports `java.lang.invoke`, `java.util` and `java.util.concurrent` and a CI
  grep fails the build on any other package, which is why its test framework is
  123 lines of `Harness.java` rather than JUnit. No NumPy, no `pytest`, no
  `mmh3`, no Maven. Adding a dependency is a design decision, so the default is
  not to.
- **Every claim is a test or a measurement.** Each repo ships the exact command
  that produced the numbers in its README, and `sift` commits
  [`bench/bench-full.txt`](https://github.com/fj-8/sift/blob/main/bench/bench-full.txt)
  — the transcript itself — and has a test that executes its own README so the
  docs cannot rot silently. `turnstile` commits three separate JVM launches of
  its bench and two launches of its padding experiment, and the README quotes the
  range across them rather than the best one. `turnstile` also has a case that
  reads its own documentation back — the number of cases the README quotes, the
  length of the three files whose sizes are used as arguments, the five
  transcripts it claims are committed — which caught a line count that a Javadoc
  fix had invalidated two commits earlier, on a machine where nothing else had
  opened the README. This page is held to the same rule by `tools/check_claims.py`,
  which clones the other four repositories and re-measures the table above: a
  registered `Harness.test(`, a `TEST(` use, a `def test_`, a header on disk, a
  parsed `rust-version`, a line of a committed transcript, an `import` in a source
  tree, a `Cargo.toml` as it stands inside the tag the README tells you to fetch,
  an `import` in this page's own tool — 31 claims, all of which have to agree. It
  was proved to mean something by breaking it nine separate ways: 18 cases to 19,
  48 tests to 49, five headers to six, 123 lines to 124, dropping `zlib` from the
  list of modules `sift` imports, 7.9× to 9.9×, `v0.3.0` pointed at a tag that
  does not exist, the same tag pointed at a manifest saying 1.74 where the tag
  says 0.3.0, and an `import requests` added to `tools/starved_legs.py` — each
  produced exactly one failing row and a non-zero exit. The total is a row of its
  own, so the number in this sentence is checked by the run instead of kept by the
  author, and it has caught the author twice: adding the three install-tag rows
  turned it red at 26 against 30, and the two rows about this repository's own
  tool at 30 against 31, both before the prose had been updated to make them true.
- **The loss is printed next to the win.** `sift` is 7.9×–65.7× slower per
  operation than the C container it replaces, and says so in a section called
  *The honest part: speed*, because the reason to use it is 4,201 bytes instead
  of 92 MB. `turnstile` loses to `ArrayBlockingQueue` at every symmetric
  producer/consumer shape it measures, and says so in the table where it wins at
  the asymmetric ones.
- **Persisted formats are hostile-input territory.** Both `bitlane` and `sift`
  put a checksum and a version in front of every payload, reject a frame whose
  declared size disagrees with the bytes present, and test a one-byte edit at
  every offset.
- **`main` is the release.** No `develop`, no history rewriting, no force-pushes
  after a tag is public.

## Continuous integration

Every repository tests itself on `main`, and each README lists its own jobs.
`karg`: `cargo test` on Linux (stable and the 1.74 MSRV), Windows and macOS,
then `fmt --check`, `clippy -D warnings`, a lock-file grep that fails if a
second crate appears, and `cargo doc` under `RUSTDOCFLAGS=-D warnings` — seven
jobs. `bitlane`: each of the five headers compiled as the only include in a
translation unit, the suite under GCC, Clang, Apple Clang (all three with
`-Wall -Wextra -Werror`) and MSVC, the same suite again under ASan and UBSan, an
MSVC build with `/W4 /WX`, and a separate `find_package` consumer built against
the installed tree — eight checks. `sift`: 231 `unittest` cases on CPython 3.11,
3.12 and 3.13 on Linux and Windows, then `pip install .` and a smoke run of both
entry points — six jobs. `turnstile`: the 18-case suite twice on JDK 17 and 21
across Linux, Windows and macOS, with `javac -Xlint:all -Werror` (and
`-Xdoclint:all/protected` on the public API) as the compile step, then an import
allowlist, a `javadoc` render, `build.sh` from a clean tree and a check that
`build.sh` is still committed executable — ten jobs.

This repository has one job of its own, and it is the checker described above:
`.github/workflows/claims.yml` clones the four at their current `main`, runs
`python3 tools/check_claims.py` with nothing installed, and fails on any row that
disagrees. It runs on a push and every Monday, because a claim about four other
repositories can go stale without anything happening here. Its scope is stated in
its output rather than assumed: it does not re-run a benchmark, it does not
re-derive karg's 48 — cargo adds the doc tests to that number, so the profile
matches it against karg's own badge and leaves the measuring to karg's CI — and it
takes turnstile's job count from the run list instead of expanding the matrix in
`ci.yml`, because a second implementation of Actions' matrix semantics is one more
thing to keep in sync with the first and the run list is the thing the claim is
about. Where there is no token or no finished run to read — the job count and the
three install tags are the four rows that ask the API rather than a file — a row
prints `skip`, the summary counts the skips, and an unmeasured claim is never
reported as an agreed one.

`bitlane` was red for its first two runs, and that is the part worth keeping.
Its own harness wrote `const auto& lhs = (a)`, so an operand like `*b.min()`
bound a reference to a byte inside the `std::optional` temporary that the call
returned — an object destroyed at the end of that initialiser, because lifetime
extension does not cross a function call. MSVC in Debug and Release kept the
stale bytes and every check passed; GCC said "using a dangling pointer to an
unnamed temporary" and then compared four garbage values. Nothing in the library
was wrong, which is exactly why the CI matrix is worth the queue time.

The strict legs have earned their keep on the other axes too. `bitlane` called
itself warning-free because MSVC said so, and `/W4` has no integer-conversion
diagnostics to give; GCC, Clang and Apple Clang objected twenty-some times
between them, all of them to `std::popcount`, `std::countr_zero` and
`std::countl_zero` answering in `int` beside unsigned counters and bit positions.
No value was ever wrong — the fix is where those conversions are written, not
what they produce. `turnstile`'s matrix has the same asymmetry on the JDK axis:
JDK 21's doclint rejects a comment that opens straight into `@param` or `@return`
with no leading sentence, JDK 17's accepts the identical file, and `a09c74e` was
consequently green on the two JDK 17 legs that got a runner and red on the two
JDK 21 legs that did — `warning: no main description` at `Turnstile.java:81` and
`:117`, with `-Werror` turning a comment with no first line into a build failure.
Its two macOS legs were cancelled before either JDK could disagree.

What a badge that is not green means here is a separate matter, and worth stating.
`main` runs share one concurrency group with cancellation turned off: a run that
has started is allowed to finish instead of being cut off by the next push. What
that setting does not promise is a verdict for every commit — a run still waiting
in the queue when a newer commit arrives is replaced by it, which is how
`turnstile`'s run for `7627612` ended `cancelled` with no job having started at
all. The newest commit on `main` always gets tested, an intermediate one can end
with nothing to report, and that is the trade the group makes rather than an
accident of the matrix.

When a run is red, the reason is often a runner and not the code, and when it is
a runner it is a macOS one: `karg`, `bitlane` and `turnstile` have each had a
macOS leg report `cancelled` with no runner ever assigned to it — no steps, no
start time, nothing to read. A run containing one cancelled leg is reported as a
`failure`, which is indistinguishable in a badge from a compile error, so the
three repositories that have a macOS leg record which one they saw, each of them
as a closed range rather than as a count of "the most recent". Between `0886512`
and `d33975f`, five `karg` runs reported `failure` with six jobs green and
`Test macos-latest / stable` never given a runner; two of the five were re-run on
their own commit and starved again — `6a1c077` after twenty-five minutes with its
`started_at` still empty — and the two commits before the range had the identical
leg scheduled on the first attempt. `bitlane`'s Apple Clang check is starved in
six of the nine runs between `b38ec65` and `4d81a45`, three attempts in a row on
`b270e95` among them, with every job that did get a runner green in all six; one
run in that range is green on all eight, and two of them are the
replaced-while-queued shape described above. `turnstile` had both macOS legs
starved on the seven runs that started jobs from `a09c74e` to `f830e3c`. Four of
those seven failed for that alone, and the other three carried a real failure
beside the starvation — doclint, a file mode, a ring-size assertion — which is
the point: the starved legs and the compile-time ones arrive in the same shape.
`sift` has no macOS leg, so its queue is only ever its own six jobs. These
ranges were written from `python3 tools/starved_legs.py`, which prints each
repository's recent `main` runs beside the legs that got no runner. It prints
history and not a verdict, because a verdict about somebody else's pool is the
one number on this page that moves while nobody is pushing anything — and a
sentence about it should be about a range that has finished.

The only third-party versions any of these repositories pin are the actions in
their workflows, and Dependabot now watches exactly that — `karg`'s two dependency
tables are empty, `sift`'s `dependencies` is an empty list, `turnstile`'s CI fails
the build on any import outside the JDK, and `bitlane` is five headers. Its first
pull requests were version bumps for `actions/checkout`, `actions/setup-java` and
`actions/setup-python`; they are merged on the same terms as any other change,
which means their own CI legs have to be green first.

## Not shown here

The profile deliberately has no star counts, language bars or contribution
graphs: they describe the account's first days, not the code. Every number in
the four READMEs is either a test or a measurement, quoted with the command
that produced it.

## Reach me

Issues on whichever repository the thing belongs to —
[karg](https://github.com/fj-8/karg/issues),
[bitlane](https://github.com/fj-8/bitlane/issues),
[sift](https://github.com/fj-8/sift/issues),
[turnstile](https://github.com/fj-8/turnstile/issues). Each has an issue form that
asks for the commands from a clean tree, the output in the words it printed, and
the toolchain version — because a report without those three cannot be turned into
a test. Each has the same pull-request checklist as a template, spelling out what
`CONTRIBUTING.md` already requires. Each has a `SECURITY.md`
that says what counts as a vulnerability (spoiler: a sketch overestimating is
not one, a frame that makes a process allocate 16 GB is).

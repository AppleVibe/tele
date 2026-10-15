# development

how to get the tele sources, build them, run a dev build safely, make a change and turn it into a patch. read [architecture](architecture.md) first for how the queue works, and [conventions](conventions.md) for how the code should look.

## prerequisites

- everything upstream needs to build telegram desktop at the tag in `UPSTREAM`. read upstream's `docs/building-win.md`, `docs/building-linux.md` or `docs/building-mac.md` **from that tag** (they are in your tdesktop checkout after `tele.py checkout`), not from upstream's default branch: toolchains and library versions change between releases.
- python 3 and git on `PATH`.
- a git identity (`user.name`, `user.email`): `tele.py` creates commits with `git am`.
- your own `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org), see upstream's `docs/api_credentials.md`. never use the official telegram desktop credentials, and never try to reuse the credentials of tele's ci.
- a lot of disk space and time. a first build prepares every library from source: expect tens of gigabytes and an hour or more.

## getting the sources

put the tele repository and a tdesktop clone next to each other. `tele.py` looks for `../tdesktop` by default. on windows, upstream's prepare script also expects `ThirdParty` and `Libraries` next to `tdesktop`, so one build folder holds everything:

```
<BuildPath>/
  ThirdParty/     created by upstream's prepare script (windows)
  Libraries/      created by upstream's prepare script (windows)
  tdesktop/       upstream clone, driven by tele.py
  tele/           this repository
```

```
cd <BuildPath>
git clone https://github.com/nitreojs/tele.git
git clone https://github.com/telegramdesktop/tdesktop.git
cd tele
git checkout next
python tele.py checkout
```

`checkout` fetches the tag from `UPSTREAM`, puts tdesktop and every submodule on a `tele` branch at that tag and applies the queue as commits. when it finishes, tdesktop is the tele source tree: `git log v7.2.9..tele` (with the tag from `UPSTREAM`) shows one commit per patch.

when you run `checkout` again later, it refuses as long as there is uncommitted or unexported work in the tree, and lists what it found. export it, or pass `--force` to throw it away.

## building

follow upstream's build doc for your platform, starting from the "prepare libraries" step: the clone step is already done. the tele specifics:

- configure with your own credentials and upstream's updater off:

  ```
  -D TDESKTOP_API_ID=<your id> -D TDESKTOP_API_HASH=<your hash> -D DESKTOP_APP_DISABLE_AUTOUPDATE=ON
  ```

  `DESKTOP_APP_DISABLE_AUTOUPDATE=ON` keeps upstream's own updater out of the build, so it can never replace your build with an official telegram. ci passes it too.
- leave `TELE_BUILD` at its default, `0`. that makes a dev build: the title bar says `tele #DEV`, the self-updater and what's new are off. only set a real number when you test the updater itself, and go back to `0` afterwards.
- to test crash reports, add `-D DESKTOP_APP_DISABLE_CRASH_REPORTS=OFF`, like ci.
- the binary is called `tele`: `out/Debug/tele.exe` on windows, `out/Debug/tele.app` on macos, `out/Debug/tele` on linux (or `Release`). an old `Telegram.exe` in `out` is from a build before the rename.
- after moving tdesktop to another tag, run upstream's prepare script again: each tag's `Telegram/build/prepare/prepare.py` can pin other library versions. tele's own patches change it too (money's wallet engine comes from gettele/money), so also run it after a `tele.py checkout` that brings a new `prepare.py`. on windows `win.bat skip-release silent wallet-engine tdesktop_rust` redoes only the wallet stages.
- the first configure downloads litehtml for html bubbles, so it needs network once.

### windows

upstream's doc uses visual studio. once `configure.bat x64 ...` has run (without `x64` you get a 32-bit project), you can also build from the terminal it asks you to set up:

```
cd <BuildPath>\tdesktop\Telegram
cmake --build ..\out --config Debug --parallel --target Telegram
```

- `win.bat skip-release silent` prepares only the debug libraries and rebuilds stale ones without asking. that's all a debug build needs.
- `-- /p:LinkIncremental=true` at the end of the build command turns incremental linking on for that build only. after one full link, rebuilding a single edited `.cpp` takes seconds instead of minutes. a build without the flag throws the incremental state away.
- a full debug build with every core busy can stop with `C1060: compiler is out of heap space`: build with fewer jobs (`--parallel 4 ... -- /p:CL_MPCount=6`) and run it again; it continues where it stopped.
- the debug `.pdb` of a tele build is bigger than 4 GB, past the linker's default limit (`LNK1140`). `set LINK=/PDBPAGESIZE:8192` before building raises it; the first time, delete `out\Debug\tele.pdb` and the `.ilk` so they're made with the new page size.
- older msvc toolsets can fail to build libjxl with `_sub_overflow_i32` not found. force-include `intrin.h` for that one stage, then continue:

  ```
  set CL=/FIintrin.h
  tdesktop\Telegram\build\prepare\win.bat skip-release silent libjxl
  set CL=
  tdesktop\Telegram\build\prepare\win.bat skip-release silent
  ```

### linux and macos

build as upstream describes. for linux that's the docker build environment from `prepare/linux.sh`, with the `-D` options above appended to the `build.sh` command. for macos, pass them to `./configure.sh`.

## running a dev build safely

a dev build is a real client on a real account. set it up so a bug can't hurt an account you care about:

- **separate data.** on windows, tele keeps its data next to the exe, so `out\Debug` gets its own `tdata`. on linux and macos, a dev build would share the data of an installed tele (`~/.local/share/tele`, `~/Library/Application Support/tele`); start it with upstream's `-workdir <folder>` to keep it apart.
- **test accounts.** use a secondary account, or telegram's test servers: a plain right-click on "add account" offers the test server. test accounts are free and disposable.
- **tele's own network off.** start with `-teleoffline` to keep tele away from the tele server, github updates and third-party services while you work on something unrelated. `-noteleserver` and `-noteleupdate` turn off one of them. see [launch flags](launch-flags.md).
- **logs.** settings → tele → debug turns debug logs on, opens the logs folder and has an mtproto inspector that browses the logged requests and responses. upstream's `-debug` launch flag also turns debug logs on from the start.

## making a change

all work happens in the tdesktop tree, as commits on the `tele` branch.

1. **edit** in the repository that owns the file: the tdesktop root, or inside the submodule (`Telegram/lib_ui` and so on). follow [conventions](conventions.md).
2. **build and run** the dev build. exercise the change by hand, with the option on and off. off has to behave exactly like upstream.
3. **commit.**
   - a new feature is one new commit at the end of the queue: `feat: <what it does>`. adding it at the end keeps every existing patch number and patch link.
   - a fix or improvement of a patch that isn't released yet goes into that patch's commit: `git commit --fixup <commit>`, then `git rebase -i --autosquash <UPSTREAM tag>`.
   - a fix of a released patch can be its own `fix:` commit at the end. the maintainer may fold it into the feature's patch before the next release.
   - commit changes to a submodule inside the submodule. never commit a moved submodule pointer in the root: `export` rejects it.
4. **export** from the tele repository:

   ```
   python tele.py export
   ```

   this rewrites `patches/` from the commits and prints the patch count per group. `git status` in the tele repository shows exactly which patches your change touched. a change in one feature should touch one patch.
5. **patch row.** for a new patch, add a row to the patch table in `docs/releases.md` (see [the patch row](#the-patch-row)).
6. **dry run** against pristine upstream (see [proving the queue applies](#proving-the-queue-applies)).
7. **commit and open a pull request** in the tele repository against `next`, with `patches/`, `docs/releases.md` and nothing else unless the change needs it:

   ```
   git add -A patches docs/releases.md
   git commit -m "feat: <what it does>"
   ```

to drop a patch, remove its commit (`git rebase -i`) and export again.

## the patch row

every patch has one row in `docs/releases.md`, under the heading of the release that introduces it. release notes, the in-app what's new and [features](features.md) are generated from these rows, so the format is strict:

```
| [109](../patches/tdesktop/0109-feat-your-subject.patch) | what it does, in one or two short lowercase sentences | tele → chats, off |
```

- the link has to be the exact file name `export` wrote, relative to `docs/`.
- "what it does" is written for users: what they see and where, not how it's implemented.
- "where to toggle" is `tele → <page>` (optionally `→ <row>`) followed by the default (`off`, `on`, `off, needs a restart`), or `always on`, or `with N` for a patch that extends patch N. the page names are the ones in the app: `interface`, `chats`, `messages`, `sending`, `notifications`, `menus`, `privacy`, `profiles and ids`, `bots`, `server`, `backup`, `updates`, `debug`. see [release notes](architecture.md#release-notes) for how this becomes a category.
- new rows go at the end of the table of the next release. if the newest section belongs to a release that is already out, start a new section above it: `### [tele N](https://github.com/nitreojs/tele/releases/tag/<UPSTREAM>-tele.N)` with the next release number.
- update the count in the `all N patches, newest release first.` line at the top.
- a patch for a submodule (`patches/Telegram/lib_ui/…`) gets a number from 1001 up (1001, 1002, …), so it never takes a number a tdesktop patch will get. numbers have to be unique: the in-app what's new matches items by number.
- leave `docs/features.md` alone: its tables are regenerated from `docs/releases.md` with `python ci/features.py` before a release.
- if the feature changes what a launch flag turns off, or the tele server protocol, update [launch flags](launch-flags.md) or [tele server](server.md) too.

## proving the queue applies

your tree applies the queue on top of your own history. ci applies it to a fresh clone of the upstream tag. check that the exported patches apply the way ci does:

```
git clone --depth 1 --branch <tag from UPSTREAM> --recurse-submodules --shallow-submodules https://github.com/telegramdesktop/tdesktop.git <scratch folder>
python tele.py --tdesktop <scratch folder> apply
```

it has to end with `tdesktop is on <tag> with N patch(es) applied` and no conflict. throw the scratch folder away afterwards. a patch that only applies in your tree usually means a commit wasn't exported, or the queue was edited by hand.

## syncing with a new upstream release

sync.yml does this in ci and opens a `patch-conflict` issue when the queue doesn't apply to a new release. resolving it is local work:

1. `git pull` in the tele repository.
2. `python tele.py checkout <new tag>`.
3. on a conflict, `tele.py` stops and prints the failing patch, the conflicted files and the repository to fix. in that repository: fix the files, `git add` them, `git am --continue`. if upstream already contains the change, `git am --skip` drops the patch.
4. `python tele.py continue` applies the rest. repeat 3 and 4 until everything is applied.
5. run upstream's prepare script again (the new tag may pin other libraries), build, and check the patches whose conflicts you resolved.
6. `python tele.py export`. this also writes the new tag into `UPSTREAM`.
7. commit `UPSTREAM` and `patches/` as `chore: rebase patches onto <tag>`.

the resolution ends up in the exported patches, so it never has to be repeated. a sync is its own change: never bump `UPSTREAM` in a feature pull request.

conflicts against upstream's `dev` branch (the `canary-conflict` issue) are resolved the same way, on a checkout of `dev`:

```
git -C ../tdesktop fetch origin dev
git -C ../tdesktop checkout --detach origin/dev
python tele.py apply
```

then fix, `git am --continue` and `python tele.py continue` as above. this only shows the conflict early: never export from a `dev` checkout, the patches would be based on `dev`. carry the fix over to your checkout of `UPSTREAM` when it applies there too, otherwise keep it for the release that brings the change.

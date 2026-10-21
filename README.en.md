# tele-ru

[🇷🇺 Русский](README.md) · [🇬🇧 English](README.en.md)

A Russian build of [tele](https://github.com/nitreojs/tele), a Telegram Desktop fork.

This repository is not a standalone fork: it keeps a **queue of patches** on top of [tdesktop](https://github.com/telegramdesktop/tdesktop). The upstream tag is pinned in `UPSTREAM`, the patches in `patches/` are applied on top of it, and GitHub Actions builds the result.

We took [nitreojs/tele](https://github.com/nitreojs/tele) and added what it didn't have:

- **a Russian interface** for everything tele adds to Telegram Desktop: settings pages, option names and descriptions, menus, dialogs, notifications;
- **our own update links and signing key** — the app updates from this repository, not the author's;
- **an empty tele server by default** — so crash reports and badges don't go anywhere unless you set a server yourself.

Telegram Desktop itself stays English: only tele's own additions are translated. The translation turns on by itself when Telegram's language is Russian (`Settings → Language`) and stays off for any other language.

## Download

Grab the latest build from [releases](../../releases/latest). None of them touch an installed Telegram or its data.

| platform | file | what to do |
| --- | --- | --- |
| Linux x64 | `tele-<version>-linux64.zip` | unpack somewhere you can write to (like `~/.local/opt/tele`) and run `./tele`. Data goes to `~/.local/share/tele`, and it adds itself to the app menu. |
| Windows x64 | `tele-<version>-win64.zip` | unpack anywhere and run `tele.exe`. Data stays next to the exe, and it adds itself to the Start menu. |
| macOS (Apple Silicon and Intel) | `tele-<version>-macos.dmg` | drag it into Applications and run the command below once, since the build isn't notarized. Data goes to `~/Library/Application Support/tele`. |

```bash
xattr -dr com.apple.quarantine /Applications/tele.app
```

### Linux Mint / Ubuntu

```bash
mkdir -p ~/.local/opt/tele
unzip tele-*-linux64.zip -d ~/.local/opt/tele
chmod +x ~/.local/opt/tele/tele
~/.local/opt/tele/tele
```

The first launch adds a shortcut to the app menu. If libraries are missing, install Telegram Desktop's build dependencies:

```bash
sudo apt install libgl1 libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 \
  libxcb-shape0 libxcb-xinerama0 libxcb-render-util0 libdbus-1-3 libopenh264-7
```

## Updates

The app checks this repository's releases every 3 hours, downloads a new build in the background and asks you to restart. The feed is signed with an ed25519 key, so a build from anywhere else won't install. Turn it off in `Settings → tele → Updates`.

The first build has to be installed by hand: auto-updates start with the next one. The author's client that may already be installed has his key and his address built in, so it can't download this build.

## What is translated

The translation lives in one module, `tele/tele_i18n.cpp`. Every string tele adds goes through `Tele::Lower()`, and that's where the Russian text is substituted. About 1700 strings: settings pages and groups, every tele option with its description, menu items, dialogs, notifications and errors.

A string that isn't in the table is shown in English, so the app never breaks or shows a blank row.

## Building

Everything is built in GitHub Actions:

- **Build** — on every push to `main`, builds Windows, Linux and macOS and publishes a release;
- **Sync** — every 3 hours, checks for a new tdesktop release and opens an issue when the patches stop applying.

### Repository secrets

| secret | why |
| --- | --- |
| `TDESKTOP_API_ID` | your own `api_id` from [my.telegram.org](https://my.telegram.org) — never someone else's |
| `TDESKTOP_API_HASH` | your own `api_hash` from there |
| `TELE_UPDATE_KEY` | the ed25519 private key that signs the update feed |
| `TELE_BOT_TOKEN` | optional: a bot that reports builds |
| `TELE_NOTIFY_CHAT` | optional: where those reports go |

The public half of the key sits in `ci/update-public-key.pem` and is compiled into `tele/tele_updater.cpp`. Change the key in all three places at once, or updates stop installing.

### Local build

```bash
git clone https://github.com/AppleVibe/tele-ru.git
git clone https://github.com/telegramdesktop/tdesktop.git
cd tele-ru
python3 tele.py checkout
```

Then follow tdesktop's own docs for your platform (`docs/building-linux.md` from the tag in `UPSTREAM`). Configure with `-D DESKTOP_APP_DISABLE_AUTOUPDATE=ON` and leave `TELE_BUILD` at `0`.

### Fixing a translation

1. `python3 tele.py checkout` — check out the tdesktop tree;
2. edit `Telegram/SourceFiles/tele/tele_i18n.cpp` in the tdesktop tree (never the patch by hand);
3. commit with `feat:` or `fix:`;
4. `python3 tele.py export` — the patches are regenerated;
5. push.

## Layout

```
UPSTREAM                      the tdesktop tag the patches apply to
patches/tdesktop/*.patch      patches for tdesktop itself
patches/Telegram/lib_ui/      patches for the submodule
tele.py                       checkout / continue / export / apply
ci/                           builds, releases, signing, notes
.github/workflows/            build, sync, canary, promote, announce
```

## Credits

- [telegramdesktop/tdesktop](https://github.com/telegramdesktop/tdesktop) — the base every build is made from.
- [nitreojs/tele](https://github.com/nitreojs/tele) — the fork this is built on. All of tele's functionality is his work; the Russian interface and the update links are what changed here.
- **Russian translation** — [@acaff](https://t.me/acaff): tele's menus and submenus, every setting name and description.
- [materialgram](https://github.com/kukuruzka165/materialgram), [freshGram](https://github.com/Snowy-Fluffy/freshGram) — ideas tele has taken in.

## License

Same as tdesktop and tele: GPL-3.0 with additional exceptions. See `LEGAL` in the tdesktop sources.

---

Russian build and translation: [@acaff](https://t.me/acaff) · [AppleVibe](https://github.com/AppleVibe).
If a string is still English or translated wrong, open an [issue](../../issues) or write on Telegram.

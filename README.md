# tele

[English](README.md) · [Русский](README.ru.md)

a telegram desktop fork: a queue of patches applied on top of every stable [tdesktop](https://github.com/telegramdesktop/tdesktop) release and built here automatically.

based on [tele build 22](https://github.com/nitreojs/tele/releases/tag/v7.3.1-tele.22), with russian translation of tele's menus and submenus.

![tele](docs/screenshot.png)

## download

grab the latest build from [releases](https://github.com/AppleVibe/tele-ru/releases/latest). none of them touch an installed telegram or its data.

| platform | file | |
|---|---|---|
| windows x64 | `tele-<version>-win64.zip` | unpack anywhere and run `tele.exe`. it keeps its data next to the exe and adds itself to the start menu. |
| linux x64 | `tele-<version>-linux64.zip` | unpack somewhere you can write to (like `~/.local/opt/tele`) and run `./tele`. data goes to `~/.local/share/tele`, and it adds itself to the app menu. |
| macos (apple silicon and intel) | `tele-<version>-macos.dmg` | drag tele into applications and run the command below once, since the build isn't notarized. data goes to `~/Library/Application Support/tele`. |

```
xattr -dr com.apple.quarantine /Applications/tele.app
```

tele updates itself: it checks these releases every 3 hours, downloads new builds in the background and asks you to restart. the feed is signed, so a build that isn't from here won't be installed. turn it off in settings → tele → updates.

every zip and dmg has a [build provenance attestation](https://github.com/AppleVibe/tele-ru/attestations). check a download with the [github cli](https://cli.github.com):

```
gh attestation verify tele-<version>-win64.zip --repo AppleVibe/tele-ru
```

## highlights

everything tele adds lives in settings → tele, right below the language row.

- [gift studio](docs/features.md#gift-studio): build any collectible from real parts and export it as png, mp4, gif or a tgs sticker.
- [ghost mode](docs/features.md#privacy): no read receipts, typing, online status or story views, for every chat or just some.
- [notification centre](docs/features.md#notifications): tele toasts, updates, crash reports and server notices in one list.
- [mtproto console](docs/features.md#debug): call any api method with your own session, with autocomplete and schema hints.
- [scripts](docs/scripting.md): javascript and typescript plugins that can use telegram's whole api, the web platform and tele's own windows, each power behind your consent. ready ones are in the [catalog](https://gettele.app/scripting/catalog).
- [money card designs](docs/features.md#chats): dress money's card in one of your collectible gifts and put your gifts on it as stickers.
- [kept deleted messages](docs/features.md#messages): messages deleted by others stay in the chat, even after a restart if you want.
- [local folders and pins](docs/features.md#interface): more folders, chats per folder and pinned chats than telegram allows, kept on this device.
- [docked media](docs/features.md#sending): attach media above the field, each with its own caption, and keep it as a draft.
- [shots](docs/features.md#menus): save messages as a picture, with or without the chat background.
- [rich quotes](docs/features.md#messages): quote part of a rich message and reply with it in the rich editor.
- [sticker captions](docs/features.md#chats): send stickers with text, and see the text under them.
- [streamer mode](docs/features.md#privacy): hide tele from screen capture, names and text from notifications, and your phone number.
- [self-updater](docs/features.md#updates): signed updates from these releases on windows, linux and macos.

## more

- [all features](docs/features.md), grouped by settings page.
- [releases](docs/releases.md): every patch, by the release that brought it.
- [launch flags](docs/launch-flags.md) that keep tele off the network for one launch.
- [title bar template](docs/title-template.md): every variable and modifier.
- [link cleaner](docs/link-cleaner.md): the tracking parameters tele removes.
- [tele server](docs/server.md): what it does and how to run your own.
- [contributing](CONTRIBUTING.md).

## credits

- [tdesktop](https://github.com/telegramdesktop/tdesktop), which every tele build is made from.
- [tele](https://github.com/nitreojs/tele) by nitreojs, the original fork and its features.
- [@acaff](https://t.me/acaff), for the russian translation of tele's menus and submenus.
- [materialgram](https://github.com/kukuruzka165/materialgram) by kukuruzka165, another tdesktop fork. these tele features come from its ideas: hiding bubble tails and the classic bubble padding, no outline on large emoji, selecting more than 100 messages, showing online members in big groups, the upload date in the media viewer, copying a sticker set's owner id, better voice quality and keeping the start of voice messages, less photo compression, a thinner photo editor brush, a smaller minimum window, a bigger, faster chat export and mentioning several people in a row.
- [freshGram](https://github.com/Snowy-Fluffy/freshGram) by Snowy-Fluffy, which combines [AyuGram Desktop](https://github.com/AyuGram/AyuGramDesktop) and materialgram. tele's secret chats prototype is ported from its secret chats, and these tele features come from its ideas: the message type filter in chat search, keeping deleted chats and topics, peeking at a hidden last seen and hiding birthday banners.
- [SPOwnerBot](https://github.com/arynyklas/SPOwnerBot) by arynyklas and [its fork](https://github.com/madrik1337/SPOwnerBot) by madrik1337, for how a sticker set's id holds its owner, including owners past 8 billion.

## contributing

bug fixes, conflict fixes and new features are welcome. for a feature, open an issue first. [CONTRIBUTING.md](CONTRIBUTING.md) walks through the whole cycle: getting the patched sources with `tele.py`, building, testing, exporting patches and opening a pull request.

- [docs/architecture.md](docs/architecture.md): the patch queue, `tele.py`, where the fork code lives and what ci does.
- [docs/development.md](docs/development.md): building, running a dev build safely and making a change.
- [docs/conventions.md](docs/conventions.md): code style, commits, patch hygiene and privacy rules.
- [docs/releasing.md](docs/releasing.md): how releases are built, signed and published.
- [AGENTS.md](AGENTS.md): rules for ai coding agents.

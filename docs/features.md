# features

every tele patch, grouped by the settings page that holds its switch. [releases](releases.md) has the same rows by the release that brought them.

everything tele adds lives in settings → tele, right below the language row, grouped into pages. the search at the top of the page, and the main settings search, find every tele setting. right-click any of them to copy a link that opens it.

backup exports your tele settings to a file you can give to anyone, and imports one with a preview of what changes. it covers tele's switches and lists, not telegram's own settings (like interface scale) or data kept per account (local pins, pinned sets, bookmarks, local folders). to move everything to another folder or pc, copy the whole `tdata` folder next to tele.

"toggle" is where the switch is and its default. `always on` has no switch, `with N` follows the switch of patch N.

more about some of them: [title bar template](title-template.md), [link cleaner](link-cleaner.md), [launch flags](launch-flags.md), [tele server](server.md).

## interface

settings → tele → interface.

| # | what it does | toggle |
|---|---|---|
| [10](../patches/tdesktop/0010-feat-make-the-title-bar-label-a-live-template.patch) | the title bar label is a template with live variables, see [title bar template](title-template.md) | tele → interface |
| [22](../patches/tdesktop/0022-feat-lowercase-every-interface-text.patch) | lowercases the whole interface. messages and names stay as they are | tele → interface, off, needs a restart |
| [30](../patches/tdesktop/0030-feat-hide-the-all-chats-folder.patch) | hides the all chats folder when you have other folders, the list opens on your first one | tele → interface, off |
| [35](../patches/tdesktop/0035-feat-lowercase-tele-s-own-texts-too.patch) | lowercase covers tele's own texts and the crash window too | with 22 |
| [38](../patches/tdesktop/0038-feat-turn-off-animated-userpics.patch) | animated userpics can stay still: separately in the chat list and in chats and profiles | tele → interface, off, in chats and profiles: tele → chats, off |
| [41](../patches/tdesktop/0041-feat-customize-the-window-title-and-format-template-.patch) | the window title (taskbar, alt+tab, system window frame) can be a template too, or follow the title bar label. every [template](title-template.md) variable takes modifiers like `{weekday|short|lower}` or `{chat|max:20}` | tele → interface |
| [82](../patches/tdesktop/0082-feat-move-chats-instantly-in-the-chat-list.patch) | chats move to their new place in the chat list right away, without the pause while the mouse moves over the list | tele → interface, off |
| [84](../patches/tdesktop/0084-feat-set-your-own-app-and-tray-icons.patch) | your own app and tray icons from any image, and the tray icon can follow the app icon | tele → interface → app icon |
| [97](../patches/tdesktop/0097-feat-redesign-the-title-template-editor.patch) | a new title template editor: variables as chips, a palette with modifiers and presets | with 10 |
| [117](../patches/tdesktop/0117-feat-hide-communities.patch) | hide communities: their chats stay in the list as regular chats | tele → interface, off |
| [123](../patches/tdesktop/0123-feat-pin-chats-past-the-limit.patch) | pin more chats than telegram allows: the extra pins stay on this device, have a hollow pin icon and can be dragged anywhere among the server pins | tele → interface, off |
| [124](../patches/tdesktop/0124-feat-folders-past-the-limit.patch) | more folders and more chats per folder than telegram allows: what doesn't fit stays on this device | tele → interface, off |
| [129](../patches/tdesktop/0129-feat-hide-message-previews-in-the-chat-list.patch) | hide message previews in the chat list, with compact rows | tele → interface, off |
| [150](../patches/tdesktop/0150-feat-make-build-the-bare-build-number.patch) | {build} in the title bar label is the bare build number, the default label is TELE #{build}, and custom labels are updated once | with 10 |
| [152](../patches/tdesktop/0152-feat-interface-scale-in-1-steps.patch) | the interface scale slider moves in 1% steps | tele → interface, off |
| [154](../patches/tdesktop/0154-feat-reduce-motion.patch) | reduce motion: every animation limit except calls on, no sticker loops, reaction bursts or message effects. turning it off restores your settings | tele → interface, off |
| [162](../patches/tdesktop/0162-feat-unsorted-folder.patch) | an unsorted folder with every chat that isn't in another folder, archived ones aside. chats with unread messages stay in it | tele → interface, off |
| [165](../patches/tdesktop/0165-feat-select-several-chats-in-the-list.patch) | alt+click selects chats, shift+click a range. a bar marks them read, archives, mutes, adds them to a folder, deletes or leaves them | tele → interface, off |
| [181](../patches/tdesktop/0181-feat-preview-chats-in-the-chat-area.patch) | alt+click or holding a userpic opens the chat read-only in the chat area, leaving messages unread | tele → interface, off |
| [191](../patches/tdesktop/0191-feat-page-keys-in-lists-and-safer-box-edges.patch) | page up, page down, home and end scroll lists and boxes, and a click just outside a box no longer closes it | tele → interface, off |
| [192](../patches/tdesktop/0192-feat-search-filter-and-export-star-transactions.patch) | search, filter, total and export star and ton transactions to csv | tele → interface, off |
| [193](../patches/tdesktop/0193-feat-filter-long-lists-by-date.patch) | filter star and ton transactions, shared media and profile gifts by a day or a date range | tele → interface, off |
| [258](../patches/tdesktop/0258-feat-lowercase-the-default-title-bar-label.patch) | the title bar label is `tele #N` by default instead of `TELE #N` | with 10 |
| [264](../patches/tdesktop/0264-feat-smaller-minimum-window-size.patch) | the window can be made as small as 256x256 instead of 380x480 | tele → interface, off |
| [275](../patches/tdesktop/0275-feat-smooth-wheel-scrolling.patch) | each mouse wheel step glides instead of jumping in chats, the chat list, sections, boxes and settings, like profiles already do. touchpads are unchanged | tele → interface, off |
| [300](../patches/tdesktop/0300-feat-compact-icon-only-folders.patch) | folders shown as icons only get smaller icons and buttons, in the side bar and in the tabs above the chat list | tele → interface, off |
| [305](../patches/tdesktop/0305-feat-scroll-to-zoom-in-the-media-viewer.patch) | scroll to zoom in the media viewer. hold ctrl or cmd while scrolling to switch photos | tele → interface, off |
| [308](../patches/tdesktop/0308-feat-smoother-wheel-glides-in-chats.patch) | wheel glides step at your monitor's refresh rate, chats move a cached image while they glide, animated stickers, emoji and gifs pause until the glide ends, and the chat list only repaints rows that changed. tele → debug → log scroll frame rate writes each glide's timings to log.txt | with 275 |
| [323](../patches/tdesktop/0323-fix-glides-in-boxes-no-longer-blank-the-chats-under-.patch) | gliding in a box, settings or another panel no longer turns the chat list and the chat behind it black | with 308 |
| [330](../patches/tdesktop/0330-feat-close-the-media-viewer-with-mouse-back.patch) | the mouse back button (mouse 4) closes the media viewer: photos, videos, the windowed viewer and stories | tele → interface, off |
| [1005](../patches/Telegram/lib_ui/0005-feat-ease-mouse-wheel-steps-in-scroll-areas.patch) | the part of smooth wheel scrolling that lives in the ui library's scroll areas | with 275 |
| [1008](../patches/Telegram/lib_ui/0008-feat-glide-at-the-screen-refresh-rate.patch) | the part of smoother glides that lives in the ui library: a glide ticks at the monitor's refresh rate while other animations keep their pace | with 275 |

## chats

settings → tele → chats.

| # | what it does | toggle |
|---|---|---|
| [8](../patches/tdesktop/0008-feat-send-quick-replies-in-groups-and-channels.patch) | business quick replies in groups and channels too. telegram only sends them in private chats, so tele posts the messages as ordinary ones (no bot keyboards, via-bot labels or effects) | tele → chats, off |
| [21](../patches/tdesktop/0021-feat-hide-call-buttons.patch) | no call button in private chats and profiles | tele → chats |
| [24](../patches/tdesktop/0024-feat-hide-sponsored-messages.patch) | no ads: no sponsored messages in channels and bots, no video ads, no sponsored search results | tele → chats, off |
| [34](../patches/tdesktop/0034-feat-hide-the-mtproxy-sponsor-channel.patch) | no sponsor channel pinned to the chat list when you connect through an mtproxy | tele → chats, off |
| [62](../patches/tdesktop/0062-feat-hide-or-confirm-call-and-voice-chat-buttons.patch) | call and voice chat buttons can each be shown, hidden, or ask before calling | tele → chats |
| [68](../patches/tdesktop/0068-feat-set-or-remove-chat-backgrounds-only-for-you.patch) | set your own background for any chat, or remove its background, only for you, from the chat menu | tele → chats → chat backgrounds |
| [71](../patches/tdesktop/0071-feat-link-usernames-to-profiles-locally.patch) | username aliases: your own @alias for any profile, in any letters, clickable and in autocomplete, only for you. aliases in sent messages become real mentions, a toast says what changed | tele → chats → username aliases |
| [72](../patches/tdesktop/0072-feat-hide-the-mentions-and-reactions-buttons.patch) | the jump to mentions and jump to reactions buttons can be hidden | tele → chats, off |
| [76](../patches/tdesktop/0076-feat-open-the-emoji-panel-and-attach-menu-by-click-o.patch) | the emoji, sticker and gif panel and the attach menu open on click only, not on hover | tele → chats, off |
| [101](../patches/tdesktop/0101-feat-find-chats-by-their-aliases.patch) | chat search finds chats by their aliases, yours and the server's | with 71 |
| [121](../patches/tdesktop/0121-feat-use-aliases-for-inline-bots.patch) | username aliases work for inline bots too: `@alias query` asks the real bot | with 71 |
| [122](../patches/tdesktop/0122-feat-hide-mention-and-reaction-badges-in-the-chat-li.patch) | the options that hide the mentions and reactions buttons also hide the @ and ❤️ badges in the chat list and topic tabs | with 72 |
| [127](../patches/tdesktop/0127-feat-pin-sticker-and-emoji-sets.patch) | pin sticker and emoji sets to the front of the panel | tele → chats, off |
| [131](../patches/tdesktop/0131-feat-turn-off-touchpad-gestures.patch) | turn off touchpad gestures: swipe to reply and swipe back, each switchable | tele → chats, off |
| [132](../patches/tdesktop/0132-feat-hide-similar-channels.patch) | hide similar channels after joining and in profiles, each switchable | tele → chats, off |
| [134](../patches/tdesktop/0134-feat-hide-and-show-the-pinned-bar-from-the-chat-menu.patch) | hide or show the pinned bar from the chat menu in chats where you can't unpin | tele → chats, on |
| [137](../patches/tdesktop/0137-feat-turn-off-ai-features.patch) | turn off telegram's ai features with one switch | tele → chats, off |
| [164](../patches/tdesktop/0164-feat-keep-saved-gifs-and-stickers-past-the-limit.patch) | saved gifs and favorite stickers past telegram's limit stay on this device | tele → chats, off |
| [168](../patches/tdesktop/0168-feat-regex-search-in-loaded-history.patch) | a .* button in the chat search finds messages by regex among the loaded ones, without asking the server | tele → chats, off |
| [175](../patches/tdesktop/0175-feat-sticker-captions.patch) | show the text attached to stickers in a bubble under them, and send or edit stickers with a caption. select part of a sticker's caption and quote it in a reply | tele → chats, off |
| [179](../patches/tdesktop/0179-feat-copy-or-delete-aliases-from-their-menu.patch) | right-click an alias in a profile or a message to copy or delete it, or open the profile | with 71 |
| [235](../patches/tdesktop/0235-feat-your-own-reaction-strip.patch) | choose how many reactions sit above the message menu and their order: click a reaction in the live preview to replace and pin it, drag to reorder | tele → chats, off |
| [254](../patches/tdesktop/0254-feat-send-quick-replies-by-their-exact-name.patch) | a message that is exactly /name sends your quick reply with that name instead of the text, and that quick reply is the first suggestion | tele → chats, off |
| [268](../patches/tdesktop/0268-feat-show-online-members-in-big-groups.patch) | big groups show how many members are online in the chat header and profile, like small groups do | tele → chats, off |
| [269](../patches/tdesktop/0269-feat-select-more-than-100-messages.patch) | select up to 10000 messages instead of 100; deleting and forwarding them goes out in parts of 100 | tele → chats, off |
| [279](../patches/tdesktop/0279-feat-hide-birthday-banners-and-effects.patch) | no birthday banners above the chat list, no confetti in profiles, no cake in the birthday row and no extra gift button in the message field on birthdays | tele → chats, off |
| [281](../patches/tdesktop/0281-feat-filter-chat-search-by-message-type.patch) | search a chat by message type: photos, videos, files, music, voice messages, round videos, gifs or links. without text it lists every message of that type | tele → chats, off |
| [288](../patches/tdesktop/0288-feat-turn-off-money.patch) | turn off money, telegram's wallet: it's gone from the app, ton connect requests can't be opened, money transfers in chats show as plain service messages, and money links only say it's off | tele → chats, off, needs a restart |
| [306](../patches/tdesktop/0306-fix-search-one-person-s-messages-by-type.patch) | searching one person's messages by type works: tele asks the server both ways and filters the rest itself | with 281 |
| [307](../patches/tdesktop/0307-feat-design-the-money-card-with-a-gift.patch) | money's card takes the colours, pattern and model of one of your collectible gifts, picked in money's ⋮ menu → card design or synced with your gift status. transfers you send in chats use its colours too | tele → chats, on |
| [313](../patches/tdesktop/0313-feat-hide-the-other-balances-above-the-money-card.patch) | hide the "you also have …" rows above the money card, here or by right-clicking one of them | tele → chats, off |
| [317](../patches/tdesktop/0317-feat-put-gifts-on-the-money-card-as-stickers.patch) | put your collectible gifts on the money card as stickers: drag them from the card design box or money's collectibles tab, move them around, and click one to take it off | with 307 |
| [322](../patches/tdesktop/0322-feat-filter-stickers-and-emoji-by-format.patch) | filter your sticker and emoji sets by format (static, animated, video or mixed), sort them, and archive or remove every shown set at once. the panel's search filters by format too, and custom emoji sets get their own list under stickers you have | tele → chats, off |

## messages

settings → tele → messages.

| # | what it does | toggle |
|---|---|---|
| [17](../patches/tdesktop/0017-feat-show-seconds-in-message-times.patch) | message times show seconds, like 14:03:21. service messages like joins and pins show their time too, with seconds | tele → messages, off |
| [18](../patches/tdesktop/0018-feat-keep-the-edit-history-of-messages.patch) | remembers what edited messages looked like while tele runs: right-click an edited message → edit history | tele → messages, off |
| [19](../patches/tdesktop/0019-feat-keep-deleted-messages.patch) | messages deleted by others or from your other devices stay in the chat until tele restarts, service messages too, faded as a whole or with a trash icon by the time. each chat gets a page with its kept deleted messages and a clear all button: chat menu → deleted messages | tele → messages, off |
| [25](../patches/tdesktop/0025-feat-open-links-without-confirmation.patch) | links with custom text open right away, without the confirmation | tele → messages, off |
| [26](../patches/tdesktop/0026-feat-open-disappearing-media-without-burning-it.patch) | view-once and timed media open without burning, and the sender still sees them unopened. message menu → mark as viewed burns them | tele → messages, off |
| [51](../patches/tdesktop/0051-feat-open-links-in-their-desktop-apps.patch) | spotify, steam, discord, zoom, teams, notion, slack and epic links open in their desktop apps when they're installed | tele → messages → open links in apps |
| [52](../patches/tdesktop/0052-feat-clean-tracking-parameters-from-links.patch) | the SUPER MAGA PALANTIR ICE PETER THIEL AI DATA HARVESTER 9000 remover: opened links lose their tracking parameters (utm, fbclid, si, gclid and [more](link-cleaner.md)). when it would change a link, its right-click menu offers open without cleaning. the same remover works on links in sent messages and captions, the rest of the text stays as it is | tele → messages, off |
| [53](../patches/tdesktop/0053-feat-reveal-spoilers-automatically.patch) | text and media spoilers are revealed right away, in chats and the chat list | tele → messages, off |
| [58](../patches/tdesktop/0058-feat-keep-messages-you-delete-yourself.patch) | messages you delete yourself are kept too, not only ones deleted by others | with 19 |
| [61](../patches/tdesktop/0061-feat-show-edit-history-as-a-chat.patch) | edit history opens as its own chat: every version as a full message with its media and time | with 18 |
| [69](../patches/tdesktop/0069-feat-skip-or-quote-deleted-messages-when-replying.patch) | replying to a message that got deleted meanwhile either drops the reply or quotes the deleted text | tele → messages |
| [77](../patches/tdesktop/0077-feat-rewrite-pasted-links-with-your-own-rules.patch) | links you paste are rewritten by your own rules, like x.com to fixupx.com. ctrl+z brings the original back. an editor for link rewrite rules: domains or regex patterns, presets for x, instagram, tiktok, reddit, bluesky and pixiv, and a field to test a link. the tiktok preset rewrites to tnktok.com, and the x preset can also rewrite to samekosabax.com and drops x's tracking parameters | tele → messages → link rewrites |
| [85](../patches/tdesktop/0085-feat-choose-when-links-get-previews-and-set-your-own.patch) | choose when links get previews: for all links, not for pasted links, or only ones you add. add a preview of any link to any message, with its size and position | tele → messages |
| [104](../patches/tdesktop/0104-feat-choose-which-app-opens-each-service.patch) | choose which app opens each service's links: the official app, an alternative like spotifast, the browser, or any program | tele → messages → open links in apps |
| [114](../patches/tdesktop/0114-feat-forward-protected-messages-as-copies.patch) | forward messages from chats that forbid it: tele sends copies and uploads their media again | tele → messages, off |
| [126](../patches/tdesktop/0126-feat-bookmark-messages-and-return-to-where-you-were-.patch) | bookmark messages from the message menu and jump back to them from the chat menu. after you send a message while scrolled up, a button returns you to where you were reading | tele → messages, off |
| [138](../patches/tdesktop/0138-feat-choose-the-map-service-for-locations.patch) | choose the map service that opens locations | tele → messages → open links in apps |
| [142](../patches/tdesktop/0142-feat-number-the-lines-of-long-code-blocks.patch) | long code blocks get line numbers, in regular and rich messages | tele → messages, off |
| [144](../patches/tdesktop/0144-feat-rewrite-only-the-link-preview.patch) | link rewrites can change only the link preview and keep your link as it is | with 77 |
| [147](../patches/tdesktop/0147-feat-remember-when-your-messages-were-read.patch) | the message menu keeps showing when a private chat read your message, even after telegram stops telling | tele → messages, on |
| [151](../patches/tdesktop/0151-feat-choose-which-deleted-messages-to-keep.patch) | choose which deleted messages to keep: in bot chats, in saved messages, and the ones you delete yourself | with 19 |
| [173](../patches/tdesktop/0173-feat-choose-how-quoted-names-of-deleted-messages-lin.patch) | the name in a quote of a deleted message can link to the author's profile or mention them | with 19 |
| [182](../patches/tdesktop/0182-feat-keep-deleted-messages-and-edit-history-after-a-.patch) | kept deleted messages and edit history survive a restart, encrypted, for 1, 7 or 30 days or forever. older tele versions can't read the kept history after this update | with 19 |
| [199](../patches/tdesktop/0199-feat-quote-rich-messages.patch) | select part of a rich message and pick quote and reply: the rich editor opens with the selection as a blockquote. a quote without an author no longer disappears when it's sent | tele → messages, on |
| [210](../patches/tdesktop/0210-feat-multiple-quotes-in-one-reply.patch) | quote several parts of a message in one reply: quoting again while replying with a quote adds the new part | tele → messages, on |
| [256](../patches/tdesktop/0256-feat-leave-kept-deleted-messages-out-of-the-chat-lis.patch) | kept deleted messages can stay out of the chat list and unread counts: the chat shows its last message that wasn't deleted, and their unread marks, mentions and notifications go away | with 19 |
| [267](../patches/tdesktop/0267-feat-hide-bubble-tails.patch) | message bubbles can lose their tails: the corner that pointed at the sender is rounded like the others | tele → messages, off |
| [270](../patches/tdesktop/0270-feat-no-outline-on-large-emoji.patch) | messages with a single emoji lose the white outline around it | tele → messages, off |
| [272](../patches/tdesktop/0272-feat-classic-text-padding-in-bubbles.patch) | bubbles without tails can use the text padding of older telegram desktop: 13 px on the sides and 7 on top | with 267 |
| [283](../patches/tdesktop/0283-feat-keep-deleted-chats-and-topics.patch) | chats and topics that get deleted, or that you leave or get removed from, stay in the list with their loaded messages until you delete them again | with 19 |
| [321](../patches/tdesktop/0321-feat-recover-deleted-channel-posts-from-forwards.patch) | open a deleted channel post from a forward of it and tele shows it again: it rebuilds the post from the forward in its place in the channel, marked like other kept deleted messages, and the time's tooltip says which forward it came from | with 19 |
| [329](../patches/tdesktop/0329-fix-loading-older-messages-no-longer-crashes-on-a-me.patch) | tele no longer crashes while loading older messages when one of them is deleted just as it loads | with 19 |

## sending

settings → tele → sending.

| # | what it does | toggle |
|---|---|---|
| [43](../patches/tdesktop/0043-feat-upload-media-in-several-chats-at-once.patch) | media uploads in several chats at once instead of waiting for each other. files in one chat still go one after another | tele → sending, off |
| [45](../patches/tdesktop/0045-feat-compute-messages-starting-with-via-calcmula.patch) | messages and captions starting with `= ` are computed with [calcmula](https://calcmula.app) and sent as the quoted query with `= result` below it. if it fails, nothing is sent and the text goes back into the field | tele → sending, off |
| [49](../patches/tdesktop/0049-feat-move-late-sent-messages-to-the-bottom.patch) | a message that took long to send moves to the bottom of the chat once it's sent, so it's clear when it went out | tele → sending, off |
| [50](../patches/tdesktop/0050-feat-queue-messages-behind-an-uploading-media.patch) | messages sent while a media is uploading wait for it and go out after it, in order | tele → sending, off |
| [67](../patches/tdesktop/0067-feat-skip-the-rich-message-prompt-on-paste.patch) | no rich message prompt when you paste formatted text | tele → sending, off |
| [80](../patches/tdesktop/0080-feat-preview-calcmula-results-while-typing.patch) | the calcmula result shows above the input field while you type, like an inline bot. a failed calcmula message goes back into the field once instead of doubling | tele → sending, off |
| [93](../patches/tdesktop/0093-feat-send-gifs-as-videos-and-videos-as-gifs.patch) | send gifs as videos and videos as gifs: in the send box, from a message's menu, and with right-click in the gif panel. a gif becomes a video without re-encoding, a video becomes a gif by dropping its sound | tele → sending, on |
| [95](../patches/tdesktop/0095-feat-send-scheduled-messages-on-time.patch) | scheduled messages are sent by tele itself at the set time while it's online, archived chats included, and one that can't be sent says why | tele → sending, off |
| [99](../patches/tdesktop/0099-feat-save-drafts-for-later.patch) | saved drafts: keep several drafts per chat, with media or rich messages, in a drafts section that looks like a chat. edit them like messages, send them now or to another chat, and bring back drafts you discarded | tele → sending → drafts |
| [100](../patches/tdesktop/0100-feat-send-photos-in-hd-by-default.patch) | photos go out in hd by default | tele → sending, on |
| [107](../patches/tdesktop/0107-feat-attach-media-above-the-field-beta.patch) | attach media above the input field instead of in a full-window box: reorder, remove, group or send as files right there, edit photos, see the album as a grid, and the unsent media stays in the chat. attached media above the field get a caption each and everything the send box has: self-destruct timer, caption above, hd, price, effects and the send menu. they can be saved as drafts, which keep video edits and price, and an edited draft video says its edits apply when sent. | tele → sending, off |
| [118](../patches/tdesktop/0118-feat-send-replies-to-older-messages-past-the-queue.patch) | replies to messages older than the uploading media don't wait in the queue | with 50 |
| [119](../patches/tdesktop/0119-feat-send-right-away-on-double-enter.patch) | enter twice sends a queued message right away | with 50 |
| [125](../patches/tdesktop/0125-feat-hide-the-gift-button-in-the-message-field.patch) | hide the gift button in the message field | tele → sending, off |
| [130](../patches/tdesktop/0130-feat-confirm-stickers-gifs-and-voice-messages-before.patch) | stickers, gifs and voice messages wait for a second click before sending | tele → sending, off |
| [135](../patches/tdesktop/0135-feat-record-voice-without-fading.patch) | voice messages record without the fade-in at the start and keep their first 0.4 seconds, which telegram desktop cuts | tele → sending, off |
| [148](../patches/tdesktop/0148-feat-calcmula-suggestions-and-sending-without-calcul.patch) | calcmula suggestions while typing, each can be sent as its own result, and alt+enter sends without calculating | with 80 |
| [157](../patches/tdesktop/0157-feat-send-an-audio-file-as-a-voice-message.patch) | send an audio file as a voice message with a waveform, from its right-click menu in the send box | tele → sending, on |
| [158](../patches/tdesktop/0158-feat-download-folders-per-chat.patch) | downloads go into a folder per chat, and any chat can get its own folder from the chat menu | tele → sending, off |
| [159](../patches/tdesktop/0159-feat-resize-the-message-field.patch) | drag the edge above the message field to set its minimum height | tele → sending, off |
| [161](../patches/tdesktop/0161-feat-translate-your-message-before-sending.patch) | translate your message before sending from the field's right-click menu or the send menu. ctrl+z brings the original back | tele → sending, on |
| [176](../patches/tdesktop/0176-feat-inline-calcmula-results-after.patch) | type an expression and = to see the calcmula result greyed out after it, → or tab inserts it | with 45 |
| [226](../patches/tdesktop/0226-feat-see-and-release-messages-queued-behind-an-uploa.patch) | messages waiting behind an upload say what they wait for, and can be sent now or dropped from their menu | with 50 |
| [236](../patches/tdesktop/0236-feat-captioned-stickers-go-to-the-docked-media.patch) | stickers with a caption go to the media attached above the field, and stickers and gifs can be attached there from their panels | with 107 |
| [242](../patches/tdesktop/0242-feat-choose-how-silent-videos-are-sent.patch) | choose whether videos without sound are sent as gifs or as videos | tele → sending |
| [245](../patches/tdesktop/0245-feat-markdown-renders-as-you-type.patch) | markdown renders while you type: bold, italic, strike, spoilers, code and code blocks, with the markers kept and dimmed. lines starting with > become quotes, >! expandable quotes | tele → sending, off |
| [259](../patches/tdesktop/0259-feat-forward-messages-one-by-one.patch) | forwarded messages go out one at a time instead of as one batch. albums stay together, and forwarding many at once can hit rate limits | tele → sending, off |
| [260](../patches/tdesktop/0260-feat-record-voice-in-higher-quality.patch) | voice messages can be recorded at 128 kbps instead of 32, for clearer sound and 4 times bigger files | tele → sending, off |
| [261](../patches/tdesktop/0261-feat-compress-photos-less.patch) | photos are compressed at jpeg quality 94 instead of 87 | tele → sending, off |
| [262](../patches/tdesktop/0262-feat-thinner-brush-in-the-photo-editor.patch) | the photo editor's brush goes down to 1 px instead of 3.4 px | tele → sending, off |
| [280](../patches/tdesktop/0280-feat-mention-several-people-in-a-row.patch) | right-click or tab in the @ list adds the person and opens the list again for the next one, and ctrl+click mentions by name instead of @username | tele → sending, off |
| [318](../patches/tdesktop/0318-fix-confirm-stickers-sent-from-sticker-set-boxes.patch) | stickers sent from a sticker set's box also wait for a second click | with 130 |

## notifications

settings → tele → notifications.

| # | what it does | toggle |
|---|---|---|
| [128](../patches/tdesktop/0128-feat-send-silently-by-default.patch) | send silently by default, everywhere or per chat from the chat menu. the send menu offers sending with sound instead | tele → notifications, off |
| [133](../patches/tdesktop/0133-feat-hide-unread-counters.patch) | hide unread counters on folder tabs and the taskbar or tray, leave out the archive, and leave out accounts from their right-click menu | tele → notifications, off |
| [155](../patches/tdesktop/0155-feat-notify-when-people-come-online.patch) | get a notification when chosen people come online, from their profile or chat menu | tele → notifications, off |
| [156](../patches/tdesktop/0156-feat-mute-folders-and-silence-chats-completely.patch) | mute a whole folder on this device, and silence chats completely, mentions and replies included | tele → notifications, on |
| [205](../patches/tdesktop/0205-feat-notification-centre.patch) | a notification centre in the main menu: tele toasts, updates, sent crash reports, online alerts and server notices in one list, kept per account for 30 days. rate limits show a toast with a countdown from 5 seconds, a bar above the chat list from a minute, and a notice when they end, instead of a silent hang. the toasts and the bar are off by default and only count waits on things you do | tele → notifications, on |
| [212](../patches/tdesktop/0212-fix-rate-limit-notices-for-slowmode-and-download-thr.patch) | slowmode and download throttling count as rate limits too, and rate limits can be logged in the notification centre | tele → notifications, on |
| [232](../patches/tdesktop/0232-feat-mentions-and-replies-in-the-notification-centre.patch) | mentions and replies from groups, muted ones included, are logged in the notification centre. click one to open the message | tele → notifications, on |
| [239](../patches/tdesktop/0239-fix-notification-centre-shows-whole-entries.patch) | the notification centre shows whole entries, long ones with show more, and plays the press ripple | with 205 |
| [240](../patches/tdesktop/0240-feat-copied-values-in-the-notification-centre.patch) | copy toasts are logged in the notification centre with the copied value: click it to copy it again | tele → notifications, on |
| [246](../patches/tdesktop/0246-feat-reply-and-mention-badges-in-the-notification-ce.patch) | replies and mentions in the notification centre have a reply or @ badge on the sender's userpic | with 232 |

## menus

settings → tele → menus.

| # | what it does | toggle |
|---|---|---|
| [29](../patches/tdesktop/0029-feat-show-the-message-id-in-the-message-menu.patch) | the message menu ends with the message id, click it to copy | tele → menus, off |
| [31](../patches/tdesktop/0031-feat-jump-to-the-first-message-of-a-chat.patch) | jump to the first message, in the chat menu | tele → menus, off |
| [33](../patches/tdesktop/0033-feat-view-messages-and-telegram-objects-as-tl.patch) | view as tl in the message menu, and for chats, profiles, members, topics, stickers and sets, custom emoji, gifts, stories and folders: fetches the object from the server and opens it on [schema.jppgr.am](https://schema.jppgr.am) | tele → menus, off |
| [55](../patches/tdesktop/0055-feat-copy-custom-emoji-ids-from-the-message-menu.patch) | right-click a custom emoji in a message to copy its id | tele → menus, off |
| [57](../patches/tdesktop/0057-feat-reorder-and-hide-message-menu-items.patch) | reorder and hide items of the message menu, items it doesn't know keep their place | tele → menus |
| [87](../patches/tdesktop/0087-feat-save-messages-as-a-picture.patch) | shot: save selected messages, or one message, as a picture from the message menu, with or without the chat background and dates | tele → menus, off |
| [105](../patches/tdesktop/0105-feat-scale-shots-up-to-4x-and-show-your-messages-as-.patch) | shots render at 1x to 4x with sharp text, bubbles, userpics, icons, media and animated emoji, can show your own messages as incoming, and the selection clears when a shot opens | with 87 |
| [112](../patches/tdesktop/0112-feat-choose-what-shots-show.patch) | choose what shots show: names, userpics, reactions, time and checks, replies, forwarded headers, buttons and link previews | with 87 |
| [139](../patches/tdesktop/0139-feat-copy-messages-as-markdown-or-html.patch) | copy messages as markdown or html from the message menu | tele → menus, off |
| [145](../patches/tdesktop/0145-feat-open-the-message-menu-next-to-the-bubble.patch) | right-clicking beside a bubble opens its message menu | tele → menus, off |
| [149](../patches/tdesktop/0149-feat-open-view-as-tl-inside-tele.patch) | view as tl opens inside tele, titled with the object's constructor. with -teleoffline it opens in the browser | with 33 |
| [171](../patches/tdesktop/0171-feat-rearrange-menus-with-groups-and-submenus-in-a-m.patch) | tele's own layout for the message, chat, profile, chat list, folder, send and field menus, with groups, submenus and thin or thick separators. an editor rearranges, hides and groups items with a live preview and presets, alt+right-click opens it from a menu. clicking the eye on a greyed item in the editor turns on the setting it needs | tele → menus |
| [255](../patches/tdesktop/0255-feat-copy-file-paths-from-the-message-menu.patch) | copy the full path of a downloaded file from its message menu | tele → menus, off |
| [274](../patches/tdesktop/0274-fix-sharp-boost-icons-and-button-emoji-in-scaled-sho.patch) | shots scaled up keep boost icons and custom emoji in bot buttons sharp | with 105 |
| [301](../patches/tdesktop/0301-feat-remove-all-your-messages-from-a-chat.patch) | remove my messages in the chat menu deletes all your messages in a chat, group or topic for everyone, newest first, after saying how many. the same item stops it | tele → menus, off |
| [332](../patches/tdesktop/0332-feat-show-skipped-messages-in-shots.patch) | a shot of messages that aren't next to each other can show how many were skipped between them, as a "2 messages skipped" badge | with 87 |
| [333](../patches/tdesktop/0333-feat-restrict-members-from-message-menus-and-find-th.patch) | group admins can restrict someone from their message or userpic menu without deleting the message, and the add exception, add admin and remove user pickers find people tele already knows by their numeric id, members or not | tele → menus, on |
| [1004](../patches/Telegram/lib_ui/0004-fix-icon-emoji-stay-sharp-in-renders-at-a-higher-rat.patch) | icons drawn inside text, like the boost mark next to names, stay sharp in shots scaled up | with 105 |

## privacy

settings → tele → privacy.

| # | what it does | toggle |
|---|---|---|
| [3](../patches/tdesktop/0003-feat-add-an-option-to-hide-stories-everywhere.patch) | hides stories everywhere: no stories bar, no rings around userpics, no stories in profiles | tele → privacy, off, needs a restart |
| [4](../patches/tdesktop/0004-feat-add-an-option-to-watch-stories-invisibly.patch) | watch stories without showing up among the viewers. reactions and replies still reveal you | tele → privacy, off |
| [16](../patches/tdesktop/0016-feat-ignore-users-by-hiding-or-fading-their-messages.patch) | ignore users from their userpic menu: their messages fade or disappear, the list lives in settings | tele → privacy |
| [27](../patches/tdesktop/0027-feat-allow-screenshots-of-disappearing-media.patch) | view-once and timed media can be screenshotted and recorded | tele → privacy, off |
| [32](../patches/tdesktop/0032-feat-add-ghost-mode.patch) | ghost mode: no read receipts, typing, online status or story views, each switchable, and per chat always or never from the chat menu. optionally reads a chat when you reply, and sends messages as scheduled a few seconds ahead so sending doesn't put you online. the message menu has mark as read up to here, and the side menu has a quick toggle | tele → privacy, off |
| [64](../patches/tdesktop/0064-feat-more-ghost-mode-options.patch) | more ghost mode: its main menu toggle is optional, sending a message while the online status is hidden sets you offline again right away, and reaction animations play once instead of over and over | tele → privacy |
| [73](../patches/tdesktop/0073-feat-pick-ignored-users-and-ghost-chats-like-privacy.patch) | ignored users and ghost chats are picked from a searchable list, like privacy exceptions | tele → privacy |
| [94](../patches/tdesktop/0094-feat-keep-drafts-on-this-device.patch) | drafts stay on this device and never go to the cloud. a button clears the ones already there | tele → privacy, off |
| [111](../patches/tdesktop/0111-feat-never-block-screen-capture.patch) | tele never blocks screenshots, screen recording or screen sharing, protected chats and disappearing media included | tele → privacy, on |
| [160](../patches/tdesktop/0160-feat-streamer-mode.patch) | streamer mode: tele is hidden from screen capture, notifications show no names or text, and the window title and every phone number are hidden | tele → privacy, off |
| [166](../patches/tdesktop/0166-feat-hide-messages-by-keyword-or-regex.patch) | hide messages by keyword or regex, everywhere and per chat, like ignored users | tele → privacy |
| [187](../patches/tdesktop/0187-feat-local-password-for-stars-and-gift-actions.patch) | a local password before transferring, converting, selling, upgrading, buying or sending gifts, paid reactions, paid media and subscriptions, each switchable | tele → privacy |
| [217](../patches/tdesktop/0217-feat-local-password-for-bot-payments-and-paid-messag.patch) | the local password can also be asked before bot payments, paid messages and suggested posts | with 187 |
| [227](../patches/tdesktop/0227-feat-show-pending-ghost-scheduled-messages.patch) | messages ghost mode holds back to send later show in the chat: right-click one to send it now or cancel it | tele → privacy, on |
| [228](../patches/tdesktop/0228-feat-ignored-users-and-hidden-words-can-stay-silent.patch) | messages from ignored users and with hidden words don't notify or count as unread, and the chat list doesn't preview them | tele → privacy, on |
| [229](../patches/tdesktop/0229-fix-invisible-stories-follow-ghost-settings-and-surv.patch) | watching stories invisibly follows per-chat ghost settings, keeps who you watched across restarts, and asks before a live story, which shows you to its author | with 4 |
| [293](../patches/tdesktop/0293-fix-closing-the-rich-editor-keeps-drafts-on-this-dev.patch) | closing the rich message editor saves its draft on this device and closes, when drafts stay on this device and in secret chats, instead of trying the cloud | with 94 |

## profiles and ids

settings → tele → profiles and ids.

| # | what it does | toggle |
|---|---|---|
| [13](../patches/tdesktop/0013-feat-show-gift-ids.patch) | a copyable gift id at the top of the collectible gift card, which only says a gift is on the ton blockchain while it really is there | tele → profiles and ids, off |
| [14](../patches/tdesktop/0014-feat-show-the-peer-id-as-its-own-profile-row.patch) | the peer id gets its own profile row instead of trailing the bio, optionally without spaces or in bot api style (-100… for channels) | tele → profiles and ids, off (see 46) |
| [23](../patches/tdesktop/0023-feat-show-the-data-center-in-profiles.patch) | a dc row in profiles: the data center the account or chat lives in | tele → profiles and ids, off |
| [46](../patches/tdesktop/0046-feat-move-show-peer-ids-into-tele-settings.patch) | show peer ids moved from experimental settings into tele | tele → profiles and ids |
| [48](../patches/tdesktop/0048-feat-open-collectible-gifts-in-see.tg.patch) | an open in see.tg link on collectible gift cards | tele → profiles and ids, off |
| [65](../patches/tdesktop/0065-feat-show-ids-on-regular-gifts.patch) | a copyable id on regular gifts too, not only on collectible ones | tele → profiles and ids, off |
| [75](../patches/tdesktop/0075-feat-show-names-instead-of-phone-numbers-in-chat-hea.patch) | people who shared their number with you but aren't in your contacts keep their name in the chat header instead of the number | tele → profiles and ids, off |
| [78](../patches/tdesktop/0078-feat-name-people-only-for-you.patch) | give people a name only you see, from their chat menu. their profile keeps the real one | tele → profiles and ids → custom names |
| [83](../patches/tdesktop/0083-feat-show-collectible-prices-at-the-purchase-date.patch) | collectible usernames and numbers show their dollar price at the purchase date, not today's | tele → profiles and ids, off |
| [96](../patches/tdesktop/0096-feat-show-id-and-dc-in-one-row.patch) | when both are shown, the dc goes next to the id in one profile row | tele → profiles and ids, off |
| [143](../patches/tdesktop/0143-feat-hide-the-collectible-status-tooltip-in-profiles.patch) | no tooltip for collectible statuses in profiles | tele → profiles and ids, off |
| [172](../patches/tdesktop/0172-feat-hide-phone-numbers-in-profiles.patch) | the mobile row is hidden in every profile, yours included | tele → profiles and ids, off |
| [184](../patches/tdesktop/0184-feat-send-several-gifts-at-once.patch) | send several copies of a gift at once, each with the same caption | tele → profiles and ids, off |
| [185](../patches/tdesktop/0185-feat-dim-hidden-gifts-and-select-several.patch) | hidden gifts are dimmed with a clear badge, and a select mode shows, hides, pins and transfers several gifts at once | tele → profiles and ids, off |
| [186](../patches/tdesktop/0186-feat-search-gifts.patch) | search a profile's collectible gifts by name, number, model, backdrop or symbol, with filter chips | tele → profiles and ids, off |
| [189](../patches/tdesktop/0189-fix-show-a-chat-s-data-center-from-its-first-photo.patch) | a group's or channel's data center comes from its first photo, marked uncertain when its photos disagree | with 23 |
| [190](../patches/tdesktop/0190-feat-more-bulk-gift-actions.patch) | the gift select mode also sells, removes from sale, converts to stars and adds to a collection, and says why an action doesn't fit the selection | with 185 |
| [196](../patches/tdesktop/0196-feat-show-the-media-s-data-center-in-the-media-viewe.patch) | the media viewer shows which data center the open photo, video or file is stored on | with 23 |
| [197](../patches/tdesktop/0197-feat-gift-studio.patch) | a gift studio: build any collectible from real parts (collection, model, backdrop, symbol, number) on a live cover in several layouts, and export png, mp4, gif or a tgs sticker that passes telegram's checks, with text as outlines. favorites, sweeps and contact sheets, parts from @GiftChanges (api.changes.tg). tgs stickers from the gift studio carry an invisible mark saying they were made with tele's gift studio. it holds no user, account, device or time data | tele → profiles and ids, gift menus |
| [198](../patches/tdesktop/0198-feat-fake-gift-upgrades.patch) | fake upgrades: the real upgrade box and spin for any upgradable gift, with the model, backdrop and symbol rolled locally by rarity and the real next number. nothing is sent and no stars are spent | tele → profiles and ids, on |
| [204](../patches/tdesktop/0204-feat-gift-grid-builder.patch) | a gift grid builder: fill a profile-like grid cell by cell with collectibles or regular gifts, custom ribbons, pins and hidden marks, drag to reorder, save grids, and export png, gif or mp4 with an optional profile frame | tele → profiles and ids |
| [208](../patches/tdesktop/0208-feat-show-usernames-for-invisible-names.patch) | people whose name is empty or invisible show their @username instead, or a phrase you choose when they have none | tele → profiles and ids, off |
| [209](../patches/tdesktop/0209-feat-show-hidden-characters.patch) | names, bios and other profile texts made only of invisible characters show those characters, so you can see something is there | tele → profiles and ids, off |
| [213](../patches/tdesktop/0213-fix-gift-batches-survive-flood-waits-and-bad-items.patch) | bulk gift actions wait out telegram's limits and skip gifts that can't be done yet instead of stopping, then say what was skipped and why | with 190 |
| [234](../patches/tdesktop/0234-feat-more-gifts-and-models-in-the-gift-studio.patch) | the gift studio opens on a random gift, lists the newest collections first, and adds the original model, your own .tgs models, regular gifts, a teddy bear collection and renaming the model, backdrop and symbol on the card | with 197 |
| [247](../patches/tdesktop/0247-feat-open-anyone-s-gifts-in-the-gift-grid.patch) | open anyone's gifts, or one of their collections, in the gift grid, or import them into a grid. big grids scroll, rows can be left out of the export and single gifts hidden | with 204 |
| [248](../patches/tdesktop/0248-feat-rarity-tiers-and-pills-in-the-gift-studio.patch) | crafted models show their rarity tier, and rarities in the gift studio sit in coloured pills | with 197 |
| [253](../patches/tdesktop/0253-fix-copy-peer-ids-as-plain-digits.patch) | copying a peer id from its profile row gives plain digits, even when the row shows them with spaces | with 14 |
| [265](../patches/tdesktop/0265-feat-show-when-media-was-uploaded-in-the-media-viewe.patch) | the media viewer shows when a photo or file was uploaded, when that differs from the message date, like in forwards | tele → profiles and ids, off |
| [266](../patches/tdesktop/0266-feat-copy-the-owner-id-of-sticker-sets.patch) | copy the id of the account that made a sticker or emoji set from the set's menu | tele → profiles and ids, off |
| [282](../patches/tdesktop/0282-feat-peek-at-a-hidden-last-seen.patch) | peek at a last seen your own privacy hides: tele briefly shares yours with that person, reads theirs and puts your settings back, even after a crash | tele → profiles and ids, off |
| [299](../patches/tdesktop/0299-feat-use-the-blurred-profile-photo-as-the-profile-ba.patch) | profiles use a blurred, darkened copy of the profile photo as the background of their header, instead of the profile colour or gift backdrop | tele → profiles and ids, off |
| [304](../patches/tdesktop/0304-feat-fill-the-whole-profile-with-the-blurred-photo-s.patch) | with the blurred photo background on, the whole profile takes the colour of the photo's lower edge, not only its header, with the text kept readable | with 299 |
| [319](../patches/tdesktop/0319-feat-blurred-profile-photo-background-out-of-beta.patch) | the blurred photo background of profiles is out of beta | with 299 |

### gift studio

the gift studio builds any collectible from real parts and exports it, the grid builder lays out a whole profile of gifts, and fake upgrades spin any upgradable gift without spending anything (201, 209 and 202 above). open them from this page or from a gift's menu.

tgs files exported from the gift studio carry an invisible mark that says they were made with tele's gift studio. it holds nothing about you: no user, account, device or time.

## bots

settings → tele → bots.

| # | what it does | toggle |
|---|---|---|
| [5](../patches/tdesktop/0005-feat-show-bot-button-payloads-in-tooltips.patch) | hovering a bot button shows what it carries: callback data, links, inline queries, web apps and more | tele → bots, off |
| [66](../patches/tdesktop/0066-feat-send-inline-results-without-via.patch) | inline bot results go out as your own messages, without via @bot | tele → bots, off |
| [231](../patches/tdesktop/0231-feat-show-the-start-parameter-on-the-start-button.patch) | a bot opened by a link shows the start parameter on its start button | tele → bots, off |
| [233](../patches/tdesktop/0233-feat-no-edited-mark-on-bot-messages.patch) | bot messages don't show the edited mark, since bots edit messages to update them | tele → bots, off |
| [243](../patches/tdesktop/0243-feat-skip-the-mini-app-terms-box-for-trusted-apps.patch) | links to a mini app you've already opened skip its terms box | tele → bots, off |
| [249](../patches/tdesktop/0249-feat-never-open-web-apps-in-fullscreen.patch) | mini apps always open in a window and can't go fullscreen | tele → bots, off |

## debug

settings → tele → debug.

| # | what it does | toggle |
|---|---|---|
| [88](../patches/tdesktop/0088-feat-debug-logs-and-an-mtproto-inspector.patch) | a debug page: debug logs on or off, open the logs or tele folder, clear logs, and an mtproto inspector for the logs that filters requests, expands objects, opens entries on [schema.jppgr.am](https://schema.jppgr.am) and opens things from message and chat menus | tele → debug |
| [195](../patches/tdesktop/0195-feat-mtproto-console.patch) | an mtproto console: call any api method with your own session in text, json or json5, with autocomplete, schema hints, validation, a result tree and history. destructive methods ask first, star methods ask for the local password | tele → debug, ctrl+alt+m |
| [218](../patches/tdesktop/0218-fix-confirm-more-irreversible-methods-in-the-mtproto.patch) | the mtproto console asks before more methods that can't be undone | with 195 |
| [273](../patches/tdesktop/0273-feat-fix-fonts-picked-in-chat-settings.patch) | a font picked in chat settings that comes out shifted or cut off, like google sans, can be measured by its real letters and drawn through directwrite, which reads the line heights such fonts mean (windows) | tele → debug, off, needs a restart |
| [278](../patches/tdesktop/0278-feat-turn-on-the-wallet-before-telegram-does.patch) | the wallet from telegram desktop 7.3 can be turned on before telegram enables it for your account. the server may still refuse it | tele → debug, off, needs a restart |
| [284](../patches/tdesktop/0284-feat-secret-chats-prototype.patch) | a secret chats prototype, ported from [freshGram](https://github.com/Snowy-Fluffy/freshGram): start and accept secret chats with text, replies, typing and read marks, and compare encryption keys. needs a local passcode. secret chats send and receive photos, videos, files, music, voice and round messages, gifs and stickers up to 100 mb, and show locations and contacts they receive. set a self-destruct timer in a secret chat from the button in the message field or the chat menu: messages disappear for both of you after they're read. timed photos and videos open while you hold them, and screenshots are announced. a partner's new name shows in the chat when it changes | tele → debug, off, needs a restart |
| [285](../patches/tdesktop/0285-feat-update-the-secret-phrase-of-wallets-without-a-b.patch) | a wallet without a backup gets an update secret phrase button in keys & backup: you write down new words, the old ones stop working and the network takes a small fee | tele → debug, off |
| [287](../patches/tdesktop/0287-feat-send-while-an-old-wallet-stays-on-this-device.patch) | keep using your wallet while the keys of a wallet you used before stay on this device, instead of having to remove them first. only when this device also holds your current wallet's key | tele → debug, off |
| [298](../patches/tdesktop/0298-feat-open-the-mtproto-inspector-and-console-as-panel.patch) | the mtproto inspector and console open as tele panels, like the money window, that can be resized and keep the keyboard focus in their page | with 88 |
| [310](../patches/tdesktop/0310-build-take-wallet-engine-from-gettele-money-for-priv.patch) | tele builds money's wallet engine from gettele/money, a copy of telegram's engine that can import private keys | with 311 |
| [311](../patches/tdesktop/0311-feat-import-wallets-from-private-keys.patch) | import a wallet into money from its private key, not only from secret words. such a wallet is never backed up to telegram, and you can switch it to 12 secret words later | tele → debug, off |
| [312](../patches/tdesktop/0312-feat-copy-secret-words-without-waiting.patch) | every list of secret words in money gets a copy words link, and showing them no longer ends with the "sure done?" check | tele → debug, on |
| [314](../patches/tdesktop/0314-build-fetch-litehtml-for-html-bubbles.patch) | tele downloads litehtml, the html engine of html bubbles, while it builds | with 315 |
| [315](../patches/tdesktop/0315-feat-render-html-cards-with-litehtml-and-run-their-s.patch) | html bubbles β: .tgw files show as html cards that can run their own scripts, for everyone using tele with the option on; other apps see a file | tele → debug, off |
| [316](../patches/tdesktop/0316-feat-show-html-bubbles-in-a-playground-chat-and-for-.patch) | an html playground chat shows what you type there as an html card, and .tgw files you get open as cards in the chat | with 315 |
| [326](../patches/tdesktop/0326-fix-html-cards-no-longer-crash-when-their-message-go.patch) | an html card no longer crashes tele when its message is rebuilt or removed while the mouse is over a link or button in it | with 316 |
| [331](../patches/tdesktop/0331-fix-me-and-other-peer-shortcuts-work-everywhere-in-t.patch) | in the mtproto console, `me` no longer fails with INPUT_FETCH_ERROR, and peers can be written as `me`, `@user` or an id where a method wants a notify or dialog peer too | with 195 |
| [1003](../patches/Telegram/lib_ui/0003-feat-let-picked-fonts-use-their-real-metrics-on-wind.patch) | the part of the picked font fix that lives in the ui library | with 273 |

## server

settings → tele → server.

| # | what it does | toggle |
|---|---|---|
| [9](../patches/tdesktop/0009-feat-apply-verification-and-marks-from-the-tele-serv.patch) | checkmarks, custom verification, scam, fake and support marks from the [tele server](server.md), shown exactly like telegram's own. custom verification icons animate, member lists update as soon as the data arrives, and refresh now fetches it right away | tele → server, on |
| [37](../patches/tdesktop/0037-feat-send-crash-reports-to-the-tele-server.patch) | when tele crashed, the next start offers to send the crash report to the tele server instead of telegram. nothing leaves without your click | tele → server, on with the server |
| [81](../patches/tdesktop/0081-feat-clear-server-data-and-explain-custom-verificati.patch) | clear the tele server's saved data, badges included. click a custom verification icon to see what it means: its description, with the icon next to it | tele → server → clear cached data |
| [91](../patches/tdesktop/0091-feat-usernames-from-the-tele-server.patch) | the tele server can give accounts extra @usernames, see [running your own server](server.md#running-your-own-server). a server username wins over the real one, your own aliases win over both | tele → server, on |
| [206](../patches/tdesktop/0206-feat-server-notices.patch) | notices from the tele server in the notification centre, optionally as a one-time coloured toast | tele → server, on |

## backup

settings → tele → backup.

| # | what it does | toggle |
|---|---|---|
| [106](../patches/tdesktop/0106-feat-export-and-import-tele-settings.patch) | export tele settings to a file or as text and import them on any account, system or tele version, with a preview first. people and device settings are optional | tele → backup |
| [263](../patches/tdesktop/0263-feat-bigger-faster-chat-export.patch) | chat export puts 10000 messages in each html file instead of 1000 and downloads files in 1 MB parts instead of 128 KB | tele → backup, off |

## updates

settings → tele → updates.

| # | what it does | toggle |
|---|---|---|
| [6](../patches/tdesktop/0006-feat-update-from-the-tele-github-releases.patch) | self-updates from these releases on windows, linux and macos, signed with ed25519. a failed update is retried sooner and a broken download continues where it stopped | tele → updates, on |
| [39](../patches/tdesktop/0039-feat-show-what-s-new-in-tele-after-an-update.patch) | after an update, you get a message with what's new in that tele version, visible only to you. fresh installs skip it | tele → updates, on |
| [74](../patches/tdesktop/0074-feat-show-what-s-new-in-a-local-tele-chat.patch) | what's new comes from a local tele chat with its own profile, grouped by settings page, once per account the first time you open it after an update. a button opens the full changelog | with 39 |
| [324](../patches/tdesktop/0324-fix-updates-on-macos-keep-the-dock-icon.patch) | on macos, an update replaces what's inside tele.app instead of the whole app, so tele stays on its dock icon instead of showing up as a second one. the update to this version still makes one duplicate | with 6 |

## everywhere

always on, or without a switch of their own.

| # | what it does | toggle |
|---|---|---|
| [1](../patches/tdesktop/0001-feat-show-the-tele-build-number-in-the-title-bar.patch) | the title bar shows which tele build you're on | always on, see 10 |
| [2](../patches/tdesktop/0002-feat-add-a-tele-section-to-the-settings.patch) | the tele section in settings | always on |
| [7](../patches/tdesktop/0007-feat-rename-the-app-to-tele.patch) | the app is called tele: `tele.exe`, its own taskbar entry, links point here. linux and macos builds are their own app, so they don't clash with an installed telegram | always on |
| [11](../patches/tdesktop/0011-feat-remove-the-account-limit.patch) | no account limit (well, 1536) | always on |
| [12](../patches/tdesktop/0012-feat-show-checkmarks-and-custom-verification-everywh.patch) | checkmarks and custom verification in the account list, the main menu, the settings header and, optionally, next to sender names in messages. badges go in telegram's order everywhere: custom verification, name, emoji status, checkmark, and the premium star stays visible next to checkmarks | always on, in messages: tele → chats, off |
| [15](../patches/tdesktop/0015-feat-copy-links-to-tele-settings.patch) | right-click any tele setting to copy a link that opens it | always on |
| [20](../patches/tdesktop/0020-fix-fade-every-unsupported-experimental-option.patch) | experimental options your system doesn't support are faded completely, title included | always on |
| [28](../patches/tdesktop/0028-feat-copy-the-callback-data-of-bot-buttons.patch) | right-click over a bot button to copy its callback data, inline query, web app url and so on | always on |
| [36](../patches/tdesktop/0036-fix-stop-maximized-windows-jittering-on-monitors-wit.patch) | a maximized window no longer jitters on a monitor without a taskbar (windows). fullscreen windows like the media viewer no longer have a 1 px gap at the edges (windows) | always on |
| [40](../patches/tdesktop/0040-feat-call-the-app-tele-everywhere.patch) | the app calls itself tele everywhere: tray menu, crash window, system menus and more | always on |
| [42](../patches/tdesktop/0042-feat-group-and-search-tele-settings.patch) | tele settings are grouped into pages like the main settings, with short descriptions and their own search field, and the main settings search finds them too. old links to tele settings open the right page | always on |
| [44](../patches/tdesktop/0044-feat-reply-timestamps-for-media-in-rich-messages.patch) | time codes like 1:23 in a reply to a rich message link to its video or audio, the first one if there are several | always on |
| [47](../patches/tdesktop/0047-feat-show-the-tele-build-in-the-main-menu.patch) | the main menu shows the tele build next to the version | always on |
| [54](../patches/tdesktop/0054-feat-move-tele-tools-to-the-bottom-of-the-message-me.patch) | tele's items sit at the bottom of the message menu: view as tl, then the message id | always on |
| [56](../patches/tdesktop/0056-fix-change-the-speed-instead-of-moving-the-media-vie.patch) | dragging while holding a video to speed it up changes the speed instead of moving the media viewer window, and the speedup no longer stops by itself | always on |
| [59](../patches/tdesktop/0059-feat-show-server-and-updates-on-the-tele-settings-pa.patch) | the server and updates rows sit right on the tele settings page | always on |
| [60](../patches/tdesktop/0060-feat-pick-brush-colors-from-the-image.patch) | an eyedropper in the photo editor picks the brush color from the image | always on |
| [63](../patches/tdesktop/0063-feat-group-the-tele-interface-and-profile-settings.patch) | the interface and the profiles and ids pages are split into groups | always on |
| [70](../patches/tdesktop/0070-feat-add-test-server-accounts-with-a-plain-right-cli.patch) | a plain right-click on add account offers the test server | always on |
| [79](../patches/tdesktop/0079-feat-add-launch-flags-to-turn-off-tele-s-own-network.patch) | launch flags that keep tele off the network for one launch, see [launch flags](launch-flags.md) | always on |
| [86](../patches/tdesktop/0086-feat-turn-username-into-a-t.me-link-in-the-link-box.patch) | in the link box (ctrl+k) and in the button links of the rich message editor, @username becomes a t.me link | always on |
| [89](../patches/tdesktop/0089-feat-new-tele-app-and-tray-icons.patch) | tele's own app and tray icons | always on |
| [90](../patches/tdesktop/0090-fix-name-the-item-Copy-Callback-Data-like-telegram-d.patch) | the menu item is called copy callback data, like in telegram | with 28 |
| [92](../patches/tdesktop/0092-fix-open-custom-emoji-in-rich-and-emoji-only-message.patch) | custom emoji in rich messages and in emoji-only messages open their pack on click, and every pack is counted | always on |
| [98](../patches/tdesktop/0098-fix-ignore-reply-counters-on-scheduled-messages.patch) | edited scheduled messages don't show junk reply counters | always on |
| [102](../patches/tdesktop/0102-fix-show-seen-and-reacted-counts-separately.patch) | the seen and reacted menu shows both counts separately | always on |
| [103](../patches/tdesktop/0103-feat-send-an-inline-bot-query-as-text.patch) | an inline bot query can be sent as plain text | always on |
| [108](../patches/tdesktop/0108-fix-show-server-badges-on-the-personal-channel-in-pr.patch) | checkmarks and custom verification from the tele server show on a profile's personal channel too | always on |
| [109](../patches/tdesktop/0109-fix-explain-a-missing-changelog-instead-of-doing-not.patch) | when a version's changelog can't be found, the tele chat says so instead of doing nothing | always on |
| [110](../patches/tdesktop/0110-feat-show-new-settings-after-an-update.patch) | after an update, a new in tele page lists the settings that version added. the what's new message links to it | always on |
| [113](../patches/tdesktop/0113-fix-trim-settings-descriptions.patch) | setting descriptions only say what their names can't | always on |
| [115](../patches/tdesktop/0115-fix-stop-videos-at-their-end.patch) | videos stop at their end, and play starts them again | always on |
| [116](../patches/tdesktop/0116-feat-hide-settings-until-their-parent-is-on.patch) | settings that only matter while another one is on stay hidden until it is | always on |
| [120](../patches/tdesktop/0120-feat-regroup-the-sending-settings.patch) | the sending settings are split into sending order, uploads, message field and scheduled messages | always on |
| [136](../patches/tdesktop/0136-fix-close-the-tele-chat-profile-card-after-a-resize.patch) | the tele chat's profile card closes after a window resize on macos | always on |
| [140](../patches/tdesktop/0140-feat-loop-videos-in-the-media-viewer.patch) | r loops the video in the media viewer | always on |
| [141](../patches/tdesktop/0141-fix-count-typed-emoji-in-recent-emoji.patch) | emoji you type count in recent emoji | always on |
| [146](../patches/tdesktop/0146-fix-taller-shot-box-docked-shot-sending-and-a-center.patch) | the shot box is taller, shots send from attached media above the field, and the draft button is centered | always on |
| [153](../patches/tdesktop/0153-fix-send-mkv-files-as-videos.patch) | .mkv files are sent as videos | always on |
| [163](../patches/tdesktop/0163-fix-gif-frame-timing-and-same-name-downloads.patch) | gif frames show for their own duration, and downloads with the same name no longer overwrite each other | always on |
| [167](../patches/tdesktop/0167-fix-show-tele-menu-items-only-when-their-feature-is-.patch) | tele's menu items only show while their feature is on, and each one can be turned off | always on |
| [169](../patches/tdesktop/0169-feat-regroup-tele-settings-pages.patch) | tele settings are split into interface, chats, messages, sending, notifications, menus, privacy, profiles and ids, bots and debug. old links still work | always on |
| [170](../patches/tdesktop/0170-feat-collapsible-sub-toggles-in-tele-settings.patch) | a setting with sub-settings folds them away, shows how many are on and switches them all off without forgetting them. turning one on with nothing selected turns all of them on | always on |
| [174](../patches/tdesktop/0174-fix-land-the-send-animation-where-the-message-really.patch) | the sending animation lands on the message even when another message arrives during it | always on |
| [177](../patches/tdesktop/0177-fix-stop-the-chat-list-repainting-while-idle.patch) | the chat list no longer repaints all the time while idle, which froze tele after a few hours | always on |
| [178](../patches/tdesktop/0178-fix-send-large-crash-dumps-zipped.patch) | crash dumps over 20 mb are sent zipped, and a report says why when its dump couldn't be attached | always on |
| [180](../patches/tdesktop/0180-fix-userpics-in-compact-chat-list-rows.patch) | userpics with a story ring or a badge show correctly in compact chat list rows | always on |
| [183](../patches/tdesktop/0183-fix-who-reacted-list-matches-the-reaction-count.patch) | the list of who reacted matches the reaction count | always on |
| [188](../patches/tdesktop/0188-fix-who-read-list-follows-the-read-state.patch) | the list of who read your message follows the read state, and readers that aren't loaded yet show up instead of nobody viewed | always on |
| [194](../patches/tdesktop/0194-fix-show-oversized-stickers-as-files-like-the-server.patch) | a .tgs sticker telegram would turn into a file (over 64 kb, not 512×512, wrong fps or too long) shows as a file to you too, like everyone else sees it | always on |
| [200](../patches/tdesktop/0200-feat-select-service-messages.patch) | select service messages (joins, pins, photo changes) like normal ones and delete them in bulk | always on |
| [201](../patches/tdesktop/0201-fix-hide-the-upgraded-gift-s-number-and-model-until-.patch) | while a gift upgrade spins, its number and model roll and stay hidden until it lands, like on mobile | always on |
| [202](../patches/tdesktop/0202-feat-send-crash-reports-without-a-dump.patch) | after a crash, sending the report is offered even without a dump, from another version or after a graphics crash, with the reason in the window and in the report | always on |
| [203](../patches/tdesktop/0203-feat-report-freezes.patch) | when tele freezes for 15 seconds it writes a dump, and the next launch offers to send a freeze report (windows and linux) | always on |
| [207](../patches/tdesktop/0207-feat-copy-a-gift-collection-s-link.patch) | right-click a gift collection in a profile to copy its link or share it | always on |
| [211](../patches/tdesktop/0211-feat-quote-voice-message-transcriptions.patch) | select part of a voice message's transcription and quote it in a reply | always on |
| [214](../patches/tdesktop/0214-fix-say-why-a-download-couldn-t-be-saved.patch) | when a download can't be saved, tele says why, and a chat's download folder can be reset when it's gone | always on |
| [215](../patches/tdesktop/0215-fix-retry-failed-upload-parts.patch) | a failed piece of an upload is retried instead of failing the whole file | always on |
| [216](../patches/tdesktop/0216-fix-teleoffline-keeps-features-that-only-use-telegra.patch) | with -teleoffline, features that only talk to telegram (gif and video conversion, link previews, shots) keep working | always on |
| [219](../patches/tdesktop/0219-fix-deletions-that-fail-on-the-server-come-back.patch) | messages whose deletion fails on the server come back with a note instead of silently disappearing | always on |
| [220](../patches/tdesktop/0220-feat-retry-failed-messages.patch) | failed messages can all be sent again at once from the menu of any of them | always on |
| [221](../patches/tdesktop/0221-feat-find-any-group-member-when-mentioning.patch) | typing @ in a big group finds any member on the server, not only the ones already loaded | always on |
| [222](../patches/tdesktop/0222-fix-load-the-call-log-in-the-right-page-sizes.patch) | the call log loads all of its pages | always on |
| [223](../patches/tdesktop/0223-fix-read-archived-stickers-from-cache-for-every-acco.patch) | archived sticker sets show for every account, not only the first | always on |
| [224](../patches/tdesktop/0224-fix-retry-loading-gift-collections.patch) | gift collections that fail to load are retried | always on |
| [225](../patches/tdesktop/0225-fix-shared-media-calendar-follows-the-open-sublist.patch) | the shared media calendar jumps within the saved messages chat you have open | always on |
| [230](../patches/tdesktop/0230-fix-tgs-stickers-telegram-would-reject.patch) | a .tgs sticker with the gzip header most windows tools write is fixed before sending, so telegram doesn't turn it into a file, and gift studio exports always load as stickers | always on |
| [237](../patches/tdesktop/0237-feat-browse-every-tele-version-s-changes.patch) | browse and search every tele version's changes | with 110 |
| [238](../patches/tdesktop/0238-fix-late-sent-messages-show-their-real-sent-time.patch) | a message that went out late shows the time telegram actually sent it | always on |
| [241](../patches/tdesktop/0241-feat-what-s-new-as-a-settings-page-with-live-toggles.patch) | what's new is a settings page: every setting a version added is a live toggle right there | with 237 |
| [244](../patches/tdesktop/0244-feat-live-previews-in-settings.patch) | the ghost mode, invisible names and peer ids settings show a live preview of what they change | always on |
| [250](../patches/tdesktop/0250-fix-unbreakable-characters-no-longer-push-message-te.patch) | a long run of characters that can't wrap, like hangul fillers, no longer pushes the message text or its selection past the bubble | always on |
| [251](../patches/tdesktop/0251-fix-the-failed-send-badge-is-clock-sized-and-no-long.patch) | the red mark on a message that failed to send is the size of the sending clock and no longer covers the time, in the chat list and in the bubble | always on |
| [252](../patches/tdesktop/0252-fix-messages-with-relative-dates-no-longer-freeze-te.patch) | a message with a countdown or relative date, like "resets in 5 minutes", no longer makes tele freeze after a while | always on |
| [257](../patches/tdesktop/0257-fix-a-line-under-every-open-group-of-tele-settings.patch) | an open group of tele settings ends with a thin line, so you can see where its settings end | with 42 |
| [271](../patches/tdesktop/0271-feat-add-tele-to-the-start-menu.patch) | tele adds itself to the start menu as "tele" on every launch, so windows search finds it, and stops overwriting the "Telegram" shortcut there (windows) | always on |
| [276](../patches/tdesktop/0276-feat-badges-on-forwarded-and-reply-headers.patch) | with badges next to sender names on, forwarded from headers and the names above replies show the custom verification icon and the checkmark too | with 12 |
| [277](../patches/tdesktop/0277-feat-select-table-cells-as-a-range.patch) | drag from one table cell to another to select whole cells as a rectangle, like in a spreadsheet. copying them pastes into excel or sheets as a grid | always on |
| [286](../patches/tdesktop/0286-feat-copy-links-to-wallet-transactions.patch) | right-click a transaction in the money window to copy its link or open it in the explorer. transaction and address links open on tonscan.org | always on |
| [289](../patches/tdesktop/0289-feat-say-that-the-money-passcode-is-tele-s-passcode.patch) | the money passcode option says it's tele's local passcode, which only locks tele at startup when lock app is on | always on |
| [290](../patches/tdesktop/0290-feat-dim-every-other-address-group-like-ios.patch) | wallet addresses show as lines of four groups with every other group dimmed, like on ios, so they're easier to check | always on |
| [291](../patches/tdesktop/0291-fix-clicking-another-collage-item-switches-the-open-.patch) | clicking another photo or video of an album while the media viewer shows one of them switches the viewer to it | always on |
| [292](../patches/tdesktop/0292-fix-double-click-selects-words-in-service-messages-a.patch) | double-click selects a word in service messages, and the comment of a money transfer can be selected in its details | always on |
| [294](../patches/tdesktop/0294-fix-dismissing-the-draft-save-box-no-longer-blocks-c.patch) | dismissing the box that saves the draft when you close the rich message editor no longer stops the editor from closing afterwards | always on |
| [295](../patches/tdesktop/0295-feat-copy-the-text-of-service-messages.patch) | right-click a service message, like a join, a pin or a gift, to copy its text | always on |
| [296](../patches/tdesktop/0296-feat-copy-and-open-transaction-links-from-money-tran.patch) | right-click a money transfer message in a chat to copy its transaction link or open it in the explorer | always on |
| [297](../patches/tdesktop/0297-feat-resize-the-money-window.patch) | the money window can be resized, its content stays in a column in the middle | always on |
| [309](../patches/tdesktop/0309-fix-quote-the-fee-of-a-wallet-key-update-again.patch) | updating a wallet's key in money no longer fails with "the update could not be completed" | always on |
| [327](../patches/tdesktop/0327-fix-gifts-in-money-look-like-gift-cards-instead-of-a.patch) | telegram gifts in money are drawn sharp at their real size, with the full backdrop pattern around the model. the model plays in the transaction and collectible windows | always on |
| [328](../patches/tdesktop/0328-fix-passkey-prompts-no-longer-count-as-freezes.patch) | waiting in the windows passkey prompt, when logging in or adding a passkey, no longer produces a freeze report | with 203 |
| [1001](../patches/Telegram/lib_ui/0001-fix-fullscreen-mini-apps-cover-the-screen-with-their.patch) | a mini app that opens in fullscreen covers the screen from its corner, with its ⋮ and ✕ buttons, instead of hanging off the screen (windows) | always on |
| [1002](../patches/Telegram/lib_ui/0002-fix-unbreakable-characters-no-longer-scroll-text-fie.patch) | a text field with a long run of characters that can't wrap no longer scrolls sideways and hides everything else | always on |
| [1006](../patches/Telegram/lib_ui/0006-fix-the-maximize-button-follows-the-real-window-stat.patch) | the maximize button of a window shows and does the right thing after resizing or moving the window drops its maximized or full screen state | always on |

## other

everything else.

| # | what it does | toggle |
|---|---|---|
| [302](../patches/tdesktop/0302-feat-scripting-prototype.patch) | tele runs scripts: typescript or javascript files in a scripts folder that can call any telegram method, watch every update and change requests on their way. each script is off until you turn it on, and tele asks you, in plain words, before it gets any grant. everything a script can do is in the [scripting reference](scripting.md). tele writes typings for every telegram method and type next to your scripts, so editors complete and check them, and a script only gets the grants it declares. scripts can keep their own data on this device and look up the chats and users tele already knows. the mtproto console gets a scripts tab with your scripts and their logs, and an editor that runs code against your account right away. results in the console's script editor unfold like in a browser's devtools, and the editor and its output sit side by side. scripts declare grants like inugram plugins and can hold a request or an update while they decide what to do with it. no script can log in or out, touch your sessions or password, or read login codes. scripts get simple ways to read chats and history, send, edit, delete, forward and react to messages, and to hear about new, edited and deleted ones. scripts can download and upload files, check or rewrite your messages before they go out, and ask you things in tele's own boxes. scripts can add items to the message, chat and profile menus and get a settings page of their own. scripts can add /commands, which show up among the suggestions when you type a slash. scripts can show messages that exist only on this device and never reach telegram. scripts can change how users and chats look on this device: name, color, emoji status, premium star and verification marks. scripts have no limit on menu items, commands, boxes and toasts, and can watch every request with one grant. scripts can put badges and highlights on messages, read messages tele has already loaded, and see the messages you send yourself. scripts can open chats and profiles, read and change the text you're typing, add keyboard shortcuts, and check links and notifications before tele opens or shows them. scripts can add buttons to the chat header and next to the message field, rows to profiles, text fields to their settings pages and buttons to their toasts, and open or save files when you pick them. scripts can post to the notification centre, which gets a scripts tab and a switch for them in its settings. scripts can put badges next to names, add a line under messages, and change a chat's label, preview and badge in the chat list or hide it there. tele → scripts β opens a scripts manager: search, filters, and a page per script with its switch, settings, grants, storage and log. scripts can also read tele's local data and settings, talk to each other, react to the connection and to sleep, and send big files. scripts can recolor the theme, set the window title and badge, control the music player and calls, switch accounts, add items to the main and tray menus, settings sections and quick buttons next to messages, and, if you allow it, run programs. scripts can read and change anything in tele's windows, like adding rows to the gift box, and check inline bot results before they're sent. | tele → scripts β, off |
| [303](../patches/tdesktop/0303-feat-ask-before-scripts-change-how-messages-and-peop.patch) | scripts need the new display grant, which tele asks you about, before they change how messages, people and chats look or show messages that were never sent, so a script can't quietly make a message say something it doesn't | with 302 |
| [320](../patches/tdesktop/0320-feat-web-platform-workers-files-sound-webviews-stori.patch) | scripts get the web platform (urls, abort signals, structured clone, intl, websockets, workers, full webcrypto, compression and images), a file area of their own, sounds, webview panels, npm packages, stories, gifts and stars, tele's own data, video chats, the media viewer, banners, selection, compose state, search providers, sticker and gif panels, mini apps, inline answers and buttons under messages. scripts installed from a link check for updates, gettele.app has a catalog of scripts, and new scripts show up in the scripts manager without a restart | with 302 |
| [325](../patches/tdesktop/0325-fix-listing-accounts-from-a-script-no-longer-crashes.patch) | tele no longer crashes at startup with two or more accounts when a script lists your accounts as soon as it starts | with 302 |
| [334](../patches/tdesktop/0334-feat-let-scripts-give-their-menu-items-icons.patch) | scripts can give their menu items, drawer items and settings entries an icon: one of tele's own, an emoji, a custom emoji, an svg or an image, see [scripting](scripting.md) | with 302 |
| [1007](../patches/Telegram/lib_ui/0007-feat-let-scripts-swap-label-texts-and-find-full-widt.patch) | text a script changed in tele's windows comes back exactly as it was, formatting and custom emoji included, when the script stops, and rows a script adds to info tables stay above their last full-width line | with 302 |

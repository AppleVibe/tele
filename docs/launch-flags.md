# launch flags

start tele with any of these to keep it off the network on its own for that launch. telegram's own connection works as usual, and your settings stay as they are.

- `-noteleserver`: nothing goes to the tele server: no checkmark or other mark updates (the saved ones still show) and no crash reports.
- `-noteleupdate`: no update checks, no downloads, no what's new.
- `-teleoffline`: both of the above, and every other outside service is off too: calcmula, ton prices of collectibles (gram.rin.ms), the gift studio, fake upgrades and the gift grid (their parts come from api.changes.tg), view as tl doesn't open inside tele (schema.jppgr.am), and scripts installed from a link aren't checked for updates. features that only use telegram, like gif and video conversion, link previews and shots, keep working.

the flags stay on when tele restarts itself, like after an update. on windows, add them to a shortcut after `tele.exe`; on linux, `./tele -teleoffline`; on macos, `open -a tele --args -teleoffline`. a shortcut with `-noteleserver` keeps even the very first launch away from the tele server. to turn the server off for good, empty its field in settings.

---
name: tele-scripting
description: Write, fix and explain scripts for tele (a Telegram Desktop fork) in TypeScript or JavaScript. Use when the user wants a tele script, asks what tele's scripting API can do, or works with defineScript, tg.*, grants, tg.ui.widgets, interceptors or tele.d.ts.
---

# tele scripting

tele runs scripts: small TypeScript or JavaScript files that live in a folder, start when you switch them on, and can do anything tele itself can do. a script talks to telegram through the raw api (any method, any update, middleware around tele's own requests), reads and changes tele's local data and settings, adds its own commands, buttons, menu items, settings pages and notices, and reaches into any window through the widget layer. power is never cut down; it's gated by grants, which tele asks you to confirm in plain words before a script starts.

this is the complete reference. every function, getter, property, type, event, grant and global has its own entry with its signature (copied from the `tele.d.ts` tele writes into your scripts folder), what it does, the grant it needs, its parameters, what it returns, what it throws, and an example. on [gettele.app/scripting](https://gettele.app/scripting) it's one page with a filter. for ai agents, [SKILL.md](https://gettele.app/scripting/SKILL.md) is a short index that points to one file per section, so an agent reads only what it needs.

- new here? start with "your first script", then "defineScript" and "grants".
- looking for a method? every `tg.*` member has its own entry, named after it.
- writing something real? the cookbook at the end has complete scripts you can copy.

## what scripts are

### what a script is

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'my script',
  setup(tg) {
    // runs when the script starts
  },
})
```

a script is a javascript or typescript module that tele runs inside itself, once for every logged-in account it is turned on for. it can react to everything the account receives, send any telegram api request as you, change or block what tele sends and receives, add buttons, commands, menu items and settings pages, and talk to the internet when you allow it.

- **grant:** none to exist; everything powerful is behind [grants](#grants).
- **notes:**
  - scripts run on [QuickJS-ng](https://github.com/quickjs-ng/quickjs) 0.17, a small modern javascript engine (ES2025+), not node and not a browser. see [globals](#globals) for what is there.
  - every script gets its own engine, memory and globals. two scripts never share javascript state, and neither do two accounts running the same script.
  - everything runs on tele's main thread: a script that blocks freezes tele until its time budget runs out (see [errors and limits](#errors-and-limits)).
  - the entry module must `export default defineScript({ ... })`.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'echo ping',
  grants: ['onUpdate(new_message)', 'account.write(send)'],
  setup(tg) {
    tg.onNewMessage((message) => {
      if (!message.out && message.text === 'ping') message.reply('pong')
    })
  },
})
```

### where scripts live

```ts
// default folder
// <tele working folder>/scripts/
```

scripts live in one folder on disk, the scripts folder. by default it is `scripts` in tele's working folder (the folder that holds `tdata`).

- **grant:** none.
- **notes:**
  - open it from the Scripts manager: Settings > tele > Scripts β, then the ⋮ menu > Open the scripts folder. tele creates the folder if it's missing.
  - the same menu has Change the folder (pick any folder) and, once changed, Use the default folder. the choice is global for all accounts and saved in `tdata/tele_scripts.json` as `{ "folder": "..." }`.
  - changing the folder stops every script of every account and loads the scripts of the new folder.
  - tele writes two files into the folder: `tele.d.ts` (the generated typings, rewritten whenever tele's api schema changes) and `tsconfig.json` (only if there is none). see [typescript setup](#typescript-setup).

Example:

```bash
# a typical scripts folder
scripts/
  tele.d.ts          # written by tele, don't edit
  tsconfig.json      # written by tele once, yours to change
  auto-read.ts       # a script
  translator/        # a folder script
    index.ts
    lang.ts
  _lib/              # skipped: shared helpers
    format.ts
```

### file layout

```ts
// a script is either
// scripts/<name>.ts | .mts | .js | .mjs
// or a folder with an entry:
// scripts/<name>/index.ts | index.js
```

tele scans the top level of the scripts folder. every matching file or folder there is one script, and its id is the file or folder name (`auto-read.ts`, `translator`).

- **grant:** none.
- **notes:**
  - a top-level `.ts`, `.mts`, `.js` or `.mjs` file is a script.
  - a top-level folder is a script when it has `index.ts` (or, if not, `index.js`). everything else inside the folder is that script's private code.
  - skipped: names starting with `_` or `.`, `node_modules`, `*.d.ts` and `*.d.mts`, and any other extension. put shared helpers in `_lib/` or similar.
  - `.ts` and `.mts` files go through a type stripper (sucrase): types are erased, enums and constructor parameter properties are compiled, nothing else changes and line numbers stay the same. there is no type checking at runtime; use `tsc` for that. typescript `namespace`s with values and legacy decorators are not supported.
  - `.js` and `.mjs` files run as they are. every file is an ES module.
  - the script id is what tele stores your switch, grants and `tg.storage` under. renaming the file makes it a new script that starts off.

Example:

```ts
// scripts/translator/index.ts
import { defineScript } from 'tele'
import { pickLanguage } from './lang.ts'

export default defineScript({
  name: 'translator',
  setup(tg) {
    console.log('default language:', pickLanguage())
  },
})
```

### imports

```ts
import { defineScript, Message, md, html } from 'tele'
import { helper } from './_lib/helper.ts'
const lazy = await import('./big-table.ts')
```

scripts can import the built-in `tele` module and their own files with relative paths. static and dynamic `import()` both work.

- **grant:** none.
- **notes:**
  - `'tele'` exports `defineScript`, `Message`, `md` and `html`, plus every api type (`import { type Tg, type PeerInfo } from 'tele'`).
  - any other specifier must start with `./` or `../`. there are no npm packages: `import x from 'lodash'` fails the start with `only relative imports and 'tele' work, not 'lodash'`.
  - a relative path must stay inside the script's root, or the start fails with `'<path>' is outside the script`. the root of a single-file script is the whole scripts folder (so it may import `./_lib/x.ts` or even `./other.ts`); the root of a folder script is its own folder.
  - resolution tries, in order: the exact path, then `+ .ts`, `+ .js`, `+ /index.ts`, `+ /index.js`. `.mts`, `.mjs` and `.json` are never guessed; write them out. a missing file fails with `can't find '<path>'`.
  - json files are not modules: importing one evaluates the text as javascript, which is normally a syntax error. keep data in a `.ts` file that exports it.
  - a module is evaluated once per start; static and dynamic imports share it.
  - every file a script loads, including files it tried and failed to load, is watched for [hot reload](#hot-reload-on-save).

Example:

```ts
// scripts/_lib/time.ts
export const hhmm = (date: Date) => date.toTimeString().slice(0, 5)

// scripts/clock.ts
import { defineScript } from 'tele'
import { hhmm } from './_lib/time.ts'

export default defineScript({
  name: 'clock',
  setup() {
    console.log('started at', hhmm(new Date()))
  },
})
```

### hot reload on save

```ts
// nothing to call: save the file
```

when you save a file a running script loaded, tele stops that script (its cleanup runs) and starts it again with the new code. for a folder script, saving any script file in its folder does the same.

- **grant:** none.
- **notes:**
  - file changes are collected for 300 ms, so editors that write a file in several steps cause one reload.
  - only files the script actually loaded count (the entry, its imports, files loaded later with `import()`, and files it tried to load). a new file nobody imports restarts nothing.
  - a new top-level script appears in the Scripts manager at once, turned off. a deleted script stops and disappears.
  - a script that failed to start, or is waiting for your approval, tries again only when one of its files changes.
  - an edited script that now declares more grants than you gave doesn't start: it waits for your approval (see [the consent box](#the-consent-box)). declaring fewer starts without asking.
  - reloading keeps `tg.storage`, persisted ghost messages and the script's log.
  - the Scripts manager's script page also has a Reload button for a running script.

Example:

```ts
export default defineScript({
  name: 'reload demo',
  setup() {
    console.log('loaded at', new Date().toLocaleTimeString())
    return () => console.log('stopping for a reload')
  },
})
```

### per-account scripts

```ts
tg.selfId // bigint, the account this copy runs in
```

scripts are turned on, granted and stored per account. with two accounts logged in, a script you turned on for both runs twice, in two separate engines, each with its own `tg`.

- **grant:** none.
- **notes:**
  - each account has its own switch, its own grants, its own `tg.storage` and its own persisted ghost messages for every script.
  - the Scripts manager opens for the account whose window you opened it from.
  - `tg.selfId` tells the copies apart. a script can never act as another account; even the `accounts` grant only lists and switches accounts.
  - logging an account out stops its scripts.

Example:

```ts
export default defineScript({
  name: 'who am i',
  setup(tg) {
    console.log('running for account', tg.selfId)
  },
})
```

### off until turned on

```ts
// a new script's state
{ enabled: false }
```

a new script is off, for every account, until you turn it on in the Scripts manager. dropping a file into the folder never runs anything by itself.

- **grant:** none.
- **notes:**
  - scripts installed from a file or a link also stay off until you turn them on.
  - while a script is off, tele still shows its name, description, author, version, icon, homepage and declared grants. it reads them from the `defineScript({ ... })` literal in the first 1 MB of the entry file without running anything, so only string literals are picked up there.
  - turning a script off stops it and forgets the grants you gave it for that account. its `tg.storage` stays.

Example:

```ts
export default defineScript({
  name: 'shown while off', // read statically while the script is off
  description: 'string literals here show in the list even before it runs',
  setup() {},
})
```

### the consent box

```ts
grants: ['account.read(peers)', 'fetch(api.example.com)']
```

when you turn on a script that declares grants, tele asks first. the box is titled "Script permissions", starts with "{script name} asks to:" and lists every grant in plain words, with dangerous ones in a bold "Dangerous: ..." line at the end.

- **grant:** shown for any non-empty `grants` list. scripts that declare nothing start without a box.
- **notes:**
  - Allow saves exactly the declared list for this account and starts the script. Cancel, Escape or clicking outside turns it back off.
  - if a running script is edited to ask for more, it stops, a toast says "Script {name} asks for more grants, review them in Settings > tele > Scripts.", its row says "Waiting for your approval", and its page has a Review permissions button that opens the box again.
  - the exact wording of every line is in each [grant item](#grants).
  - texts go through tele's lowercase setting like the rest of tele's ui.

Example:

```ts
export default defineScript({
  name: 'weather',
  grants: ['fetch(api.open-meteo.com)', 'notify'],
  // the box says:
  // weather asks to:
  // - Connect to these servers: api.open-meteo.com.
  // - Show notifications.
  async setup(tg) {},
})
```

## your first script

### step 1: open the scripts folder

```ts
// Settings > tele > Scripts β > ⋮ > Open the scripts folder
```

open tele, go to Settings > tele > Scripts β. the Scripts manager opens; its ⋮ menu has Open the scripts folder. tele creates the folder, writes `tele.d.ts` and `tsconfig.json` into it and opens it in your file manager.

- **grant:** none.
- **notes:**
  - by default the folder is `scripts` next to tele's `tdata` folder.
  - open the folder in your editor (vs code and others pick up `tsconfig.json` and `tele.d.ts` by themselves, so `tg.` autocompletes).

Example:

```bash
cd path/to/tele/scripts
code .
```

### step 2: write the script

```ts
export function defineScript<T extends ScriptDefinition>(definition: T): T
```

create `hello.ts` in the scripts folder. it needs a default export made with `defineScript`: a `name`, the grants it needs, and a `setup` function.

- **grant:** this example needs `onUpdate(new_message)` for `tg.onNewMessage` and `account.write(send)` to send.
- **notes:**
  - save the file. it appears in the Scripts manager list at once, turned off.
  - the name is what you see in the list, in toasts and in the log.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'hello',
  version: '1.0.0',
  description: 'answers /hi in saved messages',
  grants: ['onUpdate(new_message)', 'account.write(send)'],
  setup(tg) {
    console.log('hello is running for', tg.selfId)
    tg.onNewMessage(async (message) => {
      if (message.chatId === tg.selfId && message.text === '/hi') {
        await tg.sendMessage('me', 'hi from my first script')
      }
    })
    return () => console.log('hello stopped')
  },
})
```

### step 3: turn it on

```ts
// Scripts manager > hello > switch on > Allow
```

flip the switch next to hello (or open it and use Turned on). because it declares grants, the consent box asks; click Allow. the script starts and its log line `started` appears.

- **grant:** whatever the script declares; you approve them here.
- **notes:**
  - if it fails to start, the error shows under the switch in red, in a toast and in the log. fix the file and save: it retries by itself.
  - in this example, type `/hi` in Saved Messages and the script answers.

Example:

```ts
// the log page shows
// 12:00:01  started
// 12:00:01  hello is running for 123456789n
```

### step 4: edit and watch it reload

```ts
// save the file: cleanup, then setup again
```

change the text in `hello.ts` and save. tele stops the script (the function returned from `setup` runs, so "hello stopped" is logged) and starts the new version.

- **grant:** if you add a grant while editing, the script waits for your approval instead of starting.
- **notes:**
  - timers, listeners and everything registered through `tg` are removed for you on every stop. return a cleanup only for your own state.

Example:

```ts
setup(tg) {
  const timer = setInterval(() => console.log('tick'), 60_000)
  return () => clearInterval(timer) // optional: timers die with the script anyway
}
```

### typescript setup

```json
{
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "lib": ["ESNext"],
    "types": [],
    "strict": true,
    "noEmit": true,
    "allowJs": true,
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "skipLibCheck": true
  }
}
```

tele writes this `tsconfig.json` (only if the folder has none) and keeps `tele.d.ts` current. together they type everything: `tg` and all its members, every TL constructor and method, the `grants` strings and the globals.

- **grant:** none.
- **notes:**
  - `tele.d.ts` is generated from the exact api schema your tele speaks and rewritten when that changes. don't edit it.
  - with the typings, `tg.call` infers the result from `_`, listeners get the exact update type, and a misspelled grant like `'call(messages.sendMesage)'` is a type error.
  - tele never runs `tsc`; it only strips types. to check your scripts, install typescript (`npm install -g typescript`) and run `tsc -p .` in the scripts folder. no output means no errors.
  - TL names are mtcute-style: `tl.RawMessage` (one constructor), `tl.TypeMessage` (the union), `tl.messages.RawSendMessageRequest` (a method). api types come from `'tele'`: `import { type Tg, type PeerInfo } from 'tele'`.
  - typings are a bit stricter than the runtime: `long` fields are `bigint` only (the runtime also takes safe integer numbers).
  - plain `.js` scripts work too (`allowJs`), with or without JSDoc types.

Example:

```bash
cd path/to/tele/scripts
npm install -g typescript
tsc -p .
```

### where logs go

```ts
console.log(...data: unknown[]): void
```

everything a script logs, and everything tele says about it, lands in four places.

- **grant:** none.
- **notes:**
  - the script's page in the Scripts manager shows the last 5 lines live; Open the console shows the full log (see [the script console](#the-script-console)).
  - the MTProto console (its Scripts tab) shows each script's log with filters and expandable objects, and has a REPL.
  - tele's `log.txt` in the working folder gets every line as `[time] script <name>: <text>`.
  - tele's Notification centre (Scripts tab) gets tele's notes about a script (faults, failed starts, grant requests) and the script's own `tg.toast`, `tg.notify` and `tg.ui.notice` entries, while its "Log script notices" option is on (the default).
  - levels: `console.log` / `info` / `debug` are info, `console.warn` is a warning, `console.error` is an error. faults are tele's own reports (exceptions, timeouts, failed starts); only faults show a toast.

Example:

```ts
setup(tg) {
  console.log('started with', { selfId: tg.selfId })
  console.warn('this is a warning')
  console.error('this is an error, but no toast')
}
```

## defineScript

### defineScript(definition)

```ts
export function defineScript<T extends ScriptDefinition>(definition: T): T
declare function defineScript<T extends import('tele').ScriptDefinition>(
  definition: T,
): T
```

checks a script definition and returns the same object. the entry module's default export must be its result.

- **grant:** none.
- **parameters:**
  - `definition` (`ScriptDefinition`): the script: `name`, `setup` and optional metadata and grants. see the items below.
- **returns:** the same object, unchanged (nothing is copied; extra fields are allowed and ignored).
- **throws:**
  - `TypeError: defineScript needs an object` when the argument isn't an object.
  - `TypeError: defineScript needs a setup function` when `setup` isn't a function.
  - `TypeError: defineScript needs a name` when `name` is missing or not a string.
- **notes:**
  - available both as `import { defineScript } from 'tele'` and as a global; they behave the same.
  - when the script starts, tele also checks the default export: if it isn't an object the start fails with `the default export isn't defineScript({ ... })`; a definition that still has the old `permissions` field fails with `'permissions' is now 'grants'`.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'minimal',
  setup() {
    console.log('hi')
  },
})
```

### type ScriptDefinition

```ts
export interface ScriptDefinition {
  name: string
  version?: string
  description?: string
  author?: string
  icon?: string
  homepage?: string
  grants?: Grant[]
  setup(this: ScriptDefinition, tg: Tg): void | Cleanup | Promise<void | Cleanup>
}
```

the object you pass to `defineScript`.

- **grant:** none.
- **parameters:**
  - `name` (`string`): required. shown in the list, toasts, notices and the log.
  - `version` (`string`, optional): shown on the script page and in `tg.scripts.list()`.
  - `description` (`string`, optional): shown under the name in the list and on the script page.
  - `author` (`string`, optional): shown on the script page and matched by search.
  - `icon` (`string`, optional): one emoji, or an image file path (png, jpg, jpeg, webp, svg) relative to the script's root.
  - `homepage` (`string`, optional): a link shown on the script page.
  - `grants` (`Grant[]`, optional): everything the script may use. see [grants](#grants).
  - `setup` (`(tg: Tg) => void | Cleanup | Promise<void | Cleanup>`): required. runs when the script starts.
- **notes:**
  - metadata is read from the running script, and statically from the source while the script is off (string literals only).

Example:

```ts
export default defineScript({
  name: 'read receipts',
  version: '2.1.0',
  description: 'marks chats as read when you open them',
  author: 'alex',
  icon: './read.png',
  homepage: 'https://example.com/read-receipts',
  grants: ['account.write(read)'],
  setup(tg) {},
})
```

### definition.name

```ts
name: string
```

the script's display name.

- **grant:** none.
- **notes:**
  - required; `defineScript` throws without it.
  - used from the moment the module is loaded: log lines read `script <name>: ...`. before that (for example when the module fails to load) the file id is used.
  - `tg.scriptName` returns it.
  - not an id: two scripts may share a name; their ids (file names) still differ.

Example:

```ts
export default defineScript({ name: 'auto read', setup() {} })
```

### definition.version

```ts
version?: string
```

a version string for people. tele doesn't compare or enforce it.

- **grant:** none.
- **notes:**
  - shown on the script page as "version {version}" and returned by `tg.scripts.list()`.

Example:

```ts
export default defineScript({ name: 'pinger', version: '1.4.2', setup() {} })
```

### definition.description

```ts
description?: string
```

one short line about what the script does.

- **grant:** none.
- **notes:**
  - the list shows it under the name when the script has no error and isn't waiting for approval; the script page shows it under the header.
  - search matches it.

Example:

```ts
export default defineScript({
  name: 'silent nights',
  description: 'sends everything silently between 23:00 and 08:00',
  setup() {},
})
```

### definition.author

```ts
author?: string
```

who wrote the script.

- **grant:** none.
- **notes:**
  - shown on the script page as "by {author}"; search matches it.

Example:

```ts
export default defineScript({ name: 'tool', author: 'alex', setup() {} })
```

### definition.icon

```ts
icon?: string
```

the round icon in the list and on the script page: a single emoji, or a path to an image.

- **grant:** none.
- **notes:**
  - an image path ending in `.png`, `.jpg`, `.jpeg`, `.webp` or `.svg` is resolved against the script's root (the scripts folder for a single-file script, its folder for a folder script) and drawn in a circle.
  - any other string is drawn as text on a colored circle; a single emoji is drawn as that emoji.
  - without an icon, the first letter of the name is drawn.

Example:

```ts
// scripts/translator/index.ts, with scripts/translator/icon.png next to it
export default defineScript({ name: 'translator', icon: 'icon.png', setup() {} })
```

### definition.homepage

```ts
homepage?: string
```

a link to the script's page, repo or docs.

- **grant:** none.
- **notes:**
  - shown as a clickable link on the script page.

Example:

```ts
export default defineScript({
  name: 'translator',
  homepage: 'https://github.com/someone/tele-translator',
  setup() {},
})
```

### definition.grants

```ts
grants?: Grant[]
```

the list of everything the script may use. anything not covered throws `TeleError` `not-granted` at the call.

- **grant:** this is where grants are declared.
- **throws:** (the start fails, the error shows under the switch)
  - `grants must be an array of strings`.
  - `grant '<entry>' is missing ')'`, `grant '<entry>' has an empty scope`, `grant '<entry>' takes no scopes`.
  - `grant '<entry>': '<scope>' is not a method` / `an update` / `an update or new_message, edit_message, delete_message` / `one of <list>` / `a host`.
- **notes:**
  - parsed when the script starts. unknown grant names are logged (`unknown grant '<entry>' is ignored`) and ignored, so scripts written for a newer tele still start; a known name with a bad scope fails, because a typo would silently narrow it.
  - compared with what you approved for this account; if it asks for more, the script waits for approval.
  - full syntax and every grant: [grants](#grants).

Example:

```ts
export default defineScript({
  name: 'link cleaner',
  grants: ['interceptLink', 'fetch(api.example.com)'],
  setup(tg) {},
})
```

### definition.setup(tg)

```ts
setup(this: ScriptDefinition, tg: Tg): void | Cleanup | Promise<void | Cleanup>
```

runs when the script starts: register listeners, commands, buttons and so on here.

- **grant:** none to run; each api it uses needs its own grant.
- **parameters:**
  - `tg` (`Tg`): this script's api object for this account. see [what tg is](#what-tg-is).
  - `this` (`ScriptDefinition`): the definition object itself.
- **returns:** nothing, a cleanup function, or a promise of either.
- **throws:** a synchronous throw, or a promise that is already rejected after the first round of promise jobs, fails the start with that error.
- **notes:**
  - the synchronous part has 2 s; over that it is stopped (`took too long and was stopped`) and the start fails.
  - see [the setup lifecycle](#the-setup-lifecycle) for async setups.

Example:

```ts
export default defineScript({
  name: 'setup demo',
  grants: ['account.read(self)'],
  async setup(tg) {
    const me = await tg.getMe()
    console.log(`${this.name} running for`, me._ === 'user' ? me.firstName : me.id)
  },
})
```

### type Cleanup

```ts
export type Cleanup = () => void
```

a function `setup` can return (or resolve with) that tele calls when the script stops.

- **grant:** none.
- **notes:**
  - runs on turning off, reloads, the folder changing, logout, quit and the 5-failures auto-off.
  - 0.5 s budget; errors are logged, not counted as failures.
  - runs before the `tg.onUnload` callbacks.
  - you rarely need it: everything registered through `tg`, plus timers and fetches, is undone for you.

Example:

```ts
setup(tg) {
  const seen = new Map<bigint, number>()
  return () => console.log(`tracked ${seen.size} chats this session`)
}
```

### the setup lifecycle

```ts
setup(this: ScriptDefinition, tg: Tg): void | Cleanup | Promise<void | Cleanup>
```

starting one script on one account goes through fixed steps, and an async `setup` is fine.

- **grant:** none.
- **notes:**
  - start: a fresh engine, the entry module is loaded and run (3 s), `name` is read, `grants` are parsed and checked against what you approved (not covered: the script waits, nothing more runs), persisted ghost messages are restored, `tg` is built, then `setup.call(definition, tg)` runs with 2 s for its synchronous part, then pending promise jobs run once (1 s).
  - `setup` threw: the start fails with that error.
  - it returned a function: that's the cleanup.
  - it returned a promise that is already settled: resolved with a function means cleanup; rejected fails the start.
  - it returned a promise still pending (awaiting `tg.call`, a timer, `fetch`...): the script counts as started right away and its listeners are live. if the promise later resolves to a function, that function becomes the cleanup; if it later rejects, that is logged as an unhandled rejection (a fault, with a toast) and the script keeps running.
  - after a successful start the log says `started`; after a stop, `stopped`.
  - a failed start leaves the script on but not running, with the error under its switch; it retries when one of its files changes.

Example:

```ts
export default defineScript({
  name: 'async setup',
  grants: ['account.read(dialogs)'],
  async setup(tg) {
    const dialogs = await tg.getDialogs({ limit: 20 }) // the script is already running here
    console.log('loaded', dialogs.length, 'dialogs')
    const timer = setInterval(() => console.log('still here'), 600_000)
    return () => clearInterval(timer) // becomes the cleanup when the promise resolves
  },
})
```

### top-level await

```ts
const table = await import('./table.ts')
```

top-level `await` works in every module, but only for things that settle without tele's event loop.

- **grant:** none.
- **notes:**
  - after the module body runs, pending promise jobs run once. if the module is still waiting then, the start fails with `top-level await never finished`.
  - so awaiting a timer, `fetch` or anything from `tg` at top level never works. `tg` doesn't exist at load time anyway, and `fetch` is defined right before `setup` runs.
  - awaiting a dynamic `import()` or already-resolved promises is fine.
  - loading (compile and run of all modules) has 3 s.

Example:

```ts
import { defineScript } from 'tele'

const { words } = await import('./_lib/words.ts') // fine: no event loop needed

export default defineScript({
  name: 'word filter',
  setup() {
    console.log(words.length, 'words loaded')
  },
})
```

### what tg is

```ts
setup(this: ScriptDefinition, tg: Tg): void | Cleanup | Promise<void | Cleanup>
```

`tg` is the api object tele hands to `setup`: one per script per account, bound to that account and checked against that script's grants.

- **grant:** none to hold it; each member checks its own grant and throws `TeleError` `not-granted` without it.
- **notes:**
  - it is not a global. keep it in a variable or pass it around; there is no `tg` at module top level.
  - it covers raw telegram (`tg.call`, `tg.onUpdate`, `tg.interceptRpc`, `tg.interceptUpdate`), the high-level account api (`tg.getMe`, `tg.sendMessage`, `tg.onNewMessage`...), tele's ui (`tg.ui`, commands, buttons, menus, settings pages), local state (`tg.local`, `tg.options`, `tg.tele`), the app (`tg.app`, `tg.calls`, `tg.accounts`), storage (`tg.storage`), other scripts (`tg.scripts`) and more. each member has its own item in this reference.
  - after the script stops, calling `tg` members throws `InternalError: the script was stopped`.
  - registrations (`tg.onUpdate`, `tg.registerCommand`...) return a `Disposer`; all of them are undone when the script stops.

Example:

```ts
import { defineScript, type Tg } from 'tele'

const greet = (tg: Tg) => tg.toast(`hello from ${tg.scriptName}`)

export default defineScript({
  name: 'tg demo',
  setup(tg) {
    greet(tg)
  },
})
```

### stopping and reloading

```ts
type Cleanup = () => void
```

a script stops when you turn it off, when it reloads after a file change, when the scripts folder changes, when the account logs out, when tele quits, and after 5 failures in a row.

- **grant:** none.
- **notes:**
  - stop order: the cleanup returned by `setup` (0.5 s), then every `tg.onUnload` callback in registration order (0.5 s each), then tele drops every registration.
  - what tele undoes for you: listeners and interceptors, commands, buttons, menu items, settings pages, shortcuts, peer overrides, message decorations, palette and window title overrides, timers, running `tg.unsafe.exec` processes (not detached ones), uploads, and `fetch` requests. ghost messages leave the chats (persisted ones come back when it starts again).
  - requests and update batches its interceptors were holding continue as if the script weren't there; a request whose `next()` was already called gets the server's answer. held sends go out unchanged.
  - pending `tg.call` and `fetch` promises never settle; the engine is destroyed.
  - reloading is stop, then start with the new code.

Example:

```ts
setup(tg) {
  tg.onUnload(() => console.log('second: onUnload'))
  return () => console.log('first: the cleanup from setup')
}
```

### the 5-failures rule

```ts
// 5 faults in a row in listeners, interceptors or handlers
```

a script whose handlers fail 5 times in a row is turned off for that account.

- **grant:** none.
- **notes:**
  - counted: an exception, a wrong return value or a timeout in an update listener, `interceptRpc` / `interceptUpdate` middleware, send, link, notification and drop interceptors, decorators, commands, menu actions, settings page callbacks and other handlers tele calls.
  - not counted: timer callbacks, unhandled promise rejections, errors in promise jobs, `tg.call` result callbacks, `console.error`, cleanup and `onUnload` errors.
  - any successful handler call resets the count to 0.
  - at 5 the log says `failed 5 times in a row, turning it off`, a toast says "Script {name} kept failing and was turned off.", and the script's row says "Turned off after failing 5 times in a row.".
  - turning off forgets its grants, so turning it on again asks again.

Example:

```ts
setup(tg) {
  tg.onNewMessage((message) => {
    try {
      handle(message)
    } catch (error) {
      console.error('handled, not a fault:', error) // caught errors never count
    }
  })
}
```

### the Scripts manager

```ts
// Settings > tele > Scripts β
```

the Scripts manager is tele's panel for scripts: a separate resizable window per account (it remembers its size), opened from Settings > tele > Scripts β. pages slide like Settings and Back keeps the list's scroll position.

- **grant:** none.
- **notes:**
  - the list: a search field on top (matches name, file id, description and author; Enter opens the only match), tabs All, On, Off and Need attention (waiting for approval or failing), and a row per script with its icon, name, a status line and a switch.
  - the status line shows, in order: "Waiting for your approval", the start error (red), the description, "Running", "Starting" or "Off".
  - clicking a row opens the [script page](#the-script-page).
  - the ⋮ menu: Install from a file, Install from a link, Open the scripts folder, Change the folder, Use the default folder (only when changed), MTProto console.

Example:

```ts
export default defineScript({
  name: 'findable',
  description: 'search finds me by these words too',
  author: 'alex',
  setup() {},
})
```

### the script page

```ts
// Scripts manager > click a script
```

everything about one script on this account.

- **grant:** none.
- **notes:**
  - header: icon, name, "version {version} · by {author} · {file}", the description and the homepage link.
  - status: "It's waiting for your approval: it asks for permissions you haven't given yet." with Review permissions, or the start error in red (selectable).
  - Turned on: the switch. Reload (when on), Open the file, Show in folder, Remove... .
  - Settings: the page the script registered with `tg.registerSettings`, rendered inline.
  - Permissions: every granted grant in plain words with a revoke link each, then "Asks for, not given:" with declared grants you haven't approved, or "It asks for nothing.". revoking asks "Revoke «{grant}»? The script restarts and asks for it again if it needs it.".
  - Storage: "tg.storage: {n} keys, {size}" and "Saved ghost messages: {n}, {size}", with Clear storage... ("Clear everything this script saved on this account, including its saved ghost messages?"). clearing restarts a running script.
  - Log: the last 5 lines, live, and Open the console.

Example:

```ts
export default defineScript({
  name: 'with settings',
  setup(tg) {
    const page = tg.ui.settingsPage({
      title: 'with settings',
      items: () => [tg.ui.header('shown on the script page')],
    })
    tg.registerSettings(page)
  },
})
```

### the script console

```ts
console.log(...data: unknown[]): void
```

the full-height log page of one script, opened with Open the console on its page.

- **grant:** none.
- **notes:**
  - a monospace list with a time column (`HH:mm:ss`), warnings and errors colored.
  - a search field and level tabs: All, Info, Warnings, Errors (errors include faults).
  - right-click a line: Copy the line, Copy everything shown. the ⋮ menu: Copy everything shown, Clear the log.
  - keeps the last 2000 lines per script, across reloads; lost when the script leaves the folder.
  - the MTProto console's Scripts tab shows the same logs with objects as expandable trees, plus a REPL that runs code in a scratch engine or inside a running script (5 s budget for its synchronous part; REPL errors never count as failures).

Example:

```ts
setup(tg) {
  tg.onNewMessage((message) => console.log('new message', message.chatId, message.text))
}
```

### installing and removing scripts

```ts
// ⋮ > Install from a file | Install from a link
// script page > Remove...
```

besides copying files into the folder, the manager can install a script from a file or a direct link, and remove one.

- **grant:** none.
- **notes:**
  - Install from a file: pick a `.ts` or `.js` file; it is copied into the scripts folder.
  - Install from a link: "A direct link to a .ts or .js file. It goes into the scripts folder and stays off until you turn it on." http and https only, at most 5 MB, 30 s timeout, redirects only to equally safe urls.
  - other names are refused with "A script is a .ts or .js file.". an existing file asks "{file} is already in the scripts folder. Replace it?".
  - after installing: "Installed {file}. It stays off until you turn it on.".
  - Remove... asks "Remove {name}? Its file goes to the recycle bin, its storage stays until you clear it." and moves the file (or the whole folder of a folder script) to the recycle bin, or deletes it when that isn't possible. its grants are forgotten.

Example:

```bash
# the same as Install from a file
cp ~/Downloads/auto-read.ts path/to/tele/scripts/
```

## grants

### how grants work

```ts
grants?: Grant[]
```

a script declares in `grants` everything powerful it may do. you approve the list once per account; tele then checks every call against it and throws `TeleError` `not-granted` (whose `grant` field is the exact string to add) for anything not covered.

- **grant:** n/a.
- **notes:**
  - an entry is a bare name (`'call'`) meaning everything that name allows, or a name with scopes (`'call(messages.getHistory, users.getUsers)'`). `name(*)` is the same as the bare name. names may repeat; scopes add up.
  - what needs no grant at all: `tg.toast`, `tg.ui` boxes and pages, commands, buttons, menu items, quick actions, shortcuts, `tg.storage`, ghost messages, peer overrides, `tg.decorateMessage`, navigation, reading `tg.options`, the app theme and player state, connection state, `tg.schedule`, `tg.scripts.list`. they change nothing outside this tele or are triggered by you.
  - the error message names the missing grant, for example `tg.call(users.getUsers) needs the grant 'account.read(peers)'` or `fetch(https://example.com/) needs the grant 'fetch(example.com)'`.
  - whatever the grants say, the [account protection](#account-protection) and the [dangerous methods](#dangerous-methods) rule apply.

Example:

```ts
export default defineScript({
  name: 'grants demo',
  grants: ['account.read(peers)'],
  async setup(tg) {
    try {
      await tg.sendMessage('me', 'hi') // not declared
    } catch (error) {
      if (error instanceof TeleError && error.code === 'not-granted') {
        console.warn('add this grant:', error.grant) // 'account.write(send)'
      }
    }
  },
})
```

### type Grant

```ts
type Some<T extends string> = T | `${T}, ${string}`

export type Grant =
  | 'call'
  | `call(${Some<tl.RpcMethod | `${string}*`>})`
  | 'onUpdate'
  | `onUpdate(${Some<
    tl.UpdateName | 'new_message' | 'edit_message' | 'delete_message'
  >})`
  | 'interceptRpc'
  | `interceptRpc(${Some<tl.RpcMethod | `${string}*`>})`
  | 'interceptUpdate'
  | `interceptUpdate(${Some<tl.UpdateName>})`
  | 'interceptSendMessage'
  | 'account.read'
  | `account.read(${Some<
    'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft'
  >})`
  | 'account.write'
  | `account.write(${Some<
    | 'send'
    | 'edit'
    | 'delete'
    | 'forward'
    | 'react'
    | 'read'
    | 'typing'
    | 'draft'
  >})`
  | 'fetch'
  | `fetch(${string})`
  | 'clipboard.read'
  | 'clipboard.write'
  | 'openUrl'
  | 'notify'
  | 'interceptLink'
  | 'interceptNotification'
  | 'options'
  | 'scripts'
  | 'files.write'
  | 'app'
  | 'interceptDrop'
  | 'calls'
  | 'accounts'
  | 'unsafe.exec'
  | 'ui.read'
  | 'ui.write'
  | 'unsafe.automate'
  | 'unsafe.disableApiFiltering'
```

every grant string tele knows, as a typescript type: with `tele.d.ts` in the folder, `grants` autocompletes and a typo is a type error.

- **grant:** n/a.
- **notes:**
  - the type checks the first scope in a list; tele checks all of them at start.
  - at runtime, spaces around names and scopes are ignored.

Example:

```ts
import { type Grant } from 'tele'

const grants: Grant[] = ['call(help.getConfig)', 'onUpdate(updateNewMessage, updateEditMessage)']
```

### scopes and globs

```ts
'call(messages.getHistory, messages.search)'
'call(messages.*)'
'interceptRpc(messages.send*)'
'fetch(example.com)'
```

scopes narrow a grant. what a scope may be depends on the grant.

- **grant:** n/a.
- **parameters:**
  - methods (`call`, `interceptRpc`): an exact api method name, checked against tele's schema, or a prefix ending in `*` (`messages.*`, `messages.send*`), not checked.
  - updates (`onUpdate`, `interceptUpdate`): an `Update` constructor name or one of the short ones (`updateShortMessage`, `updateShortChatMessage`, `updateShortSentMessage`); `onUpdate` also takes `new_message`, `edit_message` and `delete_message`.
  - lists (`account.read`, `account.write`): one of the fixed words.
  - hosts (`fetch`): a host name; lowercased; covers the host and its subdomains.
  - no scope at all: every other grant. `grant '<entry>' takes no scopes` otherwise.
- **notes:**
  - a glob matches by prefix: `call(messages.*)` covers `messages.getHistory`, but never a [dangerous method](#dangerous-methods).
  - `fetch(github.com)` covers `github.com` and `api.github.com`, not `notgithub.com`.
  - `'*'` as an update or method name in `tg.onUpdate('*')`, `tg.interceptRpc('*')` or `tg.interceptUpdate('*')` needs the bare grant.

Example:

```ts
export default defineScript({
  name: 'scopes',
  grants: ['call(messages.get*)', 'onUpdate(updateUserStatus)', 'fetch(github.com)'],
  setup(tg) {},
})
```

### how covering works

```ts
// approved: ['call']           declared: ['call(help.getConfig)']   starts
// approved: ['fetch(github.com)'] declared: ['fetch(api.github.com)'] starts
// approved: ['call']           declared: ['call(messages.deleteMessages)'] asks
```

when a script starts, its declared grants must be covered by what you approved for this account. if they are, it starts without asking; if not, it waits for approval.

- **grant:** n/a.
- **notes:**
  - a grant covers another of the same name when the scopes are equal, when it is bare, when it is a glob whose prefix covers the other's method or prefix, or when its host covers the other's host or subdomain.
  - an exact dangerous method (`call(messages.deleteMessages)`) is covered only by itself, never by a bare grant or a glob.
  - so a script edited to declare fewer or narrower grants starts silently; one that declares more stops and asks.
  - Allow stores exactly the declared list, replacing what was approved before.

Example:

```ts
// was approved with ['fetch(example.com)']
// after editing to this, it still starts without asking:
grants: ['fetch(api.example.com)']
```

### tiers

```ts
// neutral | caution | dangerous
```

every grant has a tier that says how much trust it asks for. the tier is listed in each grant item below.

- **grant:** n/a.
- **notes:**
  - neutral: reads and reactions that stay within what a script is for (`onUpdate`, `account.read`, `fetch`, `notify`...).
  - caution: acting as you or reaching outside tele (`account.write`, `interceptSendMessage`, `clipboard.read`, `options`, `app`, `calls`, `accounts`, `files.write`, `ui.read`, `ui.write`, bare `call`...).
  - dangerous: `unsafe.exec`, `unsafe.automate`, `unsafe.disableApiFiltering`, and exact entries for dangerous methods (`call(messages.deleteMessages)`, `interceptRpc(channels.leaveChannel)`).
  - the consent box shows every grant in plain words and puts the dangerous ones in a bold "Dangerous: ..." line at the end.

Example:

```ts
grants: [
  'onUpdate(new_message)',        // neutral
  'account.write(send)',          // caution
  'call(messages.deleteHistory)', // dangerous
]
```

### what the user sees

```ts
// Script permissions
// <name> asks to:
// - <one line per grant name>
//
// Dangerous: <dangerous entries>.
```

the consent box shows one bullet per grant name, in a fixed order (account.read, account.write, onUpdate, call, interceptRpc, interceptUpdate, interceptSendMessage, fetch, clipboard.read, clipboard.write, openUrl, notify, interceptLink, interceptNotification, scripts, app, interceptDrop, calls, accounts, ui.read, ui.write, files.write, options), then the dangerous line.

- **grant:** n/a.
- **notes:**
  - a bare grant shows its "everything" sentence; scoped ones show the scoped sentence with the scopes joined by commas (methods, updates and hosts as written; account scopes as words like "chats and contacts").
  - dangerous parts are joined with "; " in the bold line, in this order: "send {methods}" for `call`, "intercept {methods}" for `interceptRpc`, "turn off the account protection: log in, change the password and sessions, see login codes", "run any program on your computer, with your rights" and "press any button in tele for you".
  - the script page's Permissions list uses the same sentences, one per approved grant string.

Example:

```ts
grants: ['account.read(self, peers)', 'call(messages.deleteMessages)']
// shows:
// - Read your profile, chats and contacts.
// Dangerous: send messages.deleteMessages.
```

### revoking

```ts
// Scripts manager > script > Permissions > revoke
```

each approved grant on the script page has a revoke link. revoking removes that one string from this account's approval and restarts the script.

- **grant:** n/a.
- **notes:**
  - if the script still declares it, it waits for approval again; if you removed it from the code, it just runs with less.
  - turning a script off forgets all its grants; turning it on asks again.
  - 5 failures in a row also forget them.

Example:

```ts
// approved: ['account.read(peers)', 'notify']
// revoke 'notify' -> the script restarts and asks for 'notify' again
```

### account protection

```ts
'unsafe.disableApiFiltering' // the only way around it
```

some things are off limits whatever the grants say, so a script can't take over your account or read your login codes.

- **grant:** lifted only by `unsafe.disableApiFiltering`.
- **throws:** `TeleError` `forbidden`: `tg.call(<method>) can take over the account, it needs the grant 'unsafe.disableApiFiltering'` from `tg.call`, `<method> can take over the account, intercepting it needs the grant 'unsafe.disableApiFiltering'` from `tg.interceptRpc`.
- **notes:**
  - the takeover filter blocks every `auth.*` method and `account.getPasskeys`, `account.deletePasskey`, `account.registerPasskey`, `account.initPasskeyRegistration`, `account.registerDevice`, `account.unregisterDevice`, `account.deleteAccount`, `account.changePhone`, `account.getAuthorizations`, `account.resetAuthorization`, `account.acceptAuthorization`, `account.verifyPhone`, `account.verifyEmail`, `account.resetPassword`, `account.updatePasswordSettings`, `messages.requestUrlAuth`, `messages.acceptUrlAuth`, in `tg.call` and `tg.interceptRpc`. globs never match them.
  - the sensitive-data filter, applied to everything scripts decode: in messages from or to 777000 (telegram's service account), every run of 5 or more digits becomes the same number of `*`; `config.autologinToken` is dropped; `draftMessage` comes with an empty `message` and no `entities` unless the script has `account.read(draft)`.
  - `updateServiceNotification` never reaches listeners or interceptors; interceptors also never see messages from 777000 or (without `account.read(draft)`) `updateDraftMessage`; those pass through untouched.
  - a middleware can't replace a result that had hidden data: the original goes to tele and a warning says changing it needs `unsafe.disableApiFiltering`.

Example:

```ts
setup(tg) {
  tg.onNewMessage((message) => {
    if (message.senderId === 777000n) console.log(message.text) // 'Login code: *****. Do not give...'
  })
}
```

### dangerous methods

```ts
'call(messages.deleteMessages)' // exact entry: allowed
'call(messages.*)'              // never covers it
```

methods that destroy data or spend money are only covered by an exact entry naming them, in `call` and `interceptRpc`. bare grants and globs skip them.

- **grant:** an exact `call(<method>)` or `interceptRpc(<method>)` entry; such an entry is dangerous tier and shows in the bold line of the consent box.
- **throws:** `TeleError` `not-granted` naming the exact entry, e.g. `tg.call(channels.deleteHistory) needs the grant 'call(channels.deleteHistory)'`.
- **notes:**
  - the list (the same one tele's MTProto console warns about): `account.deleteAccount`, `account.resetAuthorization`, `auth.resetAuthorizations`, `auth.logOut`, `account.updatePasswordSettings`, `channels.deleteChannel`, `channels.deleteHistory`, `messages.deleteHistory`, `messages.deleteChat`, `messages.deleteMessages`, `channels.deleteMessages`, `messages.editChatCreator`, `channels.deleteParticipantHistory`, `messages.deleteSavedHistory`, `messages.deleteScheduledMessages`, `photos.deletePhotos`, `stories.deleteStories`, `stickers.deleteStickerSet`, `contacts.deleteContacts`, `contacts.deleteByPhones`, `channels.leaveChannel`, `messages.deleteChatUser`, `account.setAccountTTL`, `payments.sendStarsForm`, `payments.sendPaymentForm`, `payments.transferStarGift`, `payments.convertStarGift`, `payments.upgradeStarGift`, `payments.updateStarGiftPrice`, `payments.resolveStarGiftOffer`, `payments.sendStarGiftOffer`, `payments.craftStarGift`, `messages.sendPaidReaction`, `payments.fulfillStarsSubscription`.
  - plus any method whose name contains `.delete` or `leave`, or ends in `TTL` (unless it's a getter like `getDefaultHistoryTTL`).
  - takeover methods among them (`auth.*`, `account.deleteAccount`...) also need `unsafe.disableApiFiltering`.
  - `account.write(delete)` is the exception: it allows `messages.deleteMessages` and `channels.deleteMessages` through `tg.call`, because deleting messages is what that grant means.

Example:

```ts
export default defineScript({
  name: 'cleanup bot',
  grants: ['call(messages.deleteHistory)'],
  setup(tg) {},
})
```

### grant: call

```ts
| 'call'
| `call(${Some<tl.RpcMethod | `${string}*`>})`
```

lets `tg.call` send api methods as you.

- **grant:** `call`, `call(*)`, `call(<method>, ...)`, `call(<prefix>*)`.
- **parameters:**
  - `scope` (method name or `prefix*`): which methods. exact names are checked against the schema at start.
- **tier:** neutral when scoped; caution for bare `call` / `call(*)`; dangerous for an exact dangerous method.
- **consent text:** bare: "Send any request as you, except dangerous ones."; scoped: "Send these requests as you: {methods}."; exact dangerous entries go into the bold line as "send {methods}".
- **unlocks:** `tg.call(request, options?)` for the covered methods.
- **throws:** `TeleError` `not-granted` (`tg.call(<method>) needs the grant 'call(<method>)'`, or the matching `account.*` grant when one exists); `TeleError` `forbidden` for takeover methods.
- **notes:**
  - the high-level helpers (`tg.getMe`, `tg.sendMessage`...) go through `tg.call` too; their methods are also allowed by the matching `account.read` / `account.write` scope, so you rarely need `call` for them.
  - [account protection](#account-protection) and [dangerous methods](#dangerous-methods) apply.

Example:

```ts
export default defineScript({
  name: 'config peek',
  grants: ['call(help.getConfig)'],
  async setup(tg) {
    const config = await tg.call({ _: 'help.getConfig' })
    console.log('this dc:', config.thisDc)
  },
})
```

### grant: onUpdate

```ts
| 'onUpdate'
| `onUpdate(${Some<
  tl.UpdateName | 'new_message' | 'edit_message' | 'delete_message'
>})`
```

lets the script listen to updates the account receives.

- **grant:** `onUpdate`, `onUpdate(*)`, `onUpdate(<update>, ...)`, `onUpdate(new_message)`, `onUpdate(edit_message)`, `onUpdate(delete_message)`.
- **parameters:**
  - `scope` (update name or event): `updateNewMessage`, `updateUserStatus`, any `Update` constructor or the short ones; or `new_message`, `edit_message`, `delete_message` for the message events.
- **tier:** neutral.
- **consent text:** bare: "See everything this account receives."; scoped: "See these updates: {names}.".
- **unlocks:**
  - `tg.onUpdate(type, listener)` for the covered names; `tg.onUpdate('*', listener)` needs the bare grant.
  - `tg.onNewMessage(callback)` with `new_message`, `tg.onMessageEdited(callback)` with `edit_message`, `tg.onMessageDeleted(callback)` with `delete_message`.
  - any `onUpdate` grant lets `message.chat` and `message.sender` read tele's peer cache.
- **throws:** `TeleError` `not-granted`, e.g. `tg.onUpdate('updateDeleteMessages') needs the grant 'onUpdate(updateDeleteMessages)'`.
- **notes:**
  - the events and the raw names are separate: `onUpdate(updateNewMessage)` doesn't allow `tg.onNewMessage`, and `onUpdate(new_message)` doesn't allow `tg.onUpdate('updateNewMessage')`. the bare grant allows both.

Example:

```ts
export default defineScript({
  name: 'status watcher',
  grants: ['onUpdate(updateUserStatus)'],
  setup(tg) {
    tg.onUpdate('updateUserStatus', (update) => {
      console.log(update.userId, update.status._)
    })
  },
})
```

### grant: interceptRpc

```ts
| 'interceptRpc'
| `interceptRpc(${Some<tl.RpcMethod | `${string}*`>})`
```

lets the script hold, change, answer or block the requests tele itself sends.

- **grant:** `interceptRpc`, `interceptRpc(*)`, `interceptRpc(<method>, ...)`, `interceptRpc(<prefix>*)`.
- **parameters:**
  - `scope` (method name or `prefix*`): which methods.
- **tier:** neutral; dangerous for an exact dangerous method.
- **consent text:** bare: "Change, answer or block any request tele sends, except dangerous ones."; scoped: "Change, answer or block these requests from tele: {methods}."; exact dangerous entries go into the bold line as "intercept {methods}".
- **unlocks:** `tg.interceptRpc(method, middleware)` for covered names and patterns; `tg.interceptRpc('*', ...)` needs the bare grant; a pattern like `'messages.*'` needs a glob that covers it or the bare grant.
- **throws:** `TeleError` `not-granted` (`tg.interceptRpc('<method>') needs the grant 'interceptRpc(<method>)'`); `TeleError` `forbidden` for takeover methods.
- **notes:**
  - patterns only ever catch methods the grants allow, so dangerous methods still need an exact entry and takeover methods `unsafe.disableApiFiltering`.
  - never sees the script's own `tg.call` traffic.

Example:

```ts
export default defineScript({
  name: 'no typing',
  grants: ['interceptRpc(messages.setTyping)'],
  setup(tg) {
    tg.interceptRpc('messages.setTyping', () => true) // answer locally, never send
  },
})
```

### grant: interceptUpdate

```ts
| 'interceptUpdate'
| `interceptUpdate(${Some<tl.UpdateName>})`
```

lets the script change or drop updates before tele and listeners see them.

- **grant:** `interceptUpdate`, `interceptUpdate(*)`, `interceptUpdate(<update>, ...)`.
- **parameters:**
  - `scope` (update name): any `Update` constructor or a short one.
- **tier:** neutral.
- **consent text:** bare: "Change or hide any update before tele sees it."; scoped: "Change or hide these updates: {names}.".
- **unlocks:** `tg.interceptUpdate(type, middleware)`; `'*'` needs the bare grant.
- **throws:** `TeleError` `not-granted` (`tg.interceptUpdate('<name>') needs the grant 'interceptUpdate(<name>)'`).
- **notes:**
  - without `unsafe.disableApiFiltering` interceptors never see `updateServiceNotification`, messages from 777000, or `updateDraftMessage` without `account.read(draft)`.

Example:

```ts
export default defineScript({
  name: 'hide online',
  grants: ['interceptUpdate(updateUserStatus)'],
  setup(tg) {
    tg.interceptUpdate('updateUserStatus', () => 'drop')
  },
})
```

### grant: interceptSendMessage

```ts
| 'interceptSendMessage'
```

lets the script see, change or stop what you send before it leaves.

- **grant:** `interceptSendMessage`.
- **tier:** caution.
- **consent text:** "Change or stop the messages you send.".
- **unlocks:** `tg.interceptSendMessage(middleware)` and `tg.interceptSendMessage(filter, middleware)` for every kind (text, files, documents, photos, forwards, inline results).
- **throws:** `TeleError` `not-granted` (`tg.interceptSendMessage needs the grant 'interceptSendMessage'`).
- **notes:**
  - secret chats never reach scripts.

Example:

```ts
export default defineScript({
  name: 'shrug',
  grants: ['interceptSendMessage'],
  setup(tg) {
    tg.interceptSendMessage({ text: /\/shrug/ }, ({ message }) => {
      const current = typeof message.text === 'string' ? message.text : message.text.text
      message.text = current.replace('/shrug', '¯\\_(ツ)_/¯')
      return 'send'
    })
  },
})
```

### grant: account.read

```ts
| 'account.read'
```

every `account.read` scope at once: profile, chats and contacts, messages, chat list, history and drafts.

- **grant:** `account.read`, `account.read(*)`.
- **tier:** neutral.
- **consent text:** "Read your profile, chats, messages, history and drafts.".
- **unlocks:** everything in the six scope items below.
- **notes:**
  - prefer the scopes you need; the box is shorter and you approve less.

Example:

```ts
grants: ['account.read']
```

### grant: account.read(self)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft'
>})`
```

lets the script read your own profile.

- **grant:** `account.read(self)`.
- **tier:** neutral.
- **consent text:** "Read your profile." (scopes are joined: "Read your profile, chats and contacts.").
- **unlocks:** `tg.peers.self`, `tg.getMe()`, and the raw methods `users.getUsers` and `users.getFullUser` in `tg.call`.
- **throws:** `TeleError` `not-granted` (`tg.peers.self needs the grant 'account.read(self)'`).
- **notes:**
  - the raw methods are allowed as a whole, so `users.getUsers` works for any user with this scope too.

Example:

```ts
const me = await tg.getMe()
console.log('logged in as', me._ === 'user' ? me.firstName : '?')
```

### grant: account.read(peers)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft'
>})`
```

lets the script look up users, bots, groups and channels.

- **grant:** `account.read(peers)`.
- **tier:** neutral.
- **consent text:** "Read your chats and contacts.".
- **unlocks:** `tg.peers.get(peer)`, `tg.peers.resolve(username)`, `tg.resolvePeer` / `resolveUser` / `resolveChannel` for marked ids, `Peer`s and usernames, `tg.getUser`, `tg.getChat`, `tg.getFullUser`, `tg.getFullChat`, `message.chat` / `message.sender` from tele's cache, `tg.tele.ignored.list()`, `tg.tele.ghost.get()` / `list()`, `tg.tele.localNames.list()`, and the raw methods `users.getUsers`, `users.getFullUser`, `contacts.resolveUsername`, `channels.getChannels`, `channels.getFullChannel`, `messages.getChats`, `messages.getFullChat`.
- **throws:** `TeleError` `not-granted` (`tg.peers.get needs the grant 'account.read(peers)'`).
- **notes:**
  - input peers, users and chats you already hold (from an update, say) convert without this grant.

Example:

```ts
const durov = await tg.peers.resolve('durov')
console.log(durov?.name, durov?.id)
```

### grant: account.read(messages)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft'
>})`
```

lets the script read messages by id, download media and look into tele's message cache.

- **grant:** `account.read(messages)`.
- **tier:** neutral.
- **consent text:** "Read your messages.".
- **unlocks:** `tg.getMessages`, `tg.downloadMedia` (both forms), `tg.decorateMessages`, `tg.getCachedMessage` (always `null` without it), the `message` field of `tg.interceptNotification`, the cached `previous` of `tg.onMessageEdited` and `messages` of `tg.onMessageDeleted`, and the raw methods `messages.getMessages` and `channels.getMessages`.
- **throws:** `TeleError` `not-granted` (`tg.downloadMedia needs the grant 'account.read(messages)'`).

Example:

```ts
const [message] = await tg.getMessages('me', [1])
console.log(message?.text)
```

### grant: account.read(dialogs)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft'
>})`
```

lets the script read your chat list and folders.

- **grant:** `account.read(dialogs)`.
- **tier:** neutral.
- **consent text:** "Read your chat list.".
- **unlocks:** `tg.getDialogs`, `tg.iterDialogs`, `tg.local.dialogs()`, `tg.local.unread()`, `tg.local.folders()`, and the raw methods `messages.getDialogs`, `messages.getPeerDialogs`, `messages.getPinnedDialogs`.
- **throws:** `TeleError` `not-granted` (`tg.local.dialogs needs the grant 'account.read(dialogs)'`).
- **notes:**
  - `tg.local.loaded()` needs nothing.

Example:

```ts
const unread = tg.local.unread()
console.log('badge:', unread.badge)
```

### grant: account.read(history)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft'
>})`
```

lets the script read chat history and search it.

- **grant:** `account.read(history)`.
- **tier:** neutral.
- **consent text:** "Read your chat history.".
- **unlocks:** `tg.getHistory`, `tg.iterHistory`, and the raw methods `messages.getHistory`, `messages.search`, `messages.getReplies`.
- **throws:** `TeleError` `not-granted` (`tg.call(messages.getHistory) needs the grant 'account.read(history)'`).

Example:

```ts
for await (const message of tg.iterHistory('me', { limit: 50 })) {
  if (message.mediaType === 'photo') console.log('photo', message.id)
}
```

### grant: account.read(draft)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft'
>})`
```

lets the script read what you are typing and your saved drafts.

- **grant:** `account.read(draft)`.
- **tier:** neutral.
- **consent text:** "Read your drafts.".
- **unlocks:** `tg.local.draft(chat)`, `tg.compose.get(peer?)`, `tg.compose.onInput(callback)`, draft texts in every decoded result and update (without it `draftMessage` comes with an empty `message` and no `entities`), and `updateDraftMessage` in update interceptors.
- **throws:** `TeleError` `not-granted` (`tg.compose.onInput needs the grant 'account.read(draft)'`).

Example:

```ts
tg.compose.onInput(({ chatId, text }) => {
  if (text.length > 4000) tg.toast('that is getting long')
})
```

### grant: account.write

```ts
| 'account.write'
```

every `account.write` scope at once: send, edit, delete, forward, react, read, typing and drafts.

- **grant:** `account.write`, `account.write(*)`.
- **tier:** caution.
- **consent text:** "Act as you: send, edit, delete and forward messages, react, read chats, type and change drafts.".
- **unlocks:** everything in the eight scope items below.

Example:

```ts
grants: ['account.write']
```

### grant: account.write(send)

```ts
`account.write(${Some<
  | 'send'
  | 'edit'
  | 'delete'
  | 'forward'
  | 'react'
  | 'read'
  | 'typing'
  | 'draft'
>})`
```

lets the script send messages and upload files as you.

- **grant:** `account.write(send)`.
- **tier:** caution.
- **consent text:** "Act as you: send messages." (scopes are joined: "Act as you: send messages, react.").
- **unlocks:** `tg.sendMessage`, `tg.sendMedia`, `tg.sendFile`, `tg.uploadFile`, `message.reply`, and the raw methods `messages.sendMessage`, `messages.sendMedia`, `messages.sendMultiMedia`.
- **throws:** `TeleError` `not-granted` (`tg.uploadFile needs the grant 'account.write(send)'`).

Example:

```ts
await tg.sendMessage('me', md`**reminder:** drink water`)
```

### grant: account.write(edit)

```ts
`account.write(${Some<
  | 'send'
  | 'edit'
  | 'delete'
  | 'forward'
  | 'react'
  | 'read'
  | 'typing'
  | 'draft'
>})`
```

lets the script edit messages.

- **grant:** `account.write(edit)`.
- **tier:** caution.
- **consent text:** "Act as you: edit messages.".
- **unlocks:** `tg.editMessage`, `message.edit`, and the raw method `messages.editMessage`.
- **throws:** `TeleError` `not-granted` (`tg.call(messages.editMessage) needs the grant 'account.write(edit)'`).

Example:

```ts
const sent = await tg.sendMessage('me', 'counting...')
await sent.edit('done')
```

### grant: account.write(delete)

```ts
`account.write(${Some<
  | 'send'
  | 'edit'
  | 'delete'
  | 'forward'
  | 'react'
  | 'read'
  | 'typing'
  | 'draft'
>})`
```

lets the script delete messages.

- **grant:** `account.write(delete)`.
- **tier:** caution.
- **consent text:** "Act as you: delete messages.".
- **unlocks:** `tg.deleteMessages`, `message.delete`, and the raw methods `messages.deleteMessages` and `channels.deleteMessages` (both on the [dangerous list](#dangerous-methods), allowed here because deleting messages is what this grant is for).
- **throws:** `TeleError` `not-granted` (`tg.call(messages.deleteMessages) needs the grant 'account.write(delete)'`).
- **notes:**
  - tele applies the deletion at once, so the messages vanish without waiting for the server.

Example:

```ts
await tg.deleteMessages('me', [101, 102], { revoke: true })
```

### grant: account.write(forward)

```ts
`account.write(${Some<
  | 'send'
  | 'edit'
  | 'delete'
  | 'forward'
  | 'react'
  | 'read'
  | 'typing'
  | 'draft'
>})`
```

lets the script forward messages.

- **grant:** `account.write(forward)`.
- **tier:** caution.
- **consent text:** "Act as you: forward messages.".
- **unlocks:** `tg.forwardMessages`, `message.forward`, and the raw method `messages.forwardMessages`.
- **throws:** `TeleError` `not-granted` (`tg.call(messages.forwardMessages) needs the grant 'account.write(forward)'`).

Example:

```ts
tg.onNewMessage((message) => {
  if (message.text.includes('#save')) message.forward('me')
})
```

### grant: account.write(react)

```ts
`account.write(${Some<
  | 'send'
  | 'edit'
  | 'delete'
  | 'forward'
  | 'react'
  | 'read'
  | 'typing'
  | 'draft'
>})`
```

lets the script set reactions.

- **grant:** `account.write(react)`.
- **tier:** caution.
- **consent text:** "Act as you: react.".
- **unlocks:** `tg.setReaction`, `message.react`, and the raw method `messages.sendReaction`.
- **throws:** `TeleError` `not-granted` (`tg.call(messages.sendReaction) needs the grant 'account.write(react)'`).

Example:

```ts
tg.onNewMessage((message) => {
  if (message.text === '+1') message.react('\u{1F44D}')
})
```

### grant: account.write(read)

```ts
`account.write(${Some<
  | 'send'
  | 'edit'
  | 'delete'
  | 'forward'
  | 'react'
  | 'read'
  | 'typing'
  | 'draft'
>})`
```

lets the script mark chats as read.

- **grant:** `account.write(read)`.
- **tier:** caution.
- **consent text:** "Act as you: mark chats as read.".
- **unlocks:** `tg.readHistory`, `message.read`, and the raw methods `messages.readHistory` and `channels.readHistory`.
- **throws:** `TeleError` `not-granted` (`tg.readHistory needs the grant 'account.write(read)'`).

Example:

```ts
tg.onNewMessage((message) => {
  if (message.chat?.kind === 'channel') message.read()
})
```

### grant: account.write(typing)

```ts
`account.write(${Some<
  | 'send'
  | 'edit'
  | 'delete'
  | 'forward'
  | 'react'
  | 'read'
  | 'typing'
  | 'draft'
>})`
```

lets the script show typing and other chat actions.

- **grant:** `account.write(typing)`.
- **tier:** caution.
- **consent text:** "Act as you: show typing.".
- **unlocks:** `tg.sendTyping`, and the raw method `messages.setTyping`.
- **throws:** `TeleError` `not-granted` (`tg.call(messages.setTyping) needs the grant 'account.write(typing)'`).

Example:

```ts
await tg.sendTyping('me', 'recordVoice')
```

### grant: account.write(draft)

```ts
`account.write(${Some<
  | 'send'
  | 'edit'
  | 'delete'
  | 'forward'
  | 'react'
  | 'read'
  | 'typing'
  | 'draft'
>})`
```

lets the script change drafts and the compose field.

- **grant:** `account.write(draft)`.
- **tier:** caution.
- **consent text:** "Act as you: drafts.".
- **unlocks:** `tg.setDraft`, `tg.compose.set`, `tg.compose.insert`, and the raw method `messages.saveDraft`.
- **throws:** `TeleError` `not-granted` (`tg.compose.set needs the grant 'account.write(draft)'`).

Example:

```ts
await tg.compose.insert(' -- sent from tele')
```

### grant: fetch(host)

```ts
| 'fetch'
| `fetch(${string})`
```

lets the global `fetch` reach the internet.

- **grant:** `fetch` (any host), `fetch(*)`, `fetch(<host>, ...)`.
- **parameters:**
  - `scope` (host): a host name like `api.example.com`; lowercased; must be a valid domain (`grant 'fetch(x)': 'x' is not a host` otherwise). covers the host and all its subdomains.
- **tier:** neutral.
- **consent text:** bare: "Connect to any server on the internet."; scoped: "Connect to these servers: {hosts}.".
- **unlocks:** `fetch(url, init?)` to covered hosts, and redirects to covered hosts.
- **throws:** `TeleError` `not-granted` synchronously (`fetch(<url>) needs the grant 'fetch(<host>)'`); a redirect to another host rejects with `TeleError` `not-granted` whose `grant` is the `fetch(<host>)` to add.
- **notes:**
  - only http and https.

Example:

```ts
export default defineScript({
  name: 'zen',
  grants: ['fetch(github.com)'],
  async setup() {
    const response = await fetch('https://api.github.com/zen', { headers: { 'user-agent': 'tele' } })
    console.log(await response.text())
  },
})
```

### grant: clipboard.read

```ts
| 'clipboard.read'
```

lets the script read the clipboard's text.

- **grant:** `clipboard.read`.
- **tier:** caution.
- **consent text:** "Read the clipboard.".
- **unlocks:** `tg.clipboard.read()`.
- **throws:** `TeleError` `not-granted` (`tg.clipboard.read needs the grant 'clipboard.read'`).

Example:

```ts
const text = tg.clipboard.read()
if (/^https?:\/\//.test(text)) tg.toast('a link is in your clipboard')
```

### grant: clipboard.write

```ts
| 'clipboard.write'
```

lets the script put text into the clipboard.

- **grant:** `clipboard.write`.
- **tier:** neutral.
- **consent text:** "Change the clipboard.".
- **unlocks:** `tg.clipboard.write(text)`.
- **throws:** `TeleError` `not-granted` (`tg.clipboard.write needs the grant 'clipboard.write'`).

Example:

```ts
tg.clipboard.write(String(tg.selfId))
tg.toast('your id is copied')
```

### grant: openUrl

```ts
| 'openUrl'
```

lets the script open links as if you clicked them in tele.

- **grant:** `openUrl`.
- **tier:** neutral.
- **consent text:** "Open links.".
- **unlocks:** `tg.openUrl(link)` (tg:// and t.me links open inside tele, others in the browser).
- **throws:** `TeleError` `not-granted` (`tg.openUrl needs the grant 'openUrl'`).

Example:

```ts
tg.openUrl('https://t.me/durov')
```

### grant: notify

```ts
| 'notify'
```

lets the script show desktop notifications.

- **grant:** `notify`.
- **tier:** neutral.
- **consent text:** "Show notifications.".
- **unlocks:** `tg.notify(title, text)`.
- **throws:** `TeleError` `not-granted` (`tg.notify needs the grant 'notify'`).
- **notes:**
  - `tg.toast` and `tg.ui.notice` need no grant.

Example:

```ts
tg.notify('backup', 'all chats exported')
```

### grant: interceptLink

```ts
| 'interceptLink'
```

lets the script see, rewrite or block every link opened in this account's window.

- **grant:** `interceptLink`.
- **tier:** caution.
- **consent text:** "See, change or block every link you open.".
- **unlocks:** `tg.interceptLink(interceptor)` and `tg.interceptLink(pattern, interceptor)`.
- **throws:** `TeleError` `not-granted` (`tg.interceptLink needs the grant 'interceptLink'`).

Example:

```ts
tg.interceptLink(/^https:\/\/(www\.)?youtube\.com/, ({ url }) => url.replace('youtube.com', 'yewtu.be'))
```

### grant: interceptNotification

```ts
| 'interceptNotification'
```

lets the script see and hide desktop notifications before tele shows them.

- **grant:** `interceptNotification`.
- **tier:** caution.
- **consent text:** "See or hide your notifications.".
- **unlocks:** `tg.interceptNotification(interceptor)`.
- **throws:** `TeleError` `not-granted` (`tg.interceptNotification needs the grant 'interceptNotification'`).
- **notes:**
  - the notification's `message` is filled only with `account.read(messages)`.

Example:

```ts
tg.interceptNotification(({ kind }) => (kind === 'reaction' ? 'drop' : 'show'))
```

### grant: options

```ts
| 'options'
```

lets the script change tele's settings and tele's own per-chat features.

- **grant:** `options`.
- **tier:** caution.
- **consent text:** "Change any of tele's settings, including ghost mode, link rewrites and the checkmark server, and your ignore list, local names and per-chat ghost mode.".
- **unlocks:** `tg.options.set(id, value)`, `tg.tele.ignored.set`, `tg.tele.ghost.set`, `tg.tele.localNames.set`.
- **throws:** `TeleError` `not-granted` (`tg.options.set needs the grant 'options'`).
- **notes:**
  - reading settings (`tg.options.list`, `get`, `onChange`) needs nothing; reading `tg.tele` lists needs `account.read(peers)`.

Example:

```ts
const { restart } = tg.options.set('tele-ghost', true)
if (restart) tg.toast('restart tele to apply')
```

### grant: scripts

```ts
| 'scripts'
```

lets the script talk to the account's other running scripts.

- **grant:** `scripts`.
- **tier:** neutral.
- **consent text:** "Talk to your other scripts: send them messages and call what they offer.".
- **unlocks:** `tg.scripts.emit`, `tg.scripts.on`, `tg.scripts.expose`, `tg.scripts.call`.
- **throws:** `TeleError` `not-granted` (`tg.scripts.emit needs the grant 'scripts'`).
- **notes:**
  - both ends need it, so you see both sides in their consent boxes. `tg.scripts.list()` needs nothing.

Example:

```ts
tg.scripts.expose('ping', () => 'pong')
```

### grant: files.write

```ts
| 'files.write'
```

lets the script save downloads to any path on disk.

- **grant:** `files.write`.
- **tier:** caution.
- **consent text:** "Save files anywhere on your computer.".
- **unlocks:** `tg.downloadMedia(target, { saveTo: '<absolute path>' })`.
- **throws:** `TeleError` `not-granted` (`tg.downloadMedia({ saveTo }) needs the grant 'files.write'`).
- **notes:**
  - `saveTo: 'downloads'` (tele's download folder) and `tg.ui.saveFile` (you pick the path) need no `files.write`; downloading still needs `account.read(messages)`.

Example:

```ts
const path = await tg.downloadMedia(message, { saveTo: 'D:/archive/' })
console.log('saved to', path)
```

### grant: app

```ts
| 'app'
```

lets the script control tele itself: theme, window and music player.

- **grant:** `app`.
- **tier:** caution.
- **consent text:** "Control tele: the theme and colors, the window title and badge, the music player.".
- **unlocks:** `tg.app.theme.setDark`, `tg.app.theme.setColors`, `tg.app.window.setTitle`, `tg.app.window.setBadge`, `tg.app.window.flash`, `tg.app.player.play` / `pause` / `toggle` / `stop` / `next` / `previous`.
- **throws:** `TeleError` `not-granted` (`tg.app.theme.setColors needs the grant 'app'`).
- **notes:**
  - free without it: `tg.app.theme.get`, `color`, `onChange`, `tg.app.player.current`, `onChange`.

Example:

```ts
const undo = tg.app.theme.setColors({ windowBg: '#101418' })
setTimeout(undo, 10_000)
```

### grant: interceptDrop

```ts
| 'interceptDrop'
```

lets the script see files and text dropped or pasted into chats and handle them instead of tele.

- **grant:** `interceptDrop`.
- **tier:** caution.
- **consent text:** "See the files and text you drop or paste into chats and handle them instead of tele.".
- **unlocks:** `tg.interceptDrop(interceptor)`.
- **throws:** `TeleError` `not-granted` (`tg.interceptDrop needs the grant 'interceptDrop'`).
- **notes:**
  - secret chats are never offered.

Example:

```ts
tg.interceptDrop(({ files }) => (files.some((file) => file.name.endsWith('.exe')) ? 'drop' : 'accept'))
```

### grant: calls

```ts
| 'calls'
```

lets the script see and control this account's calls.

- **grant:** `calls`.
- **tier:** caution.
- **consent text:** "See your calls, answer, decline or start them, mute you.".
- **unlocks:** all of `tg.calls`: `current`, `onChange`, `answer`, `hangup`, `setMuted`, `start`.
- **throws:** `TeleError` `not-granted` (`tg.calls.current needs the grant 'calls'`).
- **notes:**
  - only calls of the account the script runs in.

Example:

```ts
tg.calls.onChange((call) => {
  if (call?.incoming && call.state === 'waitingIncoming') console.log('call from', call.user.name)
})
```

### grant: accounts

```ts
| 'accounts'
```

lets the script list the accounts logged into tele and switch between them.

- **grant:** `accounts`.
- **tier:** caution.
- **consent text:** "See your other accounts in tele and switch between them.".
- **unlocks:** `tg.accounts.list()`, `tg.accounts.switchTo(id)`.
- **throws:** `TeleError` `not-granted` (`tg.accounts.list needs the grant 'accounts'`).
- **notes:**
  - it never lets a script act as another account; each account approves its own scripts.

Example:

```ts
const total = tg.accounts.list().reduce((sum, account) => sum + account.unread, 0)
tg.toast(`${total} unread across accounts`)
```

### grant: ui.read

```ts
| 'ui.read'
```

lets the script look at tele's own interface: every window's widgets, their texts, buttons and layout.

- **grant:** `ui.read`.
- **tier:** caution.
- **consent text:** "See everything tele shows in its windows: texts, buttons and layout.".
- **unlocks:** `tg.ui.widgets.roots()`, `tg.ui.widgets.find(...)`, `tg.ui.widgets.observe(...)`, and on every `Widget` its getters, `parent`, `children`, `find` and `closest`. the api itself is documented in the widget layer section.
- **throws:** `TeleError` `not-granted` (`tg.ui.widgets.roots needs the grant 'ui.read'`).
- **notes:**
  - what tele shows includes message texts, names and anything else on screen, so this sees much of what `account.read` would.
  - changing widgets needs `ui.write`; clicking them needs `unsafe.automate`.

Example:

```ts
export default defineScript({
  name: 'window peek',
  grants: ['ui.read'],
  setup(tg) {
    console.log('tele has', tg.ui.widgets.roots().length, 'top-level windows')
  },
})
```

### grant: ui.write

```ts
| 'ui.write'
```

lets the script change tele's interface: hide or show widgets, change their text, add widgets, rows and menu items.

- **grant:** `ui.write`.
- **tier:** caution.
- **consent text:** "Change, hide or add to anything tele shows.".
- **unlocks:** `widget.setVisible`, `widget.setText`, `widget.insert`, `widget.insertRow`, `widget.addMenuItem`. the api itself is documented in the widget layer section.
- **throws:** `TeleError` `not-granted` (`widget.setText needs the grant 'ui.write'`).
- **notes:**
  - finding the widgets to change still needs `ui.read`, so scripts declare both.
  - a changed text can make tele show something it didn't say: only allow it for scripts you trust to stay honest.

Example:

```ts
export default defineScript({
  name: 'hide stories',
  grants: ['ui.read', 'ui.write'],
  setup(tg) {
    return tg.ui.widgets.observe({ name: /stories/i }, (widget) => {
      widget.setVisible(false)
    })
  },
})
```

### grant: unsafe.exec

```ts
| 'unsafe.exec'
```

lets the script run programs on your computer.

- **grant:** `unsafe.exec`.
- **tier:** dangerous.
- **consent text:** bold line "Dangerous: run any program on your computer, with your rights."; on the script page "Run any program on your computer, with your rights.".
- **unlocks:** `tg.unsafe.exec(program, args?, options?)`.
- **throws:** `TeleError` `not-granted` (`tg.unsafe.exec needs the grant 'unsafe.exec'`).
- **notes:**
  - only install scripts with this grant from people you trust: it can do anything you can.
  - running (not detached) processes are killed when the script stops.

Example:

```ts
const { stdout } = await tg.unsafe.exec('git', ['-C', 'D:/notes', 'log', '-1', '--oneline'])
tg.toast(stdout.trim())
```

### grant: unsafe.automate

```ts
| 'unsafe.automate'
```

lets the script click any button in tele's interface for you.

- **grant:** `unsafe.automate`.
- **tier:** dangerous.
- **consent text:** bold line "Dangerous: press any button in tele for you."; on the script page "Press any button in tele for you.".
- **unlocks:** `widget.click()`. the api itself is documented in the widget layer section.
- **throws:** `TeleError` `not-granted` (`widget.click needs the grant 'unsafe.automate'`).
- **notes:**
  - a click is your click: it can confirm boxes, delete chats, log out sessions or pay, and no account protection or dangerous-method rule stands in the way.
  - finding the button still needs `ui.read`.

Example:

```ts
export default defineScript({
  name: 'auto confirm',
  grants: ['ui.read', 'unsafe.automate'],
  setup(tg) {
    return tg.ui.widgets.observe({ role: 'button', name: 'Join' }, (button) => {
      button.click()
    })
  },
})
```

### grant: unsafe.disableApiFiltering

```ts
| 'unsafe.disableApiFiltering'
```

turns off the account protection for this script.

- **grant:** `unsafe.disableApiFiltering`.
- **tier:** dangerous.
- **consent text:** bold line "Dangerous: turn off the account protection: log in, change the password and sessions, see login codes."; on the script page "Turn off the account protection: log in, change the password and sessions, see login codes.".
- **unlocks:**
  - takeover methods (`auth.*`, sessions, passwords, passkeys, `account.deleteAccount`...) in `tg.call` and `tg.interceptRpc`.
  - unfiltered results and updates: real login codes, `config.autologinToken`, draft texts.
  - `updateServiceNotification`, messages from 777000 and `updateDraftMessage` in listeners and interceptors.
  - replacing results that had hidden data in `interceptRpc`.
- **notes:**
  - dangerous methods still need exact `call(...)` / `interceptRpc(...)` entries.
  - a script with this grant can log in elsewhere as you. it exists for tools you write yourself.

Example:

```ts
export default defineScript({
  name: 'sessions',
  grants: ['call(account.getAuthorizations)', 'unsafe.disableApiFiltering'],
  async setup(tg) {
    const { authorizations } = await tg.call({ _: 'account.getAuthorizations' })
    console.log(authorizations.length, 'sessions')
  },
})
```

## errors and limits

### type TeleErrorCode

```ts
type TeleErrorCode =
  | 'not-granted'
  | 'forbidden'
  | 'handle-expired'
  | 'quota-exceeded'
  | 'not-found'
  | 'unsupported'
  | 'timed-out'
  | 'network'
  | 'internal'
```

the `code` of every `TeleError` tele throws. check `error.code`, not the message.

- **grant:** none.
- **notes:**
  - `not-granted`: a call needs a grant the script didn't declare or wasn't given; `error.grant` is the exact string to add. also a `fetch` redirect to a host without a grant.
  - `forbidden`: the [account protection](#account-protection) blocked a takeover method in `tg.call` or `tg.interceptRpc`.
  - `handle-expired`: something was used after its moment passed: `next()` after the request was already answered, a settings page used after `dispose()`, `ctx.setText` after the command finished.
  - `quota-exceeded`: `tg.downloadMedia` without `saveTo` for a file over 10 MB.
  - `not-found`: tele doesn't know the thing: a username nobody has, a marked id not in tele's cache (`resolvePeer` and the helpers built on it), `tg.readHistory` on a chat tele hasn't loaded, `tg.scripts.call` to a script that isn't running or doesn't expose that name.
  - `unsupported`: the action needs something that isn't there: a ui call when the account has no window, `message.reply()` and friends on a `Message` that didn't come from `tg`.
  - `timed-out`: `tg.scripts.call` got no answer in 30 s, `tg.unsafe.exec` hit its `timeout`, an upload or download ran out of time.
  - `network`: an upload or download failed.
  - `internal`: something broke on the other side: `tg.unsafe.exec` couldn't start the program, a `tg.scripts.call` handler threw, a send's answer had no message in it.

Example:

```ts
try {
  await tg.resolvePeer('@surely_nobody_has_this')
} catch (error) {
  if (error instanceof TeleError && error.code === 'not-found') tg.toast('no such user')
  else throw error
}
```

### RpcError and server errors

```ts
declare class RpcError extends Error {
  constructor(code: number, type: string)
  readonly name: 'RpcError'
  readonly code: number
  readonly type: string
  readonly seconds?: number
}
```

telegram's own errors reject `tg.call` (and `next()` in `interceptRpc`, and everything built on `tg.call`) with an `RpcError`.

- **grant:** none.
- **notes:**
  - `code` is the number (400, 403, 420...), `type` and `message` the error string (`USERNAME_NOT_OCCUPIED`, `FLOOD_WAIT_17`).
  - `seconds` is set for `FLOOD_WAIT_X`, `FLOOD_PREMIUM_WAIT_X` and `SLOWMODE_WAIT_X`.
  - a result tele can't decode rejects with `code` 0 and `can't read the result: ...`.
  - in `interceptRpc` you can return or throw an `RpcError` to answer tele with that error. a middleware that fails gives tele 400 `SCRIPT_FAILED`, one that runs out of time 400 `SCRIPT_TIMEOUT`.

Example:

```ts
try {
  await tg.call({ _: 'contacts.resolveUsername', username: 'x' })
} catch (error) {
  if (error instanceof RpcError && error.type === 'USERNAME_INVALID') console.warn('bad name')
}
```

### TypeError and argument errors

```ts
TypeError: <api>: <what is wrong>
```

wrong arguments are plain `TypeError`s, thrown synchronously, with the api name and often a path.

- **grant:** none.
- **notes:**
  - `tg.call` encodes the request right away: `users.getUsers.id[0]: inputPeerSelf is a InputPeer, not a InputUser`, `messages.sendMessage.peer: is required`, `x.y is not a method in the schema`.
  - inside an `async` function the throw becomes a rejection of that function's promise.
  - `InternalError: the script was stopped` means the script was stopped while the code still held `tg`.
  - `RangeError` is used for limits: `tg.storage is over its 16 MB quota`, `crypto.getRandomValues fills at most 65536 bytes`.

Example:

```ts
try {
  tg.call({ _: 'users.getUsers', id: [{ _: 'inputPeerSelf' }] } as never)
} catch (error) {
  console.error(error) // TypeError: users.getUsers.id[0]: inputPeerSelf is a InputPeer, not a InputUser
}
```

### faults and the log

```ts
// log line: <where>: <error with stack>
```

a fault is tele reporting that script code failed: an uncaught exception, a wrong return value or a timeout in something tele called.

- **grant:** none.
- **notes:**
  - logged at the fault level as `<where>: <error with stack>` (for example `interceptRpc messages.sendMessage: TypeError: ...`), shown as a toast "Script {name}: {error}", and added to the Notification centre.
  - tele's fault toasts for one script are merged: at most one toast per 5 s (the notices are still logged). the script's own `tg.toast` calls are never limited.
  - faults in handlers count toward the [5-failures rule](#the-5-failures-rule).
  - a start that fails logs `can't start: <error>` and shows the error under the switch.
  - `console.error` is just a log level: no toast, no fault.

Example:

```ts
tg.onNewMessage((message) => {
  JSON.stringify(message.raw) // throws on bigint: a fault, counted
})
```

### unhandled rejections

```ts
// log line: unhandled promise rejection: <reason>
```

a rejected promise nobody handles is logged as `unhandled promise rejection: <reason>`, with a toast, but not counted as a failure.

- **grant:** none.
- **notes:**
  - reported only when the job queue runs empty, so `await f()` that rejects inside a `try` is never reported.
  - errors thrown inside timer callbacks and promise jobs are logged and toasted the same way, also not counted.
  - a rejected `setup` promise during the start fails the start instead.

Example:

```ts
setTimeout(async () => {
  await tg.call({ _: 'help.getConfig' }).catch((error) => console.warn('handled:', error))
}, 1000)
```

### time budgets

```ts
// a call over its budget: "took too long and was stopped"
```

everything runs on tele's main thread, so every entry into script code has a time limit. over it, the code is stopped with an error that `try` / `catch` can't catch, logged as `took too long and was stopped`.

- **grant:** none.
- **notes:**

| where | budget | on error or timeout | counts as a failure |
|---|---|---|---|
| loading all modules | 3 s | the start fails | no |
| `setup`, its synchronous part | 2 s | the start fails | no |
| each update listener / event callback | 200 ms | fault, skipped | yes |
| `interceptRpc` middleware | 200 ms per synchronous turn, 10 s per request | fault; tele gets `next()`'s answer or 400 `SCRIPT_TIMEOUT` | yes |
| `interceptUpdate` middleware | 200 ms per turn, 2 s per batch | fault; the updates go through unchanged | yes |
| `interceptLink`, `interceptNotification`, `interceptDrop` | 10 s | fault; the link opens, the notification shows, the drop is accepted | yes |
| `interceptSendMessage` | 60 s | fault; the message isn't sent | yes |
| commands (`run`) | 60 s | fault; the typed text goes back into the field | yes |
| menu `visible(ctx)` | 200 ms | the item is hidden | yes |
| timer callback | 500 ms | logged, toasted | no |
| `then` callbacks when a `tg.call` settles | 200 ms | logged, toasted | no |
| promise jobs after any call | 1 s and 100000 jobs | `promise jobs took too long` | no |
| cleanup, each `onUnload` | 0.5 s each | logged | no |
| `tg.scripts.call` | 30 s | rejects `timed-out` | no |
| uploads and downloads | max(2 min, size at 50 KB/s) | rejects `timed-out` | no |
| REPL, synchronous part | 5 s | shown in the REPL | no |

  - nested calls share one deadline; awaiting doesn't use the budget, only running code does.
  - a slow script freezes tele for up to its budget, so keep handlers short and move heavy work behind `await`s and timers.

Example:

```ts
tg.onNewMessage((message) => {
  // fine: the listener returns at once, the slow part runs later in small steps
  setTimeout(() => analyze(message), 0)
})
```

### memory and stack

```ts
InternalError: out of memory
RangeError: Maximum call stack size exceeded
```

each script has its own memory and stack limits.

- **grant:** none.
- **notes:**
  - memory: 256 MB per script per account. over it, allocations throw a catchable `InternalError: out of memory`.
  - stack: 256 KB of javascript stack. deep recursion throws a catchable `RangeError: Maximum call stack size exceeded`.
  - uploads have no cap of their own; the 256 MB memory is the limit.

Example:

```ts
const depth = (n: number): number => (n === 0 ? 0 : 1 + depth(n - 1))
try {
  depth(1e6)
} catch (error) {
  console.warn('too deep:', error)
}
```

### storage and size limits

```ts
// tg.storage: 16 MB per script per account
```

the fixed size limits scripts run into.

- **grant:** none.
- **notes:**
  - `tg.storage`: 16 MB per script per account (keys plus serialized values), keys 1 to 256 characters; over the quota `set` throws `RangeError: tg.storage is over its 16 MB quota` and nothing changes.
  - persisted ghost messages: their own 16 MB per script per account.
  - `fetch`: responses up to 16 MB by default (`maxSize`), 30 s without data (`timeout`).
  - `tg.downloadMedia` into memory: 10 MB (`quota-exceeded` above; pass `saveTo` for bigger files).
  - `crypto.getRandomValues`: 65536 bytes per call.
  - logs: the last 2000 lines per script.
  - installing from a link: 5 MB.
  - metadata of scripts that are off is read from the first 1 MB of the entry file.
  - hot reload watches at most 512 paths in the scripts folder.

Example:

```ts
try {
  tg.storage.set('cache', hugeObject)
} catch (error) {
  if (error instanceof RangeError) tg.storage.delete('cache')
}
```

### flood waits

```ts
readonly seconds?: number // on RpcError
```

telegram rate-limits some requests with `FLOOD_WAIT_X`. tele handles short waits for you and hands long ones to the script.

- **grant:** none.
- **notes:**
  - `tg.call` (and every helper built on it, and `tg.peers.resolve`): a wait of 10 s or less is slept through and the same request is sent again; the promise just takes longer. a longer wait rejects at once with an `RpcError` whose `seconds` says how long.
  - `next()` in `interceptRpc` behaves like tele's own requests: tele waits out floods and migrations for it.
  - returning a `FLOOD_WAIT_X`, 5xx or `*_MIGRATE_*` error from a middleware makes tele resend the held request straight to the server, so faking those isn't useful.
  - resolving usernames is limited hard by telegram (a few dozen per hour); cache the results in `tg.storage`.

Example:

```ts
const callWithPatience = async <T>(run: () => Promise<T>): Promise<T> => {
  try {
    return await run()
  } catch (error) {
    if (error instanceof RpcError && error.seconds && error.seconds <= 60) {
      await new Promise<void>((resolve) => setTimeout(resolve, error.seconds! * 1000))
      return run()
    }
    throw error
  }
}
```

## globals

### the language

```ts
// QuickJS-ng 0.17, ES2025+
```

scripts get the full modern javascript standard library, plus a few web-style globals tele adds.

- **grant:** none.
- **notes:**
  - built in: `BigInt`, `Proxy`, `Reflect`, `Symbol.dispose` and `using`, `WeakRef`, `FinalizationRegistry`, `Iterator` helpers, `Set` methods, `Object.groupBy`, `Map.groupBy`, `Array.prototype.toSorted` / `findLast` / `at`, `Array.fromAsync`, `Promise.withResolvers`, `RegExp` `v` flag and `RegExp.escape`, `String.prototype.isWellFormed`, `JSON.rawJSON`, `Float16Array`, `Math.sumPrecise`, `Error` `cause`, `SharedArrayBuffer`, `Atomics`, `DOMException`, `escape` / `unescape`, `globalThis`, `Uint8Array` base64 and hex methods.
  - from tele: `console`, timers, `defineScript`, `fetch` (from `setup` on), `crypto`, `TextEncoder`, `TextDecoder`, `TeleError`, `RpcError`. QuickJS adds `atob`, `btoa`, `performance` and `queueMicrotask`.
  - `Date` uses the computer's time zone.

Example:

```ts
const byKind = Object.groupBy(messages, (message) => message.mediaType ?? 'text')
const { promise, resolve } = Promise.withResolvers<void>()
```

### what is not available

```ts
// not defined in scripts
// require, module, process, Buffer, __dirname, XMLHttpRequest, WebSocket,
// URL, URLSearchParams, AbortController, structuredClone, Intl,
// window, document, navigator, localStorage, setImmediate
```

scripts are not node and not a browser.

- **grant:** none.
- **notes:**
  - no node: no `require`, `module`, `process`, `Buffer`, file system or environment. files come from `tg.ui.openFile` / `tg.ui.saveFile` and `tg.downloadMedia`; programs from `tg.unsafe.exec`.
  - no dom: no `window`, `document`, `navigator`, `localStorage`. persist with `tg.storage`.
  - no `XMLHttpRequest` or `WebSocket`; use `fetch`.
  - no `URL`, `URLSearchParams`, `AbortController`, `structuredClone`, `Intl` (locale methods give plain output), `setImmediate`.
  - no npm packages: only relative imports and `'tele'`.
  - extra arguments to `setTimeout` / `setInterval` are ignored.

Example:

```ts
// instead of new URL(link).hostname
const hostname = (link: string) => /^[a-z]+:\/\/([^/:?#]+)/i.exec(link)?.[1]?.toLowerCase()
```

### console.log(...data)

```ts
declare var console: {
  log(...data: unknown[]): void
  info(...data: unknown[]): void
  debug(...data: unknown[]): void
  warn(...data: unknown[]): void
  error(...data: unknown[]): void
}
```

writes one info line to the script's log.

- **grant:** none.
- **parameters:**
  - `data` (`unknown[]`): values, formatted and joined with spaces.
- **returns:** `undefined`.
- **notes:**
  - goes to the script page, its console, the MTProto console and tele's `log.txt` as `script <name>: <text>`. no toast.
  - formatting: top-level strings as they are, nested strings quoted, bigints with `n` (`10n`), functions as `[function name]`, `Uint8Array(<length>) <hex of the first 32 bytes>…`, errors as `<name>: <message>` plus the stack, arrays `[a, b]`, objects `{ key: value }` with own enumerable keys (so `Map`, `Set` and `Date` print as `{  }` in text), cycles as `[circular]`, deeper than 6 levels as `{…}` / `[…]`.
  - when any argument is an object, the MTProto console also gets it as an expandable tree (maps, sets, dates and getters included).

Example:

```ts
console.log('peer', { id: 42n, name: 'alex' }, new Uint8Array([1, 2, 3]))
// peer { id: 42n, name: "alex" } Uint8Array(3) 010203
```

### console.info(...data)

```ts
info(...data: unknown[]): void
```

the same as `console.log`: an info line.

- **grant:** none.
- **parameters:**
  - `data` (`unknown[]`): values to log.
- **returns:** `undefined`.

Example:

```ts
console.info('cache warmed in', Math.round(performance.now()), 'ms')
```

### console.debug(...data)

```ts
debug(...data: unknown[]): void
```

the same as `console.log`: logged at the info level (there is no separate debug level).

- **grant:** none.
- **parameters:**
  - `data` (`unknown[]`): values to log.
- **returns:** `undefined`.

Example:

```ts
const DEBUG = false
if (DEBUG) console.debug('raw update', update)
```

### console.warn(...data)

```ts
warn(...data: unknown[]): void
```

writes a warning line; the console colors it and the Warnings tab shows it.

- **grant:** none.
- **parameters:**
  - `data` (`unknown[]`): values to log.
- **returns:** `undefined`.
- **notes:**
  - tele uses the same level for its own notes like `waiting for approval of ...` and `unknown grant '...' is ignored`.

Example:

```ts
if (!tg.local.loaded()) console.warn('the chat list is still loading')
```

### console.error(...data)

```ts
error(...data: unknown[]): void
```

writes an error line. it is only a log level: no toast, no fault, not counted as a failure.

- **grant:** none.
- **parameters:**
  - `data` (`unknown[]`): values to log; errors print with their stack.
- **returns:** `undefined`.

Example:

```ts
fetch('https://api.example.com/x').catch((error) => console.error('api is down:', error))
```

### setTimeout(callback, ms?)

```ts
declare function setTimeout(callback: () => void, ms?: number): number
```

runs `callback` once after `ms` milliseconds.

- **grant:** none.
- **parameters:**
  - `callback` (`() => void`): the function to run. strings are not evaluated.
  - `ms` (`number`, optional): the delay; missing, negative or `NaN` means 0.
- **returns:** a timer id (`number`) for `clearTimeout`.
- **throws:** `TypeError: a timer needs a function` when `callback` isn't a function.
- **notes:**
  - extra arguments after `ms` are ignored; the callback gets none.
  - fires on tele's main event loop (a few ms of jitter). each callback has 500 ms; errors are logged and toasted, not counted as failures.
  - every timer dies with the script; clearing them in a cleanup is optional.
  - long delays drift across sleep and clock changes; use `tg.schedule` for wall-clock times.

Example:

```ts
setTimeout(() => tg.toast('five seconds passed'), 5000)
```

### setInterval(callback, ms?)

```ts
declare function setInterval(callback: () => void, ms?: number): number
```

runs `callback` every `ms` milliseconds until cleared or until the script stops.

- **grant:** none.
- **parameters:**
  - `callback` (`() => void`): the function to run.
  - `ms` (`number`, optional): the period; at least 10 ms.
- **returns:** a timer id (`number`).
- **throws:** `TypeError: a timer needs a function`.
- **notes:**
  - same rules as `setTimeout`: no extra arguments, 500 ms per callback, gone when the script stops.

Example:

```ts
const timer = setInterval(() => console.log('connection:', tg.connection().state), 60_000)
```

### clearTimeout(id?)

```ts
declare function clearTimeout(id?: number): void
```

cancels a timer.

- **grant:** none.
- **parameters:**
  - `id` (`number`, optional): an id from `setTimeout` or `setInterval`.
- **returns:** `undefined`.
- **notes:**
  - the same function as `clearInterval`: either clears either kind. unknown or missing ids are ignored.

Example:

```ts
const pending = setTimeout(() => tg.toast('no reply in a minute'), 60_000)
tg.onNewMessage(() => clearTimeout(pending))
```

### clearInterval(id?)

```ts
declare function clearInterval(id?: number): void
```

cancels a timer; identical to `clearTimeout`.

- **grant:** none.
- **parameters:**
  - `id` (`number`, optional): an id from `setInterval` or `setTimeout`.
- **returns:** `undefined`.

Example:

```ts
let ticks = 0
const timer = setInterval(() => {
  if (++ticks === 3) clearInterval(timer)
}, 1000)
```

### fetch(url, init?)

```ts
declare function fetch(
  url: string,
  init?: {
    method?: string
    headers?: Record<string, string>
    body?: string | Uint8Array
    timeout?: number
    maxSize?: number
  },
): Promise<FetchResponse>
```

makes an http or https request through tele's network stack and resolves with the response.

- **grant:** `fetch(<host>)` (or a parent domain, or bare `fetch`).
- **parameters:**
  - `url` (`string`): an absolute `http://` or `https://` url.
  - `init.method` (`string`, optional): any method, uppercased; default `GET`.
  - `init.headers` (`Record<string, string>`, optional): a plain object of header names and values.
  - `init.body` (`string | Uint8Array`, optional): sent as UTF-8 text or raw bytes; `null` / `undefined` send nothing.
  - `init.timeout` (`number`, optional): milliseconds without any data before giving up; default 30000, `0` means none.
  - `init.maxSize` (`number`, optional): the largest response body in bytes; default 16 MB (16777216), `0` means no limit besides memory.
- **returns:** `Promise<FetchResponse>`. http errors (404, 500) still resolve, with `ok: false`.
- **throws:**
  - synchronously: `TypeError: fetch needs a url string`, `TypeError: fetch only takes http and https urls`, `TypeError: fetch: timeout is a number of milliseconds, 0 for no limit` (and the same for `maxSize` in bytes), `TypeError: fetch: body must be a string or a Uint8Array`, `TeleError` `not-granted` (`fetch(<url>) needs the grant 'fetch(<host>)'`).
  - rejects: `TypeError: fetch failed: <reason>` for network failures and timeouts, `TypeError: fetch: the response is over <maxSize> bytes`, `TeleError` `not-granted` (`fetch: the redirect to <url> needs the grant fetch(<host>)`) for a redirect to a host without a grant.
- **notes:**
  - defined right before `setup` runs; at module top level `fetch` doesn't exist yet.
  - redirects are followed hop by hop, only to http(s) hosts the grants allow.
  - goes through tele's own network access, so tele's proxy settings apply.
  - stopping the script aborts its requests; their promises never settle.
  - no streaming: the whole body is read, then the promise resolves.

Example:

```ts
const response = await fetch('https://api.example.com/translate', {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ text: 'hello', to: 'de' }),
  timeout: 10_000,
})
if (!response.ok) throw new Error(`translate failed: ${response.status}`)
const { result } = (await response.json()) as { result: string }
```

### type FetchResponse

```ts
interface FetchResponse {
  readonly ok: boolean
  readonly status: number
  readonly statusText: string
  readonly url: string
  readonly headers: Record<string, string>
  text(): Promise<string>
  json(): Promise<unknown>
  bytes(): Promise<Uint8Array>
}
```

what `fetch` resolves with: a plain object, not the web `Response` class.

- **grant:** none.
- **parameters:**
  - `ok` (`boolean`): `true` for status 200 to 299.
  - `status` (`number`): the http status code.
  - `statusText` (`string`): the server's reason phrase (`OK`, `Not Found`), can be empty with http/2.
  - `url` (`string`): the final url, after redirects.
  - `headers` (`Record<string, string>`): lowercase header names; repeated headers joined with `, `.
  - `text()` (`Promise<string>`): the body as UTF-8 text (invalid bytes become U+FFFD).
  - `json()` (`Promise<unknown>`): the body parsed as JSON; rejects with a `SyntaxError` for bad json.
  - `bytes()` (`Promise<Uint8Array>`): a copy of the raw body.
- **notes:**
  - the body readers can be called any number of times, in any order.
  - there is no `arrayBuffer()`, `blob()` or `body` stream; `(await response.bytes()).buffer` gives an `ArrayBuffer`.

Example:

```ts
const response = await fetch('https://api.github.com/repos/telegramdesktop/tdesktop')
console.log(response.status, response.headers['x-ratelimit-remaining'])
const repo = (await response.json()) as { stargazers_count: number }
```

### crypto.getRandomValues(array)

```ts
getRandomValues<T extends ArrayBufferView>(array: T): T
```

fills an integer typed array with cryptographically secure random bytes.

- **grant:** none.
- **parameters:**
  - `array` (`ArrayBufferView`): an integer typed array (`Uint8Array`, `Int32Array`, `BigUint64Array`...), at most 65536 bytes.
- **returns:** the same array, filled.
- **throws:** `TypeError: crypto.getRandomValues needs an integer typed array` for `DataView`, float arrays or non-views; `RangeError: crypto.getRandomValues fills at most 65536 bytes`.

Example:

```ts
const nonce = crypto.getRandomValues(new Uint8Array(16)).toHex()
```

### crypto.randomUUID()

```ts
randomUUID(): string
```

returns a random version 4 uuid like `3b241101-e2bb-4255-8caf-4136c566a962`.

- **grant:** none.
- **returns:** a lowercase uuid string from the secure random source.

Example:

```ts
tg.storage.set('install-id', tg.storage.get('install-id') ?? crypto.randomUUID())
```

### crypto.subtle.digest(algorithm, data)

```ts
type HashName = 'SHA-1' | 'SHA-256' | 'SHA-384' | 'SHA-512'
type HashAlgorithm = HashName | { name: HashName }
type BufferSource = ArrayBuffer | ArrayBufferView

digest(algorithm: HashAlgorithm, data: BufferSource): Promise<ArrayBuffer>
```

hashes bytes with SHA-1, SHA-256, SHA-384 or SHA-512.

- **grant:** none.
- **parameters:**
  - `algorithm` (`HashAlgorithm`): the hash name (case-insensitive) or `{ name }`.
  - `data` (`BufferSource`): the bytes to hash; turn strings into bytes with `TextEncoder`.
- **returns:** `Promise<ArrayBuffer>` with the digest.
- **throws:** rejects with `TypeError: the hash is SHA-1, SHA-256, SHA-384 or SHA-512` for anything else.

Example:

```ts
const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode('hello'))
console.log(new Uint8Array(hash).toHex())
```

### crypto.subtle.importKey(format, keyData, algorithm, extractable, usages)

```ts
importKey(
  format: 'raw',
  keyData: BufferSource,
  algorithm: { name: 'HMAC', hash: HashAlgorithm },
  extractable: boolean,
  usages: ('sign' | 'verify')[],
): Promise<CryptoKey>
```

imports raw bytes as an HMAC key for `sign` and `verify`.

- **grant:** none.
- **parameters:**
  - `format` (`'raw'`): the only supported format.
  - `keyData` (`BufferSource`): the secret; copied.
  - `algorithm` (`{ name: 'HMAC', hash }`): HMAC with SHA-1, SHA-256, SHA-384 or SHA-512.
  - `extractable` (`boolean`): stored on the key; there is no `exportKey`.
  - `usages` (`('sign' | 'verify')[]`): stored on the key.
- **returns:** `Promise<CryptoKey>`, a frozen key object.
- **throws:** rejects with `TypeError: crypto.subtle.importKey supports 'raw' HMAC keys` for other formats or algorithms, and the hash error for a bad hash.

Example:

```ts
const key = await crypto.subtle.importKey(
  'raw',
  new TextEncoder().encode('my webhook secret'),
  { name: 'HMAC', hash: 'SHA-256' },
  false,
  ['sign', 'verify'],
)
```

### crypto.subtle.sign(algorithm, key, data)

```ts
sign(algorithm: 'HMAC' | { name: 'HMAC' }, key: CryptoKey, data: BufferSource): Promise<ArrayBuffer>
```

computes the HMAC of `data` with a key from `importKey`.

- **grant:** none.
- **parameters:**
  - `algorithm` (`'HMAC' | { name: 'HMAC' }`): always HMAC.
  - `key` (`CryptoKey`): a key from `crypto.subtle.importKey` in this script.
  - `data` (`BufferSource`): the message bytes.
- **returns:** `Promise<ArrayBuffer>` with the signature.
- **throws:** rejects with `TypeError: crypto.subtle.sign needs an HMAC key from importKey`.

Example:

```ts
const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(body))
const header = new Uint8Array(signature).toHex()
```

### crypto.subtle.verify(algorithm, key, signature, data)

```ts
verify(
  algorithm: 'HMAC' | { name: 'HMAC' },
  key: CryptoKey,
  signature: BufferSource,
  data: BufferSource,
): Promise<boolean>
```

checks an HMAC signature in constant time.

- **grant:** none.
- **parameters:**
  - `algorithm` (`'HMAC' | { name: 'HMAC' }`): always HMAC.
  - `key` (`CryptoKey`): a key from `importKey`.
  - `signature` (`BufferSource`): the signature to check.
  - `data` (`BufferSource`): the signed bytes.
- **returns:** `Promise<boolean>`.
- **throws:** rejects like `sign` for a foreign key.

Example:

```ts
const valid = await crypto.subtle.verify('HMAC', key, Uint8Array.fromHex(given), new TextEncoder().encode(body))
```

### type CryptoKey

```ts
interface CryptoKey {
  readonly type: 'secret'
  readonly extractable: boolean
  readonly algorithm: { name: 'HMAC', hash: { name: HashName } }
  readonly usages: readonly string[]
}
```

the frozen key object `crypto.subtle.importKey` resolves with.

- **grant:** none.
- **parameters:**
  - `type` (`'secret'`): always `secret`.
  - `extractable` (`boolean`): what you passed to `importKey`.
  - `algorithm` (`{ name: 'HMAC', hash: { name } }`): HMAC and the hash, uppercased.
  - `usages` (`readonly string[]`): what you passed to `importKey`.
- **notes:**
  - the key bytes live inside tele's runtime and can't be read back. only keys made by this script's `importKey` work with `sign` and `verify`.

Example:

```ts
console.log(key.algorithm.hash.name) // 'SHA-256'
```

### class TextEncoder

```ts
declare class TextEncoder {
  readonly encoding: 'utf-8'
  encode(input?: string): Uint8Array
}
```

turns strings into UTF-8 bytes.

- **grant:** none.
- **parameters:**
  - `encode(input?)`: `input` (`string`, default `''`), converted with `String()` first.
- **returns:** `encode` returns a new `Uint8Array`.
- **notes:**
  - `encoding` is always `utf-8`. there is no `encodeInto`.

Example:

```ts
const bytes = new TextEncoder().encode('привет')
console.log(bytes.length) // 12
```

### class TextDecoder

```ts
declare class TextDecoder {
  constructor(label?: string, options?: { fatal?: boolean })
  readonly encoding: 'utf-8'
  readonly fatal: boolean
  decode(input?: ArrayBuffer | ArrayBufferView): string
}
```

turns UTF-8 bytes into a string.

- **grant:** none.
- **parameters:**
  - `label` (`string`, optional): `'utf-8'` or `'utf8'` (any case); default `'utf-8'`.
  - `options.fatal` (`boolean`, optional): throw on invalid bytes instead of replacing them.
  - `decode(input?)`: `input` (`ArrayBuffer | ArrayBufferView`); missing gives `''`.
- **returns:** `decode` returns the string; invalid bytes become U+FFFD unless `fatal`.
- **throws:** `RangeError: TextDecoder only knows utf-8` for other labels; `TypeError: the data is not valid utf-8` from `decode` with `fatal`.
- **notes:**
  - no streaming (`{ stream: true }` is ignored).

Example:

```ts
const text = new TextDecoder().decode(await tg.downloadMedia(message))
```

### atob(data)

```ts
declare function atob(data: string): string
```

decodes a base64 string into a "binary string" (one char per byte).

- **grant:** none.
- **parameters:**
  - `data` (`string`): base64 text.
- **returns:** a string of chars 0 to 255.
- **throws:** a `DOMException` for invalid base64.
- **notes:**
  - for bytes, `Uint8Array.fromBase64` is simpler; for text with non-latin chars, decode the bytes with `TextDecoder`.

Example:

```ts
const [, payload] = jwt.split('.')
const claims = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
```

### btoa(data)

```ts
declare function btoa(data: string): string
```

encodes a "binary string" (chars 0 to 255) as base64.

- **grant:** none.
- **parameters:**
  - `data` (`string`): chars 0 to 255 only.
- **returns:** the base64 string.
- **throws:** a `DOMException` for chars above 255.
- **notes:**
  - for any text, use `new TextEncoder().encode(text).toBase64()`.

Example:

```ts
const auth = 'Basic ' + btoa('user:password')
```

### Uint8Array base64 and hex

```ts
interface Uint8Array {
  toBase64(options?: {
    alphabet?: 'base64' | 'base64url'
    omitPadding?: boolean
  }): string
  toHex(): string
}

interface Uint8ArrayConstructor {
  fromBase64(
    string: string,
    options?: {
      alphabet?: 'base64' | 'base64url'
      lastChunkHandling?: 'loose' | 'strict' | 'stop-before-partial'
    },
  ): Uint8Array
  fromHex(string: string): Uint8Array
}
```

the standard byte helpers, built into the engine and declared in `tele.d.ts` because typescript's own libs don't have them yet.

- **grant:** none.
- **parameters:**
  - `toBase64(options?)`: `alphabet` (default `'base64'`), `omitPadding` (default `false`).
  - `toHex()`: lowercase hex.
  - `Uint8Array.fromBase64(string, options?)`: `alphabet`, `lastChunkHandling` (default `'loose'`).
  - `Uint8Array.fromHex(string)`: an even-length hex string.
- **returns:** a string, or a new `Uint8Array`.
- **throws:** `SyntaxError` for invalid base64 or hex input.

Example:

```ts
const id = crypto.getRandomValues(new Uint8Array(8))
tg.storage.set('id', id.toBase64({ alphabet: 'base64url', omitPadding: true }))
const back = Uint8Array.fromHex(id.toHex())
```

### performance.now()

```ts
declare var performance: { now(): number }
```

milliseconds since the script's engine was created, with sub-millisecond precision, for measuring durations.

- **grant:** none.
- **returns:** a `number` of milliseconds.
- **notes:**
  - not tied to the wall clock; use `Date.now()` for timestamps. `performance.timeOrigin` also exists (the engine's start in ms since the epoch) though the typings don't list it.

Example:

```ts
const start = performance.now()
const dialogs = await tg.getDialogs({ limit: 100 })
console.log(`loaded ${dialogs.length} dialogs in ${Math.round(performance.now() - start)} ms`)
```

### queueMicrotask(callback)

```ts
declare function queueMicrotask(callback: () => void): void
```

runs `callback` as a microtask, right after the current code and before any timer.

- **grant:** none.
- **parameters:**
  - `callback` (`() => void`): the function to run.
- **returns:** `undefined`.
- **notes:**
  - microtasks run in the promise-job drain after each call into the script (1 s and 100000 jobs in total).

Example:

```ts
queueMicrotask(() => console.log('second'))
console.log('first')
```

### defineScript (global)

```ts
declare function defineScript<T extends import('tele').ScriptDefinition>(
  definition: T,
): T
```

the global copy of `defineScript`, for scripts that don't import from `'tele'`. it behaves exactly like the imported one; see [defineScript(definition)](#definescriptdefinition).

- **grant:** none.
- **parameters:**
  - `definition` (`ScriptDefinition`): the script.
- **returns:** the same object.
- **throws:** the same `TypeError`s as the imported one.

Example:

```js
// scripts/plain.js
export default defineScript({
  name: 'plain js',
  setup(tg) {
    console.log('no imports needed', tg.selfId)
  },
})
```

### class TeleError

```ts
declare class TeleError extends Error {
  constructor(code: TeleErrorCode, message: string, grant?: string)
  readonly name: 'TeleError'
  readonly code: TeleErrorCode
  readonly grant?: string
}
```

the error tele throws for its own conditions: missing grants, blocked methods, things not found, timeouts. a global class, so `error instanceof TeleError` works.

- **grant:** none.
- **parameters:**
  - `code` (`TeleErrorCode`): what happened; see [type TeleErrorCode](#type-teleerrorcode).
  - `message` (`string`): a readable explanation.
  - `grant` (`string`, optional): with `not-granted`, the exact grant string to add to `grants`.
- **notes:**
  - `name` is always `'TeleError'`; `grant` is only present when given.
  - scripts may construct and throw their own, for example from a `tg.scripts.expose` handler.

Example:

```ts
try {
  tg.clipboard.read()
} catch (error) {
  if (error instanceof TeleError && error.code === 'not-granted') {
    console.warn(`add '${error.grant}' to grants`) // add 'clipboard.read' to grants
  }
}
```

### class RpcError

```ts
declare class RpcError extends Error {
  constructor(code: number, type: string)
  readonly name: 'RpcError'
  readonly code: number
  readonly type: string
  readonly seconds?: number
}
```

a telegram api error: what `tg.call` rejects with when the server says no, and what an `interceptRpc` middleware returns or throws to answer tele with an error. a global class.

- **grant:** none.
- **parameters:**
  - `code` (`number`): the error code (400, 403, 420...; 0 for a result tele couldn't decode).
  - `type` (`string`): the error string, also the `message`.
  - `seconds` (`number`, optional): parsed from `FLOOD_WAIT_X`, `FLOOD_PREMIUM_WAIT_X` and `SLOWMODE_WAIT_X`.
- **notes:**
  - `name` is always `'RpcError'`; `message === type`.

Example:

```ts
tg.interceptRpc('messages.sendMessage', ({ request }, next) => {
  if (request.message.includes('password')) return new RpcError(400, 'MESSAGE_BLOCKED_BY_SCRIPT')
  return next()
})
```

## talking to telegram

everything a script does with telegram goes through `tg`, the object `setup(tg)` gets. there is one `tg` per script per logged-in account, and nothing is shared between them. this section is the raw layer: any api method, any update, and middleware around tele's own traffic. the friendlier helpers in the next sections are built on top of it and follow the same rules.

### type Tg

```ts
export interface Tg {
  readonly selfId: bigint
  readonly scriptName: string
  readonly storage: Storage
  readonly peers: PeerCache
  toast(text: string, options?: ToastOptions): void
  readonly ui: Ui
  notify(title: string, text: string): void
  openUrl(link: string): void
  readonly clipboard: {
    read(): string
    write(text: string): void
  }
  randomId(): bigint
  readonly Message: typeof Message
  resolvePeer(peer: InputPeerLike): Promise<tl.TypeInputPeer>
  resolveUser(peer: InputPeerLike): Promise<tl.TypeInputUser>
  resolveChannel(peer: InputPeerLike): Promise<tl.TypeInputChannel>
  getMe(): Promise<tl.TypeUser>
  getUser(peer: InputPeerLike): Promise<tl.RawUser | null>
  getChat(peer: InputPeerLike): Promise<tl.TypeChat | null>
  getFullUser(peer: InputPeerLike): Promise<tl.users.TypeUserFull>
  getFullChat(peer: InputPeerLike): Promise<tl.messages.TypeChatFull>
  getMessages(peer: InputPeerLike, id: number): Promise<Message | null>
  getMessages(peer: InputPeerLike, ids: number[]): Promise<(Message | null)[]>
  getHistory(peer: InputPeerLike, options?: HistoryOptions): Promise<Message[]>
  iterHistory(
    peer: InputPeerLike,
    options?: HistoryOptions & { batchSize?: number },
  ): AsyncGenerator<Message, void, undefined>
  getDialogs(options?: DialogOptions): Promise<Dialog[]>
  iterDialogs(
    options?: DialogOptions & { batchSize?: number },
  ): AsyncGenerator<Dialog, void, undefined>
  sendMessage(
    peer: InputPeerLike,
    text: InputText,
    options?: SendOptions & { noWebpage?: boolean },
  ): Promise<Message>
  sendMedia(
    peer: InputPeerLike,
    media: tl.TypeInputMedia,
    options?: SendOptions & { caption?: InputText },
  ): Promise<Message>
  editMessage(
    peer: InputPeerLike,
    id: number,
    text: InputText | null,
    options?: EditOptions,
  ): Promise<Message>
  deleteMessages(
    peer: InputPeerLike,
    ids: number | number[],
    options?: { revoke?: boolean },
  ): Promise<void>
  forwardMessages(
    from: InputPeerLike,
    ids: number | number[],
    to: InputPeerLike,
    options?: ForwardOptions,
  ): Promise<Message[]>
  setReaction(
    peer: InputPeerLike,
    id: number,
    reactions: Reaction | Reaction[] | null,
    options?: { big?: boolean, addToRecent?: boolean },
  ): Promise<void>
  readHistory(peer: InputPeerLike, options?: { maxId?: number }): Promise<void>
  sendTyping(
    peer: InputPeerLike,
    action?: TypingAction,
    options?: { topicId?: number },
  ): Promise<void>
  setDraft(
    peer: InputPeerLike,
    text: InputText | null,
    options?: { replyTo?: number, topicId?: number, noWebpage?: boolean },
  ): Promise<void>
  downloadMedia(
    target: Message | tl.TypeMessageMedia | tl.TypePhoto | tl.TypeDocument,
  ): Promise<Uint8Array>
  downloadMedia(
    target: Message | tl.TypeMessageMedia | tl.TypePhoto | tl.TypeDocument,
    options: { saveTo: 'downloads' | string },
  ): Promise<string>
  uploadFile(
    data: Uint8Array | string,
    options?: { fileName?: string },
  ): Promise<tl.TypeInputFile>
  sendFile(
    peer: InputPeerLike,
    data: Uint8Array | string,
    options?: SendOptions & {
      fileName?: string
      mimeType?: string
      asPhoto?: boolean
      forceDocument?: boolean
      caption?: InputText
    },
  ): Promise<Message>
  interceptSendMessage(middleware: SendMiddleware): Disposer
  interceptSendMessage(filter: SendFilter, middleware: SendMiddleware): Disposer
  addLocalMessage(chat: InputPeerLike, options?: LocalMessageOptions): Promise<LocalMessage>
  localMessages(): LocalMessage[]
  overridePeer(peer: InputPeerLike, override: PeerOverride | null): Promise<Disposer>
  registerCommand(options: CommandOptions): Disposer
  registerSettings(page: Page): Disposer
  registerMessageAction(options: ActionOptions<MessageActionContext>): Disposer
  registerChatAction(
    options: ActionOptions<ActionContext> & {
      placements?: ('chat' | 'chatRow')[]
    },
  ): Disposer
  registerProfileAction(options: ActionOptions<ActionContext>): Disposer
  onNewMessage(callback: (message: Message) => unknown): Disposer
  onMessageEdited(
    callback: (message: Message, previous: Message | null) => unknown,
  ): Disposer
  decorateMessages(
    decorator: (
      message: Message,
    ) => MessageDecoration | null | void | Promise<MessageDecoration | null | void>,
  ): Disposer
  decorateMessage(
    peer: InputPeerLike,
    id: number,
    decoration: MessageDecoration | null,
  ): Promise<Disposer>
  getCachedMessage(peer: InputPeerLike, id: number): Promise<Message | null>
  readonly compose: Compose
  readonly local: Local
  readonly options: Options
  readonly scripts: Scripts
  readonly app: App
  readonly calls: Calls
  readonly accounts: { list(): AccountInfo[], switchTo(id: bigint): boolean }
  readonly unsafe: Unsafe
  readonly tele: TeleFeatures
  registerQuickAction(options: {
    emoji: string
    tooltip?: string
    chats?: 'all' | 'private' | 'groups' | 'channels'
    onClick(context: { chatId: bigint, messageId: number }): unknown
  }): Disposer
  interceptDrop(interceptor: (drop: DropInfo) => DropVerdict | void | Promise<DropVerdict | void>): Disposer
  connection(): ConnectionInfo
  onConnectionChange(callback: (connection: ConnectionInfo) => unknown): Disposer
  onWake(callback: (wake: { sleptFor: number }) => unknown): Disposer
  schedule(when: Schedule, callback: (firedAt: Date) => unknown): Disposer
  registerShortcut(keys: string, callback: () => unknown): Disposer
  registerButton(options: {
    place?: 'header' | 'compose'
    icon: string
    tooltip?: string
    chats?: CommandChats | CommandChats[]
    onClick(context: ActionContext): unknown
  }): Disposer
  registerProfileRow(options: {
    label: string
    value(peer: PeerInfo): string | null | void | Promise<string | null | void>
    onClick?(peer: PeerInfo): unknown
  }): Disposer
  interceptLink(interceptor: LinkInterceptor): Disposer
  interceptLink(pattern: RegExp, interceptor: LinkInterceptor): Disposer
  interceptNotification(
    interceptor: (
      notification: NotificationInfo,
    ) => NotificationVerdict | null | void | Promise<NotificationVerdict | null | void>,
  ): Disposer
  onMessageDeleted(callback: (deleted: DeletedMessages) => unknown): Disposer
  call<R extends tl.AnyRequest>(request: R, options?: { dc?: number, download?: boolean }): Promise<tl.RpcResult<R['_']>>
  onUpdate<N extends tl.UpdateName>(
    type: N | N[],
    listener: Listener<N>,
  ): Disposer
  onUpdate(type: '*', listener: AnyListener): Disposer
  interceptRpc<N extends tl.RpcMethod>(
    method: N | N[],
    middleware: RpcMiddleware<N>,
  ): Disposer
  interceptRpc(
    method: '*' | `${string}.*` | ('*' | `${string}.*`)[],
    middleware: RpcMiddleware<tl.RpcMethod>,
  ): Disposer
  interceptUpdate<N extends tl.UpdateName>(
    type: N | N[],
    middleware: UpdateMiddleware<tl.UpdateOf<N>>,
  ): Disposer
  interceptUpdate(
    type: '*',
    middleware: UpdateMiddleware<tl.AnyUpdate>,
  ): Disposer
  onUnload(callback: () => void): Disposer
}
```

the object passed to `setup`. it lives as long as the script runs on that account; after the script stops, every call on it throws `InternalError: the script was stopped`.

- **grant:** none for the object itself; each member names its own grant.
- **notes:**
  - members documented in this part: `selfId`, `scriptName`, `randomId`, `call`, `onUpdate`, `interceptRpc`, `interceptUpdate`, `onUnload`, `onNewMessage`, `onMessageEdited`, `onMessageDeleted` (talking to telegram); `Message`, `resolvePeer`, `resolveUser`, `resolveChannel`, `getMe`, `getUser`, `getChat`, `getFullUser`, `getFullChat`, `getMessages`, `getHistory`, `iterHistory`, `getDialogs`, `iterDialogs`, `sendMessage`, `sendMedia`, `editMessage`, `deleteMessages`, `forwardMessages`, `setReaction`, `readHistory`, `sendTyping`, `setDraft`, `getCachedMessage` (messages); `peers`, `overridePeer` (peers); `storage` (storage); `downloadMedia`, `uploadFile`, `sendFile` (files); `interceptSendMessage` (sending); `addLocalMessage`, `localMessages`, `decorateMessages`, `decorateMessage` (local messages and decorations); `local`, `options`, `tele` (local data and settings); `scripts` (script to script); `connection`, `onConnectionChange`, `onWake`, `schedule` (connection, wake and schedules).
  - the ui, app and platform members (`toast`, `notify`, `openUrl`, `clipboard`, `ui`, `compose`, `app`, `calls`, `accounts`, `unsafe`, the `register*` and `intercept*` surfaces for links, notifications and drops) are documented in their own sections.
  - high-level members are defined as non-writable properties, so a script can't replace `tg.sendMessage` for other code by accident.

Example:

```ts
import { defineScript, type Tg } from 'tele'

async function hello(tg: Tg) {
  const me = await tg.getMe()
  console.log(`${tg.scriptName} runs as ${tg.selfId}`, me)
}

export default defineScript({
  name: 'hello',
  grants: ['account.read(self)'],
  setup: hello,
})
```

### tg.call(request, options?)

```ts
call<R extends tl.AnyRequest>(
  request: R,
  options?: { dc?: number, download?: boolean },
): Promise<tl.RpcResult<R['_']>>
```

sends any telegram api method as this account and resolves with the decoded result. the request is a plain object whose `_` is the method name; fields follow the tl mapping below.

- **grant:** `call(<method>)`, a glob like `call(messages.*)`, or bare `call`. methods behind the high-level helpers are also covered by their `account.*` grant: `account.read(self)` or `account.read(peers)` covers `users.getUsers` and `users.getFullUser`; `account.read(peers)` covers `contacts.resolveUsername`, `channels.getChannels`, `channels.getFullChannel`, `messages.getChats`, `messages.getFullChat`; `account.read(messages)` covers `messages.getMessages`, `channels.getMessages`; `account.read(history)` covers `messages.getHistory`, `messages.search`, `messages.getReplies`; `account.read(dialogs)` covers `messages.getDialogs`, `messages.getPeerDialogs`, `messages.getPinnedDialogs`; `account.write(send)` covers `messages.sendMessage`, `messages.sendMedia`, `messages.sendMultiMedia`; `account.write(edit)` covers `messages.editMessage`; `account.write(delete)` covers `messages.deleteMessages`, `channels.deleteMessages`; `account.write(forward)` covers `messages.forwardMessages`; `account.write(react)` covers `messages.sendReaction`; `account.write(read)` covers `messages.readHistory`, `channels.readHistory`; `account.write(typing)` covers `messages.setTyping`; `account.write(draft)` covers `messages.saveDraft`.
- **parameters:**
  - `request` (`tl.AnyRequest`): `{ _: '<method>', ...fields }`, e.g. `{ _: 'users.getUsers', id: [{ _: 'inputUserSelf' }] }`. encoded synchronously against tele's own schema (the same layer tele speaks).
  - `options.dc` (`number`, optional): a data center id from 1 to 999. sends the request to that dc instead of the account's main one; tdesktop exports the authorization there when needed. default: the main dc.
  - `options.download` (`boolean`, optional): only with `dc`. uses tdesktop's download connection to that dc, the one meant for `upload.getFile` and friends. default `false`.
- **returns:** a promise of the method's result type, decoded: objects as `{ _, ...fields }`, `Vector<int>` as `number[]`, `Vector<User>` as an array, `Bool` as `boolean`.
- **throws:**
  - `TypeError` synchronously (inside an `async` function that becomes a rejection) for a request that doesn't encode, with a dotted path: `a request needs a _ with the method name`, `<x> is not a method in the schema`, `messages.sendMessage.peer: is required`, `users.getUsers.id[0]: inputPeerSelf is a InputPeer, not a InputUser`, and the rest under "tl: encoding errors". also `tg.call needs a request object` and `tg.call: dc is a data center id`.
  - `TeleError` `forbidden` for methods that can take over the account (everything `auth.*`, passkeys, `account.registerDevice` / `unregisterDevice`, `account.deleteAccount`, `account.changePhone`, `account.getAuthorizations`, `account.resetAuthorization`, `account.acceptAuthorization`, `account.verifyPhone`, `account.verifyEmail`, `account.resetPassword`, `account.updatePasswordSettings`, `messages.requestUrlAuth`, `messages.acceptUrlAuth`), whatever the grants say: `tg.call(<method>) can take over the account, it needs the grant 'unsafe.disableApiFiltering'`.
  - `TeleError` `not-granted` with `grant` set to the exact token to add: `tg.call(users.getUsers) needs the grant 'account.read(peers)'`. dangerous methods (anything with `.delete` or `leave` in the name, `*TTL` setters, payments, gift transfers and the rest of tele's console list) are only covered by their exact name, e.g. `call(messages.deleteMessages)`; `call`, `call(messages.*)` never cover them.
  - rejects with `RpcError` for a server error: `code` is the number (400, 420…), `type` and `message` the error string (`USERNAME_NOT_OCCUPIED`, `FLOOD_WAIT_17`). `FLOOD_WAIT_X`, `FLOOD_PREMIUM_WAIT_X` and `SLOWMODE_WAIT_X` also set `seconds`.
  - rejects with `RpcError` `code: 0` and `can't read the result: ...` when the answer doesn't decode.
  - `InternalError: the script was stopped` after the script stopped.
- **notes:**
  - flood waits up to 10 s are slept through and the same bytes are sent again (the promise just takes longer); longer ones reject at once with the `RpcError`. tdesktop still retries transport errors, 5xx and dc migrations by itself.
  - when the result is an `Updates` (or `payments.paymentResult`), tele applies it like its own results: a message sent with `tg.call` shows up in the chat. for private-chat sends answered with `updateShortSentMessage`, tele expands the answer with your request so the message is drawn.
  - every `User` and `Chat` anywhere in the result is fed into tele's cache, so `tg.peers` and tele's ui know them afterwards.
  - results go through the sensitive-data filter: digit runs of 5+ in messages from or to 777000 (login codes) become `*****`, `config.autologinToken` is dropped, and draft texts come empty without `account.read(draft)`. `unsafe.disableApiFiltering` lifts all of it.
  - script requests skip every script's `interceptRpc` and `interceptUpdate` (so a script can't deadlock on its own traffic), but update listeners (`onUpdate`, `onNewMessage`, `onMessageEdited`, `onMessageDeleted`) do see their results, the caller's own included: a listener that sends on every new message must skip its own (`message.out`, or remember the ids it sent).
  - calls run in parallel; each promise settles on its own. `then` callbacks of a settling call have 200 ms, plus the 1 s promise-job drain.
  - when the script stops, requests still in flight are cancelled and their promises never settle.

Example:

```ts
const [me] = await tg.call({ _: 'users.getUsers', id: [{ _: 'inputUserSelf' }] })

try {
  await tg.call({ _: 'contacts.resolveUsername', username: 'surely_nobody_here_42' })
} catch (error) {
  if (error instanceof RpcError && error.type === 'USERNAME_NOT_OCCUPIED') {
    console.log('free name')
  } else {
    throw error
  }
}

const part = await tg.call(
  { _: 'upload.getFile', location, offset: 0n, limit: 512 * 1024 },
  { dc: 4, download: true },
)
```

### tl: objects and _

```ts
interface TlObject {
  _: string
}
```

every tl object is a plain js object whose `_` is the constructor name exactly as in the schema; requests use the method name.

- **notes:**
  - namespaced names keep the namespace: `'message'`, `'messages.messagesSlice'`, `'inputPeerSelf'`, `'rpc_error'`, and for requests `'messages.sendMessage'`.
  - a boxed field (`Message`, `InputPeer`…) holds an object whose `_` is one of that type's constructors; the typings name the constructor `tl.RawMessage`, the union `tl.TypeMessage`, the request `tl.messages.RawSendMessageRequest`.
  - server errors inside results are decoded as generic objects `{ _: 'rpc_error', errorCode, errorMessage }`; `tg.call` turns them into an `RpcError` rejection.

Example:

```ts
const peer: tl.TypeInputPeer = { _: 'inputPeerSelf' }
const media: tl.TypeInputMedia = { _: 'inputMediaDice', emoticon: '🎲' }
```

### tl: field names

```ts
// schema: message#... flags:# out:flags.1?true id:int peer_id:Peer ...
interface RawMessage {
  _: 'message'
  out?: boolean
  id: number
  peerId: tl.TypePeer
}
```

field names are camelCase versions of the schema's snake_case names.

- **notes:**
  - each `_` followed by a lowercase letter becomes that letter uppercased, any other `_` is dropped: `peer_id` -> `peerId`, `srp_B` -> `srpB`, `default_p2p_contacts` -> `defaultP2pContacts`, `ttl_period` -> `ttlPeriod`.
  - encoding looks fields up by the same camelCase name, so snake_case keys in a request are silently ignored, and so is any other extra key.
  - a misspelled required field shows up as `<real name>: is required`; a misspelled optional one is just not sent.

Example:

```ts
await tg.call({ _: 'messages.getHistory', peer: { _: 'inputPeerSelf' }, offsetId: 0, offsetDate: 0, addOffset: 0, limit: 20, maxId: 0, minId: 0, hash: 0n })
```

### tl: flags and optional fields

```ts
interface RawMessage {
  out?: boolean          // flags.1?true
  editDate?: number      // flags.15?int
}
```

`#` fields (`flags`, `flags2`) never appear in decoded objects and are ignored on input: tele computes them from which fields are present.

- **notes:**
  - `flags.N?true` fields always come back, as `true` or `false`. when sending, any truthy value sets the bit (`1` and `'x'` count too); a missing or falsy one clears it.
  - other `flags.N?T` fields are present only when the bit is set. when sending, a value that isn't `undefined` or `null` sets the bit and is written; `undefined` or `null` leaves it out.
  - required fields need a value that isn't `undefined` or `null`, else `<path>: is required`.

Example:

```ts
await tg.call({
  _: 'messages.sendMessage',
  peer: { _: 'inputPeerSelf' },
  message: 'quiet',
  randomId: tg.randomId(),
  silent: true,
  scheduleDate: undefined,
})
```

### tl: numbers, long and bigint

```ts
interface RawUser {
  id: bigint          // long
  accessHash?: bigint // flags.0?long
}
interface RawMessage {
  id: number          // int
}
```

`int` is a js `number`, `long` is always a `bigint` when decoded, `double` is a `number`.

- **notes:**
  - `int` decodes as a signed 32-bit `number`. encoding takes an integer `number` from -2147483648 to 4294967295 (unsigned values wrap) or a `bigint` in the int32 range; errors: `expected a number`, `expected a 32-bit integer`, `doesn't fit an int`.
  - `long` decodes as a signed 64-bit `bigint`, so big unsigned values come out negative. encoding takes a `bigint` (truncated to 64 bits) or an integer `number` with abs <= 2^53-1; error: `expected a bigint`. the typings say `bigint` only.
  - `double` takes a `number` (`expected a number`).
  - compare ids as bigints (`user.id === tg.selfId`), never through `Number`. `JSON.stringify` throws on bigints: pass a replacer.

Example:

```ts
const ids = await tg.call({ _: 'contacts.getContactIDs', hash: 0n })
console.log(ids.length, typeof ids[0])
```

### tl: strings and bytes

```ts
interface RawPhotoStrippedSize {
  _: 'photoStrippedSize'
  type: string
  bytes: Uint8Array
}
```

`string` is a js string (utf-8 on the wire); `bytes`, `int128` and `int256` are `Uint8Array`s.

- **notes:**
  - `bytes` decodes to a fresh copy. encoding takes a `Uint8Array`, or a `string` that is written as utf-8; error `expected a Uint8Array`.
  - `int128` / `int256` need a `Uint8Array` of exactly 16 / 32 bytes (`expected 16 bytes` / `expected 32 bytes`).
  - `string` needs a js string (`expected a string`).

Example:

```ts
const hex = size.bytes.toHex()
```

### tl: Bool and true

```ts
// help.saveAppLog returns Bool
const ok: boolean = await tg.call({ _: 'help.saveAppLog', events: [] })
```

`Bool` is a js `boolean` both ways.

- **notes:**
  - decoding reads `boolTrue` / `boolFalse`; anything else fails with `expected Bool`.
  - encoding needs a real `boolean`; `1` or `'yes'` fail with `expected a boolean`.
  - `flags.N?true` fields are not `Bool`: see "tl: flags and optional fields".

Example:

```ts
await tg.call({ _: 'account.updateStatus', offline: false })
```

### tl: vectors

```ts
interface RawUsersGetUsersRequest {
  _: 'users.getUsers'
  id: tl.TypeInputUser[]
}
```

`Vector<T>` and bare `vector<T>` are js arrays.

- **notes:**
  - encoding needs a real js array; typed arrays and other iterables don't count (`expected an array`, `bad array`).
  - a vector count larger than the remaining bytes fails decoding with `bad vector size N`.

Example:

```ts
const users = await tg.call({ _: 'users.getUsers', id: [{ _: 'inputUserSelf' }] })
```

### tl: generic objects and !X

```ts
interface RawInvokeWithoutUpdatesRequest {
  _: 'invokeWithoutUpdates'
  query: tl.TlObject
}
```

fields typed `Object` or `!X` take any constructor, or a method object, so wrappers like `invokeWithoutUpdates.query` work.

- **notes:**
  - a bare type (`%T`, or a lowercase type name in the schema) is written without its constructor id and without the type check; it still needs an object with `_` (`expected an object with _ (T)`).
  - generic results are typed `unknown`.

Example:

```ts
await tg.call({
  _: 'invokeWithoutUpdates',
  query: { _: 'messages.setTyping', peer: { _: 'inputPeerSelf' }, action: { _: 'sendMessageTypingAction' } },
})
```

### tl: encoding errors

```ts
// TypeError: users.getUsers.id[0]: inputPeerSelf is a InputPeer, not a InputUser
tg.call({ _: 'users.getUsers', id: [{ _: 'inputPeerSelf' }] })
```

everything that turns js into tl (`tg.call`, `next(request)`, middleware answers, local messages, entities) reports problems as a `TypeError` whose message starts with a path: the method or constructor, then `.field` and `[index]` steps.

- **notes:**
  - the full list after the path: `is required`, `expected a number`, `expected a 32-bit integer`, `doesn't fit an int`, `expected a bigint`, `expected a string`, `expected a Uint8Array`, `expected 16 bytes`, `expected 32 bytes`, `expected a boolean`, `expected an array`, `bad array`, `expected an object with _ (T)`, `<name> is not in the schema`, `<name> is a <Other>, not a <T>`, `nested too deep` (more than 64 levels).
  - request-level: `a request needs a _ with the method name` (no or empty `_`), `<x> is not a method in the schema`.
  - example paths: `help.saveAppLog.events[0].type: expected a string`, `messages.sendMessage.randomId: is required`.

Example:

```ts
try {
  await tg.call({ _: 'messages.sendMessage', peer: { _: 'inputPeerSelf' }, message: 'x' } as never)
} catch (error) {
  console.log(String(error))
}
```

### tl: decoding and results

```ts
const result = await tg.call({ _: 'messages.getDialogs', offsetDate: 0, offsetId: 0, offsetPeer: { _: 'inputPeerEmpty' }, limit: 10, hash: 0n })
if (result._ === 'messages.dialogsSlice') {
  console.log(result.count)
}
```

results are decoded with the method's declared result type, so unions come back as one concrete constructor: switch on `_`.

- **notes:**
  - an unknown constructor id fails with `unknown constructor 0x...`; nesting deeper than 64 fails with `nested too deep`; errors carry the path and byte offset (`messages.messages.messages: ... at byte 1234`).
  - inside interceptors and listeners a decode failure is only logged as a warning (`can't read <method>: ...`, `can't read updates: ...`); the bytes pass to tele untouched and nothing reaches the script.
  - decoding and re-encoding an unchanged value gives the same bytes; that's how tele notices an interceptor changed nothing and passes the original through.

Example:

```ts
const history = await tg.call({ _: 'messages.getHistory', peer: { _: 'inputPeerSelf' }, offsetId: 0, offsetDate: 0, addOffset: 0, limit: 5, maxId: 0, minId: 0, hash: 0n })
if (history._ !== 'messages.messagesNotModified') {
  for (const message of history.messages) {
    if (message._ === 'message') console.log(message.id, message.message)
  }
}
```

### namespace tl

```ts
declare namespace tl {
  interface TlObject { _: string }
  type RpcMethod = keyof RpcMethods
  type AnyRequest = RpcMethods[RpcMethod]['request']
  type RpcResult<N extends RpcMethod> = RpcMethods[N]['result']
  type AnyUpdate =
    | tl.TypeUpdate
    | tl.RawUpdateShortMessage
    | tl.RawUpdateShortChatMessage
    | tl.RawUpdateShortSentMessage
  type UpdateName = AnyUpdate['_']
  type UpdateOf<N extends UpdateName> = Extract<AnyUpdate, { _: N }>
  interface RpcMethods { /* 'method.name': { request, result } */ }
}
```

the generated `tele.d.ts` (written into the scripts folder, regenerated when tele's schema changes) has one interface per constructor, per method and a union per type, plus these helpers.

- **fields:**
  - `TlObject` (`{ _: string }`): any tl object.
  - `RpcMethods` (interface): method name -> `{ request; result }`.
  - `RpcMethod` (`string` union): every method name.
  - `AnyRequest` (union): every request interface.
  - `RpcResult<N>`: the result type of method `N`.
  - `AnyUpdate` (union): every `Update` constructor plus the three short updates listeners can get.
  - `UpdateName` (`string` union): every name `onUpdate` and `interceptUpdate` accept.
  - `UpdateOf<N>`: the update interface for name `N`.
- **notes:**
  - naming is mtcute-style: `tl.RawMessage` (constructor), `tl.TypeMessage` (union), `tl.messages.RawSendMessageRequest` (method), `tl.RawRpcError`.
  - the typings are stricter than the runtime in two places: `long` fields are `bigint` only, `int` fields are `number` (fractions fail only at runtime).

Example:

```ts
function isText(update: tl.UpdateOf<'updateNewMessage'>): boolean {
  return update.message._ === 'message' && update.message.message.length > 0
}
```

### tg.onUpdate(type, listener)

```ts
onUpdate<N extends tl.UpdateName>(
  type: N | N[],
  listener: Listener<N>,
): Disposer
onUpdate(type: '*', listener: AnyListener): Disposer
```

calls `listener(update, peers)` for every update of those types tele receives, after every script's `interceptUpdate` ran and right before tele applies it.

- **grant:** `onUpdate(<name>)` for each name (or bare `onUpdate`); `'*'` needs bare `onUpdate`.
- **parameters:**
  - `type` (`tl.UpdateName | tl.UpdateName[] | '*'`): one `Update` constructor name (`'updateNewMessage'`, `'updateShortMessage'`…), an array of them, or `'*'` for all.
  - `listener` (`Listener<N>` / `AnyListener`): gets the update and the `Peers` that came with it. its return value is ignored; a returned promise isn't awaited.
- **returns:** a `Disposer` that removes the listener.
- **throws:**
  - `TypeError`: `tg.onUpdate(name or names, function)`, `tg.onUpdate takes names as strings`, `tg.onUpdate needs at least one name`, `tg.onUpdate: <x> is not an update`.
  - `TeleError` `not-granted`: `tg.onUpdate('updateDeleteMessages') needs the grant 'onUpdate(updateDeleteMessages)'`.
- **notes:**
  - what arrives: pushed updates, `updates.getDifference` / `getChannelDifference` results, and the `Updates` returned by tele's own requests and by script `tg.call`s (the latter two only for requests that left while a listener existed).
  - containers are unwrapped: each inner update of `updates`, `updatesCombined` and differences is delivered on its own with `peers` from the container. `updateShort` delivers the inner update with empty peers. `updateShortMessage`, `updateShortChatMessage` and `updateShortSentMessage` come as they are (their `_` is the short type), with empty peers.
  - difference `newMessages` arrive as synthesized `{ _: 'updateNewMessage' | 'updateNewChannelMessage', message, pts: 0, ptsCount: 0 }`; `pts: 0` marks them. deletions made in this tele (the delete menu, `tg.deleteMessages`) arrive as synthesized `updateDeleteMessages` / `updateDeleteChannelMessages` with `pts: 0` right before tele removes the messages.
  - never delivered: `updatesTooLong`, the contents of `differenceTooLong` / `channelDifferenceTooLong`, and `updateServiceNotification` (unless `unsafe.disableApiFiltering`, even with `'*'`).
  - tele doesn't catch up at start: it calls `updates.getState` and reloads the chat list, so whatever happened while tele was closed never reaches listeners. fetch history in `setup` if you must not miss anything.
  - order: registration order across all names, so a `'*'` listener registered first runs first. registering inside a listener is fine; the running dispatch uses the list as it was.
  - each call has a 200 ms budget, then 1 s for the promise jobs it started. a throw or timeout is a fault (logged, toasted, counted toward the 5-in-a-row switch-off).

Example:

```ts
tg.onUpdate(['updateNewMessage', 'updateShortMessage'], (update, peers) => {
  if (update._ === 'updateNewMessage' && update.message._ === 'message') {
    const author = peers.users.find((user) => user._ === 'user')
    console.log(update.message.message, author)
  }
})
```

### type Listener

```ts
export type Listener<N extends tl.UpdateName = tl.UpdateName> = (
  update: tl.UpdateOf<N>,
  peers: Peers,
) => unknown
```

the callback of `tg.onUpdate` for named updates; with an array of names `update` is the union of those update types.

- **fields:**
  - `update` (`tl.UpdateOf<N>`): the decoded update, after interceptors changed it.
  - `peers` (`Peers`): users and chats that came in the same container.
  - return (`unknown`): ignored.

Example:

```ts
const onEdit: Listener<'updateEditMessage'> = (update) => console.log(update.message)
tg.onUpdate('updateEditMessage', onEdit)
```

### type AnyListener

```ts
export type AnyListener = (update: tl.AnyUpdate, peers: Peers) => unknown
```

the callback of `tg.onUpdate('*', ...)`.

- **fields:**
  - `update` (`tl.AnyUpdate`): any update; switch on `update._`.
  - `peers` (`Peers`): users and chats from the same container.
  - return (`unknown`): ignored.

Example:

```ts
tg.onUpdate('*', (update) => console.log(update._))
```

### type Peers

```ts
export interface Peers {
  users: tl.TypeUser[]
  chats: tl.TypeChat[]
}
```

users and chats that arrived next to an update; empty for short updates and `updateShort`.

- **fields:**
  - `users` (`tl.TypeUser[]`): the container's `users`.
  - `chats` (`tl.TypeChat[]`): the container's `chats`.

Example:

```ts
tg.onUpdate('updateNewChannelMessage', (update, peers) => {
  const channel = peers.chats.find((chat) => chat._ === 'channel')
  console.log(channel?._ === 'channel' ? channel.title : 'unknown')
})
```

### tg.interceptRpc(method, middleware)

```ts
interceptRpc<N extends tl.RpcMethod>(
  method: N | N[],
  middleware: RpcMiddleware<N>,
): Disposer
interceptRpc(
  method: '*' | `${string}.*` | ('*' | `${string}.*`)[],
  middleware: RpcMiddleware<tl.RpcMethod>,
): Disposer
```

koa-style async middleware around the requests tele itself sends: read or edit the request, call `next()` for the server's answer, change the answer, or answer yourself without contacting the server.

- **grant:** `interceptRpc(<method>)`, a glob covering it (`interceptRpc(messages.*)`), or bare `interceptRpc`. `'*'` needs bare `interceptRpc`; a prefix pattern needs that glob or bare. dangerous methods need their exact name; takeover methods need `unsafe.disableApiFiltering`.
- **parameters:**
  - `method` (`string | string[]`): schema method names, `'*'` for every method, or a prefix ending in `*` (`'messages.*'`, `'messages.send*'`), or an array mixing them. patterns only catch methods the grants allow.
  - `middleware` (`RpcMiddleware<N>`): `(context, next) => answer`, may be async.
- **returns:** a `Disposer` that removes the middleware.
- **throws:**
  - `TypeError`: `tg.interceptRpc(name or names, function)`, `tg.interceptRpc takes names as strings`, `tg.interceptRpc needs at least one name`, `tg.interceptRpc: <x> is not a method or a prefix ending with *`.
  - `TeleError` `forbidden` for a takeover method by name: `<method> can take over the account, intercepting it needs the grant 'unsafe.disableApiFiltering'`.
  - `TeleError` `not-granted`: `tg.interceptRpc('messages.sendMessage') needs the grant 'interceptRpc(messages.sendMessage)'`.
- **notes:**
  - the intercepted request is held: tele has registered it but not sent it. all middlewares for that method, script by script (folder order) and within a script in registration order, form one chain, which starts on the next event-loop turn.
  - `context.request` is the decoded request and is mutable; `context.method` is its name.
  - `next(request?)` passes the request (by default `context.request` as it is now) to the next middleware, or after the last one sends it to the server (same dc, same ordering as the original; it skips all interceptors). it resolves with the decoded result or rejects with an `RpcError`. mtp still sleeps through flood waits and migrations for it.
  - `next()` throws synchronously: `next(): <path>: <problem>` for a request that doesn't encode, `next() takes messages.sendMessage request, not …` for a different method, `next() can only be called once`, and `TeleError` `handle-expired` after the request was already answered.
  - what the middleware returns (or its promise resolves to), and what tele gets:

| the middleware returns | tele gets |
|---|---|
| `next()`'s value, or `undefined` after calling `next()` | the server's answer to the (possibly edited) request, byte for byte |
| a tl object of the method's result type | that object; nothing is sent if `next()` wasn't called. if it doesn't encode, a fault is logged and next's answer (or the rest of the chain) is used |
| an `RpcError` (returned or thrown) | that error, as if the server answered it |
| `undefined` without calling `next()`, or `null` | a fault, and `rpc_error` 400 `SCRIPT_FAILED` |
| a thrown non-`RpcError` | a fault, and 400 `SCRIPT_FAILED` |

  - budget: 200 ms per synchronous turn and 10 s per request. over 10 s: a fault (`took longer than 10 s`); tele gets next's answer if `next()` was called, else 400 `SCRIPT_TIMEOUT`.
  - ordering: requests tele chains after the held one (sends in one chat) wait until it's answered, so messages keep their order; unrelated requests aren't delayed. keep `await`s short.
  - `next()`'s result is filtered like `tg.call` results. if anything was hidden in it, a returned replacement isn't used (a warning says changing it needs `unsafe.disableApiFiltering`) and the original goes to tele.
  - answering with `FLOOD_WAIT_X`, a 5xx or `*_MIGRATE_*` makes mtp resend the held request straight to the server, bypassing the chain.
  - not seen: `tg.call` traffic of any script, wrapper methods tele adds later (`invokeWithLayer`, `initConnection`, `invokeAfterMsg`), and mtp's own resends.
  - a script that stops while holding a request is skipped; the chain continues without it. a held request cancelled by tele isn't cancelled on the server if the chain already forwarded it.
  - `next()` can't switch methods. to answer one method with another, `tg.call` the other and return its result (the result types must match, e.g. both `Updates`).
  - changing a send changes what the server stores, and tele's local copy follows the server's answer.

Example:

```ts
tg.interceptRpc('messages.sendMessage', async ({ request }, next) => {
  if (request.message === 'ping') request.message = 'pong'
  return next()
})

tg.interceptRpc('messages.setTyping', () => true)

tg.interceptRpc('account.updateProfile', ({ request }, next) => {
  if (request.about?.includes('crypto')) return new RpcError(400, 'ABOUT_TOO_SPICY')
  return next()
})
```

### type RpcContext

```ts
export interface RpcContext<N extends tl.RpcMethod> {
  request: tl.RpcMethods[N]['request']
  readonly method: N
}
```

the first argument of an `interceptRpc` middleware.

- **fields:**
  - `request` (`tl.RpcMethods[N]['request']`): the decoded request; edit it in place or assign a new object of the same method. `next()` without arguments sends it as it is at that moment.
  - `method` (`N`, read-only): the method name, useful with arrays and globs.

Example:

```ts
tg.interceptRpc('messages.*', (context, next) => {
  console.log('tele sends', context.method)
  return next()
})
```

### type RpcNext

```ts
export type RpcNext<N extends tl.RpcMethod> = (
  request?: tl.RpcMethods[N]['request'],
) => Promise<tl.RpcResult<N>>
```

the second argument of a middleware: passes the request on and resolves with the answer.

- **parameters:**
  - `request` (optional): a replacement request of the same method; default `context.request`.
- **returns:** the decoded answer of the rest of the chain or the server.
- **throws:** see `tg.interceptRpc`: encoding `TypeError`s, a different method, a second call, `TeleError` `handle-expired`; rejects with `RpcError` for server errors.

Example:

```ts
tg.interceptRpc('messages.getHistory', async (context, next) => {
  const result = await next({ ...context.request, limit: 50 })
  return result
})
```

### type RpcAnswer

```ts
export type RpcAnswer<N extends tl.RpcMethod> =
  | tl.RpcResult<N>
  | RpcError
  | void
```

what a middleware may return: a result of the method's type, an `RpcError`, or nothing after calling `next()`.

- **fields:**
  - `tl.RpcResult<N>`: sent to tele instead of (or without) the server's answer.
  - `RpcError`: tele gets that error.
  - `void`: only valid after `next()` was called; then tele gets next's answer.

Example:

```ts
const answer: RpcAnswer<'contacts.resolveUsername'> = new RpcError(400, 'USERNAME_NOT_OCCUPIED')
```

### type RpcMiddleware

```ts
export type RpcMiddleware<N extends tl.RpcMethod> = (
  context: RpcContext<N>,
  next: RpcNext<N>,
) => RpcAnswer<N> | Promise<RpcAnswer<N>>
```

the function `tg.interceptRpc` takes.

- **fields:**
  - `context` (`RpcContext<N>`): the request and method.
  - `next` (`RpcNext<N>`): continues the chain.
  - return (`RpcAnswer<N> | Promise<RpcAnswer<N>>`): see the table under `tg.interceptRpc`.

Example:

```ts
const log: RpcMiddleware<tl.RpcMethod> = async (context, next) => {
  const started = performance.now()
  try {
    return await next()
  } finally {
    console.log(context.method, Math.round(performance.now() - started), 'ms')
  }
}
tg.interceptRpc('*', log)
```

### tg.interceptUpdate(type, middleware)

```ts
interceptUpdate<N extends tl.UpdateName>(
  type: N | N[],
  middleware: UpdateMiddleware<tl.UpdateOf<N>>,
): Disposer
interceptUpdate(
  type: '*',
  middleware: UpdateMiddleware<tl.AnyUpdate>,
): Disposer
```

changes or drops updates the server pushes (and catch-up differences) before tele and any listener sees them.

- **grant:** `interceptUpdate(<name>)` for each name, or bare `interceptUpdate`; `'*'` needs bare `interceptUpdate`.
- **parameters:**
  - `type` (`tl.UpdateName | tl.UpdateName[] | '*'`): update names as for `tg.onUpdate`.
  - `middleware` (`UpdateMiddleware<U>`): `({ update }) => 'deliver' | 'drop'`, may be async.
- **returns:** a `Disposer` that removes the interceptor.
- **throws:**
  - `TypeError`: `tg.interceptUpdate(name or names, function)`, `tg.interceptUpdate takes names as strings`, `tg.interceptUpdate needs at least one name`, `tg.interceptUpdate: <x> is not an update`.
  - `TeleError` `not-granted`: `tg.interceptUpdate('updateUserStatus') needs the grant 'interceptUpdate(updateUserStatus)'`.
- **notes:**
  - applies to pushed updates and to `updates.getDifference` / `getChannelDifference` results; not to `Updates` returned by tele's other requests (use `interceptRpc` for those) and never to `tg.call` results.
  - while any script intercepts updates, the account's pushed updates go through a queue: each message waits for every interceptor of every script, in order, and later messages wait behind it. without interceptors nothing is queued.
  - `context.update` is mutable: change it and answer `'deliver'`. `'drop'` hides it from tele and listeners.
  - dropped updates that carry `pts` are replaced by an empty `updateDeleteMessages` / `updateDeleteChannelMessages` with the same `pts` / `ptsCount`, so tele's sequence checks pass and nothing is re-fetched. updates with `qts` can't be dropped (a fault is logged and they're delivered). a dropped short update becomes an `updateShort` with that placeholder. difference `newMessages` are offered as `updateNewMessage` / `updateNewChannelMessage` and removed from the list when dropped.
  - anything other than `'deliver'` / `'drop'`, a throw or a rejection is a fault and the update is delivered as it was.
  - budget: 200 ms per synchronous turn, 2 s per batch per script. over it: a fault (`took longer than 2 s, the updates went through as they were`) and the batch is delivered unchanged.
  - without `unsafe.disableApiFiltering`, interceptors never see `updateServiceNotification`, messages from 777000, or `updateDraftMessage` without `account.read(draft)`; those pass through untouched.
  - changed containers are re-encoded as a whole; unchanged ones keep their original bytes.

Example:

```ts
tg.interceptUpdate('updateUserTyping', () => 'drop')

tg.interceptUpdate(['updateNewMessage', 'updateNewChannelMessage'], ({ update }) => {
  if (update.message._ === 'message') {
    update.message.message = update.message.message.replaceAll('lol', 'that is funny')
  }
  return 'deliver'
})
```

### type UpdateVerdict

```ts
export type UpdateVerdict = 'deliver' | 'drop'
```

the answer of an update interceptor.

- **fields:**
  - `'deliver'`: pass the (possibly changed) update on.
  - `'drop'`: hide it from tele and listeners (see `tg.interceptUpdate` for how pts stay in sync).

Example:

```ts
const verdict: UpdateVerdict = 'deliver'
```

### type UpdateContext

```ts
export interface UpdateContext<U extends tl.AnyUpdate> {
  update: U
}
```

the argument of an update interceptor.

- **fields:**
  - `update` (`U`): the decoded update, mutable. changes reach later interceptors, listeners and tele.

Example:

```ts
tg.interceptUpdate('updateUserName', (context: UpdateContext<tl.RawUpdateUserName>) => {
  context.update.firstName = context.update.firstName.toUpperCase()
  return 'deliver'
})
```

### type UpdateMiddleware

```ts
export type UpdateMiddleware<U extends tl.AnyUpdate> = (
  context: UpdateContext<U>,
) => UpdateVerdict | Promise<UpdateVerdict>
```

the function `tg.interceptUpdate` takes.

- **fields:**
  - `context` (`UpdateContext<U>`): holds the update.
  - return (`UpdateVerdict | Promise<UpdateVerdict>`): `'deliver'` or `'drop'`.

Example:

```ts
const quiet: UpdateMiddleware<tl.AnyUpdate> = ({ update }) =>
  update._ === 'updateUserStatus' ? 'drop' : 'deliver'
tg.interceptUpdate('*', quiet)
```

### tg.onUnload(callback)

```ts
onUnload(callback: () => void): Disposer
```

runs `callback` when the script stops: switched off, reloaded after a file change, the scripts folder changed, the account logged out, tele quitting, or turned off after 5 failures.

- **grant:** none.
- **parameters:**
  - `callback` (`() => void`): synchronous; a returned promise isn't awaited.
- **returns:** a `Disposer` that unregisters the callback without running it.
- **throws:** `TypeError: tg.onUnload(function)`.
- **notes:**
  - on stop, the cleanup function `setup` returned runs first (0.5 s), then every `onUnload` callback in registration order (0.5 s each; errors are logged, not counted as failures), then all registrations are dropped, timers die and pending `tg.call` promises never settle.
  - don't start async work here: the runtime is destroyed right after.

Example:

```ts
const started = Date.now()
tg.onUnload(() => {
  tg.storage.set('uptime', Date.now() - started)
})
```

### type Disposer

```ts
export interface Disposer {
  (): void
  [Symbol.dispose](): void
}
```

what every registration returns (`onUpdate`, `interceptRpc`, `onNewMessage`, `schedule`, `overridePeer`, menu items, buttons…): call it to undo the registration.

- **fields:**
  - `()` (`void`): removes the registration. calling it again does nothing.
  - `[Symbol.dispose]` (`void`): the same function, so `using` works.
- **notes:**
  - you don't have to dispose anything in cleanup: stopping the script removes all registrations by itself.
  - disposing from inside the callback it registered is fine.

Example:

```ts
using listener = tg.onNewMessage((message) => console.log(message.text))

const stop = tg.onUpdate('updateUserStatus', () => {})
setTimeout(stop, 60_000)
```

### tg.onNewMessage(callback)

```ts
onNewMessage(callback: (message: Message) => unknown): Disposer
```

calls `callback` with a `Message` for every new message tele receives: pushed, from differences, and from the `Updates` of tele's own and script requests.

- **grant:** `onUpdate(new_message)`. it's a separate grant: `onUpdate(updateNewMessage)` doesn't allow it and the other way round.
- **parameters:**
  - `callback` (`(message: Message) => unknown`): the return value is ignored; an async callback's rejection is an unhandled rejection (logged, not counted).
- **returns:** a `Disposer`.
- **throws:** `TypeError: tg.onNewMessage(function)`; `TeleError` `not-granted`: `tg.onNewMessage needs the grant 'onUpdate(new_message)'`.
- **notes:**
  - built from `updateNewMessage`, `updateNewChannelMessage`, `updateShortMessage` and `updateShortChatMessage` (short ones are turned into a full `message` with `peerId` and `fromId`). `messageEmpty` is skipped.
  - not delivered: `updateShortSentMessage` (private-chat sends, tele's and the script's own, usually come back that way; tele rebuilds them for the cache, not for this event), scheduled messages.
  - your other own sends do arrive here (in groups and channels, and messages you send from other devices), including the script's own `tg.sendMessage`: check `message.out` (or the ids you sent) before answering, or you loop.
  - `message.chat` and `message.sender` work without `account.read(peers)`: they come from tele's cache or the update's users and chats. the message's helpers (`reply`, `react`…) use the chat's input peer.
  - runs after interceptors, like `onUpdate` listeners: 200 ms per call, faults count toward the switch-off.

Example:

```ts
tg.onNewMessage(async (message) => {
  if (message.out || message.chatId !== tg.selfId) return
  if (message.text === '!ping') await message.reply('pong')
})
```

### tg.onMessageEdited(callback)

```ts
onMessageEdited(
  callback: (message: Message, previous: Message | null) => unknown,
): Disposer
```

calls `callback` for every edited message (`updateEditMessage`, `updateEditChannelMessage`), with the version from before the edit when tele had it.

- **grant:** `onUpdate(edit_message)`; `previous` needs `account.read(messages)` too.
- **parameters:**
  - `callback` (`(message, previous) => unknown`): `message` is the new version; `previous` the cached old one or `null`.
- **returns:** a `Disposer`.
- **throws:** `TypeError: tg.onMessageEdited(function)`; `TeleError` `not-granted`: `tg.onMessageEdited needs the grant 'onUpdate(edit_message)'`.
- **notes:**
  - `previous` comes from the message cache (the last 20000 messages tele received while scripts ran): `null` when the message isn't there or without `account.read(messages)`.
  - listeners run before tele applies the update, so the cache still holds the old version.
  - your own edits, the script's own included, arrive too.

Example:

```ts
tg.onMessageEdited((message, previous) => {
  if (previous && previous.text !== message.text) {
    console.log(`#${message.id}: "${previous.text}" -> "${message.text}"`)
  }
})
```

### tg.onMessageDeleted(callback)

```ts
onMessageDeleted(callback: (deleted: DeletedMessages) => unknown): Disposer
```

calls `callback` when messages are deleted (`updateDeleteMessages`, `updateDeleteChannelMessages`), with their last content when tele had it.

- **grant:** `onUpdate(delete_message)`; the `messages` contents need `account.read(messages)` too.
- **parameters:**
  - `callback` (`(deleted: DeletedMessages) => unknown`).
- **returns:** a `Disposer`.
- **throws:** `TypeError: tg.onMessageDeleted(function)`; `TeleError` `not-granted`: `tg.onMessageDeleted needs the grant 'onUpdate(delete_message)'`.
- **notes:**
  - outside channels telegram doesn't say where the messages were: `chatId` is `null` and ids are account-wide.
  - deletions made in this tele (the delete menu, `tg.deleteMessages`, `message.delete()`) arrive as a synthetic update right before tele removes them; the server never sends those back.
  - the dropped placeholders `interceptUpdate` creates are empty `updateDeleteMessages` and produce an event with no ids.

Example:

```ts
tg.onMessageDeleted(({ chatId, ids, messages }) => {
  ids.forEach((id, i) => {
    const text = messages[i]?.text
    if (text) console.log(`deleted #${id}${chatId === null ? '' : ` in ${chatId}`}: ${text}`)
  })
})
```

### type DeletedMessages

```ts
export interface DeletedMessages {
  chatId: bigint | null
  ids: number[]
  messages: (Message | null)[]
}
```

what `onMessageDeleted` gets.

- **fields:**
  - `chatId` (`bigint | null`): the marked channel id for channel and supergroup deletions; `null` for private chats and basic groups.
  - `ids` (`number[]`): the deleted message ids.
  - `messages` (`(Message | null)[]`): same order as `ids`; the cached content, or `null` when it isn't cached or without `account.read(messages)`.

Example:

```ts
tg.onMessageDeleted((deleted: DeletedMessages) => {
  console.log(deleted.ids.length, 'gone')
})
```

### tg.selfId

```ts
readonly selfId: bigint
```

this account's user id, fixed for the instance.

- **grant:** none.
- **returns:** a `bigint`; it's also the marked id of Saved Messages.
- **notes:** one instance runs per logged-in account, so with two accounts the script runs twice; `selfId` tells the instances apart. `tg.storage` is already per account.

Example:

```ts
tg.onNewMessage((message) => {
  if (message.chatId === tg.selfId) console.log('saved messages:', message.text)
})
```

### tg.scriptName

```ts
readonly scriptName: string
```

the `name` from `defineScript`, read when the script started.

- **grant:** none.
- **returns:** a `string`; tele uses it in logs (`script <name>: ...`) and dialogs.

Example:

```ts
tg.toast(`${tg.scriptName} is on`)
```

### tg.randomId()

```ts
randomId(): bigint
```

a secure random signed 64-bit `bigint`, for the `randomId` fields of send methods.

- **grant:** none.
- **returns:** a `bigint` from tele's secure random source.

Example:

```ts
await tg.call({ _: 'messages.sendMedia', peer: { _: 'inputPeerSelf' }, media: { _: 'inputMediaDice', emoticon: '🎲' }, message: '', randomId: tg.randomId() })
```

## messages

messages come to scripts as `Message` objects: a tl message with friendly getters and helpers bound to the account. the helpers on `tg` read, send, edit, delete, forward and react with the same grants as the raw methods behind them, and resolve any `InputPeerLike` for you. they all go through `tg.call`, so the flood policy, the account protection and the filters apply, and their traffic skips interceptors.

### new Message(raw)

```ts
export class Message {
  constructor(raw: tl.TypeMessage)
}
```

wraps any tl `message`, `messageService` or `messageEmpty` object. messages from events and helpers are already `Message`s; build one yourself from raw `tg.call` results.

- **grant:** none to build one; the helpers need their own grants.
- **parameters:**
  - `raw` (`tl.TypeMessage`): the tl object. it isn't copied: the getters read it live.
- **returns:** a `Message` bound to this script's account.
- **throws:** `TypeError: new Message() needs a TL message object` for anything else.
- **notes:**
  - import it from `'tele'` or use `tg.Message`; both are the same class.
  - messages built by `tg` (events, `getHistory`, `sendMessage`…) also carry the users and chats of the update or result they came in, which `chat` and `sender` fall back to. a hand-built one only has tele's cache.
  - a `Message` created before `setup` ran (at module top level) has no account, and its helpers throw `TeleError` `unsupported`.
  - getters live on the prototype: `console.log(message)` shows `Message { raw }`, and `JSON.stringify` uses `toJSON()` (the raw object; mind the bigints).

Example:

```ts
import { Message } from 'tele'

const result = await tg.call({ _: 'messages.getHistory', peer: { _: 'inputPeerSelf' }, offsetId: 0, offsetDate: 0, addOffset: 0, limit: 1, maxId: 0, minId: 0, hash: 0n })
if (result._ !== 'messages.messagesNotModified' && result.messages[0]) {
  const last = new Message(result.messages[0])
  console.log(last.text, last.chatId === tg.selfId)
}
```

### tg.Message

```ts
readonly Message: typeof Message
```

the `Message` class, for scripts that don't import from `'tele'` (plain `.js` scripts using the global `defineScript`).

- **grant:** none.
- **returns:** the same class `import { Message } from 'tele'` gives.

Example:

```ts
const wrapped = new tg.Message(rawMessage)
console.log(wrapped instanceof tg.Message)
```

### message.raw

```ts
readonly raw: tl.TypeMessage
```

the tl object the message wraps.

- **returns:** the original `message` / `messageService` / `messageEmpty` object, not a copy. it's an own enumerable property, the only one.
- **notes:** reach for `raw` for anything without a getter: `raw.replyMarkup`, `raw.ttlPeriod`, `raw.fromBoostsApplied`, `raw.factcheck`…

Example:

```ts
if (message.raw._ === 'message' && message.raw.replyMarkup) {
  console.log('has buttons')
}
```

### message.id

```ts
readonly id: number
```

the message id. outside channels and supergroups, ids are counted per account, not per chat.

- **returns:** a `number`; `0` for local messages.

Example:

```ts
await message.reply(`this was #${message.id}`)
```

### message.isService

```ts
readonly isService: boolean
```

`true` for `messageService` (joins, pins, title changes, calls…).

- **returns:** `raw._ === 'messageService'`.

Example:

```ts
tg.onNewMessage((message) => {
  if (message.isService) console.log('service:', message.action?._)
})
```

### message.date

```ts
readonly date: number
```

when the message was sent, in unix seconds.

- **returns:** `raw.date`, or `0` for `messageEmpty`.

Example:

```ts
const when = new Date(message.date * 1000)
```

### message.editDate

```ts
readonly editDate: number | null
```

when the message was last edited, in unix seconds.

- **returns:** `raw.editDate` or `null` if it was never edited.

Example:

```ts
if (message.editDate !== null) console.log('edited', message.editDate - message.date, 's later')
```

### message.out

```ts
readonly out: boolean
```

the server's "outgoing" flag: `true` for messages you sent.

- **returns:** `raw.out === true`.
- **notes:** messages in Saved Messages come with `out: false` and no `fromId`, even your own; `senderId` is still you. use `out` to skip your own messages in `onNewMessage`.

Example:

```ts
tg.onNewMessage((message) => {
  if (message.out) return
  console.log('incoming:', message.text)
})
```

### message.silent

```ts
readonly silent: boolean
```

`true` if it was sent without a notification.

- **returns:** `raw.silent === true`.

Example:

```ts
if (message.silent) console.log('sent quietly')
```

### message.mentioned

```ts
readonly mentioned: boolean
```

`true` if the message mentions you or replies to you.

- **returns:** `raw.mentioned === true`.

Example:

```ts
tg.onNewMessage((message) => {
  if (message.mentioned) tg.notify('mention', message.text)
})
```

### message.post

```ts
readonly post: boolean
```

`true` for channel posts.

- **returns:** `raw.post === true`.

Example:

```ts
if (message.post) console.log('channel post with', message.views, 'views')
```

### message.isPinned

```ts
readonly isPinned: boolean
```

`true` if the message is pinned in its chat.

- **returns:** `raw.pinned === true`.

Example:

```ts
const pinned = (await tg.getHistory('me', { limit: 100 })).filter((m) => m.isPinned)
```

### message.text

```ts
readonly text: string
```

the message text or media caption.

- **returns:** `raw.message`; `''` for service messages and `messageEmpty`.
- **notes:** login codes in messages from 777000 are masked as `*****` unless the script has `unsafe.disableApiFiltering`.

Example:

```ts
if (/^!echo /.test(message.text)) await message.reply(message.text.slice(6))
```

### message.entities

```ts
readonly entities: tl.TypeMessageEntity[]
```

the formatting of `text`: bold, links, mentions, custom emoji…

- **returns:** `raw.entities`, or `[]` when there are none and for service messages.
- **notes:** offsets and lengths count utf-16 code units, like js strings.

Example:

```ts
const links = message.entities
  .filter((entity) => entity._ === 'messageEntityTextUrl')
  .map((entity) => entity.url)
```

### message.textWithEntities

```ts
readonly textWithEntities: Required<TextWithEntities>
```

`text` and `entities` together, ready to send again or to put into `md` / `html` templates.

- **returns:** a fresh `{ text, entities }` object each time.

Example:

```ts
await tg.sendMessage('me', md`**quote:** ${message.textWithEntities}`)
```

### message.media

```ts
readonly media: tl.TypeMessageMedia | null
```

the attached media as tl.

- **returns:** `raw.media` or `null`. it can still be `messageMediaEmpty` or `messageMediaUnsupported`; `mediaType` treats those as none.
- **notes:** pass it to `tg.downloadMedia`, or as `media` of `tg.addLocalMessage`.

Example:

```ts
if (message.media?._ === 'messageMediaGeo' && message.media.geo._ === 'geoPoint') {
  console.log(message.media.geo.lat, message.media.geo.long)
}
```

### message.mediaType

```ts
readonly mediaType: MediaType | null
```

a short name for the kind of media.

- **returns:** `null` for no media, `messageMediaEmpty` and `messageMediaUnsupported`; otherwise a `MediaType`:
  - documents: `'sticker'` when it has a sticker attribute; else `'gif'` for animated ones; else `'roundVideo'` / `'video'` for video attributes; else `'voice'` / `'music'` for audio attributes; else `'document'`.
  - `messageMediaPhoto` -> `'photo'`, `messageMediaPoll` -> `'poll'`, `messageMediaContact` -> `'contact'`, `messageMediaGeo` and `messageMediaGeoLive` -> `'location'`, `messageMediaVenue` -> `'venue'`, `messageMediaStory` -> `'story'`, `messageMediaGiveaway` and `messageMediaGiveawayResults` -> `'giveaway'`, `messageMediaInvoice` -> `'invoice'`, `messageMediaDice` -> `'dice'`, `messageMediaWebPage` -> `'webpage'`, `messageMediaGame` -> `'game'`, `messageMediaPaidMedia` -> `'paidMedia'`.
  - anything else (to-do lists, video streams, newer media) -> `'other'`.

Example:

```ts
tg.onNewMessage(async (message) => {
  if (message.mediaType === 'voice' && (message.duration ?? 0) > 60) {
    await message.reply('that is a long one')
  }
})
```

### message.document

```ts
readonly document: tl.RawDocument | null
```

the document of a file, video, voice, sticker or gif message.

- **returns:** `media.document` when the media is `messageMediaDocument` holding a real `document`; `null` otherwise (also for `documentEmpty`).

Example:

```ts
const name = message.document?.attributes.find((a) => a._ === 'documentAttributeFilename')
console.log(name?._ === 'documentAttributeFilename' ? name.fileName : 'no name', message.document?.size)
```

### message.photo

```ts
readonly photo: tl.RawPhoto | null
```

the photo of a photo message.

- **returns:** `media.photo` when the media is `messageMediaPhoto` holding a real `photo`; `null` otherwise.

Example:

```ts
if (message.photo) {
  const jpeg = await tg.downloadMedia(message)
  console.log(jpeg.length, 'bytes')
}
```

### message.duration

```ts
readonly duration: number | null
```

the length of a video, round video, voice message or audio file, in seconds.

- **returns:** the `duration` of the document's first video or audio attribute; `null` for everything else, photos included.

Example:

```ts
if (message.mediaType === 'roundVideo') console.log(`${message.duration} s circle`)
```

### message.groupedId

```ts
readonly groupedId: bigint | null
```

the album id: messages of one album share it.

- **returns:** `raw.groupedId` or `null`.

Example:

```ts
const album = history.filter((m) => m.groupedId !== null && m.groupedId === message.groupedId)
```

### message.forwardedFrom

```ts
readonly forwardedFrom: tl.TypeMessageFwdHeader | null
```

the forward header of a forwarded message.

- **returns:** `raw.fwdFrom` or `null`.
- **notes:** your own message forwarded into Saved Messages has no forward header.

Example:

```ts
const origin = message.forwardedFrom
if (origin?.fromName) console.log('forwarded from a hidden account:', origin.fromName)
```

### message.viaBotId

```ts
readonly viaBotId: bigint | null
```

the inline bot the message was sent through.

- **returns:** `raw.viaBotId` or `null`.

Example:

```ts
if (message.viaBotId !== null) console.log('sent via', tg.peers.get(message.viaBotId)?.username)
```

### message.views

```ts
readonly views: number | null
```

the view counter of channel posts.

- **returns:** `raw.views` or `null`.

Example:

```ts
console.log(`${message.views ?? 0} views`)
```

### message.forwards

```ts
readonly forwards: number | null
```

how many times a channel post was forwarded.

- **returns:** `raw.forwards` or `null`.

Example:

```ts
if ((message.forwards ?? 0) > 100) console.log('viral')
```

### message.reactions

```ts
readonly reactions: tl.TypeMessageReactions | null
```

the reactions summary as tl.

- **returns:** `raw.reactions` or `null`.

Example:

```ts
const total = message.reactions?.results.reduce((sum, item) => sum + item.count, 0) ?? 0
```

### message.action

```ts
readonly action: tl.TypeMessageAction | null
```

what a service message is about.

- **returns:** `raw.action` for `messageService`, `null` otherwise.

Example:

```ts
if (message.action?._ === 'messageActionChatAddUser') {
  await message.reply('welcome')
}
```

### message.replyToMessageId

```ts
readonly replyToMessageId: number | null
```

the id of the message this one replies to.

- **returns:** `replyTo.replyToMsgId` when the reply header is a `messageReplyHeader`; `null` for no reply and for story replies.
- **notes:** in forum topics the first message of a topic is also the reply target of messages that don't reply to anything else; compare with `topicId`.

Example:

```ts
if (message.replyToMessageId !== null) {
  const parent = await tg.getMessages(message, message.replyToMessageId)
  console.log('replying to', parent?.text)
}
```

### message.topicId

```ts
readonly topicId: number | null
```

the forum topic the message belongs to.

- **returns:** for a reply header with `forumTopic`, `replyToTopId` or else `replyToMsgId`; `null` outside topics (and in the general topic).

Example:

```ts
if (message.topicId !== null) await tg.sendMessage(message, 'hi topic', { topicId: message.topicId })
```

### message.chatId

```ts
readonly chatId: bigint | null
```

the marked id of the chat the message is in.

- **returns:** users `> 0`, basic groups `-chatId`, channels and supergroups `-1000000000000 - channelId`, Saved Messages = `tg.selfId`; `null` when `raw.peerId` is missing (`messageEmpty` without it).

Example:

```ts
if (message.chatId === tg.selfId) console.log('a note to self')
```

### message.senderId

```ts
readonly senderId: bigint | null
```

the marked id of who sent it.

- **returns:** `raw.fromId` as a marked id; else you for outgoing private messages; else the chat itself (channel posts, incoming private messages, Saved Messages).

Example:

```ts
if (message.senderId === tg.selfId) console.log('my own')
```

### message.chat

```ts
readonly chat: PeerInfo | null
```

the chat as a `PeerInfo`.

- **grant:** none needed with events; tele's cache is read when the script has `account.read(peers)` or any `onUpdate` grant.
- **returns:** the `PeerInfo` from tele's cache, else one built from the users and chats the message came with (only `id`, `kind`, `name`, `username` and `input` are filled then), else `null`.

Example:

```ts
console.log(`in ${message.chat?.name ?? message.chatId}`)
```

### message.sender

```ts
readonly sender: PeerInfo | null
```

the sender as a `PeerInfo`, looked up like `chat`.

- **grant:** as for `chat`.
- **returns:** a `PeerInfo` for `senderId`, or `null`.

Example:

```ts
const who = message.sender
if (who?.kind === 'bot') return
```

### message.reply(text, options?)

```ts
reply(text: InputText, options?: SendOptions & { noWebpage?: boolean }): Promise<Message>
```

sends `text` to the same chat as a reply to this message; `tg.sendMessage` with `replyTo` set to this id.

- **grant:** `account.write(send)`.
- **parameters:**
  - `text` (`InputText`): a string or `{ text, entities }` (`md` / `html` results).
  - `options` (`SendOptions & { noWebpage? }`, optional): as for `tg.sendMessage`; `replyTo` is always this message.
- **returns:** the sent `Message`.
- **throws:** as `tg.sendMessage`; `TeleError` `unsupported` for a message without an account.
- **notes:** the chat is addressed by its input peer from the cache or the update, so no `account.read(peers)` is needed for messages from events; without either it falls back to the marked id, which needs `account.read(peers)`.

Example:

```ts
tg.onNewMessage(async (message) => {
  if (message.text === '/time') await message.reply(new Date().toISOString(), { silent: true })
})
```

### message.edit(text, options?)

```ts
edit(text: InputText | null, options?: EditOptions): Promise<Message>
```

edits this message; `tg.editMessage` for its chat and id.

- **grant:** `account.write(edit)`.
- **parameters:**
  - `text` (`InputText | null`): the new text; `null` keeps the text (to change only the media).
  - `options` (`EditOptions`, optional): `noWebpage`, `invertMedia`, `media`.
- **returns:** the edited `Message`.
- **throws:** as `tg.editMessage` (`RpcError` `MESSAGE_NOT_MODIFIED`, `MESSAGE_AUTHOR_REQUIRED`…).

Example:

```ts
const sent = await tg.sendMessage('me', 'counting…')
for (let i = 3; i > 0; i--) {
  await new Promise<void>((done) => setTimeout(done, 1000))
  await sent.edit(String(i))
}
```

### message.delete(options?)

```ts
delete(options?: { revoke?: boolean }): Promise<void>
```

deletes this message; `tg.deleteMessages` with its id.

- **grant:** `account.write(delete)`.
- **parameters:**
  - `options.revoke` (`boolean`, optional): delete for everyone; default `true`. ignored in channels and supergroups, where deletion is always for everyone.
- **returns:** resolves when the server confirmed; tele removes the message at once.
- **throws:** as `tg.deleteMessages`.

Example:

```ts
tg.onNewMessage(async (message) => {
  if (message.out && message.text.startsWith('tmp ')) {
    setTimeout(() => message.delete(), 30_000)
  }
})
```

### message.react(reaction, options?)

```ts
react(reaction: Reaction | null, options?: { big?: boolean }): Promise<void>
```

puts your reaction on this message, replacing your previous ones; `null` removes yours.

- **grant:** `account.write(react)`.
- **parameters:**
  - `reaction` (`Reaction | null`): an emoji string, `{ customEmojiId }`, or `null`.
  - `options.big` (`boolean`, optional): the big animation.
- **returns:** resolves when done.
- **throws:** as `tg.setReaction` (`RpcError` `REACTION_INVALID` for a reaction the chat doesn't allow).

Example:

```ts
await message.react('👍')
await message.react({ customEmojiId: 5368324170671202286n }, { big: true })
await message.react(null)
```

### message.forward(to, options?)

```ts
forward(to: InputPeerLike, options?: ForwardOptions): Promise<Message | null>
```

forwards this message to another chat; `tg.forwardMessages` with one id.

- **grant:** `account.write(forward)`.
- **parameters:**
  - `to` (`InputPeerLike`): the target chat.
  - `options` (`ForwardOptions`, optional).
- **returns:** the new `Message`, or `null` if the answer didn't contain it.
- **throws:** as `tg.forwardMessages`.

Example:

```ts
tg.onNewMessage(async (message) => {
  if (message.mentioned) await message.forward('me', { silent: true })
})
```

### message.read()

```ts
read(): Promise<void>
```

marks the chat as read up to this message; `tg.readHistory` with `maxId` set to this id.

- **grant:** `account.write(read)`.
- **returns:** resolves at once; tele sends the read request itself and updates badges.
- **throws:** `TeleError` `not-found` (`tele has no such chat loaded`) for a chat tele hasn't loaded.

Example:

```ts
tg.onNewMessage(async (message) => {
  if (message.chat?.kind === 'channel') await message.read()
})
```

### message.toJSON()

```ts
toJSON(): tl.TypeMessage
```

the raw tl object, so `JSON.stringify(message)` serializes `raw`.

- **returns:** `raw` itself.
- **notes:** tl objects contain bigints; use a replacer: `JSON.stringify(message, (k, v) => typeof v === 'bigint' ? String(v) : v)`.

Example:

```ts
tg.storage.set('last', message.toJSON() as never)
```

### type MediaType

```ts
export type MediaType =
  | 'photo' | 'video' | 'roundVideo' | 'voice' | 'music' | 'sticker' | 'gif' | 'document'
  | 'poll' | 'contact' | 'location' | 'venue' | 'story' | 'giveaway' | 'invoice' | 'dice'
  | 'webpage' | 'game' | 'paidMedia' | 'other'
```

the values of `message.mediaType`.

- **fields:**
  - `'photo'`: a photo (`messageMediaPhoto`).
  - `'video'`: a video document.
  - `'roundVideo'`: a round video message.
  - `'voice'`: a voice message.
  - `'music'`: an audio file.
  - `'sticker'`: a sticker, animated and video ones included.
  - `'gif'`: an animation (gif / mp4 without sound).
  - `'document'`: any other file.
  - `'poll'`: a poll or quiz.
  - `'contact'`: a shared contact.
  - `'location'`: a point or a live location.
  - `'venue'`: a place.
  - `'story'`: a forwarded story.
  - `'giveaway'`: a giveaway or its results.
  - `'invoice'`: a payment invoice.
  - `'dice'`: an animated dice-like emoji.
  - `'webpage'`: a link preview.
  - `'game'`: a game.
  - `'paidMedia'`: paid media.
  - `'other'`: media types without a name here.

Example:

```ts
const counts = new Map<MediaType, number>()
for (const m of await tg.getHistory('me')) {
  if (m.mediaType) counts.set(m.mediaType, (counts.get(m.mediaType) ?? 0) + 1)
}
```

### type TextWithEntities

```ts
export interface TextWithEntities {
  text: string
  entities?: tl.TypeMessageEntity[]
}
```

text with telegram formatting, the shape every text-taking api accepts and `md` / `html` return.

- **fields:**
  - `text` (`string`): the plain text.
  - `entities` (`tl.TypeMessageEntity[]`, optional): formatting ranges over `text` in utf-16 units; missing means none.

Example:

```ts
const bold: TextWithEntities = {
  text: 'hello',
  entities: [{ _: 'messageEntityBold', offset: 0, length: 5 }],
}
await tg.sendMessage('me', bold)
```

### type InputText

```ts
export type InputText = string | TextWithEntities
```

any text argument: a plain string (sent as it is, no markdown) or `{ text, entities }`.

- **fields:**
  - `string`: plain text without formatting. markdown in it is not parsed; wrap it in `md(...)` for that.
  - `TextWithEntities`: formatted text.
- **throws:** helpers throw `TypeError: expected a string or { text, entities }` for anything else.

Example:

```ts
const plain: InputText = '**not bold**'
const rich: InputText = md('**bold**')
```

### type TextFormat

```ts
export interface TextFormat {
  (
    strings: TemplateStringsArray,
    ...values: (InputText | number | bigint | boolean | null | undefined)[]
  ): Required<TextWithEntities>
  (text: string): Required<TextWithEntities>
}
```

the shape of `md` and `html`: a plain call or a template tag.

- **fields:**
  - `(text)`: parses the whole string.
  - ``(strings, ...values)``: parses the template, inserting values as text.
  - return (`Required<TextWithEntities>`): `{ text, entities }`, entities sorted by offset.

Example:

```ts
const format: TextFormat = md
console.log(format`**${'x'}**`.entities)
```

### md(text)

```ts
export const md: TextFormat
```

turns tele's composer markdown into `{ text, entities }`, exactly what typing it into the message field would send.

- **grant:** none.
- **parameters:**
  - `text` (`string`): markdown: `**bold**`, `__italic__`, `~~strike~~`, `||spoiler||`, `` `code` ``, ```` ```pre``` ````, and `[text](url)` links (only urls the composer accepts as links).
  - as a template tag, `values` (`InputText | number | bigint | boolean | null | undefined`): inserted as text and never parsed. a `{ text, entities }` value (another `md` result, `message.textWithEntities`) keeps its entities, shifted into place; `null` and `undefined` insert nothing; everything else goes through `String()`.
- **returns:** `{ text, entities }` with the markers removed.
- **throws:** `TypeError: md takes a string or works as a template tag`; `RangeError: md takes at most 6400 values`.
- **notes:**
  - import it with `import { md } from 'tele'`.
  - values are protected with private-use placeholders while parsing, so user input can never inject formatting.
  - entities are converted the way tele sends them; local-only tags are skipped.

Example:

```ts
import { md } from 'tele'

const name = 'a**b**c'
await tg.sendMessage('me', md`**hello** ${name}, see [the docs](https://gettele.app/scripting)`)
```

### html(text)

```ts
export const html: TextFormat
```

turns html into `{ text, entities }` with tele's html reader (the one used for pasted rich text).

- **grant:** none.
- **parameters:**
  - `text` (`string`): html such as `<b>` / `<strong>`, `<i>` / `<em>`, `<u>`, `<s>` / `<strike>` / `<del>`, `<code>`, `<pre>`, `<a href="...">`, `<blockquote>`, `<tg-spoiler>`, `<br>`. a link whose text is its own url becomes plain text (telegram auto-links it).
  - as a template tag, `values`: inserted as text, unparsed, like `md` (``html`<b>${'<i>x</i>'}</b>` `` is bold `<i>x</i>` literally).
- **returns:** `{ text, entities }`.
- **throws:** `TypeError: html takes a string or works as a template tag`; `RangeError: html takes at most 6400 values`.
- **notes:** text that isn't valid html is taken as plain text.

Example:

```ts
import { html } from 'tele'

await tg.sendMessage('me', html`<b>${message.sender?.name ?? 'someone'}</b> said <i>${message.text}</i>`)
```

### tg.getMe()

```ts
getMe(): Promise<tl.TypeUser>
```

this account's own `user`, fresh from the server.

- **grant:** `account.read(self)` or `account.read(peers)`.
- **returns:** `users.getUsers([inputUserSelf])[0]`.
- **throws:** `TeleError` `not-granted`; `RpcError` for server errors.
- **notes:** for cached data without a request use `tg.peers.self`.

Example:

```ts
const me = await tg.getMe()
if (me._ === 'user') console.log(me.firstName, me.premium)
```

### tg.getUser(peer)

```ts
getUser(peer: InputPeerLike): Promise<tl.RawUser | null>
```

a user from the server.

- **grant:** `account.read(peers)` (or `account.read(self)` for `'me'`); resolving a marked id or a username needs `account.read(peers)`.
- **parameters:**
  - `peer` (`InputPeerLike`): a user or bot.
- **returns:** the `user`, or `null` for `userEmpty`.
- **throws:** `TypeError: expected a user` for a chat or channel; `TeleError` `not-found` for an uncached id or a free username; `RpcError`.

Example:

```ts
const durov = await tg.getUser('@durov')
console.log(durov?.verified)
```

### tg.getChat(peer)

```ts
getChat(peer: InputPeerLike): Promise<tl.TypeChat | null>
```

a basic group, supergroup or channel from the server.

- **grant:** `account.read(peers)`.
- **parameters:**
  - `peer` (`InputPeerLike`): a group or channel.
- **returns:** `channels.getChannels` / `messages.getChats`' first chat, or `null`.
- **throws:** `TypeError: expected a group or a channel` for users; `TeleError` `not-found`; `RpcError` (`CHANNEL_PRIVATE`…).

Example:

```ts
const chat = await tg.getChat('@telegram')
if (chat?._ === 'channel') console.log(chat.title, chat.participantsCount)
```

### tg.getFullUser(peer)

```ts
getFullUser(peer: InputPeerLike): Promise<tl.users.TypeUserFull>
```

the full profile of a user: bio, common chats count, birthday, business info…

- **grant:** `account.read(peers)` or `account.read(self)`.
- **parameters:**
  - `peer` (`InputPeerLike`): a user or bot.
- **returns:** `users.getFullUser`'s `users.userFull` (`fullUser`, `users`, `chats`).
- **throws:** `TypeError: expected a user`; `TeleError` `not-found`; `RpcError`.

Example:

```ts
const { fullUser } = await tg.getFullUser('me')
console.log(fullUser.about)
```

### tg.getFullChat(peer)

```ts
getFullChat(peer: InputPeerLike): Promise<tl.messages.TypeChatFull>
```

the full info of a group or channel: description, members count, linked chat…

- **grant:** `account.read(peers)`.
- **parameters:**
  - `peer` (`InputPeerLike`): a group or channel.
- **returns:** `channels.getFullChannel` / `messages.getFullChat`'s `messages.chatFull`.
- **throws:** `TypeError: expected a group or a channel`; `TeleError` `not-found`; `RpcError`.

Example:

```ts
const full = await tg.getFullChat('@telegram')
console.log(full.fullChat.about)
```

### tg.getMessages(peer, id)

```ts
getMessages(peer: InputPeerLike, id: number): Promise<Message | null>
getMessages(peer: InputPeerLike, ids: number[]): Promise<(Message | null)[]>
```

messages by id.

- **grant:** `account.read(messages)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat. for channels and supergroups it picks the chat; elsewhere ids are account-wide and the peer only decides which method is used.
  - `id` / `ids` (`number` / `number[]`): message ids.
- **returns:** one `Message` or `null`; with an array, an array in the same order with `null` for missing or deleted ones.
- **throws:** `TeleError` `not-granted`, `not-found`; `RpcError`.
- **notes:** uses `channels.getMessages` for channels and `messages.getMessages` otherwise. no network-free variant: see `tg.getCachedMessage`.

Example:

```ts
const [first, second] = await tg.getMessages('me', [1, 2])
console.log(first?.text, second?.text)
```

### tg.getHistory(peer, options?)

```ts
getHistory(peer: InputPeerLike, options?: HistoryOptions): Promise<Message[]>
```

one page of a chat's history, newest first.

- **grant:** `account.read(history)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `options` (`HistoryOptions`, optional): `limit` (default 100, the server caps it at 100), `offsetId`, `offsetDate`, `addOffset`, `minId`, `maxId`.
- **returns:** the page as `Message`s (`messageEmpty` skipped).
- **throws:** `TeleError` `not-granted`, `not-found`; `RpcError`.
- **notes:** one `messages.getHistory` call with `hash: 0`. for more than a page use `iterHistory`.

Example:

```ts
const last10 = await tg.getHistory('me', { limit: 10 })
console.log(last10.map((m) => m.text))
```

### tg.iterHistory(peer, options?)

```ts
iterHistory(
  peer: InputPeerLike,
  options?: HistoryOptions & { batchSize?: number },
): AsyncGenerator<Message, void, undefined>
```

walks a chat's history from newest to oldest, page by page.

- **grant:** `account.read(history)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `options.limit` (`number`, optional): stop after this many messages; default no limit.
  - `options.batchSize` (`number`, optional): messages per request, at most 100; default 100.
  - `options.offsetId`, `offsetDate`, `minId`, `maxId` (optional): as in `HistoryOptions`; `addOffset` is ignored.
- **returns:** an async generator of `Message`s.
- **throws:** the errors of `getHistory`, from the `next()` that hit them.
- **notes:** nothing is sent until the first `next()`; each page continues from the last id it saw; it stops at `limit` or an empty page. breaking out of `for await` stops it. long walks run into flood waits: up to 10 s they're slept through, longer ones reject.

Example:

```ts
let photos = 0
for await (const message of tg.iterHistory('me', { limit: 1000 })) {
  if (message.mediaType === 'photo') photos++
}
console.log(photos, 'photos in the last 1000 messages')
```

### type HistoryOptions

```ts
export interface HistoryOptions {
  limit?: number
  offsetId?: number
  offsetDate?: number | Date
  addOffset?: number
  minId?: number
  maxId?: number
}
```

paging options of `getHistory` and `iterHistory`, the fields of `messages.getHistory`.

- **fields:**
  - `limit` (`number`, optional): how many messages; `getHistory` default 100.
  - `offsetId` (`number`, optional): start below this message id; default 0 (the newest).
  - `offsetDate` (`number | Date`, optional): start below this date (unix seconds or a `Date`).
  - `addOffset` (`number`, optional): skip this many more (negative to go newer); `getHistory` only.
  - `minId` (`number`, optional): only ids above this.
  - `maxId` (`number`, optional): only ids below this.

Example:

```ts
const yesterday = await tg.getHistory('me', { offsetDate: new Date(Date.now() - 86_400_000), limit: 20 })
```

### tg.getDialogs(options?)

```ts
getDialogs(options?: DialogOptions): Promise<Dialog[]>
```

the chat list from the server, in order.

- **grant:** `account.read(dialogs)`.
- **parameters:**
  - `options` (`DialogOptions`, optional): `limit` (default 100), `folderId`, `excludePinned`.
- **returns:** an array of `Dialog`s.
- **throws:** `TeleError` `not-granted`; `RpcError`.
- **notes:** collects `iterDialogs` with `limit: 100` unless you pass another; for tele's local list without network, use `tg.local.dialogs`.

Example:

```ts
const dialogs = await tg.getDialogs({ limit: 20 })
for (const dialog of dialogs) console.log(dialog.peer?.name, dialog.unreadCount)
```

### tg.iterDialogs(options?)

```ts
iterDialogs(
  options?: DialogOptions & { batchSize?: number },
): AsyncGenerator<Dialog, void, undefined>
```

walks the whole chat list from the server, page by page.

- **grant:** `account.read(dialogs)`.
- **parameters:**
  - `options.limit` (`number`, optional): stop after this many; default no limit.
  - `options.batchSize` (`number`, optional): dialogs per request, at most 100; default 100.
  - `options.folderId` (`number`, optional): `1` for the archive (the server's peer folder id, not a chat filter).
  - `options.excludePinned` (`boolean`, optional): skip pinned chats.
- **returns:** an async generator of `Dialog`s.
- **throws:** the errors of `messages.getDialogs`, from `next()`.
- **notes:** pages by the last dialog's top message (date, id, peer). archive entries (`dialogFolder`) and repeats are skipped. stops at the full list (`messages.dialogs`), an empty page, or `limit`.

Example:

```ts
let unread = 0
for await (const dialog of tg.iterDialogs()) unread += dialog.unreadCount
console.log(unread, 'unread in total')
```

### type DialogOptions

```ts
export interface DialogOptions {
  limit?: number
  folderId?: number
  excludePinned?: boolean
}
```

options of `getDialogs` and `iterDialogs`.

- **fields:**
  - `limit` (`number`, optional): how many dialogs; `getDialogs` default 100, `iterDialogs` default all.
  - `folderId` (`number`, optional): the peer folder: `0` main, `1` archive.
  - `excludePinned` (`boolean`, optional): leave pinned chats out.

Example:

```ts
const archived = await tg.getDialogs({ folderId: 1 })
```

### type Dialog

```ts
export interface Dialog {
  raw: tl.RawDialog
  id: bigint
  peer: PeerInfo | null
  lastMessage: Message | null
  unreadCount: number
  pinned: boolean
}
```

one chat of `getDialogs` / `iterDialogs`.

- **fields:**
  - `raw` (`tl.RawDialog`): the tl `dialog` (notify settings, read marks, draft…).
  - `id` (`bigint`): the chat's marked id.
  - `peer` (`PeerInfo | null`): built from the page's users and chats, with `id`, `kind`, `name`, `username` and `input` only (the flags like `verified` aren't filled); `null` if the page didn't include it.
  - `lastMessage` (`Message | null`): the top message, if the page had it.
  - `unreadCount` (`number`): unread messages.
  - `pinned` (`boolean`): pinned in that list.

Example:

```ts
for await (const dialog of tg.iterDialogs({ limit: 50 })) {
  if (dialog.unreadCount > 0 && dialog.peer?.kind === 'user') console.log(dialog.peer.name)
}
```

### tg.sendMessage(peer, text, options?)

```ts
sendMessage(
  peer: InputPeerLike,
  text: InputText,
  options?: SendOptions & { noWebpage?: boolean },
): Promise<Message>
```

sends a text message and resolves with it as tele received it back.

- **grant:** `account.write(send)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `text` (`InputText`): a string (no markdown) or `{ text, entities }`.
  - `options` (`SendOptions`, optional): `replyTo`, `topicId`, `silent`, `scheduleDate`, `sendAs`, `clearDraft`, `invertMedia`.
  - `options.noWebpage` (`boolean`, optional): no link preview.
- **returns:** the new `Message` (found by its random id in the answer; private-chat answers are rebuilt from `updateShortSentMessage`).
- **throws:** `TypeError: expected a string or { text, entities }`; `TeleError` `not-granted`, `not-found` (peer); `TeleError` `internal` (`the answer to messages.sendMessage had no message in it`); `RpcError` (`MESSAGE_EMPTY`, `CHAT_WRITE_FORBIDDEN`, `FLOOD_WAIT_X`…).
- **notes:**
  - uses `messages.sendMessage` with a fresh `tg.randomId()`. tele applies the answer, so the message shows up in the chat.
  - it doesn't go through `interceptSendMessage` or `interceptRpc` (only sends tele makes do). `onNewMessage` sees it with `out: true` in groups and channels; private-chat answers come back as `updateShortSentMessage`, which `onNewMessage` skips.
  - with `scheduleDate` the message goes to the chat's scheduled messages.

Example:

```ts
await tg.sendMessage('me', md`**reminder:** drink water`, { silent: true })
await tg.sendMessage('@some_channel', 'tomorrow', { scheduleDate: new Date(Date.now() + 86_400_000) })
```

### tg.sendMedia(peer, media, options?)

```ts
sendMedia(
  peer: InputPeerLike,
  media: tl.TypeInputMedia,
  options?: SendOptions & { caption?: InputText },
): Promise<Message>
```

sends any tl input media (a dice, a poll, a contact, an existing document, an uploaded file…).

- **grant:** `account.write(send)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `media` (`tl.TypeInputMedia`): e.g. `{ _: 'inputMediaDice', emoticon: '🎯' }`, `{ _: 'inputMediaUploadedPhoto', file }`.
  - `options` (`SendOptions`, optional): as for `sendMessage`.
  - `options.caption` (`InputText`, optional): the caption; default empty.
- **returns:** the new `Message`.
- **throws:** encoding `TypeError`s for bad media; as `sendMessage` (`the answer to messages.sendMedia had no message in it`, `RpcError` `MEDIA_EMPTY`…).
- **notes:** for local files use `tg.sendFile`, which uploads and calls this.

Example:

```ts
await tg.sendMedia('me', { _: 'inputMediaDice', emoticon: '🎲' })
await tg.sendMedia('me', {
  _: 'inputMediaContact',
  phoneNumber: '+10000000000',
  firstName: 'pizza',
  lastName: 'place',
  vcard: '',
}, { caption: md`call **before 9**` })
```

### type SendOptions

```ts
export interface SendOptions {
  replyTo?: number
  topicId?: number
  silent?: boolean
  scheduleDate?: number | Date
  sendAs?: InputPeerLike
  clearDraft?: boolean
  invertMedia?: boolean
}
```

common options of `sendMessage`, `sendMedia`, `sendFile` and `message.reply`.

- **fields:**
  - `replyTo` (`number`, optional): reply to this message id in the same chat.
  - `topicId` (`number`, optional): send into this forum topic (its first message id). with `replyTo` both are sent; alone it's also the reply target.
  - `silent` (`boolean`, optional): no notification.
  - `scheduleDate` (`number | Date`, optional): schedule it; unix seconds or a `Date`.
  - `sendAs` (`InputPeerLike`, optional): send as a channel you own or the group itself (anonymous admins).
  - `clearDraft` (`boolean`, optional): clear the chat's draft.
  - `invertMedia` (`boolean`, optional): show the link preview or media above the text.

Example:

```ts
const options: SendOptions = { replyTo: 42, silent: true, sendAs: '@my_channel' }
await tg.sendMessage('@my_group', 'posted as the channel', options)
```

### tg.editMessage(peer, id, text, options?)

```ts
editMessage(
  peer: InputPeerLike,
  id: number,
  text: InputText | null,
  options?: EditOptions,
): Promise<Message>
```

edits a message's text, formatting, preview or media.

- **grant:** `account.write(edit)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `id` (`number`): the message id.
  - `text` (`InputText | null`): the new text; with a string, formatting is cleared. `null` keeps the text.
  - `options` (`EditOptions`, optional): `noWebpage`, `invertMedia`, `media`.
- **returns:** the edited `Message` from the answer's edit update.
- **throws:** `TypeError` for bad text; `TeleError` `internal` (`the answer to messages.editMessage had no message in it`); `RpcError` (`MESSAGE_NOT_MODIFIED`, `MESSAGE_EDIT_TIME_EXPIRED`, `MESSAGE_ID_INVALID`…).
- **notes:** `onMessageEdited` sees the edit too, with the previous version from the cache.

Example:

```ts
const sent = await tg.sendMessage('me', 'draft')
await tg.editMessage('me', sent.id, md`**final**`)
```

### type EditOptions

```ts
export interface EditOptions {
  noWebpage?: boolean
  invertMedia?: boolean
  media?: tl.TypeInputMedia
}
```

options of `editMessage` and `message.edit`.

- **fields:**
  - `noWebpage` (`boolean`, optional): remove the link preview.
  - `invertMedia` (`boolean`, optional): show media above the text.
  - `media` (`tl.TypeInputMedia`, optional): replace the media (photo with photo, file with file…).

Example:

```ts
await tg.editMessage('me', id, null, { media: { _: 'inputMediaUploadedPhoto', file: await tg.uploadFile(jpeg, { fileName: 'new.jpg' }) } })
```

### tg.deleteMessages(peer, ids, options?)

```ts
deleteMessages(
  peer: InputPeerLike,
  ids: number | number[],
  options?: { revoke?: boolean },
): Promise<void>
```

deletes messages and removes them from tele at once.

- **grant:** `account.write(delete)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat; for channels and supergroups it picks the chat, elsewhere ids are account-wide.
  - `ids` (`number | number[]`): one id or several.
  - `options.revoke` (`boolean`, optional): delete for everyone; default `true`. channels ignore it.
- **returns:** resolves after the server answered.
- **throws:** `TeleError` `not-granted`, `not-found`; `RpcError` (`MESSAGE_DELETE_FORBIDDEN`…).
- **notes:** `channels.deleteMessages` or `messages.deleteMessages`; the returned pts is applied locally, so tele's sequence stays in sync and `onMessageDeleted` fires (with the cached contents).

Example:

```ts
const mine = (await tg.getHistory('me', { limit: 50 })).filter((m) => m.text.startsWith('#tmp'))
await tg.deleteMessages('me', mine.map((m) => m.id))
```

### tg.forwardMessages(from, ids, to, options?)

```ts
forwardMessages(
  from: InputPeerLike,
  ids: number | number[],
  to: InputPeerLike,
  options?: ForwardOptions,
): Promise<Message[]>
```

forwards messages from one chat to another.

- **grant:** `account.write(forward)`.
- **parameters:**
  - `from` (`InputPeerLike`): the source chat.
  - `ids` (`number | number[]`): message ids in it, oldest first for a natural order.
  - `to` (`InputPeerLike`): the target chat.
  - `options` (`ForwardOptions`, optional).
- **returns:** the new messages that were found in the answer (one random id per message), in the order of `ids`; missing ones are left out.
- **throws:** `TeleError` `not-granted`, `not-found`; `RpcError` (`CHAT_FORWARDS_RESTRICTED`, `MESSAGE_ID_INVALID`…).

Example:

```ts
const copies = await tg.forwardMessages('@source', [10, 11, 12], 'me', { dropAuthor: true })
console.log(copies.length, 'saved')
```

### type ForwardOptions

```ts
export interface ForwardOptions {
  silent?: boolean
  scheduleDate?: number | Date
  topicId?: number
  dropAuthor?: boolean
  dropCaption?: boolean
  sendAs?: InputPeerLike
}
```

options of `forwardMessages` and `message.forward`.

- **fields:**
  - `silent` (`boolean`, optional): no notification.
  - `scheduleDate` (`number | Date`, optional): schedule the forward.
  - `topicId` (`number`, optional): forward into this forum topic.
  - `dropAuthor` (`boolean`, optional): send as a copy without the "forwarded from" header.
  - `dropCaption` (`boolean`, optional): drop media captions (`dropMediaCaptions`).
  - `sendAs` (`InputPeerLike`, optional): forward as a channel or the group.

Example:

```ts
await message.forward('@archive', { dropAuthor: true, dropCaption: true, silent: true })
```

### tg.setReaction(peer, id, reactions, options?)

```ts
setReaction(
  peer: InputPeerLike,
  id: number,
  reactions: Reaction | Reaction[] | null,
  options?: { big?: boolean, addToRecent?: boolean },
): Promise<void>
```

sets your reactions on a message, replacing what you had; `null` or `[]` removes yours.

- **grant:** `account.write(react)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `id` (`number`): the message id.
  - `reactions` (`Reaction | Reaction[] | null`): one, several (premium allows more than one), or none.
  - `options.big` (`boolean`, optional): the big animation.
  - `options.addToRecent` (`boolean`, optional): add to your recent reactions.
- **returns:** resolves when done.
- **throws:** `RpcError` (`REACTION_INVALID`, `REACTIONS_TOO_MANY`…); `TypeError` for a bad `customEmojiId`.

Example:

```ts
await tg.setReaction('me', id, ['🔥', { customEmojiId: '5368324170671202286' }])
await tg.setReaction('me', id, null)
```

### type Reaction

```ts
export type Reaction = string | { customEmojiId: bigint | string }
```

one reaction.

- **fields:**
  - `string`: a standard emoji (`'👍'`, `'❤'`), sent as `reactionEmoji`.
  - `{ customEmojiId }` (`bigint | string`): a custom emoji document id, sent as `reactionCustomEmoji`.

Example:

```ts
const heart: Reaction = '❤'
const custom: Reaction = { customEmojiId: 5368324170671202286n }
```

### tg.readHistory(peer, options?)

```ts
readHistory(peer: InputPeerLike, options?: { maxId?: number }): Promise<void>
```

marks a chat as read the way tele does it: its unread counter, badges and the read request follow.

- **grant:** `account.write(read)`.
- **parameters:**
  - `peer` (`InputPeerLike`): a chat tele has loaded.
  - `options.maxId` (`number`, optional): read up to this id; default 0 = everything.
- **returns:** resolves at once; tele sends the request itself.
- **throws:** `TeleError` `not-found` (`tele has no such chat loaded`); `TeleError` `not-granted`.
- **notes:** it goes through tele's own read path (`readInboxTill` / `readInbox`), not a raw `messages.readHistory` call, so tele's unread state never disagrees with the server.

Example:

```ts
for (const dialog of tg.local.dialogs()) {
  if (dialog.muted && dialog.unread > 0) await tg.readHistory(dialog.chat)
}
```

### tg.sendTyping(peer, action?, options?)

```ts
sendTyping(
  peer: InputPeerLike,
  action?: TypingAction,
  options?: { topicId?: number },
): Promise<void>
```

shows "typing…" (or another action) in a chat.

- **grant:** `account.write(typing)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `action` (`TypingAction`, optional): default `'typing'`; `'cancel'` stops it.
  - `options.topicId` (`number`, optional): the forum topic.
- **returns:** resolves when sent.
- **throws:** `TypeError: unknown typing action 'x', expected one of typing, cancel, …`; `RpcError`.
- **notes:** telegram shows an action for a few seconds; repeat it to keep it up. upload actions are sent with progress 0.

Example:

```ts
await tg.sendTyping(message, 'recordVoice')
const timer = setInterval(() => tg.sendTyping(message, 'typing'), 4000)
setTimeout(() => clearInterval(timer), 15_000)
```

### type TypingAction

```ts
export type TypingAction =
  | 'typing' | 'cancel' | 'recordVideo' | 'uploadVideo' | 'recordVoice' | 'uploadVoice'
  | 'recordRound' | 'uploadRound' | 'uploadPhoto' | 'uploadDocument' | 'chooseSticker'
  | 'chooseContact' | 'playGame'
```

the actions `sendTyping` knows, each mapped to a `sendMessage*Action`.

- **fields:**
  - `'typing'`: typing a message.
  - `'cancel'`: stop showing any action.
  - `'recordVideo'` / `'uploadVideo'`: recording / sending a video.
  - `'recordVoice'` / `'uploadVoice'`: recording / sending a voice message.
  - `'recordRound'` / `'uploadRound'`: recording / sending a round video.
  - `'uploadPhoto'`: sending a photo.
  - `'uploadDocument'`: sending a file.
  - `'chooseSticker'`: choosing a sticker.
  - `'chooseContact'`: choosing a contact.
  - `'playGame'`: playing a game.

Example:

```ts
const action: TypingAction = 'chooseSticker'
await tg.sendTyping('me', action)
```

### tg.setDraft(peer, text, options?)

```ts
setDraft(
  peer: InputPeerLike,
  text: InputText | null,
  options?: { replyTo?: number, topicId?: number, noWebpage?: boolean },
): Promise<void>
```

saves a cloud draft for a chat (`messages.saveDraft`).

- **grant:** `account.write(draft)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `text` (`InputText | null`): the draft; `null` clears it.
  - `options.replyTo` (`number`, optional): the draft replies to this message.
  - `options.topicId` (`number`, optional): the forum topic.
  - `options.noWebpage` (`boolean`, optional): no link preview.
- **returns:** resolves when saved.
- **throws:** `TypeError` for bad text; `RpcError`.
- **notes:** a chat that is open in tele doesn't refresh its field from it: use `tg.compose.set` for the open chat. read local drafts with `tg.local.draft`.

Example:

```ts
await tg.setDraft('@friend', 'remember to ask about the keys')
```

### tg.getCachedMessage(peer, id)

```ts
getCachedMessage(peer: InputPeerLike, id: number): Promise<Message | null>
```

reads a message from tele's message cache, without any request.

- **grant:** `account.read(messages)`; without it, it always resolves `null`. resolving a marked id or username needs `account.read(peers)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `id` (`number`): the message id.
- **returns:** the cached `Message` (the newest version tele saw), or `null`.
- **throws:** `TypeError: needs a chat and a message id`; `TeleError` `not-found` for the peer.
- **notes:**
  - while any script runs on the account, tele keeps the raw tl of the last 20000 messages it received (new ones, loaded history, edits, your own sends), per account, in memory only.
  - private-chat messages you sent are rebuilt from `updateShortSentMessage`, without a reply header.
  - this is where `onMessageEdited`'s `previous` and `onMessageDeleted`'s `messages` come from.

Example:

```ts
const cached = await tg.getCachedMessage('me', 1234)
console.log(cached?.text ?? 'not cached')
```

## peers

users, bots, groups and channels are "peers". scripts point at them with an `InputPeerLike` (an id, a username, `'me'`, a tl object, a `PeerInfo` or a `Message`), read what tele knows about them as a `PeerInfo`, and can change how they look in this tele with `tg.overridePeer`.

### type InputPeerLike

```ts
export type InputPeerLike =
  | bigint
  | number
  | 'me'
  | 'self'
  | (string & {})
  | tl.TypePeer
  | tl.TypeInputPeer
  | tl.TypeInputUser
  | tl.TypeInputChannel
  | tl.TypeUser
  | tl.TypeChat
  | PeerInfo
  | Message
```

everything a `peer` argument accepts, in every high-level helper.

- **fields:**
  - `bigint` / `number`: a marked id: users `> 0`, basic groups `-chatId`, channels and supergroups `-1000000000000 - channelId`. your own id means `inputPeerSelf`. other ids are looked up in tele's cache (needs `account.read(peers)`).
  - `'me'` / `'self'`: you (Saved Messages); no grant.
  - `string`: a username (`'durov'`, `'@durov'`, `'t.me/durov'`, `'https://t.me/durov'`), resolved through the cache and then `contacts.resolveUsername` (needs `account.read(peers)`). a numeric string (`'-1001234567890'`) is a marked id.
  - `tl.TypePeer` (`peerUser`, `peerChat`, `peerChannel`): turned into a marked id, then looked up in the cache (`account.read(peers)`).
  - `tl.TypeInputPeer`: used as it is; no grant.
  - `tl.TypeInputUser` / `tl.TypeInputChannel`: converted to the matching input peer; no grant.
  - `tl.TypeUser` / `tl.TypeChat` (`user`, `chat`, `chatForbidden`, `channel`, `channelForbidden`): their id and access hash; no grant.
  - `PeerInfo`: its `input`; no grant.
  - `Message`: its chat (the cached input peer, else the marked id).
- **throws:**
  - `TypeError: expected a peer: a marked id, a username, 'me', a TL peer, input peer, user or chat, a PeerInfo or a Message` for anything else.
  - `TeleError` `not-found`: `<id> isn't in tele's cache, pass an input peer or a username` for an unknown marked id; `nobody has the username @<name>` for a free username.
  - `TeleError` `not-granted` when a marked id, `Peer` or username needs `account.read(peers)` and the script doesn't have it.
- **notes:** tele only knows peers it has seen (chat list, messages, profiles, results of `tg.call`). an id from elsewhere may be unknown: pass an input peer with its access hash, or a username.

Example:

```ts
await tg.sendMessage('me', 'to myself')
await tg.sendMessage('@durov', 'hi')
await tg.sendMessage(-1001234567890n, 'to a channel tele knows')
await tg.sendMessage(message, 'to the chat of that message')
await tg.sendMessage({ _: 'inputPeerUser', userId: 777000n, accessHash: 0n }, 'raw input peer')
```

### type PeerInfo

```ts
export interface PeerInfo {
  id: bigint
  kind: 'user' | 'bot' | 'chat' | 'channel' | 'supergroup'
  name: string
  username?: string
  verified: boolean
  scam: boolean
  fake: boolean
  premium: boolean
  emojiStatus: bigint | null
  color: number
  input: tl.TypeInputPeer
}
```

what tele knows about a peer, as it shows it (overrides included). `tg.peers.get`, `message.chat`, `tg.local.dialogs()`, `OutgoingMessage.chat`, action contexts and many others return it.

- **fields:**
  - `id` (`bigint`): the marked id (users `> 0`, basic groups `-chatId`, channels `-1000000000000 - channelId`).
  - `kind` (`'user' | 'bot' | 'chat' | 'channel' | 'supergroup'`): `chat` is a basic group; `supergroup` covers megagroups and gigagroups; `channel` is a broadcast channel.
  - `name` (`string`): the shown name: first and last name for users, the title otherwise. local names and `overridePeer` names and badges are applied.
  - `username` (`string`, optional): the active username without `@`; missing if there is none.
  - `verified` (`boolean`): the verified badge.
  - `scam` (`boolean`): the scam label.
  - `fake` (`boolean`): the fake label.
  - `premium` (`boolean`): telegram premium (users).
  - `emojiStatus` (`bigint | null`): the custom emoji id of the emoji status, or `null`.
  - `color` (`number`): the name color index.
  - `input` (`tl.TypeInputPeer`): tele's own input peer with the access hash; `inputPeerSelf` for you. pass it to `tg.call`.
- **notes:** `PeerInfo`s built from the users and chats of an update or a page (the fallback of `message.chat`, and `Dialog.peer`) have only `id`, `kind`, `name`, `username` and `input`. a `PeerInfo` is a snapshot: read it again for fresh values.

Example:

```ts
const info = tg.peers.get(message.senderId ?? 0n)
if (info && (info.scam || info.fake)) await message.delete()
```

### type PeerCache

```ts
export interface PeerCache {
  get(peer: tl.TypePeer | tl.TypeInputPeer | tl.TypeInputUser | tl.TypeInputChannel | bigint | number): PeerInfo | undefined
  resolve(username: string): Promise<PeerInfo | undefined>
  readonly self: PeerInfo
}
```

the type of `tg.peers`: tele's peer cache.

- **fields:**
  - `get` (`(peer) => PeerInfo | undefined`): a cached peer, no network.
  - `resolve` (`(username) => Promise<PeerInfo | undefined>`): a username, cache first, then the server.
  - `self` (`PeerInfo`, getter): you.

Example:

```ts
const peers: PeerCache = tg.peers
console.log(peers.self.name)
```

### tg.peers.get(peer)

```ts
get(
  peer:
    | tl.TypePeer
    | tl.TypeInputPeer
    | tl.TypeInputUser
    | tl.TypeInputChannel
    | bigint
    | number,
): PeerInfo | undefined
```

looks a peer up in tele's cache, synchronously and without network.

- **grant:** `account.read(peers)`.
- **parameters:**
  - `peer`: a tl `Peer`, an input peer, input user or input channel (`inputPeerSelf` / `inputUserSelf` mean you), or a marked id as `number` or `bigint`.
- **returns:** the `PeerInfo`, or `undefined` when tele hasn't loaded that peer.
- **throws:** `TypeError: tg.peers.get needs a peer, an input peer or a marked id`; `TeleError` `not-granted`: `tg.peers.get needs the grant 'account.read(peers)'`.
- **notes:** strings are not accepted here; use `tg.peers.resolve` for usernames or `tg.resolvePeer` for everything.

Example:

```ts
const chat = tg.peers.get({ _: 'peerChannel', channelId: 1234567890n })
console.log(chat?.name ?? 'not loaded')
```

### tg.peers.resolve(username)

```ts
resolve(username: string): Promise<PeerInfo | undefined>
```

finds a user, bot, group or channel by username.

- **grant:** `account.read(peers)`.
- **parameters:**
  - `username` (`string`): with or without `@`; trimmed.
- **returns:** the `PeerInfo` from the cache, else from `contacts.resolveUsername` (the result goes into tele's cache); `undefined` for `USERNAME_NOT_OCCUPIED` and `USERNAME_INVALID`.
- **throws:** `TypeError: tg.peers.resolve needs a username`; `TeleError` `not-granted`; rejects with `RpcError` for other server errors.
- **notes:** telegram rate-limits username resolving hard (a few dozen an hour): cache ids or input peers in `tg.storage`. flood waits up to 10 s are slept through. the request skips interceptors, like `tg.call`.

Example:

```ts
const bot = await tg.peers.resolve('@BotFather')
if (bot) tg.storage.set('botfather', bot.id)
```

### tg.peers.self

```ts
readonly self: PeerInfo
```

you, as a `PeerInfo`, read from tele every time.

- **grant:** `account.read(self)`; reading the getter throws without it.
- **returns:** your `PeerInfo`, `input` is `inputPeerSelf`.
- **throws:** `TeleError` `not-granted`: `tg.peers.self needs the grant 'account.read(self)'`.
- **notes:** scripts start while tele is still building the session, so at the very start of `setup` the name may be empty; read it after an `await`.

Example:

```ts
await tg.getMe()
console.log(`hi ${tg.peers.self.name}`)
```

### tg.resolvePeer(peer)

```ts
resolvePeer(peer: InputPeerLike): Promise<tl.TypeInputPeer>
```

turns any `InputPeerLike` into a tl input peer for `tg.call`.

- **grant:** none for input objects, users, chats, `PeerInfo`s and `'me'`; `account.read(peers)` for marked ids, `Peer`s and usernames.
- **parameters:**
  - `peer` (`InputPeerLike`).
- **returns:** an `inputPeerSelf` / `inputPeerUser` / `inputPeerChat` / `inputPeerChannel` (or a `FromMessage` input peer passed in as it is).
- **throws:** see `InputPeerLike`: `TypeError`, `TeleError` `not-found`, `TeleError` `not-granted`, `RpcError` from username resolving.

Example:

```ts
const peer = await tg.resolvePeer('@telegram')
await tg.call({ _: 'messages.getHistory', peer, offsetId: 0, offsetDate: 0, addOffset: 0, limit: 1, maxId: 0, minId: 0, hash: 0n })
```

### tg.resolveUser(peer)

```ts
resolveUser(peer: InputPeerLike): Promise<tl.TypeInputUser>
```

like `resolvePeer`, but gives an input user for methods that take one.

- **grant:** as `resolvePeer`.
- **parameters:**
  - `peer` (`InputPeerLike`): a user or bot.
- **returns:** `inputUserSelf` for you, `inputUser`, or `inputUserFromMessage`.
- **throws:** `TypeError: expected a user` for groups and channels; the errors of `resolvePeer`.

Example:

```ts
const id = await tg.resolveUser('@durov')
const photos = await tg.call({ _: 'photos.getUserPhotos', userId: id, offset: 0, maxId: 0n, limit: 1 })
```

### tg.resolveChannel(peer)

```ts
resolveChannel(peer: InputPeerLike): Promise<tl.TypeInputChannel>
```

like `resolvePeer`, but gives an input channel (for `channels.*` methods).

- **grant:** as `resolvePeer`.
- **parameters:**
  - `peer` (`InputPeerLike`): a channel or supergroup.
- **returns:** `inputChannel` or `inputChannelFromMessage`.
- **throws:** `TypeError: expected a channel or a supergroup` for users and basic groups; the errors of `resolvePeer`.

Example:

```ts
const channel = await tg.resolveChannel('@telegram')
const full = await tg.call({ _: 'channels.getFullChannel', channel })
```

### tg.overridePeer(peer, override)

```ts
overridePeer(peer: InputPeerLike, override: PeerOverride | null): Promise<Disposer>
```

changes how a user, bot, group or channel looks in this tele only: name, badge, verification marks, premium star, emoji status, name color, and its place in the chat list. the server never hears about it.

- **grant:** none (it changes nothing outside this tele); resolving a marked id or username needs `account.read(peers)`.
- **parameters:**
  - `peer` (`InputPeerLike`): a peer tele has in its cache.
  - `override` (`PeerOverride | null`): the fields to force; absent fields keep the real value. `null` removes this script's override of that peer.
- **returns:** a promise of a `Disposer` that removes the override.
- **throws:** `TypeError`: `tg.overridePeer: this peer isn't in tele's cache` (input objects of unknown peers), `tg.overridePeer: an override is an object or null`, `tg.overridePeer: <field> has the wrong type`; `TeleError` `not-found` for unknown marked ids and usernames.
- **notes:**
  - one override per script per peer: calling again replaces this script's whole previous override (fields aren't merged).
  - several scripts may override one peer; they stack in registration order and later ones win per field.
  - overrides are re-applied after every server update of the peer (users, chats, full info, emoji status updates), and the real values come back exactly when removed.
  - the disposer, `overridePeer(peer, null)` and stopping the script all remove it.
  - `PeerInfo` reads show overrides, so other scripts see them too.

Example:

```ts
const off = await tg.overridePeer('@durov', { badge: '⭐', label: 'boss', color: 5 })

await tg.overridePeer(tg.selfId, { premium: true, emojiStatus: 5368324170671202286n })

const spam = tg.local.dialogs().filter((dialog) => dialog.chat.scam)
for (const dialog of spam) await tg.overridePeer(dialog.chat, { hidden: true })
```

### type PeerOverride

```ts
export interface PeerOverride {
  name?: string
  verified?: boolean
  scam?: boolean
  fake?: boolean
  premium?: boolean
  botVerification?: { icon: bigint, description?: string, bot?: bigint } | null
  emojiStatus?: bigint | null
  color?: number
  badge?: string
  hidden?: boolean
  label?: string
  preview?: string
}
```

the fields `tg.overridePeer` can force. every field is optional; a missing one keeps the real value.

- **fields:**
  - `name` (`string`, optional): the shown name everywhere. your own local names (set from tele's menu or `tg.tele.localNames`) still win over it.
  - `verified` (`boolean`, optional): the verified check.
  - `scam` (`boolean`, optional): the scam label.
  - `fake` (`boolean`, optional): the fake label.
  - `premium` (`boolean`, optional): the premium star of a user; for yourself it also turns on tele's premium-only ui (the server still decides what works).
  - `botVerification` (`{ icon, description?, bot? } | null`, optional): the third-party verification icon left of the name and its profile text. `icon` (`bigint | number`, non-zero) is a custom emoji id, `description` (`string`) the profile text, `bot` (`bigint | number`) the verifying bot. `null` hides a real one.
  - `emojiStatus` (`bigint | null`, optional): a custom emoji id as the emoji status; `null` hides a real one.
  - `color` (`number`, optional): the name color index, an integer 0 to 255, taken modulo tele's palette.
  - `badge` (`string`, optional): a short text or emoji appended after the shown name, so it shows wherever the name does: chat list, header, group bubbles, profile, mentions.
  - `hidden` (`boolean`, optional): takes the chat out of the chat list and its folders; search and links still open it.
  - `label` (`string`, optional): a word drawn right of the name in the chat list.
  - `preview` (`string`, optional): replaces the last-message line in the chat list; typing and other actions still show over it.
- **throws:** a field of the wrong type is `TypeError: tg.overridePeer: <field> has the wrong type`.

Example:

```ts
const look: PeerOverride = {
  name: 'mom',
  badge: '❤',
  botVerification: { icon: 5368324170671202286n, description: 'verified by the family' },
}
await tg.overridePeer('@my_mom', look)
```

## storage

### tg.storage

```ts
readonly storage: Storage
```

a small synchronous key-value store for this script on this account. it's encrypted with the account's data, survives reloads, restarts and turning the script off, and needs no grant.

- **grant:** none.
- **returns:** the `Storage` object.
- **notes:**
  - keys are strings of 1 to 256 characters.
  - values are `StorageValue`s: `null`, booleans, finite numbers, strings, bigints, `Uint8Array`s, arrays and plain objects of those.
  - the quota is 16 MB per script per account, counting the utf-8 bytes of keys plus serialized values.
  - storage is keyed by the script id (its file or folder name): renaming the file starts empty, deleting the script file keeps the data. the Scripts manager shows the size and can clear it.
  - writes go to disk 1 s after the last change and when the session ends.
  - every account has its own storage; scripts never see each other's.

Example:

```ts
const count = (tg.storage.get<number>('runs') ?? 0) + 1
tg.storage.set('runs', count)
console.log(`started ${count} times`)
```

### type Storage

```ts
export interface Storage {
  get<T extends StorageValue = StorageValue>(key: string): T | undefined
  set(key: string, value: StorageValue | undefined): void
  has(key: string): boolean
  delete(key: string): boolean
  keys(): string[]
  clear(): void
}
```

the type of `tg.storage`.

- **fields:**
  - `get` (`(key) => T | undefined`): a fresh copy of the value.
  - `set` (`(key, value) => void`): stores a copy; `undefined` deletes.
  - `has` (`(key) => boolean`): whether the key exists.
  - `delete` (`(key) => boolean`): removes it; whether it existed.
  - `keys` (`() => string[]`): all keys, sorted.
  - `clear` (`() => void`): removes everything.

Example:

```ts
const store: Storage = tg.storage
for (const key of store.keys()) console.log(key, store.get(key))
```

### type StorageValue

```ts
export type StorageValue =
  | null
  | boolean
  | number
  | string
  | bigint
  | Uint8Array
  | StorageValue[]
  | { [key: string]: StorageValue | undefined }
```

what `tg.storage` (and `tg.scripts` messages) can hold. values are serialized to tagged json, so bigints and bytes come back as `bigint` and `Uint8Array`.

- **fields:**
  - `null`, `boolean`, `string`: as they are.
  - `number`: finite only; `NaN` and `Infinity` throw `TypeError: tg.storage keeps only finite numbers`.
  - `bigint`: kept exactly.
  - `Uint8Array`: kept as bytes (other typed arrays and `ArrayBuffer` are not plain objects and throw).
  - arrays: `undefined` items become `null`.
  - plain objects (prototype `Object.prototype` or `null`): keys with `undefined` values are dropped; any key works, including ones starting with `\u0000`.
- **throws:**
  - `TypeError: tg.storage can't keep a function` (and `can't keep a symbol`).
  - `TypeError: tg.storage keeps only plain objects, not Map` (also `Set`, `Date`, class instances…). convert them first: `[...map]`, `date.getTime()`.
  - `TypeError: tg.storage can't keep cycles`. the same object referenced twice without a cycle is fine (it's stored twice).

Example:

```ts
tg.storage.set('state', {
  seen: [1n, 2n, 3n],
  avatar: new Uint8Array([0x89, 0x50]),
  last: Date.now(),
  note: null,
})
const state = tg.storage.get<{ seen: bigint[] }>('state')
console.log(state?.seen.includes(2n))
```

### tg.storage.get(key)

```ts
get<T extends StorageValue = StorageValue>(key: string): T | undefined
```

reads a value.

- **grant:** none.
- **parameters:**
  - `key` (`string`): 1 to 256 characters.
- **returns:** a fresh copy of the stored value (changing it changes nothing until you `set` it), or `undefined` for a missing key. `T` is only a type cast, nothing is validated.
- **throws:** `TypeError: tg.storage keys are strings of 1 to 256 characters`.

Example:

```ts
const muted = tg.storage.get<string[]>('muted') ?? []
```

### tg.storage.set(key, value)

```ts
set(key: string, value: StorageValue | undefined): void
```

writes a value, replacing the old one.

- **grant:** none.
- **parameters:**
  - `key` (`string`): 1 to 256 characters.
  - `value` (`StorageValue | undefined`): the value; `undefined` (or leaving it out) deletes the key.
- **returns:** nothing.
- **throws:** `TypeError` for a bad key or a value that can't be stored (see `StorageValue`); `RangeError: tg.storage is over its 16 MB quota` (nothing changes then).
- **notes:** the value is serialized right away, so changing the object afterwards doesn't change what's stored.

Example:

```ts
tg.storage.set('settings', { lang: 'en', strict: true })
tg.storage.set('settings', undefined)
```

### tg.storage.has(key)

```ts
has(key: string): boolean
```

whether a key exists.

- **grant:** none.
- **parameters:**
  - `key` (`string`): 1 to 256 characters.
- **returns:** `true` if it's stored (also when the stored value is `null`).
- **throws:** `TypeError` for a bad key.

Example:

```ts
if (!tg.storage.has('installed')) {
  tg.storage.set('installed', Date.now())
  tg.toast('thanks for installing')
}
```

### tg.storage.delete(key)

```ts
delete(key: string): boolean
```

removes a key.

- **grant:** none.
- **parameters:**
  - `key` (`string`): 1 to 256 characters.
- **returns:** whether it existed.
- **throws:** `TypeError` for a bad key.

Example:

```ts
if (tg.storage.delete('cache')) console.log('cache cleared')
```

### tg.storage.keys()

```ts
keys(): string[]
```

every key this script stored on this account.

- **grant:** none.
- **returns:** the keys, sorted.

Example:

```ts
const notes = tg.storage.keys().filter((key) => key.startsWith('note:'))
```

### tg.storage.clear()

```ts
clear(): void
```

removes every key of this script on this account.

- **grant:** none.
- **returns:** nothing.
- **notes:** persisted local messages live in a separate store and are not cleared.

Example:

```ts
tg.ui.registerMenuItem({ place: 'main', text: 'reset my script', onClick: () => tg.storage.clear() })
```

## files

files go through tele's own loaders and uploader: the right data center, cdn files, refreshed file references and tele's download cache all work. small files come in and out as `Uint8Array`s; big downloads go straight to disk.

### tg.downloadMedia(target, options?)

```ts
downloadMedia(
  target: Message | tl.TypeMessageMedia | tl.TypePhoto | tl.TypeDocument,
): Promise<Uint8Array>
downloadMedia(
  target: Message | tl.TypeMessageMedia | tl.TypePhoto | tl.TypeDocument,
  options: { saveTo: 'downloads' | string },
): Promise<string>
```

downloads a photo or document: into memory as bytes, or with `saveTo` onto disk.

- **grant:** `account.read(messages)`; `saveTo` with a path also needs `files.write`.
- **parameters:**
  - `target`: a `Message` (its media; the message is used as the file origin, so expired file references are refreshed through it), a `messageMediaPhoto` / `messageMediaDocument`, a `photo` or a `document`.
  - `options.saveTo` (`'downloads' | string`, optional): `'downloads'` saves into tele's download folder (Settings > Advanced > Download path, or the default; tele's per-chat folders apply) with the document's own file name; an absolute path to a folder saves under the document's name there; an absolute file path saves to exactly that file (missing folders are created). photos are saved as `photo_<id>.jpg`.
- **returns:** without `saveTo`, the file bytes (`Uint8Array`; photos are the largest jpeg the server made). with `saveTo`, the path the file was written to.
- **throws:**
  - synchronously: `TypeError: tg.downloadMedia: this message has no media`, `tg.downloadMedia needs a Message, a message media, a photo or a document`, `tg.downloadMedia: <x> is not a photo or a document`, `tg.downloadMedia: this media has no photo or document`, `tg.downloadMedia: saveTo is 'downloads' or an absolute path`, encoding errors as `tg.downloadMedia: <path>: <problem>`.
  - synchronously: `TeleError` `not-granted` (`account.read(messages)`, or `files.write` for `tg.downloadMedia({ saveTo })`); `TeleError` `quota-exceeded`: `tg.downloadMedia: the file is over 10 MB, pass { saveTo } to save it to disk`.
  - rejects with `TeleError` `network` (`tg.downloadMedia: the download failed`, `tele couldn't start the download`, `the file came back empty`, `can't write <path>`) or `timed-out`.
- **notes:**
  - files tele already downloaded come from its cache.
  - in memory: at most 10 MB (the script's memory is 256 MB in total). with `saveTo`, documents stream to disk at any size.
  - timeout: 2 minutes, or for documents saved to disk the size at 50 KB/s if that's longer.
  - it's not an `async` function: argument errors throw right away instead of rejecting.

Example:

```ts
tg.registerMessageAction({
  id: 'save',
  text: 'save to downloads',
  async onClick({ chat, messageId }) {
    const message = await tg.getMessages(chat, messageId)
    if (message?.media) tg.toast(await tg.downloadMedia(message, { saveTo: 'downloads' }))
  },
})

const bytes = await tg.downloadMedia(message)
console.log(bytes.length)
```

### tg.uploadFile(data, options?)

```ts
uploadFile(
  data: Uint8Array | string,
  options?: { fileName?: string },
): Promise<tl.TypeInputFile>
```

uploads bytes to telegram and resolves with an input file to use in `inputMediaUploadedPhoto`, `inputMediaUploadedDocument`, `photos.uploadProfilePhoto` and other methods.

- **grant:** `account.write(send)`.
- **parameters:**
  - `data` (`Uint8Array | string`): the content; a string is uploaded as utf-8.
  - `options.fileName` (`string`, optional): the name sent with the parts; default `'file'`.
- **returns:** an `inputFile { id, parts, name, md5Checksum }`; files over 10 MB are uploaded as a document upload and come back as `inputFile` up to 30 MB and `inputFileBig` (no md5) above, so pass them to methods that take big files.
- **throws:** synchronously `TypeError: tg.uploadFile needs a Uint8Array`, `tg.uploadFile: the file is empty`; `TeleError` `not-granted`; rejects with `TeleError` `network` (`tg.uploadFile: the upload failed`) or `timed-out`.
- **notes:**
  - no size cap of its own besides the script's 256 MB of memory.
  - timeout: 2 minutes or the size at 50 KB/s, whichever is longer.
  - stopping the script cancels its uploads.
  - uploaded parts stay on the server for a while; use the input file soon.

Example:

```ts
const file = await tg.uploadFile(new TextEncoder().encode('id,name\n1,tele\n'), { fileName: 'export.csv' })
await tg.sendMedia('me', {
  _: 'inputMediaUploadedDocument',
  file,
  mimeType: 'text/csv',
  attributes: [{ _: 'documentAttributeFilename', fileName: 'export.csv' }],
})
```

### tg.sendFile(peer, data, options?)

```ts
sendFile(
  peer: InputPeerLike,
  data: Uint8Array | string,
  options?: SendOptions & {
    fileName?: string
    mimeType?: string
    asPhoto?: boolean
    forceDocument?: boolean
    caption?: InputText
  },
): Promise<Message>
```

uploads bytes and sends them as a file or a photo in one step.

- **grant:** `account.write(send)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `data` (`Uint8Array | string`): the content; strings are utf-8.
  - `options.fileName` (`string`, optional): the file name shown in the chat; default `'file'`.
  - `options.mimeType` (`string`, optional): default from the extension: `jpg` / `jpeg` `image/jpeg`, `png` `image/png`, `gif` `image/gif`, `webp` `image/webp`, `mp4` `video/mp4`, `webm` `video/webm`, `mp3` `audio/mpeg`, `ogg` `audio/ogg`, `m4a` `audio/mp4`, `pdf` `application/pdf`, `zip` `application/zip`, `json` `application/json`, `txt` `text/plain`, `html` `text/html`, `csv` `text/csv`, anything else `application/octet-stream`. ignored with `asPhoto`.
  - `options.asPhoto` (`boolean`, optional): send as a compressed photo (`inputMediaUploadedPhoto`) instead of a document; the data must be an image.
  - `options.forceDocument` (`boolean`, optional): send images and videos as plain files (`forceFile`).
  - `options.caption` (`InputText`, optional): the caption.
  - the rest of `SendOptions`: `replyTo`, `topicId`, `silent`, `scheduleDate`, `sendAs`, `clearDraft`, `invertMedia`.
- **returns:** the sent `Message`.
- **throws:** the errors of `uploadFile` and `sendMedia` (`RpcError` `PHOTO_INVALID_DIMENSIONS`, `IMAGE_PROCESS_FAILED` for bad photos…).
- **notes:** documents get a `documentAttributeFilename`; no video or audio attributes are added, so telegram decides how to show the file from its mime type.

Example:

```ts
const response = await fetch('https://picsum.photos/800/600')
await tg.sendFile('me', await response.bytes(), { fileName: 'random.jpg', asPhoto: true, caption: 'a random picture' })

await tg.sendFile('me', JSON.stringify({ ok: true }, null, 2), { fileName: 'state.json', silent: true })
```

## sending

`tg.interceptSendMessage` sits in front of what you send from tele itself: the composer, replies from notifications, the share box, attachments, stickers, forwards and inline results. a held send isn't drawn until every script answered, so a script can rewrite it, change its reply, silence or schedule it, turn it into a local message, or stop it.

### tg.interceptSendMessage(filter?, middleware)

```ts
interceptSendMessage(middleware: SendMiddleware): Disposer
interceptSendMessage(filter: SendFilter, middleware: SendMiddleware): Disposer
```

registers a middleware for outgoing sends of the given kinds (text by default).

- **grant:** `interceptSendMessage`.
- **parameters:**
  - `filter` (`SendFilter`, optional): which sends reach the middleware: `text`, `peer`, `kinds`. sends that don't match are passed on as `'send'` untouched.
  - `middleware` (`SendMiddleware`): `({ message }) => 'send' | 'drop' | 'local'`, may be async. change `message` in place before answering `'send'`.
- **returns:** a `Disposer` that removes the middleware.
- **throws:** `TypeError: tg.interceptSendMessage(filter?, function)`; `TypeError: tg.interceptSendMessage: kinds are 'text', 'files', 'document', 'photo', 'forward', 'inline' or 'all'`; `TeleError` `not-granted`: `tg.interceptSendMessage needs the grant 'interceptSendMessage'`.
- **notes:**
  - order: scripts in folder order, each script's middlewares in registration order. changes carry over to the next middleware; the first `'drop'` wins and nothing after it runs.
  - per-chat queue: while a send is held, later sends to the same chat wait behind it, so they keep their order. other chats aren't delayed.
  - budgets: 200 ms for each synchronous turn, 60 s in total. a throw, a rejection, another return value or running over 60 s is a fault (`took longer than 60 s, the message was not sent`) and the message is not sent.
  - `'drop'`: the message is gone (for text, the field was already cleared). `'local'`: text only; the send is dropped and the (possibly edited) text becomes a local message in that chat, replying to the same message. `'local'` for any other kind is a fault and nothing is sent. creating the local message reads the chat with `tg.peers.get`, so `'local'` also needs `account.read(peers)`.
  - after the chain, tele continues as usual with the changed message (its own processing, the local copy, the request); `interceptRpc` middlewares then see the actual request.
  - secret chats are never intercepted. `tg.sendMessage` and other script sends never come here.
  - when the script stops while holding a send, the send goes on as it was.

Example:

```ts
tg.interceptSendMessage({ text: /^!shout /, peer: 'user' }, ({ message }) => {
  const text = typeof message.text === 'string' ? message.text : message.text.text
  message.text = text.slice(7).toUpperCase()
  return 'send'
})

tg.interceptSendMessage({ kinds: ['files', 'photo'], peer: 'channel' }, ({ message }) => {
  message.silent = true
  return 'send'
})

tg.interceptSendMessage({ text: /^\/note / }, () => 'local')
```

### type SendMiddleware

```ts
export type SendMiddleware = (context: {
  message: OutgoingMessage
}) => SendVerdict | Promise<SendVerdict>
```

the function `interceptSendMessage` takes.

- **fields:**
  - `context.message` (`OutgoingMessage`): the send, mutable.
  - return (`SendVerdict | Promise<SendVerdict>`): `'send'`, `'drop'` or `'local'`.

Example:

```ts
const noSwearing: SendMiddleware = ({ message }) => {
  const text = typeof message.text === 'string' ? message.text : message.text.text
  return /darn/i.test(text) ? 'drop' : 'send'
}
tg.interceptSendMessage(noSwearing)
```

### type SendFilter

```ts
export interface SendFilter {
  text?: RegExp | boolean
  peer?: SendPeerFilter | SendPeerFilter[]
  kinds?: SendKind | SendKind[] | 'all'
}
```

decides which sends a middleware sees. every given field must match.

- **fields:**
  - `text` (`RegExp | boolean`, optional): a regexp tested on the text or caption (`lastIndex` is reset first); `true` only sends with text, `false` only sends without.
  - `peer` (`SendPeerFilter | SendPeerFilter[]`, optional): the target chat, by marked id or kind; an array matches any of them.
  - `kinds` (`SendKind | SendKind[] | 'all'`, optional): which kinds; default `'text'`, so older middlewares only see text.

Example:

```ts
const filter: SendFilter = { text: true, peer: ['group', -1001234567890n], kinds: 'all' }
tg.interceptSendMessage(filter, ({ message }) => (console.log(message.kind), 'send'))
```

### type SendPeerFilter

```ts
export type SendPeerFilter = bigint | 'user' | 'group' | 'channel'
```

one entry of `SendFilter.peer`.

- **fields:**
  - `bigint`: a marked chat id (a `number` works at runtime too).
  - `'user'`: private chats with users and bots, Saved Messages included.
  - `'group'`: basic groups and supergroups.
  - `'channel'`: broadcast channels.

Example:

```ts
tg.interceptSendMessage({ peer: tg.selfId }, ({ message }) => {
  message.silent = true
  return 'send'
})
```

### type SendKind

```ts
export type SendKind = 'text' | 'files' | 'document' | 'photo' | 'forward' | 'inline'
```

what kind of send an `OutgoingMessage` is.

- **fields:**
  - `'text'`: a text message.
  - `'files'`: new photos, videos, files or an album from disk or the clipboard.
  - `'document'`: an existing document: a sticker, a gif, a saved file.
  - `'photo'`: an existing photo sent again.
  - `'forward'`: forwarded messages.
  - `'inline'`: a chosen inline bot result.

Example:

```ts
const kinds: SendKind[] = ['document', 'inline']
tg.interceptSendMessage({ kinds }, ({ message }) => (message.silent = true, 'send'))
```

### send kind: text

```ts
// message.kind === 'text'
{ kind: 'text', text, chatId, chat, replyTo, silent, scheduleDate }
```

everything that goes through tele's text send: the composer, quick replies from notifications, the share box comment, and the text a script command returns.

- **notes:**
  - `text` is the message; change it to rewrite what's sent.
  - a forward with a comment sends the comment as a separate `'text'` send.
  - the only kind that can answer `'local'`.

Example:

```ts
tg.interceptSendMessage(({ message }) => {
  const text = typeof message.text === 'string' ? message.text : message.text.text
  if (text.endsWith(' /s')) message.text = md`${text.slice(0, -3)} __(sarcasm)__`
  return 'send'
})
```

### send kind: files

```ts
// message.kind === 'files'
{ kind: 'files', files: [{ name, size, type }], text, chatId, chat, replyTo, silent, scheduleDate }
```

new files sent from tele: photos, videos, documents, music and albums.

- **notes:**
  - `files` lists each file: `name`, `size` in bytes, `type` `'photo' | 'video' | 'music' | 'file'` (how tele is going to send it).
  - `text` is the caption of the first captioned file, or of the first file when none has one. changing it writes back to that file only; the others keep their own captions.
  - the file contents can't be changed.

Example:

```ts
tg.interceptSendMessage({ kinds: 'files' }, ({ message }) => {
  const big = message.files?.some((file) => file.size > 50 * 1024 * 1024)
  return big ? 'drop' : 'send'
})
```

### send kind: document

```ts
// message.kind === 'document'
{ kind: 'document', document: { id, name, mimeType, size, sticker, gif }, text, chatId, chat, replyTo, silent, scheduleDate }
```

an existing document sent again: stickers, gifs, saved files from the panels.

- **notes:**
  - `document.id` (`bigint`), `name`, `mimeType`, `size` (bytes), `sticker` and `gif` describe it.
  - `text` is its caption.

Example:

```ts
tg.interceptSendMessage({ kinds: 'document', peer: 'group' }, ({ message }) =>
  message.document?.sticker ? 'drop' : 'send')
```

### send kind: photo

```ts
// message.kind === 'photo'
{ kind: 'photo', photo: { id }, text, chatId, chat, replyTo, silent, scheduleDate }
```

an existing photo sent again.

- **notes:** `photo.id` (`bigint`) is the photo id; `text` is its caption.

Example:

```ts
tg.interceptSendMessage({ kinds: 'photo' }, ({ message }) => {
  console.log('resending photo', message.photo?.id)
  return 'send'
})
```

### send kind: forward

```ts
// message.kind === 'forward'
{ kind: 'forward', forward: { messages: [{ chatId, id }] }, text, chatId, chat, replyTo, silent, scheduleDate }
```

messages forwarded from tele (everything that goes through tele's forward path, like the forward box).

- **notes:**
  - `forward.messages` lists the source messages by chat (`chatId`, marked) and `id`.
  - the send is held as message ids and re-resolved when it goes on: messages deleted in the meantime are skipped.
  - a comment typed with the forward arrives as a separate `'text'` send.

Example:

```ts
tg.interceptSendMessage({ kinds: 'forward' }, ({ message }) => {
  const fromSecret = message.forward?.messages.some((item) => item.chatId === -1001234567890n)
  return fromSecret ? 'drop' : 'send'
})
```

### send kind: inline

```ts
// message.kind === 'inline'
{ kind: 'inline', inline: { botId, queryId, id, title, description }, document?, text, chatId, chat, replyTo, silent, scheduleDate }
```

a chosen inline bot result: from the inline panel, a web app's `sendInlineQuery` answer, story replies, scheduled and shortcut messages.

- **notes:**
  - `inline.botId` (`bigint`, marked), `queryId` (`bigint`), `id` (the result id), `title` and `description` describe the result; `document` is set when the result is a file, gif or sticker.
  - the text can't be changed; `replyTo`, `silent` and `scheduleDate` can.
  - a dropped send reports failure to a web app that asked for it.

Example:

```ts
tg.interceptSendMessage({ kinds: 'inline' }, ({ message }) => {
  message.scheduleDate = Math.floor(Date.now() / 1000) + 60
  return 'send'
})
```

### type SendVerdict

```ts
export type SendVerdict = 'send' | 'drop' | 'local'
```

the answer of a send middleware.

- **fields:**
  - `'send'`: go on, with your changes.
  - `'drop'`: don't send; nothing after this middleware runs.
  - `'local'`: text only: don't send, show it as a local message instead (needs `account.read(peers)`).

Example:

```ts
const verdict: SendVerdict = 'local'
```

### type OutgoingMessage

```ts
export interface OutgoingMessage {
  readonly kind: SendKind
  get text(): InputText
  set text(value: InputText)
  readonly chatId: bigint
  readonly chat: PeerInfo
  replyTo: number | null
  silent: boolean
  scheduleDate: number | null
  readonly files?: readonly { name: string, size: number, type: 'photo' | 'video' | 'music' | 'file' }[]
  readonly document?: { id: bigint, name: string, mimeType: string, size: number, sticker: boolean, gif: boolean }
  readonly photo?: { id: bigint }
  readonly forward?: { messages: readonly { chatId: bigint, id: number }[] }
  readonly inline?: { botId: bigint, queryId: bigint, id: string, title: string, description: string }
}
```

a send held by `interceptSendMessage`. the writable fields are read back after `'send'`.

- **fields:**
  - `kind` (`SendKind`): what is being sent.
  - `text` (`InputText`): comes as `{ text, entities }`; assign a string or `{ text, entities }` (`md` / `html` work). the text, or the caption for media kinds; can't be changed for `'inline'`. wrong entities are a fault.
  - `chatId` (`bigint`): the target chat's marked id.
  - `chat` (`PeerInfo`): the target chat.
  - `replyTo` (`number | null`): the replied message id in this chat, or `null`. set a number to reply, `null` to drop the reply. left alone, a reply to another chat or with a quote stays as it was.
  - `silent` (`boolean`): send without a notification.
  - `scheduleDate` (`number | null`): unix seconds to schedule it, or `null` to send now. only a number is read (a `Date` isn't); a scheduled send goes to the scheduled messages.
  - `files` (optional): for `'files'`: `name`, `size` (bytes) and `type` of each file.
  - `document` (optional): for `'document'` and file-like `'inline'` results: `id`, `name`, `mimeType`, `size`, `sticker`, `gif`.
  - `photo` (optional): for `'photo'`: `id`.
  - `forward` (optional): for `'forward'`: `messages`, each `{ chatId, id }`.
  - `inline` (optional): for `'inline'`: `botId` (marked), `queryId`, `id`, `title`, `description`.

Example:

```ts
tg.interceptSendMessage(({ message }) => {
  if (message.chat.kind === 'user' && new Date().getHours() >= 23) {
    const morning = new Date()
    morning.setDate(morning.getDate() + 1)
    morning.setHours(9, 0, 0, 0)
    message.scheduleDate = Math.floor(morning.getTime() / 1000)
  }
  return 'send'
})
```

## local messages and decorations

scripts can put messages into chats that exist only in this tele, and change how real messages look, without touching the server. both disappear when the script stops (persisted local messages come back when it starts again).

### tg.addLocalMessage(chat, options?)

```ts
addLocalMessage(chat: InputPeerLike, options?: LocalMessageOptions): Promise<LocalMessage>
```

adds a local ("ghost") message to a chat: a real-looking message or service line, from anyone, with any media, that only this tele shows.

- **grant:** none for the message itself (it changes nothing outside this tele), but the chat is looked up with `tg.peers.get`, so the call needs `account.read(peers)`.
- **parameters:**
  - `chat` (`InputPeerLike`): the chat to put it in.
  - `options` (`LocalMessageOptions`, optional): text, author, date, reply, media, action, opacity, persistence and raw tl fields.
- **returns:** the `LocalMessage`.
- **throws:** `TypeError`: `local message: <path>: <problem>` for fields that don't encode (`raw: { date: 'soon' }`), `a local message can't be messageEmpty`, `the message has no chat`, `opacity is a number from 0 to 1` (a non-number opacity), `persisted local messages are over the 16 MB quota`; the peer errors of `InputPeerLike`; `TeleError` `not-granted` without `account.read(peers)`.
- **notes:**
  - defaults: a message from you (`out: true`, `fromId` you), dated now. in a broadcast channel it's a post (`post: true`, no `fromId`). `out: false` without `from` means from the chat itself.
  - it's placed by `date` among the loaded messages and re-placed whenever tele loads history, like tele's own sending messages. no unread count, no notification; the chat list preview shows it when it's the newest.
  - its `id` is 0 for scripts; its `key` identifies it.
  - persisted ones are stored encrypted per script per account (16 MB of tl), restored before `setup` runs, and hidden while the script is off.
  - deleting it with tele's own delete removes it (and its stored copy); clearing the chat history removes local messages too.
  - opacity is clamped to 0..1.

Example:

```ts
await tg.addLocalMessage('me', { text: md`**reminder** set for 18:00`, opacity: 1 })

await tg.addLocalMessage('@durov', {
  from: '@durov',
  text: 'this never happened',
  date: new Date(Date.now() - 3_600_000),
  persist: true,
})

await tg.addLocalMessage('me', { action: { _: 'messageActionCustomAction', message: 'the script started' } })
```

### type LocalMessageOptions

```ts
export interface LocalMessageOptions {
  text?: InputText
  from?: InputPeerLike
  out?: boolean
  date?: Date | number
  replyTo?: number | null
  media?: tl.TypeMessageMedia | Message
  action?: tl.TypeMessageAction
  opacity?: number
  persist?: boolean
  raw?: Partial<Omit<tl.RawMessage, '_'>> & Partial<Omit<tl.RawMessageService, '_'>>
}
```

options of `addLocalMessage` (and, without `persist`, of `LocalMessage.edit`).

- **fields:**
  - `text` (`InputText`, optional): the text or caption; default empty.
  - `from` (`InputPeerLike`, optional): the author, any peer tele can resolve; sets `fromId`, and `out` to whether it's you.
  - `out` (`boolean`, optional): drawn as outgoing (right side, checks); overrides what `from` set.
  - `date` (`Date | number`, optional): a `Date` or unix seconds; default now.
  - `replyTo` (`number | null`, optional): reply to this message id in the chat; `null` removes a reply (in `edit`).
  - `media` (`tl.TypeMessageMedia | Message`, optional): tl media, or a `Message` whose media is copied: real photos and documents stay viewable and downloadable.
  - `action` (`tl.TypeMessageAction`, optional): makes a service line (`messageService`) instead of a message; text and media are ignored then.
  - `opacity` (`number`, optional): 0..1, default 0.5; 1 makes it look like any other message.
  - `persist` (`boolean`, optional): keep it across restarts; default `false`.
  - `raw` (optional): any `message` / `messageService` fields, merged last: `fwdFrom`, `replyMarkup`, `views`, `reactions`, `editDate`, `viaBotId`, `entities`… fields set to `undefined` or `null` are removed.

Example:

```ts
const original = await tg.getMessages('me', 42)
await tg.addLocalMessage('me', {
  media: original ?? undefined,
  text: 'a copy of #42',
  raw: { views: 1_000_000, fwdFrom: { _: 'messageFwdHeader', date: 0, fromName: 'someone famous' } },
})
```

### type LocalMessage

```ts
export interface LocalMessage {
  readonly key: number
  readonly chatId: bigint | null
  readonly persisted: boolean
  readonly opacity: number
  readonly raw: tl.RawMessage | tl.RawMessageService
  readonly message: Message
  edit(changes: Omit<LocalMessageOptions, 'persist'>): Promise<LocalMessage>
  remove(): boolean
}
```

a local message this script added.

- **fields:**
  - `key` (`number`): its stable id, the same after restarts for persisted ones; store it to find the message again in `tg.localMessages()`.
  - `chatId` (`bigint | null`): the chat's marked id.
  - `persisted` (`boolean`): whether it survives restarts.
  - `opacity` (`number`): its current opacity.
  - `raw` (`tl.RawMessage | tl.RawMessageService`): the tl object as given to tele.
  - `message` (`Message`): a `Message` over `raw` (its `id` is 0, so the server helpers like `reply` don't apply).
  - `edit` (`(changes) => Promise<LocalMessage>`): see `localMessage.edit`.
  - `remove` (`() => boolean`): see `localMessage.remove`.
- **notes:** it also has `toJSON()`, giving `{ key, chatId, persisted, opacity, message }`.

Example:

```ts
const note = await tg.addLocalMessage('me', { text: 'loading…' })
tg.storage.set('note', note.key)
```

### localMessage.edit(changes)

```ts
edit(changes: Omit<LocalMessageOptions, 'persist'>): Promise<LocalMessage>
```

changes a local message; the given fields are merged over its current ones and tele redraws it.

- **grant:** as `addLocalMessage` for `from` (resolving peers).
- **parameters:**
  - `changes`: any `LocalMessageOptions` except `persist`; `replyTo: null` removes the reply, `opacity` changes the opacity.
- **returns:** the same `LocalMessage`, updated.
- **throws:** `TypeError` as `addLocalMessage`; `TypeError: this local message was removed`.
- **notes:** if a persisted message grows over the 16 MB store, the edit is shown but not saved, and a warning is logged.

Example:

```ts
const status = await tg.addLocalMessage('me', { text: 'checking…', opacity: 0.6 })
const ok = await fetch('https://example.com').then((r) => r.ok, () => false)
await status.edit({ text: ok ? 'example.com is up' : 'example.com is down', opacity: 1 })
```

### localMessage.remove()

```ts
remove(): boolean
```

removes the local message from its chat (and from the store if persisted).

- **grant:** none.
- **returns:** whether it still existed.

Example:

```ts
for (const local of tg.localMessages()) local.remove()
```

### tg.localMessages()

```ts
localMessages(): LocalMessage[]
```

this script's local messages on this account, persisted ones restored at start included.

- **grant:** none.
- **returns:** `LocalMessage` objects, fresh each call.
- **notes:** messages the user deleted or that tele dropped with a cleared history aren't listed.

Example:

```ts
const key = tg.storage.get<number>('note')
const note = tg.localMessages().find((local) => local.key === key)
await note?.edit({ text: `still here at ${new Date().toLocaleTimeString()}` })
```

### tg.decorateMessages(decorator)

```ts
decorateMessages(
  decorator: (
    message: Message,
  ) => MessageDecoration | null | void | Promise<MessageDecoration | null | void>,
): Disposer
```

changes how real messages look in this tele: shown text, a footer, opacity, hiding, a badge. the decorator decides per message.

- **grant:** `account.read(messages)`.
- **parameters:**
  - `decorator` (`(message) => MessageDecoration | null | void`, may be async): gets each message as a `Message`; returns its decoration, or `null` / nothing for none.
- **returns:** a `Disposer` that removes this decorator's decorations everywhere.
- **throws:** `TypeError: tg.decorateMessages(function)`; `TeleError` `not-granted`: `tg.decorateMessages needs the grant 'account.read(messages)'`.
- **notes:**
  - runs once for every message version tele receives (new messages, loaded history, edits) and, right after registering, over every message tele currently has loaded.
  - async decorators are fine (e.g. translating through `fetch`); the decoration shows when the promise resolves.
  - the synchronous part has 200 ms. a throw, a rejection or a wrong shape is a fault (counted toward the switch-off).
  - the `Message` it gets has only tele's cache for `chat` and `sender`.
  - each decorator is its own layer; with several decorators or scripts, later registrations win per field.

Example:

```ts
tg.decorateMessages((message) => {
  if (/password|token/i.test(message.text)) {
    return { text: md`||${message.text}||`, badge: 'secret' }
  }
  if (message.sender?.kind === 'bot' && message.chat?.kind === 'supergroup') {
    return { opacity: 0.4 }
  }
  return null
})
```

### tg.decorateMessage(peer, id, decoration)

```ts
decorateMessage(
  peer: InputPeerLike,
  id: number,
  decoration: MessageDecoration | null,
): Promise<Disposer>
```

decorates one message by id, without a decorator function.

- **grant:** none (resolving marked ids and usernames needs `account.read(peers)`).
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `id` (`number`): the message id.
  - `decoration` (`MessageDecoration | null`): the decoration; `null` removes this script's explicit decoration of that message.
- **returns:** a promise of a `Disposer` that removes it.
- **throws:** `TypeError: needs a chat and a message id`; `TypeError: tg.decorateMessage: <problem>` for a bad decoration (`a decoration is an object`, `text is a string or { text, entities }`, `footer.entities are wrong: …`, `opacity is a number from 0 to 1`, `hidden is a boolean`, `badge is a string`); the peer errors of `InputPeerLike`.
- **notes:** one explicit decoration per script per message: calling again replaces it. it works for messages tele hasn't loaded yet and applies when they appear.

Example:

```ts
const sent = await tg.sendMessage('me', 'the real text')
const undo = await tg.decorateMessage('me', sent.id, { text: 'what you see', footer: 'decorated locally', badge: '✎' })
setTimeout(undo, 10_000)
```

### type MessageDecoration

```ts
export interface MessageDecoration {
  text?: InputText
  footer?: InputText
  opacity?: number
  hidden?: boolean
  badge?: string
}
```

how a message should look. every field is optional; missing ones keep the real look.

- **fields:**
  - `text` (`InputText`, optional): shown instead of the real text in the bubble; entities, `md` and `html` work.
  - `footer` (`InputText`, optional): added under the text as a quote block. it's part of the bubble's text, so selecting all text selects it too.
  - `opacity` (`number`, optional): 0..1, multiplied with a local message's own opacity.
  - `hidden` (`boolean`, optional): the message leaves the chat view; it's still there for the server and for search.
  - `badge` (`string`, optional): a short text shown before the time, after a channel signature.
- **notes:** decorations live in layers (each decorator, plus each script's explicit ones); later layers win per field. disposing, `null`, or stopping the script removes a layer and the real look comes back.

Example:

```ts
const look: MessageDecoration = { footer: md`__translated from german__`, badge: 'de→en' }
```

### the message cache

```ts
getCachedMessage(peer: InputPeerLike, id: number): Promise<Message | null>
```

while any script runs on an account, tele keeps the raw tl of the last 20000 messages it received for that account, in memory. it feeds `tg.getCachedMessage`, `onMessageEdited`'s `previous`, `onMessageDeleted`'s `messages`, the first run of `decorateMessages` and the `message` of notification interceptors.

- **grant:** reading it needs `account.read(messages)`; without it every lookup is `null`.
- **notes:**
  - it holds new messages, loaded history, edits (the newest version wins) and your own sends; private-chat sends are rebuilt from `updateShortSentMessage` without a reply header.
  - nothing is fetched to fill it, and it's gone when tele quits or the last script stops.
  - listeners run before tele applies an update, so in edit and delete events the cache still has the old version.

Example:

```ts
tg.onMessageDeleted(async ({ chatId, ids }) => {
  for (const id of ids) {
    const old = chatId === null ? null : await tg.getCachedMessage(chatId, id)
    if (old) console.log('deleted:', old.text)
  }
})
```

## local data and settings

tele's own state, read without network: the chat list as tele has it, unread counters, folders, drafts, tele's settings, and tele's per-person features.

### tg.local

```ts
readonly local: Local
```

reads tele's local state. nothing here sends requests.

- **grant:** per method: `account.read(dialogs)` for `dialogs`, `unread`, `folders`; `account.read(draft)` for `draft`; none for `loaded`.
- **returns:** the `Local` object (frozen).

Example:

```ts
if (tg.local.loaded()) console.log(tg.local.unread().badge, 'on the badge')
```

### type Local

```ts
export interface Local {
  dialogs(options?: { folder?: 'main' | 'archive' | number, limit?: number }): LocalDialog[]
  unread(): UnreadSummary
  folders(): LocalFolder[]
  loaded(): boolean
  draft(chat: InputPeerLike): Promise<Required<TextWithEntities> | undefined>
}
```

the type of `tg.local`.

- **fields:**
  - `dialogs` (`(options?) => LocalDialog[]`): the chat list.
  - `unread` (`() => UnreadSummary`): counters.
  - `folders` (`() => LocalFolder[]`): chat folders.
  - `loaded` (`() => boolean`): whether the main list is complete.
  - `draft` (`(chat) => Promise<…>`): a chat's local draft.

Example:

```ts
const local: Local = tg.local
console.log(local.folders().length, 'folders')
```

### tg.local.dialogs(options?)

```ts
dialogs(options?: { folder?: 'main' | 'archive' | number, limit?: number }): LocalDialog[]
```

the chat list as tele shows it, in order (pinned first), with counters.

- **grant:** `account.read(dialogs)`.
- **parameters:**
  - `options.folder` (`'main' | 'archive' | number`, optional): `'main'` (default), `'archive'`, or a folder id from `tg.local.folders()`.
  - `options.limit` (`number`, optional): at most this many; default all.
- **returns:** `LocalDialog[]`.
- **throws:** `TypeError: tg.local.dialogs: folder is 'main', 'archive' or a folder id from tg.local.folders(), limit is a number`; `TeleError` `not-granted`: `tg.local.dialogs needs the grant 'account.read(dialogs)'`.
- **notes:** only chats tele has loaded into the list: right after start it may be empty or partial; `loaded()` says when the main list is complete. synchronous.

Example:

```ts
const unreadPeople = tg.local.dialogs()
  .filter((dialog) => dialog.chat.kind === 'user' && dialog.unread > 0 && !dialog.muted)
  .map((dialog) => dialog.chat.name)
```

### type LocalDialog

```ts
export interface LocalDialog {
  chat: PeerInfo
  unread: number
  unreadMark: boolean
  mentions: number
  reactions: number
  muted: boolean
  pinned: boolean
  archived: boolean
  date: number
  lastMessageId?: number
}
```

one row of `tg.local.dialogs()`.

- **fields:**
  - `chat` (`PeerInfo`): the chat.
  - `unread` (`number`): unread messages.
  - `unreadMark` (`boolean`): marked as unread by hand.
  - `mentions` (`number`): unread mentions.
  - `reactions` (`number`): unread reactions.
  - `muted` (`boolean`): notifications muted.
  - `pinned` (`boolean`): pinned in the list you asked for.
  - `archived` (`boolean`): in the archive.
  - `date` (`number`): the chat-list time in unix seconds (the last message, or a draft).
  - `lastMessageId` (`number`, optional): the message the list previews; missing when there is none.

Example:

```ts
const stale = tg.local.dialogs().filter((d) => d.date < Date.now() / 1000 - 365 * 86_400)
```

### tg.local.unread()

```ts
unread(): UnreadSummary
```

the unread totals of the main list and the number on tele's icon.

- **grant:** `account.read(dialogs)`.
- **returns:** an `UnreadSummary`.
- **throws:** `TeleError` `not-granted`: `tg.local.unread needs the grant 'account.read(dialogs)'`.

Example:

```ts
const { badge, mentions } = tg.local.unread()
if (mentions > 0) tg.toast(`${mentions} mentions, ${badge} unread`)
```

### type UnreadSummary

```ts
export interface UnreadSummary {
  messages: number
  messagesMuted: number
  chats: number
  chatsMuted: number
  marks: number
  mentions: number
  reactions: number
  badge: number
  badgeMuted: boolean
}
```

what `tg.local.unread()` returns.

- **fields:**
  - `messages` (`number`): unread messages.
  - `messagesMuted` (`number`): of those, in muted chats.
  - `chats` (`number`): chats with unread messages.
  - `chatsMuted` (`number`): of those, muted.
  - `marks` (`number`): chats marked as unread.
  - `mentions` (`number`): unread mentions.
  - `reactions` (`number`): unread reactions.
  - `badge` (`number`): the number on tele's icon (it follows tele's counter settings).
  - `badgeMuted` (`boolean`): whether the badge is drawn as muted.

Example:

```ts
const summary: UnreadSummary = tg.local.unread()
console.log(summary.chats - summary.chatsMuted, 'chats need you')
```

### tg.local.folders()

```ts
folders(): LocalFolder[]
```

the user's chat folders (without "all chats"), with the chats in them.

- **grant:** `account.read(dialogs)`.
- **returns:** `LocalFolder[]` in tele's order.
- **throws:** `TeleError` `not-granted`: `tg.local.folders needs the grant 'account.read(dialogs)'`.

Example:

```ts
const work = tg.local.folders().find((folder) => folder.title === 'work')
if (work) console.log(tg.local.dialogs({ folder: work.id }).length, 'work chats')
```

### type LocalFolder

```ts
export interface LocalFolder {
  id: number
  title: string
  emoji: string
  chats: bigint[]
}
```

one chat folder.

- **fields:**
  - `id` (`number`): the folder id; pass it as `folder` to `tg.local.dialogs`.
  - `title` (`string`): the folder name.
  - `emoji` (`string`): its icon emoji, or `''`.
  - `chats` (`bigint[]`): marked ids of the chats tele has loaded in it.

Example:

```ts
const inFolders = new Set(tg.local.folders().flatMap((folder) => folder.chats))
```

### tg.local.loaded()

```ts
loaded(): boolean
```

whether tele has loaded the whole main chat list.

- **grant:** none.
- **returns:** `true` once the main list is complete; until then `dialogs()` may be partial.

Example:

```ts
const waitForList = async () => {
  while (!tg.local.loaded()) await new Promise<void>((done) => setTimeout(done, 1000))
}
await waitForList()
```

### tg.local.draft(chat)

```ts
draft(chat: InputPeerLike): Promise<Required<TextWithEntities> | undefined>
```

a chat's local draft: what's in its message field in tele.

- **grant:** `account.read(draft)`; resolving marked ids and usernames needs `account.read(peers)`.
- **parameters:**
  - `chat` (`InputPeerLike`): the chat.
- **returns:** `{ text, entities }`, or `undefined` when the chat has no draft or tele hasn't loaded it.
- **throws:** `TeleError` `not-granted`: `tg.local.draft needs the grant 'account.read(draft)'`; `TypeError: tg.local.draft needs a peer, an input peer or a marked id`.
- **notes:** the main draft of the chat (not topic drafts). to write the draft of the open chat use `tg.compose.set`; of another chat, `tg.setDraft`.

Example:

```ts
const draft = await tg.local.draft('me')
if (draft) console.log('you were writing:', draft.text)
```

### tg.options

```ts
readonly options: Options
```

every tele setting the settings export knows (the `tele-*` ids, about 250): toggles, choices and texts.

- **grant:** none to read; `options` to change.
- **returns:** the `Options` object (frozen).

Example:

```ts
const ghost = tg.options.list().filter((option) => option.id.includes('ghost'))
console.log(ghost.map((option) => `${option.id} = ${option.value}`))
```

### type Options

```ts
export interface Options {
  list(): OptionInfo[]
  get(id: string): OptionInfo | undefined
  set(id: string, value: boolean | string): { restart: boolean }
  onChange(callback: (change: OptionChange) => void): Disposer
  onChange(id: string, callback: (change: OptionChange) => void): Disposer
}
```

the type of `tg.options`.

- **fields:**
  - `list` (`() => OptionInfo[]`): all settings.
  - `get` (`(id) => OptionInfo | undefined`): one setting.
  - `set` (`(id, value) => { restart }`): changes one.
  - `onChange` (`(id?, callback) => Disposer`): watches changes.

Example:

```ts
const options: Options = tg.options
```

### tg.options.list()

```ts
list(): OptionInfo[]
```

every setting with its current value.

- **grant:** none.
- **returns:** `OptionInfo[]`, fresh each call.

Example:

```ts
const needRestart = tg.options.list().filter((option) => option.restartRequired).map((option) => option.id)
```

### tg.options.get(id)

```ts
get(id: string): OptionInfo | undefined
```

one setting by id.

- **grant:** none.
- **parameters:**
  - `id` (`string`): a `tele-*` id from `list()`.
- **returns:** its `OptionInfo`, or `undefined` for an unknown id (or a non-string).

Example:

```ts
const option = tg.options.get('tele-ghost')
console.log(option?.name, option?.value)
```

### tg.options.set(id, value)

```ts
set(id: string, value: boolean | string): { restart: boolean }
```

changes a setting through tele's settings importer, validated exactly like an imported settings file.

- **grant:** `options` (it can change anything, including ghost mode, link rewrites and the checkmark server).
- **parameters:**
  - `id` (`string`): the setting id.
  - `value` (`boolean | string`): a boolean for toggles, one of `choices` for choices, a string in the setting's own format for texts (titles, menu layouts, link rewrites, server addresses, lists).
- **returns:** `{ restart }`: `true` when the change applies after a restart.
- **throws:** `TeleError` `not-granted`: `tg.options.set needs the grant 'options'`; `TypeError`: `tg.options.set(id, value)`, `tg.options.set: the value is a boolean or a string`, and `tg.options.set: <reason>` with the importer's reason (`Expected on or off.`, `Unknown value "x".`, `Unknown setting x.`).
- **notes:** icons and backgrounds can't be set this way (they need image data). the change fires `onChange` for every script, this one included.

Example:

```ts
const { restart } = tg.options.set('tele-ghost', true)
if (restart) tg.toast('restart tele to apply')
```

### tg.options.onChange(id?, callback)

```ts
onChange(callback: (change: OptionChange) => void): Disposer
onChange(id: string, callback: (change: OptionChange) => void): Disposer
```

calls `callback` after a setting changes, from tele's settings, the importer or any script.

- **grant:** none.
- **parameters:**
  - `id` (`string`, optional): only this setting.
  - `callback` (`(change: OptionChange) => void`): gets the id and the new value.
- **returns:** a `Disposer`.
- **throws:** `TypeError: tg.options.onChange(id?, function)` / `tg.options.onChange(function)`.

Example:

```ts
tg.options.onChange('tele-ghost', ({ value }) => {
  tg.toast(value ? 'ghost mode on' : 'ghost mode off')
})
```

### type OptionInfo

```ts
export interface OptionInfo {
  id: string
  name: string
  description: string
  kind: 'toggle' | 'choice' | 'text'
  choices?: string[]
  value: boolean | string
  restartRequired: boolean
  group: 'settings' | 'people' | 'device'
}
```

one tele setting.

- **fields:**
  - `id` (`string`): the stable id, e.g. `'tele-ghost'`.
  - `name` (`string`): the name shown in tele's settings.
  - `description` (`string`): its explanation.
  - `kind` (`'toggle' | 'choice' | 'text'`): on/off, one of a list, or free text in the setting's format.
  - `choices` (`string[]`, optional): the allowed values of a choice.
  - `value` (`boolean | string`): the current value: a boolean for toggles, a string otherwise.
  - `restartRequired` (`boolean`): changes apply after a restart.
  - `group` (`'settings' | 'people' | 'device'`): `settings` for regular options, `people` for per-person lists (ghost chats, ignored users, hidden words, username aliases, local names, chat backgrounds), `device` for things tied to this computer (app and tray icons, link handling apps).

Example:

```ts
const choices = tg.options.list().filter((option) => option.kind === 'choice')
for (const option of choices) console.log(option.id, option.choices?.join(' | '))
```

### type OptionChange

```ts
export interface OptionChange {
  id: string
  value: boolean | string
}
```

what `onChange` callbacks get.

- **fields:**
  - `id` (`string`): the setting that changed.
  - `value` (`boolean | string`): its new value.

Example:

```ts
tg.options.onChange((change: OptionChange) => console.log(change.id, '->', change.value))
```

### tg.tele

```ts
readonly tele: TeleFeatures
```

tele's own per-person features: ignored users, per-chat ghost mode and local names.

- **grant:** `account.read(peers)` to read, `options` to change.
- **returns:** the `TeleFeatures` object (frozen).

Example:

```ts
console.log(tg.tele.ignored.list().length, 'ignored users')
```

### type TeleFeatures

```ts
export interface TeleFeatures {
  readonly ignored: {
    list(): bigint[]
    set(peer: InputPeerLike, ignored: boolean): Promise<void>
  }
  readonly ghost: {
    get(peer: InputPeerLike): Promise<GhostMode | undefined>
    set(peer: InputPeerLike, mode: GhostMode): Promise<void>
    list(): { chatId: bigint, mode: GhostMode }[]
  }
  readonly localNames: {
    list(): { chatId: bigint, name: string }[]
    set(user: InputPeerLike, name: string | null): Promise<void>
  }
}
```

the type of `tg.tele`.

- **fields:**
  - `ignored` (`{ list, set }`): ignored users.
  - `ghost` (`{ get, set, list }`): per-chat ghost mode.
  - `localNames` (`{ list, set }`): your local names for users.

Example:

```ts
const features: TeleFeatures = tg.tele
```

### tg.tele.ignored.list()

```ts
list(): bigint[]
```

the users you ignore in tele (their messages fade or disappear, depending on tele's settings).

- **grant:** `account.read(peers)`.
- **returns:** their marked ids.
- **throws:** `TeleError` `not-granted`: `tg.tele.ignored.list needs the grant 'account.read(peers)'`.

Example:

```ts
const ignored = new Set(tg.tele.ignored.list())
tg.onNewMessage((message) => {
  if (message.senderId !== null && ignored.has(message.senderId)) console.log('ignored user wrote')
})
```

### tg.tele.ignored.set(peer, ignored)

```ts
set(peer: InputPeerLike, ignored: boolean): Promise<void>
```

ignores or un-ignores a user, like the userpic menu does.

- **grant:** `options`.
- **parameters:**
  - `peer` (`InputPeerLike`): a peer in tele's cache.
  - `ignored` (`boolean`): `true` to ignore.
- **returns:** resolves when applied.
- **throws:** `TeleError` `not-granted`: `tg.tele.ignored.set needs the grant 'options'`; `TypeError: tg.tele.ignored.set needs a peer in tele's cache`; the errors of `InputPeerLike`.

Example:

```ts
tg.onNewMessage(async (message) => {
  if (message.sender?.scam) await tg.tele.ignored.set(message.sender, true)
})
```

### tg.tele.ghost.get(peer)

```ts
get(peer: InputPeerLike): Promise<GhostMode | undefined>
```

the ghost mode override of one chat.

- **grant:** `account.read(peers)`.
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
- **returns:** `'default'`, `'always'` or `'never'`; `undefined` when tele hasn't loaded the chat.
- **throws:** `TeleError` `not-granted`; the errors of `InputPeerLike`.

Example:

```ts
if ((await tg.tele.ghost.get('@boss')) !== 'always') await tg.tele.ghost.set('@boss', 'always')
```

### tg.tele.ghost.set(peer, mode)

```ts
set(peer: InputPeerLike, mode: GhostMode): Promise<void>
```

sets a chat's ghost mode override, like the chat menu does.

- **grant:** `options`.
- **parameters:**
  - `peer` (`InputPeerLike`): a chat in tele's cache.
  - `mode` (`GhostMode`): `'default'` follows the global setting, `'always'` / `'never'` force it for this chat.
- **returns:** resolves when applied.
- **throws:** `TypeError: tg.tele.ghost.set: the mode is 'default', 'always' or 'never'`; `TypeError: tg.tele.ghost.set needs a peer in tele's cache`; `TeleError` `not-granted`.

Example:

```ts
await tg.tele.ghost.set(tg.selfId, 'never')
```

### tg.tele.ghost.list()

```ts
list(): { chatId: bigint, mode: GhostMode }[]
```

every chat with a ghost mode override.

- **grant:** `account.read(peers)`.
- **returns:** `{ chatId, mode }` entries (`chatId` marked).
- **throws:** `TeleError` `not-granted`.

Example:

```ts
const always = tg.tele.ghost.list().filter((entry) => entry.mode === 'always').length
```

### type GhostMode

```ts
export type GhostMode = 'default' | 'always' | 'never'
```

a chat's ghost mode override.

- **fields:**
  - `'default'`: follow tele's ghost mode setting.
  - `'always'`: ghost in this chat even when ghost mode is off.
  - `'never'`: never ghost in this chat.

Example:

```ts
const mode: GhostMode = 'always'
```

### tg.tele.localNames.list()

```ts
list(): { chatId: bigint, name: string }[]
```

the names you gave users locally in tele.

- **grant:** `account.read(peers)`.
- **returns:** `{ chatId, name }` entries.
- **throws:** `TeleError` `not-granted`.

Example:

```ts
for (const { chatId, name } of tg.tele.localNames.list()) console.log(chatId, 'is', name)
```

### tg.tele.localNames.set(user, name)

```ts
set(user: InputPeerLike, name: string | null): Promise<void>
```

gives a user a local name (shown instead of theirs, and above `overridePeer` names), or removes it.

- **grant:** `options`.
- **parameters:**
  - `user` (`InputPeerLike`): a user in tele's cache.
  - `name` (`string | null`): the name; `null` or `''` removes it.
- **returns:** resolves when applied.
- **throws:** `TypeError: tg.tele.localNames.set works for users`; `TypeError: tg.tele.localNames.set needs a peer in tele's cache`; `TeleError` `not-granted`.

Example:

```ts
await tg.tele.localNames.set('@durov', 'pavel')
```

## script to script

the running scripts of one account can talk: fire-and-forget events and request/reply calls. both ends need the `scripts` grant, so the user sees who talks to whom.

### tg.scripts

```ts
readonly scripts: Scripts
```

messaging between this account's running scripts.

- **grant:** none for `list`; `scripts` for `emit`, `on`, `expose` and `call`.
- **returns:** the `Scripts` object (frozen).
- **notes:**
  - data travels through the storage serializer: everything `StorageValue` allows (json values, `bigint`, `Uint8Array`) survives, `undefined` arrives as `null`, and anything else throws like `tg.storage.set` (functions, `Map`, `Set`, `Date`, class instances, cycles).
  - scripts on other accounts aren't reachable; a script never receives its own events.

Example:

```ts
console.log(tg.scripts.list().filter((script) => script.running).map((script) => script.name))
```

### type Scripts

```ts
export interface Scripts {
  list(): ScriptListing[]
  emit(event: string, data?: unknown, options?: { to?: string }): number
  on(event: string, callback: (data: unknown, from: ScriptRef) => unknown): Disposer
  expose(name: string, handler: (request: { args: unknown[], from: ScriptRef }) => unknown): Disposer
  call<T = unknown>(scriptId: string, name: string, ...args: unknown[]): Promise<T>
}
```

the type of `tg.scripts`.

- **fields:**
  - `list` (`() => ScriptListing[]`): every script in the folder.
  - `emit` (`(event, data?, options?) => number`): sends an event.
  - `on` (`(event, callback) => Disposer`): receives events.
  - `expose` (`(name, handler) => Disposer`): offers a callable function.
  - `call` (`(scriptId, name, ...args) => Promise<T>`): calls another script's function.

Example:

```ts
const scripts: Scripts = tg.scripts
```

### tg.scripts.list()

```ts
list(): ScriptListing[]
```

every script in the scripts folder, running or not.

- **grant:** none.
- **returns:** `ScriptListing[]`.

Example:

```ts
const helper = tg.scripts.list().find((script) => script.name === 'translator' && script.running)
```

### tg.scripts.emit(event, data?, options?)

```ts
emit(event: string, data?: unknown, options?: { to?: string }): number
```

sends an event to the other running scripts of this account that listen to it.

- **grant:** `scripts`.
- **parameters:**
  - `event` (`string`): the event name; must not start with `\u0000` (reserved).
  - `data` (`unknown`, optional): a `StorageValue`; default `null`.
  - `options.to` (`string`, optional): only this script id.
- **returns:** how many scripts (other than this one) have a listener for `event`; `0` means nobody heard it.
- **throws:** `TypeError: a script event is a string that doesn't start with \u0000`; serializer `TypeError`s for `data`; `TeleError` `not-granted`: `tg.scripts.emit needs the grant 'scripts'`.
- **notes:** delivery is asynchronous (the receivers run on a later turn).

Example:

```ts
tg.onNewMessage((message) => {
  if (message.mentioned) tg.scripts.emit('mention', { chatId: message.chatId, id: message.id })
})
```

### tg.scripts.on(event, callback)

```ts
on(event: string, callback: (data: unknown, from: ScriptRef) => unknown): Disposer
```

listens to an event from other scripts.

- **grant:** `scripts`.
- **parameters:**
  - `event` (`string`): the event name (not starting with `\u0000`).
  - `callback` (`(data, from) => unknown`): gets a fresh copy of the data and who sent it.
- **returns:** a `Disposer`.
- **throws:** `TypeError: a script event is a string that doesn't start with \u0000`, `tg.scripts.on(event, function)`; `TeleError` `not-granted`: `tg.scripts.on needs the grant 'scripts'`.
- **notes:** each call has the listener budget (200 ms); faults count toward the switch-off.

Example:

```ts
tg.scripts.on('mention', (data, from) => {
  const { chatId } = data as { chatId: bigint }
  console.log(`${from.name} saw a mention in ${chatId}`)
})
```

### tg.scripts.expose(name, handler)

```ts
expose(name: string, handler: (request: { args: unknown[], from: ScriptRef }) => unknown): Disposer
```

offers a function other scripts can `call`.

- **grant:** `scripts`.
- **parameters:**
  - `name` (`string`): the function name.
  - `handler` (`({ args, from }) => unknown`, may be async): gets the caller's arguments and who called; its value (or resolved value) is the answer, `undefined` becomes `null`.
- **returns:** a `Disposer` that withdraws it (only if `name` still points at this handler).
- **throws:** `TypeError: tg.scripts.expose(name, handler)`; `TeleError` `not-granted`.
- **notes:** exposing the same name again replaces the handler. a throw or rejection reaches the caller as `TeleError` `internal` with the error's message; so does an answer the serializer can't carry.

Example:

```ts
tg.scripts.expose('translate', async ({ args }) => {
  const [text, to] = args as [string, string]
  const response = await fetch(`https://translate.example.com/?to=${to}&q=${encodeURIComponent(text)}`)
  return response.text()
})
```

### tg.scripts.call(scriptId, name, ...args)

```ts
call<T = unknown>(scriptId: string, name: string, ...args: unknown[]): Promise<T>
```

calls a function another running script exposed, and resolves with its answer.

- **grant:** `scripts` (the target needs it too, to expose).
- **parameters:**
  - `scriptId` (`string`): the target's id (its file or folder name, `ScriptListing.id`), not its display name.
  - `name` (`string`): the exposed function.
  - `args` (`unknown[]`): arguments, each a `StorageValue`.
- **returns:** the handler's answer (`T` is only a type cast).
- **throws:** synchronously `TypeError: tg.scripts.call(scriptId, name, ...args)` and serializer `TypeError`s; `TeleError` `not-granted`. rejects with `TeleError` `not-found` (`<id> isn't running or exposes nothing`, `<name> isn't exposed`), `TeleError` `internal` (the handler threw), `TeleError` `timed-out` (`<id> didn't answer <name> in 30 s`).

Example:

```ts
const translator = tg.scripts.list().find((script) => script.name === 'translator' && script.running)
if (translator) {
  const english = await tg.scripts.call<string>(translator.id, 'translate', message.text, 'en')
  await message.reply(english)
}
```

### type ScriptRef

```ts
export interface ScriptRef {
  id: string
  name: string
}
```

who sent an event or a call.

- **fields:**
  - `id` (`string`): the script id (file or folder name); use it for `call` and `emit({ to })`.
  - `name` (`string`): its `defineScript` name.

Example:

```ts
tg.scripts.on('ping', (_, from: ScriptRef) => tg.scripts.emit('pong', null, { to: from.id }))
```

### type ScriptListing

```ts
export interface ScriptListing extends ScriptRef {
  version: string
  running: boolean
  self: boolean
}
```

one entry of `tg.scripts.list()`.

- **fields:**
  - `id` (`string`): the script id.
  - `name` (`string`): its name (for scripts that are off, read from the file without running it).
  - `version` (`string`): its `version`, or `''`.
  - `running` (`boolean`): running on this account now.
  - `self` (`boolean`): this script.

Example:

```ts
const others = tg.scripts.list().filter((script: ScriptListing) => !script.self && script.running)
```

## connection, wake and schedules

none of these need a grant.

### tg.connection()

```ts
connection(): ConnectionInfo
```

the state of this account's connection to its main data center, the same reading as tele's "connecting…" bar.

- **grant:** none.
- **returns:** a `ConnectionInfo`.

Example:

```ts
if (tg.connection().state !== 'connected') console.log('offline for now')
```

### type ConnectionInfo

```ts
export interface ConnectionInfo {
  state: 'connected' | 'connecting' | 'waiting'
  retryIn?: number
}
```

a connection reading.

- **fields:**
  - `state` (`'connected' | 'connecting' | 'waiting'`): connected; trying now; or waiting before the next attempt.
  - `retryIn` (`number`, optional): with `'waiting'`, seconds until the next attempt.

Example:

```ts
const { state, retryIn } = tg.connection()
console.log(state === 'waiting' ? `retry in ${retryIn} s` : state)
```

### tg.onConnectionChange(callback)

```ts
onConnectionChange(callback: (connection: ConnectionInfo) => unknown): Disposer
```

calls `callback` whenever the connection state changes.

- **grant:** none.
- **parameters:**
  - `callback` (`(connection: ConnectionInfo) => unknown`): the new state.
- **returns:** a `Disposer`.
- **throws:** `TypeError: tg.onConnectionChange(function)`.
- **notes:** deduplicated per script: the same state twice in a row fires once.

Example:

```ts
let lostAt = 0
tg.onConnectionChange(({ state }) => {
  if (state !== 'connected' && !lostAt) lostAt = Date.now()
  if (state === 'connected' && lostAt) {
    console.log(`back after ${Math.round((Date.now() - lostAt) / 1000)} s`)
    lostAt = 0
  }
})
```

### tg.onWake(callback)

```ts
onWake(callback: (wake: { sleptFor: number }) => unknown): Disposer
```

calls `callback` after the computer slept or hibernated.

- **grant:** none.
- **parameters:**
  - `callback` (`({ sleptFor }) => unknown`): `sleptFor` is roughly how long it slept, in ms.
- **returns:** a `Disposer`.
- **throws:** `TypeError: tg.onWake(function)`.
- **notes:** a 5 s heartbeat notices wall-clock gaps over 30 s; the os sleep/resume notification triggers the check right away. remember that tele doesn't deliver everything missed while asleep: fetch what you need here.

Example:

```ts
tg.onWake(async ({ sleptFor }) => {
  if (sleptFor > 3_600_000) {
    const recent = await tg.getHistory('me', { limit: 20 })
    console.log('caught up with', recent.length, 'messages')
  }
})
```

### tg.schedule(when, callback)

```ts
schedule(when: Schedule, callback: (firedAt: Date) => unknown): Disposer
```

runs `callback` on the wall clock: every n ms, daily at a time, or once at a moment. unlike a long `setTimeout`, sleep and clock changes don't skew it.

- **grant:** none.
- **parameters:**
  - `when` (`Schedule`): exactly one of `{ every }`, `{ daily }`, `{ at }`.
  - `callback` (`(firedAt: Date) => unknown`): gets the time it actually ran.
- **returns:** a `Disposer` that cancels it.
- **throws:** `TypeError: tg.schedule({ every: ms >= 1000 } | { daily: 'HH:MM' } | { at: Date | ms }, function)` for a wrong shape, more than one kind, `every` under 1000, a bad time, or a missing callback.
- **notes:**
  - it re-arms at most a minute ahead, so a run missed during sleep happens right after waking, and clock changes are picked up within a minute.
  - `every` counts from the previous run, the first run is `every` ms after `schedule`.
  - `daily` is local time, the next occurrence (tomorrow if the time already passed today).
  - `at` runs once; a moment in the past runs right away, before `schedule` returns.
  - callbacks run as timers: 500 ms each, errors are logged and toasted but not counted; a returned promise isn't awaited. everything stops with the script.

Example:

```ts
tg.schedule({ daily: '09:00' }, async () => {
  await tg.sendMessage('me', md`**good morning.** ${tg.local.unread().badge} unread`)
})

tg.schedule({ every: 15 * 60_000 }, () => tg.storage.set('heartbeat', Date.now()))

tg.schedule({ at: new Date('2026-12-31T23:59:00') }, () => tg.toast('almost there'))
```

### type Schedule

```ts
export type Schedule = { every: number } | { daily: string } | { at: Date | number }
```

when `tg.schedule` runs.

- **fields:**
  - `every` (`number`): repeat every this many ms, at least 1000.
  - `daily` (`string`): `'HH:MM'` in local time, 24-hour (`'7:05'` and `'07:05'` both work).
  - `at` (`Date | number`): once, at this `Date` or epoch ms.

Example:

```ts
const hourly: Schedule = { every: 3_600_000 }
tg.schedule(hourly, (firedAt) => console.log('tick', firedAt.toISOString()))
```

## notices and dialogs

everything a script shows to the user without touching telegram: toasts, entries in the notification centre, desktop notifications, native boxes that ask something, the clipboard and links. none of it needs a grant except `tg.notify`, the clipboard and `tg.openUrl`. every box and toast appears in the window of the account the script runs in.

### type Ui

```ts
export interface Ui {
  toast(text: string, options?: ToastOptions): void
  notice(notice: string | NoticeOptions): void
  header(text: string): UiElement
  separator(text?: string): UiElement
  button(options: {
    id?: string
    text: string
    value?: string
    subtitle?: string
    onClick(): unknown
  }): UiElement
  check(options: {
    id?: string
    text: string
    checked: boolean
    subtitle?: string
    onChange(checked: boolean): unknown
  }): UiElement
  select(options: {
    id?: string
    text: string
    items: string[]
    selected: number
    subtitle?: string
    onChange(index: number): unknown
  }): UiElement
  slider(options: {
    id?: string
    text?: string
    min: number
    max: number
    step?: number
    value: number
    subtitle?: string
    label?(value: number): string
    onChange(value: number): unknown
  }): UiElement
  input(options: {
    id?: string
    text: string
    value: string
    placeholder?: string
    maxLength?: number
    multiline?: boolean
    subtitle?: string
    onChange(value: string): unknown
  }): UiElement
  item(options: {
    id?: string
    text: string
    icon?: string
    value?: string
    subtitle?: string
    onClick(): unknown
  }): UiElement
  color(options: {
    id?: string
    text: string
    value: string
    subtitle?: string
    onChange(value: string): unknown
  }): UiElement
  keybind(options: {
    id?: string
    text: string
    value: string
    subtitle?: string
    onChange(value: string): unknown
  }): UiElement
  settingsPage(options: { title?: string, items(): UiElement[] }): Page
  readonly widgets: Widgets
  registerMenuItem(options: { place: 'main' | 'tray', text: string, emoji?: string, onClick(): unknown }): Disposer
  registerSettingsEntry(options: { title: string, emoji?: string, page: Page, onClick?(): unknown }): Disposer
  openSection(page: Page): boolean
  openPage(page: Page): void
  dialog(options: AlertOptions): Promise<AlertAnswer>
  prompt(options: PromptOptions): Promise<string | null>
  chooser(options: ChooserOptions & { multiple?: false }): Promise<number | null>
  chooser(options: ChooserOptions & { multiple: true }): Promise<number[] | null>
}

export interface Ui {
  openChat(peer: InputPeerLike, options?: { message?: number }): Promise<void>
  openProfile(peer: InputPeerLike): Promise<void>
  openSettings(section?: SettingsSection): void
  back(): void
  current(): { chatId: bigint | null, windowActive: boolean }
  onChatOpened(
    callback: (opened: { chatId: bigint | null, chat: PeerInfo | null }) => unknown,
  ): Disposer
  openFile(options?: {
    title?: string
    filter?: string
    multiple?: boolean
  }): Promise<{ name: string, path: string, bytes: Uint8Array }[] | null>
  saveFile(
    data: Uint8Array | string,
    options?: { title?: string, filter?: string, name?: string },
  ): Promise<string | null>
}
```

`tg.ui` is the script's handle on tele's interface: boxes, settings pages and their rows, menu entries, navigation and file pickers. tele.d.ts declares it in two parts, the second adds navigation and files.

- **grant:** none for most members; `tg.ui.widgets` needs `ui.read`, `ui.write` and `unsafe.automate`, see "the widget layer".
- **notes:** every member is documented below under its own name. members that show something need a window showing this account; when there is none (typically a logged-in account that isn't the active one and has no separate window), they throw `TeleError` `unsupported` or quietly return `false`, as noted per member.
- **members:**
  - `toast`, `notice`, `dialog`, `prompt`, `chooser`: this section.
  - `settingsPage`, `header`, `separator`, `button`, `check`, `select`, `slider`, `input`, `item`, `color`, `keybind`, `openPage`, `openSection`, `registerSettingsEntry`, `openFile`, `saveFile`: "pages and settings".
  - `registerMenuItem`: "menus, buttons and commands".
  - `openChat`, `openProfile`, `openSettings`, `back`, `current`, `onChatOpened`: "navigation and compose".
  - `widgets`: "the widget layer".

Example:

```ts
const answer = await tg.ui.dialog({ message: 'clear the cache?', positive: 'clear', negative: 'keep' })
if (answer === 'positive') tg.ui.toast('cleared')
```

### tg.toast(text, options?)

```ts
toast(text: string, options?: ToastOptions): void
```

shows a short toast at the bottom of this account's window, optionally with one link-style button at its end. the toast is also logged in tele's notification centre.

- **grant:** none.
- **parameters:**
  - `text` (`string`): the message. anything else is turned into a string.
  - `options` (`ToastOptions`, optional): how long it stays and an optional button, see `type ToastOptions`.
- **returns:** nothing. the toast appears on the next event-loop turn.
- **throws:** nothing for normal use; calling it after the script stopped throws `InternalError: the script was stopped`.
- **notes:**
  - default duration is 1.5 s, or 5 s when the toast has a button.
  - toasts aren't rate-limited: a script that toasts in a loop really floods the screen. tele's own fault toasts about a failing script are merged (at most one per 5 s), yours are not.
  - the button's `onClick` runs at most once. tele keeps it until 2 s after the toast disappears, then forgets it.
  - when the account has no window nothing is shown, but the notification centre entry is still added.
  - the notification centre entry has no tone and the script's name as its title (only when the centre and its "Log script notices" option are on, both are by default).

Example:

```ts
tg.toast('message copied')

tg.toast('draft cleared', {
  duration: 6000,
  button: { text: 'undo', onClick: () => tg.compose.set(saved) },
})
```

### tg.ui.toast(text, options?)

```ts
toast(text: string, options?: ToastOptions): void
```

the same function as `tg.toast`, reachable from `tg.ui` so ui code can stay in one namespace.

- **grant:** none.
- **parameters:**
  - `text` (`string`): the message.
  - `options` (`ToastOptions`, optional): duration and button.
- **returns:** nothing.
- **notes:** everything said for `tg.toast` applies.

Example:

```ts
tg.ui.toast('saved', { duration: 3000 })
```

### type ToastOptions

```ts
export interface ToastOptions {
  duration?: number
  button?: { text: string, onClick(): unknown }
}
```

options of `tg.toast` and `tg.ui.toast`.

- **fields:**
  - `duration` (`number`, optional): how long the toast stays, in milliseconds. zero, negative or missing means the default: 1.5 s, or 5 s with a button.
  - `button` (`{ text: string, onClick(): unknown }`, optional): a link-style button drawn after the text. both `text` (non-empty) and `onClick` (a function) are needed, otherwise the toast shows without a button.
    - `text` (`string`): the button's label.
    - `onClick` (`() => unknown`): runs once when the user clicks it, on the next event-loop turn, with the listener budget (200 ms for the synchronous part). may be async.

Example:

```ts
const options: ToastOptions = { duration: 8000, button: { text: 'open', onClick: () => tg.ui.openChat('me') } }
tg.toast('saved to your saved messages', options)
```

### tg.ui.notice(notice)

```ts
notice(notice: string | NoticeOptions): void
```

adds an entry to tele's notification centre (the notices section, **Scripts** tab) without showing a toast. good for things the user may want to read later: a finished job, a warning, a summary with links.

- **grant:** none.
- **parameters:**
  - `notice` (`string | NoticeOptions`): a plain text, or an object with a title, rich text, a tone and up to two buttons, see `type NoticeOptions`.
- **returns:** nothing.
- **throws:**
  - `TypeError: tg.ui.notice: tone is info, success, warning or critical` for an unknown tone.
  - `TypeError: tg.ui.notice: a button is { text, url }` when one of the first two buttons misses its text or url.
  - `TypeError: tg.ui.notice needs a text: a string or { title, text, tone, buttons }` for an empty or whitespace-only text.
- **notes:**
  - the entry's title is `title`, or the script's name when there's none. the tab and its entries carry tele's purple experimental icon.
  - entries are only kept while the notification centre and its "Log script notices" option are on (both default on). `tg.toast`, `tg.notify` and tele's own notes about the script (faults, can't start, waiting for grants) land in the same tab.
  - `text` keeps its entities, so `md` and `html` work: bold, links, code and so on.

Example:

```ts
import { md } from 'tele'

tg.ui.notice('backup finished')
tg.ui.notice({
  title: 'weekly report',
  text: md`**${count}** new messages in your watched chats`,
  tone: 'success',
  buttons: [{ text: 'open saved messages', url: 'tg://resolve?domain=telegram' }],
})
```

### type NoticeOptions

```ts
export interface NoticeOptions {
  title?: string
  text: InputText
  tone?: 'info' | 'success' | 'warning' | 'critical'
  buttons?: { text: string, url: string }[]
}
```

the object form of `tg.ui.notice`.

- **fields:**
  - `title` (`string`, optional): the entry's title. defaults to the script's name.
  - `text` (`InputText`): the body, a string or `{ text, entities }`. must not be empty.
  - `tone` (`'info' | 'success' | 'warning' | 'critical'`, optional): the entry's color and icon. without it the entry is neutral.
  - `buttons` (`{ text: string, url: string }[]`, optional): up to two buttons under the text; more are ignored. each needs a non-empty `text` and `url`. a click opens `url` the way a link in a message opens (so `tg://` and `t.me` links work and `interceptLink` sees it).

Example:

```ts
tg.ui.notice({ text: 'the api key expired', tone: 'critical', buttons: [{ text: 'get a new one', url: 'https://example.com/keys' }] })
```

### tg.notify(title, text)

```ts
notify(title: string, text: string): void
```

shows a desktop notification through tele's own notification system, the same one tele uses for "came online" alerts. the notification is attached to saved messages.

- **grant:** `notify`.
- **parameters:**
  - `title` (`string`): the notification title. may be empty.
  - `text` (`string`): the body.
- **returns:** nothing.
- **throws:** `TeleError` `not-granted` without the `notify` grant.
- **notes:**
  - it follows the user's notification settings: nothing pops up when desktop notifications are off, and for an account that isn't the active one only with "notify from all accounts".
  - native notifications show the title and the text; tele's own popups show `title: text` under saved messages.
  - the notification centre always gets an info entry with `title` and `text` on two lines.

Example:

```ts
export default defineScript({
  name: 'deploy watcher',
  grants: ['notify', 'fetch(ci.example.com)'],
  setup(tg) {
    tg.schedule({ every: 60_000 }, async () => {
      const state = await (await fetch('https://ci.example.com/status')).text()
      if (state === 'failed') tg.notify('ci', 'the main build failed')
    })
  },
})
```

### tg.ui.dialog(options)

```ts
dialog(options: AlertOptions): Promise<AlertAnswer>
```

opens a native box with a message and up to three buttons and resolves with the button the user pressed.

- **grant:** none.
- **parameters:**
  - `options` (`AlertOptions`): title, message, button labels and the danger flag, see `type AlertOptions`.
- **returns:** `Promise<AlertAnswer>`: `'positive'`, `'negative'`, `'neutral'`, or `'dismissed'` when the box was closed another way (Escape, a click outside, the window closing).
- **throws:**
  - `TypeError: tg.ui.dialog needs an options object` when `options` isn't an object.
  - `TeleError` `unsupported` (`tg.ui.dialog: this account has no window`) when the account has no window.
- **notes:**
  - the box title is the script's name unless `title` is given; a given title gets an extra line naming the script ("from the script ..."), so a script can't pass for tele itself.
  - only buttons with a label appear: the positive one always (`'OK'` by default), negative and neutral when you give their text.
  - each call opens its own box; the promise settles when the user answers.

Example:

```ts
const answer = await tg.ui.dialog({
  title: 'delete 120 messages?',
  message: 'this removes them for everyone in the chat.',
  positive: 'delete',
  negative: 'cancel',
  danger: true,
})
if (answer !== 'positive') return
```

### type AlertOptions

```ts
export interface AlertOptions {
  title?: string
  message?: string
  positive?: string
  negative?: string
  neutral?: string
  danger?: boolean
}
```

options of `tg.ui.dialog`.

- **fields:**
  - `title` (`string`, optional): the box title. defaults to the script's name; a custom one adds a line naming the script.
  - `message` (`string`, optional): the text in the box. plain text.
  - `positive` (`string`, optional): the main button's label, `'OK'` by default. answers `'positive'`.
  - `negative` (`string`, optional): a second button, shown only when given. answers `'negative'`.
  - `neutral` (`string`, optional): a third button, shown only when given. answers `'neutral'`.
  - `danger` (`boolean`, optional): paints the positive button in the attention (red) color, for destructive actions.

Example:

```ts
const options: AlertOptions = { message: 'save changes?', positive: 'save', negative: 'discard', neutral: 'cancel' }
```

### type AlertAnswer

```ts
export type AlertAnswer = 'positive' | 'negative' | 'neutral' | 'dismissed'
```

what `tg.ui.dialog` resolves with.

- **values:**
  - `'positive'`: the main button.
  - `'negative'`: the negative button.
  - `'neutral'`: the neutral button.
  - `'dismissed'`: the box closed without a button: Escape, a click outside, or the window closing.

Example:

```ts
switch (await tg.ui.dialog({ message: 'sync now?', positive: 'yes', negative: 'no' })) {
  case 'positive': await sync(); break
  case 'dismissed': tg.toast('asked again tomorrow'); break
}
```

### tg.ui.prompt(options)

```ts
prompt(options: PromptOptions): Promise<string | null>
```

opens a box with a text field and OK / Cancel and resolves with what the user typed.

- **grant:** none.
- **parameters:**
  - `options` (`PromptOptions`): title, message, placeholder, initial value, length limit and multiline mode, see `type PromptOptions`.
- **returns:** `Promise<string | null>`: the text (possibly empty) after OK or Enter, `null` after Cancel, Escape or a click outside.
- **throws:**
  - `TypeError: tg.ui.prompt needs an options object`.
  - `TeleError` `unsupported` (`tg.ui.prompt: this account has no window`).
- **notes:**
  - the field gets focus and its initial value is selected, so typing replaces it.
  - the title follows the same rule as `tg.ui.dialog`: the script's name by default, a line naming the script under a custom one.

Example:

```ts
const name = await tg.ui.prompt({ title: 'rename the tag', placeholder: 'tag name', value: current, maxLength: 32 })
if (name !== null && name.trim()) rename(name.trim())
```

### type PromptOptions

```ts
export interface PromptOptions {
  title?: string
  message?: string
  placeholder?: string
  value?: string
  maxLength?: number
  multiline?: boolean
}
```

options of `tg.ui.prompt`.

- **fields:**
  - `title` (`string`, optional): the box title, the script's name by default.
  - `message` (`string`, optional): a line of explanation above the field.
  - `placeholder` (`string`, optional): the grey hint shown while the field is empty.
  - `value` (`string`, optional): the initial text, selected when the box opens.
  - `maxLength` (`number`, optional): the most characters the field accepts. zero or missing means no limit.
  - `multiline` (`boolean`, optional): a multi-line field instead of a single line.

Example:

```ts
const note = await tg.ui.prompt({ title: 'note for this chat', multiline: true, value: tg.storage.get<string>('note') ?? '' })
```

### tg.ui.chooser(options)

```ts
chooser(options: ChooserOptions & { multiple?: false }): Promise<number | null>
chooser(options: ChooserOptions & { multiple: true }): Promise<number[] | null>
```

opens a box with a list to pick from: a radio list that answers on the first click, or with `multiple: true` a list of checkboxes with OK / Cancel.

- **grant:** none.
- **parameters:**
  - `options` (`ChooserOptions & { multiple?: boolean }`): title, items, the initial selection, and `multiple`, see `type ChooserOptions`.
- **returns:**
  - single: `Promise<number | null>`: the index of the picked item, `null` after Cancel, Escape or a click outside.
  - multiple: `Promise<number[] | null>`: the indexes of the checked items in list order after OK (an empty array when nothing is checked), `null` when cancelled.
- **throws:**
  - `TypeError: tg.ui.chooser needs an options object`.
  - `TypeError: tg.ui.chooser needs items` when `items` is missing or empty.
  - `TeleError` `unsupported` (`tg.ui.chooser: this account has no window`).
- **notes:**
  - items are shown as plain text; non-strings are turned into strings.
  - in single mode clicking the already selected item doesn't count as an answer; pick another one or cancel.

Example:

```ts
const languages = ['english', 'deutsch', 'русский']
const index = await tg.ui.chooser({ title: 'translate to', items: languages, selected: 0 })
if (index !== null) tg.storage.set('lang', languages[index])

const picked = await tg.ui.chooser({ title: 'watch these', items: chats.map((chat) => chat.name), multiple: true, selected: [0, 2] })
```

### type ChooserOptions

```ts
export interface ChooserOptions {
  title?: string
  items: string[]
  selected?: number | number[]
}
```

options of `tg.ui.chooser`; the call itself adds `multiple`.

- **fields:**
  - `title` (`string`, optional): the box title, the script's name by default.
  - `items` (`string[]`): the choices, at least one.
  - `selected` (`number | number[]`, optional): what starts selected. in single mode the first index counts; in multiple mode every listed index starts checked.
  - `multiple` (`boolean`, optional, from the call's signature): `true` for checkboxes and an array answer.

Example:

```ts
const options: ChooserOptions = { title: 'sort by', items: ['date', 'name', 'unread'], selected: 0 }
```

### tg.clipboard

```ts
readonly clipboard: {
  read(): string
  write(text: string): void
}
```

plain-text access to the system clipboard. each method has its own grant, so a script can write without being able to read.

- **grant:** `clipboard.read` for `read`, `clipboard.write` for `write`.
- **notes:** text only. images and files on the clipboard are invisible here; for dropped or pasted files see `tg.interceptDrop`.

Example:

```ts
tg.clipboard.write(String(ctx.chatId))
```

### tg.clipboard.read()

```ts
read(): string
```

returns the clipboard's current text.

- **grant:** `clipboard.read` (caution: the clipboard often holds passwords and codes, the consent box says "read the clipboard").
- **returns:** `string`: the text, an empty string when the clipboard holds no text.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
const copied = tg.clipboard.read()
if (/^https?:\/\//.test(copied)) await tg.compose.insert(copied)
```

### tg.clipboard.write(text)

```ts
write(text: string): void
```

replaces the clipboard's content with `text`.

- **grant:** `clipboard.write`.
- **parameters:**
  - `text` (`string`): the new content; non-strings are turned into strings, a missing value clears the clipboard text.
- **returns:** nothing.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.registerMessageAction({
  id: 'copy_id',
  text: 'copy message id',
  onClick: (ctx) => {
    tg.clipboard.write(`${ctx.chatId}/${ctx.messageId}`)
    tg.toast('copied')
  },
})
```

### tg.openUrl(link)

```ts
openUrl(link: string): void
```

opens a link exactly as if the user clicked it in this account's window: `tg://` and `t.me` links are handled inside tele, other links go wherever a click on them would go.

- **grant:** `openUrl`.
- **parameters:**
  - `link` (`string`): the link; surrounding whitespace is trimmed.
- **returns:** nothing. the link opens on the next event-loop turn.
- **throws:**
  - `TeleError` `not-granted` without the grant.
  - `TypeError: tg.openUrl needs a link` for an empty link.
- **notes:** the link goes through every script's `tg.interceptLink`, this script's included.

Example:

```ts
tg.registerChatAction({
  id: 'search_web',
  text: 'search this chat on the web',
  onClick: (ctx) => tg.openUrl(`https://duckduckgo.com/?q=${encodeURIComponent(ctx.chat.name)}`),
})
```

## pages and settings

scripts describe settings declaratively, like inu: `tg.ui.settingsPage({ title, items })` takes a function that returns rows, and tele renders them with its own settings widgets. the page is controlled like a react component: rows always show what the last `items()` call returned, and after every click or change tele calls your handler and then `items()` again. keep your state in variables or `tg.storage`, read it in `items()`, change it in handlers.

a page can be shown in three places: inline on the script's page in the scripts manager (`tg.registerSettings`), in a box (`tg.ui.openPage`), or as a real settings section with a back arrow (`tg.ui.openSection`, `tg.ui.registerSettingsEntry`). the same page object can be in all of them at once.

```ts
let enabled = tg.storage.get<boolean>('enabled') ?? true
let volume = tg.storage.get<number>('volume') ?? 50
const page = tg.ui.settingsPage({
  title: 'my script',
  items: () => [
    tg.ui.header('general'),
    tg.ui.check({ text: 'enabled', checked: enabled, onChange: (value) => { enabled = value; tg.storage.set('enabled', value) } }),
    tg.ui.slider({ text: 'volume', min: 0, max: 100, step: 5, value: volume, label: (value) => `${value}%`, onChange: (value) => { volume = value; tg.storage.set('volume', value) } }),
  ],
})
tg.registerSettings(page)
```

### tg.ui.settingsPage(options)

```ts
settingsPage(options: { title?: string, items(): UiElement[] }): Page
```

creates a page whose rows come from `items()`. creating it shows nothing; pass it to `tg.registerSettings`, `tg.ui.openPage`, `tg.ui.openSection` or `tg.ui.registerSettingsEntry`.

- **grant:** none.
- **parameters:**
  - `options.title` (`string`, optional): the page title, used for boxes and sections. without it they show the script's name. empty string by default.
  - `options.items` (`() => UiElement[]`): returns the rows, built with `tg.ui.header`, `separator`, `button`, `check`, `select`, `slider`, `input`, `item`, `color` and `keybind`. called when the page is shown, after every row event (except slider moves), and on `page.invalidate()`.
- **returns:** `Page`, a frozen `{ title, invalidate(), dispose() }`.
- **throws:** `TypeError: tg.ui.settingsPage({ title, items: () => [...] })` when `items` isn't a function.
- **notes:**
  - `items()` runs synchronously with the listener budget (200 ms); it can't be async. read cached values in it and fetch data elsewhere, then call `page.invalidate()`.
  - if `items()` throws or returns something that isn't an array, it's a fault (logged, counts toward "5 in a row") and the page keeps the last good rows.
  - rows are updated in place while the page's structure stays the same: same row types in the same order, the same rows having a subtitle and a value, the same number of `select` items, the same `item` rows having an icon, the same `slider` range, step and text. switches animate, labels change. any structural change rebuilds the page.
  - handlers (`onClick`, `onChange`) run with the 200 ms budget for their synchronous part and may be async; the re-render happens right after the synchronous part, so after an `await` call `page.invalidate()` yourself.
  - there's no limit on the number of pages per script. all of them close when the script stops.

Example:

```ts
let city = tg.storage.get<string>('city') ?? 'berlin'
let units = tg.storage.get<number>('units') ?? 0
const page = tg.ui.settingsPage({
  title: 'weather',
  items: () => [
    tg.ui.input({ text: 'city', value: city, onChange: (value) => { city = value; tg.storage.set('city', value) } }),
    tg.ui.select({ text: 'units', items: ['celsius', 'fahrenheit'], selected: units, onChange: (index) => { units = index; tg.storage.set('units', index) } }),
  ],
})
tg.registerSettings(page)
```

### type Page

```ts
export interface Page {
  readonly title: string
  invalidate(): void
  dispose(): void
}
```

a page made by `tg.ui.settingsPage`. it's a frozen object; tele recognizes its own pages, so an object that merely looks like one is rejected with `TypeError: expected a page from tg.ui.settingsPage`.

- **fields:**
  - `title` (`string`): the title given to `settingsPage`, `''` when none was.
  - `invalidate` (`() => void`): re-render the page wherever it's shown, see `page.invalidate()`.
  - `dispose` (`() => void`): close the page everywhere and forget it, see `page.dispose()`.

Example:

```ts
const page = tg.ui.settingsPage({ title: 'stats', items: () => [tg.ui.item({ text: 'messages today', value: String(count), onClick: () => {} })] })
tg.onNewMessage(() => { count++; page.invalidate() })
```

### page.title

```ts
readonly title: string
```

the title the page was created with, `''` when none was given. it can't be changed; create a new page for a new title.

- **grant:** none.
- **returns:** `string`.

Example:

```ts
console.log(`opening ${page.title || tg.scriptName}`)
```

### page.invalidate()

```ts
invalidate(): void
```

calls `items()` again and updates every place the page is shown. use it after changes that didn't come from the page itself: a timer, an update, a finished `fetch`, an `await` inside a handler.

- **grant:** none.
- **returns:** nothing. the re-render happens on the next event-loop turn.
- **throws:** `TeleError` `handle-expired` (`this page was disposed`) after `page.dispose()`.
- **notes:** calling it while the page isn't shown anywhere is cheap and does nothing.

Example:

```ts
let status = 'checking...'
const page = tg.ui.settingsPage({ items: () => [tg.ui.item({ text: 'server', value: status, onClick: refresh })] })
async function refresh() {
  status = (await fetch('https://status.example.com')).ok ? 'up' : 'down'
  page.invalidate()
}
```

### page.dispose()

```ts
dispose(): void
```

closes the page wherever it's shown (an open box closes, a section goes back, the inline settings in the scripts manager disappear) and frees it.

- **grant:** none.
- **returns:** nothing.
- **throws:** nothing; disposing twice is fine.
- **notes:** after disposal `invalidate`, `tg.ui.openPage` and `tg.registerSettings` throw `TeleError` `handle-expired`, `tg.ui.openSection` returns `false`, `tg.ui.registerSettingsEntry` throws a `TypeError`. pages are disposed by themselves when the script stops.

Example:

```ts
const wizard = tg.ui.settingsPage({ title: 'setup', items: () => [tg.ui.button({ text: 'done', onClick: () => wizard.dispose() })] })
tg.ui.openPage(wizard)
```

### type UiElement

```ts
export interface UiElement {
  readonly type: 'header' | 'button' | 'check' | 'select' | 'slider' | 'input' | 'separator' | 'item' | 'color' | 'keybind'
}
```

one row of a settings page, made by a row builder. it's a frozen copy of the options you passed plus `type`; tele reads it when the page renders.

- **fields:**
  - `type` (`'header' | 'button' | 'check' | 'select' | 'slider' | 'input' | 'separator' | 'item' | 'color' | 'keybind'`): which row it is. set by the builder, can't be overridden.
  - every option given to the builder, as given (`text`, `value`, `onChange`, ...).
- **notes:**
  - only rows returned from `items()` count; building a row doesn't show it.
  - every builder takes `id?: string`. tele doesn't use it; it's there for your own bookkeeping (finding a row in a list, keys in tests).
  - `subtitle` (on every row except `header` and `separator`) is a small grey line of text under the row.
  - the builders accept a plain string as a shorthand for `{ text }` (typed only for `header` and `separator`).

Example:

```ts
const rows: UiElement[] = [tg.ui.header('filters')]
for (const word of words) rows.push(tg.ui.button({ id: word, text: word, onClick: () => remove(word) }))
```

### tg.ui.header(text)

```ts
header(text: string): UiElement
```

a section title inside the page, in the accent color, like tele's own settings headers.

- **grant:** none.
- **parameters:**
  - `text` (`string`): the title.
- **returns:** `UiElement` with `type: 'header'`.
- **notes:** has no events and ignores `subtitle`.

Example:

```ts
items: () => [tg.ui.header('notifications'), tg.ui.check({ text: 'sound', checked: sound, onChange: setSound })]
```

### tg.ui.separator(text?)

```ts
separator(text?: string): UiElement
```

a divider between groups of rows. with `text` it's tele's divider with an explanation paragraph on it, the grey block under settings groups.

- **grant:** none.
- **parameters:**
  - `text` (`string`, optional): the explanation shown in the divider.
- **returns:** `UiElement` with `type: 'separator'`.
- **notes:** switching between an empty and a text separator is a structural change (the page is rebuilt).

Example:

```ts
items: () => [
  tg.ui.check({ text: 'hide read chats', checked: hide, onChange: setHide }),
  tg.ui.separator('chats you read are hidden from the list until a new message arrives.'),
]
```

### tg.ui.button(options)

```ts
button(options: {
  id?: string
  text: string
  value?: string
  subtitle?: string
  onClick(): unknown
}): UiElement
```

a clickable settings row, optionally with a value label on its right side.

- **grant:** none.
- **parameters:**
  - `options.id` (`string`, optional): your own name for the row; unused by tele.
  - `options.text` (`string`): the row's label.
  - `options.value` (`string`, optional): a grey label at the right end of the row, like "3 chats". a row with a value and one without are different structures.
  - `options.subtitle` (`string`, optional): a small line under the row.
  - `options.onClick` (`() => unknown`): runs on click (200 ms synchronous budget, may be async); then `items()` runs again.
- **returns:** `UiElement` with `type: 'button'`.

Example:

```ts
tg.ui.button({ text: 'clear the cache', value: `${cache.size} items`, onClick: () => { cache.clear(); tg.toast('cleared') } })
```

### tg.ui.check(options)

```ts
check(options: {
  id?: string
  text: string
  checked: boolean
  subtitle?: string
  onChange(checked: boolean): unknown
}): UiElement
```

a row with a switch on its right side.

- **grant:** none.
- **parameters:**
  - `options.id` (`string`, optional): your own name for the row.
  - `options.text` (`string`): the row's label.
  - `options.checked` (`boolean`): what the switch shows.
  - `options.subtitle` (`string`, optional): a small line under the row.
  - `options.onChange` (`(checked: boolean) => unknown`): runs when the user flips the switch, with the new state; then `items()` runs again, so return the new `checked` from it.
- **returns:** `UiElement` with `type: 'check'`.

Example:

```ts
tg.ui.check({
  text: 'mark as read on open',
  checked: tg.storage.get<boolean>('autoread') ?? false,
  subtitle: 'opening a chat reads every message in it.',
  onChange: (checked) => tg.storage.set('autoread', checked),
})
```

### tg.ui.select(options)

```ts
select(options: {
  id?: string
  text: string
  items: string[]
  selected: number
  subtitle?: string
  onChange(index: number): unknown
}): UiElement
```

a row that shows the selected choice on its right side; clicking it opens a chooser box (a radio list titled with `text`).

- **grant:** none.
- **parameters:**
  - `options.id` (`string`, optional): your own name for the row.
  - `options.text` (`string`): the row's label and the chooser's title.
  - `options.items` (`string[]`): the choices.
  - `options.selected` (`number`): the index of the current choice. out of range (for example `-1`) shows no value.
  - `options.subtitle` (`string`, optional): a small line under the row.
  - `options.onChange` (`(index: number) => unknown`): runs with the picked index when it differs from `selected`; then `items()` runs again.
- **returns:** `UiElement` with `type: 'select'`.
- **notes:** the number of `items` is part of the page structure; changing it rebuilds the page.

Example:

```ts
const modes = ['off', 'mentions only', 'everything']
tg.ui.select({ text: 'notify about', items: modes, selected: mode, onChange: (index) => { mode = index; tg.storage.set('mode', index) } })
```

### tg.ui.slider(options)

```ts
slider(options: {
  id?: string
  text?: string
  min: number
  max: number
  step?: number
  value: number
  subtitle?: string
  label?(value: number): string
  onChange(value: number): unknown
}): UiElement
```

a horizontal slider with the current value printed next to it, like tele's interface scale slider.

- **grant:** none.
- **parameters:**
  - `options.id` (`string`, optional): your own name for the row.
  - `options.text` (`string`, optional): a label line above the slider.
  - `options.min` (`number`): the left end. 0 when not a number.
  - `options.max` (`number`): the right end. 100 when not a number.
  - `options.step` (`number`, optional): the distance between positions, 1 by default (zero or negative also mean 1). the slider has `floor((max - min) / step) + 1` positions, at least 2 and at most 1000.
  - `options.value` (`number`): the current value, snapped to the nearest position. `min` when not a number.
  - `options.subtitle` (`string`, optional): a small line under the slider.
  - `options.label` (`(value: number) => string`, optional): formats the number shown next to the slider, for example `(value) => value + ' ms'`. without it the plain number is shown. tele measures the label of `max` to size the label area.
  - `options.onChange` (`(value: number) => unknown`): runs on every position the user drags over, with `min + position * step`.
- **returns:** `UiElement` with `type: 'slider'`.
- **notes:**
  - unlike other rows, slider changes don't re-run `items()` (that would fight the drag). call `page.invalidate()` if other rows show the value.
  - `min`, `max`, `step` and whether there's a `text` are part of the page structure.
  - `label` runs with the 200 ms budget; if it throws, the plain number is shown.

Example:

```ts
tg.ui.slider({
  text: 'delay before the auto-reply',
  min: 0,
  max: 600,
  step: 30,
  value: delay,
  label: (value) => (value ? `${value / 60} min` : 'at once'),
  onChange: (value) => { delay = value; tg.storage.set('delay', value) },
})
```

### tg.ui.input(options)

```ts
input(options: {
  id?: string
  text: string
  value: string
  placeholder?: string
  maxLength?: number
  multiline?: boolean
  subtitle?: string
  onChange(value: string): unknown
}): UiElement
```

a row that shows a text value; clicking it opens a prompt box to edit the value.

- **grant:** none.
- **parameters:**
  - `options.id` (`string`, optional): your own name for the row.
  - `options.text` (`string`): the row's label and the prompt's title.
  - `options.value` (`string`): the current text, shown on the right and preselected in the prompt.
  - `options.placeholder` (`string`, optional): shown on the row while `value` is empty, and as the field's hint in the prompt.
  - `options.maxLength` (`number`, optional): the most characters the prompt accepts; 0 or missing means no limit.
  - `options.multiline` (`boolean`, optional): a multi-line field in the prompt.
  - `options.subtitle` (`string`, optional): a small line under the row.
  - `options.onChange` (`(value: string) => unknown`): runs with the new text after OK, only when it differs from `value`; then `items()` runs again. cancelling does nothing.
- **returns:** `UiElement` with `type: 'input'`.

Example:

```ts
tg.ui.input({
  text: 'api key',
  value: key ? `${key.slice(0, 4)}...` : '',
  placeholder: 'not set',
  maxLength: 64,
  onChange: (value) => { key = value.trim(); tg.storage.set('key', key) },
})
```

### tg.ui.item(options)

```ts
item(options: {
  id?: string
  text: string
  icon?: string
  value?: string
  subtitle?: string
  onClick(): unknown
}): UiElement
```

a list row: an optional icon (an emoji or short text) before the label, a value on the right, clickable. good for lists of things the script manages.

- **grant:** none.
- **parameters:**
  - `options.id` (`string`, optional): your own name for the row.
  - `options.text` (`string`): the label.
  - `options.icon` (`string`, optional): drawn before the label, for example `'⭐'`. having an icon or not is part of the page structure.
  - `options.value` (`string`, optional): a grey label at the right end.
  - `options.subtitle` (`string`, optional): a small line under the row.
  - `options.onClick` (`() => unknown`): runs on click; then `items()` runs again.
- **returns:** `UiElement` with `type: 'item'`.

Example:

```ts
items: () => watched.map((chat) => tg.ui.item({
  text: chat.name,
  icon: '👁',
  value: `${chat.hits} hits`,
  onClick: () => tg.ui.openChat(chat.id),
}))
```

### tg.ui.color(options)

```ts
color(options: {
  id?: string
  text: string
  value: string
  subtitle?: string
  onChange(value: string): unknown
}): UiElement
```

a row that shows a color value; clicking it opens tele's color editor (the one from the theme editor, with alpha) in a box with save and cancel.

- **grant:** none.
- **parameters:**
  - `options.id` (`string`, optional): your own name for the row.
  - `options.text` (`string`): the row's label and the editor box's title.
  - `options.value` (`string`): the current color as `'#rgb'`, `'#rgba'`, `'#rrggbb'` or `'#rrggbbaa'`, shown as text on the right. an unparsable value opens the editor at the theme's text color.
  - `options.subtitle` (`string`, optional): a small line under the row.
  - `options.onChange` (`(value: string) => unknown`): runs after save with the new color, always as lowercase `'#rrggbbaa'`, only when it differs from `value`; then `items()` runs again.
- **returns:** `UiElement` with `type: 'color'`.
- **notes:** the result plugs straight into `tg.app.theme.setColors`.

Example:

```ts
let accent = tg.storage.get<string>('accent') ?? '#e0569bff'
let undo: Disposer | null = null
tg.ui.color({
  text: 'accent color',
  value: accent,
  onChange: (value) => {
    accent = value
    tg.storage.set('accent', value)
    undo?.()
    undo = tg.app.theme.setColors({ activeButtonBg: value, windowBgActive: value })
  },
})
```

### tg.ui.keybind(options)

```ts
keybind(options: {
  id?: string
  text: string
  value: string
  subtitle?: string
  onChange(value: string): unknown
}): UiElement
```

a row that shows a key combination; clicking it opens a box that captures the next combination the user presses.

- **grant:** none.
- **parameters:**
  - `options.id` (`string`, optional): your own name for the row.
  - `options.text` (`string`): the row's label and the capture box's title.
  - `options.value` (`string`): the current combination in qt's portable text form (`'Ctrl+Shift+K'`), or `''` for none, shown as "not set".
  - `options.subtitle` (`string`, optional): a small line under the row.
  - `options.onChange` (`(value: string) => unknown`): runs with the captured combination, only when it differs from `value`; then `items()` runs again.
- **returns:** `UiElement` with `type: 'keybind'`.
- **notes:**
  - in the box, modifier keys alone are ignored (hold them and press a key), Backspace without modifiers clears the value (`onChange('')`), Escape or Cancel closes without a change.
  - the value is the same format `tg.registerShortcut` takes, so you can re-register the shortcut in `onChange`.

Example:

```ts
let keys = tg.storage.get<string>('keys') ?? 'Ctrl+Shift+T'
let shortcut = tg.registerShortcut(keys, translateDraft)
tg.ui.keybind({
  text: 'translate the draft',
  value: keys,
  onChange: (value) => {
    keys = value
    tg.storage.set('keys', value)
    shortcut()
    if (value) shortcut = tg.registerShortcut(value, translateDraft)
  },
})
```

### tg.registerSettings(page)

```ts
registerSettings(page: Page): Disposer
```

makes `page` the script's settings: the scripts manager renders it inline on the script's page, in its "settings" block.

- **grant:** none.
- **parameters:**
  - `page` (`Page`): a page from `tg.ui.settingsPage`.
- **returns:** `Disposer` that removes the inline settings again (the page itself stays usable).
- **throws:**
  - `TypeError: expected a page from tg.ui.settingsPage` for anything else.
  - `TeleError` `handle-expired` for a disposed page.
- **notes:**
  - a script has one settings page: a second call replaces the first. the disposer only clears it while its page is still the registered one.
  - the inline settings exist only while the script runs. when it's off, its page in the manager has no settings block.

Example:

```ts
export default defineScript({
  name: 'reply delay',
  setup(tg) {
    let seconds = tg.storage.get<number>('seconds') ?? 5
    tg.registerSettings(tg.ui.settingsPage({
      items: () => [tg.ui.slider({ text: 'delay', min: 0, max: 60, value: seconds, label: (value) => `${value} s`, onChange: (value) => { seconds = value; tg.storage.set('seconds', value) } })],
    }))
  },
})
```

### tg.ui.openPage(page)

```ts
openPage(page: Page): void
```

shows `page` right now in a box over this account's window, with a close button.

- **grant:** none.
- **parameters:**
  - `page` (`Page`): a page from `tg.ui.settingsPage`.
- **returns:** nothing.
- **throws:**
  - `TypeError: expected a page from tg.ui.settingsPage`.
  - `TeleError` `handle-expired` for a disposed page.
  - `TeleError` `unsupported` (`tg.ui.openPage: this account has no window`).
- **notes:** the box title is the page title, or the script's name. the box closes when the page is disposed or the script stops.

Example:

```ts
tg.registerChatAction({ id: 'options', text: 'my script options', onClick: () => tg.ui.openPage(page) })
```

### tg.ui.openSection(page)

```ts
openSection(page: Page): boolean
```

opens `page` as a real settings section in this account's window: it replaces the current settings content, shows the page title in the header and has a back arrow, just like tele's own sections.

- **grant:** none.
- **parameters:**
  - `page` (`Page`): a page from `tg.ui.settingsPage`.
- **returns:** `boolean`: `true` when the section opened, `false` when the account has no window or the page was disposed.
- **throws:** `TypeError: expected a page from tg.ui.settingsPage`.
- **notes:** the section title is the page title, or the script's name. if the page is disposed while open, the section goes back. a section restored later (for example by navigating forward) after the script stopped shows "this page is no longer available".

Example:

```ts
tg.ui.registerMenuItem({ place: 'main', emoji: '🧭', text: 'my script', onClick: () => tg.ui.openSection(page) })
```

### tg.ui.registerSettingsEntry(options)

```ts
registerSettingsEntry(options: { title: string, emoji?: string, page: Page, onClick?(): unknown }): Disposer
```

adds a button to tele's main settings page, after tele's own entries and a divider. clicking it opens `page` as a settings section (like `tg.ui.openSection`).

- **grant:** none.
- **parameters:**
  - `options.title` (`string`): the button's label.
  - `options.emoji` (`string`, optional): drawn before the label.
  - `options.page` (`Page`): the page to open.
  - `options.onClick` (`() => unknown`, optional): runs after the section opened, for example to refresh data and `page.invalidate()`.
- **returns:** `Disposer` that removes the button.
- **throws:**
  - `TypeError: expected a page from tg.ui.settingsPage` for something that isn't a page.
  - `TypeError: tg.ui.registerSettingsEntry needs a page from tg.ui.settingsPage` for a disposed page.
  - `TypeError: tg.ui.registerSettingsEntry({ ..., onClick })` when `onClick` is given but isn't a function.
- **notes:** entries of all scripts (of every account) are listed in the order they were registered. they disappear when the script stops.

Example:

```ts
tg.ui.registerSettingsEntry({
  title: 'auto-reply',
  emoji: '💬',
  page,
  onClick: () => { stats = loadStats(); page.invalidate() },
})
```

### tg.ui.openFile(options?)

```ts
openFile(options?: {
  title?: string
  filter?: string
  multiple?: boolean
}): Promise<{ name: string, path: string, bytes: Uint8Array }[] | null>
```

shows the system's open-file dialog over this account's window and resolves with the chosen files, read into memory.

- **grant:** none: the user picks the file, so the script only gets what was chosen.
- **parameters:**
  - `options.title` (`string`, optional): the dialog title, the script's name by default.
  - `options.filter` (`string`, optional): qt's filter syntax, `'Images (*.png *.jpg);;All files (*)'` (groups separated by `;;`). all files by default.
  - `options.multiple` (`boolean`, optional): allow choosing several files.
- **returns:** `Promise<{ name, path, bytes }[] | null>`: one entry per readable file (`name` is the file name, `path` the full path, `bytes` its content), or `null` when the dialog was cancelled or nothing could be read. a single pick is still an array of one.
- **throws:** `TeleError` `unsupported` (`this account has no window`).
- **notes:**
  - files are read whole, so mind the script's 256 MB memory limit; for big files read only `path` and hand it to something that streams (`tg.sendFile` accepts bytes, `tg.unsafe.exec` takes paths).
  - on systems where the dialog hands over content without a path, the entry has empty `name` and `path`.

Example:

```ts
const files = await tg.ui.openFile({ title: 'import word list', filter: 'Text (*.txt);;All files (*)' })
if (files) {
  const words = new TextDecoder().decode(files[0].bytes).split('\n').map((line) => line.trim()).filter(Boolean)
  tg.storage.set('words', words)
  tg.toast(`${words.length} words imported`)
}
```

### tg.ui.saveFile(data, options?)

```ts
saveFile(
  data: Uint8Array | string,
  options?: { title?: string, filter?: string, name?: string },
): Promise<string | null>
```

shows the system's save dialog and writes `data` to the chosen path.

- **grant:** none: the user picks the location (writing to arbitrary paths without asking is `files.write`, through `tg.downloadMedia`).
- **parameters:**
  - `data` (`Uint8Array | string`): the content; a string is written as UTF-8.
  - `options.title` (`string`, optional): the dialog title, the script's name by default.
  - `options.filter` (`string`, optional): qt's filter syntax, like `openFile`.
  - `options.name` (`string`, optional): the suggested file name.
- **returns:** `Promise<string | null>`: the path that was written, or `null` when cancelled.
- **throws:**
  - `TypeError: tg.ui.saveFile needs a Uint8Array or a string` synchronously for other data.
  - `TeleError` `unsupported` (`this account has no window`).
  - the promise rejects with `TypeError: tg.ui.saveFile: can't write <path>` when the file can't be written.
- **notes:** an existing file is replaced (the system dialog asks the user first).

Example:

```ts
const history = await tg.getHistory(ctx.chat, { limit: 100 })
const text = history.reverse().map((message) => `${message.sender?.name ?? '?'}: ${message.text}`).join('\n')
const path = await tg.ui.saveFile(text, { name: `${ctx.chat.name}.txt`, filter: 'Text (*.txt)' })
if (path) tg.toast(`saved to ${path}`)
```

## menus, buttons and commands

places where a script adds its own controls to tele: context menu items, `/commands` in the compose field, keyboard shortcuts, buttons in the chat header and compose bar, rows in profiles, quick buttons next to messages, and items in the left drawer and the tray menu. none of them needs a grant (the user triggers them), every registration returns a `Disposer`, any number per script is fine, and all of them disappear when the script stops.

### the menu editor

tele has a menu editor: Alt + right-click on a context menu lets the user move and hide its items, and tele remembers the layout. items added with `tg.registerMessageAction`, `tg.registerChatAction` and `tg.registerProfileAction` are real items of that system, not something drawn on top.

- **grant:** none.
- **notes:**
  - each action has a stable key `script.<script id>.<id>`, where the script id is the file or folder name with every character outside `a-z 0-9 _` turned into `_`, and `id` is the action's `id`. the layout is saved by that key, so keep ids stable between versions.
  - a new action appears at the bottom of its menu, with tele's experimental icon. once the user moves or hides it in the editor, it stays where they put it.
  - when the script stops (or the disposer runs) the item becomes inactive: it disappears from the menu and from the editor, but its saved placement is kept, so it comes back to the same place when the script starts again. the placement is only forgotten if the user saves the editor while the script is off.
  - the same action registered by the script in several accounts is one menu item.

Example:

```ts
// keep the id stable: renaming 'translate' to 'tr' would lose the user's placement
tg.registerMessageAction({ id: 'translate', text: 'translate', onClick: translate })
```

### tg.registerMessageAction(options)

```ts
registerMessageAction(options: ActionOptions<MessageActionContext>): Disposer
```

adds an item to the message context menu (right-click on a message in a chat and in tele's other message lists).

- **grant:** none.
- **parameters:**
  - `options` (`ActionOptions<MessageActionContext>`): `id`, `text`, `onClick(ctx)` and an optional `visible(ctx)`, see `type ActionOptions`. the context has `chatId`, `chat`, `messageId` and `text`, see `type MessageActionContext`.
- **returns:** `Disposer` that removes the item.
- **throws:**
  - `TypeError: tg.registerMessageAction needs an options object`.
  - `TypeError: tg.registerMessageAction: id must be 1 to 64 of a-z, 0-9 and _`.
  - `TypeError: tg.registerMessageAction needs a text` for an empty or whitespace-only `text`.
  - `TypeError: tg.registerMessageAction: onClick must be a function, visible a function if given`.
  - `TypeError: tg.registerMessageAction: the id '<id>' is already registered` for a second action with the same id in this script.
- **notes:** see "the menu editor" for placement. `visible` runs synchronously while the menu is built; `onClick` runs on the next event-loop turn after the menu closed.

Example:

```ts
tg.registerMessageAction({
  id: 'quote_copy',
  text: 'copy as quote',
  visible: (ctx) => ctx.text.length > 0,
  onClick: (ctx) => {
    tg.clipboard.write(ctx.text.split('\n').map((line) => `> ${line}`).join('\n'))
    tg.toast('copied as a quote')
  },
})
```

### tg.registerChatAction(options)

```ts
registerChatAction(
  options: ActionOptions<ActionContext> & {
    placements?: ('chat' | 'chatRow')[]
  },
): Disposer
```

adds an item to the chat's menus: the ⋮ menu at the top of an open chat (and its replies view) and the context menu of a chat in the chat list.

- **grant:** none.
- **parameters:**
  - `options` (`ActionOptions<ActionContext> & { placements? }`): `id`, `text`, `onClick(ctx)`, `visible(ctx)` like the other actions, plus:
  - `options.placements` (`('chat' | 'chatRow')[]`, optional): where it appears. `'chat'` is the open chat's ⋮ menu, `'chatRow'` the chat list's right-click menu. both by default.
- **returns:** `Disposer` that removes it from every placement.
- **throws:**
  - the same `TypeError`s as `tg.registerMessageAction`, with `tg.registerChatAction` in the message.
  - `TypeError: tg.registerChatAction: unknown placement '<value>', expected 'chat' or 'chatRow'` (nothing is registered then).
- **notes:** each placement is its own menu for the menu editor; the same `id` may be used once per placement. topics and folders don't get chat actions.

Example:

```ts
tg.registerChatAction({
  id: 'export',
  text: 'export the last 100 messages',
  placements: ['chat'],
  visible: (ctx) => ctx.chat.kind !== 'channel',
  onClick: async (ctx) => {
    const messages = await tg.getHistory(ctx.chat, { limit: 100 })
    await tg.ui.saveFile(messages.map((message) => message.text).join('\n'), { name: `${ctx.chat.name}.txt` })
  },
})
```

### tg.registerProfileAction(options)

```ts
registerProfileAction(options: ActionOptions<ActionContext>): Disposer
```

adds an item to the ⋮ menu of a user's, group's or channel's profile.

- **grant:** none.
- **parameters:**
  - `options` (`ActionOptions<ActionContext>`): `id`, `text`, `onClick(ctx)` and an optional `visible(ctx)`; the context is the profile's chat.
- **returns:** `Disposer` that removes the item.
- **throws:** the same `TypeError`s as `tg.registerMessageAction`, with `tg.registerProfileAction` in the message.

Example:

```ts
tg.registerProfileAction({
  id: 'copy_id',
  text: 'copy id',
  onClick: (ctx) => {
    tg.clipboard.write(String(ctx.chatId))
    tg.toast(`copied ${ctx.chatId}`)
  },
})
```

### type ActionOptions

```ts
export interface ActionOptions<C> {
  id: string
  text: string
  onClick(context: C): unknown
  visible?(context: C): boolean
}
```

options shared by the three menu actions; `C` is `MessageActionContext` for message actions and `ActionContext` for chat and profile actions.

- **fields:**
  - `id` (`string`): 1 to 64 characters of `a-z`, `0-9` and `_`, unique per menu within the script. it's part of the menu editor key, so keep it stable.
  - `text` (`string`): the item's label, not empty.
  - `onClick` (`(context: C) => unknown`): runs when the item is chosen, on the next event-loop turn, with the 200 ms budget for its synchronous part. may be async. a throw is a fault.
  - `visible` (`(context: C) => boolean`, optional): runs synchronously every time the menu is built (200 ms budget). a falsy result or a throw hides the item for that menu. without it the item always shows. keep it cheap: no network, no awaits (a returned promise counts as truthy).

Example:

```ts
const options: ActionOptions<ActionContext> = {
  id: 'mute_week',
  text: 'mute for a week',
  visible: (ctx) => ctx.chat.kind === 'supergroup',
  onClick: (ctx) => muteForAWeek(ctx.chat),
}
tg.registerChatAction(options)
```

### type ActionContext

```ts
export interface ActionContext {
  chatId: bigint
  chat: PeerInfo
}
```

what chat actions, profile actions, buttons (`tg.registerButton`) and message actions (as a base) receive.

- **fields:**
  - `chatId` (`bigint`): the chat's marked id: a user's id, `-chatId` for a basic group, `-1000000000000 - channelId` for channels and supergroups.
  - `chat` (`PeerInfo`): the chat's info from tele's cache (name, kind, username, input peer...). pass it straight to any method that takes an `InputPeerLike`: it needs no `account.read(peers)` grant, unlike a bare `chatId`.

Example:

```ts
onClick: async (ctx) => {
  await tg.ui.openProfile(ctx.chat)
}
```

### type MessageActionContext

```ts
export interface MessageActionContext extends ActionContext {
  messageId: number
  text: string
}
```

what a message action's `onClick` and `visible` receive.

- **fields:**
  - `chatId` (`bigint`): the chat's marked id.
  - `chat` (`PeerInfo`): the chat.
  - `messageId` (`number`): the message's id in that chat.
  - `text` (`string`): tele's local copy of the message text (empty for media without a caption, service messages and the like). no grant is needed for it: the user pointed at the message.
- **notes:** for the full message use `tg.getMessages(ctx.chat, ctx.messageId)` (`account.read(messages)`) or `tg.getCachedMessage(ctx.chat, ctx.messageId)`.

Example:

```ts
onClick: async (ctx) => {
  const message = await tg.getCachedMessage(ctx.chat, ctx.messageId)
  if (message?.mediaType === 'photo') await tg.downloadMedia(message, { saveTo: 'downloads' })
}
```

### tg.registerCommand(options)

```ts
registerCommand(options: CommandOptions): Disposer
```

adds a `/name` command to the compose field. it shows in the `/` autocomplete like a bot command (with tele's experimental icon and the script's name after the description), and typing `/name args` and sending, or choosing the row, runs your function instead of sending anything.

- **grant:** none.
- **parameters:**
  - `options` (`CommandOptions`): `name`, `description`, `args`, `chats` and `run(args, ctx)`, see `type CommandOptions`.
- **returns:** `Disposer` that removes the command.
- **throws:**
  - `TypeError: tg.registerCommand needs an options object`.
  - `TypeError: tg.registerCommand: the name must be 1 to 32 of a-z, 0-9 and _`.
  - `TypeError: tg.registerCommand: chats is 'all', 'private', 'groups', 'channels' or an array of them` for a `chats` of the wrong type, `TypeError: tg.registerCommand: unknown chats '<value>'` for an unknown value.
  - `TypeError: tg.registerCommand needs a run function`.
  - `TypeError: tg.registerCommand: /<name> is already registered` when this script already has that name.
- **notes:**
  - running: when the field's whole text is `/name` or `/name args...` (args may span lines) and the user sends, the field is cleared and `run(args, ctx)` is called. typing is matched case-insensitively.
  - the autocomplete: clicking or Enter on a row without `args` runs the command right away; on a row with `args` it inserts `/name ` so the user can type them. Tab always inserts.
  - what `run` returns decides what's sent: a string or `{ text, entities }` goes out through tele's normal send path (drawn as your own message, seen by `interceptSendMessage` and `interceptRpc`); `undefined` or `null` sends nothing.
  - a throw, a rejection, any other return value, or 60 s without settling is a fault: it's logged, and the typed text is put back into the field so nothing is lost.
  - several scripts may register the same name: the first running script in folder order wins.
  - in private chats with people the `/` autocomplete is normally off; it's shown there as soon as any script offers commands for private chats.
  - stopping the script while `run` is pending puts the typed text back.

Example:

```ts
import { defineScript, md } from 'tele'

export default defineScript({
  name: 'text tools',
  setup(tg) {
    tg.registerCommand({ name: 'shrug', description: 'append a shrug', args: 'text', run: (args) => `${args} ¯\\_(ツ)_/¯`.trim() })
    tg.registerCommand({ name: 'loud', description: 'bold upper case', args: 'text', run: (args) => md`**${args.toUpperCase()}**` })
    tg.registerCommand({
      name: 'template',
      description: 'insert the greeting template',
      chats: 'private',
      run: (_args, ctx) => ctx.setText(`hi ${ctx.chat.name}, `),
    })
  },
})
```

### type CommandOptions

```ts
export interface CommandOptions {
  name: string
  description?: string
  args?: string
  chats?: CommandChats | CommandChats[]
  run(
    args: string,
    context: CommandContext,
  ): InputText | void | Promise<InputText | void>
}
```

options of `tg.registerCommand`.

- **fields:**
  - `name` (`string`): 1 to 32 characters of lowercase `a-z`, `0-9` and `_`. a leading `/` is dropped, so `'/shrug'` works too.
  - `description` (`string`, optional): shown in the autocomplete row, followed by ` · <script name>`.
  - `args` (`string`, optional): a hint that the command takes arguments, like `'text'` or `'amount currency'`. its presence changes what choosing the row does (inserts instead of runs).
  - `chats` (`CommandChats | CommandChats[]`, optional): which chats offer the command, `'all'` by default.
  - `run` (`(args: string, context: CommandContext) => InputText | void | Promise<InputText | void>`): does the work. `args` is everything after `/name` (an empty string when nothing was typed). return text to send it, nothing to send nothing. 200 ms for the synchronous part, 60 s until the promise must settle.

Example:

```ts
const options: CommandOptions = {
  name: 'roll',
  description: 'roll NdM dice',
  args: '2d6',
  run: (args) => {
    const [count, sides] = (args || '1d6').split('d').map(Number)
    const rolls = Array.from({ length: count }, () => 1 + Math.floor(Math.random() * sides))
    return `🎲 ${rolls.join(' + ')} = ${rolls.reduce((a, b) => a + b, 0)}`
  },
}
tg.registerCommand(options)
```

### type CommandContext

```ts
export interface CommandContext {
  chat: PeerInfo
  chatId: bigint
  text: string
  setText(text: InputText): void
}
```

the second argument of a command's `run`.

- **fields:**
  - `chat` (`PeerInfo`): the chat the command was typed in.
  - `chatId` (`bigint`): its marked id.
  - `text` (`string`): the whole typed text, `/name` included.
  - `setText` (`(text: InputText) => void`): puts a string or `{ text, entities }` into the compose field with the cursor at the end. works while `run` is still going (show progress, then the result). after the command finished it throws `TeleError` `handle-expired` (`ctx.setText was called after the command finished`); a value that isn't text throws `TypeError: ctx.setText takes a string or { text, entities }`.

Example:

```ts
tg.registerCommand({
  name: 'tldr',
  description: 'summarize the link',
  args: 'url',
  run: async (args, ctx) => {
    ctx.setText('summarizing...')
    const summary = await summarize(args)
    ctx.setText('')
    return summary
  },
})
```

### type CommandChats

```ts
export type CommandChats = 'all' | 'private' | 'groups' | 'channels'
```

chat kinds for `registerCommand` and `registerButton` (and, as a single value, `registerQuickAction`).

- **values:**
  - `'all'`: every chat.
  - `'private'`: chats with users and bots.
  - `'groups'`: basic groups and supergroups.
  - `'channels'`: broadcast channels.
- **notes:** pass an array to combine, `['private', 'groups']`.

Example:

```ts
tg.registerCommand({ name: 'ping', chats: ['private', 'groups'], run: () => 'pong' })
```

### tg.registerShortcut(keys, callback)

```ts
registerShortcut(keys: string, callback: () => unknown): Disposer
```

runs `callback` when the user presses a key combination while this account's main window has focus.

- **grant:** none.
- **parameters:**
  - `keys` (`string`): a key sequence in qt's portable text format: `'Ctrl+Shift+K'`, `'Alt+F1'`, `'Ctrl+K, Ctrl+T'` (a chord: press both in turn). on macOS `Ctrl` means Command, as in qt.
  - `callback` (`() => unknown`): runs on the next event-loop turn after the keys, with the 200 ms budget; may be async.
- **returns:** `Disposer` that removes the shortcut.
- **throws:**
  - `TypeError: tg.registerShortcut(keys, function)` when `keys` isn't a string or `callback` isn't a function.
  - `TypeError: tg.registerShortcut: '<keys>' isn't a key sequence like 'Ctrl+Shift+K'` for a sequence qt can't parse.
- **notes:**
  - if the window doesn't exist yet (tele is still starting), the shortcut is attached as soon as it does.
  - the combination `tg.ui.keybind` captures is in the same format.

Example:

```ts
tg.registerShortcut('Ctrl+Shift+S', () => tg.ui.openChat('me'))
tg.registerShortcut('Ctrl+K, Ctrl+B', () => tg.ui.back())
```

### tg.registerButton(options)

```ts
registerButton(options: {
  place?: 'header' | 'compose'
  icon: string
  tooltip?: string
  chats?: CommandChats | CommandChats[]
  onClick(context: ActionContext): unknown
}): Disposer
```

adds a small button with an emoji or a short text on it, either in the chat's top bar or in the compose bar, in the chats you choose.

- **grant:** none.
- **parameters:**
  - `options.place` (`'header' | 'compose'`, optional): `'header'` (default) puts it in the chat's top bar right of the search button (hidden while messages are selected); `'compose'` puts it in the compose bar left of the emoji button, both in the main chat view and in topics and other sections.
  - `options.icon` (`string`): what's drawn in the button: an emoji or one or two characters.
  - `options.tooltip` (`string`, optional): shown on hover, also the button's accessible name.
  - `options.chats` (`CommandChats | CommandChats[]`, optional): where the button shows, `'all'` by default.
  - `options.onClick` (`(context: ActionContext) => unknown`): runs with `{ chatId, chat }` of the chat the button is in.
- **returns:** `Disposer` that removes the button.
- **throws:**
  - `TypeError: tg.registerButton needs an options object`.
  - `TypeError: tg.registerButton needs an icon and an onClick function`.
  - `TypeError: tg.registerButton: place is 'header' or 'compose'`.
  - `TypeError: tg.registerButton: <value> is not all, private, groups or channels`.
- **notes:** buttons appear and disappear in already open chats as scripts register and dispose them.

Example:

```ts
tg.registerButton({
  place: 'compose',
  icon: '🌐',
  tooltip: 'translate the draft to english',
  chats: ['private', 'groups'],
  onClick: async (ctx) => {
    const draft = await tg.compose.get(ctx.chat)
    if (draft?.text.text) await tg.compose.set(await translate(draft.text.text, 'en'), ctx.chat)
  },
})
```

### tg.registerProfileRow(options)

```ts
registerProfileRow(options: {
  label: string
  value(peer: PeerInfo): string | null | void | Promise<string | null | void>
  onClick?(peer: PeerInfo): unknown
}): Disposer
```

adds an info row to every user, group and channel profile opened afterwards, under tele's own id, real name, aliases and data center rows.

- **grant:** none.
- **parameters:**
  - `options.label` (`string`): the small caption under the value, like "username" or "phone" in tele's rows.
  - `options.value` (`(peer: PeerInfo) => string | null | void | Promise<...>`): computes the row's text for the profile's peer. may be async (up to 10 s); the row appears when it resolves. `null`, `undefined` or `''` hide the row for that profile; anything else is turned into a string.
  - `options.onClick` (`(peer: PeerInfo) => unknown`, optional): makes the value a link; runs with the profile's peer when clicked.
- **returns:** `Disposer`. profiles opened after it no longer get the row.
- **throws:**
  - `TypeError: tg.registerProfileRow needs an options object`.
  - `TypeError: tg.registerProfileRow needs a label, a value function and maybe an onClick function`.
- **notes:** a throw or a rejection in `value` is a fault and hides the row; so does taking longer than 10 s.

Example:

```ts
tg.registerProfileRow({
  label: 'first seen',
  value: (peer) => {
    const seen = tg.storage.get<number>(`seen:${peer.id}`)
    return seen ? new Date(seen).toISOString().slice(0, 10) : null
  },
})
tg.registerProfileRow({
  label: 'marked id (click to copy)',
  value: (peer) => String(peer.id),
  onClick: (peer) => { tg.clipboard.write(String(peer.id)); tg.toast('copied') },
})
```

### tg.registerQuickAction(options)

```ts
registerQuickAction(options: {
  emoji: string
  tooltip?: string
  chats?: 'all' | 'private' | 'groups' | 'channels'
  onClick(context: { chatId: bigint, messageId: number }): unknown
}): Disposer
```

adds a round emoji button that appears next to a message bubble when the mouse is over the message, like the share button next to channel posts.

- **grant:** none.
- **parameters:**
  - `options.emoji` (`string`): the button's emoji (or short text).
  - `options.tooltip` (`string`, optional): shown on hover.
  - `options.chats` (`'all' | 'private' | 'groups' | 'channels'`, optional): one chat kind where the button shows, `'all'` by default. unlike commands and buttons it takes a single value, not an array.
  - `options.onClick` (`(context: { chatId: bigint, messageId: number }) => unknown`): runs with the message's chat (marked id) and id.
- **returns:** `Disposer` that removes the button.
- **throws:**
  - `TypeError: tg.registerQuickAction({ ..., onClick })` when `onClick` isn't a function.
  - `TypeError: tg.registerQuickAction needs an emoji`.
- **notes:** only messages in this account's chats get the script's buttons. to work with the message, resolve it: `tg.getCachedMessage(chatId, messageId)` (a bare `chatId` needs `account.read(peers)`, the message needs `account.read(messages)`).

Example:

```ts
tg.registerQuickAction({
  emoji: '📌',
  tooltip: 'remember this message',
  onClick: ({ chatId, messageId }) => {
    const saved = tg.storage.get<string[]>('pins') ?? []
    tg.storage.set('pins', [...saved, `${chatId}/${messageId}`])
    tg.toast('remembered')
  },
})
```

### tg.ui.registerMenuItem(options)

```ts
registerMenuItem(options: { place: 'main' | 'tray', text: string, emoji?: string, onClick(): unknown }): Disposer
```

adds an item to the left drawer (the main menu behind the ☰ button) or to the tray icon's menu.

- **grant:** none.
- **parameters:**
  - `options.place` (`'main' | 'tray'`): `'main'` adds it at the end of the left drawer, after a separator; `'tray'` adds it to the tray menu before Quit.
  - `options.text` (`string`): the item's label.
  - `options.emoji` (`string`, optional): drawn before the label.
  - `options.onClick` (`() => unknown`): runs when the item is clicked (the drawer closes first).
- **returns:** `Disposer` that removes the item.
- **throws:**
  - `TypeError: tg.ui.registerMenuItem({ ..., onClick })` when `onClick` isn't a function.
  - `TypeError: tg.ui.registerMenuItem: place is 'main' or 'tray'`.
- **notes:**
  - the drawer and the tray belong to the whole app, so items of every account's scripts show there, in registration order.
  - tray items are hidden while tele is locked with a passcode.
  - these items are not part of the menu editor.

Example:

```ts
tg.ui.registerMenuItem({ place: 'main', emoji: '📊', text: 'chat stats', onClick: () => tg.ui.openSection(statsPage) })
tg.ui.registerMenuItem({ place: 'tray', emoji: '🌙', text: 'toggle night mode', onClick: () => tg.app.theme.setDark(!tg.app.theme.get().dark) })
```

## navigation and compose

moving around this account's window and working with the text the user is typing. navigation needs no grant; the compose field is a draft, so it uses the `draft` scopes of `account.read` and `account.write`.

a note on peers: these methods take any `InputPeerLike`. a `PeerInfo` (like `ctx.chat` in menus and buttons), a `Message`, `'me'` or a TL input peer work without extra grants; a bare marked id or a username is looked up through `tg.peers` and so needs `account.read(peers)`.

### tg.ui.openChat(peer, options?)

```ts
openChat(peer: InputPeerLike, options?: { message?: number }): Promise<void>
```

opens a chat in this account's window, optionally scrolled to a message (which is highlighted, like after clicking a reply).

- **grant:** none (`account.read(peers)` when `peer` is a bare id or a username).
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `options.message` (`number`, optional): a message id in that chat to jump to. without it the chat opens where tele would open it (at the first unread message).
- **returns:** `Promise<void>` that resolves once the navigation is queued; the chat opens on the next event-loop turn.
- **throws:**
  - rejects with `TeleError` `not-found` for an id tele has never seen or a free username.
  - rejects with `TypeError: this peer isn't in tele's cache` for an input peer of a chat tele hasn't loaded.
  - rejects with `TeleError` `unsupported` (`this account has no window`).
- **notes:** the chat opens like a click in the chat list: the stack of sections opened before it is cleared.

Example:

```ts
tg.registerShortcut('Ctrl+Shift+Y', () => tg.ui.openChat('me'))

tg.registerQuickAction({
  emoji: '↩️',
  tooltip: 'jump to the replied message',
  onClick: async ({ chatId, messageId }) => {
    const message = await tg.getCachedMessage(chatId, messageId)
    if (message?.replyToMessageId) await tg.ui.openChat(message, { message: message.replyToMessageId })
  },
})
```

### tg.ui.openProfile(peer)

```ts
openProfile(peer: InputPeerLike): Promise<void>
```

opens the profile (info section) of a user, group or channel.

- **grant:** none (`account.read(peers)` for a bare id or a username).
- **parameters:**
  - `peer` (`InputPeerLike`): whose profile.
- **returns:** `Promise<void>`, resolved once the navigation is queued.
- **throws:** like `tg.ui.openChat`: `not-found`, `TypeError: this peer isn't in tele's cache`, `unsupported`.

Example:

```ts
tg.registerMessageAction({
  id: 'sender_profile',
  text: 'open the sender profile',
  onClick: async (ctx) => {
    const message = await tg.getCachedMessage(ctx.chat, ctx.messageId)
    if (message?.sender) await tg.ui.openProfile(message.sender)
  },
})
```

### tg.ui.openSettings(section?)

```ts
openSettings(section?: SettingsSection): void
```

opens tele's settings at a section.

- **grant:** none.
- **parameters:**
  - `section` (`SettingsSection`, optional): which section, `'main'` by default. see `type SettingsSection` for the list.
- **returns:** nothing. the section opens on the next event-loop turn.
- **throws:**
  - `TypeError: tg.ui.openSettings: <name> isn't a settings section` for anything else.
  - `TeleError` `unsupported` (`this account has no window`).

Example:

```ts
tg.registerChatAction({ id: 'privacy', text: 'privacy settings', onClick: () => tg.ui.openSettings('privacy') })
```

### type SettingsSection

```ts
export type SettingsSection =
  | 'main' | 'chat' | 'notifications' | 'privacy' | 'advanced' | 'folders'
  | 'calls' | 'information' | 'premium' | 'sessions' | 'blocked'
  | 'shortcuts' | 'tele'
```

the settings sections `tg.ui.openSettings` can open.

- **values:**
  - `'main'`: the main settings page with the list of sections (and scripts' `registerSettingsEntry` buttons).
  - `'chat'`: chat settings: themes, backgrounds, text size, stickers and emoji.
  - `'notifications'`: notifications and sounds.
  - `'privacy'`: privacy and security.
  - `'advanced'`: advanced: data and storage, connection type, window and system integration.
  - `'folders'`: chat folders.
  - `'calls'`: speakers, microphone and camera for calls.
  - `'information'`: my account: name, username, bio, birthday.
  - `'premium'`: the telegram premium page.
  - `'sessions'`: active sessions (devices).
  - `'blocked'`: the blocked users list.
  - `'shortcuts'`: keyboard shortcuts.
  - `'tele'`: tele's own settings page.

Example:

```ts
tg.ui.registerMenuItem({ place: 'main', emoji: '⚙️', text: 'tele settings', onClick: () => tg.ui.openSettings('tele') })
```

### tg.ui.back()

```ts
back(): void
```

goes back one step in this account's window, like the back arrow: from a section to the previous one, from a profile to the chat.

- **grant:** none.
- **returns:** nothing. it happens on the next event-loop turn.
- **throws:** `TeleError` `unsupported` (`this account has no window`).

Example:

```ts
tg.registerShortcut('Alt+Left', () => tg.ui.back())
```

### tg.ui.current()

```ts
current(): { chatId: bigint | null, windowActive: boolean }
```

tells what this account's window shows right now.

- **grant:** none.
- **returns:**
  - `chatId` (`bigint | null`): the marked id of the open chat, `null` when no chat is open or the account has no window.
  - `windowActive` (`boolean`): whether the window is the focused one on the desktop. `false` when minimized, behind other apps or missing.
- **notes:** cheap and synchronous, fine to call in listeners: for example to skip a notification for the chat the user is looking at.

Example:

```ts
tg.onNewMessage((message) => {
  const { chatId, windowActive } = tg.ui.current()
  if (windowActive && chatId === message.chatId) return
  if (message.mentioned) tg.notify(message.chat?.name ?? 'mention', message.text)
})
```

### tg.ui.onChatOpened(callback)

```ts
onChatOpened(
  callback: (opened: { chatId: bigint | null, chat: PeerInfo | null }) => unknown,
): Disposer
```

calls `callback` every time this account's window switches to another chat, or to no chat.

- **grant:** none.
- **parameters:**
  - `callback` (`(opened) => unknown`): gets `{ chatId, chat }`: the marked id and info of the chat now open, both `null` when none is (for example after Escape closed the chat). runs on the next event-loop turn with the 200 ms budget.
- **returns:** `Disposer` that stops the calls.
- **throws:** `TypeError: tg.ui.onChatOpened(function)`.
- **notes:** it doesn't fire for the chat that is open when you subscribe; read `tg.ui.current()` for that. if the window doesn't exist yet, the subscription starts once it does.

Example:

```ts
tg.ui.onChatOpened(({ chat }) => {
  if (chat?.scam || chat?.fake) tg.toast(`careful: ${chat.name} is marked as ${chat.scam ? 'scam' : 'fake'}`)
})
```

### tg.compose

```ts
readonly compose: Compose
```

the compose field (the message input at the bottom of a chat). see `type Compose` and the four methods below.

- **grant:** `account.read(draft)` to read and listen, `account.write(draft)` to change.
- **notes:**
  - without a `peer` argument the methods work on the open chat's field. with one, they work on that chat's field if it's open somewhere (the main chat view, a topic or another section); otherwise there's no field and they return `null` / `false`.
  - this is the live field, not the cloud draft. for saved drafts of chats that aren't open see `tg.local.draft` and `tg.setDraft`.

Example:

```ts
const draft = await tg.compose.get()
if (draft) await tg.compose.set(draft.text.text.trim())
```

### type Compose

```ts
export interface Compose {
  get(peer?: InputPeerLike): Promise<{ chatId: bigint, text: Required<TextWithEntities> } | null>
  set(text: InputText, peer?: InputPeerLike): Promise<boolean>
  insert(text: InputText, peer?: InputPeerLike): Promise<boolean>
  onInput(callback: (input: { chatId: bigint, text: string }) => unknown): Disposer
}
```

the type of `tg.compose`.

- **fields:**
  - `get` (`(peer?) => Promise<{ chatId, text } | null>`): read the field, see `tg.compose.get`.
  - `set` (`(text, peer?) => Promise<boolean>`): replace the field's text, see `tg.compose.set`.
  - `insert` (`(text, peer?) => Promise<boolean>`): insert at the cursor, see `tg.compose.insert`.
  - `onInput` (`(callback) => Disposer`): listen to changes, see `tg.compose.onInput`.

Example:

```ts
const compose: Compose = tg.compose
```

### tg.compose.get(peer?)

```ts
get(peer?: InputPeerLike): Promise<{ chatId: bigint, text: Required<TextWithEntities> } | null>
```

reads the text in a compose field, with its formatting as entities.

- **grant:** `account.read(draft)`.
- **parameters:**
  - `peer` (`InputPeerLike`, optional): whose field. the open chat's by default.
- **returns:** `Promise<{ chatId, text } | null>`: `chatId` is the field's chat (marked id), `text` is `{ text, entities }` (bold, links, custom emoji... as TL entities). `null` when there's no such field (no chat open, or that chat isn't open).
- **throws:** `TeleError` `not-granted` without the grant (synchronously inside the async call, so the promise rejects).

Example:

```ts
const current = await tg.compose.get()
if (current && current.text.text.length > 4000) tg.toast(`${current.text.text.length} characters, that's two messages`)
```

### tg.compose.set(text, peer?)

```ts
set(text: InputText, peer?: InputPeerLike): Promise<boolean>
```

replaces the whole text of a compose field and puts the cursor at the end.

- **grant:** `account.write(draft)`.
- **parameters:**
  - `text` (`InputText`): a string, or `{ text, entities }` (from `md`/`html`) to set formatted text.
  - `peer` (`InputPeerLike`, optional): whose field, the open chat's by default.
- **returns:** `Promise<boolean>`: `true` when a field was changed, `false` when there was none.
- **throws:**
  - `TeleError` `not-granted` without the grant.
  - `TypeError: tg.compose.set needs a string or { text, entities }`.
- **notes:** the change fires `tg.compose.onInput` (yours too), so don't set unconditionally from `onInput`.

Example:

```ts
import { md } from 'tele'

await tg.compose.set(md`**meeting notes** ${new Date().toISOString().slice(0, 10)}\n`)
```

### tg.compose.insert(text, peer?)

```ts
insert(text: InputText, peer?: InputPeerLike): Promise<boolean>
```

inserts text at the cursor, keeping the formatting of the text around it, and moves the cursor after the inserted part.

- **grant:** `account.write(draft)`.
- **parameters:**
  - `text` (`InputText`): the text to insert, plain or with entities.
  - `peer` (`InputPeerLike`, optional): whose field, the open chat's by default.
- **returns:** `Promise<boolean>`: `true` when inserted, `false` without a field.
- **throws:**
  - `TeleError` `not-granted` without the grant.
  - `TypeError: tg.compose.insert needs a string or { text, entities }`.
- **notes:** a selection isn't replaced: the text goes in at the cursor position.

Example:

```ts
tg.registerButton({
  place: 'compose',
  icon: '🕒',
  tooltip: 'insert the time',
  onClick: (ctx) => tg.compose.insert(new Date().toTimeString().slice(0, 5), ctx.chat),
})
```

### tg.compose.onInput(callback)

```ts
onInput(callback: (input: { chatId: bigint, text: string }) => unknown): Disposer
```

calls `callback` after every change in any compose field of this account.

- **grant:** `account.read(draft)`.
- **parameters:**
  - `callback` (`(input) => unknown`): gets `{ chatId, text }`: the field's chat (marked id) and its plain text after the change. runs on the next event-loop turn with the 200 ms budget; may be async.
- **returns:** `Disposer` that stops the calls.
- **throws:**
  - `TypeError: tg.compose.onInput(function)`.
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - it fires for every keystroke, paste and programmatic change, including `tg.compose.set` / `insert` from this script. guard against loops: only change the field when the text actually needs it.
  - `text` is plain; call `tg.compose.get(chatId)` for entities.

Example:

```ts
const snippets: Record<string, string> = { ':shrug:': '¯\\_(ツ)_/¯', ':tm:': '™' }
tg.compose.onInput(async ({ chatId, text }) => {
  let next = text
  for (const [key, value] of Object.entries(snippets)) next = next.replaceAll(key, value)
  if (next !== text) await tg.compose.set(next, chatId)
})
```

## interception

three gates that run before tele acts on something the user did: opening a link, showing a desktop notification, and dropping or pasting into a chat. a gate's interceptor decides whether tele goes on. they all need a caution-tier grant, and all of them fail open: if an interceptor throws, returns something unexpected or takes longer than 10 s, it's a fault and tele behaves as if no script were there. when several scripts intercept, they run in folder order, each script's interceptors in registration order; the first `'drop'` wins. when the script stops, pending gates finish as if it said nothing.

### tg.interceptLink(pattern?, interceptor)

```ts
interceptLink(interceptor: LinkInterceptor): Disposer
interceptLink(pattern: RegExp, interceptor: LinkInterceptor): Disposer
```

sees every link opened in this account's window before tele handles it, and can let it open, block it, or replace it with another url. covers clicks in messages, bios, buttons and bot keyboards, `tg.openUrl` from any script, and the like.

- **grant:** `interceptLink` (caution, "see, change or block every link you open").
- **parameters:**
  - `pattern` (`RegExp`, optional): only links matching it reach `interceptor`; others pass by untouched. `lastIndex` is reset before each test, so `g` and `y` flags are safe.
  - `interceptor` (`LinkInterceptor`): `({ url }) => verdict`, may be async, see `type LinkInterceptor` and `type LinkVerdict`.
- **returns:** `Disposer` that removes the interceptor.
- **throws:**
  - `TypeError: tg.interceptLink(function)` without a function.
  - `TypeError: tg.interceptLink(pattern?, function)` when the first of two arguments isn't a `RegExp`.
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - a returned url is passed on: the next interceptor (of this script, then of later scripts) sees the new url, and tele opens the final one.
  - the link tele finally opens doesn't go through the interceptors again.
  - fails open: a throw, a wrong value or 10 s opens the original link.

Example:

```ts
const TRACKING = /^(utm_[a-z_]+|fbclid|gclid|yclid|mc_eid|igshid)$/i
tg.interceptLink(/^https?:\/\/[^?#]*\?/, ({ url }) => {
  const [, base, query, hash = ''] = /^([^?#]*)\?([^#]*)(#.*)?$/.exec(url) ?? []
  if (base === undefined) return 'open'
  const kept = query.split('&').filter((pair) => pair && !TRACKING.test(pair.split('=')[0]))
  const clean = base + (kept.length ? `?${kept.join('&')}` : '') + hash
  return clean === url ? 'open' : clean
})
tg.interceptLink(/^https?:\/\/([^/]*\.)?bad-site\.example(\/|$)/, () => {
  tg.toast('blocked a link to bad-site.example')
  return 'drop'
})
```

### type LinkInterceptor

```ts
export type LinkInterceptor = (
  context: { url: string },
) => LinkVerdict | null | void | Promise<LinkVerdict | null | void>
```

the function `tg.interceptLink` calls.

- **parameters:**
  - `context.url` (`string`): the link as it would open now (after earlier interceptors' rewrites).
- **returns:** a `LinkVerdict`, `null` / `undefined` (same as `'open'`), or a promise of one.

Example:

```ts
const toNitter: LinkInterceptor = ({ url }) => url.replace(/^https:\/\/(www\.)?(twitter|x)\.com\//, 'https://nitter.net/')
tg.interceptLink(/^https:\/\/(www\.)?(twitter|x)\.com\//, toNitter)
```

### type LinkVerdict

```ts
export type LinkVerdict = 'open' | 'drop' | string
```

what a link interceptor answers.

- **values:**
  - `'open'` (or `null`, `undefined`, nothing): go on with the current url.
  - `'drop'`: don't open anything. later interceptors don't run.
  - any other string: the new url to continue with.
- **notes:** any other kind of value is a fault (`TypeError: an interceptor returns 'open', 'drop', a new url or nothing`) and the original link opens.

Example:

```ts
tg.interceptLink(({ url }) => (url.startsWith('http://') ? url.replace('http://', 'https://') : 'open'))
```

### tg.interceptNotification(interceptor)

```ts
interceptNotification(
  interceptor: (
    notification: NotificationInfo,
  ) => NotificationVerdict | null | void | Promise<NotificationVerdict | null | void>,
): Disposer
```

runs when tele is about to schedule a desktop notification for this account and can hide it. the message itself is untouched (it arrives, counts as unread, shows in the chat); only the notification is skipped.

- **grant:** `interceptNotification` (caution, "see or hide your notifications"). to get the message's content in `notification.message` add `account.read(messages)`.
- **parameters:**
  - `interceptor` (`(notification: NotificationInfo) => NotificationVerdict | null | void | Promise<...>`): gets the notification's info, answers `'show'` or `'drop'`, may be async. see `type NotificationInfo`.
- **returns:** `Disposer` that removes the interceptor.
- **throws:**
  - `TypeError: tg.interceptNotification(function)`.
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - it runs at the very start of tele's scheduling, before tele applies mute settings and the like, so it also sees messages from muted chats that tele wouldn't announce anyway. `'show'` hands the notification back to tele's usual checks; it never makes a muted chat notify.
  - fails open: a throw, a wrong value (`TypeError: an interceptor returns 'show', 'drop' or nothing`) or 10 s shows the notification. while the gate runs, the notification waits.

Example:

```ts
export default defineScript({
  name: 'quiet coworkers',
  grants: ['interceptNotification', 'account.read(messages)'],
  setup(tg) {
    tg.interceptNotification(({ kind, message }) => {
      const hour = new Date().getHours()
      const offHours = hour < 9 || hour >= 19
      if (offHours && kind === 'message' && message?.chat?.name.includes('work')) return 'drop'
      return 'show'
    })
  },
})
```

### type NotificationInfo

```ts
export interface NotificationInfo {
  readonly chatId: bigint
  readonly kind: 'message' | 'reaction' | 'pollVote'
  readonly fromId: bigint | null
  readonly message: Message | null
}
```

what `tg.interceptNotification`'s interceptor receives, a frozen object.

- **fields:**
  - `chatId` (`bigint`): the chat's marked id.
  - `kind` (`'message' | 'reaction' | 'pollVote'`): a new message, a reaction to your message, or a vote in your poll.
  - `fromId` (`bigint | null`): for reactions and poll votes, the marked id of who reacted or voted. `null` for messages (use `message.senderId`).
  - `message` (`Message | null`): the message the notification is about (for reactions and votes, your message), from tele's message cache. `null` without `account.read(messages)` or when it isn't cached. login codes from telegram's service account are masked as usual.

Example:

```ts
tg.interceptNotification((info) => {
  if (info.kind === 'reaction' && info.fromId === annoyingFriendId) return 'drop'
})
```

### type NotificationVerdict

```ts
export type NotificationVerdict = 'show' | 'drop'
```

what a notification interceptor answers.

- **values:**
  - `'show'` (or `null`, `undefined`, nothing): let tele show it (later interceptors still run).
  - `'drop'`: don't show it; later interceptors don't run.

Example:

```ts
tg.interceptNotification(({ message }) => (message?.text.startsWith('[bot]') ? 'drop' : 'show'))
```

### tg.interceptDrop(interceptor)

```ts
interceptDrop(interceptor: (drop: DropInfo) => DropVerdict | void | Promise<DropVerdict | void>): Disposer
```

sees what is about to open tele's "send files" box in a chat: files dropped onto the chat, images and files pasted into it, links dragged from a browser. the interceptor can let tele go on or handle the drop itself.

- **grant:** `interceptDrop` (caution, "see the files and text you drop or paste into chats and handle them instead of tele").
- **parameters:**
  - `interceptor` (`(drop: DropInfo) => DropVerdict | void | Promise<...>`): gets what was dropped, answers `'accept'` (tele goes on as usual) or `'drop'` (tele ignores it). may be async. see `type DropInfo`.
- **returns:** `Disposer` that removes the interceptor.
- **throws:**
  - `TypeError: tg.interceptDrop(function)`.
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - while interceptors run, tele holds a copy of the dropped data; after every script accepted, it replays the drop exactly as it came, so the usual send box follows.
  - secret chats are never intercepted.
  - fails open: a throw, a wrong value (`TypeError: an interceptor returns 'accept', 'drop' or nothing`) or 10 s accepts the drop. a `tg.ui.dialog` inside the interceptor counts toward the 10 s.

Example:

```ts
tg.interceptDrop(async (drop) => {
  const big = drop.files.filter((file) => file.size > 200 * 1024 * 1024)
  if (big.length) {
    tg.toast(`not sending ${big.map((file) => file.name).join(', ')}: over 200 MB`)
    return 'drop'
  }
  return 'accept'
})
```

### type DropInfo

```ts
export interface DropInfo {
  chatId: bigint
  files: { name: string, path: string, size: number }[]
  urls: string[]
  text: string
  image: boolean
}
```

what a drop interceptor receives, a frozen object.

- **fields:**
  - `chatId` (`bigint`): the chat it was dropped on or pasted into (marked id).
  - `files` (`{ name: string, path: string, size: number }[]`): local files: `name` is the file name, `path` the full path, `size` in bytes. scripts get paths, not contents; a path is what `tg.unsafe.exec` needs.
  - `urls` (`string[]`): dropped urls that aren't local files (links dragged from a browser).
  - `text` (`string`): the text part of the data, `''` when there's none. drags from other apps often carry one (a link's address, a file list); plain text pasted into the field doesn't go through this gate.
  - `image` (`boolean`): `true` when the data holds an image (a screenshot pasted from the clipboard, an image dragged from a browser). the pixels aren't passed to the script.

Example:

```ts
tg.interceptDrop((drop) => {
  console.log(`${drop.files.length} files, ${drop.urls.length} urls, text: ${drop.text.length} chars, image: ${drop.image}`)
})
```

### type DropVerdict

```ts
export type DropVerdict = 'accept' | 'drop'
```

what a drop interceptor answers.

- **values:**
  - `'accept'` (or nothing): go on; after all scripts accept, tele handles the drop normally.
  - `'drop'`: tele ignores the drop or paste; later interceptors don't run. handle it yourself if you like (send the files your way, upload them somewhere).

Example:

```ts
tg.interceptDrop((drop) => (drop.files.some((file) => /\.(exe|scr|bat|cmd|msi)$/i.test(file.name)) ? 'drop' : 'accept'))
```

## the widget layer

`tg.ui.widgets` is the generic escape hatch: it shows a script tele's widget tree (the qt widgets of every tele window) and lets it change what's there and add to it. use it for screens no dedicated api covers, like the table in a gift box or a menu tele builds on the fly.

it reaches into internals: widget types and layouts are tele's and tdesktop's own classes and can change in any version. when a dedicated api exists (`registerMessageAction`, `registerButton`, `registerProfileRow`, `tg.ui.settingsPage`...), use that; it keeps working across updates.

- **grant:** `ui.read` (caution, "see everything tele shows in its windows: texts, buttons and layout") to look; `ui.write` (caution, "change, hide or add to anything tele shows") to change and add; `unsafe.automate` (dangerous, "press any button in tele for you") to click.
- **notes:**
  - the tree is app-wide: every window of tele, whichever account it shows, not only this script's account.
  - every change a script makes (`setVisible`, `setText`, `insert`, `insertRow`, `addMenuItem`) is undone when it stops, in reverse order.
  - all of it runs on tele's main thread; a `find` over a big window walks thousands of widgets, so narrow it with `within` and a `limit`, and prefer `observe` to polling.

Example:

```ts
for (const root of tg.ui.widgets.roots()) console.log(root.type, root.rect)
const buttons = tg.ui.widgets.find({ role: 'button', within: { type: /MainWindow/ } }, 20)
console.log(buttons.map((button) => button.name || button.type))
```

### tg.ui.widgets

```ts
readonly widgets: Widgets
```

the entry point of the widget layer, see `type Widgets`.

- **grant:** `ui.read` for `roots`, `find` and `observe`.

Example:

```ts
const { widgets } = tg.ui
```

### type Widgets

```ts
export interface Widgets {
  roots(): Widget[]
  find(selector: WidgetSelector, limit?: number): Widget[]
  observe(selector: WidgetSelector, callback: (widget: Widget) => unknown): Disposer
}
```

the type of `tg.ui.widgets`.

- **fields:**
  - `roots` (`() => Widget[]`): the visible top-level windows, see `tg.ui.widgets.roots()`.
  - `find` (`(selector, limit?) => Widget[]`): search every window, see `tg.ui.widgets.find`.
  - `observe` (`(selector, callback) => Disposer`): get called for matching widgets as they appear, see `tg.ui.widgets.observe`.

Example:

```ts
const widgets: Widgets = tg.ui.widgets
```

### tg.ui.widgets.roots()

```ts
roots(): Widget[]
```

lists tele's visible top-level widgets: main windows, separate chat windows, the media viewer, open popup menus, tooltips and other windows of their own.

- **grant:** `ui.read`.
- **returns:** `Widget[]`, one handle per visible top-level widget.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
const windows = tg.ui.widgets.roots().filter((root) => root.role === 'window')
console.log(`${windows.length} tele windows open`)
```

### tg.ui.widgets.find(selector, limit?)

```ts
find(selector: WidgetSelector, limit?: number): Widget[]
```

searches every tele window for widgets that match `selector`, top-level widgets included, in tree order (parents before children).

- **grant:** `ui.read`.
- **parameters:**
  - `selector` (`WidgetSelector`): what to look for, see `type WidgetSelector`.
  - `limit` (`number`, optional): the most widgets to return, 1000 by default (at least 1).
- **returns:** `Widget[]`, empty when nothing matches.
- **throws:**
  - `TypeError: a widget selector is an object: { type?, name?, role?, within?, hidden? }`.
  - `TypeError: selector.type must be a string or a RegExp` (or `selector.name`).
  - `TeleError` `not-granted` without the grant.
- **notes:** without `hidden: true`, hidden widgets and everything inside them are skipped.

Example:

```ts
const [main] = tg.ui.widgets.find({ type: /MainWindow/ }, 1)
const labels = tg.ui.widgets.find({ type: 'Ui::FlatLabel', within: { type: /PopupMenu|Box$/ } }, 50)
```

### tg.ui.widgets.observe(selector, callback)

```ts
observe(selector: WidgetSelector, callback: (widget: Widget) => unknown): Disposer
```

calls `callback` for every matching widget that's already visible, and then every time a matching widget is shown: a box opens, a menu pops up, a screen is built. this is how a script decorates screens tele creates on demand.

- **grant:** `ui.read`.
- **parameters:**
  - `selector` (`WidgetSelector`): which widgets. `hidden` is ignored: a widget is reported when it becomes visible.
  - `callback` (`(widget: Widget) => unknown`): gets the widget, on the next event-loop turn after it was shown (so its children and texts are usually there), with the 200 ms budget. may be async.
- **returns:** `Disposer` that stops the calls. changes already made stay until the script stops.
- **throws:**
  - `TypeError: tg.ui.widgets.observe(selector, callback)` when `callback` isn't a function.
  - the selector `TypeError`s of `find`.
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - `type` and `role` are checked when the widget is shown; `name` and `within` are checked when the callback is about to run, so they see the widget's state at that moment.
  - a widget that is hidden and shown again is reported again: remember ids (`widget.id`) to handle each widget once.
  - only the first 4096 already visible matches are reported at registration.

Example:

```ts
const seen = new Set<number>()
tg.ui.widgets.observe({ type: /PopupMenu/ }, (menu) => {
  if (seen.has(menu.id)) return
  seen.add(menu.id)
  console.log('a menu opened with', menu.find({ role: 'menuitem' }).map((item) => item.name))
})
```

### type WidgetSelector

```ts
export interface WidgetSelector {
  type?: string | RegExp
  name?: string | RegExp
  role?: string
  within?: WidgetSelector
  hidden?: boolean
}
```

describes widgets for `find`, `observe` and `closest`. every given field must match; an empty selector `{}` matches every widget.

- **fields:**
  - `type` (`string | RegExp`, optional): the widget's c++ class name (`widget.type`). a string must match exactly; a `RegExp` matches anywhere unless anchored, and its `i` flag is honoured (other flags are ignored).
  - `name` (`string | RegExp`, optional): the widget's accessible name (`widget.name`), exact for a string, a pattern for a `RegExp`.
  - `role` (`string`, optional): the accessible role, exact, one of the names listed under `widget.role`.
  - `within` (`WidgetSelector`, optional): the match must be inside a widget matching this selector (searched first, up to 1000 scopes). for `closest`, the ancestor itself must be inside a match of `within`.
  - `hidden` (`boolean`, optional): `true` also finds hidden widgets. visible ones only by default. `observe` and `closest` ignore it.

Example:

```ts
const selector: WidgetSelector = { role: 'button', name: /^(share|copy link)$/i, within: { type: /Box$/ } }
```

### type Widget

```ts
export interface Widget {
  readonly id: number
  readonly alive: boolean
  readonly type: string
  readonly role: string
  readonly name: string
  readonly value: string
  readonly description: string
  readonly visible: boolean
  readonly rect: { x: number, y: number, width: number, height: number }
  parent(): Widget | null
  children(): Widget[]
  find(selector: WidgetSelector, limit?: number): Widget[]
  closest(selector: WidgetSelector): Widget | null
  setVisible(visible: boolean): void
  setText(text: string): boolean
  insert(where: 'before' | 'after', page: Page): Disposer
  insertRow(row: { label: string, value: string, index?: number, onClick?(): unknown }): Disposer
  addMenuItem(item: { text: string, onClick(): unknown }): Disposer
  click(): boolean
}
```

a live handle to one widget, a frozen object. its getters read the widget every time, so they always show its current state; nothing is copied.

- **fields:**
  - `id` (`number`): the widget's id, the same for as long as the widget lives, also across `find` calls. use it to remember widgets.
  - `alive` (`boolean`): `false` once tele destroyed the widget (a box closed, a screen was rebuilt).
  - `type` (`string`): the c++ class name.
  - `role`, `name`, `value`, `description` (`string`): from tele's accessibility layer.
  - `visible` (`boolean`): whether it's shown.
  - `rect`: its geometry inside its window.
  - `parent`, `children`, `find`, `closest`: walk the tree.
  - `setVisible`, `setText`, `insert`, `insertRow`, `addMenuItem`: change or add (`ui.write`).
  - `click`: press it (`unsafe.automate`).
- **notes:**
  - the getters and `parent`, `children`, `find`, `closest` need `ui.read`; the changing methods need `ui.write`; `click` needs `unsafe.automate`. `id` needs nothing.
  - on a destroyed widget the getters return empty values (`''`, `false`, a zero `rect`), `parent()` is `null`, `children()` and `find()` are empty, `setText` and `click` return `false`, `setVisible` does nothing, and `insert`, `insertRow`, `addMenuItem` throw `TeleError` `not-found`.

Example:

```ts
const [label] = tg.ui.widgets.find({ type: 'Ui::FlatLabel', name: /^model$/i }, 1)
if (label) setTimeout(() => console.log(label.alive ? 'still open' : 'closed'), 10_000)
```

### widget.id

```ts
readonly id: number
```

the widget's id: a positive number given the first time a script sees the widget, stable for the widget's whole life and shared by all scripts.

- **grant:** none (reading the handle's own field).
- **returns:** `number`.
- **notes:** ids aren't reused while tele runs, but they don't survive a restart, and a screen that tele rebuilds consists of new widgets with new ids.

Example:

```ts
const decorated = new Set<number>()
tg.ui.widgets.observe({ type: /TableLayout/ }, (table) => {
  if (decorated.has(table.id)) return
  decorated.add(table.id)
})
```

### widget.alive

```ts
readonly alive: boolean
```

`true` while the widget exists, `false` after tele destroyed it.

- **grant:** `ui.read`.
- **returns:** `boolean`.

Example:

```ts
const timer = setInterval(() => {
  if (!box.alive) clearInterval(timer)
}, 1000)
```

### widget.type

```ts
readonly type: string
```

the widget's most specific c++ class name with its namespace, such as `'Platform::MainWindow'`, `'Ui::FlatLabel'`, `'Ui::TableLayout'`, `'Ui::PopupMenu'` or `'Ui::VerticalLayout'`. boxes are usually classes whose names end in `Box`, like `'Ui::GenericBox'`.

- **grant:** `ui.read`.
- **returns:** `string`, `''` for a destroyed widget.
- **notes:** these are internal class names. log `type` while exploring (`console.log(widget.children().map((child) => child.type))`), match with a `RegExp` that is no stricter than needed, and expect renames after tele updates. tables in gift, giveaway and transaction boxes are `Ui::TableLayout`; context and ⋮ menus are `Ui::PopupMenu`.

Example:

```ts
const types = new Set(tg.ui.widgets.find({}, 1000).map((widget) => widget.type))
console.log([...types].sort().join('\n'))
```

### widget.role

```ts
readonly role: string
```

the widget's accessible role, a simple word describing what it is.

- **grant:** `ui.read`.
- **returns:** `string`, one of: `'button'`, `'checkbox'`, `'radio'`, `'text'`, `'link'`, `'input'`, `'list'`, `'listitem'`, `'dialog'`, `'window'`, `'group'`, `'tab'`, `'tabs'`, `'menuitem'`, `'menu'`, `'slider'`, `'separator'`, `'image'`, `'scrollbar'`, `'tooltip'`, `'table'`, `'cell'`, or `'widget'` for anything else (and for widgets that aren't tele's own).
- **notes:** roles change much less often than class names, so `role` plus `name` is the sturdiest selector.

Example:

```ts
const checkboxes = tg.ui.widgets.find({ role: 'checkbox', within: { type: /Box$/ } })
```

### widget.name

```ts
readonly name: string
```

the widget's accessible name: what a screen reader would read, usually its visible text (a label's text, a button's caption, a menu item's label).

- **grant:** `ui.read`.
- **returns:** `string`, `''` when it has none.
- **notes:** names follow the interface language: match translations too (`/^(model|модель)$/i`) if your users don't all use english.

Example:

```ts
const share = tg.ui.widgets.find({ role: 'menuitem', name: /^share$/i }, 1)[0]
```

### widget.value

```ts
readonly value: string
```

the widget's accessible value: the text in an input, a slider's position, a checkbox's state and the like.

- **grant:** `ui.read`.
- **returns:** `string`, `''` when it has none.

Example:

```ts
const search = tg.ui.widgets.find({ role: 'input' }, 1)[0]
console.log('the first input says', search?.value)
```

### widget.description

```ts
readonly description: string
```

the widget's accessible description, extra text some widgets carry (a tooltip-like hint, a status).

- **grant:** `ui.read`.
- **returns:** `string`, `''` when it has none.

Example:

```ts
for (const button of tg.ui.widgets.find({ role: 'button' }, 30)) console.log(button.name, '-', button.description)
```

### widget.visible

```ts
readonly visible: boolean
```

whether the widget is shown right now: it and all its parents are visible.

- **grant:** `ui.read`.
- **returns:** `boolean`, `false` for a destroyed widget.

Example:

```ts
const hidden = tg.ui.widgets.find({ type: /Badge/, hidden: true }).filter((widget) => !widget.visible)
```

### widget.rect

```ts
readonly rect: { x: number, y: number, width: number, height: number }
```

the widget's position and size in logical pixels, relative to the top-left corner of its window.

- **grant:** `ui.read`.
- **returns:** `{ x, y, width, height }`, all zero for a destroyed widget.
- **notes:** handy to pair widgets that are laid out side by side, like a table's label and its value (same `y`).

Example:

```ts
const [label] = table.find({ name: /^owner$/i }, 1)
const value = table.find({ role: 'text' }).find((widget) => widget.rect.y === label?.rect.y && widget.id !== label?.id)
```

### widget.parent()

```ts
parent(): Widget | null
```

the widget's parent widget.

- **grant:** `ui.read`.
- **returns:** `Widget | null`, `null` for a top-level widget or a destroyed one.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
let current: Widget | null = label
while (current) {
  console.log(current.type)
  current = current.parent()
}
```

### widget.children()

```ts
children(): Widget[]
```

the widget's direct child widgets, hidden ones included, in qt's child order (usually creation order).

- **grant:** `ui.read`.
- **returns:** `Widget[]`, empty for a destroyed widget or one without children.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
console.log(table.children().map((child) => `${child.role} ${child.name}`))
```

### widget.find(selector, limit?)

```ts
find(selector: WidgetSelector, limit?: number): Widget[]
```

like `tg.ui.widgets.find`, but searches only inside this widget (its descendants, not the widget itself).

- **grant:** `ui.read`.
- **parameters:**
  - `selector` (`WidgetSelector`): what to look for.
  - `limit` (`number`, optional): the most results, 1000 by default.
- **returns:** `Widget[]` in tree order.
- **throws:** the selector `TypeError`s of `tg.ui.widgets.find`; `TeleError` `not-granted`.

Example:

```ts
const items = menu.find({ role: 'menuitem' })
if (items.some((item) => /copy link/i.test(item.name))) menu.addMenuItem({ text: 'open in browser', onClick: openInBrowser })
```

### widget.closest(selector)

```ts
closest(selector: WidgetSelector): Widget | null
```

walks up from the widget's parent and returns the first ancestor that matches `selector`: `type`, `name` and `role`, and with `within` the ancestor must itself be inside a widget matching `within`. `hidden` doesn't matter here.

- **grant:** `ui.read`.
- **parameters:**
  - `selector` (`WidgetSelector`): what the ancestor must match.
- **returns:** `Widget | null`, `null` when no ancestor matches. the widget itself is never returned.
- **throws:** the selector `TypeError`s; `TeleError` `not-granted`.

Example:

```ts
const box = label.closest({ type: /Box$/ })
```

### widget.setVisible(visible)

```ts
setVisible(visible: boolean): void
```

shows or hides the widget.

- **grant:** `ui.write`.
- **parameters:**
  - `visible` (`boolean`): `true` to show; anything but `true` hides.
- **returns:** nothing.
- **throws:** `TeleError` `not-granted` without the grant.
- **notes:**
  - the visibility the widget had before this script's first change is restored when the script stops. there's no disposer; call `setVisible` again to undo earlier.
  - tele may show or hide the widget itself later (when its state changes), overriding yours; re-apply from `observe` if it matters.
  - a hidden widget keeps its place in tele's internal layout; whether the space closes depends on the layout around it.

Example:

```ts
tg.ui.widgets.observe({ role: 'button', name: /^premium$/i }, (button) => button.setVisible(false))
```

### widget.setText(text)

```ts
setText(text: string): boolean
```

replaces the text of a label (`Ui::FlatLabel`, tele's text widget).

- **grant:** `ui.write`.
- **parameters:**
  - `text` (`string`): the new text, plain (no formatting, no links).
- **returns:** `boolean`: `true` when the widget is a label and was changed, `false` for any other widget.
- **throws:** `TeleError` `not-granted` without the grant.
- **notes:**
  - when the script stops the label gets back exactly what it showed before the first change, formatting, links and custom emoji included.
  - a label bound to live data (a counter, an online status) may overwrite your text the next time the data changes.

Example:

```ts
const [model] = table.find({ type: 'Ui::FlatLabel', name: /^model$/i }, 1)
model?.setText(`${model.name} (rare)`)
```

### widget.insert(where, page)

```ts
insert(where: 'before' | 'after', page: Page): Disposer
```

puts a script page (built with `tg.ui.settingsPage`) into the screen, right before or after the widget. the page renders with tele's settings rows and is live: events, `invalidate()` and `dispose()` work as everywhere else.

- **grant:** `ui.write`.
- **parameters:**
  - `where` (`'before' | 'after'`): which side of the widget.
  - `page` (`Page`): a page from `tg.ui.settingsPage`.
- **returns:** `Disposer` that removes the inserted block.
- **throws:**
  - `TypeError: widget.insert('before' | 'after', page)` for another `where`.
  - `TypeError: expected a page from tg.ui.settingsPage` for something that isn't a page.
  - `TeleError` `not-found` (`this page was disposed, or this account has no window`) for a disposed page or an account without a window.
  - `TeleError` `not-found` (`this widget isn't inside a vertical layout tele can insert into`) when no ancestor is a vertical layout (a top-level window, a free-floating widget).
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - tele walks up from the widget to the nearest vertical layout around it and inserts the block next to the widget's row in that layout (the widget itself, or the ancestor that is that row).
  - `page.dispose()` removes the block too; so does stopping the script. when tele destroys the screen, the block goes with it.

Example:

```ts
const page = tg.ui.settingsPage({
  items: () => [tg.ui.header('from my script'), tg.ui.button({ text: 'do the thing', onClick: doTheThing })],
})
const remove = table.insert('after', page)
```

### widget.insertRow(row)

```ts
insertRow(row: { label: string, value: string, index?: number, onClick?(): unknown }): Disposer
```

adds a label / value row to a table (`Ui::TableLayout`, the tables in gift, giveaway and transaction boxes), styled like tele's own rows.

- **grant:** `ui.write`.
- **parameters:**
  - `row.label` (`string`): the left column.
  - `row.value` (`string`): the right column, plain text.
  - `row.index` (`number`, optional): where to insert, 0 for the top. missing or negative means after the last two-column row, so full-width rows at the bottom (like the gift box's "gifted by ... with the comment ..." line) stay last; past the end means the very end.
  - `row.onClick` (`() => unknown`, optional): makes the value a link; runs when it's clicked, with the 200 ms budget, may be async.
- **returns:** `Disposer` that removes the row.
- **throws:**
  - `TypeError: widget.insertRow({ label, value, index?, onClick? })` when `row` isn't an object.
  - `TeleError` `not-found` (`this widget isn't a table`) for any widget that isn't a `Ui::TableLayout`.
  - `TeleError` `not-granted` without the grant.
- **notes:** the row can't be edited after insertion: dispose it and insert a new one (keep the index).

Example:

```ts
let row = table.insertRow({ label: 'price', value: 'loading...' })
const price = await fetchPrice()
row()
row = table.insertRow({ label: 'price', value: `${price} TON`, onClick: () => tg.toast('from the market api') })
```

### widget.addMenuItem(item)

```ts
addMenuItem(item: { text: string, onClick(): unknown }): Disposer
```

adds an item at the bottom of a popup menu (a context menu or a ⋮ menu). the widget may be the menu (`Ui::PopupMenu`) or anything inside it.

- **grant:** `ui.write`.
- **parameters:**
  - `item.text` (`string`): the item's label.
  - `item.onClick` (`() => unknown`): runs when the item is chosen, on the next event-loop turn, with the 200 ms budget.
- **returns:** `Disposer` that removes the item from the menu (if it's still open).
- **throws:**
  - `TypeError: widget.addMenuItem({ text, onClick })` when `onClick` isn't a function.
  - `TeleError` `not-found` (`this widget isn't inside a popup menu`) when neither the widget nor an ancestor is a `Ui::PopupMenu`.
  - `TeleError` `not-granted` without the grant.
- **notes:** menus are built anew every time they open, so add items from `tg.ui.widgets.observe({ type: /PopupMenu/ }, ...)`. for message, chat and profile menus prefer `registerMessageAction` and friends: their items work with the menu editor.

Example:

```ts
tg.ui.widgets.observe({ type: /PopupMenu/ }, (menu) => {
  if (menu.find({ role: 'menuitem', name: /^copy link$/i }, 1).length) {
    menu.addMenuItem({ text: 'copy as markdown', onClick: copyAsMarkdown })
  }
})
```

### widget.click()

```ts
click(): boolean
```

presses a button as if the user clicked it with the left mouse button: any widget built on tele's button class (`Ui::AbstractButton`: buttons, settings rows, menu-like rows, icons, links drawn as buttons).

- **grant:** `unsafe.automate` (dangerous: it can press anything a user could, "send", "delete", "pay" included).
- **returns:** `boolean`: `true` when the click was queued, `false` when the widget isn't a button or is disabled.
- **throws:** `TeleError` `not-granted` without the grant.
- **notes:** the click happens on the next event-loop turn, without modifier keys. what it does is whatever the button does; nothing asks the user again.

Example:

```ts
export default defineScript({
  name: 'auto expand',
  grants: ['ui.read', 'unsafe.automate'],
  setup(tg) {
    tg.ui.widgets.observe({ role: 'button', name: /^show more$/i }, (button) => {
      button.click()
    })
  },
})
```

## app and system

control over tele itself and the computer it runs on: the theme and palette, the window title and badge, the music player, calls, the other logged-in accounts, and running programs. reading state is mostly free; changing it needs `app`, `calls`, `accounts` (all caution) or `unsafe.exec` (dangerous). everything a script changes here is undone when it stops: palette overrides, title, badge; running programs are killed.

### tg.app

```ts
readonly app: App
```

tele's appearance and media controls, see `type App`.

- **grant:** none to read (`theme.get`, `theme.color`, `theme.onChange`, `player.current`, `player.onChange`); `app` (caution, "control tele: the theme and colors, the window title and badge, the music player") for everything that changes something.

Example:

```ts
console.log(tg.app.theme.get().dark ? 'night mode' : 'day mode')
```

### type App

```ts
export interface App {
  readonly theme: {
    get(): { dark: boolean }
    setDark(dark: boolean): void
    color(name: string): string | undefined
    setColors(colors: Record<string, string>): Disposer
    onChange(callback: (theme: { dark: boolean }) => unknown): Disposer
  }
  readonly window: {
    setTitle(title: string | null): void
    setBadge(count: number | null): void
    flash(): void
  }
  readonly player: {
    current(): NowPlaying | null
    play(): boolean
    pause(): boolean
    toggle(): boolean
    stop(): boolean
    next(): boolean
    previous(): boolean
    onChange(callback: (playing: NowPlaying | null) => unknown): Disposer
  }
}
```

the type of `tg.app`; every member has its own item below.

- **fields:**
  - `theme`: night mode and the color palette: `get`, `setDark`, `color`, `setColors`, `onChange`.
  - `window`: the main window's title, unread badge and attention flash: `setTitle`, `setBadge`, `flash`.
  - `player`: tele's music and voice player: `current`, `play`, `pause`, `toggle`, `stop`, `next`, `previous`, `onChange`.

Example:

```ts
const { theme, window, player } = tg.app
```

### tg.app.theme

```ts
readonly theme: {
  get(): { dark: boolean }
  setDark(dark: boolean): void
  color(name: string): string | undefined
  setColors(colors: Record<string, string>): Disposer
  onChange(callback: (theme: { dark: boolean }) => unknown): Disposer
}
```

night mode and the color palette.

- **grant:** none for `get`, `color`, `onChange`; `app` for `setDark` and `setColors`.

Example:

```ts
const { theme } = tg.app
theme.onChange(({ dark }) => console.log(dark ? 'night' : 'day'))
```

### tg.app.theme.get()

```ts
get(): { dark: boolean }
```

reads whether tele is in night mode.

- **grant:** none.
- **returns:** `{ dark: boolean }`, `dark` is `true` in night mode.

Example:

```ts
const { dark } = tg.app.theme.get()
```

### tg.app.theme.setDark(dark)

```ts
setDark(dark: boolean): void
```

switches night mode on or off, like the moon button in the drawer.

- **grant:** `app`.
- **parameters:**
  - `dark` (`boolean`): `true` for night mode. any value is read as a boolean.
- **returns:** nothing. the switch happens on the next event-loop turn, and only when the mode actually changes.
- **throws:** `TeleError` `not-granted` without the grant.
- **notes:** this is the user's own setting: it stays after the script stops.

Example:

```ts
tg.schedule({ daily: '21:00' }, () => tg.app.theme.setDark(true))
tg.schedule({ daily: '07:30' }, () => tg.app.theme.setDark(false))
```

### tg.app.theme.color(name)

```ts
color(name: string): string | undefined
```

reads a color of the current palette.

- **grant:** none.
- **parameters:**
  - `name` (`string`): a palette name, see "palette names".
- **returns:** `string | undefined`: the color as lowercase `'#rrggbbaa'` (with any script overrides applied), `undefined` for an unknown name.

Example:

```ts
const background = tg.app.theme.color('windowBg')
const isLight = background !== undefined && parseInt(background.slice(1, 3), 16) > 128
```

### tg.app.theme.setColors(colors)

```ts
setColors(colors: Record<string, string>): Disposer
```

overrides palette colors live, without making a theme. the change is everywhere at once: tele repaints with the new colors.

- **grant:** `app`.
- **parameters:**
  - `colors` (`Record<string, string>`): palette names to colors, each `'#rgb'`, `'#rgba'`, `'#rrggbb'` or `'#rrggbbaa'` (css order, alpha last).
- **returns:** `Disposer` that restores the theme's own values of the colors this call set.
- **throws:**
  - `TypeError: tg.app.theme.setColors({ name: '#rrggbb' | '#rrggbbaa' })` when `colors` isn't a plain object.
  - `TypeError: tg.app.theme.setColors: <name> isn't '#rrggbb' or '#rrggbbaa'` for a bad value.
  - `TypeError: tg.app.theme.setColors: <name> isn't a palette color` for an unknown name. nothing is changed then.
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - overrides survive theme and night-mode switches: when the theme changes, they're applied on top of the new one. so a script that wants different colors for day and night should listen to `onChange` and set them again.
  - several calls (and several scripts) may override the same color: the latest one wins; disposing it brings back the previous override, or the theme's value.
  - everything is restored when the script stops.
  - triggers `tg.app.theme.onChange` (palette changes count).

Example:

```ts
const undo = tg.app.theme.setColors({
  activeButtonBg: '#e0569b',
  windowBgActive: '#e0569b',
  dialogsBgActive: '#e0569b',
})
tg.onUnload(undo)
```

### tg.app.theme.onChange(callback)

```ts
onChange(callback: (theme: { dark: boolean }) => unknown): Disposer
```

calls `callback` after a night-mode switch or any palette change: a new theme, a theme edit, a script's `setColors` or its undo.

- **grant:** none.
- **parameters:**
  - `callback` (`(theme: { dark: boolean }) => unknown`): gets the new night-mode state. runs on the next event-loop turn with the 200 ms budget.
- **returns:** `Disposer` that stops the calls.
- **throws:** `TypeError: tg.app.theme.onChange(function)`.
- **notes:** your own `setColors` calls fire it too; don't call `setColors` unconditionally from it or you loop.

Example:

```ts
let undo: Disposer | null = null
const apply = (dark: boolean) => {
  const wanted = dark ? '#7aa2f7' : '#3d59a1'
  if (tg.app.theme.color('activeButtonBg') === `${wanted}ff`) return
  undo?.()
  undo = tg.app.theme.setColors({ activeButtonBg: wanted })
}
apply(tg.app.theme.get().dark)
tg.app.theme.onChange(({ dark }) => apply(dark))
```

### palette names

the names `tg.app.theme.color` and `setColors` take are the keys of tele's color palette, the same ones `.tdesktop-theme` files use (about 500 of them). a few useful ones:

| name | what it paints |
|---|---|
| `windowBg` | the main background of panels, boxes and settings |
| `windowFg` | the main text color |
| `windowSubTextFg` | secondary grey text |
| `windowBgOver` | rows under the mouse |
| `windowBgActive` | accent background (selected items, switches) |
| `windowActiveTextFg` | accent text (links in settings, headers) |
| `activeButtonBg` | filled accent buttons |
| `activeButtonFg` | text on filled accent buttons |
| `attentionButtonFg` | red "danger" text buttons |
| `dialogsBg` | the chat list background |
| `dialogsBgOver` | a chat row under the mouse |
| `dialogsBgActive` | the selected chat row |
| `dialogsNameFg` | chat names in the list |
| `msgInBg` | incoming message bubbles |
| `msgOutBg` | outgoing message bubbles |
| `historyTextInFg` | text in incoming bubbles |
| `historyTextOutFg` | text in outgoing bubbles |
| `historyComposeAreaBg` | the compose bar |
| `menuBg` | context menus |
| `boxBg` | boxes (dialogs) |
| `titleBg` | the window title bar |
| `sideBarBg` | the folders side bar |

- **notes:**
  - the full list: a `.tdesktop-theme` file is a zip archive; every key in its `colors.tdesktop-theme` is a valid name. the same list is `colors.palette` in tdesktop's `lib_ui` sources.
  - names are case-sensitive.

Example:

```ts
for (const name of ['windowBg', 'msgOutBg', 'activeButtonBg']) console.log(name, tg.app.theme.color(name))
```

### tg.app.window

```ts
readonly window: {
  setTitle(title: string | null): void
  setBadge(count: number | null): void
  flash(): void
}
```

the main window's title, its unread badge (taskbar or dock, tray, title) and the attention flash.

- **grant:** `app` for every member.
- **notes:** these are app-wide, not per account: the last script that set a title or badge wins, and both go back to tele when that script removes them or stops.

Example:

```ts
tg.app.window.setTitle('tele - focus mode')
```

### tg.app.window.setTitle(title)

```ts
setTitle(title: string | null): void
```

replaces the main window's title (taking over tele's title template), or gives it back with `null`.

- **grant:** `app`.
- **parameters:**
  - `title` (`string | null`): the new title; `null` or `undefined` removes this script's title.
- **returns:** nothing.
- **throws:** `TeleError` `not-granted` without the grant.
- **notes:**
  - the title belongs to the whole app: when several scripts set one, the last one set wins; removing it shows the previous script's title, or tele's own.
  - the title isn't shown while tele is locked with a passcode or in streamer mode, so it can't leak anything.
  - removed when the script stops.

Example:

```ts
tg.app.player.onChange((track) => {
  tg.app.window.setTitle(track?.playing ? `♪ ${track.performer} - ${track.title}` : null)
})
```

### tg.app.window.setBadge(count)

```ts
setBadge(count: number | null): void
```

replaces the unread counter tele shows on the taskbar or dock icon, the tray icon and in the window title.

- **grant:** `app`.
- **parameters:**
  - `count` (`number | null`): the number to show (negative becomes 0); `null` or `undefined` gives the badge back to tele.
- **returns:** nothing.
- **throws:** `TeleError` `not-granted` without the grant.
- **notes:** app-wide, last script wins, removed when the script stops (like `setTitle`).

Example:

```ts
// count only unread chats from the "work" folder
const work = tg.local.folders().find((folder) => folder.title === 'work')
const update = () => {
  const unread = tg.local.dialogs({ folder: work?.id ?? 'main' }).filter((dialog) => dialog.unread > 0 && !dialog.muted).length
  tg.app.window.setBadge(unread)
}
tg.schedule({ every: 5000 }, update)
```

### tg.app.window.flash()

```ts
flash(): void
```

asks the system to draw the user's attention to tele's window: the taskbar button flashes (windows), the dock icon bounces (macOS), the window is marked urgent (linux). nothing happens when the window is already active.

- **grant:** `app`.
- **returns:** nothing.
- **throws:** `TeleError` `not-granted` without the grant.
- **notes:** it flashes tele's active main window, whichever account it shows.

Example:

```ts
tg.onNewMessage((message) => {
  if (message.text.toLowerCase().includes('urgent') && !tg.ui.current().windowActive) tg.app.window.flash()
})
```

### tg.app.player

```ts
readonly player: {
  current(): NowPlaying | null
  play(): boolean
  pause(): boolean
  toggle(): boolean
  stop(): boolean
  next(): boolean
  previous(): boolean
  onChange(callback: (playing: NowPlaying | null) => unknown): Disposer
}
```

tele's media player: music files, voice messages and round video messages played from chats.

- **grant:** none for `current` and `onChange`; `app` for the controls.
- **notes:** the player is app-wide: a script sees and controls whatever plays, from any account.

Example:

```ts
const track = tg.app.player.current()
if (track?.playing) tg.app.player.pause()
```

### tg.app.player.current()

```ts
current(): NowPlaying | null
```

reads what tele's player is playing (music, a voice message, a round video message).

- **grant:** none.
- **returns:** `NowPlaying | null`: the current track, `null` when nothing is loaded in the player. see `type NowPlaying`.

Example:

```ts
const track = tg.app.player.current()
if (track) tg.toast(`${track.playing ? 'playing' : 'paused'}: ${track.performer} - ${track.title}`)
```

### tg.app.player.play()

```ts
play(): boolean
```

resumes the current track.

- **grant:** `app`.
- **returns:** `boolean`: always `true` (it's a request to the player; nothing happens without a track).
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.registerShortcut('Ctrl+Alt+P', () => tg.app.player.play())
```

### tg.app.player.pause()

```ts
pause(): boolean
```

pauses the current track.

- **grant:** `app`.
- **returns:** `boolean`: always `true`.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.calls.onChange((call) => { if (call) tg.app.player.pause() })
```

### tg.app.player.toggle()

```ts
toggle(): boolean
```

play when paused, pause when playing, like the player's play button.

- **grant:** `app`.
- **returns:** `boolean`: always `true`.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.registerShortcut('Ctrl+Alt+Space', () => tg.app.player.toggle())
```

### tg.app.player.stop()

```ts
stop(): boolean
```

stops playback.

- **grant:** `app`.
- **returns:** `boolean`: always `true`.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.schedule({ daily: '23:30' }, () => tg.app.player.stop())
```

### tg.app.player.next()

```ts
next(): boolean
```

skips to the next track of the current playlist (the chat's music or voice messages).

- **grant:** `app`.
- **returns:** `boolean`: `true` when there was a next track, `false` otherwise.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
if (!tg.app.player.next()) tg.toast('that was the last one')
```

### tg.app.player.previous()

```ts
previous(): boolean
```

goes to the previous track of the current playlist.

- **grant:** `app`.
- **returns:** `boolean`: `true` when there was a previous track, `false` otherwise.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.registerShortcut('Ctrl+Alt+Left', () => tg.app.player.previous())
```

### tg.app.player.onChange(callback)

```ts
onChange(callback: (playing: NowPlaying | null) => unknown): Disposer
```

calls `callback` when the track changes or playback starts, pauses or stops. position changes alone don't fire it.

- **grant:** none.
- **parameters:**
  - `callback` (`(playing: NowPlaying | null) => unknown`): gets the new state, `null` when the player closed. runs on the next event-loop turn with the 200 ms budget.
- **returns:** `Disposer` that stops the calls.
- **throws:** `TypeError: tg.app.player.onChange(function)`.

Example:

```ts
tg.app.player.onChange((track) => {
  console.log(track ? `${track.playing ? '▶' : '⏸'} ${track.performer} - ${track.title}` : '⏹ nothing')
})
```

### type NowPlaying

```ts
export interface NowPlaying {
  type: 'song' | 'voice' | 'video'
  title: string
  performer: string
  duration: number
  position: number
  playing: boolean
  chatId?: bigint
  messageId?: number
  documentId: bigint
}
```

a snapshot of tele's player, from `tg.app.player.current()` and `onChange`.

- **fields:**
  - `type` (`'song' | 'voice' | 'video'`): a music file, a voice message, or a round video message.
  - `title` (`string`): the song's title from its tags, or the file name when there's none.
  - `performer` (`string`): the song's artist, `''` for voice and video or untagged files.
  - `duration` (`number`): the length in milliseconds.
  - `position` (`number`): the playback position in milliseconds, at the moment of the snapshot.
  - `playing` (`boolean`): `true` while playing, `false` when paused or stopped.
  - `chatId` (`bigint`, optional): the chat of the message the track comes from (marked id).
  - `messageId` (`number`, optional): that message's id.
  - `documentId` (`bigint`): the file's document id, stable across messages forwarding the same file.

Example:

```ts
const track = tg.app.player.current()
if (track?.chatId && track.messageId) await tg.ui.openChat(track.chatId, { message: track.messageId })
```

### tg.calls

```ts
readonly calls: Calls
```

this account's voice and video calls (one-to-one calls, not group calls or video chats). see `type Calls`.

- **grant:** `calls` (caution, "see your calls, answer, decline or start them, mute you") for every member.
- **notes:** a script only sees and controls calls of its own account; a call on another account looks like no call.

Example:

```ts
const call = tg.calls.current()
if (call) console.log(`in a call with ${call.user.name}: ${call.state}`)
```

### type Calls

```ts
export interface Calls {
  current(): CallInfo | null
  answer(): boolean
  hangup(): boolean
  setMuted(muted: boolean): boolean
  start(user: InputPeerLike, options?: { video?: boolean }): Promise<void>
  onChange(callback: (call: CallInfo | null) => unknown): Disposer
}
```

the type of `tg.calls`.

- **fields:**
  - `current` (`() => CallInfo | null`): the ongoing call.
  - `answer` (`() => boolean`): answer the incoming call.
  - `hangup` (`() => boolean`): end or decline.
  - `setMuted` (`(muted: boolean) => boolean`): mute or unmute the microphone.
  - `start` (`(user, options?) => Promise<void>`): call someone.
  - `onChange` (`(callback) => Disposer`): follow state changes.

Example:

```ts
const calls: Calls = tg.calls
```

### tg.calls.current()

```ts
current(): CallInfo | null
```

reads the ongoing call of this account.

- **grant:** `calls`.
- **returns:** `CallInfo | null`: the call, `null` when there's none (or it belongs to another account).
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
const call = tg.calls.current()
if (call?.state === 'established') tg.toast(`talking to ${call.user.name}`)
```

### tg.calls.answer()

```ts
answer(): boolean
```

answers the incoming call, like the green button.

- **grant:** `calls`.
- **returns:** `boolean`: `false` when this account has no call, `true` otherwise.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.calls.onChange((call) => {
  if (call?.incoming && call.state === 'waitingIncoming' && trusted.has(call.user.id)) tg.calls.answer()
})
```

### tg.calls.hangup()

```ts
hangup(): boolean
```

ends the call, or declines it while it's ringing.

- **grant:** `calls`.
- **returns:** `boolean`: `false` when this account has no call, `true` otherwise.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.calls.onChange((call) => {
  if (call?.incoming && call.state === 'waitingIncoming' && blocked.has(call.user.id)) tg.calls.hangup()
})
```

### tg.calls.setMuted(muted)

```ts
setMuted(muted: boolean): boolean
```

mutes or unmutes your microphone in the call.

- **grant:** `calls`.
- **parameters:**
  - `muted` (`boolean`): `true` to mute.
- **returns:** `boolean`: `false` when this account has no call, `true` otherwise.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.registerShortcut('Ctrl+Alt+M', () => {
  const call = tg.calls.current()
  if (call) tg.calls.setMuted(!call.muted)
})
```

### tg.calls.start(user, options?)

```ts
start(user: InputPeerLike, options?: { video?: boolean }): Promise<void>
```

starts a call to a user, the same as the call button in their profile (tele's usual checks and permission prompts apply).

- **grant:** `calls` (and `account.read(peers)` when `user` is a bare id or a username).
- **parameters:**
  - `user` (`InputPeerLike`): who to call; must be a user tele has loaded.
  - `options.video` (`boolean`, optional): start with the camera on.
- **returns:** `Promise<void>` that resolves once the call is requested; follow it with `onChange`.
- **throws:**
  - rejects with `TeleError` `not-granted` without the grant.
  - rejects with `TypeError: tg.calls.start needs a user` for a group, a channel or a peer tele hasn't loaded.
  - rejects with `TeleError` `not-found` for an unknown id or username.

Example:

```ts
tg.registerProfileAction({
  id: 'video_call',
  text: 'video call',
  visible: (ctx) => ctx.chat.kind === 'user',
  onClick: (ctx) => tg.calls.start(ctx.chat, { video: true }),
})
```

### tg.calls.onChange(callback)

```ts
onChange(callback: (call: CallInfo | null) => unknown): Disposer
```

calls `callback` when a call of this account starts or ends, changes state, or is muted or unmuted.

- **grant:** `calls`.
- **parameters:**
  - `callback` (`(call: CallInfo | null) => unknown`): gets the call's new state, `null` once there's no call. runs on the next event-loop turn with the 200 ms budget.
- **returns:** `Disposer` that stops the calls.
- **throws:**
  - `TypeError: tg.calls.onChange(function)`.
  - `TeleError` `not-granted` without the grant.
- **notes:** repeated identical states are merged; you get each change once.

Example:

```ts
let started = 0
tg.calls.onChange((call) => {
  if (call?.state === 'established' && !started) started = Date.now()
  if (!call && started) {
    tg.ui.notice(`the call lasted ${Math.round((Date.now() - started) / 60000)} min`)
    started = 0
  }
})
```

### type CallInfo

```ts
export interface CallInfo {
  user: PeerInfo
  incoming: boolean
  state: string
  muted: boolean
}
```

a snapshot of a one-to-one call.

- **fields:**
  - `user` (`PeerInfo`): the other person.
  - `incoming` (`boolean`): `true` when they called you.
  - `state` (`string`): tdesktop's call state in camelCase, one of:
    - `'starting'`, `'requesting'`, `'waiting'`: an outgoing call is being set up.
    - `'waitingIncoming'`: an incoming call that rings, not answered yet.
    - `'ringing'`: your outgoing call rings on their side.
    - `'exchangingKeys'`, `'waitingInit'`, `'waitingInitAck'`: connecting after the answer.
    - `'established'`: talking.
    - `'waitingUserConfirmation'`: tele waits for you to confirm something before going on.
    - `'busy'`: they are in another call.
    - `'hangingUp'`, `'failedHangingUp'`, `'migrationHangingUp'`: ending.
    - `'ended'`, `'endedByOtherDevice'`, `'failed'`: over (answered or declined on another device for the second).
    - `'unknown'`: a state tele doesn't know a name for.
  - `muted` (`boolean`): whether your microphone is muted.

Example:

```ts
tg.calls.onChange((call) => {
  if (call?.state === 'busy') tg.toast(`${call.user.name} is busy`)
})
```

### tg.accounts

```ts
readonly accounts: { list(): AccountInfo[], switchTo(id: bigint): boolean }
```

the accounts logged in to this tele. scripts can see them and switch the active one; they can't act as another account (each account turns on and approves its own scripts).

- **grant:** `accounts` (caution, "see your other accounts in tele and switch between them").

Example:

```ts
for (const account of tg.accounts.list()) console.log(account.name, account.unread)
```

### tg.accounts.list()

```ts
list(): AccountInfo[]
```

lists the logged-in accounts in tele's order (the order of the account switcher).

- **grant:** `accounts`.
- **returns:** `AccountInfo[]`; the script's own account is always there, marked with `self: true`.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
const total = tg.accounts.list().reduce((sum, account) => sum + account.unread, 0)
```

### tg.accounts.switchTo(id)

```ts
switchTo(id: bigint): boolean
```

makes another account the active one, like picking it in the account switcher.

- **grant:** `accounts`.
- **parameters:**
  - `id` (`bigint`): the account's user id from `list()` (a number is accepted too).
- **returns:** `boolean`: `true` when such an account exists (the switch happens on the next event-loop turn), `false` otherwise.
- **throws:**
  - `TypeError: tg.accounts.switchTo needs an account id from list()` for a value that isn't an id.
  - `TeleError` `not-granted` without the grant.
- **notes:** the script keeps running in its own account after the switch.

Example:

```ts
const next = tg.accounts.list().find((account) => !account.active && account.unread > 0)
if (next) tg.accounts.switchTo(next.id)
```

### type AccountInfo

```ts
export interface AccountInfo {
  id: bigint
  name: string
  username: string
  active: boolean
  self: boolean
  unread: number
}
```

one logged-in account, from `tg.accounts.list()`.

- **fields:**
  - `id` (`bigint`): the account's user id.
  - `name` (`string`): its display name.
  - `username` (`string`): its username without `@`, `''` when it has none.
  - `active` (`boolean`): whether it's the account tele currently shows.
  - `self` (`boolean`): whether it's the account this script runs in.
  - `unread` (`number`): its unread badge, as tele counts it.

Example:

```ts
const others = tg.accounts.list().filter((account) => !account.self).map((account) => `@${account.username || account.name}`)
```

### tg.unsafe

```ts
readonly unsafe: Unsafe
```

things that reach outside tele with the user's full rights. see `type Unsafe`.

- **grant:** `unsafe.exec` (dangerous) for `exec`.

Example:

```ts
const { stdout } = await tg.unsafe.exec('git', ['-C', '/home/me/notes', 'status', '--short'], { timeout: 5000 })
```

### type Unsafe

```ts
export interface Unsafe {
  exec(program: string, args?: string[], options?: { cwd?: string, input?: string, timeout?: number }): Promise<ExecResult>
  exec(program: string, args: string[], options: { cwd?: string, detached: true }): Promise<number>
}
```

the type of `tg.unsafe`.

- **fields:**
  - `exec`: run a program and wait for it, or start it detached. see `tg.unsafe.exec`.

Example:

```ts
const unsafe: Unsafe = tg.unsafe
```

### tg.unsafe.exec(program, args?, options?)

```ts
exec(program: string, args?: string[], options?: { cwd?: string, input?: string, timeout?: number }): Promise<ExecResult>
exec(program: string, args: string[], options: { cwd?: string, detached: true }): Promise<number>
```

runs a program on the user's computer. by default tele waits for it to exit and resolves with its exit code and output; with `detached: true` it only starts it and resolves with its process id.

- **grant:** `unsafe.exec` (dangerous: the consent box says, in bold, "run any program on your computer, with your rights").
- **parameters:**
  - `program` (`string`): the program: a name looked up in `PATH`, or a full path. there's no shell: to use pipes, redirects or shell built-ins, run the shell yourself (`'sh', ['-c', '...']` or `'cmd', ['/c', '...']`).
  - `args` (`string[]`, optional): the arguments, each passed as is (no quoting needed, no globbing). non-strings are turned into strings.
  - `options.cwd` (`string`, optional): the working directory; tele's own by default.
  - `options.input` (`string`, optional): written to the program's stdin as UTF-8, then stdin is closed. without it stdin is closed right away.
  - `options.timeout` (`number`, optional): milliseconds until the program is killed. 0 or missing means no limit.
  - `options.detached` (`true`, optional): start the program outside tele and don't wait. `input` and `timeout` don't apply.
- **returns:**
  - waiting: `Promise<ExecResult>`: `{ code, crashed, stdout, stderr }` when the program exits, whatever the exit code. see `type ExecResult`.
  - detached: `Promise<number>`: the started process id.
- **throws:**
  - `TypeError: tg.unsafe.exec(program, args?, { cwd, input, timeout, detached })` for an empty or missing `program`.
  - `TeleError` `not-granted` without the grant.
  - rejects with `TeleError` `internal` (`tg.unsafe.exec: can't start <program>`) when it can't be started (not found, not executable).
  - rejects with `TeleError` `timed-out` (`tg.unsafe.exec: timed out`) when `timeout` passed; the program is killed.
- **notes:**
  - results always settle asynchronously, even "can't start", so a `.catch` attached right away is never reported as an unhandled rejection.
  - programs started without `detached` are killed when the script stops (turned off, reloaded, tele quits). detached ones live on.
  - output is read whole into memory and decoded as UTF-8; mind the 256 MB memory limit with chatty programs.
  - the program runs with the user's rights. never pass text from messages into `args` of a shell (`sh -c`), that's how remote code execution happens; pass it as a separate argument of a real program instead.

Example:

```ts
const isWindows = (await tg.unsafe.exec('cmd', ['/c', 'ver'], { timeout: 3000 }).catch(() => null)) !== null
const result = isWindows
  ? await tg.unsafe.exec('cmd', ['/c', 'dir'], { cwd: 'C:\\', timeout: 5000 })
  : await tg.unsafe.exec('ls', ['-la'], { cwd: '/', timeout: 5000 })
console.log(result.code, result.stdout)

const pid = await tg.unsafe.exec('code', ['/home/me/notes'], { detached: true })
```

### type ExecResult

```ts
export interface ExecResult {
  code: number
  crashed: boolean
  stdout: string
  stderr: string
}
```

what a waited `tg.unsafe.exec` resolves with.

- **fields:**
  - `code` (`number`): the exit code. a non-zero code doesn't reject; check it.
  - `crashed` (`boolean`): `true` when the program crashed or was killed by a signal instead of exiting normally (then `code` means nothing).
  - `stdout` (`string`): everything it wrote to standard output, decoded as UTF-8.
  - `stderr` (`string`): everything it wrote to standard error, decoded as UTF-8.

Example:

```ts
const result = await tg.unsafe.exec('git', ['pull'], { cwd: '/home/me/notes', timeout: 30_000 })
if (result.crashed || result.code !== 0) tg.ui.notice({ text: result.stderr || `git exited with ${result.code}`, tone: 'warning' })
```

## cookbook

complete scripts that combine the apis above. each one is a single file: save it as `<name>.ts` in the scripts folder, turn it on in settings > tele > scripts, and allow the grants it asks for. they're small on purpose; change them to taste.

### away auto-reply

answers private messages once per person while you're away. a switch on the script's settings page and a shortcut (Ctrl+Shift+A) turn away mode on and off; the reply text is editable.

- **grant:** `onUpdate(new_message)` to see new messages, `account.write(send)` to reply.
- **notes:** it only answers people (not bots, groups or channels), and each person once until you come back. messages that arrived while tele was closed aren't answered: tele doesn't replay them to scripts.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'away auto-reply',
  description: 'answers private messages once while you are away',
  icon: '💤',
  grants: ['onUpdate(new_message)', 'account.write(send)'],
  setup(tg) {
    let away = tg.storage.get<boolean>('away') ?? false
    let text = tg.storage.get<string>('text') ?? "i'm away right now, i'll answer when i'm back."
    const answered = new Set<bigint>()

    const setAway = (value: boolean) => {
      away = value
      tg.storage.set('away', value)
      answered.clear()
      page.invalidate()
      tg.toast(value ? 'away mode on' : 'welcome back')
    }

    const page = tg.ui.settingsPage({
      title: 'away auto-reply',
      items: () => [
        tg.ui.check({ text: "i'm away", checked: away, subtitle: 'Ctrl+Shift+A toggles it too.', onChange: setAway }),
        tg.ui.input({
          text: 'reply',
          value: text,
          multiline: true,
          maxLength: 500,
          onChange: (value) => {
            text = value.trim() || text
            tg.storage.set('text', text)
          },
        }),
        tg.ui.separator(`answered ${answered.size} people since you left.`),
      ],
    })
    tg.registerSettings(page)
    tg.registerShortcut('Ctrl+Shift+A', () => setAway(!away))

    tg.onNewMessage(async (message) => {
      const from = message.senderId
      if (!away || message.out || message.chat?.kind !== 'user' || from === null || answered.has(from)) return
      answered.add(from)
      page.invalidate()
      await message.reply(text)
    })
  },
})
```

### link cleaner

removes tracking parameters (`utm_*`, `fbclid`, `gclid`...) from every link before it opens, and counts how many it cleaned.

- **grant:** `interceptLink`.
- **notes:** it rewrites only the query string; the link's address and anchor stay. extra parameters to strip can be added on the settings page, comma-separated.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'link cleaner',
  description: 'strips tracking parameters from links you open',
  icon: '🧹',
  grants: ['interceptLink'],
  setup(tg) {
    const builtIn = ['fbclid', 'gclid', 'yclid', 'dclid', 'mc_eid', 'igshid', '_hsenc', '_hsmi']
    let extra = tg.storage.get<string>('extra') ?? ''
    let cleaned = tg.storage.get<number>('cleaned') ?? 0

    const isTracking = (key: string) => {
      const name = key.toLowerCase()
      const custom = extra.split(',').map((item) => item.trim().toLowerCase()).filter(Boolean)
      return name.startsWith('utm_') || builtIn.includes(name) || custom.includes(name)
    }

    const clean = (url: string) => {
      const match = /^([^?#]*)\?([^#]*)(#.*)?$/.exec(url)
      if (!match) return url
      const [, base, query, hash = ''] = match
      const keyOf = (pair: string) => {
        try {
          return decodeURIComponent(pair.split('=')[0])
        } catch {
          return pair
        }
      }
      const kept = query.split('&').filter((pair) => pair && !isTracking(keyOf(pair)))
      return base + (kept.length ? `?${kept.join('&')}` : '') + hash
    }

    const page = tg.ui.settingsPage({
      title: 'link cleaner',
      items: () => [
        tg.ui.item({ text: 'links cleaned', icon: '🧹', value: String(cleaned), onClick: () => {} }),
        tg.ui.input({
          text: 'also strip',
          value: extra,
          placeholder: 'ref, source',
          onChange: (value) => {
            extra = value
            tg.storage.set('extra', value)
          },
        }),
        tg.ui.separator('parameters starting with utm_ and the usual click ids are always stripped.'),
      ],
    })
    tg.registerSettings(page)

    tg.interceptLink(/^https?:\/\/[^?#]*\?/i, ({ url }) => {
      const result = clean(url)
      if (result === url) return 'open'
      tg.storage.set('cleaned', ++cleaned)
      page.invalidate()
      return result
    })
  },
})
```

### music status in your bio

while a song is in tele's player, your bio says what you're listening to; when the player closes, your normal bio comes back.

- **grant:** `call(account.updateProfile)` to change the bio.
- **notes:**
  - the bio changes when the song changes, not on pause or seek, and at most once every 30 s, to stay far from telegram's flood limits.
  - telegram limits the bio to 70 characters (140 with premium); the status is cut to fit.
  - set your normal bio on the settings page: the script can't read it without more grants, and that's the text it puts back.
  - close the player before turning the script off, or the last song stays in your bio.

Example:

```ts
import { defineScript } from 'tele'
import type { NowPlaying } from 'tele'

export default defineScript({
  name: 'music status',
  description: 'shows the song you listen to in your bio',
  icon: '🎵',
  grants: ['call(account.updateProfile)'],
  setup(tg) {
    let normal = tg.storage.get<string>('bio') ?? ''
    let shown: string | null = null
    let lastUpdate = 0
    let timer = 0

    const write = async (about: string) => {
      if (about === shown) return
      shown = about
      lastUpdate = Date.now()
      await tg.call({ _: 'account.updateProfile', about })
    }

    const statusOf = (track: NowPlaying | null) =>
      (track?.type === 'song')
        ? `🎧 ${track.performer ? `${track.performer} - ` : ''}${track.title}`.slice(0, 70)
        : normal

    const update = () => {
      clearTimeout(timer)
      const wait = Math.max(0, lastUpdate + 30_000 - Date.now())
      timer = setTimeout(() => {
        write(statusOf(tg.app.player.current())).catch((error) => console.warn('bio update failed', error))
      }, wait)
    }

    tg.registerSettings(tg.ui.settingsPage({
      title: 'music status',
      items: () => [
        tg.ui.input({
          text: 'my normal bio',
          value: normal,
          maxLength: 70,
          placeholder: 'empty',
          onChange: (value) => {
            normal = value
            tg.storage.set('bio', value)
            update()
          },
        }),
      ],
    }))

    let lastKey = ''
    tg.app.player.onChange((track) => {
      const key = (track?.type === 'song') ? String(track.documentId) : ''
      if (key === lastKey) return
      lastKey = key
      update()
    })
  },
})
```

### theme scheduler

switches night mode on and off at the times you choose, every day.

- **grant:** `app` to switch night mode.
- **notes:** `tg.schedule` runs on the wall clock, so it's right after the computer slept and after clock changes. at start the script also applies the mode that fits the current time.

Example:

```ts
import { defineScript } from 'tele'
import type { Disposer } from 'tele'

export default defineScript({
  name: 'theme scheduler',
  description: 'night mode by the clock',
  icon: '🌗',
  grants: ['app'],
  setup(tg) {
    const TIME = /^([01]?\d|2[0-3]):([0-5]\d)$/
    let night = tg.storage.get<string>('night') ?? '21:00'
    let day = tg.storage.get<string>('day') ?? '07:30'
    let schedules: Disposer[] = []

    const minutes = (time: string) => {
      const [, hours, mins] = TIME.exec(time) ?? ['', '0', '0']
      return Number(hours) * 60 + Number(mins)
    }

    const shouldBeDark = () => {
      const now = new Date()
      const current = now.getHours() * 60 + now.getMinutes()
      const from = minutes(night)
      const to = minutes(day)
      return from > to ? (current >= from || current < to) : (current >= from && current < to)
    }

    const arm = () => {
      for (const dispose of schedules) dispose()
      schedules = [
        tg.schedule({ daily: night }, () => tg.app.theme.setDark(true)),
        tg.schedule({ daily: day }, () => tg.app.theme.setDark(false)),
      ]
      tg.app.theme.setDark(shouldBeDark())
    }

    const timeRow = (text: string, value: string, save: (value: string) => void) => tg.ui.input({
      text,
      value,
      placeholder: 'HH:MM',
      maxLength: 5,
      onChange: (next) => {
        if (!TIME.test(next.trim())) {
          tg.toast(`"${next}" isn't a time like 21:00`)
          return
        }
        save(next.trim())
        arm()
      },
    })

    tg.registerSettings(tg.ui.settingsPage({
      title: 'theme scheduler',
      items: () => [
        timeRow('night mode from', night, (value) => { night = value; tg.storage.set('night', value) }),
        timeRow('day mode from', day, (value) => { day = value; tg.storage.set('day', value) }),
      ],
    }))
    arm()
  },
})
```

### drop guard

refuses to send programs and scripts, and files that are too big, when you drag them into a chat by mistake, and explains why in the notification centre.

- **grant:** `interceptDrop`.
- **notes:** it only looks at names and sizes, never at contents. dropping the same file with the script off (or the size limit raised) sends it as usual.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'drop guard',
  description: 'stops risky files from being dropped into chats',
  icon: '🛡️',
  grants: ['interceptDrop'],
  setup(tg) {
    const RISKY = /\.(exe|msi|bat|cmd|scr|ps1|vbs|jar|apk|dmg|pkg|sh)$/i
    let limit = tg.storage.get<number>('limitMb') ?? 500

    tg.registerSettings(tg.ui.settingsPage({
      title: 'drop guard',
      items: () => [
        tg.ui.slider({
          text: 'largest file to send by drag and drop',
          min: 50,
          max: 2000,
          step: 50,
          value: limit,
          label: (value) => (value >= 1000 ? `${(value / 1000).toFixed(1)} GB` : `${value} MB`),
          onChange: (value) => {
            limit = value
            tg.storage.set('limitMb', value)
          },
        }),
      ],
    }))

    tg.interceptDrop((drop) => {
      const risky = drop.files.filter((file) => RISKY.test(file.name))
      const huge = drop.files.filter((file) => file.size > limit * 1024 * 1024)
      if (!risky.length && !huge.length) return 'accept'
      const reasons = [
        ...risky.map((file) => `${file.name} is a program or a script`),
        ...huge.map((file) => `${file.name} is ${Math.round(file.size / 1024 / 1024)} MB`),
      ]
      tg.ui.notice({ title: 'drop guard', text: `not sent: ${reasons.join('; ')}.`, tone: 'warning' })
      tg.toast('drop guard stopped that file, see the notification centre')
      return 'drop'
    })
  },
})
```

### quick translate button

adds "translate" to the message menu. the translation appears under the message as a quote (only in your tele); choosing it again removes it. the target language is set on the settings page.

- **grant:** `fetch(translate.googleapis.com)` for the translation service.
- **notes:** `tg.decorateMessage` needs no grant and changes nothing on the server: other people never see the translation. the endpoint used is google's public one; swap in any translation api (and its `fetch(...)` grant).

Example:

```ts
import { defineScript } from 'tele'
import type { Disposer } from 'tele'

export default defineScript({
  name: 'quick translate',
  description: 'translate any message in place',
  icon: '🌐',
  grants: ['fetch(translate.googleapis.com)'],
  setup(tg) {
    const languages = ['en', 'de', 'es', 'fr', 'ru', 'uk', 'tr', 'ja']
    let target = tg.storage.get<number>('target') ?? 0
    const shown = new Map<string, Disposer>()

    tg.registerSettings(tg.ui.settingsPage({
      title: 'quick translate',
      items: () => [
        tg.ui.select({ text: 'translate to', items: languages, selected: target, onChange: (index) => { target = index; tg.storage.set('target', index) } }),
      ],
    }))

    const translate = async (text: string) => {
      const url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&dt=t'
        + `&tl=${languages[target]}&q=${encodeURIComponent(text)}`
      const response = await fetch(url, { timeout: 10_000 })
      if (!response.ok) throw new Error(`translate answered ${response.status}`)
      const data = await response.json() as [[string, string][], unknown, string]
      return { text: data[0].map((part) => part[0]).join(''), from: data[2] }
    }

    tg.registerMessageAction({
      id: 'translate',
      text: 'translate',
      visible: (ctx) => ctx.text.trim().length > 0,
      onClick: async (ctx) => {
        const key = `${ctx.chatId}:${ctx.messageId}`
        const existing = shown.get(key)
        if (existing) {
          existing()
          shown.delete(key)
          return
        }
        try {
          const result = await translate(ctx.text)
          shown.set(key, await tg.decorateMessage(ctx.chat, ctx.messageId, {
            footer: `${result.from} → ${languages[target]}: ${result.text}`,
          }))
        } catch (error) {
          tg.toast(`couldn't translate: ${String(error)}`)
        }
      },
    })
  },
})
```

### quiet hours

no desktop notifications between the hours you set, except for messages that mention you. messages still arrive and count as unread.

- **grant:** `interceptNotification` to hide notifications, `account.read(messages)` to see whether a message mentions you.
- **notes:** an overnight range (22 to 8) works; set both sliders to the same hour to turn quiet hours off.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'quiet hours',
  description: 'no notifications at night, mentions still come through',
  icon: '🤫',
  grants: ['interceptNotification', 'account.read(messages)'],
  setup(tg) {
    let from = tg.storage.get<number>('from') ?? 22
    let to = tg.storage.get<number>('to') ?? 8
    let mentions = tg.storage.get<boolean>('mentions') ?? true
    let hidden = 0

    const quietNow = () => {
      const hour = new Date().getHours()
      return from === to ? false : from < to ? (hour >= from && hour < to) : (hour >= from || hour < to)
    }

    const hourRow = (text: string, value: number, save: (value: number) => void) => tg.ui.slider({
      text,
      min: 0,
      max: 23,
      value,
      label: (hour) => `${String(hour).padStart(2, '0')}:00`,
      onChange: save,
    })

    const page = tg.ui.settingsPage({
      title: 'quiet hours',
      items: () => [
        hourRow('quiet from', from, (value) => { from = value; tg.storage.set('from', value) }),
        hourRow('until', to, (value) => { to = value; tg.storage.set('to', value) }),
        tg.ui.check({ text: 'let mentions through', checked: mentions, onChange: (value) => { mentions = value; tg.storage.set('mentions', value) } }),
        tg.ui.separator(`${hidden} notifications hidden since tele started.`),
      ],
    })
    tg.registerSettings(page)

    tg.interceptNotification(({ kind, message }) => {
      if (!quietNow()) return 'show'
      if (mentions && kind === 'message' && message?.mentioned) return 'show'
      hidden++
      page.invalidate()
      return 'drop'
    })
  },
})
```

### compose snippets

type a short code like `:shrug:` or `;addr` anywhere and it turns into the full text while you type. snippets are managed on the settings page.

- **grant:** `account.read(draft)` to watch the field, `account.write(draft)` to change it, `account.read(peers)` to address the field by its chat id.
- **notes:** the replacement only happens when the text really changes, so the script doesn't loop on its own `onInput` events.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'compose snippets',
  description: 'expand short codes while you type',
  icon: '✂️',
  grants: ['account.read(draft, peers)', 'account.write(draft)'],
  setup(tg) {
    let snippets = tg.storage.get<Record<string, string>>('snippets') ?? { ':shrug:': '¯\\_(ツ)_/¯', ':tm:': '™' }
    const save = () => {
      tg.storage.set('snippets', snippets)
      page.invalidate()
    }

    const page = tg.ui.settingsPage({
      title: 'compose snippets',
      items: () => [
        tg.ui.header('snippets'),
        ...Object.entries(snippets).map(([code, text]) => tg.ui.item({
          id: code,
          text: code,
          value: text.length > 24 ? `${text.slice(0, 24)}...` : text,
          subtitle: 'click to remove',
          onClick: () => {
            const { [code]: _removed, ...rest } = snippets
            snippets = rest
            save()
          },
        })),
        tg.ui.button({
          text: 'add a snippet',
          onClick: async () => {
            const code = await tg.ui.prompt({ title: 'code', placeholder: ':code:', maxLength: 32 })
            if (!code?.trim()) return
            const text = await tg.ui.prompt({ title: `${code.trim()} expands to`, multiline: true })
            if (text === null) return
            snippets = { ...snippets, [code.trim()]: text }
            save()
          },
        }),
      ],
    })
    tg.registerSettings(page)

    tg.compose.onInput(async ({ chatId, text }) => {
      let next = text
      for (const [code, value] of Object.entries(snippets)) next = next.replaceAll(code, value)
      if (next !== text) await tg.compose.set(next, chatId)
    })
  },
})
```

### calculator command

`/calc 2 * (3 + 4)` in any chat sends `2 * (3 + 4) = 14`. `/calc` alone puts `/calc ` back into the field so you can type the expression.

- **grant:** none: commands run when you trigger them, and their text goes out through tele's normal send path.
- **notes:** the expression is parsed by the script itself (numbers, `+ - * / % ^` and parentheses), nothing is ever evaluated as code. an invalid expression throws, which is a logged fault, and the typed text comes back into the field.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'calculator',
  description: '/calc for quick math in any chat',
  icon: '🧮',
  setup(tg) {
    const evaluate = (source: string): number => {
      const tokens = source.match(/\d+(?:\.\d+)?|[-+*/%^()]/g) ?? []
      if (tokens.join('') !== source.replace(/\s+/g, '')) throw new Error(`not arithmetic: ${source}`)
      let index = 0
      const peek = () => tokens[index]
      const take = () => tokens[index++]
      const primary = (): number => {
        const token = take()
        if (token === '(') {
          const value = sum()
          if (take() !== ')') throw new Error('a ) is missing')
          return value
        }
        if (token === '-') return -primary()
        if (token === '+') return primary()
        if (token === undefined || !/^\d/.test(token)) throw new Error(`unexpected ${token ?? 'end'}`)
        return Number(token)
      }
      const power = (): number => {
        const base = primary()
        if (peek() !== '^') return base
        take()
        return base ** power()
      }
      const product = (): number => {
        let value = power()
        while (peek() === '*' || peek() === '/' || peek() === '%') {
          const operator = take()
          const right = power()
          value = operator === '*' ? value * right : operator === '/' ? value / right : value % right
        }
        return value
      }
      const sum = (): number => {
        let value = product()
        while (peek() === '+' || peek() === '-') {
          const operator = take()
          const right = product()
          value = operator === '+' ? value + right : value - right
        }
        return value
      }
      const result = sum()
      if (index !== tokens.length) throw new Error(`unexpected ${peek()}`)
      return result
    }

    tg.registerCommand({
      name: 'calc',
      description: 'calculate and send the result',
      args: 'expression',
      run: (args, ctx) => {
        const expression = args.trim()
        if (!expression) {
          ctx.setText('/calc ')
          return
        }
        const value = evaluate(expression)
        if (!Number.isFinite(value)) throw new Error(`${expression} has no finite result`)
        return `${expression} = ${Number(value.toPrecision(12))}`
      },
    })
  },
})
```

### call assistant

pauses music when a call starts and resumes it afterwards, mutes you automatically when a call connects (optional), and logs every call's length in the notification centre.

- **grant:** `calls` to follow and mute calls, `app` to pause and resume the player.
- **notes:** only calls of the account the script runs in are seen; turn the script on in each account you call from.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'call assistant',
  description: 'music pause, auto-mute and a call log',
  icon: '📞',
  grants: ['calls', 'app'],
  setup(tg) {
    let autoMute = tg.storage.get<boolean>('autoMute') ?? false
    let resume = false
    let connected = 0
    let muted = false
    let partner = ''

    tg.registerSettings(tg.ui.settingsPage({
      title: 'call assistant',
      items: () => [
        tg.ui.check({ text: 'mute me when a call connects', checked: autoMute, onChange: (value) => { autoMute = value; tg.storage.set('autoMute', value) } }),
      ],
    }))

    tg.calls.onChange((call) => {
      if (call && !partner) {
        partner = call.user.name
        const track = tg.app.player.current()
        resume = track?.playing === true
        if (resume) tg.app.player.pause()
      }
      if (call?.state === 'established' && !connected) {
        connected = Date.now()
        if (autoMute && !muted) {
          muted = true
          tg.calls.setMuted(true)
          tg.toast('you are muted, Ctrl+Alt+M to talk')
        }
      }
      if (!call && partner) {
        const minutes = connected ? Math.max(1, Math.round((Date.now() - connected) / 60_000)) : 0
        tg.ui.notice(minutes ? `call with ${partner}: ${minutes} min` : `missed or declined call with ${partner}`)
        if (resume) tg.app.player.play()
        resume = false
        connected = 0
        muted = false
        partner = ''
      }
    })

    tg.registerShortcut('Ctrl+Alt+M', () => {
      const call = tg.calls.current()
      if (call) tg.calls.setMuted(!call.muted)
    })
  },
})
```

### account switcher in the tray

adds every logged-in account to the tray menu with its unread count; clicking one brings that account up.

- **grant:** `accounts`.
- **notes:** the list refreshes every 10 s, so new logins and unread counts show up without restarting the script. turn it on in one account only, or every account adds its own copy.

Example:

```ts
import { defineScript } from 'tele'
import type { Disposer } from 'tele'

export default defineScript({
  name: 'tray accounts',
  description: 'switch accounts from the tray menu',
  icon: '👥',
  grants: ['accounts'],
  setup(tg) {
    let items: Disposer[] = []
    let shown = ''

    const refresh = () => {
      const accounts = tg.accounts.list()
      const key = accounts.map((account) => `${account.id}:${account.unread}:${account.active}`).join(',')
      if (key === shown) return
      shown = key
      for (const dispose of items) dispose()
      items = accounts.map((account) => tg.ui.registerMenuItem({
        place: 'tray',
        emoji: account.active ? '●' : '○',
        text: `${account.name}${account.unread ? ` (${account.unread})` : ''}`,
        onClick: () => tg.accounts.switchTo(account.id),
      }))
    }

    refresh()
    tg.schedule({ every: 10_000 }, refresh)
  },
})
```

### system info command

`/sys` sends a short description of your computer (os, uptime) by running a system program. a small, safe example of `tg.unsafe.exec`: fixed programs and arguments, nothing from the chat is ever passed to them.

- **grant:** `unsafe.exec` (dangerous: it may run any program).
- **notes:** the programs are killed after 5 s; a missing program rejects with `TeleError` `internal`, which the command turns into a fault, and the typed text comes back.

Example:

```ts
import { defineScript } from 'tele'

export default defineScript({
  name: 'system info',
  description: '/sys sends your os and uptime',
  icon: '🖥️',
  grants: ['unsafe.exec'],
  setup(tg) {
    const run = async (program: string, args: string[]) => {
      const result = await tg.unsafe.exec(program, args, { timeout: 5000 })
      if (result.crashed || result.code !== 0) throw new Error(`${program} failed: ${result.stderr.trim()}`)
      return result.stdout.trim()
    }

    tg.registerCommand({
      name: 'sys',
      description: 'send os and uptime',
      run: async () => {
        const windows = await tg.unsafe.exec('cmd', ['/c', 'ver'], { timeout: 5000 }).then((result) => result.stdout.trim(), () => null)
        if (windows) {
          const boot = await run('powershell', ['-NoProfile', '-Command', '(Get-CimInstance Win32_OperatingSystem).LastBootUpTime.ToString("u")'])
          return `💻 ${windows}\n⏱ up since ${boot}`
        }
        return `💻 ${await run('uname', ['-sr'])}\n⏱ ${await run('uptime', [])}`
      },
    })
  },
})
```

### gift box extras

decorates the box of a unique (collectible) gift: a "market price" row in its table, fetched from a price api; "(rare)" after the model's name; a block under the table with buttons to copy the model name and open its price history; and an "open price history" item in the box's ⋮ menu. all of it goes away when the script is turned off.

- **grant:** `ui.read` to find the gift table and menus, `ui.write` to add the row, the block and the menu item, `fetch(api.example.com)` for the price api, `openUrl` and `clipboard.write` for the buttons.
- **notes:**
  - this uses the widget layer, so it depends on how tele builds the gift box today: the table is a `Ui::TableLayout` whose labels read "model" and "owner" (the names follow the interface language; the pattern also has the russian ones). a future tele may change that; the script then just does nothing.
  - `api.example.com` stands for whatever gift price service you use: change the url, the response parsing and the `fetch(...)` grant together.
  - the value next to a label is found by position (the label and its value share a row, so the same `rect.y`).
  - the ⋮ menu item is only added while a decorated gift box is open, so other menus with a "copy link" item stay as they are.

Example:

```ts
import { defineScript } from 'tele'
import type { Widget } from 'tele'

export default defineScript({
  name: 'gift box extras',
  description: 'market price and shortcuts in unique gift boxes',
  icon: '🎁',
  grants: ['ui.read', 'ui.write', 'fetch(api.example.com)', 'openUrl', 'clipboard.write'],
  setup(tg) {
    const GIFT_LABELS = /^(model|модель|owner|владелец)$/i
    const MODEL_LABEL = /^(model|модель)$/i
    const decorated = new Set<number>()
    let current: { table: Widget, model: string } | null = null

    const valueOf = (table: Widget, label: Widget) => table
      .find({ type: 'Ui::FlatLabel' })
      .find((widget) => widget.id !== label.id && widget.rect.y === label.rect.y && widget.rect.x > label.rect.x)

    const fetchPrice = async (model: string) => {
      const response = await fetch(`https://api.example.com/gifts/price?model=${encodeURIComponent(model)}`, { timeout: 8000 })
      if (!response.ok) throw new Error(`price api answered ${response.status}`)
      const data = await response.json() as { floor?: number, currency?: string }
      return (data.floor === undefined) ? 'unknown' : `${data.floor} ${data.currency ?? 'TON'}`
    }

    const historyUrl = (model: string) => `https://api.example.com/gifts/history?model=${encodeURIComponent(model)}`

    const decorate = async (table: Widget) => {
      if (decorated.has(table.id) || !table.find({ name: GIFT_LABELS }, 1).length) return
      decorated.add(table.id)

      const modelLabel = table.find({ name: MODEL_LABEL }, 1)[0]
      const model = (modelLabel && valueOf(table, modelLabel)?.name) || ''
      current = { table, model }
      modelLabel?.setText(`${modelLabel.name} (rare)`)

      const page = tg.ui.settingsPage({
        items: () => [
          tg.ui.header('gift box extras'),
          tg.ui.button({
            text: 'copy the model name',
            value: model,
            onClick: () => {
              tg.clipboard.write(model)
              tg.toast('copied')
            },
          }),
          tg.ui.button({ text: 'open the price history', onClick: () => tg.openUrl(historyUrl(model)) }),
        ],
      })
      table.insert('after', page)

      const loading = table.insertRow({ label: 'market price', value: 'loading...' })
      let price = 'unavailable'
      try {
        price = model ? await fetchPrice(model) : 'unknown model'
      } catch (error) {
        console.warn('price lookup failed', error)
      }
      if (!table.alive) return
      loading()
      table.insertRow({ label: 'market price', value: price, onClick: () => tg.openUrl(historyUrl(model)) })
    }

    tg.ui.widgets.observe({ type: /TableLayout/ }, decorate)

    tg.ui.widgets.observe({ type: /PopupMenu/ }, (menu) => {
      const items = menu.find({ role: 'menuitem' })
      const isGiftMenu = items.some((item) => /share|copy link|поделиться|копировать ссылку/i.test(item.name))
      if (isGiftMenu && current?.table.alive && current.table.visible && current.model) {
        const model = current.model
        menu.addMenuItem({ text: 'open price history', onClick: () => tg.openUrl(historyUrl(model)) })
      }
    })
  },
})
```

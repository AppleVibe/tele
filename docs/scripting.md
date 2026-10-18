---
name: tele-scripting
description: Write, fix and explain scripts for tele (a Telegram Desktop fork) in TypeScript or JavaScript. Use when the user wants a tele script, asks what tele's scripting API can do, or works with defineScript, tg.*, grants, tg.ui.widgets, interceptors or tele.d.ts.
---

# tele scripting

tele runs scripts: small TypeScript or JavaScript files that live in a folder, start when you switch them on, and can do anything tele itself can do. a script talks to telegram through the raw api (any method, any update, middleware around tele's own requests), reads and changes tele's local data and settings, adds its own commands, buttons, menu items, settings pages, notices, banners, search results, sticker sets and inline answers, opens its own web pages and telegram's mini apps, works with stories, gifts, calls and files on disk, and reaches into any window through the widget layer. next to the javascript standard library it gets the familiar web platform: `fetch`, `WebSocket`, `URL`, `AbortController`, `crypto.subtle`, `Intl`, workers and more. power is never cut down; it's gated by grants, which tele asks you to confirm in plain words before a script starts.

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
  - everything runs on tele's main thread: a script that blocks freezes tele until its time budget runs out (see [errors and limits](#errors-and-limits)). heavy work can move to a `Worker`, which runs on its own thread.
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
  - the same menu has Change the folder (pick any folder) and, once changed, Use the default folder. the choice is global for all accounts and saved in `tdata/tele_scripts.json`, which also holds `"sources"`, the update links of link-installed scripts (see [updates for link-installed scripts](#updates-for-link-installed-scripts)): `{ "folder": "...", "sources": { ... } }`.
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
  - `.ts` and `.mts` files go through a type stripper (sucrase): types are erased, enums and constructor parameter properties are compiled, nothing else changes and line numbers stay the same, and stack traces map columns back to the typescript source. there is no type checking at runtime; use `tsc` for that. typescript `namespace`s with values and legacy decorators are not supported.
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
import { nanoid } from 'nanoid'
import config from './config.json' with { type: 'json' }
const lazy = await import('./big-table.ts')
```

scripts can import the built-in `tele` module, their own files with relative paths, packages from `node_modules` (see [npm packages](#npm-packages)) and json files. static and dynamic `import()` both work.

- **grant:** none.
- **notes:**
  - `'tele'` exports `defineScript`, `Message`, `md` and `html`, plus every api type (`import { type Tg, type PeerInfo } from 'tele'`). it always wins over a package called `tele`.
  - a specifier starting with `./` or `../` is a file of the script; `#name` is an entry of the nearest `package.json`'s `"imports"`; anything else is a package. absolute paths and urls fail the start with `only relative imports, 'tele' and packages from node_modules work, not '<specifier>'`.
  - a relative path must stay inside the script's root (or inside the scripts folder's `node_modules`), or the start fails with `'<path>' is outside the script`. the root of a single-file script is the whole scripts folder (so it may import `./_lib/x.ts` or even `./other.ts`); the root of a folder script is its own folder.
  - resolution of your own files tries, in order: the exact path, then `+ .ts`, `+ .js`, `+ /index.ts`, `+ /index.js`; `.mts`, `.mjs` and `.json` are never guessed, write them out. files inside `node_modules` are resolved like node does it: the exact path, then `+ .js`, `+ .mjs`, `+ .ts`, `+ .json`, `+ /index.js`, `+ /index.mjs`, `+ /index.ts`. a missing file fails with `can't find '<path>'`.
  - json: a `.json` file, or any file imported `with { type: 'json' }`, is a module whose default export is the parsed value (no named exports). invalid json fails with the parser's `SyntaxError`. any other import attribute fails with `TypeError: import type '<type>' isn't supported, only type: 'json'` (or `the import attribute '<key>' isn't supported, only type: 'json'`). the generated `tsconfig.json` turns on `resolveJsonModule`, so `tsc` types json imports too.
  - a module is evaluated once per start; static and dynamic imports share it. a json file imported both with and without `with { type: 'json' }` is two modules with equal values.
  - every file a script loads, including files it tried and failed to load, package files, the `package.json` files resolution read and the `node_modules/<name>` folders it looked in for a missing package, is watched for [hot reload](#hot-reload-on-save).
  - `.ts` and `.mts` files keep their line numbers after stripping, and stack traces (`error.stack`, errors in the log) also map columns back to the typescript source, so `file.ts:12:34` is where your editor shows it. columns of `.js` files are byte offsets. a script that sets its own `Error.prepareStackTrace` gets the raw positions in its call sites.

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

### npm packages

```ts
// npm install nanoid dayjs   (in the scripts folder)
import { nanoid } from 'nanoid'
import dayjs from 'dayjs'
```

bare specifiers (`'pkg'`, `'pkg/sub/path'`, `'@scope/pkg'`) resolve from `node_modules` the way node and bundlers do. install packages with npm, pnpm, yarn or bun in the scripts folder, or in a folder script's own folder. es modules are the format; simple commonjs files work as a default export.

- **grant:** none. package code runs inside the script with the script's grants, like the script's own files.
- **notes:**
  - lookup: for an import in a file in folder `F`, tele tries `F/node_modules/<name>`, then the `node_modules` of each parent folder, up to and including the scripts folder. so a folder script sees its own `node_modules` first, then the scripts folder's; a single-file script uses the scripts folder's (and a package sees its own nested `node_modules` first).
  - the entry comes from `package.json`: `exports` first (a string, an array of fallbacks, condition objects, subpath exports like `"./sub"` and patterns like `"./features/*"`, the longest matching prefix wins). conditions are picked by priority, not by their order in the file: `import`, then `module`, then `browser`, then `default`. `require`, `node`, `types` and any other condition are never used; so a package with a `browser` build (no node built-ins) gets that one over its node `default`.
  - without `exports`: `module`, then `main`, then `index.js` (and `.mjs`, `.ts`); a subpath is a file inside the package with the same extension guesses.
  - `exports` is a whitelist: a subpath the package doesn't list fails with `package '<name>' doesn't export './sub'`, one mapped to `null` with `'<name>/sub' is not exported by node_modules/<name>/package.json`, and a package with only `require`/`node` conditions with `'<name>': node_modules/<name>/package.json has no condition tele uses (import, module, browser or default), only node, require`.
  - a package's `"imports"` (`#internal` specifiers, patterns, and targets that are other packages) work inside that package; your own folder script can use them too with its own `package.json`.
  - commonjs: a `.cjs` file, or a `.js` file under `node_modules` that has no `import`/`export` and uses `module.exports`, `exports.x =` or `require(`, runs on its own as a commonjs module (sloppy mode, `this` is `module.exports`, `exports`, `module`, `__filename` and `__dirname` exist) and becomes a single default export: `import pkg from 'pkg'` works, named imports from it (`import { x } from 'pkg'`) fail to link. a file that sets `exports.__esModule = true` and has `exports.default` gives `exports.default` as the default export (like esbuild). `require()` inside such a file throws `require('<name>') in <file>: tele runs a commonjs file only on its own and can't require() other modules; import an es module build of the package instead`. so umd bundles and dependency-free commonjs files work; anything that requires other files needs its es module build (often `lodash-es`-style packages or an `import` condition) or a bundle (`esbuild --bundle --format=esm`).
  - there is no node: `node:<name>` always fails, and a bare built-in name (`fs`, `path`, `crypto`…) fails unless a package with that name is installed (npm polyfills like `buffer` or `events` do work). the error says what to use instead, e.g. `'node:fs' is a node built-in, and tele scripts don't run on node: use tg.fs (the script's file area) instead`: `fs` → `tg.fs`, `path` → `URL` and string methods, `url` → the global `URL` and `URLSearchParams`, `querystring` → `URLSearchParams`, `crypto` → the global `crypto`, `buffer` → `Uint8Array`, `TextEncoder`, `TextDecoder`, `atob` and `btoa`, `string_decoder` → `TextDecoder`, `events` → `EventTarget`, `zlib` → `compression`, `worker_threads` → `Worker`, `child_process` → `tg.unsafe.exec`, `http`, `https`, `http2`, `net`, `tls`, `dns`, `dgram` → `fetch` and `WebSocket`, `timers` → `setTimeout` and `setInterval`, `util` → `structuredClone`, `TextEncoder` and `TextDecoder`, `console` → the global `console`; the rest say `tele has no equivalent`.
  - which packages work: es modules (or simple commonjs) that only need the language and the [globals](#globals) tele has, like date, string, id, parsing and validation libraries. packages that touch `window`, `document`, `localStorage`, `process` or node built-ins when they load fail with the usual `ReferenceError` or one of the errors above.
  - a package that isn't installed fails the start with `can't find package '<name>' in node_modules: install it in the scripts folder (npm install <name>)`; installing it restarts the script.
  - package files are watched like your own: `npm update` restarts the scripts that loaded the package. `node_modules` folders are never scanned for scripts.
  - typings: `tsc` uses the package's own types (`types`, a `types` condition in `exports`) or `@types/<name>`; the generated `tsconfig.json` resolves like a bundler (`moduleResolution: "Bundler"`).
  - workers can't import anything, packages included: bundle what a worker needs into its file.

Example:

```ts
// scripts/ids.ts, after `npm install nanoid dayjs` in the scripts folder
import { defineScript } from 'tele'
import { nanoid } from 'nanoid'
import dayjs from 'dayjs'

export default defineScript({
  name: 'ids',
  setup(tg) {
    tg.toast(`session ${nanoid(10)} started at ${dayjs().format('HH:mm:ss')}`)
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
  - only files the script actually loaded count (the entry, its imports, files loaded later with `import()`, files it tried to load, and the package files and `package.json` files of [npm packages](#npm-packages) it used). a new file nobody imports restarts nothing.
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

a version string for people, and the number tele compares when it checks a link-installed script for updates.

- **grant:** none.
- **notes:**
  - shown on the script page as "version {version}" and returned by `tg.scripts.list()`.
  - for updates, versions are compared semver-style: an optional leading `v`, dot-separated numbers (missing parts count as 0, so `1.2` equals `1.2.0`), an optional `-prerelease` that sorts before the release (`1.0.0-beta.2` < `1.0.0`), `+build` ignored. when either side isn't in that shape, any different text counts as an update.
  - a script without a version never shows "update available": tele only offers what the link's `defineScript({ version })` says is newer.
  - tele reads it statically (see [off until turned on](#off-until-turned-on)), so write it as a string literal.

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
  - the status line shows, in order: "Waiting for your approval", the start error (red), "Update available: {version}" (accent color), the description, "Running", "Starting" or "Off".
  - opening the manager checks every link-installed script for updates (at most once a minute per script); see [updates for link-installed scripts](#updates-for-link-installed-scripts).
  - clicking a row opens the [script page](#the-script-page).
  - the ⋮ menu: Install from a file, Install from a link, Open the scripts folder, Rescan the scripts folder, Change the folder, Use the default folder (only when changed), MTProto console.
  - new, removed and renamed scripts show up on their own: tele watches the folder and also checks it every 2 seconds (for folders where change notifications don't arrive, like network drives or some sync tools), and rescans whenever the manager opens. Rescan the scripts folder does it at once.

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
  - status: "It's waiting for your approval: it asks for permissions you haven't given yet." with Review permissions, or the start error in red (selectable). then, when the update link has a newer version, "Update available: {version}" with Update to {version}... .
  - Turned on: the switch. Reload (when on), Open the file, Show in folder, Remove... .
  - Settings: the page the script registered with `tg.registerSettings`, rendered inline.
  - Permissions: every granted grant in plain words with a revoke link each, then "Asks for, not given:" with declared grants you haven't approved, or "It asks for nothing.". revoking asks "Revoke «{grant}»? The script restarts and asks for it again if it needs it.".
  - Updates (single-file `.ts` and `.js` scripts only): "Update link: {url}" with Check for updates and Change update link..., or "No update link: it was installed from a file or copied into the folder." with Set update link... .
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
  - Install from a file: pick a `.ts` or `.js` file; it is copied into the scripts folder. it has no update link (set one on its page if you want updates).
  - Install from a link: "A direct link to a .ts or .js file. It goes into the scripts folder and stays off until you turn it on. tele checks the link for new versions." http and https only, at most 5 MB, 30 s timeout, redirects only to equally safe urls. the link you typed is remembered as the script's update link.
  - the install link `tg://tele/script?url=<encoded url>` (an http(s) url, `encodeURIComponent`-encoded) opens the Scripts manager's Install from a link box with that url filled in. nothing is downloaded until you press Install, and the script stays off until you turn it on and approve its grants, like any link install. a link without a valid http(s) url shows "This link doesn't point to a script.". the file gets the name at the end of the url.
  - the script catalog at [gettele.app/scripting/catalog](https://gettele.app/scripting/catalog) lists ready scripts with their grants; each card has an install link of that form, the source and a copy-link button (paste the link into Install from a link when `tg://` opens another app). catalog installs keep the catalog url as their update link.
  - other names are refused with "A script is a .ts or .js file.". an existing file asks "{file} is already in the scripts folder. Replace it?". replacing from a file drops the old update link; replacing from a link sets the new one.
  - after installing: "Installed {file}. It stays off until you turn it on.".
  - Remove... asks "Remove {name}? Its file goes to the recycle bin, its storage stays until you clear it." and moves the file (or the whole folder of a folder script) to the recycle bin, or deletes it when that isn't possible. its grants and its update link are forgotten.
  - if the script kept files in its [file area](#the-file-area), a second box asks "Also delete the files {name} kept in its file area? They are in {folder}."; Delete removes that folder.

Example:

```bash
# the same as Install from a file
cp ~/Downloads/auto-read.ts path/to/tele/scripts/
```

### updates for link-installed scripts

```ts
// script page > Update to {version}...
// script page > Updates > Check for updates | Set update link...
```

a script installed from a link keeps that link, and tele looks there for newer versions: when you open the Scripts manager and every 6 hours while tele runs (the first check a minute after start).

- **grant:** none.
- **notes:**
  - the update link is app-wide, kept per script file name in `tdata/tele_scripts.json` under `"sources"` (`{ "url", "etag", "latest" }`), next to `"folder"`. folder scripts have no update link.
  - a check downloads the link (at most 1 MB, 30 s timeout, tele's proxy, `If-None-Match` with the last `ETag`, so an unchanged file costs a `304`), reads `defineScript({ version })` from it the same static way as for scripts that are off, and remembers that version. nothing is written into the scripts folder and nothing runs.
  - when the link's version is newer than the installed one (see [definition.version](#definitionversion)), the row says "Update available: {version}" and the page shows it with Update to {version}... .
  - Update to {version}... downloads the file again and asks: "Update {name} from {old} to {new}? Its file is replaced and the old one goes to the recycle bin.", then the grants diff: "New grants:" (each in plain words, plus "It waits for your approval of them before it runs again." when it's on), "No longer asks for:", or "It asks for the same grants.". a grant counts as new only when the old declaration doesn't already cover it.
  - confirming moves the old file to the recycle bin, writes the new one and says "Updated {name} to {version}.". hot reload restarts a script that is on; when it now declares more than you approved it waits for your approval like any edit (see [the consent box](#the-consent-box)). a script that is off stays off.
  - when the downloaded file is byte-for-byte the installed one: "It's up to date.".
  - Check for updates checks this script now and says "Update available: {version}", "It's up to date." or "Can't check for updates: {error}".
  - Set update link... / Change update link... take a direct http(s) link to the newest `.ts`/`.js` file and check it at once; saving an empty field stops checking. use a link that always points at the latest version (a gist's raw link without the revision hash, a repo's raw `main` link), not a pinned revision.
  - failed automatic checks go to tele's `log.txt` only.
  - with the `-teleoffline` [launch flag](launch-flags.md) tele doesn't check at all, and Check for updates says "Can't check for updates: updates are off for this launch.". installing from a link still works: it's something you asked for.

Example:

```ts
// https://gist.githubusercontent.com/you/<id>/raw/pinger.ts
export default defineScript({
  name: 'pinger',
  version: '1.5.0', // was '1.4.2': everyone who installed the raw link sees "Update available: 1.5.0"
  grants: ['call(help.getConfig)'],
  setup(tg) {},
})
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
  - what needs no grant at all: `tg.toast`, `tg.ui` boxes and pages, commands, buttons, menu items, quick actions, shortcuts, `tg.storage`, navigation, reading `tg.options`, the app theme and player state, connection state, `tg.schedule`, `tg.scripts.list`, the script's own file area in `tg.fs`, `tg.image`, `compression`, workers, banners, sticker and gif panels, registering inline answers, search providers, the media viewer and html `tg.ui.webview` panels. they change nothing outside this tele or are triggered by you.
  - changing what tele shows you about messages and people (decorations, peer overrides, local messages) changes nothing on the server either, but it needs [`display`](#grant-display): a script could make a message say something it doesn't ("send money to this card") or make a stranger look verified, so tele asks first.
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
    'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft' | 'stories' | 'gifts'
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
    | 'notify'
    | 'stories'
    | 'gifts'
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
  | 'display'
  | `display(${Some<'messages' | 'peers' | 'local'>})`
  | 'fs.read'
  | `fs.read(${string})`
  | 'fs.write'
  | `fs.write(${string})`
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
'fs.read(documents/notes)'
```

scopes narrow a grant. what a scope may be depends on the grant.

- **grant:** n/a.
- **parameters:**
  - methods (`call`, `interceptRpc`): an exact api method name, checked against tele's schema, or a prefix ending in `*` (`messages.*`, `messages.send*`), not checked.
  - updates (`onUpdate`, `interceptUpdate`): an `Update` constructor name or one of the short ones (`updateShortMessage`, `updateShortChatMessage`, `updateShortSentMessage`); `onUpdate` also takes `new_message`, `edit_message` and `delete_message`.
  - lists (`account.read`, `account.write`, `display`): one of the fixed words.
  - hosts (`fetch`): a host name; lowercased; covers the host and its subdomains.
  - folders (`fs.read`, `fs.write`): an absolute path, or `~`, `home`, `documents`, `downloads`, `desktop`, `pictures`, `music`, `videos` or `temp` (the system's folders), optionally followed by `/sub`; covers the folder and everything in it. anything else is `grant 'fs.read(x)': 'x' is not a folder (...)`.
  - no scope at all: every other grant. `grant '<entry>' takes no scopes` otherwise.
- **notes:**
  - a glob matches by prefix: `call(messages.*)` covers `messages.getHistory`, but never a [dangerous method](#dangerous-methods).
  - `fetch(github.com)` covers `github.com` and `api.github.com`, not `notgithub.com`.
  - `fs.read(documents)` covers every file under the documents folder; `..` is resolved first, so `documents/../secret.txt` isn't inside it.
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
  - a grant covers another of the same name when the scopes are equal, when it is bare, when it is a glob whose prefix covers the other's method or prefix, when its host covers the other's host or subdomain, or when its folder contains the other's folder (`fs.read(documents)` covers `fs.read(documents/notes)`).
  - an exact dangerous method (`call(messages.deleteMessages)`) is covered only by itself, never by a bare grant or a glob.
  - `account.write(gifts)` is covered only by itself: a bare `account.write` (or `account.write(*)`) never covers it.
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
  - caution: acting as you, reaching outside tele or changing what it shows you (`account.write`, `interceptSendMessage`, `clipboard.read`, `options`, `app`, `calls`, `accounts`, `files.write`, `ui.read`, `ui.write`, `display`, `fs.read(<folder>)`, `fs.write(<folder>)`, bare `call`...).
  - dangerous: `unsafe.exec`, `unsafe.automate`, `unsafe.disableApiFiltering`, bare `fs.read` and `fs.write`, `account.write(gifts)`, and exact entries for dangerous methods (`call(messages.deleteMessages)`, `interceptRpc(channels.leaveChannel)`).
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

the consent box shows one bullet per grant name, in a fixed order (account.read, account.write, onUpdate, call, interceptRpc, interceptUpdate, interceptSendMessage, fetch, clipboard.read, clipboard.write, openUrl, notify, interceptLink, interceptNotification, scripts, app, interceptDrop, calls, accounts, ui.read, ui.write, fs.read, fs.write, display, files.write, options), then the dangerous line.

- **grant:** n/a.
- **notes:**
  - a bare grant shows its "everything" sentence; scoped ones show the scoped sentence with the scopes joined by commas (methods, updates and hosts as written; account scopes as words like "chats and contacts", folders as written).
  - dangerous parts are joined with "; " in the bold line, in this order: "send {methods}" for `call`, "intercept {methods}" for `interceptRpc`, "turn off the account protection: log in, change the password and sessions, see login codes", "run any program on your computer, with your rights", "press any button in tele for you", then, in the order the grants are declared, "transfer, sell, convert and upgrade your gifts" for `account.write(gifts)`, "read any file on your computer" for a bare `fs.read` and "create, change and delete any file on your computer" for a bare `fs.write`.
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

every `account.read` scope at once: profile, chats and contacts, messages, chat list, history, drafts, stories and gifts.

- **grant:** `account.read`, `account.read(*)`.
- **tier:** neutral.
- **consent text:** "Read your profile, chats, messages, history, drafts, stories and gifts.".
- **unlocks:** everything in the eight scope items below.
- **notes:**
  - prefer the scopes you need; the box is shorter and you approve less.

Example:

```ts
grants: ['account.read']
```

### grant: account.read(self)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft' | 'stories' | 'gifts'
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
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft' | 'stories' | 'gifts'
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
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft' | 'stories' | 'gifts'
>})`
```

lets the script read messages by id, download media and look into tele's message cache.

- **grant:** `account.read(messages)`.
- **tier:** neutral.
- **consent text:** "Read your messages.".
- **unlocks:** `tg.getMessages`, `tg.downloadMedia` (both forms), `tg.decorateMessages` (together with `display(messages)`), `tg.getCachedMessage` (always `null` without it), the `message` field of `tg.interceptNotification`, the cached `previous` of `tg.onMessageEdited` and `messages` of `tg.onMessageDeleted`, `tg.tele.bookmarks.list`, `tg.tele.editHistory`, `tg.tele.deleted.list`, `onKept` and `interceptKeep` (that one with `options`), `tg.interceptSearch`, and the raw methods `messages.getMessages` and `channels.getMessages`.
- **throws:** `TeleError` `not-granted` (`tg.downloadMedia needs the grant 'account.read(messages)'`).

Example:

```ts
const [message] = await tg.getMessages('me', [1])
console.log(message?.text)
```

### grant: account.read(dialogs)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft' | 'stories' | 'gifts'
>})`
```

lets the script read your chat list and folders.

- **grant:** `account.read(dialogs)`.
- **tier:** neutral.
- **consent text:** "Read your chat list.".
- **unlocks:** `tg.getDialogs`, `tg.iterDialogs`, `tg.local.dialogs()`, `tg.local.unread()`, `tg.local.folders()`, `tg.tele.pins.list`, the chats in the rules of `tg.tele.folders.list()`, and the raw methods `messages.getDialogs`, `messages.getPeerDialogs`, `messages.getPinnedDialogs`.
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
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft' | 'stories' | 'gifts'
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
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft' | 'stories' | 'gifts'
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

### grant: account.read(stories)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft' | 'stories' | 'gifts'
>})`
```

lets the script read stories: a peer's active stories, its archive and pinned stories, who has stories to watch, and new stories as they come.

- **grant:** `account.read(stories)`.
- **tier:** neutral.
- **consent text:** "Read your stories." (scopes are joined: "Read your chats and contacts, stories.").
- **unlocks:** `tg.stories.list`, `tg.stories.get`, `tg.stories.archive`, `tg.stories.pinned`, `tg.stories.sources`, `tg.stories.onStory`, `tg.stories.interceptStoryView`, and the raw methods `stories.getPeerStories`, `stories.getStoriesByID`, `stories.getStoriesArchive`, `stories.getPinnedStories`.
- **throws:** `TeleError` `not-granted` (`tg.stories.sources needs the grant 'account.read(stories)'`).
- **notes:**
  - `tg.stories.registerStoryAction` needs no grant; marking stories as read is `account.write(stories)`. see [stories](#stories).

Example:

```ts
for (const source of tg.stories.sources()) console.log(source.peer, source.unread)
```

### grant: account.read(gifts)

```ts
`account.read(${Some<
  'self' | 'peers' | 'messages' | 'dialogs' | 'history' | 'draft' | 'stories' | 'gifts'
>})`
```

lets the script read star gifts and stars: the gifts on a profile, unique gifts by slug, the gift catalog, what a unique gift is worth, your stars balance and its history.

- **grant:** `account.read(gifts)`.
- **tier:** neutral.
- **consent text:** "Read your gifts." (scopes are joined: "Read your profile, gifts.").
- **unlocks:** `tg.gifts.list`, `tg.gifts.get`, `tg.gifts.catalog`, `tg.gifts.value`, `tg.stars.balance`, `tg.stars.history`, and the raw methods `payments.getSavedStarGifts`, `payments.getSavedStarGift`, `payments.getUniqueStarGift`, `payments.getStarGifts`, `payments.getUniqueStarGiftValueInfo`, `payments.getStarsStatus`, `payments.getStarsTransactions`.
- **throws:** `TeleError` `not-granted` (`tg.gifts.list needs the grant 'account.read(gifts)'`).
- **notes:**
  - changing gifts is the separate, dangerous `account.write(gifts)`. see [gifts and stars](#gifts-and-stars).

Example:

```ts
const { count } = await tg.gifts.list()
console.log(count, 'gifts on your profile')
```

### grant: account.write

```ts
| 'account.write'
```

every `account.write` scope but one at once: send, edit, delete, forward, react, read, typing, drafts, notification settings and stories. gifts are left out: `account.write(gifts)` is only given by its exact entry.

- **grant:** `account.write`, `account.write(*)`.
- **tier:** caution.
- **consent text:** "Act as you: send, edit, delete and forward messages, react, read chats, type, change drafts and notification settings and post stories (not your gifts: they need their own grant).".
- **unlocks:** everything in the scope items below except `account.write(gifts)`.

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
  | 'notify'
  | 'stories'
  | 'gifts'
>})`
```

lets the script send messages and upload files as you.

- **grant:** `account.write(send)`.
- **tier:** caution.
- **consent text:** "Act as you: send messages." (scopes are joined: "Act as you: send messages, react.").
- **unlocks:** `tg.sendMessage`, `tg.sendMedia`, `tg.sendFile`, `tg.uploadFile`, `message.reply`, sending from the script's sticker sets and gif sources (`tg.ui.registerStickerSet`, `tg.ui.registerGifSource`, checked on click), sending the inline answers of `tg.registerInline` (checked when the user picks a result: without it tele shows a toast and sends nothing; registering needs no grant), and the raw methods `messages.sendMessage`, `messages.sendMedia`, `messages.sendMultiMedia`.
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
  | 'notify'
  | 'stories'
  | 'gifts'
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
  | 'notify'
  | 'stories'
  | 'gifts'
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
  | 'notify'
  | 'stories'
  | 'gifts'
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
  | 'notify'
  | 'stories'
  | 'gifts'
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
  | 'notify'
  | 'stories'
  | 'gifts'
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
  | 'notify'
  | 'stories'
  | 'gifts'
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
  | 'notify'
  | 'stories'
  | 'gifts'
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

### grant: account.write(notify)

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
  | 'notify'
  | 'stories'
  | 'gifts'
>})`
```

lets the script change a chat's notification settings that are kept on the server: its notification sound and a channel's silent posting.

- **grant:** `account.write(notify)`.
- **tier:** caution.
- **consent text:** "Act as you: change notification settings.".
- **unlocks:** `tg.notifications.setSound(peer, sound)` and `tg.compose.setSendOptions({ silent })`.
- **throws:** `TeleError` `not-granted` (`tg.notifications.setSound needs the grant 'account.write(notify)'`).
- **notes:**
  - reading a chat's sound (`tg.notifications.getSound`) needs nothing.

Example:

```ts
await tg.notifications.setSound('me', 'none')
```

### grant: account.write(stories)

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
  | 'notify'
  | 'stories'
  | 'gifts'
>})`
```

lets the script post, edit and delete your stories, react to stories and mark them as read.

- **grant:** `account.write(stories)`.
- **tier:** caution.
- **consent text:** "Act as you: post, edit and delete stories.".
- **unlocks:** `tg.stories.post`, `tg.stories.edit`, `tg.stories.delete`, `tg.stories.react`, `tg.stories.markRead`, and the raw methods `stories.sendStory`, `stories.editStory`, `stories.deleteStories`, `stories.readStories`, `stories.sendReaction` (`stories.deleteStories` is a [dangerous method](#dangerous-methods), but this grant allows it, like `account.write(delete)` does for messages).
- **throws:** `TeleError` `not-granted` (`tg.stories.post needs the grant 'account.write(stories)'`).
- **notes:**
  - posting bytes uploads them itself; it doesn't need `account.write(send)`.

Example:

```ts
const photo = (await tg.ui.openFile({ filter: 'Images (*.jpg *.png)' }))?.[0]
if (photo) await tg.stories.post({ media: photo.bytes, caption: 'from tele' })
```

### grant: account.write(gifts)

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
  | 'notify'
  | 'stories'
  | 'gifts'
>})`
```

lets the script transfer, sell, convert, upgrade, pin and hide your star gifts. transferring and upgrading can spend stars, without a confirmation box.

- **grant:** `account.write(gifts)`, only as this exact entry: a bare `account.write` or `account.write(*)` never covers it.
- **tier:** dangerous.
- **consent text:** "Act as you: transfer, sell, convert and upgrade your gifts.", and "transfer, sell, convert and upgrade your gifts" in the bold "Dangerous: ..." line.
- **unlocks:** `tg.gifts.transfer`, `tg.gifts.convert`, `tg.gifts.upgrade`, `tg.gifts.sell`, `tg.gifts.unlist`, `tg.gifts.setPinned`, `tg.gifts.setVisible`, and the raw methods `payments.saveStarGift`, `payments.convertStarGift`, `payments.upgradeStarGift`, `payments.transferStarGift`, `payments.updateStarGiftPrice`, `payments.toggleStarGiftsPinnedToTop`, plus `payments.getPaymentForm` and `payments.sendStarsForm` for a gift upgrade or transfer invoice.
- **throws:** `TeleError` `not-granted` (`tg.gifts.transfer needs the grant 'account.write(gifts)'`).
- **notes:**
  - grant it only to scripts you trust with your stars. see [gifts and stars](#gifts-and-stars).

Example:

```ts
export default defineScript({
  name: 'gift mover',
  grants: ['account.read(gifts)', 'account.write(gifts)'],
  async setup(tg) {
    const { gifts } = await tg.gifts.list()
    const unique = gifts.find((gift) => gift.unique)
    if (unique) await tg.gifts.transfer(unique, '@friend')
  },
})
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
- **unlocks:** `fetch(url, init?)` to covered hosts and redirects to covered hosts, `new WebSocket(url)` to covered hosts, and `tg.ui.webview({ url })` for the url's host; the page of an html webview may reach covered hosts too.
- **throws:** `TeleError` `not-granted` synchronously (`fetch(<url>) needs the grant 'fetch(<host>)'`); a redirect to another host rejects with `TeleError` `not-granted` whose `grant` is the `fetch(<host>)` to add.
- **notes:**
  - only http and https (`ws` and `wss` for `WebSocket`).

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
- **unlocks:** `tg.options.set(id, value)`, `tg.tele.ignored.set`, `tg.tele.ghost.set`, `tg.tele.localNames.set`, `tg.tele.bookmarks.add` / `remove`, `tg.tele.pins.pin` / `unpin`, `tg.tele.folders.create` / `edit` / `delete` / `reorder`, `tg.tele.hiddenWords.add` / `remove`, and `tg.tele.deleted.interceptKeep` (together with `account.read(messages)`).
- **throws:** `TeleError` `not-granted` (`tg.options.set needs the grant 'options'`).
- **notes:**
  - reading settings (`tg.options.list`, `get`, `onChange`) needs nothing; reading the ignored, ghost and local-name lists needs `account.read(peers)`, bookmarks, edit history and kept messages `account.read(messages)`, pins `account.read(dialogs)`; folders and hidden words are free to read.

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
  - reading and writing files yourself is `tg.fs`, with [`fs.read`](#grant-fsread) / [`fs.write`](#grant-fswrite) outside the script's own area.

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
- **unlocks:** `tg.interceptDrop(interceptor)` and `tg.compose.interceptPaste(interceptor)`.
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

lets the script see and control this account's calls, group calls and video chats.

- **grant:** `calls`.
- **tier:** caution.
- **consent text:** "See your calls, answer, decline or start them, mute you.".
- **unlocks:** all of `tg.calls`: `current`, `onChange`, `answer`, `hangup`, `setMuted`, `start`, and for group calls and video chats `group`, `onGroupChange`, `join`, `leave`, `raiseHand`, `participants`.
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
- **unlocks:** `tg.ui.widgets.roots()`, `tg.ui.widgets.find(...)`, `tg.ui.widgets.observe(...)`, and on every `Widget` its getters, `parent`, `children`, `find` and `closest`; also `tg.ui.webApps()` and `tg.ui.onWebAppEvent(callback)`, because mini app windows are tele windows. the widget api is documented in the widget layer section.
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

### grant: display

```ts
| 'display'
```

every `display` scope at once: rewrite or hide messages, change how people and chats look, and show messages that were never sent.

- **grant:** `display`, `display(*)`.
- **tier:** caution.
- **consent text:** "Change what you see on this device: rewrite or hide messages, rename people and chats and change their marks, and show messages that were never sent.".
- **unlocks:** everything in the three scope items below.
- **notes:**
  - nothing here reaches the server or other people: it only changes what this tele shows you. that is exactly why it asks: a script could make a message say something it doesn't ("send money to this card"), hide a warning, or make a stranger look verified.
  - prefer the scopes you need.

Example:

```ts
grants: ['display']
```

### grant: display(messages)

```ts
`display(${Some<'messages' | 'peers' | 'local'>})`
```

lets the script change how real messages look: shown text, a footer, opacity, hiding them, a badge, buttons under them.

- **grant:** `display(messages)`.
- **tier:** caution.
- **consent text:** "Change what you see on this device: messages." (scopes are joined: "Change what you see on this device: messages, chats and contacts.").
- **unlocks:** `tg.decorateMessages(decorator)` (which also needs `account.read(messages)`, checked after this one) and `tg.decorateMessage(peer, id, decoration)`.
- **throws:** `TeleError` `not-granted` with `grant` set to `'display(messages)'`: `tg.decorateMessages needs the grant 'display(messages)'` (thrown right away), `tg.decorateMessage needs the grant 'display(messages)'` (a rejection).
- **notes:**
  - `tg.getCachedMessage` doesn't need it; reading the cache is `account.read(messages)`.

Example:

```ts
import { md } from 'tele'

export default defineScript({
  name: 'spoiler secrets',
  grants: ['display(messages)', 'account.read(messages)'],
  setup(tg) {
    tg.decorateMessages((message) =>
      /password/i.test(message.text) ? { text: md`||${message.text}||` } : null)
  },
})
```

### grant: display(peers)

```ts
`display(${Some<'messages' | 'peers' | 'local'>})`
```

lets the script change how users, bots, groups and channels look in this tele.

- **grant:** `display(peers)`.
- **tier:** caution.
- **consent text:** "Change what you see on this device: chats and contacts.".
- **unlocks:** `tg.overridePeer(peer, override)`, with every `PeerOverride` field: `name`, `verified`, `scam`, `fake`, `premium`, `botVerification`, `emojiStatus`, `color`, `badge`, `hidden`, `label`, `preview`.
- **throws:** `TeleError` `not-granted` (a rejection): `tg.overridePeer needs the grant 'display(peers)'`, `grant` is `'display(peers)'`.
- **notes:**
  - resolving a marked id or username for `overridePeer` still needs `account.read(peers)`; input peers and `PeerInfo`s you already hold don't.

Example:

```ts
export default defineScript({
  name: 'boss badge',
  grants: ['display(peers)', 'account.read(peers)'],
  async setup(tg) {
    await tg.overridePeer('@my_boss', { badge: '👔' })
  },
})
```

### grant: display(local)

```ts
`display(${Some<'messages' | 'peers' | 'local'>})`
```

lets the script show local ("ghost") messages: messages and service lines that were never sent and exist only in this tele.

- **grant:** `display(local)`.
- **tier:** caution.
- **consent text:** "Change what you see on this device: messages that were never sent.".
- **unlocks:** `tg.addLocalMessage(chat, options?)`, `localMessage.edit(changes)`, and the `'local'` verdict of `tg.interceptSendMessage`.
- **throws:** `TeleError` `not-granted` (a rejection), `grant` is `'display(local)'`: `tg.addLocalMessage needs the grant 'display(local)'`, `localMessage.edit needs the grant 'display(local)'`.
- **notes:**
  - `tg.localMessages()` and `localMessage.remove()` need nothing: a script can always list and remove its own local messages, persisted ones included.
  - a `'local'` verdict without it is a fault in the send interceptor, and the send doesn't go out.

Example:

```ts
export default defineScript({
  name: 'notes to self',
  grants: ['display(local)', 'interceptSendMessage'],
  setup(tg) {
    tg.interceptSendMessage({ text: /^\/note / }, () => 'local')
  },
})
```

### grant: fs.read

```ts
| 'fs.read'
| `fs.read(${string})`
```

lets `tg.fs` read files and folders outside the script's own file area.

- **grant:** `fs.read(<folder>, ...)` for those folders and everything inside them, or bare `fs.read` (`fs.read(*)`) for any file on the computer.
- **parameters:**
  - `scope` (folder): an absolute path (`C:/Users/me/notes`, `/home/me/notes`), or `~`, `home`, `documents`, `downloads`, `desktop`, `pictures`, `music`, `videos` or `temp` (the system's folders), optionally followed by `/sub`. `\` works like `/`. anything else is `grant 'fs.read(x)': 'x' is not a folder (an absolute path, ~ or documents, downloads, desktop, pictures, music, videos, home, temp, optionally followed by /sub)`.
- **tier:** caution with a folder; bare `fs.read` is dangerous.
- **consent text:** scoped: "Read files in {folders}." (the folders as written); bare: "Read any file on your computer.", plus "read any file on your computer" in the bold "Dangerous: ..." line.
- **unlocks:** outside the file area: `tg.fs.readText`, `tg.fs.readBytes`, `tg.fs.list`, `tg.fs.stat`, `tg.fs.exists`, and the source of `tg.fs.copy`.
- **throws:** `TeleError` `not-granted` whose `grant` is the exact absolute path (`tg.fs.read needs the grant 'fs.read(C:/Users/me/Documents/x.txt)'`); any folder grant covering it works too.
- **notes:**
  - the script's own file area needs no grant at all.
  - it doesn't include writing; declare `fs.write` too to change files.
  - tele's data and other scripts' areas stay out of reach even with the bare grant. see [the file area](#the-file-area).

Example:

```ts
export default defineScript({
  name: 'todo reader',
  grants: ['fs.read(documents/todo)'],
  async setup(tg) {
    const text = await tg.fs.readText('documents/todo/today.md')
    tg.toast(`${text.split('\n').length} lines to do`)
  },
})
```

### grant: fs.write

```ts
| 'fs.write'
| `fs.write(${string})`
```

lets `tg.fs` create, change, move and delete files and folders outside the script's own file area.

- **grant:** `fs.write(<folder>, ...)` for those folders and everything inside them, or bare `fs.write` (`fs.write(*)`) for any file on the computer.
- **parameters:**
  - `scope` (folder): the same folders as `fs.read`: an absolute path, or `~`, `home`, `documents`, `downloads`, `desktop`, `pictures`, `music`, `videos` or `temp`, optionally followed by `/sub`.
- **tier:** caution with a folder; bare `fs.write` is dangerous.
- **consent text:** scoped: "Create, change and delete files in {folders}."; bare: "Create, change and delete any file on your computer.", plus "create, change and delete any file on your computer" in the bold "Dangerous: ..." line.
- **unlocks:** outside the file area: `tg.fs.writeText`, `tg.fs.writeBytes`, `tg.fs.mkdir`, `tg.fs.remove`, both ends of `tg.fs.rename`, and the target of `tg.fs.copy`.
- **throws:** `TeleError` `not-granted` whose `grant` is the exact absolute path (`tg.fs.write needs the grant 'fs.write(C:/Users/me/Desktop/out.txt)'`).
- **notes:**
  - it doesn't include reading: a script that reads back what it writes declares both.
  - `tg.downloadMedia({ saveTo })` is still `files.write`, a different grant.

Example:

```ts
export default defineScript({
  name: 'daily export',
  grants: ['fs.write(documents/tele-export)'],
  async setup(tg) {
    await tg.fs.mkdir('documents/tele-export', { recursive: true })
    await tg.fs.writeText(`documents/tele-export/${new Date().toISOString().slice(0, 10)}.txt`, 'hello')
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

everything except workers runs on tele's main thread, so every entry into script code has a time limit. over it, the code is stopped with an error that `try` / `catch` can't catch, logged as `took too long and was stopped`.

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
  - a slow script freezes tele for up to its budget, so keep handlers short and move heavy work behind `await`s and timers, or into a `Worker`.
  - the newer interceptors and providers (`tg.compose.interceptPaste`, `tg.ui.registerSearchProvider`, `tg.interceptSearch`, `tg.stories.interceptStoryView`, `tg.tele.deleted.interceptKeep`) get 2 s to answer and then fall back to what tele does by itself; see each item.
  - code inside a `Worker` has no budget: it runs on its own thread, so an endless loop only blocks that worker.

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
  - the file area (`tg.fs`): 256 MB per script; one read returns at most 256 MB.
  - `compression.gunzip` / `inflate` / `inflateRaw`: 64 MB of output by default (`maxSize`, at most 256 MB).
  - `tg.image`: 100 megapixels per image, in and out.
  - `WebSocket`: 64 MB per message.
  - workers: 8 per script at a time, each with its own 256 MB of memory.
  - `tg.app.playSound` and `tg.stories.post` bytes: 10 MB.
  - logs: the last 2000 lines per script.
  - installing from a link: 5 MB.
  - update checks and updates of link-installed scripts: 1 MB.
  - metadata of scripts that are off is read from the first 1 MB of the entry file.
  - hot reload watches at most 512 paths in the scripts folder.

Example:

```ts
const hugeObject = { blob: 'x'.repeat(20_000_000) }
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
  - from tele: `console`, timers, `defineScript`, `fetch` (from `setup` on), `crypto` with the whole `crypto.subtle`, `TextEncoder`, `TextDecoder`, `URL`, `URLSearchParams`, `EventTarget`, `Event`, `CustomEvent`, `AbortController`, `AbortSignal`, `structuredClone`, `reportError`, `WebSocket`, `MessageEvent`, `CloseEvent`, `Worker`, `ErrorEvent`, `Intl` (and with it locale-aware `toLocaleString` and `localeCompare`), `compression`, `TeleError`, `RpcError`. QuickJS adds `atob`, `btoa`, `performance` and `queueMicrotask`.
  - `Date` uses the computer's time zone.

Example:

```ts
const byKind = Object.groupBy(messages, (message) => message.mediaType ?? 'text')
const { promise, resolve } = Promise.withResolvers<void>()
```

### what is not available

```ts
// not defined in scripts
// process, Buffer, XMLHttpRequest, Blob,
// window, document, navigator, localStorage, setImmediate
```

scripts are not node and not a browser.

- **grant:** none.
- **notes:**
  - no node: no `require`, `module`, `process`, `Buffer` or environment. files come from `tg.fs` (the script's own file area, other folders with `fs.read` / `fs.write`), `tg.ui.openFile` / `tg.ui.saveFile` and `tg.downloadMedia`; programs from `tg.unsafe.exec`.
  - no dom: no `window`, `document`, `navigator`, `localStorage`. persist with `tg.storage`.
  - no `XMLHttpRequest`; use `fetch`, and `WebSocket` for sockets. no `Blob`: binary data is a `Uint8Array` or an `ArrayBuffer`.
  - no `setImmediate`; use `queueMicrotask` or `setTimeout(callback, 0)`.
  - `require`, `module`, `exports`, `__filename` and `__dirname` exist only inside commonjs files of [npm packages](#npm-packages); es modules (your scripts) have none of them.
  - extra arguments to `setTimeout` / `setInterval` are ignored.

Example:

```ts
// instead of Buffer.from('hello').toString('base64')
const base64 = new TextEncoder().encode('hello').toBase64()
// instead of setImmediate(next)
setTimeout(() => console.log('next turn'), 0)
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
interface FetchInit {
  method?: string
  headers?: Record<string, string>
  body?: string | Uint8Array
  timeout?: number
  maxSize?: number
}

interface FetchInit {
  signal?: AbortSignal | null
}

declare function fetch(url: string | URL, init?: FetchInit): Promise<FetchResponse>
```

makes an http or https request through tele's network stack and resolves with the response.

- **grant:** `fetch(<host>)` (or a parent domain, or bare `fetch`).
- **parameters:**
  - `url` (`string | URL`): an absolute `http://` or `https://` url, as a string or a `URL`.
  - `init.method` (`string`, optional): any method, uppercased; default `GET`.
  - `init.headers` (`Record<string, string>`, optional): a plain object of header names and values.
  - `init.body` (`string | Uint8Array`, optional): sent as UTF-8 text or raw bytes; `null` / `undefined` send nothing.
  - `init.timeout` (`number`, optional): milliseconds without any data before giving up; default 30000, `0` means none.
  - `init.maxSize` (`number`, optional): the largest response body in bytes; default 16 MB (16777216), `0` means no limit besides memory.
  - `init.signal` (`AbortSignal | null`, optional): aborting it cancels the request and rejects with `signal.reason`; an already aborted signal rejects before any request or grant check.
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
  signal: AbortSignal.timeout(10_000),
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

### class URL

```ts
declare class URL {
  constructor(url: string | URL, base?: string | URL)
  href: string
  readonly origin: string
  protocol: string
  username: string
  password: string
  host: string
  hostname: string
  port: string
  pathname: string
  search: string
  readonly searchParams: URLSearchParams
  hash: string
  toString(): string
  toJSON(): string
  static canParse(url: string | URL, base?: string | URL): boolean
  static parse(url: string | URL, base?: string | URL): URL | null
}
```

parses a url the way browsers do (the WHATWG URL standard) and lets you read and change its parts.

- **grant:** none.
- **parameters:**
  - `url` (`string | URL`): an absolute url, or a relative one when `base` is given.
  - `base` (`string | URL`, optional): the url `url` is resolved against (`../`, `?query`, `#hash`, `//host/path` all work).
  - `href`: the whole url; setting it reparses everything.
  - `protocol`, `username`, `password`, `host` (with the port), `hostname`, `port`, `pathname`, `search` (with `?`), `hash` (with `#`): the parts as strings; setting one changes only that part, invalid values are ignored like in browsers.
  - `origin` (read only): `scheme://host[:port]` for `http`, `https`, `ws`, `wss` and `ftp`, `'null'` for everything else.
  - `searchParams` (read only): the query as a live `URLSearchParams`; changing it rewrites `search`, setting `search` or `href` refreshes it.
  - `URL.canParse(url, base?)`: whether `new URL(url, base)` would work.
  - `URL.parse(url, base?)`: the `URL`, or `null` instead of throwing.
- **returns:** `toString()` and `toJSON()` give `href`, so `JSON.stringify` and template strings print the url.
- **throws:** `TypeError: invalid url: <url>` from the constructor and the `href` setter.
- **notes:**
  - special schemes (`http`, `https`, `ws`, `wss`, `ftp`, `file`) get normalized hosts (lowercase, IPv4 and IPv6 forms, punycode for unicode domains), default ports dropped, dot segments resolved and `\` read as `/`. other schemes (`tg:`, `mailto:`, `data:`, your own) keep their text and get an opaque origin.
  - each part is percent-encoded with its own rules; `searchParams` uses form encoding (space as `+`).
  - unicode domains are lowercased, NFKC-normalized and punycoded; the full UTS 46 mapping table isn't there, so rare characters may differ from a browser.
  - `fetch` takes a `URL` directly.

Example:

```ts
const api = new URL('/search', 'https://api.example.com')
api.searchParams.set('q', 'tele scripts')
api.searchParams.set('page', '2')
console.log(api.href) // https://api.example.com/search?q=tele+scripts&page=2
const response = await fetch(api)
```

### class URLSearchParams

```ts
declare class URLSearchParams {
  constructor(
    init?: Iterable<readonly [string, string]> | readonly (readonly string[])[] | Record<string, string> | string | URLSearchParams,
  )
  readonly size: number
  append(name: string, value: string): void
  delete(name: string, value?: string): void
  get(name: string): string | null
  getAll(name: string): string[]
  has(name: string, value?: string): boolean
  set(name: string, value: string): void
  sort(): void
  forEach(callback: (value: string, name: string, parent: URLSearchParams) => void, thisArg?: unknown): void
  entries(): URLSearchParamsIterator<[string, string]>
  keys(): URLSearchParamsIterator<string>
  values(): URLSearchParamsIterator<string>
  [Symbol.iterator](): URLSearchParamsIterator<[string, string]>
  toString(): string
}

interface URLSearchParamsIterator<T> extends IteratorObject<T, BuiltinIteratorReturn, unknown> {
  [Symbol.iterator](): URLSearchParamsIterator<T>
}
```

an ordered list of name/value pairs in `application/x-www-form-urlencoded` form: query strings and form bodies.

- **grant:** none.
- **parameters:**
  - `init` (optional): a query string (a leading `?` is skipped), an object of names and values, or anything iterable of `[name, value]` pairs (arrays, a `Map`, another `URLSearchParams`).
  - `append(name, value)`: adds a pair at the end, even if the name is there.
  - `delete(name, value?)`: removes every pair with that name, or only the ones with that value too.
  - `get(name)` / `getAll(name)`: the first value (`null` when missing) / all values in order.
  - `has(name, value?)`: whether such a pair exists.
  - `set(name, value)`: replaces the first pair with that name and removes the others, or appends.
  - `sort()`: sorts by name (by UTF-16 code units), keeping the order of equal names.
  - `size`: the number of pairs.
- **returns:** `toString()` gives the encoded string without `?`; `entries`/`keys`/`values` and `for...of` give live iterators with iterator helpers (`.map`, `.toArray`).
- **throws:** `TypeError` for a pair that doesn't have exactly two items, or when a method gets too few arguments.
- **notes:**
  - encoding: letters, digits and `*-._` stay, space becomes `+`, everything else is `%XX` of its UTF-8 bytes; decoding turns `+` into a space and invalid UTF-8 into U+FFFD.
  - the one from `url.searchParams` writes every change back into the url.

Example:

```ts
const body = new URLSearchParams({ grant_type: 'client_credentials', scope: 'read write' })
await fetch('https://auth.example.com/token', {
  method: 'POST',
  headers: { 'content-type': 'application/x-www-form-urlencoded' },
  body: body.toString(),
})
```

### class EventTarget

```ts
declare class EventTarget {
  constructor()
  addEventListener(
    type: string,
    callback: EventListenerOrEventListenerObject | null,
    options?: AddEventListenerOptions | boolean,
  ): void
  removeEventListener(
    type: string,
    callback: EventListenerOrEventListenerObject | null,
    options?: EventListenerOptions | boolean,
  ): void
  dispatchEvent(event: Event): boolean
}

interface AddEventListenerOptions extends EventListenerOptions {
  once?: boolean
  passive?: boolean
  signal?: AbortSignal
}

interface EventListenerOptions {
  capture?: boolean
}

interface EventListener {
  (evt: Event): void
}

interface EventListenerObject {
  handleEvent(object: Event): void
}

type EventListenerOrEventListenerObject = EventListener | EventListenerObject
```

the browser's event emitter. `AbortSignal`, `WebSocket` and other web-style objects are event targets, and your own classes can extend it.

- **grant:** none.
- **parameters:**
  - `callback`: a function, or an object with a `handleEvent(event)` method (called with the object as `this`). a function gets the target as `this`.
  - `options.once`: remove the listener before its first call.
  - `options.signal`: remove the listener when this `AbortSignal` aborts; an already aborted signal adds nothing.
  - `options.passive`: `preventDefault()` does nothing inside this listener.
  - `options.capture` (or a boolean `options`): kept only to tell listeners apart; there is no tree, so no capturing phase.
- **returns:** `dispatchEvent` returns `false` when a listener called `preventDefault()` on a cancelable event, else `true`.
- **throws:** `TypeError` when `dispatchEvent` gets something that isn't an `Event`; a `DOMException` `InvalidStateError` when the event is already being dispatched.
- **notes:**
  - the same function with the same `capture` is added only once.
  - listeners run synchronously in the order they were added; listeners added during a dispatch wait for the next one, removed ones are skipped.
  - an exception in one listener doesn't stop the others: it goes to `reportError` and shows up as a script error.
  - there is no bubbling between targets; `event.target` and `currentTarget` are the target itself.

Example:

```ts
class Counter extends EventTarget {
  #value = 0
  increment() {
    this.#value += 1
    this.dispatchEvent(new CustomEvent('change', { detail: this.#value }))
  }
}
const counter = new Counter()
const stop = new AbortController()
counter.addEventListener('change', (event) => {
  if (event instanceof CustomEvent) console.log('now', event.detail)
}, { signal: stop.signal })
counter.increment()
stop.abort()
```

### class Event

```ts
declare class Event {
  constructor(type: string, eventInitDict?: EventInit)
  readonly type: string
  readonly target: EventTarget | null
  readonly srcElement: EventTarget | null
  readonly currentTarget: EventTarget | null
  readonly eventPhase: number
  readonly bubbles: boolean
  readonly cancelable: boolean
  readonly composed: boolean
  readonly defaultPrevented: boolean
  readonly isTrusted: boolean
  readonly timeStamp: number
  returnValue: boolean
  cancelBubble: boolean
  composedPath(): EventTarget[]
  preventDefault(): void
  stopPropagation(): void
  stopImmediatePropagation(): void
  initEvent(type: string, bubbles?: boolean, cancelable?: boolean): void
}

interface EventInit {
  bubbles?: boolean
  cancelable?: boolean
  composed?: boolean
}
```

an event passed to `EventTarget` listeners.

- **grant:** none.
- **parameters:**
  - `type`: the event name listeners subscribe to.
  - `eventInitDict.cancelable`: lets `preventDefault()` set `defaultPrevented`.
  - `target` / `currentTarget`: the target it was dispatched on (`currentTarget` is `null` again after the dispatch).
  - `timeStamp`: `performance.now()` when the event was created.
  - `isTrusted`: `true` only for events tele fires itself (like `abort` on a signal).
  - `stopImmediatePropagation()`: skips the remaining listeners.
- **notes:**
  - extend it for your own event types (`class ProgressEvent extends Event`); the constructor reads `bubbles`, `cancelable` and `composed` from the init.
  - `bubbles`, `composed` and the phase constants exist for compatibility; without a tree nothing bubbles.

Example:

```ts
const event = new Event('save', { cancelable: true })
if (!editor.dispatchEvent(event)) console.log('a listener cancelled the save')
```

### class CustomEvent

```ts
declare class CustomEvent<T = any> extends Event {
  constructor(type: string, eventInitDict?: CustomEventInit<T>)
  readonly detail: T
}

interface CustomEventInit<T = any> extends EventInit {
  detail?: T
}
```

an `Event` with a payload.

- **grant:** none.
- **parameters:**
  - `eventInitDict.detail`: any value; listeners read it as `event.detail`.
- **returns:** `detail` is `null` when not given.

Example:

```ts
target.dispatchEvent(new CustomEvent('progress', { detail: { done: 3, total: 10 } }))
```

### class DOMException

```ts
declare class DOMException extends Error {
  constructor(message?: string, name?: string)
  readonly name: string
  readonly message: string
  readonly code: number
  static readonly ABORT_ERR: 20
  static readonly TIMEOUT_ERR: 23
  static readonly DATA_CLONE_ERR: 25
  // and the other legacy constants, INDEX_SIZE_ERR (1) to DATA_CLONE_ERR (25)
}
```

the error type of web APIs, identified by `name`.

- **grant:** none.
- **parameters:**
  - `message` (`string`, optional): the text; default `''`.
  - `name` (`string`, optional): the kind; default `'Error'`.
  - `code`: the legacy number for known names (`SyntaxError` 12, `NotFoundError` 8, `AbortError` 20, `TimeoutError` 23, `DataCloneError` 25, ...), `0` for other names.
- **notes:**
  - built into QuickJS; `instanceof Error` is true and `stack` is set.
  - names you'll meet: `AbortError` (an aborted `AbortController`), `TimeoutError` (`AbortSignal.timeout`), `DataCloneError` (`structuredClone`), `InvalidCharacterError` (`atob`), `InvalidStateError` (dispatching an event twice).
  - check `error.name`, not `code`.

Example:

```ts
try {
  await fetch(url, { signal: AbortSignal.timeout(5000) })
} catch (error) {
  if (error instanceof DOMException && error.name === 'TimeoutError') console.warn('too slow')
  else throw error
}
```

### class AbortController

```ts
declare class AbortController {
  constructor()
  readonly signal: AbortSignal
  abort(reason?: unknown): void
}
```

makes an `AbortSignal` and aborts it when you call `abort`.

- **grant:** none.
- **parameters:**
  - `abort(reason?)`: aborts `signal` with `reason`; without one, a `DOMException` named `AbortError` (`signal is aborted without reason`). later calls do nothing.
- **notes:**
  - hand `signal` to `fetch`, `addEventListener` or your own code; one controller can cancel many things.

Example:

```ts
const controller = new AbortController()
tg.onUnload(() => controller.abort())
const response = await fetch('https://api.example.com/stream', { signal: controller.signal })
```

### class AbortSignal

```ts
declare class AbortSignal extends EventTarget {
  private constructor()
  readonly aborted: boolean
  readonly reason: unknown
  onabort: ((this: AbortSignal, event: Event) => unknown) | null
  throwIfAborted(): void
  static abort(reason?: unknown): AbortSignal
  static timeout(milliseconds: number): AbortSignal
  static any(signals: Iterable<AbortSignal>): AbortSignal
}

interface AbortSignalEventMap {
  abort: Event
}
```

tells long-running work that it should stop.

- **grant:** none.
- **parameters:**
  - `aborted` / `reason`: whether it was aborted, and with what (`undefined` before).
  - `throwIfAborted()`: throws `reason` when aborted; handy between steps of a loop.
  - `onabort` and `addEventListener('abort', ...)`: called once, when it aborts (`onabort` first if it was set first).
  - `AbortSignal.abort(reason?)`: a signal that is already aborted.
  - `AbortSignal.timeout(ms)`: a signal that aborts after `ms` milliseconds with a `DOMException` named `TimeoutError`.
  - `AbortSignal.any(signals)`: a signal that aborts as soon as any of `signals` does, with that signal's reason (at once if one already is).
- **throws:** `TypeError` from `new AbortSignal()` (use a controller or the static methods); `TypeError` from `timeout` for a negative or non-finite delay; `TypeError` from `any` for anything that isn't a signal.
- **notes:**
  - `fetch(url, { signal })` rejects with `signal.reason` the moment it aborts and cancels the request; a signal that is already aborted rejects before any request (no grant check either).
  - `timeout` runs on a script timer, so it stops with the script like every timer.
  - a signal from `any` stays linked to its sources until it aborts; avoid making endless `any` signals over a long-lived source that never aborts.

Example:

```ts
const stop = new AbortController()
tg.onUnload(() => stop.abort())
const signal = AbortSignal.any([stop.signal, AbortSignal.timeout(10_000)])
for (const id of ids) {
  signal.throwIfAborted()
  await fetch(`https://api.example.com/items/${id}`, { signal })
}
```

### structuredClone(value, options?)

```ts
type Transferable = ArrayBuffer

interface StructuredSerializeOptions {
  transfer?: Transferable[]
}

declare function structuredClone<T = any>(value: T, options?: StructuredSerializeOptions): T
```

deep-copies a value with the browser's structured clone rules.

- **grant:** none.
- **parameters:**
  - `value`: primitives (including `bigint`, `undefined`, `-0`, `NaN`), plain objects, arrays (holes stay holes), `Date`, `RegExp` (source and flags), `Map`, `Set`, `ArrayBuffer` (resizable too), every typed array, `DataView`, `Error` and its built-in subclasses, `DOMException`, and `Boolean`/`Number`/`String`/`BigInt` wrapper objects.
  - `options.transfer`: `ArrayBuffer`s to move instead of copy: the copy gets the bytes, the originals become detached (length 0).
- **returns:** the copy. cycles and shared references are kept: an object reached twice is copied once.
- **throws:** a `DOMException` named `DataCloneError` for functions, symbols, `WeakMap`, `WeakSet`, `WeakRef`, `FinalizationRegistry`, `Promise`, generators, `SharedArrayBuffer`, out-of-bounds `DataView`s and web objects like `URL`, `EventTarget` and `AbortController`; for a transfer list with something other than an `ArrayBuffer`, a duplicate, or a detached buffer.
- **notes:**
  - objects copy only their own enumerable string keys; getters are read once and become plain values. class instances come back as plain objects (no prototype, no methods), like in browsers.
  - errors keep `name` (unknown names become `Error`), `message`, `stack` and a cloned `cause`.
  - views over a resizable buffer come back with a fixed length.
  - `tg.storage` keeps its own, smaller set of types.

Example:

```ts
const saved = { filters: [{ word: 'ad' }], updated: new Date() }
const draft = structuredClone(saved)
draft.filters.push({ word: 'spam' })
console.log(saved.filters.length, draft.filters.length, draft.updated instanceof Date) // 1 2 true
```

### reportError(error)

```ts
declare function reportError(error: unknown): void
```

reports an error the way an uncaught exception would be, without stopping the current code.

- **grant:** none.
- **parameters:**
  - `error` (`unknown`): anything; usually an `Error`.
- **notes:**
  - the error is thrown from a microtask, so it lands in the script log and counts as a script error.
  - `EventTarget` uses it for exceptions in listeners.

Example:

```ts
for (const job of jobs) {
  try {
    await job()
  } catch (error) {
    reportError(error)
  }
}
```

### new WebSocket(url, protocols?)

```ts
declare class WebSocket extends EventTarget {
  constructor(url: string | URL, protocols?: string | string[])
  static readonly CONNECTING: 0
  static readonly OPEN: 1
  static readonly CLOSING: 2
  static readonly CLOSED: 3
  readonly url: string
  readonly protocol: string
  readonly extensions: string
  readonly readyState: number
  readonly bufferedAmount: number
  binaryType: WebSocketBinaryType
  onopen: ((this: WebSocket, event: Event) => unknown) | null
  onmessage: ((this: WebSocket, event: MessageEvent<string | ArrayBuffer>) => unknown) | null
  onerror: ((this: WebSocket, event: Event) => unknown) | null
  onclose: ((this: WebSocket, event: CloseEvent) => unknown) | null
  send(data: string | ArrayBuffer | ArrayBufferView): void
  close(code?: number, reason?: string): void
}

type WebSocketBinaryType = 'arraybuffer'
```

opens a websocket connection (RFC 6455) with the browser's `WebSocket` shape: connect, then `send` and listen for `message`.

- **grant:** `fetch(<host>)` (or a parent domain, or bare `fetch`): the same grant as `fetch`.
- **parameters:**
  - `url` (`string | URL`): an absolute `ws://` or `wss://` url; `http://` and `https://` are turned into `ws://` and `wss://`. No fragment (`#...`).
  - `protocols` (`string | string[]`, optional): subprotocols offered in `Sec-WebSocket-Protocol`, each an http token, no duplicates.
- **returns:** the socket, `readyState` `CONNECTING`; `open` fires once the handshake is done.
- **throws:** `DOMException` `SyntaxError` for a bad url, another scheme, a fragment or a bad / repeated subprotocol; `TeleError` `not-granted` (`WebSocket needs the grant 'fetch(<host>)'`); `TeleError` `unsupported` for `wss://` when tele has no TLS.
- **notes:**
  - members: `url` (the parsed url), `protocol` (the subprotocol the server chose, `''` until `open` and when it chose none), `extensions` (always `''`: no extensions are negotiated), `readyState` (`CONNECTING` 0, `OPEN` 1, `CLOSING` 2, `CLOSED` 3, also on instances), `bufferedAmount` (bytes queued in tele and not written to the network yet, plus whatever `send` dropped after `close`).
  - `binaryType` is always `'arraybuffer'`: binary messages arrive as `ArrayBuffer` (wrap it in `new Uint8Array(data)`). Setting `'blob'` throws `DOMException` `NotSupportedError` (there is no `Blob`); other values are ignored like in browsers.
  - goes through tele's network stack: the same proxy as `fetch`, the system's certificate authorities for `wss://`. No `Origin` header and no cookies are sent.
  - a server that ignores the offered subprotocols is accepted (`protocol` stays `''`); one that picks a subprotocol that wasn't offered, or any extension, fails the connection. Redirects are failures.
  - the handshake has 30 seconds; after that the socket fails (`error`, then `close` 1006).
  - stopping or reloading the script closes every socket it opened with 1001 (going away); its handlers never run again.
  - a socket that is never closed stays open (and its handlers alive) until the script stops.

Example:

```ts
const socket = new WebSocket('wss://echo.websocket.org/')
socket.onopen = () => socket.send(JSON.stringify({ hello: 'tele' }))
socket.onmessage = (event) => {
  if (typeof event.data === 'string') console.log('text', event.data)
  else console.log('bytes', new Uint8Array(event.data).length)
}
socket.onclose = (event) => console.log('closed', event.code, event.reason)
```

### websocket.send(data)

```ts
send(data: string | ArrayBuffer | ArrayBufferView): void
```

sends one message: a string as a text frame (UTF-8), bytes as a binary frame.

- **grant:** none (the socket's grant was checked when it was made).
- **parameters:**
  - `data` (`string | ArrayBuffer | ArrayBufferView`): text, or the bytes of an `ArrayBuffer` or of a typed array / `DataView` window (only `byteOffset` to `byteOffset + byteLength`). Anything else is sent as `String(data)`; lone surrogates become U+FFFD.
- **returns:** nothing; the message is queued and written in the background (`bufferedAmount` shows what's still queued).
- **throws:** `DOMException` `InvalidStateError` while `CONNECTING`; `RangeError: WebSocket: a message is over 64 MB`.
- **notes:**
  - after `close()` (or once the socket closed) `send` throws nothing and drops the message, adding its size to `bufferedAmount`, like browsers.
  - every message is one frame, masked as RFC 6455 requires from clients.

Example:

```ts
socket.send('ping')
socket.send(new Uint8Array([1, 2, 3]))
```

### websocket.close(code?, reason?)

```ts
close(code?: number, reason?: string): void
```

starts the closing handshake; `close` fires when the server answers.

- **grant:** none.
- **parameters:**
  - `code` (`number`, optional): 1000 or 3000 to 4999. Without it the close frame carries no code (the server usually answers 1005), or 1000 when a `reason` is given.
  - `reason` (`string`, optional): at most 123 bytes of UTF-8.
- **returns:** nothing; `readyState` becomes `CLOSING` right away.
- **throws:** `DOMException` `InvalidAccessError` for any other code; `DOMException` `SyntaxError` for a reason over 123 bytes.
- **notes:**
  - while `CONNECTING` it gives up on the connection: `error`, then `close` with 1006.
  - on `CLOSING` / `CLOSED` sockets it does nothing.
  - a server that doesn't answer within 5 seconds gets cut off: `close` with 1006, `wasClean` false.

Example:

```ts
socket.close(4000, 'done')
```

### websocket events

```ts
interface WebSocketEventMap {
  open: Event
  message: MessageEvent<string | ArrayBuffer>
  error: Event
  close: CloseEvent
}
```

what a socket fires, through `addEventListener(type, listener)` or the `on<type>` properties.

- **grant:** none.
- **parameters:**
  - `open` (`Event`): the handshake is done, `readyState` is `OPEN`, `protocol` is set.
  - `message` (`MessageEvent<string | ArrayBuffer>`): a whole message: `data` is a `string` for text, an `ArrayBuffer` for binary; `origin` is the socket's origin (`wss://host`). Fragmented messages are joined first; only fired while `OPEN`.
  - `error` (`Event`): the connection failed (refused, TLS, a bad handshake, a protocol error from the server, a timeout). `readyState` is already `CLOSED`; `close` follows right after.
  - `close` (`CloseEvent`): the socket is `CLOSED`. `code` and `reason` are what the server sent (1005 if its close frame had no code), `wasClean` is true when both sides exchanged close frames.
- **notes:**
  - `onopen`, `onmessage`, `onerror`, `onclose` hold one handler each (`null` removes it); `addEventListener` adds any number, with `once` and `signal`.
  - a dropped connection without a close frame closes with 1006, `wasClean` false, without `error`.
  - differences from browsers: when the connection fails, `close`'s `reason` carries tele's description (`Connection refused`, `the server refused the upgrade: HTTP/1.1 404 Not Found`...) instead of `''`. When the server breaks the protocol tele sends the matching close code and reports it in `close`: 1002 (bad frames), 1007 (text that isn't UTF-8), 1009 (a message over 64 MB).
  - server pings are answered with pongs automatically; they aren't events.

Example:

```ts
socket.addEventListener('message', (event) => {
  const data = typeof event.data === 'string' ? JSON.parse(event.data) : new Uint8Array(event.data)
  console.log(data)
})
socket.addEventListener('close', (event) => {
  if (!event.wasClean) console.warn('lost the connection:', event.code, event.reason)
}, { once: true })
```

### class MessageEvent

```ts
declare class MessageEvent<T = unknown> extends Event {
  constructor(type: string, init?: MessageEventInit<T>)
  readonly data: T
  readonly origin: string
  readonly lastEventId: string
  readonly source: null
  readonly ports: readonly unknown[]
}

interface MessageEventInit<T = unknown> extends EventInit {
  data?: T
  origin?: string
  lastEventId?: string
  source?: null
  ports?: unknown[]
}
```

the event for a message: a `WebSocket` message, and anything else in tele that delivers messages to listeners.

- **grant:** none.
- **parameters:**
  - `data` (`T`): the message; `null` when not given.
  - `origin` (`string`): where it came from; `''` when not given.
  - `lastEventId` (`string`), `source` (`null`), `ports` (frozen, empty): kept for the web shape.
- **throws:** `TypeError` without a `type` or with an `init` that isn't an object.

Example:

```ts
const target = new EventTarget()
target.addEventListener('message', (event) => console.log((event as MessageEvent<string>).data))
target.dispatchEvent(new MessageEvent('message', { data: 'hi' }))
```

### class CloseEvent

```ts
declare class CloseEvent extends Event {
  constructor(type: string, init?: CloseEventInit)
  readonly code: number
  readonly reason: string
  readonly wasClean: boolean
}

interface CloseEventInit extends EventInit {
  code?: number
  reason?: string
  wasClean?: boolean
}
```

the event a `WebSocket` fires when it is closed.

- **grant:** none.
- **parameters:**
  - `code` (`number`): the close code (0 when not given). From a socket: the server's code, 1005 for none, 1006 when the connection was lost or failed, 1002 / 1007 / 1009 when tele closed it for a protocol error.
  - `reason` (`string`): the server's reason, or tele's description of a failure; `''` when not given.
  - `wasClean` (`boolean`): whether the closing handshake finished.
- **throws:** `TypeError` without a `type` or with an `init` that isn't an object.

Example:

```ts
socket.onclose = ({ code, reason, wasClean }) => console.log(code, reason, wasClean)
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

### crypto.subtle

```ts
type HashName = 'SHA-1' | 'SHA-256' | 'SHA-384' | 'SHA-512'
type HashAlgorithm = HashName | { name: HashName }
type BufferSource = ArrayBuffer | ArrayBufferView
type KeyUsage = 'encrypt' | 'decrypt' | 'sign' | 'verify' | 'deriveKey' | 'deriveBits' | 'wrapKey' | 'unwrapKey'
type KeyFormat = 'raw' | 'spki' | 'pkcs8' | 'jwk'
type KeyType = 'public' | 'private' | 'secret'
type NamedCurve = 'P-256' | 'P-384' | 'P-521'
type AesName = 'AES-GCM' | 'AES-CBC' | 'AES-CTR' | 'AES-KW'
type RsaName = 'RSA-OAEP' | 'RSASSA-PKCS1-v1_5' | 'RSA-PSS'

interface AesGcmParams {
  name: 'AES-GCM'
  iv: BufferSource
  additionalData?: BufferSource
  tagLength?: 32 | 64 | 96 | 104 | 112 | 120 | 128
}

interface AesCbcParams {
  name: 'AES-CBC'
  iv: BufferSource
}

interface AesCtrParams {
  name: 'AES-CTR'
  counter: BufferSource
  length: number
}

interface RsaOaepParams {
  name: 'RSA-OAEP'
  label?: BufferSource
}

interface EcdsaParams {
  name: 'ECDSA'
  hash: HashAlgorithm
}

interface RsaPssParams {
  name: 'RSA-PSS'
  saltLength: number
}

interface Pbkdf2Params {
  name: 'PBKDF2'
  salt: BufferSource
  iterations: number
  hash: HashAlgorithm
}

interface HkdfParams {
  name: 'HKDF'
  salt: BufferSource
  info: BufferSource
  hash: HashAlgorithm
}

interface EcdhKeyDeriveParams {
  name: 'ECDH' | 'X25519'
  public: CryptoKey
}

interface AesKeyGenParams {
  name: AesName
  length: 128 | 192 | 256
}

interface HmacKeyGenParams {
  name: 'HMAC'
  hash: HashAlgorithm
  length?: number
}

interface EcKeyGenParams {
  name: 'ECDSA' | 'ECDH'
  namedCurve: NamedCurve
}

interface RsaHashedKeyGenParams {
  name: RsaName
  modulusLength: number
  publicExponent: Uint8Array
  hash: HashAlgorithm
}

interface RsaHashedImportParams {
  name: RsaName
  hash: HashAlgorithm
}

type CipherAlgorithm = AesGcmParams | AesCbcParams | AesCtrParams | RsaOaepParams | 'RSA-OAEP'
type WrapAlgorithm = CipherAlgorithm | 'AES-KW' | { name: 'AES-KW' }

type SignAlgorithm =
  | 'HMAC' | 'Ed25519' | 'RSASSA-PKCS1-v1_5'
  | { name: 'HMAC' | 'Ed25519' | 'RSASSA-PKCS1-v1_5' }
  | EcdsaParams
  | RsaPssParams

type DeriveAlgorithm = Pbkdf2Params | HkdfParams | EcdhKeyDeriveParams
type PairAlgorithm = EcKeyGenParams | RsaHashedKeyGenParams | 'Ed25519' | 'X25519' | { name: 'Ed25519' | 'X25519' }
type SecretAlgorithm = AesKeyGenParams | HmacKeyGenParams

type ImportAlgorithm =
  | AesName | 'PBKDF2' | 'HKDF' | 'Ed25519' | 'X25519'
  | { name: AesName | 'PBKDF2' | 'HKDF' | 'Ed25519' | 'X25519' }
  | HmacKeyGenParams
  | EcKeyGenParams
  | RsaHashedImportParams

type DerivedKeyAlgorithm = AesKeyGenParams | HmacKeyGenParams | 'HKDF' | 'PBKDF2' | { name: 'HKDF' | 'PBKDF2' }

declare class SubtleCrypto {
  private constructor()
  // the methods below
}

interface Crypto {
  getRandomValues<T extends ArrayBufferView>(array: T): T
  randomUUID(): string
  readonly subtle: SubtleCrypto
}

declare var crypto: Crypto
```

the WebCrypto api of browsers, with the same names, shapes and errors, so libraries written for `crypto.subtle` (jose, age, signal-style ratchets, PGP helpers) work unchanged. hashing, HMAC, AES, ECDH/X25519, ECDSA/Ed25519, RSA, PBKDF2 and HKDF all run on OpenSSL inside tele, off the UI thread.

| algorithm | operations | key formats | generateKey / import parameters | operation parameters |
| --- | --- | --- | --- | --- |
| `AES-GCM` | encrypt, decrypt, wrapKey, unwrapKey | raw, jwk (`A128GCM`...) | `{ length: 128 \| 192 \| 256 }` | `AesGcmParams` |
| `AES-CBC` | encrypt, decrypt, wrapKey, unwrapKey | raw, jwk (`A128CBC`...) | `{ length }` | `AesCbcParams` (16-byte iv, PKCS#7 padding) |
| `AES-CTR` | encrypt, decrypt, wrapKey, unwrapKey | raw, jwk (`A128CTR`...) | `{ length }` | `AesCtrParams` (16-byte counter block, `length` counter bits 1-128) |
| `AES-KW` | wrapKey, unwrapKey | raw, jwk (`A128KW`...) | `{ length }` | none (RFC 3394) |
| `HMAC` | sign, verify | raw, jwk (`HS256`...) | `{ hash, length? }` (default: the hash's block size) | none, the hash comes from the key |
| `PBKDF2` | deriveBits, deriveKey | raw (import only, never extractable) | none | `Pbkdf2Params` |
| `HKDF` | deriveBits, deriveKey | raw (import only, never extractable) | none | `HkdfParams` |
| `ECDH` | deriveBits, deriveKey | raw (public point), spki, pkcs8, jwk | `{ namedCurve }` | `EcdhKeyDeriveParams` |
| `X25519` | deriveBits, deriveKey | raw (public), spki, pkcs8, jwk | none | `EcdhKeyDeriveParams` |
| `ECDSA` | sign, verify | raw (public point), spki, pkcs8, jwk | `{ namedCurve }` | `EcdsaParams` (signatures are r‖s, IEEE P1363, like browsers) |
| `Ed25519` | sign, verify | raw (public), spki, pkcs8, jwk | none | none |
| `RSASSA-PKCS1-v1_5` | sign, verify | spki, pkcs8, jwk (`RS256`...) | `RsaHashedKeyGenParams` / `{ hash }` | none |
| `RSA-PSS` | sign, verify | spki, pkcs8, jwk (`PS256`...) | `RsaHashedKeyGenParams` / `{ hash }` | `RsaPssParams` |
| `RSA-OAEP` | encrypt, decrypt, wrapKey, unwrapKey | spki, pkcs8, jwk (`RSA-OAEP-256`...) | `RsaHashedKeyGenParams` / `{ hash }` | `RsaOaepParams` |

- **grant:** none.
- **parameters:**
  - algorithms are a name or `{ name, ...parameters }`; names are case-insensitive. hashes are `SHA-1`, `SHA-256`, `SHA-384`, `SHA-512`.
  - `BufferSource` is any `ArrayBuffer`, typed array or `DataView`; the bytes are copied when the call starts.
- **returns:** every method returns a promise; bytes come back as `ArrayBuffer`.
- **throws:** every method rejects instead of throwing, with a `DOMException` named like in browsers:
  - `NotSupportedError`: an unknown algorithm, or one that can't do this operation (`encrypt` with `HMAC`), or a format the algorithm doesn't have (`raw` RSA keys).
  - `InvalidAccessError`: the key belongs to another algorithm, its `usages` don't allow the operation, it isn't extractable, or it's the wrong half of a pair.
  - `DataError`: key data that doesn't parse or doesn't match the algorithm (a 15-byte AES key, a P-384 spki imported as P-256, a jwk with the wrong `kty`/`crv`/`alg`/`use`/`key_ops`).
  - `OperationError`: the operation itself failed (a wrong AES-GCM tag or RSA-OAEP label, a bad iv, an AES-CTR counter that would repeat, a length the algorithm can't produce).
  - `SyntaxError`: usages that don't fit the key (`['encrypt']` for HMAC) or an empty list for secret and private keys.
  - `TypeError`: wrong argument types, an unknown hash (`TypeError: the hash is SHA-1, SHA-256, SHA-384 or SHA-512`) or something that isn't a `CryptoKey`.
- **notes:**
  - key material stays inside tele's native code; a script only holds `CryptoKey` objects. keys are freed when the script drops them or stops.
  - `getRandomValues` and `randomUUID` are the items above; workers keep the smaller `crypto.subtle` with only `digest`, HMAC `importKey`/`sign`/`verify`.
  - not there: `RSA-PSS`/`RSA-OAEP` keys with the special `id-RSASSA-PSS` spki type, compressed points on export, X448/Ed448, `AES-KW` around jwk keys whose JSON isn't a multiple of 8 bytes (same as browsers).

Example:

```ts
const key = await crypto.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt', 'decrypt'])
const iv = crypto.getRandomValues(new Uint8Array(12))
const sealed = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, new TextEncoder().encode('secret note'))
const opened = new TextDecoder().decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, sealed))
```

### crypto.subtle.digest(algorithm, data)

```ts
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

### crypto.subtle.generateKey(algorithm, extractable, usages)

```ts
generateKey(algorithm: PairAlgorithm, extractable: boolean, usages: readonly KeyUsage[]): Promise<CryptoKeyPair>
generateKey(algorithm: SecretAlgorithm, extractable: boolean, usages: readonly KeyUsage[]): Promise<CryptoKey>
```

makes a new random secret key, or a key pair.

- **grant:** none.
- **parameters:**
  - `algorithm`: AES (`length` 128, 192 or 256), HMAC (`hash`, optional `length` in bits, a multiple of 8; default 512 for SHA-1/SHA-256 and 1024 for SHA-384/SHA-512), ECDSA/ECDH (`namedCurve`), Ed25519, X25519, or RSA (`modulusLength` from 1024 to 16384 in steps of 8, `publicExponent` `[1, 0, 1]` or `[3]`, `hash`).
  - `extractable` (`boolean`): whether `exportKey`/`wrapKey` may read the secret or private key. the public half of a pair is always extractable.
  - `usages` (`KeyUsage[]`): what the key may do; for pairs they're split (`sign` goes to the private key, `verify` to the public one).
- **returns:** `Promise<CryptoKey>` for secret keys, `Promise<CryptoKeyPair>` for asymmetric algorithms.
- **throws:** `OperationError` for a bad length, modulus or exponent; `NotSupportedError` for an unknown curve or `PBKDF2`/`HKDF`; `SyntaxError` for usages that don't fit.
- **notes:**
  - RSA key generation runs on a worker thread; 2048 bits usually takes well under a second, 4096 can take a few.

Example:

```ts
const { publicKey, privateKey } = await crypto.subtle.generateKey({ name: 'ECDSA', namedCurve: 'P-256' }, true, ['sign', 'verify'])
tg.storage.set('identity', { ...(await crypto.subtle.exportKey('jwk', privateKey)) })
```

### crypto.subtle.importKey(format, keyData, algorithm, extractable, usages)

```ts
importKey(
  format: 'jwk',
  keyData: JsonWebKey,
  algorithm: ImportAlgorithm,
  extractable: boolean,
  usages: readonly KeyUsage[],
): Promise<CryptoKey>
importKey(
  format: 'raw' | 'spki' | 'pkcs8',
  keyData: BufferSource,
  algorithm: ImportAlgorithm,
  extractable: boolean,
  usages: readonly KeyUsage[],
): Promise<CryptoKey>

interface JsonWebKey {
  kty?: string
  alg?: string
  use?: string
  key_ops?: string[]
  ext?: boolean
  crv?: string
  x?: string
  y?: string
  d?: string
  n?: string
  e?: string
  p?: string
  q?: string
  dp?: string
  dq?: string
  qi?: string
  k?: string
}
```

turns key bytes or a JSON Web Key into a `CryptoKey`.

- **grant:** none.
- **parameters:**
  - `format`: `'raw'` (secret bytes, an EC public point `04‖x‖y` or compressed, a 32-byte Ed25519/X25519 public key), `'spki'` (DER public key), `'pkcs8'` (DER private key) or `'jwk'`. the table in `crypto.subtle` lists which algorithm takes which.
  - `keyData` (`BufferSource | JsonWebKey`): the key; a jwk is a plain object with base64url fields. its `alg`, `use`, `key_ops` and `ext` are checked like browsers do.
  - `algorithm`: the algorithm the key will be used with. HMAC may give `length` in bits; ECDSA/ECDH need `namedCurve`; RSA needs `hash`.
  - `extractable` (`boolean`): whether it can be exported or wrapped later. PBKDF2 and HKDF keys can't be extractable.
  - `usages` (`KeyUsage[]`): what it may do. ECDH/X25519 public keys take `[]`.
- **returns:** `Promise<CryptoKey>`; its `type` is `secret`, `public` (raw, spki, a jwk without `d`) or `private` (pkcs8, a jwk with `d`).
- **throws:** `DataError` for key data that doesn't parse or doesn't match (wrong size, curve, `kty`, a public half that doesn't fit the private one); `NotSupportedError` for a format the algorithm doesn't have; `SyntaxError` for wrong usages.
- **notes:**
  - EC and Ed25519/X25519 keys are validated (point on the curve, private matching public); an RSA jwk private key needs all of `n e d p q dp dq qi`.

Example:

```ts
const peer = await crypto.subtle.importKey('raw', Uint8Array.fromBase64(theirKey), 'X25519', false, [])
const mine = await crypto.subtle.importKey('jwk', tg.storage.get('x25519') as JsonWebKey, 'X25519', false, ['deriveKey'])
```

### crypto.subtle.exportKey(format, key)

```ts
exportKey(format: 'jwk', key: CryptoKey): Promise<JsonWebKey>
exportKey(format: 'raw' | 'spki' | 'pkcs8', key: CryptoKey): Promise<ArrayBuffer>
```

reads an extractable key back out.

- **grant:** none.
- **parameters:**
  - `format`: `'raw'` for secret keys and public EC/Ed25519/X25519 keys (EC points come out uncompressed), `'spki'` for public keys, `'pkcs8'` for private keys, `'jwk'` for everything.
  - `key` (`CryptoKey`): an extractable key.
- **returns:** `Promise<ArrayBuffer>`, or `Promise<JsonWebKey>` with `kty`, the key fields, `alg` (`A256GCM`, `HS256`, `RS256`, `PS256`, `RSA-OAEP-256`, `Ed25519`...), `key_ops` (the key's usages) and `ext: true`.
- **throws:** `InvalidAccessError` for a non-extractable key or the wrong half (`spki` of a private key); `NotSupportedError` for a format the algorithm doesn't have.

Example:

```ts
const spki = new Uint8Array(await crypto.subtle.exportKey('spki', publicKey))
const pem = `-----BEGIN PUBLIC KEY-----\n${spki.toBase64()}\n-----END PUBLIC KEY-----`
```

### crypto.subtle.encrypt(algorithm, key, data)

```ts
encrypt(algorithm: CipherAlgorithm, key: CryptoKey, data: BufferSource): Promise<ArrayBuffer>
```

encrypts bytes with AES-GCM, AES-CBC, AES-CTR or RSA-OAEP.

- **grant:** none.
- **parameters:**
  - `algorithm`: `AES-GCM` with an `iv` (12 bytes is the norm; never reuse one with the same key), optional `additionalData` and `tagLength` (bits, default 128); `AES-CBC` with a 16-byte `iv`; `AES-CTR` with a 16-byte `counter` block and `length`, the number of its low bits that count; `RSA-OAEP` with an optional `label`.
  - `key` (`CryptoKey`): a key of the same algorithm with the `encrypt` usage (the public key for RSA-OAEP).
  - `data` (`BufferSource`): the plaintext.
- **returns:** `Promise<ArrayBuffer>`: for AES-GCM the ciphertext followed by the tag; for AES-CBC the PKCS#7-padded ciphertext.
- **throws:** `InvalidAccessError` for a key of another algorithm or without `encrypt`; `OperationError` for a bad iv, tag length or counter, a counter that would wrap onto itself, or RSA-OAEP data longer than the key allows.

Example:

```ts
const iv = crypto.getRandomValues(new Uint8Array(12))
const sealed = await crypto.subtle.encrypt({ name: 'AES-GCM', iv, additionalData: new TextEncoder().encode(String(chatId)) }, key, bytes)
```

### crypto.subtle.decrypt(algorithm, key, data)

```ts
decrypt(algorithm: CipherAlgorithm, key: CryptoKey, data: BufferSource): Promise<ArrayBuffer>
```

reverses `encrypt`.

- **grant:** none.
- **parameters:**
  - `algorithm`: the same parameters `encrypt` got.
  - `key` (`CryptoKey`): a key with the `decrypt` usage (the private key for RSA-OAEP).
  - `data` (`BufferSource`): what `encrypt` returned.
- **returns:** `Promise<ArrayBuffer>` with the plaintext.
- **throws:** `OperationError` when the AES-GCM tag, the AES-CBC padding, the RSA-OAEP padding or label doesn't check out; otherwise like `encrypt`.

Example:

```ts
try {
  const text = new TextDecoder().decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv }, key, sealed))
} catch (error) {
  if (error instanceof DOMException && error.name === 'OperationError') console.log('tampered or wrong key')
}
```

### crypto.subtle.sign(algorithm, key, data)

```ts
sign(algorithm: SignAlgorithm, key: CryptoKey, data: BufferSource): Promise<ArrayBuffer>
```

signs bytes with HMAC, ECDSA, Ed25519, RSASSA-PKCS1-v1_5 or RSA-PSS.

- **grant:** none.
- **parameters:**
  - `algorithm`: the algorithm of the key; ECDSA also takes the `hash`, RSA-PSS the `saltLength` in bytes (32 for SHA-256 is usual). HMAC and RSASSA use the key's hash.
  - `key` (`CryptoKey`): a secret HMAC key or a private key, with the `sign` usage.
  - `data` (`BufferSource`): the message.
- **returns:** `Promise<ArrayBuffer>`: the MAC, the raw Ed25519 or RSA signature, or ECDSA `r‖s` (64, 96 or 132 bytes for P-256, P-384, P-521), the same format browsers use.
- **throws:** `InvalidAccessError` for a key of another algorithm or without `sign`; `TypeError` for something that isn't a `CryptoKey`.

Example:

```ts
const signature = await crypto.subtle.sign({ name: 'ECDSA', hash: 'SHA-256' }, privateKey, new TextEncoder().encode(body))
```

### crypto.subtle.verify(algorithm, key, signature, data)

```ts
verify(algorithm: SignAlgorithm, key: CryptoKey, signature: BufferSource, data: BufferSource): Promise<boolean>
```

checks a signature; HMAC is compared in constant time.

- **grant:** none.
- **parameters:**
  - `algorithm`: as for `sign`.
  - `key` (`CryptoKey`): the HMAC key or the public key, with the `verify` usage.
  - `signature` (`BufferSource`): the signature to check.
  - `data` (`BufferSource`): the signed bytes.
- **returns:** `Promise<boolean>`; a malformed signature is just `false`.
- **throws:** like `sign`.

Example:

```ts
const valid = await crypto.subtle.verify('Ed25519', publicKey, Uint8Array.fromBase64(given), new TextEncoder().encode(body))
```

### crypto.subtle.deriveBits(algorithm, baseKey, length?)

```ts
deriveBits(algorithm: DeriveAlgorithm, baseKey: CryptoKey, length?: number | null): Promise<ArrayBuffer>
```

stretches a password (PBKDF2), expands a secret (HKDF) or agrees on a shared secret (ECDH, X25519).

- **grant:** none.
- **parameters:**
  - `algorithm`: `PBKDF2` with `salt`, `iterations` and `hash`; `HKDF` with `salt`, `info` and `hash`; `ECDH`/`X25519` with the other side's `public` key (same algorithm and curve).
  - `baseKey` (`CryptoKey`): an imported PBKDF2/HKDF key or your private ECDH/X25519 key, with `deriveBits`.
  - `length` (`number | null`): bits to derive. PBKDF2 and HKDF need a multiple of 8; ECDH/X25519 take `null` for the whole shared secret or fewer bits to cut it.
- **returns:** `Promise<ArrayBuffer>`.
- **throws:** `OperationError` for zero iterations, a length the algorithm can't give (HKDF above 255 hash lengths, ECDH above the secret); `InvalidAccessError` for a `public` key of another algorithm or curve.
- **notes:**
  - PBKDF2 runs on a worker thread, so 600 000 iterations don't freeze tele.

Example:

```ts
const password = await crypto.subtle.importKey('raw', new TextEncoder().encode(input), 'PBKDF2', false, ['deriveBits'])
const hash = await crypto.subtle.deriveBits({ name: 'PBKDF2', salt, iterations: 600_000, hash: 'SHA-256' }, password, 256)
```

### crypto.subtle.deriveKey(algorithm, baseKey, derivedKeyType, extractable, usages)

```ts
deriveKey(
  algorithm: DeriveAlgorithm,
  baseKey: CryptoKey,
  derivedKeyType: DerivedKeyAlgorithm,
  extractable: boolean,
  usages: readonly KeyUsage[],
): Promise<CryptoKey>
```

`deriveBits` followed by `importKey('raw', ...)`: makes an AES or HMAC key (or an HKDF key from an ECDH secret) directly.

- **grant:** none.
- **parameters:**
  - `algorithm`, `baseKey`: as for `deriveBits`; the base key needs the `deriveKey` usage.
  - `derivedKeyType`: the key to make; AES needs `length`, HMAC derives its hash's block size unless `length` is given, HKDF/PBKDF2 take the whole secret (only after ECDH/X25519).
  - `extractable`, `usages`: for the new key.
- **returns:** `Promise<CryptoKey>`.
- **throws:** like `deriveBits` and `importKey`.

Example:

```ts
const shared = await crypto.subtle.deriveKey({ name: 'X25519', public: peer }, mine, 'HKDF', false, ['deriveKey'])
const chatKey = await crypto.subtle.deriveKey(
  { name: 'HKDF', hash: 'SHA-256', salt: new Uint8Array(32), info: new TextEncoder().encode('tele chat') },
  shared,
  { name: 'AES-GCM', length: 256 },
  false,
  ['encrypt', 'decrypt'],
)
```

### crypto.subtle.wrapKey(format, key, wrappingKey, wrapAlgorithm)

```ts
wrapKey(format: KeyFormat, key: CryptoKey, wrappingKey: CryptoKey, wrapAlgorithm: WrapAlgorithm): Promise<ArrayBuffer>
```

exports a key and encrypts the result in one step, for storing keys under a master key.

- **grant:** none.
- **parameters:**
  - `format` (`KeyFormat`): how `key` is exported first; `jwk` is wrapped as its JSON text.
  - `key` (`CryptoKey`): an extractable key.
  - `wrappingKey` (`CryptoKey`): an AES or RSA-OAEP public key with the `wrapKey` usage.
  - `wrapAlgorithm`: the parameters `encrypt` would take, or `AES-KW` (RFC 3394).
- **returns:** `Promise<ArrayBuffer>` with the wrapped key.
- **throws:** like `exportKey` and `encrypt`; `AES-KW` needs a multiple of 8 bytes (at least 16), so wrap jwk keys with AES-GCM instead.

Example:

```ts
const iv = crypto.getRandomValues(new Uint8Array(12))
const blob = await crypto.subtle.wrapKey('pkcs8', identity, masterKey, { name: 'AES-GCM', iv })
```

### crypto.subtle.unwrapKey(format, wrappedKey, unwrappingKey, unwrapAlgorithm, unwrappedKeyAlgorithm, extractable, usages)

```ts
unwrapKey(
  format: KeyFormat,
  wrappedKey: BufferSource,
  unwrappingKey: CryptoKey,
  unwrapAlgorithm: WrapAlgorithm,
  unwrappedKeyAlgorithm: ImportAlgorithm,
  extractable: boolean,
  usages: readonly KeyUsage[],
): Promise<CryptoKey>
```

decrypts a wrapped key and imports it.

- **grant:** none.
- **parameters:**
  - `format` (`KeyFormat`): the format it was wrapped in.
  - `wrappedKey` (`BufferSource`): what `wrapKey` returned.
  - `unwrappingKey` (`CryptoKey`): the AES key or RSA-OAEP private key, with `unwrapKey`.
  - `unwrapAlgorithm`: the parameters used to wrap.
  - `unwrappedKeyAlgorithm`, `extractable`, `usages`: as for `importKey`.
- **returns:** `Promise<CryptoKey>`.
- **throws:** `OperationError` if the blob was changed or the key is wrong; `DataError` if the result isn't a valid key; otherwise like `importKey`.

Example:

```ts
const identity = await crypto.subtle.unwrapKey('pkcs8', blob, masterKey, { name: 'AES-GCM', iv }, { name: 'ECDSA', namedCurve: 'P-256' }, false, ['sign'])
```

### class CryptoKey

```ts
declare class CryptoKey {
  private constructor()
  readonly type: KeyType
  readonly extractable: boolean
  readonly algorithm: KeyAlgorithm
  readonly usages: readonly KeyUsage[]
}

interface KeyAlgorithm {
  readonly name: string
  readonly length?: number
  readonly hash?: { readonly name: HashName }
  readonly namedCurve?: NamedCurve
  readonly modulusLength?: number
  readonly publicExponent?: Uint8Array
}

interface CryptoKeyPair {
  publicKey: CryptoKey
  privateKey: CryptoKey
}
```

a key made by `generateKey`, `importKey`, `deriveKey` or `unwrapKey`.

- **grant:** none.
- **parameters:**
  - `type`: `secret` for AES/HMAC/PBKDF2/HKDF, `public` or `private` for the halves of a pair.
  - `extractable`: whether `exportKey`/`wrapKey` work on it.
  - `algorithm`: frozen; `name` plus `length` (AES and HMAC, bits), `hash` (HMAC, RSA), `namedCurve` (ECDSA, ECDH), `modulusLength` and `publicExponent` (RSA).
  - `usages`: frozen, in the order `encrypt, decrypt, sign, verify, deriveKey, deriveBits, wrapKey, unwrapKey`.
- **notes:**
  - `new CryptoKey()` throws `TypeError: Illegal constructor`; `instanceof CryptoKey` works.
  - the key material lives in tele's native code and can't be read except through `exportKey`; a key only works in the script that made it.

Example:

```ts
console.log(key.type, key.algorithm.name, key.algorithm.hash?.name, key.usages.join())
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

### compression.gzip(input, options?)

```ts
type CompressionInput = Uint8Array | ArrayBuffer | string

interface CompressionOptions {
  level?: number
}

gzip(input: CompressionInput, options?: CompressionOptions): Promise<Uint8Array>

declare var compression: {
  gzip(input: CompressionInput, options?: CompressionOptions): Promise<Uint8Array>
  gunzip(input: CompressionInput, options?: DecompressionOptions): Promise<Uint8Array>
  deflate(input: CompressionInput, options?: CompressionOptions): Promise<Uint8Array>
  inflate(input: CompressionInput, options?: DecompressionOptions): Promise<Uint8Array>
  deflateRaw(input: CompressionInput, options?: CompressionOptions): Promise<Uint8Array>
  inflateRaw(input: CompressionInput, options?: DecompressionOptions): Promise<Uint8Array>
}
```

compresses bytes into the gzip format (what `.gz` files, `Content-Encoding: gzip` and most web apis use).

- **grant:** none.
- **parameters:**
  - `input` (`CompressionInput`): the bytes; a string is compressed as utf-8.
  - `options.level` (`number`, optional): 0 (no compression) to 9 (smallest, slowest); default zlib's 6.
- **returns:** `Promise<Uint8Array>` with the gzip stream (a 10-byte header without a file name or time, the deflate data, a crc32 and the size).
- **throws:** synchronously `TypeError: compression.gzip needs a Uint8Array, an ArrayBuffer or a string`, `compression.gzip: options is an object`, `compression.gzip: level is an integer from 0 to 9`; rejects with `TeleError` `internal` if zlib itself fails.
- **notes:**
  - the work runs on a background thread, so big inputs don't freeze tele.
  - it's not an `async` function: argument errors throw right away instead of rejecting.

Example:

```ts
const packed = await compression.gzip(JSON.stringify(state), { level: 9 })
tg.storage.set('state', packed.toBase64())
```

### compression.gunzip(input, options?)

```ts
interface DecompressionOptions {
  maxSize?: number
}

gunzip(input: CompressionInput, options?: DecompressionOptions): Promise<Uint8Array>
```

decompresses gzip data.

- **grant:** none.
- **parameters:**
  - `input` (`CompressionInput`): the gzip bytes; a string is taken as its utf-8 bytes.
  - `options.maxSize` (`number`, optional): the most bytes the output may have, 1 to 268435456 (256 MB); default 67108864 (64 MB). protects the script from decompression bombs.
- **returns:** `Promise<Uint8Array>` with the original bytes; turn them into text with `TextDecoder`.
- **throws:**
  - synchronously: `TypeError: compression.gunzip needs a Uint8Array, an ArrayBuffer or a string`, `compression.gunzip: options is an object`, `compression.gunzip: maxSize is an integer from 1 to 268435456`.
  - rejects with `TeleError` `quota-exceeded` (`compression.gunzip: the output is over maxSize (<n> bytes)`): decompression stops as soon as the output passes `maxSize`.
  - rejects with `TeleError` `unsupported` for data that isn't gzip: `compression.gunzip: the data isn't valid gzip (<zlib's reason>)`, `compression.gunzip: the data is truncated`, `compression.gunzip: unexpected bytes after the end of the data`.
- **notes:**
  - several gzip members one after another (concatenated `.gz` files) come out as one result.
  - anything else after the end of the stream, including zero padding, is an error.
  - the output is limited by the script's 256 MB of memory too.

Example:

```ts
const response = await fetch('https://example.com/data.json.gz')
const json = JSON.parse(new TextDecoder().decode(await compression.gunzip(await response.bytes(), { maxSize: 8 << 20 })))
```

### compression.deflate(input, options?)

```ts
deflate(input: CompressionInput, options?: CompressionOptions): Promise<Uint8Array>
```

compresses bytes into the zlib format (rfc 1950: a 2-byte header, deflate data and an adler32), what `Content-Encoding: deflate`, png chunks and many file formats use.

- **grant:** none.
- **parameters:**
  - `input` (`CompressionInput`): the bytes; a string is compressed as utf-8.
  - `options.level` (`number`, optional): 0 to 9; default 6.
- **returns:** `Promise<Uint8Array>` with the zlib stream.
- **throws:** synchronously `TypeError: compression.deflate needs a Uint8Array, an ArrayBuffer or a string`, `compression.deflate: level is an integer from 0 to 9`; rejects with `TeleError` `internal` if zlib fails.

Example:

```ts
const packed = await compression.deflate(new Uint8Array(1000))
console.log(packed.length) // a few bytes
```

### compression.inflate(input, options?)

```ts
inflate(input: CompressionInput, options?: DecompressionOptions): Promise<Uint8Array>
```

decompresses zlib-format data (what `compression.deflate` makes).

- **grant:** none.
- **parameters:**
  - `input` (`CompressionInput`): the zlib bytes.
  - `options.maxSize` (`number`, optional): the output limit, 1 to 268435456; default 64 MB.
- **returns:** `Promise<Uint8Array>` with the original bytes.
- **throws:** synchronously the same `TypeError`s as `compression.gunzip` (with `compression.inflate`); rejects with `TeleError` `quota-exceeded` over `maxSize`, `TeleError` `unsupported` for data that isn't zlib (`the data isn't valid zlib (incorrect header check)` for gzip or raw data), truncated data or bytes after the end.

Example:

```ts
const text = new TextDecoder().decode(await compression.inflate(Uint8Array.fromHex('789ccb48cdc9c90700062c0215')))
```

### compression.deflateRaw(input, options?)

```ts
deflateRaw(input: CompressionInput, options?: CompressionOptions): Promise<Uint8Array>
```

compresses bytes into raw deflate data (rfc 1951) with no header or checksum, what zip entries and some protocols use.

- **grant:** none.
- **parameters:**
  - `input` (`CompressionInput`): the bytes; a string is compressed as utf-8.
  - `options.level` (`number`, optional): 0 to 9; default 6.
- **returns:** `Promise<Uint8Array>` with the deflate data.
- **throws:** synchronously `TypeError: compression.deflateRaw needs a Uint8Array, an ArrayBuffer or a string`, `compression.deflateRaw: level is an integer from 0 to 9`; rejects with `TeleError` `internal` if zlib fails.

Example:

```ts
const entry = await compression.deflateRaw(fileBytes)
```

### compression.inflateRaw(input, options?)

```ts
inflateRaw(input: CompressionInput, options?: DecompressionOptions): Promise<Uint8Array>
```

decompresses raw deflate data (what `compression.deflateRaw` makes, or a zip entry's data).

- **grant:** none.
- **parameters:**
  - `input` (`CompressionInput`): the deflate bytes.
  - `options.maxSize` (`number`, optional): the output limit, 1 to 268435456; default 64 MB.
- **returns:** `Promise<Uint8Array>` with the original bytes.
- **throws:** synchronously the same `TypeError`s as `compression.gunzip` (with `compression.inflateRaw`); rejects with `TeleError` `quota-exceeded` over `maxSize`, `TeleError` `unsupported` for invalid or truncated data or bytes after the end.
- **notes:**
  - raw deflate has no checksum, so some corruptions decode into wrong bytes instead of failing.

Example:

```ts
const original = await compression.inflateRaw(entry, { maxSize: 1 << 20 })
```

### Intl

```ts
declare namespace Intl {
  function getCanonicalLocales(locales?: string | readonly string[]): string[]
  function supportedValuesOf(key: 'calendar' | 'collation' | 'currency' | 'numberingSystem' | 'timeZone' | 'unit'): string[]
  // NumberFormat, DateTimeFormat, RelativeTimeFormat, PluralRules, Collator, ListFormat, Locale
}
```

the ECMA-402 internationalization api. QuickJS has none, so tele builds it from Qt's locale data (`QLocale`, `QCollator`) plus its own CLDR tables. the shapes are the standard ones (typings come from TypeScript's own `lib`), so most `Intl` code and libraries work unchanged; the output is close to a browser but not byte-identical.

- **grant:** none.
- **parameters:**
  - `locales` (every constructor, `getCanonicalLocales`, `supportedLocalesOf`): a BCP 47 tag (`'ru'`, `'en-US'`, `'zh-Hant-TW'`, `'de-u-nu-latn'`), an `Intl.Locale`, an array of them, or `undefined` for the default. the first tag whose language Qt knows wins.
  - `getCanonicalLocales(locales)`: the tags fixed up (`'EN-us'` becomes `'en-US'`), duplicates dropped.
  - `supportedValuesOf(key)`: what this implementation knows for `key`; `timeZone` is just the local zone and `'UTC'`.
  - `<Constructor>.supportedLocalesOf(locales, options?)`: the tags whose language Qt has data for.
- **returns:** see each class.
- **throws:** `RangeError: Incorrect locale information provided` for malformed tags (`'en_US'`), `RangeError` for option values out of range, `TypeError` for options that contradict each other, like a browser.
- **notes:**
  - the default locale is tele's interface language (Settings > Language), with the region taken from the system locale when the languages match (english interface on an `en-GB` system gives `en-GB`, otherwise `en-US`); a custom language pack falls back to the system locale.
  - numbers, currency symbols, month and day names, date and time patterns, separators and the digits (Arabic, Persian…) come from Qt for every language Qt knows (hundreds). Qt's CLDR data is older than a browser's, so some patterns differ (for example `de` dates are `05.03.2024` where Chrome says `5.3.2024`, `ja` long times use `時分秒`).
  - tele's own tables (plural rules, list patterns, relative time words, compact suffixes) cover `en`, `ru`, `uk`, `be`, `de`, `fr`, `es`, `it`, `pt`, `pl`, `cs`, `tr`, `ar`, `ja`, `zh`, `ko`, `fa`, `id`, `nl`, `sv`; other languages fall back to English rules for those pieces.
  - not there: `Intl.Segmenter`, `Intl.DisplayNames`, `Intl.DurationFormat`, calendars other than gregorian, time zones other than `'UTC'`, the computer's own zone and fixed offsets like `'+03:00'`.
  - `Number.prototype.toLocaleString`, `BigInt.prototype.toLocaleString`, `Date.prototype.toLocaleString` / `toLocaleDateString` / `toLocaleTimeString` and `String.prototype.localeCompare` go through these classes, so they take the same `locales` and `options`.

Example:

```ts
console.log((1234567.891).toLocaleString('ru-RU')) // 1 234 567,891
console.log(new Date().toLocaleDateString(undefined, { dateStyle: 'long' })) // in tele's language
console.log(Intl.DateTimeFormat().resolvedOptions().timeZone) // 'Europe/Moscow'
```

### class Intl.NumberFormat

```ts
declare class Intl.NumberFormat {
  constructor(locales?: string | string[], options?: Intl.NumberFormatOptions)
  format(value: number | bigint | string): string
  formatToParts(value: number | bigint | string): Intl.NumberFormatPart[]
  formatRange(start: number | bigint | string, end: number | bigint | string): string
  formatRangeToParts(start: number | bigint | string, end: number | bigint | string): Intl.NumberRangeFormatPart[]
  resolvedOptions(): Intl.ResolvedNumberFormatOptions
  static supportedLocalesOf(locales: string | string[], options?: { localeMatcher?: string }): string[]
}
```

formats numbers, percentages, money and units with the locale's separators, grouping and digits.

- **grant:** none.
- **parameters:**
  - `style`: `'decimal'` (default), `'percent'` (multiplies by 100), `'currency'` (needs `currency`, an ISO code like `'USD'`), `'unit'` (needs `unit`, like `'kilobyte'` or `'kilometer-per-hour'`).
  - `currencyDisplay`: `'symbol'` (default), `'narrowSymbol'`, `'code'`, `'name'`; `currencySign: 'accounting'` uses parentheses where the locale does.
  - `minimumIntegerDigits`, `minimumFractionDigits`, `maximumFractionDigits`, `minimumSignificantDigits`, `maximumSignificantDigits`, `roundingPriority`, `roundingIncrement`, `roundingMode` (all nine), `trailingZeroDisplay`: the standard rounding options with the standard defaults (0 to 3 fraction digits, the currency's minor units for money, 0 for percent).
  - `useGrouping`: `'auto'` (default), `'always'`, `'min2'`, `true`, `false`.
  - `notation`: `'standard'`, `'scientific'`, `'engineering'`, `'compact'` with `compactDisplay: 'short' | 'long'` (`1.2K`, `1.2 million`, `1,2 тыс.`, `5 тысяч`, `1.2万`).
  - `signDisplay`: `'auto'`, `'never'`, `'always'`, `'exceptZero'`, `'negative'`.
  - `numberingSystem` or `-u-nu-` in the tag: `'latn'` or another digit set (`'arab'`, `'arabext'`, `'deva'`…).
- **returns:** `format` gives the string (it's a bound getter, so `list.map(format.format)` works); `formatToParts` the typed pieces (`integer`, `group`, `decimal`, `fraction`, `currency`, `percentSign`, `minusSign`, `compact`, `unit`, `exponent…`); `resolvedOptions` what was actually used.
- **throws:** `TypeError: Currency code is required with currency style.`, `RangeError: Invalid currency code : <code>`, `RangeError` for digit options out of range.
- **notes:**
  - rounding works on the exact decimal value, so `1.005` with two digits is `1.01` like in a browser; bigints and numeric strings (`'1234.5678901234567890'`) are formatted exactly.
  - partial: compact suffixes exist for the 20 languages above (others use English `K`/`M`/`B`/`T`); currency names (`'name'`) are Qt's singular names (`1.00 US Dollar`, not `US dollars`); `unit` uses English symbols and long names, Russian ones for `ru`, metric symbols elsewhere; `NaN` is spelled `NaN` except in `ru` and `uk`.
  - a foreign currency's symbol comes from tele's list of well-known symbols (`$`, `€`, `£`, `¥`, `CA$`…), then from another region of the same language, else the ISO code.

Example:

```ts
const money = new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' })
console.log(money.format(1234.5)) // 1 234,50 ₽
console.log(new Intl.NumberFormat('en-US', { notation: 'compact' }).format(15300)) // 15K
```

### class Intl.DateTimeFormat

```ts
declare class Intl.DateTimeFormat {
  constructor(locales?: string | string[], options?: Intl.DateTimeFormatOptions)
  format(date?: Date | number): string
  formatToParts(date?: Date | number): Intl.DateTimeFormatPart[]
  formatRange(start: Date | number, end: Date | number): string
  formatRangeToParts(start: Date | number, end: Date | number): Intl.DateTimeRangeFormatPart[]
  resolvedOptions(): Intl.ResolvedDateTimeFormatOptions
  static supportedLocalesOf(locales: string | string[], options?: { localeMatcher?: string }): string[]
}
```

formats dates and times with the locale's month and day names and Qt's date and time patterns.

- **grant:** none.
- **parameters:**
  - `dateStyle` / `timeStyle`: `'full'`, `'long'`, `'medium'`, `'short'` (can't be mixed with the component options).
  - components: `weekday`, `era`, `year`, `month` (`'numeric'`, `'2-digit'`, `'short'`, `'long'`, `'narrow'`), `day`, `hour`, `minute`, `second`, `fractionalSecondDigits` (1 to 3), `dayPeriod`, `timeZoneName` (`'short'`, `'long'`, `'shortOffset'`, `'longOffset'`). with none of them you get the numeric date.
  - `hour12` / `hourCycle` (`'h11'`, `'h12'`, `'h23'`, `'h24'`) or `-u-hc-` in the tag; the default follows the locale (12 hours for `en-US`, 24 for `ru`).
  - `timeZone`: `'UTC'` (and its aliases like `'Etc/UTC'`, `'GMT'`), the computer's zone (its IANA name, the default) or a fixed offset `'+03:00'`.
- **returns:** `format` (a bound getter) gives the string, `formatToParts` the typed pieces, `formatRange` both ends (`3/5/2024 – 3/8/2024`, a shared date when only the time differs), `resolvedOptions` the locale, `calendar: 'gregory'`, `timeZone`, the hour cycle and the components or styles used.
- **throws:** `RangeError: Invalid time zone specified: <zone>` for any other zone, `RangeError: Invalid time value` for invalid dates, `TypeError` when styles and components are mixed.
- **notes:**
  - partial: patterns come from Qt's long and short formats with fields taken out or added, not from CLDR's per-skeleton table, so unusual combinations can differ from a browser (spacing, the order of the weekday, `dateStyle: 'medium'` uses abbreviated month names everywhere).
  - only the gregorian calendar; `era` names exist for `en`, `ru`, `uk`, `de`, `fr`, `es` (English elsewhere).
  - the local zone's short name is Qt's abbreviation (`MSK`); when Qt only has a long Windows name, `GMT+3` is shown instead.
  - `Date.prototype.toLocaleString` and friends use this class; an invalid date gives `'Invalid Date'`.

Example:

```ts
const when = Date.UTC(2024, 2, 5, 15, 4, 5)
console.log(new Intl.DateTimeFormat('ru-RU', { dateStyle: 'long', timeZone: 'UTC' }).format(when)) // 5 марта 2024 г.
console.log(new Date(when).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: 'UTC' })) // 3:04 PM
```

### class Intl.RelativeTimeFormat

```ts
declare class Intl.RelativeTimeFormat {
  constructor(locales?: string | string[], options?: Intl.RelativeTimeFormatOptions)
  format(value: number, unit: Intl.RelativeTimeFormatUnit): string
  formatToParts(value: number, unit: Intl.RelativeTimeFormatUnit): Intl.RelativeTimeFormatPart[]
  resolvedOptions(): Intl.ResolvedRelativeTimeFormatOptions
  static supportedLocalesOf(locales: string | string[], options?: { localeMatcher?: string }): string[]
}
```

phrases like "in 3 days", "5 часов назад" or "yesterday".

- **grant:** none.
- **parameters:**
  - `value` (`number`): negative (and `-0`) is the past.
  - `unit`: `'second'`, `'minute'`, `'hour'`, `'day'`, `'week'`, `'month'`, `'quarter'`, `'year'`, singular or plural.
  - `numeric`: `'always'` (default, `1 day ago`) or `'auto'` (`yesterday`, `next year`, `сейчас`).
  - `style`: `'long'` (default), `'short'`, `'narrow'`.
- **returns:** the phrase; `formatToParts` gives the number parts (with `unit`) between literals.
- **throws:** `RangeError` for a non-finite value or an unknown unit.
- **notes:**
  - partial: words for the 20 languages above except `ar` and `fa`, which use English. `short` and `narrow` are real only for `en` and `ru`; other languages use the long words.
  - the number uses the locale's digits and plural rules (`через 21 день`, `через 1,5 дня`).

Example:

```ts
const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
console.log(rtf.format(-1, 'day'), '|', rtf.format(3, 'days')) // yesterday | in 3 days
```

### class Intl.PluralRules

```ts
declare class Intl.PluralRules {
  constructor(locales?: string | string[], options?: Intl.PluralRulesOptions)
  select(n: number): Intl.LDMLPluralRule
  selectRange(start: number, end: number): Intl.LDMLPluralRule
  resolvedOptions(): Intl.ResolvedPluralRulesOptions
  static supportedLocalesOf(locales: string | string[], options?: { localeMatcher?: string }): string[]
}
```

tells which plural form a number takes: `'zero'`, `'one'`, `'two'`, `'few'`, `'many'` or `'other'`.

- **grant:** none.
- **parameters:**
  - `type`: `'cardinal'` (default, "1 day, 2 days") or `'ordinal'` ("1st, 2nd").
  - the digit options of `NumberFormat` (`minimumFractionDigits`…): the number is rounded first, so `1` with one fraction digit is `1.0` and takes `'other'` in English.
- **returns:** the category; `resolvedOptions().pluralCategories` lists the categories the language has.
- **notes:**
  - CLDR rules for `en`, `ru`, `uk`, `be`, `de`, `fr`, `es`, `it`, `pt` (`pt-PT` too), `pl`, `cs`, `tr`, `ar`, `ja`, `zh`, `ko`, `fa`, `id`, `nl`, `sv`; other languages use the English rules.
  - `selectRange` returns the category of the end, which is what most languages do.

Example:

```ts
const forms: Partial<Record<Intl.LDMLPluralRule, string>> = { one: 'сообщение', few: 'сообщения', many: 'сообщений', other: 'сообщения' }
const pr = new Intl.PluralRules('ru')
const label = (n: number) => `${n} ${forms[pr.select(n)] ?? forms.other}`
console.log(label(1), label(3), label(25)) // 1 сообщение 3 сообщения 25 сообщений
```

### class Intl.Collator

```ts
declare class Intl.Collator {
  constructor(locales?: string | string[], options?: Intl.CollatorOptions)
  compare(x: string, y: string): number
  resolvedOptions(): Intl.ResolvedCollatorOptions
  static supportedLocalesOf(locales: string | string[], options?: { localeMatcher?: string }): string[]
}
```

compares strings in the locale's alphabetical order, through Qt's `QCollator`.

- **grant:** none.
- **parameters:**
  - `numeric` (or `-u-kn`): compare digit runs as numbers (`item2` before `item10`).
  - `sensitivity`: `'variant'` (default), `'case'`, `'accent'` (ignores case), `'base'` (ignores case and accents).
  - `ignorePunctuation`: skip punctuation.
  - `usage`, `caseFirst`, `collation`: accepted and reported, but they don't change the order.
- **returns:** `compare` (a bound getter, so `list.sort(collator.compare)` works) returns `-1`, `0` or `1`.
- **notes:**
  - the order is the operating system's collation through Qt (ICU on Linux and macOS, the Windows API on Windows), so ties between visually different strings can differ between platforms.
  - accents are stripped in JavaScript for `'base'` and `'case'`.

Example:

```ts
const files = ['photo10.jpg', 'Photo2.jpg', 'photo1.jpg']
files.sort(new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' }).compare)
console.log(files) // ['photo1.jpg', 'Photo2.jpg', 'photo10.jpg']
```

### class Intl.ListFormat

```ts
declare class Intl.ListFormat {
  constructor(locales?: string | string[], options?: Intl.ListFormatOptions)
  format(list: Iterable<string>): string
  formatToParts(list: Iterable<string>): { type: 'element' | 'literal', value: string }[]
  resolvedOptions(): Intl.ResolvedListFormatOptions
  static supportedLocalesOf(locales: string | string[], options?: { localeMatcher?: string }): string[]
}
```

joins a list the way the language does: "a, b, and c", "a, b и c", "a、b和c".

- **grant:** none.
- **parameters:**
  - `type`: `'conjunction'` (and, default), `'disjunction'` (or), `'unit'` (`3 ft, 7 in`).
  - `style`: `'long'` (default), `'short'`, `'narrow'`.
- **returns:** the joined string; `formatToParts` gives `element` and `literal` pieces.
- **throws:** `TypeError` when an item isn't a string.
- **notes:**
  - CLDR patterns for the 20 languages above (Spanish `y`/`o` become `e`/`u` before the right sounds); other languages use English.

Example:

```ts
console.log(new Intl.ListFormat('ru').format(['Аня', 'Боря', 'Вика'])) // Аня, Боря и Вика
```

### class Intl.Locale

```ts
declare class Intl.Locale {
  constructor(tag: string | Intl.Locale, options?: Intl.LocaleOptions)
  readonly baseName: string
  readonly language: string
  readonly script: string | undefined
  readonly region: string | undefined
  readonly calendar: string | undefined
  readonly collation: string | undefined
  readonly hourCycle: string | undefined
  readonly caseFirst: string | undefined
  readonly numeric: boolean
  readonly numberingSystem: string | undefined
  maximize(): Intl.Locale
  minimize(): Intl.Locale
  getTextInfo(): { direction: 'ltr' | 'rtl' }
  getWeekInfo(): { firstDay: number, weekend: number[], minimalDays: number }
  toString(): string
}
```

a parsed BCP 47 tag.

- **grant:** none.
- **parameters:**
  - `tag`: a tag string or another `Intl.Locale`.
  - `options`: `language`, `script`, `region` and the `-u-` keywords (`calendar`, `collation`, `hourCycle`, `caseFirst`, `numeric`, `numberingSystem`) override the tag.
- **returns:** the parts; `toString()` the canonical tag with its `-u-` extension.
- **throws:** `RangeError: Incorrect locale information provided` for malformed tags or options.
- **notes:**
  - partial: `maximize()` only adds Qt's default region (no script), `minimize()` drops the script and a default region; `getTextInfo` and `getWeekInfo().firstDay` come from Qt, the weekend is always Saturday and Sunday.

Example:

```ts
const locale = new Intl.Locale('ru-Cyrl-RU')
console.log(locale.language, locale.script, locale.region, locale.baseName) // ru Cyrl RU ru-Cyrl-RU
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

### class Worker

```ts
interface WorkerOptions {
  name?: string
}

declare class Worker extends EventTarget {
  constructor(path: string | URL, options?: WorkerOptions)
  postMessage(data: unknown, transfer?: Transferable[] | StructuredSerializeOptions): void
  terminate(): void
  onmessage: ((this: Worker, event: MessageEvent) => void) | null
  onmessageerror: ((this: Worker, event: MessageEvent) => void) | null
  onerror: ((this: Worker, event: ErrorEvent) => void) | null
  addEventListener(type: 'message' | 'messageerror', listener: (this: Worker, event: MessageEvent) => void, options?: AddEventListenerOptions | boolean): void
  addEventListener(type: 'error', listener: (this: Worker, event: ErrorEvent) => void, options?: AddEventListenerOptions | boolean): void
  addEventListener(type: string, listener: EventListenerOrEventListenerObject | null, options?: AddEventListenerOptions | boolean): void
  removeEventListener(type: 'message' | 'messageerror', listener: (this: Worker, event: MessageEvent) => void, options?: EventListenerOptions | boolean): void
  removeEventListener(type: 'error', listener: (this: Worker, event: ErrorEvent) => void, options?: EventListenerOptions | boolean): void
  removeEventListener(type: string, listener: EventListenerOrEventListenerObject | null, options?: EventListenerOptions | boolean): void
}
```

runs a file of the script in the background: its own QuickJS runtime on its own thread, so heavy computation doesn't freeze tele or the script. the two sides talk only through messages.

- **grant:** none.
- **parameters:**
  - `path` (`string | URL`): a `.ts` or `.js` file of the script, relative to the script's folder (the folder of its entry file, not of the module calling `new Worker`); `.ts` and `.js` can be left out. a `file:` url works too. TypeScript is stripped like for imports.
  - `options.name` (`string`, optional): shown in the worker's log lines and as `self.name` inside; default `''` (logs then use the file name).
  - `postMessage(data)`: copies `data` to the worker, which gets a `message` event with the copy.
  - `terminate()`: stops the worker right away, even in the middle of an endless loop, and waits for its thread to end; pending messages are dropped, no more events come.
  - `onmessage` / `addEventListener('message')`: a `MessageEvent` whose `data` is a copy of what the worker posted.
  - `onmessageerror` / `addEventListener('messageerror')`: a message that could not be copied back into this script (for example, over the memory limit); `data` is `undefined`.
  - `onerror` / `addEventListener('error')`: an `ErrorEvent` for an uncaught error inside the worker (a throwing listener or timer, a top-level throw, a syntax error, an import, a file the stripper rejects). call `event.preventDefault()` to keep it out of the log.
- **returns:** the `Worker`. it starts loading at once; messages posted before it is ready wait in order.
- **throws:**
  - `TeleError` `not-found` (`can't find '<path>'`), `forbidden` (`'<path>' is outside the script`), `unsupported` (`a worker starts from a file of the script, not '<url>'`) for anything but a script file.
  - `TeleError` `quota-exceeded` (`a script runs at most 8 workers at once`).
  - `postMessage`: `DOMException` `DataCloneError` for values that can't be copied (functions, symbols, `Error` objects, `DataView`, `WeakMap`, promises, objects with getter properties).
- **notes:**
  - messages are copied with QuickJS's own serializer, never shared: plain objects, arrays, strings, numbers, booleans, `null`, `undefined`, `bigint`, `Date`, `RegExp`, `Map`, `Set`, `ArrayBuffer`, typed arrays (with their whole buffer), boxed primitives, cycles and repeated references. class instances arrive as plain objects (own enumerable fields only, no prototype).
  - transferables are not supported: a `transfer` list is accepted and ignored, the data is always copied and the sender keeps its buffers.
  - the worker gets no `tg`, no `fetch`, no `Worker` and no imports: send it the data it needs. see `type WorkerGlobalScope` for what it has.
  - each worker has 256 MB of memory and the same stack as a script; there is no time budget inside a worker, endless loops only cost its own thread.
  - `console.*` inside the worker goes to the script's log as `[worker <name>] ...`.
  - workers stop when the script stops or reloads. a worker that ends itself with `close()` sends no event; later `postMessage` calls do nothing.
  - saving only the worker file doesn't reload the script; save the script's own file to restart with the new worker code.

Example:

```ts
// primes.ts, next to the script
declare const self: WorkerGlobalScope
self.onmessage = (event) => {
  const limit = Number(event.data)
  const primes: number[] = []
  for (let n = 2; primes.length < limit; ++n) {
    if (primes.every((p) => n % p !== 0)) primes.push(n)
  }
  self.postMessage(primes)
}

// index.ts
const worker = new Worker('./primes.ts', { name: 'primes' })
worker.onmessage = (event) => console.log('got', (event.data as number[]).length, 'primes')
worker.onerror = (event) => {
  event.preventDefault()
  console.warn('primes failed:', event.message, `${event.filename}:${event.lineno}`)
}
worker.postMessage(20_000)
```

### type WorkerGlobalScope

```ts
interface WorkerGlobalScope extends EventTarget {
  readonly self: WorkerGlobalScope
  readonly name: string
  postMessage(data: unknown, transfer?: Transferable[] | StructuredSerializeOptions): void
  close(): never
  onmessage: ((this: WorkerGlobalScope, event: MessageEvent) => void) | null
  onmessageerror: ((this: WorkerGlobalScope, event: MessageEvent) => void) | null
  addEventListener(type: 'message' | 'messageerror', listener: (this: WorkerGlobalScope, event: MessageEvent) => void, options?: AddEventListenerOptions | boolean): void
  addEventListener(type: string, listener: EventListenerOrEventListenerObject | null, options?: AddEventListenerOptions | boolean): void
  removeEventListener(type: 'message' | 'messageerror', listener: (this: WorkerGlobalScope, event: MessageEvent) => void, options?: EventListenerOptions | boolean): void
  removeEventListener(type: string, listener: EventListenerOrEventListenerObject | null, options?: EventListenerOptions | boolean): void
}
```

the globals inside a worker file. they exist only there: type them with `declare const self: WorkerGlobalScope` at the top of the worker file (the declaration is stripped).

- **grant:** none.
- **parameters:**
  - `self` (`WorkerGlobalScope`): `globalThis`; `postMessage`, `close`, `onmessage` and the listener methods are also plain globals.
  - `name` (`string`): `options.name` from `new Worker`, or `''`.
  - `postMessage(data)`: copies `data` to the script, which gets a `message` event on its `Worker`. same copy rules and `DataCloneError` as `worker.postMessage`.
  - `close()`: ends the worker at once: the code after it doesn't run, timers and queued messages are dropped. messages posted before it are still delivered.
  - `onmessage` / `addEventListener('message')`: a `MessageEvent` with a copy of what the script posted; `messageerror` when it couldn't be copied in.
- **notes:**
  - also available: `console.*`, `setTimeout` / `setInterval` / `clearTimeout` / `clearInterval`, `queueMicrotask`, `performance.now()`, `TextEncoder` / `TextDecoder`, `atob` / `btoa`, `crypto.getRandomValues` / `crypto.randomUUID` / `crypto.subtle.digest` and HMAC, `structuredClone`, `URL` / `URLSearchParams`, `EventTarget` / `Event` / `CustomEvent` / `MessageEvent` / `ErrorEvent`, `AbortController`, `DOMException`, `reportError`, `Intl`, `TeleError`, and the whole javascript standard library.
  - not available: `tg`, `fetch`, `defineScript`, `Worker`, `WebSocket`, imports (static or dynamic: they fail with `a worker can't import modules, ...`; `import type` is fine, it is stripped).
  - the file runs as a module: top-level `await` works.
  - an uncaught error (in a listener, a timer, a microtask, or passed to `reportError`) fires `error` on the script's `Worker` with the message, file, line and column; the worker keeps running. an unhandled promise rejection is only logged.

Example:

```ts
// hash.ts
declare const self: WorkerGlobalScope
self.addEventListener('message', async (event) => {
  const bytes = new TextEncoder().encode(String(event.data))
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))
  self.postMessage(digest.toHex())
  if (event.data === 'last') self.close()
})
```

### class ErrorEvent

```ts
interface ErrorEventInit extends EventInit {
  message?: string
  filename?: string
  lineno?: number
  colno?: number
  error?: unknown
}

declare class ErrorEvent extends Event {
  constructor(type: string, init?: ErrorEventInit)
  readonly message: string
  readonly filename: string
  readonly lineno: number
  readonly colno: number
  readonly error: unknown
}
```

the event a `Worker` fires for an uncaught error inside it; usable as a plain event class too.

- **grant:** none.
- **parameters:**
  - `message` (`string`): `Uncaught <name>: <message>` for errors, `Uncaught <value>` for anything else thrown.
  - `filename` (`string`): the full path of the worker file (or the first script file in the stack).
  - `lineno` / `colno` (`number`): where it was thrown, 1-based; `0` when unknown.
  - `error` (`unknown`): always `undefined` for worker errors: the error object stays in the worker.
- **notes:**
  - worker errors are cancelable: without `preventDefault()` they are also written to the script's log as an error.

Example:

```ts
worker.addEventListener('error', (event) => {
  event.preventDefault()
  tg.toast(`worker failed at line ${event.lineno}: ${event.message}`)
})
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

export interface Tg {
  readonly image: Images
}

export interface Tg {
  readonly fs: Fs
}

export interface Tg {
  readonly notifications: Notifications
}

export interface Tg {
  readonly stories: Stories
}

export interface Tg {
  readonly gifts: Gifts
  readonly stars: Stars
}

export interface Tg {
  interceptSearch(interceptor: SearchInterceptor): Disposer
}

export interface Tg {
  registerInline(answerer: InlineAnswerer): Disposer
}
```

the object passed to `setup`. it lives as long as the script runs on that account; after the script stops, every call on it throws `InternalError: the script was stopped`.

- **grant:** none for the object itself; each member names its own grant.
- **notes:**
  - members documented in this part: `selfId`, `scriptName`, `randomId`, `call`, `onUpdate`, `interceptRpc`, `interceptUpdate`, `onUnload`, `onNewMessage`, `onMessageEdited`, `onMessageDeleted` (talking to telegram); `Message`, `resolvePeer`, `resolveUser`, `resolveChannel`, `getMe`, `getUser`, `getChat`, `getFullUser`, `getFullChat`, `getMessages`, `getHistory`, `iterHistory`, `getDialogs`, `iterDialogs`, `sendMessage`, `sendMedia`, `editMessage`, `deleteMessages`, `forwardMessages`, `setReaction`, `readHistory`, `sendTyping`, `setDraft`, `getCachedMessage` (messages); `peers`, `overridePeer` (peers); `storage` (storage); `downloadMedia`, `uploadFile`, `sendFile` (files); `interceptSendMessage` (sending); `addLocalMessage`, `localMessages`, `decorateMessages`, `decorateMessage` (local messages and decorations); `local`, `options`, `tele` (local data and settings); `scripts` (script to script); `connection`, `onConnectionChange`, `onWake`, `schedule` (connection, wake and schedules).
  - the ui, app and platform members (`toast`, `notify`, `openUrl`, `clipboard`, `ui`, `compose`, `app`, `calls`, `accounts`, `unsafe`, the `register*` and `intercept*` surfaces for links, notifications and drops) are documented in their own sections.
  - the later `export interface Tg` blocks are interface merging: features declared further down in `tele.d.ts` add `image` (images), `fs` (the file area), `notifications` (app and system), `stories` (stories), `gifts` and `stars` (gifts and stars) and `interceptSearch` (search).
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

- **grant:** `display(peers)`; resolving a marked id or username needs `account.read(peers)` too.
- **parameters:**
  - `peer` (`InputPeerLike`): a peer tele has in its cache.
  - `override` (`PeerOverride | null`): the fields to force; absent fields keep the real value. `null` removes this script's override of that peer.
- **returns:** a promise of a `Disposer` that removes the override.
- **throws:** `TypeError`: `tg.overridePeer: this peer isn't in tele's cache` (input objects of unknown peers), `tg.overridePeer: an override is an object or null`, `tg.overridePeer: <field> has the wrong type`; `TeleError` `not-found` for unknown marked ids and usernames; `TeleError` `not-granted`: `tg.overridePeer needs the grant 'display(peers)'`. all of these reject the promise.
- **notes:**
  - one override per script per peer: calling again replaces this script's whole previous override (fields aren't merged).
  - several scripts may override one peer; they stack in registration order and later ones win per field.
  - overrides are re-applied after every server update of the peer (users, chats, full info, emoji status updates), and the real values come back exactly when removed.
  - the disposer, `overridePeer(peer, null)` and stopping the script all remove it.
  - `PeerInfo` reads show overrides, so other scripts see them too.
  - the server and other people never see an override, but it changes what you see, which is why it needs `display(peers)`: a stranger can be made to look verified.

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

- **grant:** `display(peers)`, for `tg.overridePeer`; every field needs the same grant.
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

files go through tele's own loaders and uploader: the right data center, cdn files, refreshed file references and tele's download cache all work. small files come in and out as `Uint8Array`s; big downloads go straight to disk. to read and write files yourself see [the file area](#the-file-area); to resize or convert pictures, [images](#images).

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

## the file area

`tg.fs` reads and writes real files. every script has its own folder, the file area (`<scripts folder>/.data/<script id>/`), where it works without any grant; relative paths always land there. any other folder needs `fs.read(folder)` / `fs.write(folder)`, and tele's own data stays out of reach even with the bare grants. every method is async and runs off the ui thread.

### tg.fs

```ts
readonly fs: Fs
```

the script's file api.

- **grant:** none inside the file area; `fs.read` / `fs.write` (bare or with a folder) outside it, see "paths and grants".
- **returns:** the `Fs` object (frozen).
- **notes:**
  - the area is created on first use and belongs to the script, not to an account: every account running the script shares it.
  - it's keyed by the script id (its file or folder name): renaming the script starts a new, empty area. removing the script in the Scripts manager offers to delete its area too.
  - folders starting with `.` are skipped by the script scanner, so `.data` never shows up as a script.
  - the area is not encrypted: it's plain files, unlike `tg.storage`.

Example:

```ts
await tg.fs.writeText('notes/today.txt', `started at ${new Date().toISOString()}\n`, { append: true })
console.log(await tg.fs.readText('notes/today.txt'))
```

### type Fs

```ts
export interface Fs {
  readonly root: string
  readText(path: string): Promise<string>
  readBytes(path: string): Promise<Uint8Array>
  writeText(path: string, text: string, options?: { append?: boolean }): Promise<void>
  writeBytes(
    path: string,
    bytes: Uint8Array | ArrayBuffer | ArrayBufferView,
    options?: { append?: boolean },
  ): Promise<void>
  list(path?: string): Promise<FsEntry[]>
  stat(path: string): Promise<FsStat | null>
  exists(path: string): Promise<boolean>
  mkdir(path: string, options?: { recursive?: boolean }): Promise<void>
  remove(path: string, options?: { recursive?: boolean }): Promise<void>
  rename(from: string, to: string): Promise<void>
  copy(from: string, to: string): Promise<void>
}
```

the type of `tg.fs`.

- **fields:**
  - `root` (`string`): the absolute path of the file area.
  - `readText` / `readBytes`: a whole file as text or bytes.
  - `writeText` / `writeBytes`: create, replace or append to a file.
  - `list` / `stat` / `exists`: what's there.
  - `mkdir` / `remove` / `rename` / `copy`: folders and moving things around.

Example:

```ts
const fs: Fs = tg.fs
for (const entry of await fs.list()) console.log(entry.kind, entry.name, entry.size)
```

### type FsEntry

```ts
export interface FsEntry {
  name: string
  kind: 'file' | 'folder'
  size: number
  modified: number
}
```

one item of `tg.fs.list`.

- **fields:**
  - `name` (`string`): the file or folder name, without the path.
  - `kind` (`'file' | 'folder'`): a link counts as what it points to.
  - `size` (`number`): bytes; `0` for folders.
  - `modified` (`number`): the last change, ms since 1970 (like `Date.now()`).

Example:

```ts
const big = (await tg.fs.list('cache')).filter((entry) => entry.kind === 'file' && entry.size > 1_000_000)
```

### type FsStat

```ts
export interface FsStat {
  kind: 'file' | 'folder'
  size: number
  modified: number
  created: number
}
```

what `tg.fs.stat` returns for an existing path.

- **fields:**
  - `kind` (`'file' | 'folder'`): a link counts as what it points to.
  - `size` (`number`): bytes; `0` for folders.
  - `modified` (`number`): the last change, ms since 1970.
  - `created` (`number`): the creation time, ms since 1970; on systems that don't keep it, the same as `modified`.

Example:

```ts
const stat = await tg.fs.stat('cache/index.json')
if (stat && Date.now() - stat.modified > 86_400_000) await tg.fs.remove('cache', { recursive: true })
```

### paths and grants

```ts
'notes/today.txt'           // the file area
'documents/exports/a.txt'   // needs fs.read(documents) / fs.write(documents)
'C:/Users/me/Desktop/x.txt' // needs a grant covering that folder
```

how a path string becomes a file, and which grant it needs.

- **grant:** none inside the file area. reading outside it (`readText`, `readBytes`, `list`, `stat`, `exists`, the source of `copy`) needs `fs.read` or `fs.read(<folder>)` covering the path; changing outside it (`writeText`, `writeBytes`, `mkdir`, `remove`, both ends of `rename`, the target of `copy`) needs `fs.write` or `fs.write(<folder>)`. `fs.write` doesn't include reading: declare both when the script reads back what it writes.
- **parameters:**
  - a relative path (`notes/a.txt`, `./x`, `.`) is inside the file area. `..` is resolved first; a path that ends up outside the area is refused with `forbidden`, never looked up elsewhere.
  - an absolute path (`C:/Users/me/x.txt`, `/home/me/x.txt`) is used as it is. one inside the file area needs no grant.
  - named folders, the same names grants use: `~/x` and `home/x`, `documents/x`, `downloads/x`, `desktop/x`, `pictures/x`, `music/x`, `videos/x`, `temp/x` (the system's folders). so a folder in the area that's called `temp` is `./temp/x`.
  - `\` works like `/`. on windows, names ending in `.` or a space, `:` outside the drive letter, the characters `<>"|?*` and `//./` / `//?/` device paths are refused.
- **throws:** every method rejects (argument errors too, the methods are `async`):
  - `TypeError` (`tg.fs.readText: path is a non-empty string`, `tg.fs.readText: '<path>' isn't a valid path`).
  - `TeleError` `forbidden` (`tg.fs.readText: '../x' leads out of the script's file area`, or one of the protected places, see "what tg.fs never touches").
  - `TeleError` `not-granted` with `grant` set to `fs.read(<absolute path>)` / `fs.write(<absolute path>)` (`tg.fs.read needs the grant 'fs.read(C:/Users/me/Documents/x.txt)'`); a folder grant covering it works too.
  - `TeleError` `not-found` (`tg.fs.readText: this system has no 'music' folder`) when the system has no such named folder.
- **notes:** grants cover a folder and everything inside it, after `..` is resolved: `fs.write(temp/my-app)` doesn't cover `temp/my-app/../other`.

Example:

```ts
export default defineScript({
  name: 'exporter',
  grants: ['fs.read(documents/exports)', 'fs.write(documents/exports)'],
  async setup(tg) {
    await tg.fs.mkdir('documents/exports', { recursive: true })
    await tg.fs.writeText('documents/exports/hello.txt', 'hi')
    console.log(await tg.fs.list('documents/exports'))
  },
})
```

### what tg.fs never touches

```ts
// <tele working folder>/tdata/
// <scripts folder>/.data/<another script>/
```

places refused with `TeleError` `forbidden` for every script, whatever it was granted (the bare `fs.read` / `fs.write` too).

- **grant:** none unlocks them.
- **notes:**
  - tele's data: the `tdata` folder in tele's working folder and everything inside it (sessions, keys, settings, caches), including the account folders where tele keeps the encrypted script storage, local messages and the per-account script state.
  - other scripts' file areas: everything under `<scripts folder>/.data/` except the script's own area, and the `.data` folder itself (it would list every script's area).
  - removing, renaming or replacing a folder that contains any of these (tele's working folder, the scripts folder) is refused as a whole.
  - links are followed for this check: a link or junction that leads into one of these places is refused like the place itself, also inside a folder you `remove`, `rename` or `copy`.
  - inside the file area, a link that leads out of it is refused too.

Example:

```ts
try {
  await tg.fs.list(tg.fs.root + '/..')
} catch (error) {
  if (error instanceof TeleError) console.log(error.code)
}
```

### tg.fs.root

```ts
readonly root: string
```

the absolute path of the script's file area, with `/` separators and no trailing slash.

- **grant:** none.
- **returns:** `<scripts folder>/.data/<script id>`; it may not exist until the first call creates it.

Example:

```ts
console.log(`my files are in ${tg.fs.root}`)
await tg.fs.writeText(`${tg.fs.root}/a.txt`, 'same as writeText("a.txt")')
```

### tg.fs.readText(path)

```ts
readText(path: string): Promise<string>
```

reads a whole file as utf-8 text.

- **grant:** none in the file area; `fs.read` outside it.
- **parameters:**
  - `path` (`string`): see "paths and grants".
- **returns:** the text. a utf-8 byte order mark is dropped; invalid bytes become U+FFFD.
- **throws:** rejects with `TeleError` `not-found` (`tg.fs.readText: there's nothing at <path>`), `unsupported` (`<path> is a folder`), `quota-exceeded` (`<path> is over 256 MB`), `internal` (`can't read <path>: <reason>`), plus the path errors.
- **notes:** at most 256 MB per read, but the whole script has 256 MB of memory, so keep big files in pieces.

Example:

```ts
const config = JSON.parse(await tg.fs.readText('config.json').catch(() => '{}'))
```

### tg.fs.readBytes(path)

```ts
readBytes(path: string): Promise<Uint8Array>
```

reads a whole file as bytes.

- **grant:** none in the file area; `fs.read` outside it.
- **parameters:**
  - `path` (`string`): see "paths and grants".
- **returns:** the bytes.
- **throws:** like `readText`: `not-found`, `unsupported` for a folder, `quota-exceeded` over 256 MB, `internal`, plus the path errors.

Example:

```ts
const photo = await tg.fs.readBytes('pictures/cat.jpg')
await tg.sendFile('me', photo, { fileName: 'cat.jpg', asPhoto: true })
```

### tg.fs.writeText(path, text, options?)

```ts
writeText(path: string, text: string, options?: { append?: boolean }): Promise<void>
```

writes text as utf-8, replacing the file or appending to it.

- **grant:** none in the file area; `fs.write` outside it.
- **parameters:**
  - `path` (`string`): the file; missing folders on the way are created.
  - `text` (`string`): the content.
  - `options.append` (`boolean`, optional): add to the end instead of replacing.
- **returns:** nothing.
- **throws:** rejects with `TypeError: tg.fs.writeText: text is a string`, `TeleError` `quota-exceeded` (`tg.fs.writeText: the script's file area would go over its 256 MB quota`), `unsupported` (`<path> is a folder`), `internal` (`can't write <path>: <reason>`), plus the path errors.
- **notes:**
  - replacing writes a temporary file and swaps it in, so a crash never leaves half a file (where the system can't do that, the file is written in place).
  - in the file area, the quota counts every file in it; the check happens before anything is written. outside it there's no quota.

Example:

```ts
await tg.fs.writeText('log.txt', `${new Date().toISOString()} started\n`, { append: true })
```

### tg.fs.writeBytes(path, bytes, options?)

```ts
writeBytes(
  path: string,
  bytes: Uint8Array | ArrayBuffer | ArrayBufferView,
  options?: { append?: boolean },
): Promise<void>
```

writes bytes, replacing the file or appending to it.

- **grant:** none in the file area; `fs.write` outside it.
- **parameters:**
  - `path` (`string`): the file; missing folders are created.
  - `bytes` (`Uint8Array | ArrayBuffer | ArrayBufferView`): the content; for other typed arrays and `DataView`s the bytes they view are written.
  - `options.append` (`boolean`, optional): add to the end instead of replacing.
- **returns:** nothing.
- **throws:** rejects with `TypeError: tg.fs.writeBytes: bytes are a Uint8Array, an ArrayBuffer or an ArrayBuffer view`, otherwise like `writeText`.

Example:

```ts
const avatar = await tg.downloadMedia(message)
await tg.fs.writeBytes(`avatars/${message.id}.jpg`, avatar)
```

### tg.fs.list(path?)

```ts
list(path?: string): Promise<FsEntry[]>
```

the files and folders directly inside a folder.

- **grant:** none in the file area; `fs.read` outside it.
- **parameters:**
  - `path` (`string`, optional): the folder, `'.'` (the area itself) by default.
- **returns:** `FsEntry`s sorted by name, hidden files included, without `.` and `..`.
- **throws:** rejects with `TeleError` `not-found` (`there's nothing at <path>`), `unsupported` (`<path> is a file`), plus the path errors.

Example:

```ts
for (const entry of await tg.fs.list('downloads')) {
  if (entry.kind === 'file' && entry.name.endsWith('.torrent')) console.log(entry.name)
}
```

### tg.fs.stat(path)

```ts
stat(path: string): Promise<FsStat | null>
```

what's at a path.

- **grant:** none in the file area; `fs.read` outside it.
- **parameters:**
  - `path` (`string`): a file or folder.
- **returns:** an `FsStat`, or `null` when nothing is there.
- **throws:** rejects with the path errors.

Example:

```ts
const stat = await tg.fs.stat('cache.json')
console.log(stat ? `${stat.size} bytes, ${new Date(stat.modified)}` : 'no cache yet')
```

### tg.fs.exists(path)

```ts
exists(path: string): Promise<boolean>
```

whether a file or folder is there.

- **grant:** none in the file area; `fs.read` outside it.
- **parameters:**
  - `path` (`string`): a file or folder.
- **returns:** `true` or `false` (a broken link is `false`).
- **throws:** rejects with the path errors.

Example:

```ts
if (!(await tg.fs.exists('settings.json'))) await tg.fs.writeText('settings.json', '{}')
```

### tg.fs.mkdir(path, options?)

```ts
mkdir(path: string, options?: { recursive?: boolean }): Promise<void>
```

creates a folder.

- **grant:** none in the file area; `fs.write` outside it.
- **parameters:**
  - `path` (`string`): the new folder.
  - `options.recursive` (`boolean`, optional): create the missing folders above it too.
- **returns:** nothing; an existing folder is fine.
- **throws:** rejects with `TeleError` `not-found` (`there's no folder <parent>`, without `recursive`), `unsupported` (`<path> is a file`), `internal` (`can't create <path>`), plus the path errors.
- **notes:** folders don't count towards the quota.

Example:

```ts
await tg.fs.mkdir('exports/2026/10', { recursive: true })
```

### tg.fs.remove(path, options?)

```ts
remove(path: string, options?: { recursive?: boolean }): Promise<void>
```

deletes a file, a link or a folder. it doesn't go to the recycle bin.

- **grant:** none in the file area; `fs.write` outside it.
- **parameters:**
  - `path` (`string`): what to delete. `'.'` deletes the whole area (it's created again on the next call).
  - `options.recursive` (`boolean`, optional): delete a folder with everything in it.
- **returns:** nothing.
- **throws:** rejects with `TeleError` `not-found` (`there's nothing at <path>`), `unsupported` (`<path> isn't empty, pass { recursive: true }`), `internal` (`can't remove <path>`), `forbidden` when the folder contains a protected place or a link into one, plus the path errors.
- **notes:** a link is removed itself, never what it points to.

Example:

```ts
await tg.fs.remove('cache', { recursive: true }).catch(() => {})
```

### tg.fs.rename(from, to)

```ts
rename(from: string, to: string): Promise<void>
```

moves or renames a file or folder, also between the file area and outside folders.

- **grant:** none in the file area; `fs.write` for an end outside it (both ends change).
- **parameters:**
  - `from` (`string`): what to move.
  - `to` (`string`): the new path; missing folders are created. an existing file there is replaced; an existing folder is not.
- **returns:** nothing.
- **throws:** rejects with `TeleError` `not-found` (nothing at `from`), `unsupported` (`<to> already exists` for folders, `can't move <from> into itself`), `quota-exceeded` (moving into the area), `internal` (`can't move <from> to <to>`; folders can't move between drives), plus the path errors.

Example:

```ts
await tg.fs.writeText('report.tmp', text)
await tg.fs.rename('report.tmp', 'report.txt')
```

### tg.fs.copy(from, to)

```ts
copy(from: string, to: string): Promise<void>
```

copies a file, or a folder with everything in it.

- **grant:** none in the file area; `fs.read` for `from` outside it, `fs.write` for `to` outside it.
- **parameters:**
  - `from` (`string`): a file or folder.
  - `to` (`string`): the new path; missing folders are created. an existing file is replaced; for a folder `to` must not exist.
- **returns:** nothing.
- **throws:** rejects with `TeleError` `not-found` (nothing at `from`), `unsupported` (`<to> is a folder`, `<to> already exists`, `can't copy <from> into itself`, `<to> is the same file`), `quota-exceeded` (copying into the area), `internal` (`can't copy <from> to <to>`), plus the path errors.

Example:

```ts
await tg.fs.copy('documents/template.docx', 'work/today.docx')
```

## images

`tg.image` reads, changes and writes images in tele's own image code (qt's decoders and encoders): sizes and formats, resizing, cropping, rotating, converting, and raw rgba pixels. it needs no grant. every call decodes the bytes, works on a background thread so big images don't freeze tele, and resolves with new bytes; nothing is cached between calls. useful for avatars, stickers, thumbnails and preparing files for `tg.uploadFile`.

```ts
const avatar = await tg.image.resize(photo, { width: 512, height: 512, fit: 'cover', format: 'jpeg', quality: 90 })
```

common rules for every `tg.image` method:

- input bytes are a `Uint8Array` or an `ArrayBuffer`: jpeg, png, webp, gif, bmp and whatever else this tele's qt can read (often also ico, tiff, heif, avif). exif orientation is applied, so a phone photo comes out the way it looks.
- animated images (gif, animated webp) are read as their first frame.
- images over 100 megapixels (input or result) reject with `TeleError` `quota-exceeded`.
- the output `format` defaults to the input's format. tele can write jpeg, png, webp and bmp (and other formats qt has a writer for here, like ico or ppm); a format it can't write, including the default for gif input, rejects with `TeleError` `unsupported`, so pass `format`.
- `quality` (0 to 100) goes to the encoder: jpeg and webp quality, png compression effort; unset uses the encoder's default.
- transparent pixels written to jpeg or bmp are put on white (or on `background` in `resize`).
- bytes that aren't a readable image reject with `TeleError` `unsupported` (`tg.image.<method>: these bytes aren't an image tele can read`, or `can't decode the image (<reason>)`).
- argument errors throw synchronously: none of these is an `async` function.

### tg.image

```ts
readonly image: Images

export interface Images {
  info(bytes: ImageInput): Promise<ImageInfo>
  resize(bytes: ImageInput, options: ImageResizeOptions): Promise<Uint8Array>
  crop(bytes: ImageInput, options: ImageCropOptions): Promise<Uint8Array>
  rotate(bytes: ImageInput, degrees: 90 | 180 | 270, options?: ImageEncodeOptions): Promise<Uint8Array>
  convert(bytes: ImageInput, options: ImageEncodeOptions & { format: ImageFormat }): Promise<Uint8Array>
  toPixels(bytes: ImageInput): Promise<ImagePixels>
  fromPixels(
    pixels: { width: number, height: number, data: Uint8Array | Uint8ClampedArray },
    options?: ImageEncodeOptions,
  ): Promise<Uint8Array>
}
```

the script's image tools: read the size and format, resize, crop, rotate, convert and get at the pixels. every member has its own item below.

- **grant:** none.
- **returns:** the `Images` object (frozen).

Example:

```ts
const dot = await tg.image.fromPixels({ width: 1, height: 1, data: new Uint8Array([255, 0, 0, 255]) })
console.log(await tg.image.info(dot)) // { width: 1, height: 1, format: 'png', ... }
```

### tg.image.info(bytes)

```ts
export type ImageInput = Uint8Array | ArrayBuffer

export interface ImageInfo {
  width: number
  height: number
  format: string
  animated: boolean
  frames: number
}

info(bytes: ImageInput): Promise<ImageInfo>
```

reads an image's size and format from its header, without decoding the pixels.

- **grant:** none.
- **parameters:**
  - `bytes` (`ImageInput`): the image file.
- **returns:** `Promise<ImageInfo>`: `width` and `height` as shown (after the exif rotation), `format` in lowercase (`'jpeg'`, `'png'`, `'webp'`, `'gif'`...), `frames` (1 for still images) and `animated` (more than one frame).
- **throws:** synchronously `TypeError: tg.image.info needs the image as a Uint8Array or an ArrayBuffer`; rejects with `TeleError` `unsupported` for bytes that aren't an image.
- **notes:**
  - no size limit: it never decodes the whole image.

Example:

```ts
const { width, height, format } = await tg.image.info(await tg.downloadMedia(message))
console.log(`${width}x${height} ${format}`)
```

### tg.image.resize(bytes, options)

```ts
export type ImageFormat = 'jpeg' | 'png' | 'webp' | 'bmp'
export type ImageFit = 'contain' | 'cover' | 'fill' | 'inside' | 'outside'

export interface ImageEncodeOptions {
  format?: ImageFormat
  quality?: number
}

export interface ImageResizeOptions extends ImageEncodeOptions {
  width?: number
  height?: number
  fit?: ImageFit
  background?: string
}

resize(bytes: ImageInput, options: ImageResizeOptions): Promise<Uint8Array>
```

scales an image with smooth filtering, up or down.

- **grant:** none.
- **parameters:**
  - `bytes` (`ImageInput`): the image file.
  - `options.width`, `options.height` (`number`, optional): the target box in pixels, integers from 1 to 1000000. with only one of them the other follows the aspect ratio and `fit` doesn't matter.
  - `options.fit` (`ImageFit`, optional): how the image goes into a `width` × `height` box; default `'cover'`.
    - `'cover'`: keeps the aspect ratio, fills the box and crops the overflow from the middle; the result is exactly the box.
    - `'contain'`: keeps the aspect ratio, fits inside the box and pads the rest with `background`; the result is exactly the box.
    - `'fill'`: stretches to exactly the box.
    - `'inside'`: keeps the aspect ratio and fits inside the box; the result can be smaller than the box on one side.
    - `'outside'`: keeps the aspect ratio and covers the box without cropping; the result can be bigger on one side.
  - `options.background` (`string`, optional): `'#rgb'`, `'#rgba'`, `'#rrggbb'`, `'#rrggbbaa'` or `'transparent'`: the padding for `'contain'` (default transparent) and the color under transparent pixels when writing jpeg or bmp (default white).
  - `options.format`, `options.quality`: see the rules above.
- **returns:** `Promise<Uint8Array>` with the encoded image.
- **throws:**
  - synchronously: `TypeError: tg.image.resize needs { width, height, fit }`, `tg.image.resize needs a width, a height or both`, `tg.image.resize: width is an integer from 1 to 1000000` (same for `height`, `quality`), `tg.image.resize: fit is 'contain', 'cover', 'fill', 'inside' or 'outside'`, `tg.image.resize: background is a color like '#ffffff', '#00000080' or 'transparent'`, `tg.image.resize: format is a name like 'jpeg', 'png', 'webp' or 'bmp'`.
  - rejects with `TeleError` `quota-exceeded` (`tg.image.resize: the result would be over 100 megapixels`, or the input is), `unsupported`.

Example:

```ts
const thumb = await tg.image.resize(bytes, { width: 320, height: 320, fit: 'inside', format: 'jpeg', quality: 80 })
const sticker = await tg.image.resize(bytes, { width: 512, height: 512, fit: 'contain', format: 'webp' })
```

### tg.image.crop(bytes, options)

```ts
export interface ImageCropOptions extends ImageEncodeOptions {
  x: number
  y: number
  width: number
  height: number
}

crop(bytes: ImageInput, options: ImageCropOptions): Promise<Uint8Array>
```

cuts out a rectangle of the image, pixel for pixel.

- **grant:** none.
- **parameters:**
  - `bytes` (`ImageInput`): the image file.
  - `options.x`, `options.y` (`number`): the top-left corner, integers from 0, in the image as shown (after the exif rotation).
  - `options.width`, `options.height` (`number`): the size, integers from 1.
  - `options.format`, `options.quality`: see the rules above.
- **returns:** `Promise<Uint8Array>` with the encoded crop.
- **throws:** synchronously `TypeError: tg.image.crop needs x` (and `y`, `width`, `height`), `tg.image.crop: x is an integer from 0 to 1000000`; rejects with `TypeError: tg.image.crop: the area <x>,<y> <w>x<h> is outside the <W>x<H> image` when the rectangle doesn't lie fully inside the image, `TeleError` `quota-exceeded` or `unsupported`.

Example:

```ts
const { width, height } = await tg.image.info(bytes)
const side = Math.min(width, height)
const square = await tg.image.crop(bytes, { x: (width - side) >> 1, y: (height - side) >> 1, width: side, height: side })
```

### tg.image.rotate(bytes, degrees, options?)

```ts
rotate(bytes: ImageInput, degrees: 90 | 180 | 270, options?: ImageEncodeOptions): Promise<Uint8Array>
```

turns an image clockwise by a quarter, half or three quarters, losslessly in pixels (the encoder may still recompress, as with jpeg).

- **grant:** none.
- **parameters:**
  - `bytes` (`ImageInput`): the image file.
  - `degrees` (`90 | 180 | 270`): the clockwise angle.
  - `options.format`, `options.quality` (optional): see the rules above.
- **returns:** `Promise<Uint8Array>` with the rotated image; 90 and 270 swap width and height.
- **throws:** synchronously `TypeError: tg.image.rotate: degrees is 90, 180 or 270`; rejects with `TeleError` `quota-exceeded` or `unsupported`.

Example:

```ts
const upright = await tg.image.rotate(bytes, 90, { format: 'png' })
```

### tg.image.convert(bytes, options)

```ts
convert(bytes: ImageInput, options: ImageEncodeOptions & { format: ImageFormat }): Promise<Uint8Array>
```

re-encodes an image in another format or quality, keeping its pixels and size.

- **grant:** none.
- **parameters:**
  - `bytes` (`ImageInput`): the image file.
  - `options.format` (`ImageFormat`): the output format.
  - `options.quality` (`number`, optional): 0 to 100.
- **returns:** `Promise<Uint8Array>` with the converted image.
- **throws:** synchronously `TypeError: tg.image.convert needs { format }`, `tg.image.convert: format is a name like 'jpeg', 'png', 'webp' or 'bmp'`; rejects with `TeleError` `unsupported` (`tg.image.convert: tele can't write <format> images here, pass another format`, or the input isn't an image) or `quota-exceeded`.

Example:

```ts
const jpeg = await tg.image.convert(await tg.downloadMedia(message), { format: 'jpeg', quality: 85 })
```

### tg.image.toPixels(bytes)

```ts
export interface ImagePixels {
  width: number
  height: number
  data: Uint8Array
}

toPixels(bytes: ImageInput): Promise<ImagePixels>
```

decodes an image into raw pixels for scripts that analyse or draw themselves.

- **grant:** none.
- **parameters:**
  - `bytes` (`ImageInput`): the image file.
- **returns:** `Promise<ImagePixels>`: `data` holds `width * height * 4` bytes, rows top to bottom, each pixel as red, green, blue, alpha (straight, not premultiplied alpha), like a canvas `ImageData`.
- **throws:** synchronously `TypeError: tg.image.toPixels needs the image as a Uint8Array or an ArrayBuffer`; rejects with `TeleError` `quota-exceeded` or `unsupported`.
- **notes:**
  - the pixels count against the script's 256 MB of memory: a 12 megapixel photo is 48 MB. over the limit the promise rejects with `InternalError: out of memory`.

Example:

```ts
const { width, height, data } = await tg.image.toPixels(bytes)
let sum = 0
for (let i = 0; i < data.length; i += 4) sum += data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114
console.log('average brightness', sum / (width * height))
```

### tg.image.fromPixels(pixels, options?)

```ts
fromPixels(
  pixels: { width: number, height: number, data: Uint8Array | Uint8ClampedArray },
  options?: ImageEncodeOptions,
): Promise<Uint8Array>
```

encodes raw rgba pixels into an image file.

- **grant:** none.
- **parameters:**
  - `pixels.width`, `pixels.height` (`number`): integers from 1, at most 100 megapixels together.
  - `pixels.data` (`Uint8Array | Uint8ClampedArray`): exactly `width * height * 4` bytes in the `toPixels` layout (rgba, straight alpha, rows top to bottom).
  - `options.format` (`ImageFormat`, optional): default `'png'`.
  - `options.quality` (`number`, optional): 0 to 100.
- **returns:** `Promise<Uint8Array>` with the encoded image.
- **throws:** synchronously `TypeError: tg.image.fromPixels needs { width, height, data }`, `tg.image.fromPixels: width is an integer from 1 to 1000000`, `tg.image.fromPixels: data is a Uint8Array of RGBA bytes`, `tg.image.fromPixels: data has <n> bytes, <w>x<h> RGBA needs <m>`, `TeleError` `quota-exceeded` (`tg.image.fromPixels: <w>x<h> is over 100 megapixels`); rejects with `TeleError` `unsupported` for a format tele can't write.

Example:

```ts
const size = 64
const data = new Uint8Array(size * size * 4)
for (let i = 0; i < data.length; i += 4) data.set([0x2a, 0xab, 0xee, 0xff], i)
const png = await tg.image.fromPixels({ width: size, height: size, data })
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
  - `'drop'`: the message is gone (for text, the field was already cleared). `'local'`: text only; the send is dropped and the (possibly edited) text becomes a local message in that chat, replying to the same message. it calls `tg.addLocalMessage`, so `'local'` needs `display(local)`. `'local'` for any other kind, or without `display(local)` (the `not-granted` rejection), is a fault (counted toward the switch-off) and nothing is sent; the typed text is gone like with `'drop'`.
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
  - `'local'`: text only: don't send, show it as a local message instead (needs `display(local)`; without it the verdict is a fault and nothing is sent).

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

## stories

`tg.stories` reads, posts and manages stories, adds items to the story viewer's menu, reports new stories and decides story by story whether watching one is sent to the server. reads need `account.read(stories)` (neutral), everything that changes something on the server needs `account.write(stories)` (caution): posting, editing, deleting, reacting and marking stories as read. a story is a plain object (see `type Story`); peers in it are marked ids as `bigint`. tele's ghost mode is respected the way tele's own viewer does it: `tg.stories.markRead` doesn't tell the server when ghost mode hides story views for that peer. menu items, listeners and interceptors are removed when the script stops.

### tg.stories

```ts
readonly stories: Stories

export interface Stories {
  list(peer: InputPeerLike): Promise<Story[]>
  get(peer: InputPeerLike, id: number): Promise<Story | null>
  get(peer: InputPeerLike, ids: number[]): Promise<(Story | null)[]>
  archive(peer: InputPeerLike, options?: StoryPageOptions): Promise<Story[]>
  pinned(peer: InputPeerLike, options?: StoryPageOptions): Promise<Story[]>
  sources(): StorySource[]
  markRead(peer: InputPeerLike, maxId: number): Promise<boolean>
  post(options: StoryPostOptions): Promise<Story>
  edit(id: number, options: StoryEditOptions): Promise<Story>
  delete(ids: number | number[], options?: { peer?: InputPeerLike }): Promise<number[]>
  react(
    peer: InputPeerLike,
    id: number,
    reaction: Reaction | null,
    options?: { addToRecent?: boolean },
  ): Promise<void>
  onStory(callback: (story: Story) => unknown): Disposer
  registerStoryAction(options: StoryActionOptions): Disposer
  interceptStoryView(interceptor: StoryViewInterceptor): Disposer
}
```

the script's handle on stories: reading them, posting and managing your own, the story viewer's menu and story views. every member has its own item below.

- **grant:** `account.read(stories)` to read, listen and intercept views, `account.write(stories)` to post, edit, delete, react and mark as read; `registerStoryAction` needs none.
- **returns:** the `Stories` object (frozen).

Example:

```ts
const mine = await tg.stories.list('me')
console.log(`${mine.length} active stories, ${tg.stories.sources().length} people with stories`)
```

### type Story

```ts
export interface Story {
  id: number
  peer: bigint
  from: bigint | null
  date: number
  expireDate: number
  caption: string
  entities: tl.TypeMessageEntity[]
  media: StoryMedia
  views: StoryViewCounts | null
  privacy: StoryPrivacy | 'other'
  pinned: boolean
  closeFriends: boolean
  out: boolean
  edited: boolean
  noForwards: boolean
  sentReaction: Reaction | null
  raw: tl.RawStoryItem
}
```

one story, built from the server's `storyItem`.

- **fields:**
  - `id` (`number`): the story id, unique per peer.
  - `peer` (`bigint`): the marked id of the user or channel the story belongs to.
  - `from` (`bigint | null`): who posted it when that's not `peer` (a channel story posted by an admin), else `null`.
  - `date`, `expireDate` (`number`): unix seconds of posting and of leaving the active list.
  - `caption` (`string`) and `entities` (`tl.TypeMessageEntity[]`): the caption, `''` and `[]` without one.
  - `media` (`StoryMedia`): what's shown, see `type StoryMedia`.
  - `views` (`StoryViewCounts | null`): view, reaction and forward counts with the recent viewers; the server sends them for your own stories and channels you manage, `null` otherwise.
  - `privacy` (`StoryPrivacy | 'other'`): who can see it, as far as the server tells; `'other'` when it doesn't say.
  - `pinned` (`boolean`): kept on the profile after it expires.
  - `closeFriends` (`boolean`): visible to close friends only.
  - `out` (`boolean`): posted by you.
  - `edited`, `noForwards` (`boolean`): edited after posting; forwarding and saving are off.
  - `sentReaction` (`Reaction | null`): your reaction.
  - `raw` (`tl.RawStoryItem`): the server's object.

Example:

```ts
const [story] = await tg.stories.list('durov')
if (story) console.log(story.id, story.media.type, new Date(story.expireDate * 1000))
```

### type StoryMedia

```ts
export type StoryMedia =
  | { type: 'photo', photo: tl.TypePhoto | null, raw: tl.TypeMessageMedia }
  | {
    type: 'video'
    document: tl.TypeDocument | null
    duration: number | null
    raw: tl.TypeMessageMedia
  }
  | { type: 'live', raw: tl.TypeMessageMedia }
  | { type: 'other', raw: tl.TypeMessageMedia }
```

the media of a story, by `type`.

- **values:**
  - `'photo'`: `photo` is the server's photo.
  - `'video'`: `document` is the video, `duration` its length in seconds (`null` when the server didn't say).
  - `'live'`: a live stream story.
  - `'other'`: anything else; look at `raw`.
- **notes:** pass `photo`, `document` or `raw` to `tg.downloadMedia` to get the bytes (that has its own grant).

Example:

```ts
for (const story of await tg.stories.list('me')) {
  if (story.media.type === 'video') console.log(story.id, `${story.media.duration ?? '?'} s`)
}
```

### type StoryViewCounts

```ts
export interface StoryViewCounts {
  count: number
  reactions: number
  forwards: number
  recentViewers: bigint[]
}
```

the counters of a story you can see the statistics of.

- **fields:**
  - `count` (`number`): views.
  - `reactions` (`number`): reactions.
  - `forwards` (`number`): forwards and reposts.
  - `recentViewers` (`bigint[]`): user ids of the last few viewers.

Example:

```ts
const own = await tg.stories.list('me')
console.log(own.map((story) => `${story.id}: ${story.views?.count ?? 0} views`).join('\n'))
```

### type StoryPrivacy

```ts
export type StoryPrivacy = 'everyone' | 'contacts' | 'close' | 'selected'
```

who can see a story you post or edit.

- **values:**
  - `'everyone'`: everybody; `users` are the people it's hidden from.
  - `'contacts'`: your contacts; `users` are the contacts it's hidden from.
  - `'close'`: your close friends list (managed in telegram's privacy settings); `users` is ignored.
  - `'selected'`: only `users`, which can't be empty.

Example:

```ts
await tg.stories.post({ media: bytes, privacy: 'contacts', users: ['@boss'] })
```

### tg.stories.list(peer)

```ts
list(peer: InputPeerLike): Promise<Story[]>
```

the active (not expired) stories of a user or channel, in the server's order, fresh from the server.

- **grant:** `account.read(stories)`.
- **parameters:**
  - `peer` (`InputPeerLike`): whose stories; `'me'` for yours.
- **returns:** the stories, `[]` when there are none.
- **throws:** `TeleError` `not-granted` without the grant; `TeleError` `not-found` for a peer tele doesn't know; `RpcError` from the server.
- **notes:** the server sometimes sends only the ids of close-friends stories; these are fetched in a second request so every entry is complete. listing doesn't mark anything as viewed.

Example:

```ts
const stories = await tg.stories.list('telegram')
console.log(`${stories.length} active, newest ${stories.at(-1)?.id ?? 'none'}`)
```

### tg.stories.get(peer, ids)

```ts
get(peer: InputPeerLike, id: number): Promise<Story | null>
get(peer: InputPeerLike, ids: number[]): Promise<(Story | null)[]>
```

stories by id, active, pinned or (for your own) archived.

- **grant:** `account.read(stories)`.
- **parameters:**
  - `peer` (`InputPeerLike`): whose stories.
  - `id` / `ids` (`number | number[]`): story ids.
- **returns:** the story or `null`; for an array, one entry per id in the same order, `null` for ids that don't exist or you can't see.
- **throws:** `TypeError: tg.stories.get: story ids are positive integers`; `TeleError` `not-granted`; `RpcError`.
- **notes:** doesn't mark anything as viewed.

Example:

```ts
const [first, second] = await tg.stories.get('me', [1, 2])
console.log(first?.caption, second?.caption)
```

### tg.stories.archive(peer, options?)

```ts
archive(peer: InputPeerLike, options?: StoryPageOptions): Promise<Story[]>
```

one page of the story archive: every story ever posted that's still kept, newest first. works for you and for channels you manage.

- **grant:** `account.read(stories)`.
- **parameters:**
  - `peer` (`InputPeerLike`): `'me'` or a channel you manage.
  - `options.offsetId` (`number`, optional): start below this story id; `0` (the default) starts at the newest.
  - `options.limit` (`number`, optional): 1 to 100, default 100.
- **returns:** up to `limit` stories; pass the last one's `id` as `offsetId` for the next page, an empty page is the end.
- **throws:** `TypeError: tg.stories.archive: limit is 1 to 100`, `TypeError: tg.stories.archive: offsetId is a story id or 0`; `TeleError` `not-granted`; `RpcError` (`CHAT_ADMIN_REQUIRED` for a channel you don't manage).

Example:

```ts
let offsetId = 0
for (;;) {
  const page = await tg.stories.archive('me', { offsetId, limit: 100 })
  if (!page.length) break
  console.log(page.map((story) => story.id).join(', '))
  offsetId = page[page.length - 1].id
}
```

### tg.stories.pinned(peer, options?)

```ts
pinned(peer: InputPeerLike, options?: StoryPageOptions): Promise<Story[]>
```

one page of the stories kept on a profile (the "posts" of a user or channel), newest first.

- **grant:** `account.read(stories)`.
- **parameters:** like `tg.stories.archive`: `peer`, `options.offsetId`, `options.limit` (1 to 100, default 100).
- **returns:** up to `limit` stories.
- **throws:** like `tg.stories.archive`, with `tg.stories.pinned` in the messages.

Example:

```ts
const posts = await tg.stories.pinned('durov', { limit: 10 })
console.log(posts.map((story) => story.caption).filter(Boolean))
```

### type StoryPageOptions

```ts
export interface StoryPageOptions {
  offsetId?: number
  limit?: number
}
```

paging for `tg.stories.archive` and `tg.stories.pinned`.

- **fields:**
  - `offsetId` (`number`, optional): only stories with a smaller id; `0` from the newest.
  - `limit` (`number`, optional): 1 to 100, default 100.

Example:

```ts
const older = await tg.stories.pinned('me', { offsetId: 120, limit: 20 })
```

### tg.stories.sources()

```ts
sources(): StorySource[]
```

the peers in tele's stories bar right now, from tele's cache: who has active stories, how many and how many you haven't seen. shown ones first, then the hidden (archived) ones.

- **grant:** `account.read(stories)`.
- **returns:** `StorySource[]`, see `type StorySource`; `[]` before tele loaded the list or with tele's "hide stories" option on.
- **throws:** `TeleError` `not-granted`.
- **notes:** synchronous, no request.

Example:

```ts
const unread = tg.stories.sources().filter((source) => source.unread > 0 && !source.hidden)
console.log(`${unread.length} people have stories you haven't seen`)
```

### type StorySource

```ts
export interface StorySource {
  peer: bigint
  count: number
  unread: number
  last: number
  hidden: boolean
  live: boolean
}
```

one peer of the stories bar.

- **fields:**
  - `peer` (`bigint`): its marked id; pass it to `tg.stories.list`.
  - `count` (`number`): active stories.
  - `unread` (`number`): those you haven't seen.
  - `last` (`number`): unix seconds of the newest one.
  - `hidden` (`boolean`): in the hidden (archived) part of the bar.
  - `live` (`boolean`): streaming live now.

Example:

```ts
for (const source of tg.stories.sources()) console.log(source.peer, `${source.unread}/${source.count}`)
```

### tg.stories.markRead(peer, maxId)

```ts
markRead(peer: InputPeerLike, maxId: number): Promise<boolean>
```

marks a peer's stories up to `maxId` as seen. the server then lists you among the viewers of these stories: the author sees that you watched them.

- **grant:** `account.write(stories)` (caution).
- **parameters:**
  - `peer` (`InputPeerLike`): whose stories.
  - `maxId` (`number`): the newest story id to mark.
- **returns:** `true` when the server was told; `false` when tele's ghost mode hides story views for this peer: the stories are marked seen in tele only (the bar's ring turns grey), exactly like tele's own viewer does it, and nobody is told.
- **throws:** `TypeError: tg.stories.markRead(peer, maxId): maxId is a story id`; `TeleError` `not-granted`; `RpcError`.
- **notes:** this is the only way scripts mark stories read; reacting (`tg.stories.react`) also tells the author you saw the story, ghost mode or not.

Example:

```ts
const stories = await tg.stories.list(friend)
const last = stories.at(-1)
if (last && !(await tg.stories.markRead(friend, last.id))) console.log('ghost mode kept it quiet')
```

### tg.stories.post(options)

```ts
post(options: StoryPostOptions): Promise<Story>
```

posts a story to your profile or to a channel you can post stories to.

- **grant:** `account.write(stories)` (caution).
- **parameters:**
  - `options` (`StoryPostOptions`): the media and how it's shown, see `type StoryPostOptions`.
- **returns:** the new story.
- **throws:**
  - `TypeError: tg.stories.post needs an options object`.
  - `TypeError: tg.stories.post: media must be a Uint8Array or an InputMedia`, `TypeError: tg.stories.post: the media is empty`.
  - `TypeError: tg.stories.post: unknown privacy '<privacy>', expected everyone, contacts, close, selected`, `TypeError: tg.stories.post: privacy 'selected' needs users`.
  - `TypeError: tg.stories.post: period is a number of seconds`, `TypeError: tg.stories.post: caption is a string or { text, entities }`.
  - `TeleError` `quota-exceeded` for media over 10 MB, `network` / `timed-out` when the upload fails, `not-granted` without the grant.
  - `RpcError` from the server: `PREMIUM_ACCOUNT_REQUIRED` for a `period` other than a day without Premium, `STORIES_TOO_MUCH` over the daily limit, `MEDIA_INVALID`…
- **notes:** bytes are uploaded with tele's uploader and sent as a photo (JPEG, PNG or WebP; the server converts it). for a video, upload it yourself and pass an `inputMediaUploadedDocument` with a `documentAttributeVideo`. everything is checked before the upload starts.

Example:

```ts
const bytes = await (await fetch('https://picsum.photos/720/1280')).bytes()
const story = await tg.stories.post({ media: bytes, caption: 'from a script', privacy: 'close' })
console.log(`posted ${story.id}, gone at ${new Date(story.expireDate * 1000)}`)
```

### type StoryPostOptions

```ts
export interface StoryPostOptions {
  media: Uint8Array | tl.TypeInputMedia
  caption?: InputText
  privacy?: StoryPrivacy
  users?: InputPeerLike[]
  period?: number
  pinned?: boolean
  protect?: boolean
  peer?: InputPeerLike
  fileName?: string
}
```

what `tg.stories.post` posts.

- **fields:**
  - `media` (`Uint8Array | tl.TypeInputMedia`): image bytes (uploaded and posted as a photo) or a ready TL input media.
  - `caption` (`InputText`, optional): text or `{ text, entities }`, e.g. from `md`.
  - `privacy` (`StoryPrivacy`, optional): who sees it, `'everyone'` by default.
  - `users` (`InputPeerLike[]`, optional): the excluded people for `'everyone'` / `'contacts'`, the allowed ones for `'selected'`.
  - `period` (`number`, optional): seconds it stays active: 21600, 43200, 86400 (the default) or 172800; anything but a day needs Premium.
  - `pinned` (`boolean`, optional): also keep it on the profile.
  - `protect` (`boolean`, optional): no forwarding or saving.
  - `peer` (`InputPeerLike`, optional): a channel to post to; `'me'` by default.
  - `fileName` (`string`, optional): the upload's file name, `story.jpg` by default.

Example:

```ts
await tg.stories.post({ media: bytes, caption: md`**hello**`, period: 6 * 3600, pinned: true, protect: true })
```

### tg.stories.edit(id, options)

```ts
edit(id: number, options: StoryEditOptions): Promise<Story>
```

changes the caption or the privacy of one of your stories (or of a channel's you manage).

- **grant:** `account.write(stories)` (caution).
- **parameters:**
  - `id` (`number`): the story.
  - `options` (`StoryEditOptions`): what to change; fields left out stay as they are.
- **returns:** the edited story.
- **throws:** `TypeError: tg.stories.edit(id, options): id is a story id`, `TypeError: tg.stories.edit(id, options)`, the caption and privacy `TypeError`s of `tg.stories.post`; `TeleError` `not-granted`; `RpcError` (`STORY_NOT_MODIFIED`, `STORY_ID_INVALID`…).

Example:

```ts
await tg.stories.edit(story.id, { caption: 'updated', privacy: 'contacts' })
```

### type StoryEditOptions

```ts
export interface StoryEditOptions {
  caption?: InputText
  privacy?: StoryPrivacy
  users?: InputPeerLike[]
  peer?: InputPeerLike
}
```

what `tg.stories.edit` changes.

- **fields:**
  - `caption` (`InputText`, optional): the new caption; `''` removes it.
  - `privacy` (`StoryPrivacy`, optional) with `users` (`InputPeerLike[]`, optional): the new audience, like in `type StoryPostOptions`.
  - `peer` (`InputPeerLike`, optional): the channel the story belongs to; `'me'` by default.

Example:

```ts
await tg.stories.edit(12, { privacy: 'selected', users: ['@alice', '@bob'] })
```

### tg.stories.delete(ids, options?)

```ts
delete(ids: number | number[], options?: { peer?: InputPeerLike }): Promise<number[]>
```

deletes your stories (or a channel's you manage), active or archived. tele's stories bar and profile update right away.

- **grant:** `account.write(stories)` (caution).
- **parameters:**
  - `ids` (`number | number[]`): the stories.
  - `options.peer` (`InputPeerLike`, optional): the channel; `'me'` by default.
- **returns:** the ids the server deleted.
- **throws:** `TypeError: tg.stories.delete: story ids are positive integers`; `TeleError` `not-granted`; `RpcError`.

Example:

```ts
const old = (await tg.stories.archive('me')).filter((story) => story.date < Date.now() / 1000 - 365 * 86400)
console.log('deleted', await tg.stories.delete(old.map((story) => story.id)))
```

### tg.stories.react(peer, id, reaction, options?)

```ts
react(
  peer: InputPeerLike,
  id: number,
  reaction: Reaction | null,
  options?: { addToRecent?: boolean },
): Promise<void>
```

sets your reaction on a story, `null` removes it.

- **grant:** `account.write(stories)` (caution).
- **parameters:**
  - `peer` (`InputPeerLike`): whose story.
  - `id` (`number`): the story.
  - `reaction` (`Reaction | null`): an emoji or `{ customEmojiId }`, see `type Reaction`.
  - `options.addToRecent` (`boolean`, optional): add it to your recent reactions.
- **returns:** resolves when done.
- **throws:** `TypeError: tg.stories.react(peer, id, reaction): id is a story id`, `TypeError: tg.stories.react: a reaction is an emoji string, { customEmojiId } or null`; `TeleError` `not-granted`; `RpcError` (`REACTION_INVALID`…).
- **notes:** a reaction shows the author that you saw the story, even with tele's ghost mode on (tele's own viewer asks first; a script doesn't).

Example:

```ts
const [story] = await tg.stories.list(friend)
if (story) await tg.stories.react(friend, story.id, '🔥')
```

### tg.stories.onStory(callback)

```ts
onStory(callback: (story: Story) => unknown): Disposer
```

calls `callback` with every story posted after the call that tele learns about: contacts' new stories as they arrive, channels' when tele loads them, and your own.

- **grant:** `account.read(stories)`.
- **parameters:**
  - `callback` (`(story: Story) => unknown`): may be async.
- **returns:** `Disposer` that stops it.
- **throws:** `TypeError: tg.stories.onStory(function)`; `TeleError` `not-granted`.
- **notes:** each story is reported once, after it's fetched by id (a story deleted in between is skipped, a failed fetch is logged as a warning). stories tele hides with its "hide stories" option don't arrive. loading a story doesn't mark it viewed.

Example:

```ts
tg.stories.onStory((story) => {
  if (story.peer !== tg.selfId) console.log(`new story ${story.id} from ${story.peer}: ${story.caption || story.media.type}`)
})
```

### tg.stories.registerStoryAction(options)

```ts
registerStoryAction(options: StoryActionOptions): Disposer
```

adds an item to the ⋮ menu of the story viewer, for every story of this account.

- **grant:** none.
- **parameters:**
  - `options` (`StoryActionOptions`): `text`, an optional `emoji` shown before it, an optional `icon`, and `onClick(ctx)` with the story's `peer` and `storyId`, see `type StoryActionOptions`.
- **returns:** `Disposer` that removes the item.
- **throws:**
  - `TypeError: tg.stories.registerStoryAction needs an options object`.
  - `TypeError: tg.stories.registerStoryAction needs a text` for an empty or whitespace-only `text`.
  - `TypeError: tg.stories.registerStoryAction: emoji must be a string`, `TypeError: tg.stories.registerStoryAction: onClick must be a function`.
  - `TypeError: tg.stories.registerStoryAction: <problem>` for a bad `icon`, see `type MenuIcon`.
- **notes:** items appear below tele's own ones, in registration order, script by script. `onClick` runs on the next event-loop turn after the click; reading the story needs `account.read(stories)`.

Example:

```ts
tg.stories.registerStoryAction({
  text: 'copy link',
  emoji: '🔗',
  onClick: ({ peer, storyId }) => {
    const name = tg.peers.get(peer)?.username
    if (name) tg.clipboard.write(`https://t.me/${name}/s/${storyId}`)
  },
})
```

### type StoryActionOptions

```ts
export interface StoryActionOptions {
  text: string
  emoji?: string
  icon?: MenuIcon
  onClick(context: StoryActionContext): unknown
}

export interface StoryActionContext {
  peer: bigint
  storyId: number
}
```

a story viewer menu item.

- **fields:**
  - `text` (`string`): the item's text.
  - `emoji` (`string`, optional): shown before the text.
  - `icon` (`MenuIcon`, optional): the item's icon, see `type MenuIcon`. without it the item gets tele's experimental icon.
  - `onClick` (`(context: StoryActionContext) => unknown`): runs on click, may be async; `context.peer` is the story's marked peer id, `context.storyId` its id.

Example:

```ts
tg.stories.registerStoryAction({ text: 'log', onClick: ({ peer, storyId }) => console.log(peer, storyId) })
```

### tg.stories.interceptStoryView(interceptor)

```ts
interceptStoryView(interceptor: StoryViewInterceptor): Disposer
```

asks the script each time tele's story viewer is about to count a story as watched (after a few seconds of it, or when you move on), before tele tells the server. `'skip'` keeps that one story quiet, like ghost mode does for a whole chat.

- **grant:** `account.read(stories)`.
- **parameters:**
  - `interceptor` (`StoryViewInterceptor`): `(view) => 'view' | 'skip'`, may be async, see `type StoryViewInterceptor`.
- **returns:** `Disposer` that removes the interceptor.
- **throws:** `TypeError: tg.stories.interceptStoryView(function)`; `TeleError` `not-granted`.
- **notes:**
  - `'skip'`: no read request and no view count is sent for this story; tele marks it seen locally (the ring turns grey) and remembers it like a ghost-mode read. the read state is a "seen up to" id per peer, so watching a newer story of the same peer normally later still tells the server about everything up to it.
  - `'view'`, `null` or nothing: tele goes on as usual, which with ghost mode on for that peer still means nothing is sent.
  - with several interceptors (of this script, then of later scripts in folder order) the first `'skip'` wins.
  - fails open: a throw or another value is logged as an error and counts as `'view'`; an interceptor that doesn't answer within 2 s counts as `'view'` too. your own stories aren't asked about.

Example:

```ts
const quiet = new Set([123456789n])
tg.stories.interceptStoryView((view) => (quiet.has(view.peer) ? 'skip' : 'view'))
```

### type StoryViewInterceptor

```ts
export type StoryViewInterceptor = (
  view: StoryViewInfo,
) => StoryViewVerdict | null | void | Promise<StoryViewVerdict | null | void>

export type StoryViewVerdict = 'view' | 'skip'

export interface StoryViewInfo {
  peer: bigint
  storyId: number
  date: number
  expireDate: number
  pinned: boolean
  privacy: StoryPrivacy | 'other'
  caption: string
  media: 'photo' | 'video' | 'live' | 'other'
}
```

what an interceptor gets and answers. the info comes from tele's cache, no request.

- **fields:**
  - `peer` (`bigint`), `storyId` (`number`): the story.
  - `date`, `expireDate` (`number`): unix seconds of posting and expiry.
  - `pinned` (`boolean`): kept on the profile.
  - `privacy` (`StoryPrivacy | 'other'`): its audience as tele knows it.
  - `caption` (`string`): the caption text.
  - `media` (`'photo' | 'video' | 'live' | 'other'`): the kind of media.
- **values:** `'view'` lets tele send the view, `'skip'` keeps it local.

Example:

```ts
tg.stories.interceptStoryView((view) => (view.privacy === 'close' ? 'skip' : 'view'))
```

## gifts and stars

`tg.gifts` reads and manages star gifts: the gifts on your profile (or a channel's), unique (upgraded) gifts by their slug, the catalog of gifts on sale and what a unique gift is worth. `tg.stars` reads your stars balance and its history. reading needs `account.read(gifts)`; every action that changes a gift needs the dangerous grant `account.write(gifts)`, which only an exact `account.write(gifts)` gives (a bare `account.write` doesn't). transferring and upgrading a gift can spend your stars: tele asks the server for the price and pays it from your balance without a confirmation box, so only grant `account.write(gifts)` to scripts you trust with your stars. every gift comes normalized (`Gift`, `SavedGift`) with the TL object in `raw`.

### the gifts grants

```ts
grants: ['account.read(gifts)', 'account.write(gifts)']
```

what the two gift grants allow, also for the raw API.

- **grant:** `account.read(gifts)` (neutral, "read your gifts") covers `tg.gifts.list`, `get`, `catalog`, `value`, `tg.stars.balance`, `history`, and the raw methods `payments.getSavedStarGifts`, `payments.getSavedStarGift`, `payments.getUniqueStarGift`, `payments.getStarGifts`, `payments.getUniqueStarGiftValueInfo`, `payments.getStarsStatus`, `payments.getStarsTransactions` in `tg.call`.
- **grant:** `account.write(gifts)` (dangerous, "transfer, sell, convert and upgrade your gifts") covers the write members and the raw methods `payments.saveStarGift`, `payments.convertStarGift`, `payments.upgradeStarGift`, `payments.transferStarGift`, `payments.updateStarGiftPrice`, `payments.toggleStarGiftsPinnedToTop`, plus `payments.getPaymentForm` and `payments.sendStarsForm` when the invoice is a gift upgrade (`inputInvoiceStarGiftUpgrade`) or a gift transfer (`inputInvoiceStarGiftTransfer`).
- **notes:** paying any other invoice (bots, subscriptions, buying gifts) isn't a gift action: it still needs `call(payments.sendStarsForm)`. a glob like `call(payments.*)` covers the reads and `payments.saveStarGift` / `payments.toggleStarGiftsPinnedToTop`, never the [dangerous](#dangerous-methods) `payments.transferStarGift`, `convertStarGift`, `upgradeStarGift`, `updateStarGiftPrice` or `sendStarsForm`.

Example:

```ts
export default defineScript({
  name: 'gift shelf',
  version: '1',
  grants: ['account.read(gifts)'],
  async setup(tg) {
    const { count } = await tg.gifts.list()
    tg.toast(`${count} gifts on your profile`)
  },
})
```

### tg.gifts

```ts
readonly gifts: Gifts
```

star gifts: reads (`list`, `get`, `catalog`, `value`) and actions (`transfer`, `convert`, `upgrade`, `sell`, `unlist`, `setPinned`, `setVisible`).

- **grant:** `account.read(gifts)` for the reads, the exact `account.write(gifts)` (dangerous) for the actions.
- **notes:** the actions are real: they change your profile for everyone, and `transfer` and `upgrade` may spend stars.

Example:

```ts
const { gifts } = await tg.gifts.list()
for (const gift of gifts) console.log(gift.title ?? 'gift', gift.unique ? `#${gift.number}` : `${gift.stars} stars`)
```

### type Gifts

```ts
export interface Gifts {
  list(peer?: InputPeerLike | null, options?: GiftListOptions): Promise<SavedGiftsPage>
  get(slug: string): Promise<Gift>
  catalog(): Promise<Gift[]>
  value(slug: string): Promise<GiftValueInfo>
  transfer(gift: GiftLike, to: InputPeerLike): Promise<GiftActionResult>
  convert(gift: GiftLike): Promise<void>
  upgrade(gift: GiftLike, options?: { keepDetails?: boolean }): Promise<GiftActionResult>
  sell(gift: GiftLike, options: { price: bigint | number }): Promise<void>
  unlist(gift: GiftLike): Promise<void>
  setPinned(gifts: GiftLike[], peer?: InputPeerLike): Promise<void>
  setVisible(gift: GiftLike, visible: boolean): Promise<void>
}
```

the type of `tg.gifts`.

- **fields:**
  - `list` (`(peer?, options?) => Promise<SavedGiftsPage>`): gifts on a profile.
  - `get` (`(slug) => Promise<Gift>`): a unique gift by its slug.
  - `catalog` (`() => Promise<Gift[]>`): the gifts you can send.
  - `value` (`(slug) => Promise<GiftValueInfo>`): what a unique gift is worth.
  - `transfer` (`(gift, to) => Promise<GiftActionResult>`): give a unique gift away.
  - `convert` (`(gift) => Promise<void>`): turn a regular gift into stars.
  - `upgrade` (`(gift, options?) => Promise<GiftActionResult>`): make a regular gift unique.
  - `sell` / `unlist` (`(gift, options) => Promise<void>`, `(gift) => Promise<void>`): put a unique gift on resale or take it off.
  - `setPinned` (`(gifts, peer?) => Promise<void>`): choose the pinned gifts.
  - `setVisible` (`(gift, visible) => Promise<void>`): show or hide a gift on the profile.

Example:

```ts
const gifts: Gifts = tg.gifts
```

### tg.gifts.list(peer?, options?)

```ts
list(peer?: InputPeerLike | null, options?: GiftListOptions): Promise<SavedGiftsPage>

export interface GiftListOptions {
  limit?: number
  offset?: string
}
```

reads one page of the gifts on a profile, newest first, like the Gifts tab of a profile (`payments.getSavedStarGifts`).

- **grant:** `account.read(gifts)` (and `account.read(peers)` when `peer` is a username).
- **parameters:**
  - `peer` (`InputPeerLike | null`, optional): whose gifts; default `'me'`. a channel shows the channel's gifts.
  - `options.limit` (`number`, optional): gifts per page, 1 to 100; default 50.
  - `options.offset` (`string`, optional): the `nextOffset` of the previous page.
- **returns:** `Promise<SavedGiftsPage>`: `{ gifts, count, nextOffset }`; `nextOffset` is `null` on the last page.
- **throws:**
  - rejects with `TeleError` `not-granted` without the grant.
  - rejects with `TypeError` for a bad `limit` or `offset`, or a value that isn't a peer.
  - rejects with `TeleError` `not-found` for an unknown id or username; `RpcError` from the server.
- **notes:** your own gifts and a channel's come with an `input`, so you can pass them to the actions; another user's gifts have `input: null` and every `can...` flag `false`. hidden gifts (`visible: false`) are listed only to their owner.

Example:

```ts
let offset: string | undefined
let unique = 0
do {
  const page = await tg.gifts.list('me', { limit: 100, offset })
  unique += page.gifts.filter((gift) => gift.unique).length
  offset = page.nextOffset ?? undefined
} while (offset)
console.log(unique, 'unique gifts')
```

### tg.gifts.get(slug)

```ts
get(slug: string): Promise<Gift>
```

looks up a unique gift by its slug, the part after `t.me/nft/` (`payments.getUniqueStarGift`).

- **grant:** `account.read(gifts)`.
- **parameters:**
  - `slug` (`string`): the slug (`'PlushPepe-1'`) or the whole link (`'https://t.me/nft/PlushPepe-1'`).
- **returns:** `Promise<Gift>` with `unique: true`, its model, pattern, backdrop, owner and number.
- **throws:**
  - rejects with `TeleError` `not-granted` without the grant.
  - rejects with `TypeError` for an empty slug.
  - rejects with `TeleError` `not-found` when there's no such gift (`STARGIFT_SLUG_INVALID`); other `RpcError`s as they come.

Example:

```ts
const gift = await tg.gifts.get('https://t.me/nft/PlushPepe-1')
console.log(`${gift.title} #${gift.number} owned by ${gift.ownerName ?? gift.owner}`)
```

### tg.gifts.catalog()

```ts
catalog(): Promise<Gift[]>
```

the gifts you can send right now, as the gift picker shows them (`payments.getStarGifts`).

- **grant:** `account.read(gifts)`.
- **returns:** `Promise<Gift[]>`: regular gifts with their price (`stars`), conversion value, upgrade price, and availability for limited ones.
- **throws:** rejects with `TeleError` `not-granted` without the grant; `RpcError`.

Example:

```ts
const limited = (await tg.gifts.catalog()).filter((gift) => gift.limited && !gift.soldOut)
console.log(limited.map((gift) => `${gift.stars}⭐ ${gift.availability?.remains} left`).join('\n'))
```

### tg.gifts.value(slug)

```ts
value(slug: string): Promise<GiftValueInfo>
```

what a unique gift is worth: its estimated value, first sale, last sale and floor price (`payments.getUniqueStarGiftValueInfo`).

- **grant:** `account.read(gifts)`.
- **parameters:**
  - `slug` (`string`): the slug or the `t.me/nft/` link.
- **returns:** `Promise<GiftValueInfo>`; prices are in the smallest units of `currency` (cents for USD).
- **throws:**
  - rejects with `TeleError` `not-granted` without the grant.
  - rejects with `TypeError` for an empty slug.
  - rejects with `TeleError` `not-found` for an unknown slug; `RpcError` when the server has no value for the gift.

Example:

```ts
const info = await tg.gifts.value('PlushPepe-1')
console.log(`about ${Number(info.value) / 100} ${info.currency}`)
```

### tg.gifts.transfer(gift, to)

```ts
transfer(gift: GiftLike, to: InputPeerLike): Promise<GiftActionResult>
```

gives one of your unique gifts to someone else, like Transfer in the gift box. when the transfer costs stars, tele pays it from your balance.

- **grant:** `account.write(gifts)` (dangerous, exact).
- **parameters:**
  - `gift` (`GiftLike`): a unique gift you own (a `SavedGift` from `list`, its slug, or a TL input saved star gift).
  - `to` (`InputPeerLike`): the new owner, a user or a channel.
- **returns:** `Promise<GiftActionResult>`: `stars` is what was spent (`0n` for a free transfer).
- **throws:**
  - rejects with `TeleError` `not-granted` without the exact grant.
  - rejects with `TypeError` for a value that isn't a gift or a missing `to`.
  - rejects with `TeleError` `unsupported` when the price isn't in stars (TON) or the payment needs a browser confirmation.
  - rejects with `RpcError` from the server, for example `STARGIFT_TRANSFER_TOO_EARLY_<seconds>` (see `canTransferAt`) or `BALANCE_TOO_LOW`.
- **notes:** tele asks the server for a payment form (`payments.getPaymentForm` with `inputInvoiceStarGiftTransfer`); when the server answers `NO_PAYMENT_NEEDED` it transfers for free (`payments.transferStarGift`), otherwise it pays the form's price with `payments.sendStarsForm`. there's no confirmation box: check `gift.transferStars` first if you care about the price. never run this from an automatic test.

Example:

```ts
const { gifts } = await tg.gifts.list()
const gift = gifts.find((item) => item.canTransfer && item.transferStars === null)
if (gift) await tg.gifts.transfer(gift, '@friend')
```

### tg.gifts.convert(gift)

```ts
convert(gift: GiftLike): Promise<void>
```

turns a regular gift you received into stars, like Convert in the gift box; the gift leaves your profile for good.

- **grant:** `account.write(gifts)` (dangerous, exact).
- **parameters:**
  - `gift` (`GiftLike`): a regular gift you own; `canConvert` tells whether it can still be converted, `convertStars` how much you get.
- **returns:** `Promise<void>` once it's converted.
- **throws:** rejects with `TeleError` `not-granted` without the exact grant; `TypeError` for a value that isn't a gift; `RpcError` from the server (a unique gift, or the conversion period is over).

Example:

```ts
const { gifts } = await tg.gifts.list()
for (const gift of gifts.filter((item) => item.canConvert && !item.visible)) await tg.gifts.convert(gift)
```

### tg.gifts.upgrade(gift, options?)

```ts
upgrade(gift: GiftLike, options?: { keepDetails?: boolean }): Promise<GiftActionResult>
```

makes a regular gift unique, like Upgrade in the gift box. a prepaid upgrade is free; otherwise tele pays the upgrade price in stars from your balance.

- **grant:** `account.write(gifts)` (dangerous, exact).
- **parameters:**
  - `gift` (`GiftLike`): a regular gift you own that can be upgraded (`canUpgrade`).
  - `options.keepDetails` (`boolean`, optional): keep the sender, recipient, date and message on the unique gift (its `originalDetails`).
- **returns:** `Promise<GiftActionResult>`: `stars` spent and the new unique gift in `gift` (when the server's answer has it).
- **throws:**
  - rejects with `TeleError` `not-granted` without the exact grant.
  - rejects with `TypeError` for a value that isn't a gift.
  - rejects with `TeleError` `unsupported` when the price isn't in stars or the payment needs a browser confirmation.
  - rejects with `RpcError` from the server, for example `BALANCE_TOO_LOW`.
- **notes:** a `SavedGift` with `upgradePrepaid: true` goes straight to `payments.upgradeStarGift`; anything else asks for a payment form first (`inputInvoiceStarGiftUpgrade`) and pays it with `payments.sendStarsForm`, falling back to the free upgrade on `NO_PAYMENT_NEEDED`. the price is the gift's `upgradeStars`.

Example:

```ts
const { gifts } = await tg.gifts.list()
const prepaid = gifts.find((gift) => gift.canUpgrade && gift.upgradePrepaid)
if (prepaid) {
  const { gift } = await tg.gifts.upgrade(prepaid, { keepDetails: true })
  if (gift) tg.toast(`now ${gift.title} #${gift.number}`)
}
```

### tg.gifts.sell(gift, options)

```ts
sell(gift: GiftLike, options: { price: bigint | number }): Promise<void>
```

puts one of your unique gifts on resale for a price in stars, or changes its price (`payments.updateStarGiftPrice`).

- **grant:** `account.write(gifts)` (dangerous, exact).
- **parameters:**
  - `gift` (`GiftLike`): a unique gift you own; `canResellAt` tells when it can be put on sale.
  - `options.price` (`bigint | number`): the price in whole stars, above 0.
- **returns:** `Promise<void>` once it's listed; the gift's `resaleStars` shows the price.
- **throws:** rejects with `TeleError` `not-granted` without the exact grant; `TypeError` for a bad price or a value that isn't a gift; `RpcError` from the server (too early, a price out of the allowed range).

Example:

```ts
await tg.gifts.sell('PlushPepe-1', { price: 5000n })
```

### tg.gifts.unlist(gift)

```ts
unlist(gift: GiftLike): Promise<void>
```

takes a unique gift off resale.

- **grant:** `account.write(gifts)` (dangerous, exact).
- **parameters:**
  - `gift` (`GiftLike`): a unique gift of yours that is on sale.
- **returns:** `Promise<void>`.
- **throws:** rejects with `TeleError` `not-granted` without the exact grant; `TypeError` for a value that isn't a gift; `RpcError`.

Example:

```ts
const { gifts } = await tg.gifts.list()
for (const gift of gifts.filter((item) => item.resaleStars !== null)) await tg.gifts.unlist(gift)
```

### tg.gifts.setPinned(gifts, peer?)

```ts
setPinned(gifts: GiftLike[], peer?: InputPeerLike): Promise<void>
```

makes exactly these gifts the pinned ones at the top of the profile, in this order (`payments.toggleStarGiftsPinnedToTop`).

- **grant:** `account.write(gifts)` (dangerous, exact).
- **parameters:**
  - `gifts` (`GiftLike[]`): the gifts to pin; `[]` unpins all. the server allows only a few pinned gifts.
  - `peer` (`InputPeerLike`, optional): whose profile; default the channel of the first channel gift, else you.
- **returns:** `Promise<void>`.
- **throws:** rejects with `TeleError` `not-granted` without the exact grant; `TypeError` for something that isn't an array of gifts; `RpcError` (too many pinned gifts).
- **notes:** this replaces the pinned list; to pin one more, pass the current pinned gifts plus the new one.

Example:

```ts
const { gifts } = await tg.gifts.list('me', { limit: 100 })
const pinned = gifts.filter((gift) => gift.pinned)
const best = gifts.find((gift) => gift.unique && !gift.pinned)
if (best) await tg.gifts.setPinned([...pinned, best])
```

### tg.gifts.setVisible(gift, visible)

```ts
setVisible(gift: GiftLike, visible: boolean): Promise<void>
```

shows a gift on your profile or hides it, like Show on my page / Hide in the gift box (`payments.saveStarGift`).

- **grant:** `account.write(gifts)` (dangerous, exact).
- **parameters:**
  - `gift` (`GiftLike`): one of your gifts.
  - `visible` (`boolean`): `false` hides it; anything else shows it.
- **returns:** `Promise<void>`.
- **throws:** rejects with `TeleError` `not-granted` without the exact grant; `TypeError` for a value that isn't a gift; `RpcError`.

Example:

```ts
const { gifts } = await tg.gifts.list()
for (const gift of gifts.filter((item) => !item.unique && item.visible)) await tg.gifts.setVisible(gift, false)
```

### type Gift

```ts
export interface Gift {
  unique: boolean
  id: bigint
  giftId: bigint
  slug: string | null
  link: string | null
  title: string | null
  number: number | null
  owner: bigint | null
  ownerName: string | null
  model: GiftModel | null
  pattern: GiftPattern | null
  backdrop: GiftBackdrop | null
  originalDetails: GiftOriginalDetails | null
  attributes: tl.TypeStarGiftAttribute[]
  sticker: tl.TypeDocument | null
  stars: bigint | null
  convertStars: bigint | null
  upgradeStars: bigint | null
  resaleStars: bigint | null
  limited: boolean
  soldOut: boolean
  availability: GiftAvailability | null
  value: GiftValue | null
  raw: tl.TypeStarGift
}

export type GiftRarity = number | 'uncommon' | 'rare' | 'epic' | 'legendary'

export interface GiftModel {
  name: string
  rarity: GiftRarity | null
  document: tl.TypeDocument
  crafted: boolean
}

export interface GiftPattern {
  name: string
  rarity: GiftRarity | null
  document: tl.TypeDocument
}

export interface GiftBackdrop {
  name: string
  rarity: GiftRarity | null
  centerColor: number
  edgeColor: number
  patternColor: number
  textColor: number
}

export interface GiftOriginalDetails {
  sender: bigint | null
  recipient: bigint | null
  date: number
  message: TextWithEntities | null
}

export interface GiftValue {
  amount: bigint
  currency: string
  usd: bigint | null
}

export interface GiftAvailability {
  total: number
  remains: number | null
  issued: number | null
}
```

a star gift, regular (`starGift`) or unique (`starGiftUnique`), from `get`, `catalog`, the stars history and inside `SavedGift`.

- **fields:**
  - `unique` (`boolean`): an upgraded, collectible gift with its own number, model, pattern and backdrop.
  - `id` (`bigint`): the gift's id (for a unique gift, the id of this collectible).
  - `giftId` (`bigint`): the id of the regular gift it belongs to (the same as `id` for a regular gift).
  - `slug`, `link` (`string | null`): a unique gift's slug and its `https://t.me/nft/<slug>` link; `null` for regular gifts.
  - `title` (`string | null`): the gift's name (regular gifts often have none).
  - `number` (`number | null`): a unique gift's number in its collection.
  - `owner` (`bigint | null`): a unique gift's owner as a marked id; `null` when hidden or kept outside Telegram.
  - `ownerName` (`string | null`): the owner's name, from the server's answer or the gift (hidden owners and blockchain wallets).
  - `model`, `pattern` (`{ name, rarity, document }`): the 3D model (also `crafted`) and the symbol pattern, with their sticker documents.
  - `backdrop` (`{ name, rarity, centerColor, edgeColor, patternColor, textColor }`): the background; colors are `0xRRGGBB` numbers.
  - `rarity` of those: per mille (`number`, 15 = 1.5% of the collection) or a level `'uncommon' | 'rare' | 'epic' | 'legendary'`, `null` when unknown.
  - `originalDetails` (`{ sender, recipient, date, message } | null`): who gave it to whom, kept on upgrade; ids are marked ids.
  - `attributes` (`tl.TypeStarGiftAttribute[]`): all attributes as TL objects.
  - `sticker` (`tl.TypeDocument | null`): the sticker to show (a unique gift's model).
  - `stars` (`bigint | null`): a regular gift's price in stars.
  - `convertStars` (`bigint | null`): stars you get by converting it.
  - `upgradeStars` (`bigint | null`): the upgrade price, `null` when it can't be upgraded.
  - `resaleStars` (`bigint | null`): a unique gift's resale price in stars while it's on sale.
  - `limited`, `soldOut` (`boolean`): a limited edition, and whether it's sold out.
  - `availability` (`{ total, remains, issued } | null`): a limited gift's total and remaining count, or a unique gift's total and issued count.
  - `value` (`{ amount, currency, usd } | null`): a unique gift's estimated value in the smallest currency units (see `tg.gifts.value` for details).
  - `raw` (`tl.TypeStarGift`): the TL object.

Example:

```ts
const gift = await tg.gifts.get('PlushPepe-1')
if (gift.backdrop) tg.toast(`${gift.model?.name} on ${gift.backdrop.name} (#${gift.backdrop.centerColor.toString(16)})`)
```

### type SavedGift

```ts
export interface SavedGift extends Gift {
  input: tl.TypeInputSavedStarGift | null
  from: bigint | null
  fromName: string | null
  date: number
  message: TextWithEntities | null
  visible: boolean
  pinned: boolean
  nameHidden: boolean
  canUpgrade: boolean
  upgradePrepaid: boolean
  canConvert: boolean
  canTransfer: boolean
  transferStars: bigint | null
  canTransferAt: number | null
  canResellAt: number | null
  saved: tl.RawSavedStarGift
}
```

a gift on a profile, from `tg.gifts.list`: the `Gift` plus what belongs to this copy.

- **fields:**
  - `input` (`tl.TypeInputSavedStarGift | null`): what the actions send for it; `null` on another user's profile.
  - `from`, `fromName` (`bigint | null`, `string | null`): the sender's marked id and name; `null` when anonymous.
  - `date` (`number`): when it was received, in unix seconds.
  - `message` (`TextWithEntities | null`): the sender's message.
  - `visible` (`boolean`): shown on the profile.
  - `pinned` (`boolean`): pinned at the top.
  - `nameHidden` (`boolean`): the sender asked to hide their name from others.
  - `canUpgrade`, `upgradePrepaid` (`boolean`): it can be upgraded, and the sender already paid for that.
  - `canConvert` (`boolean`): it can still be converted to `convertStars` stars.
  - `canTransfer` (`boolean`): a unique gift of yours you can transfer now.
  - `transferStars` (`bigint | null`): what a transfer costs, `null` when it's free.
  - `canTransferAt`, `canResellAt` (`number | null`): unix seconds from which transfer and resale are allowed.
  - `saved` (`tl.RawSavedStarGift`): the TL object; `raw` is still the gift itself.
  - `convertStars` here is this copy's value (it can differ from the catalog's).

Example:

```ts
const { gifts } = await tg.gifts.list()
const fromFriends = gifts.filter((gift) => gift.from !== null).map((gift) => `${gift.fromName}: ${gift.message?.text ?? ''}`)
```

### type GiftLike

```ts
export type GiftLike = SavedGift | Gift | string | tl.TypeInputSavedStarGift
```

what the actions accept as a gift.

- **fields:**
  - `SavedGift`: its `input` is used (the best choice: it works for regular gifts too).
  - `Gift`: a unique gift, by its slug.
  - `string`: a unique gift's slug or `t.me/nft/` link.
  - `tl.TypeInputSavedStarGift`: `inputSavedStarGiftUser` (by the gift message id), `inputSavedStarGiftChat` (a channel's gift) or `inputSavedStarGiftSlug`.

Example:

```ts
await tg.gifts.setVisible({ _: 'inputSavedStarGiftSlug', slug: 'PlushPepe-1' }, true)
```

### type SavedGiftsPage

```ts
export interface SavedGiftsPage {
  gifts: SavedGift[]
  count: number
  nextOffset: string | null
}
```

one page of `tg.gifts.list`.

- **fields:**
  - `gifts` (`SavedGift[]`): this page.
  - `count` (`number`): how many gifts the profile has in total.
  - `nextOffset` (`string | null`): pass it as `options.offset` for the next page; `null` on the last one.

Example:

```ts
const { count } = await tg.gifts.list('me', { limit: 1 })
```

### type GiftValueInfo

```ts
export interface GiftValueInfo {
  currency: string
  value: bigint
  isAverage: boolean
  lastSaleOnFragment: boolean
  initialSaleDate: number
  initialSaleStars: bigint
  initialSalePrice: bigint
  lastSaleDate: number | null
  lastSalePrice: bigint | null
  floorPrice: bigint | null
  raw: tl.payments.RawUniqueStarGiftValueInfo
}
```

from `tg.gifts.value`. prices are in the smallest units of `currency`.

- **fields:**
  - `currency` (`string`): the currency code, e.g. `'USD'`.
  - `value` (`bigint`): the estimated value; `isAverage` when it's the average of the collection.
  - `lastSaleOnFragment` (`boolean`): the last sale happened on Fragment.
  - `initialSaleDate`, `initialSaleStars`, `initialSalePrice`: when the regular gift was first sold, for how many stars, and that in `currency`.
  - `lastSaleDate`, `lastSalePrice` (`number | null`, `bigint | null`): the last resale.
  - `floorPrice` (`bigint | null`): the cheapest gift of the collection on sale.
  - `raw`: the TL object.

Example:

```ts
const info = await tg.gifts.value('PlushPepe-1')
if (info.floorPrice !== null && info.value < info.floorPrice) console.log('worth less than the floor')
```

### type GiftActionResult

```ts
export interface GiftActionResult {
  stars: bigint
  gift: Gift | null
  updates: tl.TypeUpdates | null
}
```

what `transfer` and `upgrade` resolve with.

- **fields:**
  - `stars` (`bigint`): stars spent from your balance, `0n` when it was free.
  - `gift` (`Gift | null`): the unique gift from the server's answer (the upgraded gift), when there is one.
  - `updates` (`tl.TypeUpdates | null`): the server's updates, already applied to tele.

Example:

```ts
const { stars } = await tg.gifts.transfer('PlushPepe-1', '@friend')
if (stars > 0n) tg.toast(`the transfer cost ${stars} stars`)
```

### tg.stars

```ts
readonly stars: Stars
```

your stars: the balance and its history.

- **grant:** `account.read(gifts)`.

Example:

```ts
tg.toast(`${(await tg.stars.balance()).stars} ⭐`)
```

### type Stars

```ts
export interface Stars {
  balance(): Promise<StarsBalance>
  history(options?: { limit?: number, offset?: string }): Promise<StarsHistoryPage>
}
```

the type of `tg.stars`.

- **fields:**
  - `balance` (`() => Promise<StarsBalance>`): the current balance.
  - `history` (`(options?) => Promise<StarsHistoryPage>`): transactions, newest first.

Example:

```ts
const stars: Stars = tg.stars
```

### tg.stars.balance()

```ts
balance(): Promise<StarsBalance>

export interface StarsBalance {
  stars: bigint
  nanos: number
  raw: tl.payments.RawStarsStatus
}
```

reads your stars balance (`payments.getStarsStatus`).

- **grant:** `account.read(gifts)`.
- **returns:** `Promise<StarsBalance>`: `{ stars, nanos, raw }`; `stars` is the whole stars (`bigint`), `nanos` the fraction in billionths, `raw` the `payments.starsStatus` (with your subscriptions and the first page of history).
- **throws:** rejects with `TeleError` `not-granted` without the grant; `RpcError`.

Example:

```ts
const { stars } = await tg.stars.balance()
if (stars < 100n) tg.ui.notice('fewer than 100 stars left')
```

### tg.stars.history(options?)

```ts
history(options?: { limit?: number, offset?: string }): Promise<StarsHistoryPage>

export interface StarsHistoryPage {
  transactions: StarsTransaction[]
  nextOffset: string | null
}
```

reads one page of your stars transactions, newest first (`payments.getStarsTransactions`).

- **grant:** `account.read(gifts)`.
- **parameters:**
  - `options.limit` (`number`, optional): transactions per page, 1 to 100; default 50.
  - `options.offset` (`string`, optional): the `nextOffset` of the previous page.
- **returns:** `Promise<StarsHistoryPage>`: `{ transactions: StarsTransaction[], nextOffset: string | null }`.
- **throws:** rejects with `TeleError` `not-granted` without the grant; `TypeError` for a bad `limit` or `offset`; `RpcError`.

Example:

```ts
const { transactions } = await tg.stars.history({ limit: 20 })
const spent = transactions.filter((entry) => entry.stars < 0n).reduce((sum, entry) => sum - entry.stars, 0n)
console.log(`spent ${spent} stars recently`)
```

### type StarsTransaction

```ts
export interface StarsTransaction {
  id: string
  stars: bigint
  nanos: number
  date: number
  source: StarsSource
  peer: bigint | null
  peerName: string | null
  title: string | null
  description: string | null
  refund: boolean
  pending: boolean
  failed: boolean
  gift: Gift | null
  raw: tl.RawStarsTransaction
}

export type StarsSource =
  | 'peer'
  | 'appStore'
  | 'playMarket'
  | 'premiumBot'
  | 'fragment'
  | 'ads'
  | 'api'
  | 'unsupported'
```

one entry of `tg.stars.history`.

- **fields:**
  - `id` (`string`): the transaction id.
  - `stars`, `nanos` (`bigint`, `number`): the amount, negative when stars left your balance.
  - `date` (`number`): unix seconds.
  - `source` (`StarsSource`): `'peer'` (a user, bot or channel), `'appStore'`, `'playMarket'`, `'premiumBot'`, `'fragment'`, `'ads'`, `'api'` or `'unsupported'`.
  - `peer`, `peerName` (`bigint | null`, `string | null`): the other side for `'peer'`, as a marked id and its name.
  - `title`, `description` (`string | null`): the bot's product, when there is one.
  - `refund`, `pending`, `failed` (`boolean`): the transaction's state.
  - `gift` (`Gift | null`): the gift it was about (bought, converted, upgraded, transferred, resold).
  - `raw` (`tl.RawStarsTransaction`): the TL object, with every other flag.

Example:

```ts
const { transactions } = await tg.stars.history()
for (const entry of transactions.filter((item) => item.gift)) console.log(entry.stars, entry.gift?.title)
```

## local messages and decorations

scripts can put messages into chats that exist only in this tele, and change how real messages look, without touching the server. both disappear when the script stops (persisted local messages come back when it starts again). both need the [`display`](#grant-display) grant: `display(local)` for local messages, `display(messages)` for decorations.

### tg.addLocalMessage(chat, options?)

```ts
addLocalMessage(chat: InputPeerLike, options?: LocalMessageOptions): Promise<LocalMessage>
```

adds a local ("ghost") message to a chat: a real-looking message or service line, from anyone, with any media, that only this tele shows.

- **grant:** `display(local)`. resolving a marked id, a `Peer` or a username (for `chat` or `from`) needs `account.read(peers)` too; input peers, `PeerInfo`s, `Message`s and `'me'` don't.
- **parameters:**
  - `chat` (`InputPeerLike`): the chat to put it in.
  - `options` (`LocalMessageOptions`, optional): text, author, date, reply, media, action, opacity, persistence and raw tl fields.
- **returns:** the `LocalMessage`.
- **throws:** `TypeError`: `local message: <path>: <problem>` for fields that don't encode (`raw: { date: 'soon' }`), `a local message can't be messageEmpty`, `the message has no chat`, `opacity is a number from 0 to 1` (a non-number opacity), `persisted local messages are over the 16 MB quota`; the peer errors of `InputPeerLike`; `TeleError` `not-granted`: `tg.addLocalMessage needs the grant 'display(local)'`. all of these reject the promise; the grant is checked after the chat and `from` are resolved.
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

- **grant:** `display(local)`; resolving a new `from` needs `account.read(peers)` as in `addLocalMessage`.
- **parameters:**
  - `changes`: any `LocalMessageOptions` except `persist`; `replyTo: null` removes the reply, `opacity` changes the opacity.
- **returns:** the same `LocalMessage`, updated.
- **throws:** `TypeError` as `addLocalMessage`; `TypeError: this local message was removed`; `TeleError` `not-granted`: `localMessage.edit needs the grant 'display(local)'`. all of these reject.
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

changes how real messages look in this tele: shown text, a footer, opacity, hiding, a badge, buttons under them. the decorator decides per message.

- **grant:** `display(messages)` and `account.read(messages)`.
- **parameters:**
  - `decorator` (`(message) => MessageDecoration | null | void`, may be async): gets each message as a `Message`; returns its decoration, or `null` / nothing for none.
- **returns:** a `Disposer` that removes this decorator's decorations everywhere.
- **throws:** `TeleError` `not-granted`: `tg.decorateMessages needs the grant 'display(messages)'` (checked first), then `TypeError: tg.decorateMessages(function)`, then `TeleError` `not-granted`: `tg.decorateMessages needs the grant 'account.read(messages)'`. all thrown synchronously.
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

- **grant:** `display(messages)` (resolving marked ids and usernames needs `account.read(peers)` too).
- **parameters:**
  - `peer` (`InputPeerLike`): the chat.
  - `id` (`number`): the message id.
  - `decoration` (`MessageDecoration | null`): the decoration; `null` removes this script's explicit decoration of that message.
- **returns:** a promise of a `Disposer` that removes it.
- **throws:** `TypeError: needs a chat and a message id`; `TypeError: tg.decorateMessage: <problem>` for a bad decoration (`a decoration is an object`, `text is a string or { text, entities }`, `footer.entities are wrong: …`, `opacity is a number from 0 to 1`, `hidden is a boolean`, `badge is a string`, and the `buttons` problems listed under [type MessageDecoration](#type-messagedecoration)); the peer errors of `InputPeerLike`; `TeleError` `not-granted`: `tg.decorateMessage needs the grant 'display(messages)'`. all of these reject the promise.
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
  buttons?: MessageDecorationButton[][]
}
```

how a message should look. every field is optional; missing ones keep the real look.

- **grant:** `display(messages)`, for `tg.decorateMessages` and `tg.decorateMessage`.
- **fields:**
  - `text` (`InputText`, optional): shown instead of the real text in the bubble; entities, `md` and `html` work.
  - `footer` (`InputText`, optional): added under the text as a quote block. it's part of the bubble's text, so selecting all text selects it too.
  - `opacity` (`number`, optional): 0..1, multiplied with a local message's own opacity.
  - `hidden` (`boolean`, optional): the message leaves the chat view; it's still there for the server and for search.
  - `badge` (`string`, optional): a short text shown before the time, after a channel signature.
  - `buttons` (`MessageDecorationButton[][]`, optional): rows of buttons drawn under the bubble like a bot's inline keyboard, after the message's real inline keyboard. up to 8 rows of 1 to 8 buttons; `[]` shows no script rows (it hides the rows of an earlier layer).
- **throws:** a bad `buttons` value is a `TypeError` from `tg.decorateMessage` (`tg.decorateMessage: buttons is an array of up to 8 rows`, `buttons[i] is an array of 1 to 8 buttons`, `buttons[i][j] is { text, onClick, style? }`, `buttons[i][j].text is a non-empty string`, `buttons[i][j].onClick is a function`, `buttons[i][j].style is 'default', 'primary' or 'danger'`) and a fault in `tg.decorateMessages`.
- **notes:** decorations live in layers (each decorator, plus each script's explicit ones); later layers win per field, so `buttons` of a later layer replace the rows of an earlier one. disposing, `null`, or stopping the script removes a layer and the real look comes back.

Example:

```ts
const look: MessageDecoration = { footer: md`__translated from german__`, badge: 'de→en' }
```

### type MessageDecorationButton

```ts
export interface MessageDecorationButton {
  text: string
  onClick(context: { chatId: bigint, messageId: number }): unknown
  style?: 'default' | 'primary' | 'danger'
}
```

one button of `MessageDecoration.buttons`. it lives only in this tele: nothing is sent to telegram, no bot gets a callback and no text is sent when it's clicked.

- **grant:** `display(messages)` (the decoration's).
- **fields:**
  - `text` (`string`): the label, one line, plain text (emoji work); cut with an ellipsis when the row is narrow.
  - `onClick` (`(context) => unknown`, may be async): called on a left click with the message's `chatId` (marked id) and `messageId`.
  - `style` (`'default' | 'primary' | 'danger'`, optional): the look of a bot button: `'default'` (the usual translucent one), `'primary'` (accent blue) or `'danger'` (red).
- **notes:**
  - a message with a real bot keyboard keeps it working; the script rows come after the bot's rows.
  - the rows follow the decoration: server edits of the message keep them (`decorateMessage` keeps its decoration, a decorator runs again), and disposing it, `decorateMessage(peer, id, null)` or stopping the script removes them.
  - `onClick` runs with the listener budget (200 ms for the synchronous part); a throw is a fault (logged, counts toward the switch-off), an async `onClick`'s rejection is an unhandled rejection (logged, not counted).
  - the function stays alive while the decoration does; each run of a decorator makes new buttons and frees the old ones.
  - hidden in tele's screenshots when they hide inline buttons; not shown in the admin log.

Example:

```ts
const sent = await tg.sendMessage('me', 'deploy v2.4?')
await tg.decorateMessage('me', sent.id, {
  buttons: [[
    { text: '✅ deploy', style: 'primary', onClick: () => tg.toast('deploying') },
    { text: '✖ cancel', style: 'danger', onClick: ({ messageId }) => tg.decorateMessage('me', messageId, null) },
  ]],
})
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

tele's own state, read without network: the chat list as tele has it, unread counters, folders, drafts, tele's settings, and tele's own features: ignored users, ghost mode, local names, bookmarks, local pins and folders, hidden words, edit history and kept deleted messages.

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

tele's own features: ignored users, per-chat ghost mode, local names, bookmarks, local pins, folders, hidden words, edit history and kept deleted messages.

- **grant:** `account.read(peers)` to read ignored users, ghost modes and local names; `account.read(messages)` for bookmarks, edit history and kept messages; `account.read(dialogs)` for pins; `options` for every change. each member's item names its grant.
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

export interface TeleFeatures {
  readonly bookmarks: {
    list(): TeleBookmark[]
    add(message: Message, name?: string): Promise<void>
    add(chat: InputPeerLike, messageId: number, name?: string): Promise<void>
    remove(message: Message): Promise<boolean>
    remove(chat: InputPeerLike, messageId: number): Promise<boolean>
    onChange(callback: () => unknown): Disposer
  }
  readonly pins: {
    list(folder?: number): bigint[]
    pin(chat: InputPeerLike, folder?: number): Promise<void>
    unpin(chat: InputPeerLike, folder?: number): Promise<void>
  }
  readonly folders: {
    list(): TeleFolder[]
    create(folder: TeleFolderChanges & { title: string }): Promise<number>
    edit(id: number, changes: TeleFolderChanges): Promise<void>
    delete(id: number): Promise<void>
    reorder(ids: number[]): Promise<void>
  }
  readonly hiddenWords: {
    list(chat?: InputPeerLike): Promise<string[]>
    add(rule: string, chat?: InputPeerLike): Promise<boolean>
    remove(rule: string, chat?: InputPeerLike): Promise<boolean>
  }
  editHistory(message: Message): Promise<TeleEditVersion[]>
  editHistory(chat: InputPeerLike, messageId: number): Promise<TeleEditVersion[]>
  readonly deleted: {
    list(chat: InputPeerLike): Promise<Message[]>
    onKept(callback: (kept: TeleKeptMessage) => unknown): Disposer
    interceptKeep(
      interceptor: (
        kept: TeleKeptMessage,
      ) => TeleKeepVerdict | void | Promise<TeleKeepVerdict | void>,
    ): Disposer
  }
}
```

the type of `tg.tele`. the second block is interface merging: it comes with the bookmarks, pins, folders, hidden words, edit history and kept messages features.

- **fields:**
  - `ignored` (`{ list, set }`): ignored users.
  - `ghost` (`{ get, set, list }`): per-chat ghost mode.
  - `localNames` (`{ list, set }`): your local names for users.
  - `bookmarks` (`{ list, add, remove, onChange }`): messages bookmarked in tele.
  - `pins` (`{ list, pin, unpin }`): chats tele pins locally, past Telegram's pin limit.
  - `folders` (`{ list, create, edit, delete, reorder }`): chat folders, tele's local ones included.
  - `hiddenWords` (`{ list, add, remove }`): words that hide messages, globally or in one chat.
  - `editHistory` (`(message) => Promise<TeleEditVersion[]>`): the earlier versions of an edited message.
  - `deleted` (`{ list, onKept, interceptKeep }`): deleted messages tele kept.

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

### tg.tele.bookmarks.list()

```ts
list(): TeleBookmark[]
```

every message you bookmarked in tele (the message menu's "bookmark"), in every chat of this account.

- **grant:** `account.read(messages)`.
- **returns:** `TeleBookmark[]`, fresh each call; empty when bookmarks are off in tele's settings (`tele-bookmarks`).
- **throws:** `TeleError` `not-granted`: `tg.tele.bookmarks.list needs the grant 'account.read(messages)'`.

Example:

```ts
for (const bookmark of tg.tele.bookmarks.list()) console.log(bookmark.chatId, bookmark.messageId, bookmark.name || bookmark.preview)
```

### type TeleBookmark

```ts
export interface TeleBookmark {
  chatId: bigint
  messageId: number
  topicId: number | null
  name: string
  preview: string
  date: number
}
```

one bookmark.

- **fields:**
  - `chatId` (`bigint`): the chat's marked id.
  - `messageId` (`number`): the bookmarked message.
  - `topicId` (`number | null`): the forum topic it's in, `null` outside forums.
  - `name` (`string`): the name you gave it, `''` when unnamed.
  - `preview` (`string`): the message text tele saved when you bookmarked it (one line, up to 256 characters).
  - `date` (`number`): when you bookmarked it, unix seconds.

Example:

```ts
const recent = tg.tele.bookmarks.list().filter((bookmark: TeleBookmark) => bookmark.date > Date.now() / 1000 - 86_400)
```

### tg.tele.bookmarks.add(message, name?)

```ts
add(message: Message, name?: string): Promise<void>
add(chat: InputPeerLike, messageId: number, name?: string): Promise<void>
```

bookmarks a message, like the message menu does; bookmarking it again replaces the name.

- **grant:** `options`.
- **parameters:**
  - `message` (`Message`): the message; or `chat` (`InputPeerLike`) and `messageId` (`number`).
  - `name` (`string`, optional): a name shown in tele's bookmark list instead of the preview.
- **returns:** resolves when the bookmark is saved. tele loads the message from the server when it isn't loaded.
- **throws:** `TeleError` `not-granted`: `tg.tele.bookmarks.add needs the grant 'options'`; `TeleError` `unsupported`: `tg.tele.bookmarks.add: bookmarks are off in tele's settings` and `tg.tele.bookmarks.add: this message can't be bookmarked` (local, scheduled or unsent messages); `TeleError` `not-found`: `tg.tele.bookmarks.add: no message 42 in that chat`; `TypeError`: `tg.tele.bookmarks.add(message) or tg.tele.bookmarks.add(chat, messageId)`, `tg.tele.bookmarks.add: name is a string`, `tg.tele.bookmarks.add needs a chat in tele's cache and a message id`; the errors of `InputPeerLike`.

Example:

```ts
tg.onNewMessage(async (message) => {
  if (message.text.includes('#todo')) await tg.tele.bookmarks.add(message, 'todo')
})
```

### tg.tele.bookmarks.remove(message)

```ts
remove(message: Message): Promise<boolean>
remove(chat: InputPeerLike, messageId: number): Promise<boolean>
```

removes a bookmark.

- **grant:** `options`.
- **parameters:**
  - `message` (`Message`): the message; or `chat` (`InputPeerLike`) and `messageId` (`number`).
- **returns:** `true` when there was a bookmark to remove.
- **throws:** `TeleError` `not-granted`; `TypeError`: `tg.tele.bookmarks.remove(message) or tg.tele.bookmarks.remove(chat, messageId)`, `tg.tele.bookmarks.remove needs a chat and a message id`; the errors of `InputPeerLike`.

Example:

```ts
for (const bookmark of tg.tele.bookmarks.list()) {
  if (bookmark.date < Date.now() / 1000 - 30 * 86_400) await tg.tele.bookmarks.remove(bookmark.chatId, bookmark.messageId)
}
```

### tg.tele.bookmarks.onChange(callback)

```ts
onChange(callback: () => unknown): Disposer
```

calls `callback` after bookmarks change: added, renamed, removed (by you, a script, or a deleted message), or the feature turned on or off.

- **grant:** none (read the list with `list()`, which needs `account.read(messages)`).
- **parameters:**
  - `callback` (`() => unknown`): called with no arguments, after the change.
- **returns:** a `Disposer` that stops it; it also stops with the script.
- **throws:** `TypeError: tg.tele.bookmarks.onChange(callback)`.

Example:

```ts
tg.tele.bookmarks.onChange(() => console.log(tg.tele.bookmarks.list().length, 'bookmarks'))
```

### tg.tele.pins.list(folder?)

```ts
list(folder?: number): bigint[]
```

the chats tele pins locally (past Telegram's pin limit, shown with a hollow pin) in the main list and the archive, or in one chat folder.

- **grant:** `account.read(dialogs)`.
- **parameters:**
  - `folder` (`number`, optional): a folder id from `tg.tele.folders.list()`; `0` or nothing for the main list and the archive.
- **returns:** the chats' marked ids, in pin order; empty when local pins are off in tele's settings (`tele-local-pins`).
- **throws:** `TeleError` `not-granted`: `tg.tele.pins.list needs the grant 'account.read(dialogs)'`; `TypeError: tg.tele.pins.list: folder is a folder id from tg.tele.folders.list() or 0`.
- **notes:** server pins aren't listed: they're in `tg.local.dialogs()` (`pinned`).

Example:

```ts
console.log(tg.tele.pins.list().length, 'chats pinned locally')
```

### tg.tele.pins.pin(chat, folder?)

```ts
pin(chat: InputPeerLike, folder?: number): Promise<void>
```

pins a chat locally (only on this device, any number of chats), in the main list (or the archive, for an archived chat) or in a chat folder.

- **grant:** `options`.
- **parameters:**
  - `chat` (`InputPeerLike`): a chat in tele's cache.
  - `folder` (`number`, optional): a folder id; `0` or nothing for the main list.
- **returns:** resolves when pinned; the new pin goes last.
- **throws:** `TeleError` `not-granted`: `tg.tele.pins.pin needs the grant 'options'`; `TeleError` `unsupported`: `tg.tele.pins.pin: local pins are off in tele's settings`, `tg.tele.pins.pin: tele can't pin this chat in that list` (tele doesn't know its list yet); `TypeError`: `tg.tele.pins.pin needs a chat in tele's cache`, `tg.tele.pins.pin: folder is a folder id from tg.tele.folders.list() or 0`; the errors of `InputPeerLike`.

Example:

```ts
await tg.tele.pins.pin('@durov')
```

### tg.tele.pins.unpin(chat, folder?)

```ts
unpin(chat: InputPeerLike, folder?: number): Promise<void>
```

removes a local pin. a chat also pinned on the server stays pinned there.

- **grant:** `options`.
- **parameters:**
  - `chat` (`InputPeerLike`): a chat in tele's cache.
  - `folder` (`number`, optional): the folder id the pin is in; `0` or nothing for the main list.
- **returns:** resolves when done; unpinning a chat that isn't pinned locally does nothing.
- **throws:** the errors of `pin`, with `tg.tele.pins.unpin` in the messages.

Example:

```ts
for (const chatId of tg.tele.pins.list()) await tg.tele.pins.unpin(chatId)
```

### tg.tele.folders.list()

```ts
list(): TeleFolder[]
```

the chat folders with their rules, in tele's order, without "all chats". tele's local folders (past Telegram's folder limit) are included.

- **grant:** none; the chats in the rules (`include`, `exclude`, `pinned`) only with `account.read(dialogs)`.
- **returns:** `TeleFolder[]`, fresh each call.

Example:

```ts
const empty = tg.tele.folders.list().filter((folder) => folder.include?.length === 0 && !Object.values(folder.flags).some(Boolean))
```

### type TeleFolder

```ts
export interface TeleFolder {
  id: number
  title: string
  emoji: string
  color: number | null
  flags: TeleFolderFlags
  shared: boolean
  local: boolean
  include?: bigint[]
  exclude?: bigint[]
  pinned?: bigint[]
}
```

one chat folder.

- **fields:**
  - `id` (`number`): the folder id (`tg.local.dialogs({ folder: id })` lists its chats).
  - `title` (`string`): the name (custom emoji in it come back as their text).
  - `emoji` (`string`): its icon emoji, or `''`.
  - `color` (`number | null`): its tag color index, `null` without one.
  - `flags` (`TeleFolderFlags`): which kinds of chats it takes in and leaves out.
  - `shared` (`boolean`): a shared folder (a chat folder link you joined or made).
  - `local` (`boolean`): one of tele's local folders, kept only on this device.
  - `include` (`bigint[]`, optional): chats always in it, besides the pinned ones; only with `account.read(dialogs)`.
  - `exclude` (`bigint[]`, optional): chats never in it; only with `account.read(dialogs)`.
  - `pinned` (`bigint[]`, optional): chats pinned in it, in order (they're in the folder too); only with `account.read(dialogs)`.

Example:

```ts
const work = tg.tele.folders.list().find((folder: TeleFolder) => folder.title === 'work')
```

### type TeleFolderFlags

```ts
export interface TeleFolderFlags {
  contacts: boolean
  nonContacts: boolean
  groups: boolean
  channels: boolean
  bots: boolean
  excludeMuted: boolean
  excludeRead: boolean
  excludeArchived: boolean
}
```

a folder's rules by chat kind, like the folder editor's "included chats" types and "exclude" toggles.

- **fields:**
  - `contacts`, `nonContacts`, `groups`, `channels`, `bots` (`boolean`): take in every chat of that kind.
  - `excludeMuted`, `excludeRead`, `excludeArchived` (`boolean`): leave out muted, read or archived chats.

Example:

```ts
const flags: Partial<TeleFolderFlags> = { groups: true, excludeMuted: true }
```

### tg.tele.folders.create(folder)

```ts
create(folder: TeleFolderChanges & { title: string }): Promise<number>
```

creates a chat folder, saved to your account like the folder editor does (a local tele folder when you're at Telegram's folder limit and tele's local folders are on).

- **grant:** `options`.
- **parameters:**
  - `folder` (`TeleFolderChanges & { title: string }`): the new folder; `title` is required, everything else defaults to empty.
- **returns:** the new folder's id, once the server saved it. the folder goes last.
- **throws:** `TeleError` `not-granted`: `tg.tele.folders.create needs the grant 'options'`; `TypeError`: `tg.tele.folders.create: the folder is an object`, `tg.tele.folders.create: a new folder needs a title`, `tg.tele.folders.create: title can't be empty`, `tg.tele.folders.create: title is a string`, `tg.tele.folders.create: emoji is a string`, `tg.tele.folders.create: color is a color index (0 to 255) or null`, `tg.tele.folders.create: flags is an object of booleans`, `tg.tele.folders.create: flags.groups is a boolean`, `tg.tele.folders.create: include is an array of chats` / `include is an array of chats in tele's cache` (same for `exclude` and `pinned`); `TeleError` `forbidden` (or `quota-exceeded` for `..._TOO_MUCH` and flood waits): `tg.tele.folders.create: the server refused: FILTER_INCLUDE_EMPTY`, and the folder is removed again; the errors of `InputPeerLike`.
- **notes:** the server wants at least one chat or kind of chat in a folder, and a title of up to 12 characters.

Example:

```ts
const id = await tg.tele.folders.create({ title: 'bots', emoji: '🤖', flags: { bots: true } })
```

### type TeleFolderChanges

```ts
export interface TeleFolderChanges {
  title?: string
  emoji?: string
  color?: number | null
  flags?: Partial<TeleFolderFlags>
  include?: InputPeerLike[]
  exclude?: InputPeerLike[]
  pinned?: InputPeerLike[]
}
```

the parts of a folder to set; a missing field keeps its value (or is empty in a new folder).

- **fields:**
  - `title` (`string`, optional): the name.
  - `emoji` (`string`, optional): the icon emoji, `''` for none.
  - `color` (`number | null`, optional): the tag color index, `null` for none.
  - `flags` (`Partial<TeleFolderFlags>`, optional): only the flags given change.
  - `include` (`InputPeerLike[]`, optional): replaces the chats always in it.
  - `exclude` (`InputPeerLike[]`, optional): replaces the chats never in it.
  - `pinned` (`InputPeerLike[]`, optional): replaces the pinned chats, in order (they're included too).
- **notes:** in shared folders the server ignores `flags` and `exclude`.

Example:

```ts
const changes: TeleFolderChanges = { exclude: ['@spam_channel'], flags: { excludeRead: true } }
```

### tg.tele.folders.edit(id, changes)

```ts
edit(id: number, changes: TeleFolderChanges): Promise<void>
```

changes a folder, like saving it in the folder editor: tele shows the change at once and puts the old folder back if the server refuses.

- **grant:** `options`.
- **parameters:**
  - `id` (`number`): a folder id from `list()`.
  - `changes` (`TeleFolderChanges`): what to change.
- **returns:** resolves when saved.
- **throws:** the `TypeError`s and server refusals of `create`, with `tg.tele.folders.edit` in the messages; `TypeError: tg.tele.folders.edit: id is a folder id from tg.tele.folders.list()`; `TeleError` `not-found`: `tg.tele.folders.edit: no folder 7`; `TeleError` `unsupported`: `tg.tele.folders.edit: tele's unsorted folder can't be edited`.

Example:

```ts
const work = tg.tele.folders.list().find((folder) => folder.title === 'work')
if (work) await tg.tele.folders.edit(work.id, { include: [...(work.include ?? []), '@newcolleague'] })
```

### tg.tele.folders.delete(id)

```ts
delete(id: number): Promise<void>
```

deletes a folder (the chats stay). deleting a shared folder keeps its chats too.

- **grant:** `options`.
- **parameters:**
  - `id` (`number`): a folder id from `list()`.
- **returns:** resolves when the server deleted it.
- **throws:** `TeleError` `not-granted`; `TypeError: tg.tele.folders.delete: id is a folder id from tg.tele.folders.list()`; `TeleError` `not-found`: `tg.tele.folders.delete: no folder 7`; `TeleError` `unsupported`: `tg.tele.folders.delete: tele's unsorted folder is a setting`; `TeleError` `forbidden`: `tg.tele.folders.delete: the server refused: ...` (the folder comes back).

Example:

```ts
const id = await tg.tele.folders.create({ title: 'temp', flags: { groups: true } })
await tg.tele.folders.delete(id)
```

### tg.tele.folders.reorder(ids)

```ts
reorder(ids: number[]): Promise<void>
```

puts the folders in this order, like dragging them in the folder settings.

- **grant:** `options`.
- **parameters:**
  - `ids` (`number[]`): every id from `list()` exactly once; add `0` to place "all chats" too (moving it needs Premium), otherwise it keeps its place.
- **returns:** resolves at once; tele saves the order in the background.
- **throws:** `TeleError` `not-granted`; `TypeError: tg.tele.folders.reorder needs every folder id from tg.tele.folders.list() exactly once`.

Example:

```ts
const sorted = tg.tele.folders.list().sort((a, b) => a.title.localeCompare(b.title)).map((folder) => folder.id)
await tg.tele.folders.reorder(sorted)
```

### tg.tele.hiddenWords.list(chat?)

```ts
list(chat?: InputPeerLike): Promise<string[]>
```

tele's hidden words: messages containing one of them are hidden (your own messages never are). the global list, or one chat's extra rules.

- **grant:** none.
- **parameters:**
  - `chat` (`InputPeerLike`, optional): a chat in tele's cache; its rules apply on top of the global ones.
- **returns:** the rules, one per entry: a word or phrase (matched anywhere, ignoring case), or a `/regex/` (`/regex/i` works too, matching always ignores case).
- **throws:** `TypeError: tg.tele.hiddenWords.list needs a chat in tele's cache`; the errors of `InputPeerLike`.

Example:

```ts
console.log(await tg.tele.hiddenWords.list())
```

### tg.tele.hiddenWords.add(rule, chat?)

```ts
add(rule: string, chat?: InputPeerLike): Promise<boolean>
```

adds a rule to the global list or to one chat's rules; matching messages hide at once.

- **grant:** `options`.
- **parameters:**
  - `rule` (`string`): one line: a word or phrase, or a `/regex/`; surrounding spaces are trimmed.
  - `chat` (`InputPeerLike`, optional): a chat in tele's cache, for a rule only there.
- **returns:** `true` when added, `false` when the rule was already there.
- **throws:** `TeleError` `not-granted`: `tg.tele.hiddenWords.add needs the grant 'options'`; `TypeError`: `tg.tele.hiddenWords.add(rule, chat?): rule is a string`, `tg.tele.hiddenWords.add: a rule is one line of text or a valid /regex/` (also for a regex that doesn't compile), `tg.tele.hiddenWords.add needs a chat in tele's cache`; the errors of `InputPeerLike`.

Example:

```ts
await tg.tele.hiddenWords.add('/\\bcrypto\\s+giveaway\\b/')
```

### tg.tele.hiddenWords.remove(rule, chat?)

```ts
remove(rule: string, chat?: InputPeerLike): Promise<boolean>
```

removes a rule (exactly as `list()` shows it).

- **grant:** `options`.
- **parameters:**
  - `rule` (`string`): the rule.
  - `chat` (`InputPeerLike`, optional): the chat whose rules to change; the global list without it.
- **returns:** `true` when removed, `false` when it wasn't there.
- **throws:** the errors of `add`, with `tg.tele.hiddenWords.remove` in the messages.

Example:

```ts
for (const rule of await tg.tele.hiddenWords.list()) if (rule.startsWith('/')) await tg.tele.hiddenWords.remove(rule)
```

### tg.tele.editHistory(message)

```ts
editHistory(message: Message): Promise<TeleEditVersion[]>
editHistory(chat: InputPeerLike, messageId: number): Promise<TeleEditVersion[]>
```

the versions of an edited message tele kept (the message menu's "edit history"), oldest first, the current one last.

- **grant:** `account.read(messages)`.
- **parameters:**
  - `message` (`Message`): the message; or `chat` (`InputPeerLike`) and `messageId` (`number`).
- **returns:** `TeleEditVersion[]`; empty when tele kept no edits of it, hasn't loaded it, or edit history is off in tele's settings (`tele-edit-history`).
- **throws:** `TeleError` `not-granted`: `tg.tele.editHistory needs the grant 'account.read(messages)'`; `TypeError`: `tg.tele.editHistory(message) or tg.tele.editHistory(chat, messageId)`, `tg.tele.editHistory needs a chat and a message id`; the errors of `InputPeerLike`.

Example:

```ts
tg.onMessageEdited(async (message) => {
  const versions = await tg.tele.editHistory(message)
  if (versions.length > 1) console.log('was:', versions[versions.length - 2].message.text)
})
```

### type TeleEditVersion

```ts
export interface TeleEditVersion {
  date: number
  original: boolean
  current: boolean
  message: Message
}
```

one version of an edited message.

- **fields:**
  - `date` (`number`): since when the message read like this, unix seconds.
  - `original` (`boolean`): the text before the first edit.
  - `current` (`boolean`): the text it has now.
  - `message` (`Message`): the message as it was: its id, chat, sender and date, this version's `text` and `entities`, and `editDate` (missing on the original). media isn't kept per version, so `media` is `null`.

Example:

```ts
const texts = (await tg.tele.editHistory('@channel', 42)).map((version: TeleEditVersion) => version.message.text)
```

### tg.tele.deleted.list(chat)

```ts
list(chat: InputPeerLike): Promise<Message[]>
```

the deleted messages tele kept in a chat ("keep deleted messages" in tele's settings), oldest first.

- **grant:** `account.read(messages)`.
- **parameters:**
  - `chat` (`InputPeerLike`): a chat in tele's cache.
- **returns:** `Message[]`: the full message when tele saw it arrive while scripts were running, otherwise its id, chat, sender, date, text and entities (no media); empty when keeping is off.
- **throws:** `TeleError` `not-granted`: `tg.tele.deleted.list needs the grant 'account.read(messages)'`; `TypeError: tg.tele.deleted.list needs a chat in tele's cache`; the errors of `InputPeerLike`.

Example:

```ts
const kept = await tg.tele.deleted.list('@friend')
console.log(kept.map((message) => message.text))
```

### tg.tele.deleted.onKept(callback)

```ts
onKept(callback: (kept: TeleKeptMessage) => unknown): Disposer
```

calls `callback` for every message tele keeps after it was deleted, a moment after it's kept.

- **grant:** `account.read(messages)`.
- **parameters:**
  - `callback` (`(kept: TeleKeptMessage) => unknown`): called once per message.
- **returns:** a `Disposer` that stops it; it also stops with the script.
- **throws:** `TeleError` `not-granted`: `tg.tele.deleted.onKept needs the grant 'account.read(messages)'`; `TypeError: tg.tele.deleted.onKept(callback)`.
- **notes:** `tg.onMessageDeleted` sees every deletion; this sees the ones tele kept (not in bots or Saved Messages unless tele's settings say so, not self-destructing ones).

Example:

```ts
tg.tele.deleted.onKept(({ message }) => tg.toast(`deleted: ${message.text.slice(0, 40)}`))
```

### tg.tele.deleted.interceptKeep(interceptor)

```ts
interceptKeep(
  interceptor: (
    kept: TeleKeptMessage,
  ) => TeleKeepVerdict | void | Promise<TeleKeepVerdict | void>,
): Disposer
```

lets the script decide which deleted messages tele keeps: `'discard'` removes a kept message (gone from the chat and from tele's store), `'keep'` or nothing keeps it.

- **grant:** `account.read(messages)` and `options`.
- **parameters:**
  - `interceptor` (`(kept) => TeleKeepVerdict | void | Promise<...>`): called once per kept message.
- **returns:** a `Disposer` that stops it; it also stops with the script.
- **throws:** `TeleError` `not-granted`: `tg.tele.deleted.interceptKeep needs the grant 'account.read(messages)'` or `... needs the grant 'options'`; `TypeError: tg.tele.deleted.interceptKeep(callback)`.
- **notes:** tele keeps the message first and asks right after, so a discarded message can flash for a moment. an answer after 2 seconds, an error or any other value keeps it. when several scripts intercept, one `'discard'` is enough. it can only drop what tele keeps: it can't keep a message tele's settings wouldn't.

Example:

```ts
tg.tele.deleted.interceptKeep(({ message }) => (message.mediaType === 'sticker' ? 'discard' : 'keep'))
```

### type TeleKeptMessage

```ts
export interface TeleKeptMessage {
  chatId: bigint
  own: boolean
  message: Message
}
```

a deleted message tele just kept.

- **fields:**
  - `chatId` (`bigint`): the chat's marked id.
  - `own` (`boolean`): you deleted it yourself (kept when "keep your own deleted messages" is on).
  - `message` (`Message`): the message, like `tg.tele.deleted.list` gives it.

Example:

```ts
tg.tele.deleted.onKept((kept: TeleKeptMessage) => { if (!kept.own) console.log(kept.chatId, kept.message.id) })
```

### type TeleKeepVerdict

```ts
export type TeleKeepVerdict = 'keep' | 'discard'
```

an `interceptKeep` answer.

- **fields:**
  - `'keep'`: keep the deleted message (also what no answer means).
  - `'discard'`: remove it for good.

Example:

```ts
const verdict: TeleKeepVerdict = 'discard'
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
  text(options: { id?: string, text: string } | string): UiElement
  image(options: {
    id?: string
    bytes: Uint8Array | ArrayBuffer
    height?: number
    subtitle?: string
    onClick?(): unknown
  }): UiElement
  progress(options: {
    id?: string
    text?: string
    value: number
    subtitle?: string
  }): UiElement
  peer(options: {
    id?: string
    peer: bigint | number | 'me' | PeerInfo
    text?: string
    subtitle?: string
    onClick?(): unknown
  }): UiElement
  settingsPage(options: { title?: string, items(): UiElement[] }): Page
  readonly widgets: Widgets
  registerMenuItem(options: { place: 'main' | 'tray', text: string, emoji?: string, icon?: MenuIcon, onClick(): unknown }): Disposer
  registerSettingsEntry(options: { title: string, emoji?: string, icon?: MenuIcon, page: Page, onClick?(): unknown }): Disposer
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

export interface Ui {
  webview(options: WebviewOptions): WebviewPanel
}

export interface Ui {
  openMedia(
    message: Message | { peer: InputPeerLike, id: number },
    options?: { index?: number },
  ): Promise<void>
  onMediaOpened(callback: (event: MediaViewerEvent) => unknown): Disposer
  registerMediaAction(options: MediaActionOptions): Disposer
  mediaViewer(): MediaViewerItem | null
}

export interface Ui {
  banner(options: BannerOptions): Disposer
  selection(): MessageSelection | null
  onSelectionChanged(callback: (selection: MessageSelection | null) => unknown): Disposer
}

export interface Ui {
  registerSearchProvider(provider: SearchProvider): Disposer
}

export interface Ui {
  registerStickerSet(options: PanelStickerSetOptions): Disposer
  registerGifSource(options: PanelGifSourceOptions): Disposer
  registerEmojiSet(options: PanelEmojiSetOptions): Disposer
}

export interface Ui {
  openWebApp(bot: InputPeerLike, options?: WebAppOptions): Promise<void>
  webApps(): WebAppInfo[]
  onWebAppEvent(callback: (event: WebAppEvent) => unknown): Disposer
}
```

`tg.ui` is the script's handle on tele's interface: boxes, settings pages and their rows, menu entries, navigation and file pickers. tele.d.ts declares it in several parts: the second adds navigation and files, the later ones come with the features that extend it.

- **grant:** none for most members; `tg.ui.widgets` needs `ui.read`, `ui.write` and `unsafe.automate`, see "the widget layer"; `webApps` and `onWebAppEvent` need `ui.read`.
- **notes:** every member is documented below under its own name. members that show something need a window showing this account; when there is none (typically a logged-in account that isn't the active one and has no separate window), they throw `TeleError` `unsupported` or quietly return `false`, as noted per member.
- **members:**
  - `toast`, `notice`, `dialog`, `prompt`, `chooser`: this section.
  - `settingsPage`, `header`, `separator`, `button`, `check`, `select`, `slider`, `input`, `item`, `color`, `keybind`, `text`, `image`, `progress`, `peer`, `openPage`, `openSection`, `registerSettingsEntry`, `openFile`, `saveFile`: "pages and settings".
  - `registerMenuItem`: "menus, buttons and commands".
  - `openChat`, `openProfile`, `openSettings`, `back`, `current`, `onChatOpened`, `banner`, `selection`, `onSelectionChanged`: "navigation and compose".
  - `webview`: "webviews".
  - `registerSearchProvider`: "search".
  - `registerStickerSet`, `registerGifSource`, `registerEmojiSet`: "sticker and gif panels".
  - `openMedia`, `onMediaOpened`, `registerMediaAction`, `mediaViewer`: "media viewer".
  - `openWebApp`, `webApps`, `onWebAppEvent`: "mini apps".
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
  readonly type: 'header' | 'button' | 'check' | 'select' | 'slider' | 'input' | 'separator' | 'item' | 'color' | 'keybind' | 'text' | 'image' | 'progress' | 'peer'
}
```

one row of a settings page, made by a row builder. it's a frozen copy of the options you passed plus `type`; tele reads it when the page renders.

- **fields:**
  - `type` (`'header' | 'button' | 'check' | 'select' | 'slider' | 'input' | 'separator' | 'item' | 'color' | 'keybind' | 'text' | 'image' | 'progress' | 'peer'`): which row it is. set by the builder, can't be overridden.
  - every option given to the builder, as given (`text`, `value`, `onChange`, ...).
- **notes:**
  - only rows returned from `items()` count; building a row doesn't show it.
  - every builder takes `id?: string`. tele doesn't use it; it's there for your own bookkeeping (finding a row in a list, keys in tests).
  - `subtitle` (on every row except `header`, `separator` and `text`) is a small grey line of text under the row.
  - the builders accept a plain string as a shorthand for `{ text }` (typed only for `header`, `separator` and `text`).

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

### tg.ui.text(options)

```ts
text(options: { id?: string, text: string } | string): UiElement
```

a paragraph of text on a page. it understands the composer's markdown (`**bold**`, `__italic__`, `` `code` ``, `~~strike~~`, `||spoiler||`) and links (`[label](https://example.com)` and bare urls), so a page can explain itself or point somewhere.

- **grant:** none.
- **parameters:**
  - `options` (`string`): the text; a string is the same as `{ text }`.
  - `options.id` (`string`, optional): your own name for the row.
  - `options.text` (`string`): the paragraph.
- **returns:** `UiElement` with `type: 'text'`.
- **notes:**
  - links open like any link in tele: through `tg.interceptLink` interceptors and tele's own handlers.
  - the paragraph wraps to the page's width; long text makes the page scroll.

Example:

```ts
tg.ui.text('this script mirrors your **saved messages** to [notion](https://notion.so). nothing leaves this computer otherwise.')
```

### tg.ui.image(options)

```ts
image(options: {
  id?: string
  bytes: Uint8Array | ArrayBuffer
  height?: number
  subtitle?: string
  onClick?(): unknown
}): UiElement
```

a picture on a page: png, jpeg, webp, bmp or gif (the first frame), scaled down to the page's width and to `height`, keeping its proportions, centred.

- **grant:** none.
- **parameters:**
  - `options.bytes` (`Uint8Array | ArrayBuffer`): the image file.
  - `options.height` (`number`, optional): the largest height in pixels at 100% interface scale (scaled with the interface); default 240.
  - `options.subtitle` (`string`, optional): a small line under the picture.
  - `options.onClick` (`() => unknown`, optional): runs when the picture is clicked.
- **returns:** `UiElement` with `type: 'image'`.
- **notes:**
  - bytes that aren't an image leave an empty row (no error).
  - pages re-render when `invalidate()` is called; a new `bytes` value replaces the picture in place.
  - there is no url form: download the picture with `fetch` (and its grant) and pass the bytes.

Example:

```ts
const response = await fetch('https://picsum.photos/600/300')
const photo = await response.bytes()
const page = tg.ui.settingsPage({
  title: 'photo of the day',
  items: () => [tg.ui.image({ bytes: photo, height: 180, onClick: () => tg.openUrl('https://picsum.photos') })],
})
```

### tg.ui.progress(options)

```ts
progress(options: {
  id?: string
  text?: string
  value: number
  subtitle?: string
}): UiElement
```

a progress bar with an optional label above and a small line under it.

- **grant:** none.
- **parameters:**
  - `options.text` (`string`, optional): the label above the bar.
  - `options.value` (`number`): how far along, from 0 to 1 (clamped); a negative value draws an empty track (unknown progress).
  - `options.subtitle` (`string`, optional): a small line under the bar, e.g. "12 of 40".
- **returns:** `UiElement` with `type: 'progress'`.
- **notes:**
  - call the page's `invalidate()` after changing the value: the bar updates in place without rebuilding the page.

Example:

```ts
let done = 0
const page = tg.ui.settingsPage({
  title: 'export',
  items: () => [tg.ui.progress({ text: 'exporting your chats', value: done / chats.length, subtitle: `${done} of ${chats.length}` })],
})
for (const chat of chats) {
  await exportChat(chat)
  done += 1
  page.invalidate()
}
```

### tg.ui.peer(options)

```ts
peer(options: {
  id?: string
  peer: bigint | number | 'me' | PeerInfo
  text?: string
  subtitle?: string
  onClick?(): unknown
}): UiElement
```

a row with a user's or chat's userpic and name, like the rows in tele's member lists.

- **grant:** none (only peers tele already has loaded are drawn with their picture and name).
- **parameters:**
  - `options.peer` (`bigint | number | 'me' | PeerInfo`): a marked id, `'me'`, or a `PeerInfo` from `tg.peers.get` / `tg.resolvePeer`.
  - `options.text` (`string`, optional): replaces the shown name.
  - `options.subtitle` (`string`, optional): the grey line under the name (a status, a count, a date).
  - `options.onClick` (`() => unknown`, optional): runs when the row is clicked (e.g. `tg.ui.openChat(peer)`).
- **returns:** `UiElement` with `type: 'peer'`.
- **notes:**
  - a peer tele hasn't loaded shows its id instead of a name and no picture; the userpic appears when its photo finishes downloading.

Example:

```ts
const top = await tg.getDialogs({ limit: 5 })
const page = tg.ui.settingsPage({
  title: 'recent chats',
  items: () => top.flatMap(({ peer, unreadCount }) => peer ? [tg.ui.peer({
    peer,
    subtitle: `${unreadCount} unread`,
    onClick: () => tg.ui.openChat(peer),
  })] : []),
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
registerSettingsEntry(options: { title: string, emoji?: string, icon?: MenuIcon, page: Page, onClick?(): unknown }): Disposer
```

adds a button to tele's main settings page, after tele's own entries and a divider. clicking it opens `page` as a settings section (like `tg.ui.openSection`).

- **grant:** none.
- **parameters:**
  - `options.title` (`string`): the button's label.
  - `options.emoji` (`string`, optional): drawn before the label.
  - `options.icon` (`MenuIcon`, optional): drawn in the button's icon column like tele's own settings entries, see `type MenuIcon`; with an icon the label lines up with theirs.
  - `options.page` (`Page`): the page to open.
  - `options.onClick` (`() => unknown`, optional): runs after the section opened, for example to refresh data and `page.invalidate()`.
- **returns:** `Disposer` that removes the button.
- **throws:**
  - `TypeError: expected a page from tg.ui.settingsPage` for something that isn't a page.
  - `TypeError: tg.ui.registerSettingsEntry needs a page from tg.ui.settingsPage` for a disposed page.
  - `TypeError: tg.ui.registerSettingsEntry({ ..., onClick })` when `onClick` is given but isn't a function.
  - `TypeError: tg.ui.registerSettingsEntry: <problem>` for a bad `icon`, see `type MenuIcon`.
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

## webviews

a webview panel is a separate window with a web page in it, for ui that page rows can't do: charts, editors, galleries, little games. the page is html you pass as a string or an https url. it talks to the script only through a json message bridge (`window.tele` inside the page), gets tele's theme colours as css variables, and has no other access to tele or the account. a script can have any number of panels; all of them close when the script stops.

```ts
const panel = tg.ui.webview({
  title: 'counter',
  html: `<button id="b" style="background: var(--tele-accent)">0</button>
<script>
  const b = document.getElementById('b')
  b.onclick = () => tele.postMessage({ clicked: Number(b.textContent) })
  tele.onMessage = (data) => { b.textContent = data.count }
</script>`,
})
panel.onMessage<{ clicked: number }>((data) => panel.postMessage({ count: data.clicked + 1 }))
```

### tg.ui.webview(options)

```ts
webview(options: WebviewOptions): WebviewPanel

export type WebviewOptions = WebviewCommonOptions & (
  | { html: string, url?: undefined }
  | { url: string, html?: undefined }
)

export interface WebviewCommonOptions {
  title: string
  width?: number
  height?: number
  resizable?: boolean
}
```

opens a panel over this account's window, the same kind of window as the mtproto console, and loads `html` or `url` in it. returns right away; the page loads in the background.

- **grant:** none for `html`. `url` needs `fetch(<host>)` for the url's host, the same grant `fetch` uses (so `fetch(example.com)` covers `www.example.com`, and `fetch` without a host covers every host).
- **parameters:**
  - `options.title` (`string`): the panel's title.
  - `options.html` (`string`): a whole html document (or a fragment), served from memory. give either `html` or `url`.
  - `options.url` (`string`): an `https://` page to load.
  - `options.width` (`number`, optional): the page width in pixels at 100% interface scale, 120 to 4096; tele scales it like its own windows. 480 by default.
  - `options.height` (`number`, optional): the page height, same rules. 600 by default; a panel taller than the screen is cut to fit.
  - `options.resizable` (`boolean`, optional): whether the user can resize the panel (down to 120×120). `true` by default.
- **returns:** `WebviewPanel`, the handle for messages, the title and closing.
- **throws:**
  - `TypeError: tg.ui.webview needs { title, html | url }` without an options object, `tg.ui.webview needs a title` for a missing or empty title, `tg.ui.webview needs either html or url` for neither or both, `tg.ui.webview: html is a string` / `url is a string`, `tg.ui.webview: width is a number from 120 to 4096` (same for `height`), `tg.ui.webview: resizable is a boolean`.
  - `TypeError: tg.ui.webview only takes https urls` for any other url.
  - `TeleError` `not-granted` with `grant` set to `fetch(<host>)` for an url whose host isn't granted.
  - `TeleError` `unsupported`: `tg.ui.webview: <reason>` when this system has no usable webview (the same check as mini apps and the mtproto console: WebView2 on windows, WebKitGTK on linux), `tg.ui.webview: this account has no window`, `tg.ui.webview: could not start the webview`.
- **notes:**
  - `html` is served as `index.html` from tele's internal origin. nothing else is served there, so relative links to other files don't load: inline your css and scripts, use `data:` urls for images, or load from hosts you have `fetch` grants for.
  - `html` pages run under a content security policy: the page itself, `data:` and `blob:` urls, inline scripts and styles and `eval` are allowed; images, scripts, styles, fonts, `fetch`, `XMLHttpRequest` and websockets reach only the hosts covered by the script's `fetch` grants (none for a script without them). webrtc is turned off. a page can't send data anywhere the script itself couldn't.
  - `url` pages load their own resources like a browser would, but the panel only navigates to `https` hosts covered by the script's `fetch` grants. other navigations, `target="_blank"` links and `window.open` are blocked silently; to open a link in the browser, post it to the script and call `tg.openUrl` (grant `openUrl`).
  - `localStorage`, cookies and other site data persist per script per account, apart from other scripts and from tele's own webviews.
  - the panel gets keyboard focus when it opens and whenever its window is activated. Escape goes to the page and doesn't close the panel; the close button and tele's close-window shortcut (Ctrl+W) do.
  - several panels can be open at once, from one script or many. they aren't restored after a restart.

Example:

```ts
tg.registerChatAction({
  id: 'stats',
  text: 'chat stats',
  onClick: async (ctx) => {
    const history = await tg.getHistory(ctx.chat, { limit: 100 })
    const panel = tg.ui.webview({ title: `stats: ${ctx.chat.name}`, html: statsPage, width: 640, height: 420 })
    panel.postMessage(history.map((message) => ({ date: message.date, length: message.text.length })))
  },
})
```

### type WebviewPanel

```ts
export interface WebviewPanel {
  postMessage(data: unknown): void
  onMessage<T = unknown>(callback: (data: T) => unknown): Disposer
  setTitle(text: string): void
  close(): void
  onClose(callback: () => unknown): Disposer
  readonly closed: boolean
}
```

the frozen handle `tg.ui.webview` returns.

- **grant:** none.
- **parameters:**
  - `postMessage(data)`: sends `data` to the page as json (`JSON.stringify` on the script side, parsed again in the page). messages sent before the page has loaded wait and are delivered right after it loads, in order; for `url` pages that's only the first load, messages sent while a later navigation is in progress are lost. does nothing after the panel closed.
  - `onMessage(callback)`: calls `callback(data)` with every message the page sends through `tele.postMessage`, already parsed. any number of callbacks; messages that arrive while none is registered are dropped. the type parameter only types `data`, nothing is checked.
  - `setTitle(text)`: changes the panel's title. does nothing after the panel closed.
  - `close()`: closes the panel, then runs the `onClose` callbacks right away. does nothing if it's already closed.
  - `onClose(callback)`: runs `callback()` once when the panel closes, by the user (close button, Ctrl+W), by `close()`, or because the webview process died. not called when the script stops.
  - `closed` (`boolean`): `true` once the panel has closed.
- **returns:** `onMessage` and `onClose` return a `Disposer` that removes that callback.
- **throws:**
  - `TypeError: WebviewPanel.postMessage needs JSON-serializable data` for `undefined`, functions, symbols, bigints and cyclic objects.
  - `TypeError: WebviewPanel.onMessage needs a function` / `WebviewPanel.onClose needs a function`.
  - `TypeError: WebviewPanel.setTitle needs a non-empty string`.
- **notes:**
  - callbacks run with the listener budget like other events; a throwing callback is a fault (logged, counts toward "5 in a row"), the other callbacks still run. a callback that throws inside `close()` makes `close()` throw after all of them ran.
  - the page can send messages at any rate; a script that does heavy work per message should debounce in the page.

Example:

```ts
const panel = tg.ui.webview({ title: 'notes', html: notesPage })
panel.postMessage({ text: tg.storage.get<string>('notes') ?? '' })
const stop = panel.onMessage<{ text: string }>((data) => tg.storage.set('notes', data.text))
panel.onClose(() => {
  stop()
  tg.toast('notes saved')
})
```

### the page side: window.tele

```ts
interface Window {
  readonly tele: {
    postMessage(data: unknown): void
    onMessage: ((data: unknown) => void) | null
  }
}
```

what the page gets: a `window.tele` bridge and tele's colours. it's injected into every page the panel loads (also into `url` pages), in the top frame only, before the page's own scripts run.

- **grant:** none.
- **parameters:**
  - `tele.postMessage(data)`: sends `data` to the script's `onMessage` callbacks. `data` must be json-serializable, otherwise it throws `TypeError: tele.postMessage needs JSON-serializable data`.
  - `tele.onMessage`: set it to a function to receive the script's `postMessage` data, already parsed. messages that arrived before it was set are kept (up to 1000) and handed over as soon as it is. set it to `null` to stop.
  - `window` also fires a `tele-message` event (a `CustomEvent`, the data in `event.detail`) for every message, for pages that prefer `addEventListener('tele-message', ...)`. events aren't kept for listeners added later.
  - css variables on `:root` (as inline styles of the `<html>` element), updated live when tele's theme changes: `--tele-bg` (window background), `--tele-text` (text), `--tele-accent` (buttons and accents), `--tele-secondary-bg` (hovered rows, secondary surfaces), `--tele-hint` (secondary text), `--tele-link` (links and active text). each is `#rrggbb` or `rgba(...)`.
- **returns:** nothing.
- **throws:** nothing beyond `tele.postMessage`'s TypeError.
- **notes:**
  - errors thrown by `tele.onMessage` or `tele-message` listeners show up in the page's console, they don't stop the bridge.
  - the page has no other way into tele: no `tg`, no account, no files. anything it needs comes through the script.

Example:

```html
<style>
  body { background: var(--tele-bg); color: var(--tele-text); font: 14px system-ui, sans-serif; }
  button { background: var(--tele-accent); color: var(--tele-bg); border: 0; border-radius: 8px; padding: 8px 14px; }
</style>
<textarea id="notes" style="width: 100%; height: 80vh"></textarea>
<script>
  const notes = document.getElementById('notes')
  tele.onMessage = (data) => { notes.value = data.text }
  notes.addEventListener('input', () => tele.postMessage({ text: notes.value }))
</script>
```

## menus, buttons and commands

places where a script adds its own controls to tele: context menu items, `/commands` in the compose field, keyboard shortcuts, buttons in the chat header and compose bar, rows in profiles, quick buttons next to messages, and items in the left drawer and the tray menu. none of them needs a grant (the user triggers them), every registration returns a `Disposer`, any number per script is fine, and all of them disappear when the script stops.

### the menu editor

tele has a menu editor: Alt + right-click on a context menu lets the user move and hide its items, and tele remembers the layout. items added with `tg.registerMessageAction`, `tg.registerChatAction` and `tg.registerProfileAction` are real items of that system, not something drawn on top.

- **grant:** none.
- **notes:**
  - each action has a stable key `script.<script id>.<id>`, where the script id is the file or folder name with every character outside `a-z 0-9 _` turned into `_`, and `id` is the action's `id`. the layout is saved by that key, so keep ids stable between versions.
  - a new action appears at the bottom of its menu, with its `icon` (see `type MenuIcon`) or tele's experimental icon. once the user moves or hides it in the editor, it stays where they put it.
  - when the script stops (or the disposer runs) the item becomes inactive: it disappears from the menu and from the editor, but its saved placement is kept, so it comes back to the same place when the script starts again. the placement is only forgotten if the user saves the editor while the script is off.
  - the same action registered by the script in several accounts is one menu item.

Example:

```ts
// keep the id stable: renaming 'translate' to 'tr' would lose the user's placement
tg.registerMessageAction({ id: 'translate', text: 'translate', onClick: translate })
```

### type MenuIcon

```ts
export type MenuIconName =
  | 'reactions'
  | 'reply'
  | 'copy'
  // … every icon of tele's own menus: tele.d.ts lists all 222
export type MenuIcon = MenuIconName | (string & {}) | bigint | Uint8Array
```

the icon of a menu item, a drawer item or a settings entry: `icon` in `ActionOptions`, `MediaActionOptions` and `StoryActionOptions`, and in `tg.ui.registerMenuItem`, `tg.ui.registerSettingsEntry` and `widget.addMenuItem`.

- **forms:**
  - a tele icon name (`'copy'`, `'delete'`, `'link'`, `'pin'`, `'settings'`…): the icon tele's own items use, in their color. `MenuIconName` in `tele.d.ts` lists every name.
  - one emoji (`'🧪'`): drawn in color, at emoji size.
  - an SVG: a string that starts with `<svg` (or `<?xml`), a `.svg` file or SVG bytes. drawn as a mask in the menu's icon color, so it follows the theme like tele's icons; its own colors are ignored.
  - an image: a `.png`, `.jpg` / `.jpeg` or `.webp` file, or its bytes as a `Uint8Array`. drawn as it is, scaled down to the icon size.
  - a custom emoji: its document id as a `bigint` (the `documentId` of a `messageEntityCustomEmoji` or an `emojiStatus`). drawn like in messages: animated (power saving stops it), and in the icon color when it's a text-colored emoji.
- **notes:**
  - file paths are relative to the script's folder (the scripts folder for a single-file script); absolute paths work too. the file is read once, when the item is registered. files and bytes are limited to 1 MB.
  - the icon sits in the menu's icon column, at the same size as tele's icons. menus without an icon column, like the tray menu, show the item without it.
  - in the media viewer's and the story viewer's dark menus, tele icons and SVGs take the menu's light text color.
  - the menu editor shows tele icons on script items; other icons show as the experimental icon in the editor, and the real menu keeps them however the items are moved.
- **throws:** `TypeError` with the registering method's name in front, e.g. `TypeError: tg.registerMessageAction: icon can't be empty`:
  - `icon must be a string, a bigint or a Uint8Array`.
  - `icon can't be empty` for a blank string.
  - `icon '<text>' isn't a tele icon name, one emoji, an <svg> or an image file`.
  - `the icon isn't a valid SVG`.
  - `can't read the icon file <path>`, `the icon file is over 1 MB`, `the icon is over 1 MB` (bytes).
  - `the icon file isn't a valid SVG, PNG, JPEG or WebP image`, `the icon bytes aren't a valid SVG, PNG, JPEG or WebP image`.
  - `icon must be a custom emoji document id` for a `bigint` that isn't positive.

Example:

```ts
tg.registerMessageAction({ id: 'copy_md', text: 'copy as markdown', icon: 'copy', onClick: copyAsMarkdown })
tg.registerChatAction({ id: 'stats', text: 'chat stats', icon: '📊', onClick: showStats })
tg.registerProfileAction({ id: 'card', text: 'contact card', icon: 'icons/card.svg', onClick: showCard })
tg.ui.registerMenuItem({ place: 'main', text: 'my bot', icon: 5368324170671202286n, onClick: openBot })
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
  - `TypeError: tg.registerMessageAction: <problem>` for a bad `icon`, see `type MenuIcon`.
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
  icon?: MenuIcon
  onClick(context: C): unknown
  visible?(context: C): boolean
}
```

options shared by the three menu actions; `C` is `MessageActionContext` for message actions and `ActionContext` for chat and profile actions.

- **fields:**
  - `id` (`string`): 1 to 64 characters of `a-z`, `0-9` and `_`, unique per menu within the script. it's part of the menu editor key, so keep it stable.
  - `text` (`string`): the item's label, not empty.
  - `icon` (`MenuIcon`, optional): the item's icon, see `type MenuIcon`. without it the item gets tele's experimental icon.
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
registerMenuItem(options: { place: 'main' | 'tray', text: string, emoji?: string, icon?: MenuIcon, onClick(): unknown }): Disposer
```

adds an item to the left drawer (the main menu behind the ☰ button) or to the tray icon's menu.

- **grant:** none.
- **parameters:**
  - `options.place` (`'main' | 'tray'`): `'main'` adds it at the end of the left drawer, after a separator; `'tray'` adds it to the tray menu before Quit.
  - `options.text` (`string`): the item's label.
  - `options.emoji` (`string`, optional): drawn before the label.
  - `options.icon` (`MenuIcon`, optional): drawn in the drawer row's icon column like tele's own items, see `type MenuIcon`. the tray menu has no icon column and ignores it.
  - `options.onClick` (`() => unknown`): runs when the item is clicked (the drawer closes first).
- **returns:** `Disposer` that removes the item.
- **throws:**
  - `TypeError: tg.ui.registerMenuItem({ ..., onClick })` when `onClick` isn't a function.
  - `TypeError: tg.ui.registerMenuItem: place is 'main' or 'tray'`.
  - `TypeError: tg.ui.registerMenuItem: <problem>` for a bad `icon`, see `type MenuIcon`.
- **notes:**
  - the drawer and the tray belong to the whole app, so items of every account's scripts show there, in registration order.
  - tray items are hidden while tele is locked with a passcode.
  - these items are not part of the menu editor.

Example:

```ts
tg.ui.registerMenuItem({ place: 'main', emoji: '📊', text: 'chat stats', onClick: () => tg.ui.openSection(statsPage) })
tg.ui.registerMenuItem({ place: 'tray', emoji: '🌙', text: 'toggle night mode', onClick: () => tg.app.theme.setDark(!tg.app.theme.get().dark) })
```

## inline answers

a script can answer inline queries the way an inline bot does: the user types `@<trigger> <query>` in the message field and tele shows the script's results in its own inline results panel, with no network involved. choosing a result sends a normal message from the user (text, a TL media or a file), so sending needs `account.write(send)`; registering needs no grant. inline queries to real bots work as before. what a script registers here goes away when its disposer runs or the script stops.

### tg.registerInline(answerer)

```ts
registerInline(answerer: InlineAnswerer): Disposer
```

registers `@<answerer.trigger>` on this account: when the message field starts with `@<trigger>` and a space, tele calls `answerer.results` with the rest of the text and shows what it returns in the inline results panel above the field. clicking a result (or its thumbnail, or right-click > a send option) sends its `message` to the open chat and clears the field.

- **grant:** none to register; `account.write(send)` to send, checked when the user picks a result: without it tele shows a toast and sends nothing.
- **parameters:**
  - `answerer` (`InlineAnswerer`): `{ trigger, title?, results }`, see `type InlineAnswerer`.
- **returns:** `Disposer` that removes the trigger (an open panel for it closes).
- **throws:**
  - `TypeError: tg.registerInline({ trigger, title?, results })` without an object with a `results` function.
  - `TypeError: tg.registerInline: trigger is 2-32 characters of a-z, 0-9 and _, starting with a letter`.
  - `TypeError: tg.registerInline: title must be a string`.
  - `TeleError` `forbidden` (`the trigger @calc is taken by "<script>"`) when a running script on this account already registered the trigger.
- **notes:**
  - who wins `@calc`: tele first parses the field like it does for bots (`@`, a username that starts with a letter, a space). if tele already knows an inline bot with that username (a bot you used or saw, so it's in tele's cache, including tele's username aliases), the bot answers and the script isn't asked. otherwise the script answers and tele never looks the username up on the server. so a bot you actually use is never hijacked, typing a trigger leaks nothing to Telegram, and a bot you never used with the same name can't be reached while the script runs: pick triggers that aren't bot names (bot usernames end in `bot`).
  - the trigger is matched case-insensitively (`@Calc 1+1` works); it must be typed with a space after it, `@calc` alone does nothing. message editing doesn't show inline results.
  - `title` becomes the field's placeholder after `@<trigger> `, like a bot's inline placeholder.
  - tele waits 400 ms after the last keystroke (like for bots) and asks again for every new query; a query that changes meanwhile is cancelled: `context.signal` aborts and whatever the old call returns is ignored. answers are cached per query until the trigger or the chat changes, so typing a previous query again shows its results at once.
  - an answer has 2 s. a `results` that throws, returns something that isn't an array or doesn't answer in time shows an empty panel with `@<trigger>: <the error message>` (or `@<trigger>: didn't answer in time`); the error is in the script's log. an empty array (or `null`) hides the panel, like a bot without results.
  - up to 50 results are shown as rows (title, description, thumbnail); a result that isn't valid (no id, a repeated id, no title, a bad `message`, a `thumb` that isn't bytes) is skipped and logged.
  - the message is sent with `tg.sendMessage`, `tg.sendMedia` or `tg.sendFile` to the open chat, as a reply when the user is replying to a message of that chat, silent or scheduled when picked from the right-click menu. a send that fails shows a toast with the error. in the scheduled messages section a plain click sends right away.
  - the panel is the one inline bots use: in a chat and in topics, replies and other compose fields of a window.

Example:

```ts
// grants: ['account.write(send)']
tg.registerInline({
  trigger: 'shrug',
  title: 'text to shrug at',
  results: (query) => [
    { id: 'plain', title: '¯\\_(ツ)_/¯', description: query, message: `${query} ¯\\_(ツ)_/¯`.trim() },
    { id: 'bold', title: 'bold', description: query, message: md`**${query}** ¯\\_(ツ)_/¯` },
  ],
})
```

### type InlineAnswerer

```ts
export interface InlineAnswerer {
  trigger: string
  title?: string
  results(
    query: string,
    context: InlineQueryContext,
  ):
    | readonly InlineResult[]
    | null
    | void
    | Promise<readonly InlineResult[] | null | void>
}
```

what `tg.registerInline` takes.

- **parameters:**
  - `trigger` (`string`): the word after `@`, 2 to 32 characters of `a-z`, `0-9` and `_`, starting with a letter; unique per account.
  - `title` (`string`, optional): the field placeholder shown after `@<trigger> `.
  - `results` (`(query, context) => results`): gets the text after `@<trigger> ` (possibly empty) and an `InlineQueryContext`, returns the results (an empty array, `null` or nothing for none), may be async. it's called as a method of `answerer`.
- **returns:** `InlineResult[]`, see `type InlineResult`.

Example:

```ts
const notes: InlineAnswerer = {
  trigger: 'note',
  title: 'name of a saved note',
  results(query) {
    const saved = tg.storage.get<Record<string, string>>('notes') ?? {}
    return Object.entries(saved)
      .filter(([name]) => name.startsWith(query))
      .map(([name, text]) => ({ id: name, title: name, description: text, message: text }))
  },
}
tg.registerInline(notes)
```

### type InlineQueryContext

```ts
export interface InlineQueryContext {
  readonly chat: bigint
  readonly signal: AbortSignal
}
```

the second argument of `InlineAnswerer.results`.

- **values:**
  - `chat` (`bigint`): the marked id of the chat whose field is being typed in; an `InputPeerLike`.
  - `signal` (`AbortSignal`): aborts when the query changes, the trigger is erased or the 2 s run out. pass it to `fetch` or check `signal.aborted` in long work.

Example:

```ts
// grants: ['account.write(send)', 'fetch(api.example.com)']
tg.registerInline({
  trigger: 'wiki',
  async results(query, { signal }) {
    if (!query) return []
    const response = await fetch(`https://api.example.com/search?q=${encodeURIComponent(query)}`, { signal })
    const pages = (await response.json()) as { title: string, url: string }[]
    return pages.map((page) => ({ id: page.url, title: page.title, description: page.url, message: page.url }))
  },
})
```

### type InlineResult

```ts
export interface InlineMediaMessage {
  media: Uint8Array | tl.TypeInputMedia
  caption?: InputText
}

export interface InlineResult {
  id: string
  title: string
  description?: string
  thumb?: Uint8Array
  message: InputText | InlineMediaMessage
}
```

one row of the panel and what it sends.

- **values:**
  - `id` (`string`): non-empty, unique within one answer.
  - `title` (`string`): the bold first line (up to two lines shown).
  - `description` (`string`, optional): the grey text under the title.
  - `thumb` (`Uint8Array`, optional): image bytes in any format tele reads (png, jpeg, webp, gif, bmp...), up to 4 MB; scaled down to 160 px and shown from memory. without it the row has no picture.
  - `message` (`InputText | InlineMediaMessage`): what choosing the row sends: a string or `TextWithEntities` (`md`/`html`) as a text message; `{ media, caption? }` with a TL `InputMedia` (sent with `tg.sendMedia`) or raw bytes (uploaded with `tg.sendFile`: jpeg and png go as a photo, gif as `animation.gif`, mp4 as `video.mp4`, anything else as a file named `file`). a text must not be empty.

Example:

```ts
// grants: ['account.write(send)']
tg.registerInline({
  trigger: 'roll',
  title: 'dice, darts or a picture',
  async results() {
    const pixels = new Uint8Array(32 * 32 * 4).fill(200)
    const square = await tg.image.fromPixels({ width: 32, height: 32, data: pixels })
    const list: InlineResult[] = [
      { id: 'dice', title: '🎲', message: { media: { _: 'inputMediaDice', emoticon: '🎲' } } },
      { id: 'darts', title: '🎯', message: { media: { _: 'inputMediaDice', emoticon: '🎯' } } },
      { id: 'square', title: 'a grey square', thumb: square, message: { media: square, caption: 'grey' } },
    ]
    return list
  },
})
```

## navigation and compose

moving around this account's window and working with the text the user is typing. navigation, banners and the message selection need no grant; the compose field's text is a draft, so reading and changing it uses the `draft` scopes of `account.read` and `account.write`, while its reply, attachments and send options have their own rules (see each item).

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

### tg.ui.banner(options)

```ts
banner(options: BannerOptions): Disposer
```

shows a bar above the messages of a chat, like tele's own "add contact" or join-requests bars: an optional emoji, the text, up to three buttons and a close button. several banners in one chat stack in the order they were made. with `place: 'chats'` the bar goes above the chat list instead, see `tg.ui.banner({ place: 'chats' })`.

- **grant:** none.
- **parameters:**
  - `options` (`BannerOptions`): `place: 'chat'`, the `chat`, the `text`, and optionally `icon`, `buttons`, `closable`, `onClose`. see `type BannerOptions`.
- **returns:** `Disposer` that removes the banner (without calling `onClose`).
- **throws:**
  - `TypeError: tg.ui.banner(options)` for a non-object.
  - `TypeError: tg.ui.banner: place must be 'chat' or 'chats'`.
  - `TypeError: tg.ui.banner: place 'chat' needs a chat`.
  - `TypeError: tg.ui.banner: text must be a non-empty string`.
  - `TypeError: tg.ui.banner: icon must be a string`.
  - `TypeError: tg.ui.banner: buttons must be an array of { text, onClick }` (more than three buttons, an empty text or a missing `onClick` included).
  - `TypeError: tg.ui.banner: onClose must be a function`.
- **notes:**
  - the banner shows wherever that chat's messages are on screen in this account: the main chat view and the chat's topic, replies and saved-sublist views (not the scheduled messages view). it appears as soon as the chat is opened and stays until it's disposed, closed or the script stops; it doesn't need the chat to be open when you make it.
  - `chat` takes any `InputPeerLike`. a marked id, `'me'`, a `PeerInfo`, a `Message` or a TL peer work without a lookup and without grants; a username is resolved in the background (which needs `account.read(peers)`), and a failure is logged instead of thrown.
  - the text is plain (no markdown) and wraps. a button click doesn't close the banner; the close button (shown unless `closable: false`) removes it and then calls `onClose`.
  - button and close callbacks run on the next event-loop turn with the 200 ms budget.

Example:

```ts
tg.registerChatAction({
  id: 'remind',
  text: 'pin a reminder bar',
  onClick: (ctx) => {
    const hide = tg.ui.banner({
      place: 'chat',
      chat: ctx.chat,
      icon: '⏰',
      text: 'reply to the invoice before friday',
      buttons: [
        { text: 'open settings', onClick: () => tg.ui.openSettings('tele') },
        { text: 'done', onClick: () => hide() },
      ],
      onClose: () => tg.toast('reminder dismissed'),
    })
  },
})
```

### type BannerOptions

```ts
export interface BannerButton {
  text: string
  onClick(): unknown
}

export interface BannerOptions {
  place: 'chat' | 'chats'
  chat?: InputPeerLike
  text: string
  icon?: string
  buttons?: BannerButton[]
  closable?: boolean
  onClose?(): unknown
}
```

what `tg.ui.banner` takes, for both places.

- **fields:**
  - `place` (`'chat' | 'chats'`): `'chat'` puts the bar above a chat's messages, `'chats'` above the chat list.
  - `chat` (`InputPeerLike`, optional): which chat, required for `'chat'`, ignored for `'chats'`.
  - `text` (`string`): the text, plain, trimmed, not empty.
  - `icon` (`string`, optional): an emoji drawn before the text.
  - `buttons` (`BannerButton[]`, optional): up to three buttons on the right, each `{ text, onClick }`. `onClick` gets no arguments; return a promise if you like, nothing waits for it.
  - `closable` (`boolean`, optional): `false` hides the close button. `true` by default.
  - `onClose` (`() => unknown`, optional): called after the user closed the banner with its close button. disposing it yourself doesn't call it.

Example:

```ts
const options: BannerOptions = { place: 'chat', chat: 'me', text: 'notes to self live here', closable: false }
tg.ui.banner(options)
```

### tg.ui.banner({ place: 'chats' })

```ts
banner(options: BannerOptions): Disposer
```

with `place: 'chats'`, shows a bar above the chat list of this account's windows: an optional emoji, the text, up to three buttons and a close button. see `tg.ui.banner(options)` for the in-chat bar and `type BannerOptions` for the fields.

- **grant:** none.
- **parameters:**
  - `options` (`BannerOptions`): `place: 'chats'`, `text`, and optionally `icon`, `buttons`, `closable`, `onClose`. `chat` is ignored.
- **returns:** `Disposer` that removes the banner (without calling `onClose`).
- **throws:**
  - `TypeError: tg.ui.banner: text must be a non-empty string`.
  - `TypeError: tg.ui.banner: icon must be a string`.
  - `TypeError: tg.ui.banner: buttons must be an array of { text, onClick }` (more than three buttons, an empty text or a missing `onClick` included).
  - `TypeError: tg.ui.banner: onClose must be a function`.
- **notes:**
  - the text is plain (no markdown) and wraps; the buttons wrap to more lines when the list is narrow.
  - a button click doesn't close the banner. the close button (shown unless `closable: false`) removes it and then calls `onClose`.
  - the banners hide while a search is open in the chat list and come back when it closes. several banners stack in the order they were made, above tele's own list (and below tele's suggestion bars).
  - every window of the account shows the banner, the chat lists of folders and forums too; a narrow chat list beside a forum doesn't.

Example:

```ts
const banner = tg.ui.banner({
  place: 'chats',
  icon: '🧹',
  text: 'you have 12 unread channels older than a month',
  buttons: [{ text: 'review', onClick: () => tg.ui.openChat('me') }],
  onClose: () => tg.storage.set('cleanupDismissed', true),
})
setTimeout(() => banner(), 3_600_000)
```

### tg.ui.selection()

```ts
selection(): MessageSelection | null
```

tells which messages the user has selected (with a click on a message's check, or by dragging across messages) in this account's window.

- **grant:** none.
- **returns:** `{ chatId, ids }` (see `type MessageSelection`) for the selection in the chat on screen, or `null` when nothing is selected.
- **notes:**
  - only whole-message selection counts; text selected inside one message isn't reported.
  - ids only: read the messages with `tg.getMessages` / `tg.getCachedMessage` (which need `account.read(messages)`).
  - secret chats are never reported.

Example:

```ts
tg.registerShortcut('Ctrl+Shift+C', async () => {
  const selected = tg.ui.selection()
  if (!selected) return tg.toast('select some messages first')
  const messages = await tg.getMessages(selected.chatId, selected.ids)
  tg.clipboard.write(messages.map((message) => message?.text ?? '').join('\n'))
})
```

### tg.ui.onSelectionChanged(callback)

```ts
onSelectionChanged(callback: (selection: MessageSelection | null) => unknown): Disposer
```

calls `callback` when the message selection in this account's window changes: messages selected or unselected, the selection cleared, or the view holding it closed.

- **grant:** none.
- **parameters:**
  - `callback` (`(selection) => unknown`): gets the selection after the change, like `tg.ui.selection()` returns it, `null` once nothing is selected. runs on the next event-loop turn with the 200 ms budget; quick changes (dragging across messages) are merged into one call.
- **returns:** `Disposer` that stops the calls.
- **throws:** `TypeError: tg.ui.onSelectionChanged(function)`.

Example:

```ts
tg.ui.onSelectionChanged((selection) => {
  tg.app.window.setBadge(selection ? selection.ids.length : null)
})
```

### type MessageSelection

```ts
export interface MessageSelection {
  chatId: bigint
  ids: number[]
}
```

a selection of messages in one chat.

- **fields:**
  - `chatId` (`bigint`): the chat (marked id).
  - `ids` (`number[]`): the selected message ids, ascending, never empty.

Example:

```ts
const selection: MessageSelection | null = tg.ui.selection()
if (selection) console.log(`${selection.ids.length} selected in ${selection.chatId}`)
```

### tg.compose

```ts
readonly compose: Compose
```

the compose field (the message input at the bottom of a chat). see `type Compose` and the methods below.

- **grant:** `account.read(draft)` to read the text and listen to it, `account.write(draft)` to change it. the field's state, reply, attachments and `sendAs` need nothing, `silent` needs `account.write(notify)` and `interceptPaste` needs `interceptDrop`.
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

export interface Compose {
  state(peer?: InputPeerLike): Promise<ComposeState | null>
  onStateChange(callback: (state: ComposeState) => unknown): Disposer
  setReply(messageId: number | null, peer?: InputPeerLike): Promise<boolean>
  attach(files: AttachFile[], peer?: InputPeerLike): Promise<boolean>
  setSendOptions(
    options: { silent?: boolean, sendAs?: InputPeerLike },
    peer?: InputPeerLike,
  ): Promise<boolean>
  interceptPaste(interceptor: PasteInterceptor): Disposer
}
```

the type of `tg.compose`; the second block is interface merging, added with the reply, attachment, send-option and paste members.

- **fields:**
  - `get` (`(peer?) => Promise<{ chatId, text } | null>`): read the field, see `tg.compose.get`.
  - `set` (`(text, peer?) => Promise<boolean>`): replace the field's text, see `tg.compose.set`.
  - `insert` (`(text, peer?) => Promise<boolean>`): insert at the cursor, see `tg.compose.insert`.
  - `onInput` (`(callback) => Disposer`): listen to changes, see `tg.compose.onInput`.
  - `state` (`(peer?) => Promise<ComposeState | null>`): the field's reply, edit, forward and send options, see `tg.compose.state`.
  - `onStateChange` (`(callback) => Disposer`): follow that state, see `tg.compose.onStateChange`.
  - `setReply` (`(messageId, peer?) => Promise<boolean>`): set or clear the reply, see `tg.compose.setReply`.
  - `attach` (`(files, peer?) => Promise<boolean>`): open the send box with files, see `tg.compose.attach`.
  - `setSendOptions` (`(options, peer?) => Promise<boolean>`): silent posting and the send-as peer, see `tg.compose.setSendOptions`.
  - `interceptPaste` (`(interceptor) => Disposer`): handle what is pasted into the field, see `tg.compose.interceptPaste`.

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

### tg.compose.state(peer?)

```ts
state(peer?: InputPeerLike): Promise<ComposeState | null>
```

reads what the compose field is set up to do: the message it replies to or edits, the forwarded messages waiting under it, silent sending and the "send as" choice.

- **grant:** none. the result has ids only; reading those messages needs `account.read(messages)`, the text in the field needs `account.read(draft)` (`tg.compose.get`).
- **parameters:**
  - `peer` (`InputPeerLike`, optional): whose field. the open chat's by default.
- **returns:** `Promise<ComposeState | null>`, `null` when there's no such field (no chat open, the chat isn't open anywhere, or a secret chat). see `type ComposeState`.
- **notes:** a marked id, `'me'`, a `PeerInfo`, a `Message` or a TL peer work without a lookup; a username is resolved through `tg.peers`.

Example:

```ts
const state = await tg.compose.state()
if (state?.replyTo) {
  const message = await tg.getCachedMessage(state.replyTo.chatId, state.replyTo.messageId)
  console.log(`replying to: ${message?.text ?? 'a message tele has not loaded'}`)
}
```

### type ComposeState

```ts
export interface ComposeState {
  chatId: bigint
  replyTo: { chatId: bigint, messageId: number } | null
  editing: number | null
  silent: boolean
  scheduled: boolean
  sendAs: bigint | null
  attached: number
}
```

the state of one compose field.

- **fields:**
  - `chatId` (`bigint`): the field's chat (marked id).
  - `replyTo` (`{ chatId, messageId } | null`): the message the next send replies to; `chatId` differs from the field's chat for a reply to another chat. `null` without a reply.
  - `editing` (`number | null`): the id of the message being edited, `null` when not editing.
  - `silent` (`boolean`): `true` when posts in this channel go out without sound (the bell in the field). always `false` outside channels.
  - `scheduled` (`boolean`): `true` for the field of the scheduled messages view, where everything sent is scheduled.
  - `sendAs` (`bigint | null`): the marked id of the peer messages are sent as, when the chat offers a choice (anonymous admins, channels you own); `null` when it doesn't.
  - `attached` (`number`): how many messages are waiting under the field to be forwarded with the next send (the forward bar), `0` for none.

Example:

```ts
const state = await tg.compose.state()
if (state?.editing) tg.toast(`editing message ${state.editing}`)
```

### tg.compose.onStateChange(callback)

```ts
onStateChange(callback: (state: ComposeState) => unknown): Disposer
```

calls `callback` when the state of any compose field of this account changes: a reply set or cancelled, editing started or finished, messages added to or removed from the forward bar, silent sending toggled, another "send as" picked.

- **grant:** none.
- **parameters:**
  - `callback` (`(state: ComposeState) => unknown`): gets the field's new state. runs on the next event-loop turn with the 200 ms budget.
- **returns:** `Disposer` that stops the calls.
- **throws:** `TypeError: tg.compose.onStateChange(function)`.
- **notes:** it doesn't fire for typing (use `tg.compose.onInput`), nor for the state fields already had when you subscribed. switching chats can fire it for the field that now shows another chat.

Example:

```ts
tg.compose.onStateChange((state) => {
  if (state.replyTo) console.log(`replying in ${state.chatId} to ${state.replyTo.messageId}`)
})
```

### tg.compose.setReply(messageId, peer?)

```ts
setReply(messageId: number | null, peer?: InputPeerLike): Promise<boolean>
```

makes a compose field reply to a message of its chat, like "reply" in the message menu, or cancels the reply.

- **grant:** none.
- **parameters:**
  - `messageId` (`number | null`): a message id in the field's chat, or `null` to cancel the reply.
  - `peer` (`InputPeerLike`, optional): whose field, the open chat's by default.
- **returns:** `Promise<boolean>`: `true` when the field took the request, `false` when there's no field or tele hasn't loaded that message.
- **throws:** rejects with `TypeError: tg.compose.setReply: messageId must be a positive integer or null`.
- **notes:** it goes through the same path as "reply" in the message menu, so tele's own rules apply: in a chat you can't write to it offers to reply in another chat instead.

Example:

```ts
tg.onNewMessage(async (message) => {
  const { chatId } = tg.ui.current()
  if (message.mentioned && chatId === message.chatId) await tg.compose.setReply(message.id)
})
```

### tg.compose.attach(files, peer?)

```ts
attach(files: AttachFile[], peer?: InputPeerLike): Promise<boolean>
```

opens tele's "send files" box for a chat with the given files, as if they were pasted or dropped: the user still picks the options, adds a caption and presses send.

- **grant:** none.
- **parameters:**
  - `files` (`AttachFile[]`): 1 to 100 files, each `{ name, bytes }`. images become photos, videos videos and the rest documents, like tele decides for a drop.
  - `peer` (`InputPeerLike`, optional): which chat, the open one by default. it needs a chat view with a field: the main chat view, a topic or replies.
- **returns:** `Promise<boolean>`: `true` when the box opened, `false` when there's no field for that chat or tele refused the files (it shows its own error then, for example when the chat doesn't allow media).
- **throws:** rejects with a `TypeError` for anything but a non-empty array of `{ name, bytes }` with non-empty names and bytes (`Uint8Array` or `ArrayBuffer`), or more than 100 files.
- **notes:** the files are prepared in the background (previews, video info); the promise resolves when the box is shown.

Example:

```ts
tg.registerButton({
  place: 'compose',
  icon: '📊',
  tooltip: 'attach a report',
  onClick: async (ctx) => {
    const csv = new TextEncoder().encode('day,messages\nmonday,42\n')
    await tg.compose.attach([{ name: 'report.csv', bytes: csv }], ctx.chat)
  },
})
```

### type AttachFile

```ts
export interface AttachFile {
  name: string
  bytes: Uint8Array | ArrayBuffer
}
```

a file a script hands to tele's send box.

- **fields:**
  - `name` (`string`): the file name shown and sent (its extension tells tele the type of a document).
  - `bytes` (`Uint8Array | ArrayBuffer`): the content, not empty.

Example:

```ts
const file: AttachFile = { name: 'hello.txt', bytes: new TextEncoder().encode('hello') }
await tg.compose.attach([file])
```

### tg.compose.setSendOptions(options, peer?)

```ts
setSendOptions(
  options: { silent?: boolean, sendAs?: InputPeerLike },
  peer?: InputPeerLike,
): Promise<boolean>
```

changes how the next messages in a chat are sent: silently, or as another peer.

- **grant:** none for `sendAs`; `account.write(notify)` for `silent`, because silent posting is a notification setting of the channel kept on the server (the bell in the field).
- **parameters:**
  - `options.silent` (`boolean`, optional): post silently in a channel you can post in.
  - `options.sendAs` (`InputPeerLike`, optional): send as this peer; it has to be one of the choices the chat offers (yourself, the group, channels you own).
  - `peer` (`InputPeerLike`, optional): which chat, the open one by default.
- **returns:** `Promise<boolean>`: `true` when applied, `false` without a chat.
- **throws:**
  - rejects with `TypeError: tg.compose.setSendOptions({ silent?, sendAs? })`, `TypeError: tg.compose.setSendOptions: silent must be a boolean` or `TypeError: tg.compose.setSendOptions needs silent or sendAs`.
  - rejects with `TeleError` `not-granted` for `silent` without the grant.
  - rejects with `TeleError` `unsupported` for `silent` outside a channel you post in.
  - rejects with `TeleError` `not-found` when the chat doesn't offer sending as that peer, `forbidden` when that choice needs telegram premium.
- **notes:** `sendAs` is picked for this tele session, like the menu next to the field, but it isn't saved on the server as the chat's default.

Example:

```ts
const myChannel = -1001234567890n
tg.ui.onChatOpened(async ({ chat }) => {
  if (chat?.kind === 'supergroup') await tg.compose.setSendOptions({ sendAs: myChannel }).catch(() => {})
})
```

### tg.compose.interceptPaste(interceptor)

```ts
interceptPaste(interceptor: PasteInterceptor): Disposer

export type PasteInterceptor = (
  paste: PasteInfo,
) => PasteVerdict | null | void | Promise<PasteVerdict | null | void>
```

sees what is pasted (or dropped) into a message field before it lands there: text, an image from the clipboard, copied files. the interceptor keeps it, drops it, replaces it with other text, or turns it into files for the send box.

- **grant:** `interceptDrop` (caution, "see the files and text you drop or paste into chats and handle them instead of tele"): pasted text can be anything the user copied, passwords included.
- **parameters:**
  - `interceptor` (`PasteInterceptor`): gets a `PasteInfo` (see `type PasteInfo`), answers a `PasteVerdict` (see `type PasteVerdict`). may be async.
- **returns:** `Disposer` that removes the interceptor.
- **throws:**
  - `TypeError: tg.compose.interceptPaste(function)`.
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - while interceptors run, tele holds a copy of the pasted data; on `'keep'` it inserts it exactly as it came (formatting included), so tele's own handling follows: an image or files still open the send box, a long text still offers to go as a file, and `tg.interceptDrop` interceptors still see images and files.
  - several interceptors (of all scripts) run one after another in the order they were registered; the first answer other than `'keep'` wins.
  - fails open: a throw, a wrong value (`TypeError: an interceptor returns 'keep', 'drop', { text }, { files } or nothing`, logged) or 2 s keeps the paste. keep interceptors quick: the paste shows up only after they answer.
  - the text lands at the cursor as it is when the answer comes; if the field shows another chat by then, nothing is inserted. secret chats are never intercepted.

Example:

```ts
tg.compose.interceptPaste((paste) => {
  if (paste.kind !== 'text') return 'keep'
  const clean = paste.text.replace(/[?&](utm_[a-z]+|fbclid|gclid)=[^&\s]*/g, '')
  return clean === paste.text ? 'keep' : { text: clean }
})
```

### type PasteInfo

```ts
export interface PasteInfo {
  chatId: bigint
  kind: 'text' | 'image' | 'files'
  text: string
  files: { name: string, path: string, size: number }[]
}
```

what a paste interceptor receives, a frozen object.

- **fields:**
  - `chatId` (`bigint`): the chat whose field gets the paste (marked id).
  - `kind` (`'text' | 'image' | 'files'`): `'files'` when local files were copied, `'image'` for an image (a screenshot from the clipboard), `'text'` otherwise.
  - `text` (`string`): the plain text of the paste, `''` when there's none. copied files often carry their paths as text.
  - `files` (`{ name: string, path: string, size: number }[]`): the copied local files: name, full path, size in bytes. the pixels of an image and the contents of files aren't passed.

Example:

```ts
tg.compose.interceptPaste((paste) => {
  console.log(`${paste.kind} paste into ${paste.chatId}: ${paste.text.length} chars, ${paste.files.length} files`)
})
```

### type PasteVerdict

```ts
export type PasteVerdict = 'keep' | 'drop' | { text: string } | { files: AttachFile[] }
```

what a paste interceptor answers.

- **values:**
  - `'keep'` (or nothing): the next interceptor runs; after the last one tele inserts the paste as usual.
  - `'drop'`: nothing is inserted; later interceptors don't run.
  - `{ text }`: this text is inserted at the cursor instead (plain, no formatting); `''` inserts nothing.
  - `{ files }`: nothing is inserted and tele's send box opens with these files, like `tg.compose.attach`.

Example:

```ts
tg.compose.interceptPaste((paste) => {
  const match = /^data:image\/(png|jpeg);base64,([A-Za-z0-9+/=]+)$/.exec(paste.text.trim())
  if (paste.kind !== 'text' || !match) return 'keep'
  const bytes = Uint8Array.from(atob(match[2]), (char) => char.charCodeAt(0))
  return { files: [{ name: `pasted.${match[1]}`, bytes }] }
})
```

## search

two ways into the search in the chat list: a provider adds its own block of results above tele's, and an interceptor filters or reorders the messages tele found before they show. both cover the chat-list search, including "search in this chat" there (the provider then gets the chat's id); the search bar inside an opened chat isn't covered. what a script registers here goes away when it stops.

### tg.ui.registerSearchProvider(provider)

```ts
registerSearchProvider(provider: SearchProvider): Disposer
```

adds a block titled `provider.title` to the chat-list search results of this account: while the user types, tele calls `provider.search` with the query and shows what it returns above its own chats and messages. a result can open a chat (or a message in it), run a callback, or both.

- **grant:** none. a result's `peer` given as a username is resolved through `tg.peers.resolve` and so needs `account.read(peers)`; `'me'`, a marked id tele has in its cache, a `PeerInfo`, a `Message` or a TL input peer need nothing.
- **parameters:**
  - `provider` (`SearchProvider`): `{ title, search }`, see `type SearchProvider`.
- **returns:** `Disposer` that removes the provider and its block.
- **throws:**
  - `TypeError: tg.ui.registerSearchProvider({ title, search })` without an object with a `search` function.
  - `TypeError: tg.ui.registerSearchProvider: title must be a non-empty string`.
- **notes:**
  - tele waits 300 ms after the last keystroke before asking, and asks again for every new query (or chat). a query that has changed meanwhile is cancelled: `context.signal` aborts and whatever the old call returns is ignored.
  - an answer has 2 s. a provider that throws, returns something that isn't an array or doesn't answer in time shows no block for that query; the error is in the script's log.
  - an empty query (or clearing the search) removes all blocks. the query is trimmed.
  - up to 20 results per provider are shown; a result that isn't valid (no title, a wrong `messageId`, ...) is skipped and logged.
  - several providers show their blocks in the order they were registered. a provider registered while a search is open runs at once.
  - the block sits above tele's own results; arrow keys and Enter don't reach it, the mouse does.

Example:

```ts
tg.ui.registerSearchProvider({
  title: 'calc',
  search(query) {
    const match = /^(-?\d+(?:\.\d+)?)\s*([+\-*/])\s*(-?\d+(?:\.\d+)?)$/.exec(query)
    if (!match) return []
    const [, left, operator, right] = match
    const a = Number(left)
    const b = Number(right)
    const value = operator === '+' ? a + b : operator === '-' ? a - b : operator === '*' ? a * b : a / b
    return [{ title: String(value), subtitle: query, onClick: () => tg.toast(`${query} = ${value}`) }]
  },
})
```

### type SearchProvider

```ts
export interface SearchProvider {
  title: string
  search(
    query: string,
    context: SearchProviderContext,
  ):
    | readonly SearchProviderResult[]
    | null
    | void
    | Promise<readonly SearchProviderResult[] | null | void>
}
```

what `tg.ui.registerSearchProvider` takes.

- **parameters:**
  - `title` (`string`): the header of the provider's block, up to 64 characters.
  - `search` (`(query, context) => results`): gets the trimmed query and a `SearchProviderContext`, returns the results (an empty array, `null` or nothing for none), may be async. it's called as a method of `provider`.
- **returns:** `SearchProviderResult[]`, see `type SearchProviderResult`.

Example:

```ts
const notes: SearchProvider = {
  title: 'notes',
  async search(query, { signal }) {
    const saved = tg.storage.get<Record<string, string>>('notes') ?? {}
    await new Promise<void>((resolve) => setTimeout(resolve, 100))
    if (signal.aborted) return []
    return Object.entries(saved)
      .filter(([name]) => name.includes(query))
      .map(([name, text]) => ({ title: name, subtitle: text }))
  },
}
tg.ui.registerSearchProvider(notes)
```

### type SearchProviderContext

```ts
export interface SearchProviderContext {
  readonly chatId?: bigint
  readonly signal: AbortSignal
}
```

the second argument of `SearchProvider.search`.

- **values:**
  - `chatId` (`bigint`, optional): the marked id of the chat when the user searches inside one chat from the chat list ("search in this chat"); missing for a global search.
  - `signal` (`AbortSignal`): aborts when the query changes, the search closes or the 2 s run out. pass it to `fetch` or check `signal.aborted` in long work.

Example:

```ts
tg.ui.registerSearchProvider({
  title: 'this chat',
  search: (query, { chatId }) => (chatId === undefined ? [] : [{ title: `"${query}" in ${chatId}`, peer: chatId }]),
})
```

### type SearchProviderResult

```ts
export interface SearchProviderResult {
  title: string
  subtitle?: string
  peer?: InputPeerLike
  messageId?: number
  onClick?(): unknown
}
```

one row of a provider's block.

- **values:**
  - `title` (`string`): the first line, bold; must not be empty.
  - `subtitle` (`string`, optional): the second line, grey.
  - `peer` (`InputPeerLike`, optional): shows the chat's userpic, and a click opens that chat. a peer tele can't resolve is dropped (logged) and the row stays.
  - `messageId` (`number`, optional): with `peer`, the click opens the chat at this message.
  - `onClick` (`() => unknown`, optional): runs on a click (after opening `peer`, if any); may be async, errors go to the log.

Example:

```ts
tg.ui.registerSearchProvider({
  title: 'shortcuts',
  search: (query) => ('saved'.startsWith(query.toLowerCase()) ? [{ title: 'Saved Messages', subtitle: 'open', peer: 'me' }] : []),
})
```

### tg.interceptSearch(interceptor)

```ts
interceptSearch(interceptor: SearchInterceptor): Disposer
```

sees every page of messages tele's chat-list message search finds in this account (global, in one chat, public posts) before they show, and decides which of them show and in which order.

- **grant:** `account.read(messages)`.
- **parameters:**
  - `interceptor` (`SearchInterceptor`): gets a `SearchInterception` and returns the results to show, see `type SearchInterceptor`.
- **returns:** `Disposer` that removes the interceptor.
- **throws:**
  - `TypeError: tg.interceptSearch(function)`.
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - it runs once per page: the first page and every page loaded while scrolling. the list keeps loading while it runs.
  - fails open: a throw, a wrong value (`TypeError: an interceptor returns the results to show or nothing`, `TypeError: an interceptor returns entries of results only`) or 2 s without an answer shows the page as tele found it.
  - several interceptors (of this script, then of later scripts) run one after another; each gets what the previous one kept.
  - the "N messages found" counter keeps the server's number.
  - a message found by its link (pasted `t.me/...` link) isn't passed and always shows.

Example:

```ts
tg.interceptSearch(({ results }) => results.filter((message) => !/#spoiler/i.test(message.text)))
```

### type SearchInterceptor

```ts
export type SearchInterceptor = (
  search: SearchInterception,
) =>
  | readonly SearchedMessage[]
  | null
  | void
  | Promise<readonly SearchedMessage[] | null | void>
```

the function `tg.interceptSearch` calls.

- **parameters:**
  - `search` (`SearchInterception`): the query and this page's messages, see `type SearchInterception`.
- **returns:**
  - an array of entries of `search.results`: only these show, in this order (filter to drop, sort to reorder; duplicates show once). an entry may also be a copy with the same `chatId` and `id`.
  - `null` / `undefined` (nothing): the page shows unchanged.
  - or a promise of one of these.

Example:

```ts
const newestFirst: SearchInterceptor = ({ results }) => results.toSorted((a, b) => b.date.getTime() - a.date.getTime())
tg.interceptSearch(newestFirst)
```

### type SearchInterception

```ts
export interface SearchInterception {
  readonly query: string
  readonly chatId?: bigint
  readonly results: SearchedMessage[]
}
```

what a search interceptor gets.

- **values:**
  - `query` (`string`): the query as tele searched it.
  - `chatId` (`bigint`, optional): the chat when the search runs inside one chat.
  - `results` (`SearchedMessage[]`): this page's messages in tele's order.

Example:

```ts
tg.interceptSearch(({ query, results }) => {
  console.log(`'${query}': ${results.length} messages on this page`)
})
```

### type SearchedMessage

```ts
export interface SearchedMessage {
  readonly chatId: bigint
  readonly id: number
  readonly text: string
  readonly date: Date
  readonly fromId: bigint
}
```

one message found by tele's search.

- **values:**
  - `chatId` (`bigint`): the marked id of the message's chat.
  - `id` (`number`): the message id in that chat.
  - `text` (`string`): the plain text (caption for media), empty when there is none.
  - `date` (`Date`): when it was sent.
  - `fromId` (`bigint`): the marked id of the sender (the chat itself for channel posts).

Example:

```ts
tg.interceptSearch(({ results }) => results.filter((message) => message.fromId !== 777000n))
```

## sticker and gif panels

scripts can add their own content to the panel next to the message field: a sticker set in the stickers tab, a set of custom emoji in the emoji tab, and results in the GIF tab's search. registering needs no grant. picking a script sticker or GIF sends a real message as you, so it needs `account.write(send)`, checked when the user clicks: without it tele shows a toast and sends nothing. stickers and GIFs can be TL documents (sent as they are) or raw files: a file is shown right away from memory and uploaded on its first click (`messages.uploadMedia` to Saved Messages' peer, nothing is posted), then sent like any sticker or GIF; later clicks reuse the upload. everything a script adds disappears when its disposer runs or the script stops.

### tg.ui.registerStickerSet(options)

```ts
registerStickerSet(options: PanelStickerSetOptions): Disposer

export interface PanelStickerSetOptions {
  title: string
  icon?: number
  stickers(): PanelSticker[] | Promise<PanelSticker[]>
}
```

adds a sticker set to the stickers tab of this account's panel: a section with the set's title after your installed sets, and a tab in the footer. clicking a sticker sends it to the open chat like any sticker (as a reply when you're replying).

- **grant:** none to register; `account.write(send)` to send (checked on click, a toast explains when it's missing).
- **parameters:**
  - `options.title` (`string`): the section title.
  - `options.icon` (`number`, optional): index of the sticker drawn on the footer tab, `0` by default.
  - `options.stickers` (`() => PanelSticker[] | Promise<PanelSticker[]>`): called once, right away; the set shows when it resolves. up to 200 stickers.
- **returns:** `Disposer` that removes the set.
- **throws:**
  - `TypeError: tg.ui.registerStickerSet({ title, icon?, stickers: () => [...] })` when `stickers` isn't a function.
  - `TypeError: tg.ui.registerStickerSet: title is a non-empty string`.
  - `TypeError: tg.ui.registerStickerSet: icon is the index of a sticker`.
- **notes:**
  - an error in `stickers()` or a bad item (`TypeError: tg.ui.registerStickerSet: sticker 2 is not a webp, tgs or webm file`) is logged to the script console and the set stays hidden.
  - input documents tele doesn't have cached are skipped with a warning; pass full `document` objects (from `messages.getStickerSet`, `messages.getSavedGifs`, a message's media) to be sure.
  - files must be webp, tgs (gzipped lottie) or webm, up to 2 MB here; Telegram's own sticker limits apply on upload (512 px on the longest side; 64 KB tgs, 256 KB webm).
  - script stickers have no right-click menu: no favorites, no send-with-options, no set box.
  - only the main panel (next to the message field) shows script sets, not the mask or profile-photo pickers.

Example:

```ts
// grants: ['account.write(send)', 'fetch(example.com)']
const names = ['cat', 'dog']
tg.ui.registerStickerSet({
  title: 'my pets',
  stickers: () => Promise.all(names.map(async (name) => ({
    bytes: await (await fetch(`https://example.com/stickers/${name}.webp`)).bytes(),
    name: `${name}.webp`,
    emoji: '🐾',
  }))),
})
```

### type PanelSticker

```ts
export interface PanelStickerFile {
  bytes: Uint8Array | ArrayBuffer
  name?: string
  emoji?: string
  width?: number
  height?: number
  duration?: number
}

export type PanelSticker = tl.TypeDocument | tl.TypeInputDocument | PanelStickerFile
```

one sticker of a script set.

- **grant:** none.
- **notes:**
  - `tl.TypeDocument`: a full `document` that is a sticker; sent as it is.
  - `tl.TypeInputDocument`: an `inputDocument` resolved through tele's cache by its `id`; skipped when tele doesn't know it.
  - `PanelStickerFile`: raw webp, tgs or webm bytes; the kind is detected from the content. `name` is the file name (`sticker.webp` by default), `emoji` the sticker's emoji, `width`/`height` the size of a webm (512 by default; a webp's size is read from it), `duration` a webm's length in seconds.

Example:

```ts
// grants: ['account.write(send)', 'call(messages.getStickerSet)']
const set = await tg.call({ _: 'messages.getStickerSet', stickerset: { _: 'inputStickerSetShortName', shortName: 'HotCherry' }, hash: 0 })
if (set._ === 'messages.stickerSet') {
  tg.ui.registerStickerSet({ title: 'cherry', stickers: () => set.documents })
}
```

### tg.ui.registerGifSource(options)

```ts
registerGifSource(options: PanelGifSourceOptions): Disposer

export interface PanelGifSourceOptions {
  title: string
  search(query: string): PanelGif[] | Promise<PanelGif[]>
}
```

answers the GIF tab's search: when the user types a query there, `search(query)` runs and its results show first, before the results of Telegram's GIF bot. clicking one sends it to the open chat as a GIF.

- **grant:** none to register; `account.write(send)` to send (checked on click, a toast explains when it's missing).
- **parameters:**
  - `options.title` (`string`): the source's name, used in error toasts.
  - `options.search` (`(query: string) => PanelGif[] | Promise<PanelGif[]>`): called once per query and account (answers are cached for the last 32 queries); up to 50 results.
- **returns:** `Disposer` that removes the source and its results.
- **throws:**
  - `TypeError: tg.ui.registerGifSource({ title, search: (query) => [...] })` when `search` isn't a function.
  - `TypeError: tg.ui.registerGifSource: title is a non-empty string`.
- **notes:**
  - nothing waits for `search`: the bot's results show as usual and yours appear when they arrive.
  - an error (thrown, rejected or a bad item) is logged to the script console and counts as no results.
  - the footer's emoji categories search too, with the emoji as the query.
  - there is no paging: one answer per query.
  - script results have no right-click menu (no saving to your GIFs, no send-with-options).

Example:

```ts
// grants: ['account.write(send)', 'call(messages.getSavedGifs)']
tg.ui.registerGifSource({
  title: 'my reactions',
  search: async (query) => {
    const saved = await tg.call({ _: 'messages.getSavedGifs', hash: 0n })
    return saved._ === 'messages.savedGifs'
      ? saved.gifs.filter((gif) => gif._ === 'document' && gif.attributes.some((a) => a._ === 'documentAttributeFilename' && a.fileName.includes(query)))
      : []
  },
})
```

### type PanelGif

```ts
export interface PanelGifFile {
  bytes: Uint8Array | ArrayBuffer
  name?: string
  width?: number
  height?: number
  duration?: number
}

export type PanelGif = tl.TypeDocument | PanelGifFile
```

one GIF result.

- **grant:** none.
- **notes:**
  - `tl.TypeDocument`: a full `document` that is an animation or a video; sent as it is.
  - `PanelGifFile`: raw gif or mp4 bytes, up to 10 MB. a gif's size is read from its header; for an mp4 give `width`/`height` (256 by default) and `duration` in seconds (1 by default). `name` is the file name (`animation.gif` by default).

Example:

```ts
const party = await (await fetch('https://example.com/party.gif')).bytes()
tg.ui.registerGifSource({ title: 'party', search: (query) => (query.includes('party') ? [{ bytes: party, name: 'party.gif' }] : []) })
```

### tg.ui.registerEmojiSet(options)

```ts
registerEmojiSet(options: PanelEmojiSetOptions): Disposer

export interface PanelEmojiSetOptions {
  title: string
  emoji(): (bigint | string)[] | Promise<(bigint | string)[]>
}
```

adds a set of custom emoji to the emoji tab of this account's panel, after your own emoji sets, with a footer tab. clicking one inserts it into the message field like any custom emoji; nothing is sent until you send the message.

- **grant:** none.
- **parameters:**
  - `options.title` (`string`): the section title.
  - `options.emoji` (`() => (bigint | string)[] | Promise<(bigint | string)[]>`): custom emoji document ids, called once, right away; up to 200. ids tele doesn't know are fetched with `messages.getCustomEmojiDocuments`.
- **returns:** `Disposer` that removes the set.
- **throws:**
  - `TypeError: tg.ui.registerEmojiSet({ title, emoji: () => [...] })` when `emoji` isn't a function.
  - `TypeError: tg.ui.registerEmojiSet: title is a non-empty string`.
- **notes:**
  - a bad id (`TypeError: tg.ui.registerEmojiSet: emoji 3 is not a custom emoji id (a bigint or a string of digits)`) is logged to the script console and the set stays hidden.
  - custom emoji need Telegram Premium like everywhere else: without it the section shows the unlock button, and when premium can't be bought here the set is hidden.
  - only the main emoji panel shows script sets, not the reaction, status or topic icon pickers.

Example:

```ts
tg.ui.registerEmojiSet({
  title: 'favorites',
  emoji: () => ['5368324170671202286', '5373141891321699086'],
})
```

## media viewer

tele's media viewer (the full-screen window photos, videos and GIFs open in): open it on a message, follow what it shows, add items to its ⋮ menu. none of it needs a grant: the events and contexts carry ids only (chat, message, album position, kind), never the media or the text. to read the message itself use `tg.getMessages` / `tg.getCachedMessage` with their grants.

the viewer is one window for all accounts. a script only hears about media of its own account: for another account's media `tg.ui.mediaViewer()` is `null` and nothing fires.

### type MediaViewerItem

```ts
export interface MediaViewerItem {
  chatId: bigint
  messageId: number
  index: number
  type: MediaType
}
```

the media item the viewer shows, as `tg.ui.mediaViewer()`, `tg.ui.onMediaOpened` and media actions get it.

- **fields:**
  - `chatId` (`bigint`): marked id of the chat the message is in.
  - `messageId` (`number`): the message with the media. in an album every item is its own message, so this is the item's message.
  - `index` (`number`): the position in the album (0 for the first item), or in the paid media of the message; 0 for a single item.
  - `type` (`MediaType`): the kind of the item shown: `'photo'`, `'video'`, `'gif'`, `'roundVideo'`, `'document'` (an image sent as a file) and so on. for paid media it's the kind of the item inside (`'photo'`, `'video'`), not `'paidMedia'`.

Example:

```ts
const item = tg.ui.mediaViewer()
if (item) console.log(item.chatId, item.messageId, item.index, item.type)
```

### type MediaViewerEvent

```ts
export interface MediaViewerEvent extends MediaViewerItem {
  open: boolean
}
```

what `tg.ui.onMediaOpened` gets: a `MediaViewerItem` plus `open`, `true` when the viewer shows this item, `false` when it stopped showing message media (it closed, or moved to something that isn't a message, like a profile photo).

Example:

```ts
tg.ui.onMediaOpened((event: MediaViewerEvent) => {
  if (!event.open) console.log('the viewer stopped showing', event.messageId)
})
```

### type MediaActionOptions

```ts
export interface MediaActionOptions {
  text: string
  emoji?: string
  icon?: MenuIcon
  filter?(context: MediaViewerItem): boolean | Promise<boolean>
  onClick(context: MediaViewerItem): unknown
}
```

the options of `tg.ui.registerMediaAction`.

- **fields:**
  - `text` (`string`): the menu item's label, not empty.
  - `emoji` (`string`, optional): shown before the text.
  - `icon` (`MenuIcon`, optional): the item's icon, see `type MenuIcon`. without it the item gets tele's experimental icon.
  - `filter` (`(context) => boolean | Promise<boolean>`, optional): whether the item shows for this media. without it the item shows on every message media.
  - `onClick` (`(context) => unknown`): runs when the user picks the item.

Example:

```ts
const action: MediaActionOptions = {
  text: 'log this item',
  emoji: '📝',
  filter: (item) => item.type === 'photo',
  onClick: (item) => console.log(item.chatId, item.messageId, item.index),
}
tg.ui.registerMediaAction(action)
```

### tg.ui.openMedia(message, options?)

```ts
openMedia(
  message: Message | { peer: InputPeerLike, id: number },
  options?: { index?: number },
): Promise<void>
```

opens the media viewer on a message's photo or video, as if the user clicked it in the chat: the viewer can then move through the chat's media with the arrows.

- **grant:** none (`account.read(peers)` when `peer` is a bare id or a username).
- **parameters:**
  - `message` (`Message | { peer, id }`): a `Message`, or a chat and a message id in it. a message tele hasn't loaded is fetched first.
  - `options.index` (`number`, optional): the album item to open, 0 for the first. the message can be any item of the album. for a message with several paid media it picks the item inside the message. without it the message itself opens.
- **returns:** `Promise<void>` that resolves once the viewer opens.
- **throws:**
  - rejects with `TypeError` for a missing message, an id that isn't a positive integer, options that aren't an object or an index that isn't a non-negative integer.
  - rejects with `TeleError` `not-found` for a chat tele has never seen, a message that doesn't exist (`there's no message 5 in this chat`) or an index past the end (`the album has 3 items`).
  - rejects with `TeleError` `unsupported` when the message has nothing the viewer opens (`this message has no photo or video`, `a music doesn't open in the media viewer`), for a shared story, paid media that isn't bought, or when the account has no window.
- **notes:** photos, videos, GIFs, round videos and images sent as files open; music, voice messages, stickers and other files don't. with tele's external media viewer option on, photos open there instead, like a click would.

Example:

```ts
tg.registerMessageAction({
  id: 'open_second',
  text: 'Open the second photo',
  onClick: ({ chatId, messageId }) => tg.ui.openMedia({ peer: chatId, id: messageId }, { index: 1 }),
})
```

### tg.ui.onMediaOpened(callback)

```ts
onMediaOpened(callback: (event: MediaViewerEvent) => unknown): Disposer
```

calls `callback` every time the viewer shows a message's media of this account, and once more when it stops.

- **grant:** none.
- **parameters:**
  - `callback` (`(event: MediaViewerEvent) => unknown`): gets `{ chatId, messageId, index, type, open: true }` when the viewer opens or moves to another item (arrows, album thumbnails), and the last item with `open: false` when the viewer closes or moves to something that isn't a message. runs on the next event-loop turn with the 200 ms budget.
- **returns:** `Disposer` that stops the calls.
- **throws:** `TypeError: tg.ui.onMediaOpened(function)`.
- **notes:** it doesn't fire for what's already open when you subscribe; read `tg.ui.mediaViewer()` for that. stories and profile photos aren't messages, so they don't fire `open: true`.

Example:

```ts
tg.ui.onMediaOpened(({ chatId, messageId, open }) => {
  console.log(open ? `viewing ${messageId} in ${chatId}` : 'viewer closed')
})
```

### tg.ui.registerMediaAction(options)

```ts
registerMediaAction(options: MediaActionOptions): Disposer
```

adds an item to the media viewer's ⋮ menu (and its right-click menu) on message media of this account.

- **grant:** none.
- **parameters:**
  - `options` (`MediaActionOptions`): `text`, optional `emoji` and `icon`, optional `filter(context)` and `onClick(context)`. both functions get the item shown as a `MediaViewerItem`.
- **returns:** `Disposer` that removes the item. stopping the script removes it too.
- **throws:** `TypeError` (`tg.ui.registerMediaAction needs a text`, `onClick must be a function`, `filter must be a function`, `emoji must be a string`, or an `icon` problem, see `type MenuIcon`).
- **notes:**
  - `filter` runs when the viewer moves to an item, not when the menu opens, so the menu never waits on a script. until it answers `true` the item stays hidden; a filter that throws or rejects hides it.
  - the item isn't there on stories, profile photos or sponsored media.

Example:

```ts
tg.ui.registerMediaAction({
  text: 'Show ids',
  emoji: '🆔',
  filter: ({ type }) => type === 'photo',
  onClick: ({ chatId, messageId }) => tg.toast(`photo ${messageId} in ${chatId}`),
})
```

### tg.ui.mediaViewer()

```ts
mediaViewer(): MediaViewerItem | null
```

tells what the media viewer shows right now.

- **grant:** none.
- **returns:** `MediaViewerItem | null`: the message media shown, `null` when the viewer is closed or shows something else (a story, a profile photo, another account's media).
- **notes:** cheap and synchronous.

Example:

```ts
const shown = tg.ui.mediaViewer()
if (shown) console.log(`the viewer shows ${shown.type} ${shown.messageId}`)
```

## mini apps

opening bots' mini apps (web apps) and watching what they ask tele to do. opening needs no grant: tele shows the app like it does after a click on a `t.me/bot?startapp` link or a menu button, with the same confirmation for bots you haven't trusted yet, and the bot gets exactly what tdesktop gives it (your name, id, language and theme). the app is bound to the bot's own chat, never to the chat you have open. watching the open apps and their events needs `ui.read`: a mini app window is something tele shows, and its events can carry what you type into the page.

running your own code inside a mini app page isn't provided on purpose: the page belongs to a third party (wallets, shops, games) and a script that could read or change it could take your money or your logins there. for your own pages use `tg.ui.webview`.

### tg.ui.openWebApp(bot, options?)

```ts
openWebApp(bot: InputPeerLike, options?: WebAppOptions): Promise<void>
```

opens a bot's mini app in tele's mini app window.

- **grant:** none (`account.read(peers)` when `bot` is a bare id or a username).
- **parameters:**
  - `bot` (`InputPeerLike`): the bot.
  - `options.url` (`string`, optional): an `http(s)` address of the bot's web app, opened like an inline `web_app` button in the bot's chat. without it tele opens the bot's main mini app (the "open app" button on its profile), or, for a bot without one, the web app of its menu button.
  - `options.startParam` (`string`, optional): the start parameter the app reads as `start_param` (like `?startapp=` in a link): up to 512 of `A-Z`, `a-z`, `0-9`, `_` and `-`.
  - `options.mode` (`WebAppMode`, optional): `'fullscreen'` asks for the full screen, `'compact'` asks for the compact size of the main mini app; the default is the size the bot chose. see `type WebAppMode`.
- **returns:** `Promise<void>` that resolves once the opening is queued; tele then asks for confirmation when needed, loads the app and shows it. if the user declines or the server refuses (a toast shows the error), the app just doesn't open.
- **throws:**
  - rejects with `TypeError` for options that aren't an object, a `url` that isn't an `http(s)` address, a bad `startParam` or `mode`.
  - rejects with `TypeError: this peer isn't in tele's cache` for an input peer of a user tele hasn't loaded.
  - rejects with `TeleError` `not-found` when the peer isn't a bot, `unsupported` when the bot has no mini app (and no `url` was given) or the account has no window.
- **notes:**
  - opening the same bot's app the same way again focuses the window that is already open.
  - for a bot without a main mini app tele loads its full info first to find the menu button (up to 10 s).
  - tele's own options still apply: with "never open web apps in fullscreen" (`tele-webapps-no-fullscreen`) on, `'fullscreen'` opens a normal window.

Example:

```ts
tg.registerChatAction({
  id: 'wallet',
  text: 'open wallet',
  onClick: () => tg.ui.openWebApp('wallet', { mode: 'fullscreen' }),
})
```

### tg.ui.webApps()

```ts
webApps(): WebAppInfo[]
```

lists the mini apps open in this account right now.

- **grant:** `ui.read`.
- **returns:** one `WebAppInfo` (`{ bot, url, mode }`) per open mini app window, see `type WebAppInfo`. apps still loading or waiting for confirmation aren't listed yet; games aren't listed.
- **throws:** `TeleError` `not-granted` without `ui.read`.

Example:

```ts
for (const app of tg.ui.webApps()) console.log(`${app.bot}: ${app.url} (${app.mode})`)
```

### tg.ui.onWebAppEvent(callback)

```ts
onWebAppEvent(callback: (event: WebAppEvent) => unknown): Disposer
```

calls `callback` for every event an open mini app of this account sends to tele (the page's `Telegram.WebApp` calls: `web_app_ready`, `web_app_expand`, `web_app_setup_main_button`, `web_app_open_link`, `web_app_data_send`, ...).

- **grant:** `ui.read`.
- **parameters:**
  - `callback` (`(event) => unknown`): gets a `WebAppEvent` (`{ bot, name, data }`). runs on the next event-loop turn with the 200 ms budget, after tele has already handled the event.
- **returns:** `Disposer` that stops the calls.
- **throws:**
  - `TypeError: tg.ui.onWebAppEvent(function)`.
  - `TeleError` `not-granted` without `ui.read`.
- **notes:**
  - read-only: the callback can't stop, change or answer an event; tele handles every event the same with or without listeners.
  - the `value` of `web_app_device_storage_save_key` and `web_app_secure_storage_save_key` is replaced by `null`: what an app keeps on your device is its own.
  - only events the page sends are reported, not what tele sends back to the page. games aren't reported.

Example:

```ts
tg.ui.onWebAppEvent(({ bot, name, data }) => {
  if (name === 'web_app_open_link') console.log(`bot ${bot} opens ${String(data.url)}`)
})
```

### type WebAppMode

```ts
export type WebAppMode = 'compact' | 'fullsize' | 'fullscreen'
```

the size of a mini app window.

- **values:**
  - `'compact'`: the small window (on phones, the half-height sheet).
  - `'fullsize'`: the full window size the bot asked for.
  - `'fullscreen'`: the window covers the screen.

Example:

```ts
const mode: WebAppMode = 'fullscreen'
await tg.ui.openWebApp('wallet', { mode })
```

### type WebAppOptions

```ts
export interface WebAppOptions {
  url?: string
  startParam?: string
  mode?: WebAppMode
}
```

the options of `tg.ui.openWebApp`.

- **fields:**
  - `url` (`string`, optional): an `http(s)` address of the bot's web app instead of its main mini app.
  - `startParam` (`string`, optional): the start parameter, up to 512 of `A-Z`, `a-z`, `0-9`, `_` and `-`.
  - `mode` (`WebAppMode`, optional): the size to ask for.

Example:

```ts
const options: WebAppOptions = { startParam: 'from_tele', mode: 'compact' }
await tg.ui.openWebApp('wallet', options)
```

### type WebAppInfo

```ts
export interface WebAppInfo {
  bot: bigint
  url: string
  mode: WebAppMode
}
```

an open mini app, as `tg.ui.webApps` lists it.

- **fields:**
  - `bot` (`bigint`): the bot's id.
  - `url` (`string`): the address the app was opened at, without the `tgWebApp...` launch parameters (they carry your signed login data for the bot's server).
  - `mode` (`WebAppMode`): `'fullscreen'` while the window is full screen, otherwise the size the server opened it with.

Example:

```ts
const wallet = tg.ui.webApps().find((app) => app.url.includes('wallet'))
```

### type WebAppEvent

```ts
export interface WebAppEvent {
  bot: bigint
  name: string
  data: Record<string, unknown>
}
```

an event a mini app sent to tele, as `tg.ui.onWebAppEvent` gets it.

- **fields:**
  - `bot` (`bigint`): the id of the bot whose app sent it.
  - `name` (`string`): the event name, `web_app_*` for mini apps (older pages also send a few legacy names like `iframe_ready`).
  - `data` (`Record<string, unknown>`): the event's parameters as the page sent them (an empty object when there are none), for example `{ url }` for `web_app_open_link` or `{ is_visible, text, color }` for `web_app_setup_main_button`.

Example:

```ts
tg.ui.onWebAppEvent((event: WebAppEvent) => {
  if (event.name === 'web_app_data_send') tg.toast(`the app sent data to its bot: ${String(event.data.data)}`)
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
  - `text` (`string`): the text part of the data, `''` when there's none. drags from other apps often carry one (a link's address, a file list); plain text pasted into the field doesn't go through this gate; `tg.compose.interceptPaste` sees it.
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
  addMenuItem(item: { text: string, icon?: MenuIcon, onClick(): unknown }): Disposer
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
addMenuItem(item: { text: string, icon?: MenuIcon, onClick(): unknown }): Disposer
```

adds an item at the bottom of a popup menu (a context menu or a ⋮ menu). the widget may be the menu (`Ui::PopupMenu`) or anything inside it.

- **grant:** `ui.write`.
- **parameters:**
  - `item.text` (`string`): the item's label.
  - `item.icon` (`MenuIcon`, optional): the item's icon, see `type MenuIcon`; drawn only in menus with an icon column.
  - `item.onClick` (`() => unknown`): runs when the item is chosen, on the next event-loop turn, with the 200 ms budget.
- **returns:** `Disposer` that removes the item from the menu (if it's still open).
- **throws:**
  - `TypeError: widget.addMenuItem({ text, onClick })` when `onClick` isn't a function.
  - `TypeError: widget.addMenuItem: <problem>` for a bad `icon`, see `type MenuIcon`.
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

control over tele itself and the computer it runs on: the theme and palette, the window title, badge and focus, the music player, sounds and per-chat notification sounds, calls and video chats, the other logged-in accounts, and running programs. reading state is mostly free; changing it needs `app`, `calls`, `accounts`, `account.write(notify)` (all caution) or `unsafe.exec` (dangerous). everything a script changes here is undone when it stops: palette overrides, title, badge; running programs are killed.

### tg.app

```ts
readonly app: App
```

tele's appearance, window focus, sounds and media controls, see `type App`.

- **grant:** none to read (`theme.get`, `theme.color`, `theme.onChange`, `player.current`, `player.onChange`, `focus`) or to play a sound (`playSound`); `app` (caution, "control tele: the theme and colors, the window title and badge, the music player") for everything that changes something.

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

export interface App {
  playSound(source: SoundSource, options?: PlaySoundOptions): SoundPlayback
}

export interface App {
  readonly focus: AppFocus
}
```

the type of `tg.app`; every member has its own item below. the later blocks are interface merging: `playSound` and `focus` come with the sound and focus features.

- **fields:**
  - `theme`: night mode and the color palette: `get`, `setDark`, `color`, `setColors`, `onChange`.
  - `window`: the main window's title, unread badge and attention flash: `setTitle`, `setBadge`, `flash`.
  - `player`: tele's music and voice player: `current`, `play`, `pause`, `toggle`, `stop`, `next`, `previous`, `onChange`.
  - `playSound` (`(source, options?) => SoundPlayback`): play a sound through tele's audio output.
  - `focus` (`AppFocus`): whether a window of this account is the active one: `focused`, `onChange`.

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

### tg.app.focus

```ts
readonly focus: AppFocus

export interface AppFocus {
  readonly focused: boolean
  onChange(callback: (focused: boolean) => unknown): Disposer
}
```

whether a window of this account is the focused window on the desktop. it lives in `tg.app.focus` rather than `tg.app.window` because `tg.app.window` is a frozen object whose type can't be extended.

- **grant:** none.
- **fields:**
  - `focused` (`boolean`): `true` while the main window or a separate chat window of this account is the active window. `false` when tele is minimized, behind another app, or another account's window (or the media viewer) is in front.
  - `onChange` (`(callback) => Disposer`): see `tg.app.focus.onChange`.
- **notes:** `tg.ui.current().windowActive` is the same check for the main window alone.

Example:

```ts
if (!tg.app.focus.focused) tg.app.window.flash()
```

### tg.app.focus.onChange(callback)

```ts
onChange(callback: (focused: boolean) => unknown): Disposer
```

calls `callback` when this account's windows gain or lose the focus: switching to another app and back, minimizing, clicking another account's window.

- **grant:** none.
- **parameters:**
  - `callback` (`(focused: boolean) => unknown`): gets the new state. runs on the next event-loop turn with the 200 ms budget. moving between two windows of the same account doesn't call it.
- **returns:** `Disposer` that stops the calls.
- **throws:** `TypeError: tg.app.focus.onChange(function)`.

Example:

```ts
let away = 0
tg.app.focus.onChange((focused) => {
  if (!focused) away = Date.now()
  else if (away) tg.toast(`welcome back after ${Math.round((Date.now() - away) / 1000)} s`)
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

### tg.app.playSound(source, options?)

```ts
playSound(source: SoundSource, options?: PlaySoundOptions): SoundPlayback

export type SoundSource = Uint8Array | ArrayBuffer | 'notification'

export interface PlaySoundOptions {
  volume?: number
}
```

plays a sound through tele's own audio output (the one notification sounds use), with no ui.

- **grant:** none.
- **parameters:**
  - `source` (`SoundSource`, that is `Uint8Array | ArrayBuffer | 'notification'`): the bytes of an audio file, or `'notification'`.
    - bytes: any audio file tdesktop's ffmpeg decoder reads: ogg/opus, mp3, wav, flac, m4a and so on. at most 10 MB; the file is decoded off the main thread before it plays.
    - `'notification'`: the sound tele plays for new messages in private chats right now: the user's chosen default sound (Settings > Notifications), a custom ringtone included, or tele's built-in sound. when the user chose "no sound" there, nothing plays and `done` resolves at once.
  - `options.volume` (`number`, optional): from `0` to `1`. without it, bytes play at the notification volume from Settings > Notifications, and `'notification'` at the volume chosen for private chats' sound (or the same notification volume). `0` plays nothing and resolves `done` at once.
- **returns:** `SoundPlayback`: `done` resolves when the sound has finished playing, `stop()` cuts it short.
- **throws:**
  - `TypeError` for a source that isn't bytes or `'notification'`, empty bytes, options that aren't an object, or a `volume` outside `0..1`.
  - `TeleError` `quota-exceeded` for more than 10 MB of bytes.
  - `done` rejects with `TeleError` `unsupported` when tele can't decode the bytes or has no audio output device.
- **notes:** several sounds can play at once. `'notification'` also lowers the music player for its length, like a real notification. every sound stops when the script stops. it plays even when the user turned notification sounds off: a script decides when to call it.

Example:

```ts
const beep = await fetch('https://example.com/beep.ogg').then((response) => response.bytes())
const sound = tg.app.playSound(beep, { volume: 0.5 })
setTimeout(() => sound.stop(), 2000)
await sound.done
```

### type SoundPlayback

```ts
export interface SoundPlayback {
  readonly done: Promise<void>
  stop(): void
  [Symbol.dispose](): void
}
```

one sound started by `tg.app.playSound`.

- **fields:**
  - `done` (`Promise<void>`): resolves when the sound ends by itself or through `stop()`; rejects with `TeleError` `unsupported` when it can't play. it never settles when the script stops first.
  - `stop()`: stops the sound (it may still be decoding, then it never plays) and resolves `done`. calling it again does nothing.
  - `[Symbol.dispose]()`: the same as `stop()`, so `using` stops the sound at the end of the block.

Example:

```ts
{
  using alarm = tg.app.playSound('notification')
  await Promise.race([alarm.done, new Promise<void>((resolve) => setTimeout(resolve, 500))])
}
```

### tg.notifications

```ts
readonly notifications: Notifications

export interface Notifications {
  getSound(peer: InputPeerLike): Promise<NotifySoundInfo>
  setSound(peer: InputPeerLike, sound: NotifySoundChoice): Promise<NotifySoundInfo>
}
```

per-chat notification sounds, the same setting as "Select tone" / "Disable sound" in a chat's mute menu.

- **grant:** none for `getSound`; `account.write(notify)` (caution) for `setSound`.

Example:

```ts
const { kind } = await tg.notifications.getSound('me')
```

### tg.notifications.getSound(peer)

```ts
getSound(peer: InputPeerLike): Promise<NotifySoundInfo>
```

reads the notification sound a chat has on its own, from tele's local data.

- **grant:** none (and `account.read(peers)` when `peer` is a bare id or a username).
- **parameters:**
  - `peer` (`InputPeerLike`): the chat; must be one tele has loaded.
- **returns:** `Promise<NotifySoundInfo>`. `kind: 'default'` means the chat follows the default sound for its type (private chats, groups or channels). when tele doesn't know the chat's settings yet, it asks the server first and waits up to 5 s; it also loads the saved ringtones list to find a custom sound's title.
- **throws:**
  - rejects with `TypeError` for something that isn't a peer.
  - rejects with `TeleError` `not-found` for a chat tele hasn't loaded.
  - rejects with `TeleError` `timed-out` when the chat's settings don't arrive within 5 s.

Example:

```ts
const sound = await tg.notifications.getSound(message)
console.log(sound.kind === 'custom' ? `ringtone ${sound.title}` : sound.kind)
```

### tg.notifications.setSound(peer, sound)

```ts
setSound(peer: InputPeerLike, sound: NotifySoundChoice): Promise<NotifySoundInfo>

export type NotifySoundChoice =
  | 'default'
  | 'none'
  | { bytes: Uint8Array | ArrayBuffer, name: string }
```

changes a chat's notification sound through tdesktop's own notify settings path: the chat list, the mute menu and the profile update at once, and the change goes to the server (as `account.updateNotifySettings`) a moment later, exactly as when the user picks a tone.

- **grant:** `account.write(notify)` (and `account.read(peers)` when `peer` is a bare id or a username).
- **parameters:**
  - `peer` (`InputPeerLike`): the chat; must be one tele has loaded.
  - `sound` (`NotifySoundChoice`):
    - `'default'`: follow the default sound for the chat's type.
    - `'none'`: no sound (notifications still show).
    - `{ bytes, name }`: a new custom sound. `bytes` (`Uint8Array | ArrayBuffer`) is an audio file, `name` (`string`) its file name, shown as the tone's title (without the extension). it's uploaded like the "Upload sound" button of the tone picker does (`account.uploadRingtone`, which also adds it to the account's saved ringtones), then set as the chat's sound. telegram limits ringtones: by default 100 KB and 5 seconds (app config `ringtone_size_max`, `ringtone_duration_max`), and mp3 is the safe format (tdesktop's own picker only offers mp3; ogg usually works too).
- **returns:** `Promise<NotifySoundInfo>` with the new setting (`id` and `title` for an uploaded sound).
- **throws:**
  - rejects with `TypeError` for a bad `sound` (another string, missing or empty `bytes`, an empty `name`) or something that isn't a peer.
  - rejects with `TeleError` `not-granted` without the grant.
  - rejects with `TeleError` `not-found` for a chat tele hasn't loaded.
  - rejects with `TeleError` `quota-exceeded` for bytes over the size limit, or when telegram refuses the duration (`RINGTONE_DURATION_TOO_LONG`) or size (`RINGTONE_SIZE_TOO_BIG`).
  - rejects with `TeleError` `unsupported` when telegram doesn't take the format (`RINGTONE_MIME_INVALID`).
  - rejects with `TeleError` `network` when the upload fails or for any other server error (its type is in the message).
- **notes:** this is the account's own setting: it stays after the script stops; an upload still in progress is cancelled when the script stops. tdesktop ignores Saved Messages' own sound when it plays notifications (they follow the private chats' default), but the setting is still stored and synced. the chat's mute state and the other notification settings don't change.

Example:

```ts
const tone = await fetch('https://example.com/ding.mp3').then((response) => response.bytes())
await tg.notifications.setSound('@durov', { bytes: tone, name: 'ding.mp3' })
await tg.notifications.setSound('me', 'none')
```

### type NotifySoundInfo

```ts
export interface NotifySoundInfo {
  kind: 'default' | 'none' | 'custom'
  id?: bigint
  title?: string
}
```

a chat's own notification sound.

- **fields:**
  - `kind`: `'default'` follows the default sound for the chat's type, `'none'` is silent, `'custom'` is a ringtone.
  - `id` (`bigint`, optional): the ringtone's document id, for `'custom'` sounds from the account's saved ringtones.
  - `title` (`string`, optional): the ringtone's title as tele's tone picker shows it, when tele knows it.

Example:

```ts
const { kind, title } = await tg.notifications.getSound('me')
```

### tg.calls

```ts
readonly calls: Calls
```

this account's voice and video calls (one-to-one calls, and group calls / video chats through `group`, `join`, `leave`, `raiseHand`, `participants`, `onGroupChange`). see `type Calls`.

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

export interface Calls {
  group(): GroupCallInfo | null
  onGroupChange(callback: (call: GroupCallInfo | null, changes: GroupCallChange[]) => unknown): Disposer
  join(chat: InputPeerLike, options?: { muted?: boolean, joinAs?: InputPeerLike }): Promise<GroupCallInfo>
  leave(): boolean
  raiseHand(raised: boolean): boolean
  participants(chat?: InputPeerLike, options?: { limit?: number }): Promise<GroupCallParticipant[]>
}
```

the type of `tg.calls`; the second block is interface merging, added with group calls.

- **fields:**
  - `current` (`() => CallInfo | null`): the ongoing call.
  - `answer` (`() => boolean`): answer the incoming call.
  - `hangup` (`() => boolean`): end or decline.
  - `setMuted` (`(muted: boolean) => boolean`): mute or unmute the microphone.
  - `start` (`(user, options?) => Promise<void>`): call someone.
  - `onChange` (`(callback) => Disposer`): follow state changes.
  - `group` (`() => GroupCallInfo | null`): the group call or video chat you're in.
  - `onGroupChange` (`(callback) => Disposer`): follow it.
  - `join` (`(chat, options?) => Promise<GroupCallInfo>`): join a chat's video chat.
  - `leave` (`() => boolean`): leave it.
  - `raiseHand` (`(raised: boolean) => boolean`): raise or lower your hand.
  - `participants` (`(chat?, options?) => Promise<GroupCallParticipant[]>`): who is in a group call.

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

mutes or unmutes your microphone in the call. with no one-to-one call, it mutes or unmutes you in the group call or video chat you're in.

- **grant:** `calls`.
- **parameters:**
  - `muted` (`boolean`): `true` to mute.
- **returns:** `boolean`: `false` when this account is in neither kind of call, or when an admin muted you in a group call and you ask to unmute; `true` otherwise.
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

### tg.calls.group()

```ts
group(): GroupCallInfo | null
```

reads the group call or video chat this account is in (voice chats in groups, video chats and live streams in channels, conference calls).

- **grant:** `calls`.
- **returns:** `GroupCallInfo | null`: the call with its participants, `null` when this account isn't in one (or the one tele is in belongs to another account).
- **throws:** `TeleError` `not-granted` without the grant.
- **notes:**
  - tele is in one call at a time: while it's in a group call, `tg.calls.current()` is `null`, and the other way round.
  - `tg.calls.setMuted(muted)` works here too: with no one-to-one call it mutes or unmutes you in the group call, and returns `false` when there's neither or when an admin muted you and you ask to unmute.

Example:

```ts
const call = tg.calls.group()
if (call) console.log(`${call.peer.name}: ${call.count} people, ${call.participants.filter((p) => p.speaking).length} talking`)
```

### tg.calls.onGroupChange(callback)

```ts
onGroupChange(callback: (call: GroupCallInfo | null, changes: GroupCallChange[]) => unknown): Disposer
```

calls `callback` when this account joins or leaves a group call, when the call changes state (connecting, joined, scheduled, recording, title, who you join as, your microphone), and when its participants come, go, mute, raise or lower a hand, turn video on, or start and stop talking.

- **grant:** `calls`.
- **parameters:**
  - `callback` (`(call: GroupCallInfo | null, changes: GroupCallChange[]) => unknown`): gets the call's new snapshot (`null` once you left) and what changed since the last call. runs on the next event-loop turn with the 200 ms budget.
- **returns:** `Disposer` that stops the calls.
- **throws:**
  - `TypeError: tg.calls.onGroupChange(function)`.
  - `TeleError` `not-granted` without the grant.
- **notes:**
  - changes are batched for 250 ms, so a burst of updates arrives as one call with several `changes`.
  - talking is rate-limited: a change where only `'speaking'` differs comes at most once a second; any other change comes with the next 250 ms batch and carries the latest talking state too.
  - it doesn't fire on registration; read `tg.calls.group()` for the state at that moment.

Example:

```ts
tg.calls.onGroupChange((call, changes) => {
  if (!call) return console.log('left the video chat')
  if (changes.includes('raisedHand')) {
    const hands = call.participants.filter((p) => p.raisedHand).map((p) => p.peer.name)
    if (hands.length) tg.toast(`hands up: ${hands.join(', ')}`)
  }
})
```

### tg.calls.join(chat, options?)

```ts
join(chat: InputPeerLike, options?: { muted?: boolean, joinAs?: InputPeerLike }): Promise<GroupCallInfo>
```

joins the group call or video chat that is going on in a group or a channel, the same as its join button.

- **grant:** `calls` (and `account.read(peers)` when `chat` or `joinAs` is a bare id or a username).
- **parameters:**
  - `chat` (`InputPeerLike`): the group or channel with the call; must be one tele has loaded.
  - `options.muted` (`boolean`, optional): join with the microphone off (default `true`). `false` unmutes you once you're in, unless an admin keeps you muted.
  - `options.joinAs` (`InputPeerLike`, optional): who to appear as: you, or a channel you own that telegram offers for this call. it becomes the chat's default for joining.
- **returns:** `Promise<GroupCallInfo>` that resolves once you're in (or registered for a scheduled call), with the call's snapshot. already in that call: it applies `muted` and resolves right away.
- **throws:**
  - rejects with `TeleError` `not-granted` without the grant.
  - rejects with `TypeError: tg.calls.join needs a group or a channel tele has loaded` for a user or an unknown peer, and `TypeError: tg.calls.join: joinAs must be a peer tele has loaded`.
  - rejects with `TeleError` `not-found` when nothing is going on in that chat (it never starts a new call).
  - rejects with `TeleError` `timed-out` when you're not in after 60 s, for example because the user cancelled one of tele's boxes.
  - rejects with `TeleError` `internal` when joining fails or the call ends meanwhile, `unsupported` when the account has no window, and `RpcError` when telegram refuses to give the chat's info.
- **notes:**
  - tele's usual flow runs: if you're in another call, tele asks before leaving it; if telegram offers several identities and none was chosen before (or `joinAs` isn't one of them), tele shows its "join as" box. the promise waits for those.
  - the call panel opens like after a click.

Example:

```ts
tg.registerChatAction({
  id: 'listen',
  text: 'listen in (muted)',
  visible: (ctx) => ctx.chat.kind !== 'user',
  onClick: async (ctx) => {
    const call = await tg.calls.join(ctx.chat, { muted: true })
    tg.toast(`in ${call.title || call.peer.name} with ${call.count} people`)
  },
})
```

### tg.calls.leave()

```ts
leave(): boolean
```

leaves the group call this account is in, like the leave button. the call goes on for everyone else.

- **grant:** `calls`.
- **returns:** `boolean`: `false` when this account isn't in a group call, `true` otherwise.
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.calls.onGroupChange((call) => {
  if (call?.joined && call.count <= 1) tg.calls.leave()
})
```

### tg.calls.raiseHand(raised)

```ts
raiseHand(raised: boolean): boolean
```

raises or lowers your hand in the group call. a hand only means something while an admin keeps you muted: it asks them to let you talk.

- **grant:** `calls`.
- **parameters:**
  - `raised` (`boolean`): `true` to raise, `false` to lower.
- **returns:** `boolean`: `true` when your hand is now as asked; `false` when there's no group call, or when you raise it but you may already talk (or it's a live stream or a conference call, which have no hands).
- **throws:** `TeleError` `not-granted` without the grant.

Example:

```ts
tg.calls.onGroupChange((call, changes) => {
  if (call && changes.includes('state') && call.mute === 'forceMuted') tg.calls.raiseHand(true)
})
```

### tg.calls.participants(chat?, options?)

```ts
participants(chat?: InputPeerLike, options?: { limit?: number }): Promise<GroupCallParticipant[]>
```

lists who is in a group call, also one you aren't in.

- **grant:** `calls` (and `account.read(peers)` when `chat` is a bare id or a username).
- **parameters:**
  - `chat` (`InputPeerLike`, optional): the group or channel with the call. leave it out for the call you're in.
  - `options.limit` (`number`, optional): at most this many (default 100, capped at 5000).
- **returns:** `Promise<GroupCallParticipant[]>`. for the call you're in, the list tele already has (`speaking` is live); for another chat, a fresh list from telegram (`phone.getGroupParticipants`, in pages of 100), where `speaking` is always `false`.
- **throws:**
  - rejects with `TeleError` `not-granted` without the grant.
  - rejects with `TypeError: tg.calls.participants needs a group or a channel tele has loaded` and `TypeError: tg.calls.participants: limit must be a positive integer`.
  - rejects with `TeleError` `not-found` when there's no call in that chat, or no `chat` and you're not in a call.
  - rejects with `RpcError` when telegram refuses (for example a private channel you're not in).
- **notes:** peers telegram sends that tele can't load are left out.

Example:

```ts
const people = await tg.calls.participants('@durov_russia', { limit: 20 })
console.log(people.map((p) => `${p.peer.name}${p.muted ? '' : ' (mic on)'}`).join('\n'))
```

### type GroupCallInfo

```ts
export interface GroupCallInfo {
  peer: PeerInfo
  title: string
  state: GroupCallState
  joined: boolean
  joinAs: PeerInfo
  mute: GroupCallMute
  muted: boolean
  mutedByAdmin: boolean
  raisedHand: boolean
  stream: boolean
  count: number
  recording: boolean
  scheduled: number | null
  participants: GroupCallParticipant[]
}
```

a snapshot of the group call this account is in.

- **fields:**
  - `peer` (`PeerInfo`): the group or channel of the call.
  - `title` (`string`): the call's own title, `''` when it has none (tele shows the chat's name then).
  - `state` (`GroupCallState`): where joining is.
  - `joined` (`boolean`): `true` once you're in and connected (`state === 'joined'`).
  - `joinAs` (`PeerInfo`): who you appear as: you or one of your channels.
  - `mute` (`GroupCallMute`): your microphone in detail.
  - `muted` (`boolean`): `true` unless your microphone is on (`'active'` or `'pushToTalk'`).
  - `mutedByAdmin` (`boolean`): an admin keeps you muted (or it's a live stream you only watch).
  - `raisedHand` (`boolean`): your hand is up.
  - `stream` (`boolean`): a live stream from an external app (rtmp) instead of a voice chat.
  - `count` (`number`): how many people are in, by telegram's count (more than `participants` in big calls).
  - `recording` (`boolean`): the call is being recorded.
  - `scheduled` (`number | null`): unix time the call is scheduled to start, `null` when it's live.
  - `participants` (`GroupCallParticipant[]`): the participants tele has loaded, you included.

Example:

```ts
const call = tg.calls.group()
if (call?.recording) tg.toast('this video chat is being recorded')
```

### type GroupCallParticipant

```ts
export interface GroupCallParticipant {
  peer: PeerInfo
  self: boolean
  speaking: boolean
  muted: boolean
  mutedByAdmin: boolean
  raisedHand: boolean
  video: boolean
  screen: boolean
}
```

one person (or channel) in a group call.

- **fields:**
  - `peer` (`PeerInfo`): who it is.
  - `self` (`boolean`): it's you (as `joinAs`).
  - `speaking` (`boolean`): talking right now (tele keeps it on for about 1.5 s after the voice stops). always `false` in lists fetched for a call you aren't in.
  - `muted` (`boolean`): their microphone is off.
  - `mutedByAdmin` (`boolean`): muted by an admin, can't unmute themselves.
  - `raisedHand` (`boolean`): their hand is up.
  - `video` (`boolean`): their camera is on.
  - `screen` (`boolean`): they share their screen.

Example:

```ts
const talking = tg.calls.group()?.participants.filter((p) => p.speaking && !p.self) ?? []
```

### type GroupCallState

```ts
export type GroupCallState =
  | 'creating'
  | 'waiting'
  | 'joining'
  | 'connecting'
  | 'joined'
  | 'failedHangingUp'
  | 'failed'
  | 'hangingUp'
  | 'ended'
  | 'unknown'
```

tdesktop's group call state in camelCase.

- **grant:** none.
- **notes:**
  - `'creating'`, `'joining'`, `'connecting'`: on the way in.
  - `'waiting'`: in a scheduled call that hasn't started.
  - `'joined'`: in and connected.
  - `'hangingUp'`, `'failedHangingUp'`: leaving.
  - `'ended'`, `'failed'`: over.
  - `'unknown'`: a state tele doesn't know a name for.

Example:

```ts
tg.calls.onGroupChange((call) => {
  if (call?.state === 'waiting' && call.scheduled) console.log('starts at', new Date(call.scheduled * 1000))
})
```

### type GroupCallMute

```ts
export type GroupCallMute = 'active' | 'pushToTalk' | 'muted' | 'forceMuted' | 'raisedHand'
```

your microphone in a group call.

- **grant:** none.
- **notes:**
  - `'active'`: on.
  - `'pushToTalk'`: on while the push-to-talk key is held.
  - `'muted'`: off, you can turn it on.
  - `'forceMuted'`: an admin muted you; raise your hand to ask.
  - `'raisedHand'`: muted by an admin, hand up.

Example:

```ts
const call = tg.calls.group()
if (call?.mute === 'muted') tg.calls.setMuted(false)
```

### type GroupCallChange

```ts
export type GroupCallChange = 'state' | 'participants' | 'raisedHand' | 'speaking'
```

what changed in a `tg.calls.onGroupChange` call.

- **grant:** none.
- **notes:**
  - `'state'`: joined or left, the state, your microphone, who you join as, the title, recording, the schedule.
  - `'participants'`: someone came or went, muted or unmuted, turned video or screen sharing on or off, or the total count moved.
  - `'raisedHand'`: a hand went up or down (yours too).
  - `'speaking'`: someone started or stopped talking.

Example:

```ts
tg.calls.onGroupChange((call, changes) => {
  if (changes.includes('participants')) console.log(`${call?.count ?? 0} in the call`)
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
- **notes:**
  - while tele is starting, the list has only the accounts loaded so far, none of them `active`. call it again later, for example from a timer, for the full list.

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

- **grant:** `fetch(translate.googleapis.com)` for the translation service, `display(messages)` to show the translation under the message.
- **notes:** `tg.decorateMessage` changes nothing on the server: other people never see the translation. the endpoint used is google's public one; swap in any translation api (and its `fetch(...)` grant).

Example:

```ts
import { defineScript } from 'tele'
import type { Disposer } from 'tele'

export default defineScript({
  name: 'quick translate',
  description: 'translate any message in place',
  icon: '🌐',
  grants: ['fetch(translate.googleapis.com)', 'display(messages)'],
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

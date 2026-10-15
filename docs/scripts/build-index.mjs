import { readdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs'

const root = new URL('./', import.meta.url)
const fields = ['name', 'description', 'author', 'icon', 'version', 'homepage']
const required = ['name', 'description', 'author', 'version']
const literal = String.raw`'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"`
const decode = (token) => Function(`return ${token}`)()

const peek = (id, source) => {
  const start = source.indexOf('defineScript({')
  if (start < 0) throw new Error(`${id}: no defineScript({ ... })`)
  const end = source.indexOf('\n  setup(', start)
  const head = source.slice(start, end < 0 ? undefined : end)
  const meta = {}
  for (const field of fields) {
    const match = head.match(new RegExp(String.raw`\n  ${field}: (${literal}),`))
    if (match) meta[field] = decode(match[1])
  }
  for (const field of required) {
    if (!meta[field]) throw new Error(`${id}: defineScript has no ${field}`)
  }
  const grants = head.match(/\n  grants: \[([^\]]*)\]/)
  const { name, description, author, icon, version, homepage } = meta
  return {
    id,
    name,
    description,
    author,
    icon,
    grants: grants ? [...grants[1].matchAll(new RegExp(literal, 'g'))].map((m) => decode(m[0])) : [],
    version,
    homepage,
  }
}

const entries = readdirSync(root, { withFileTypes: true })
  .filter((dirent) => dirent.isDirectory())
  .map((dirent) => dirent.name)
  .sort()
  .map((id) => {
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(id)) throw new Error(`${id}: an id is lowercase words joined by -`)
    const file = new URL(`${id}/script.ts`, root)
    if (!existsSync(file)) throw new Error(`${id}: no script.ts`)
    return peek(id, readFileSync(file, 'utf8').replace(/\r\n/g, '\n'))
  })

writeFileSync(new URL('index.json', root), JSON.stringify(entries, null, 2) + '\n')
console.log(`index.json: ${entries.length} scripts`)

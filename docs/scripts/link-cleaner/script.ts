import { defineScript } from 'tele'

export default defineScript({
  name: 'link cleaner',
  description: 'strips tracking parameters from links you open',
  icon: '🧹',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/link-cleaner',
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

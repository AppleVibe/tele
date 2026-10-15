import { defineScript } from 'tele'

export default defineScript({
  name: 'drop guard',
  description: 'stops risky files from being dropped into chats',
  icon: '🛡️',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/drop-guard',
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

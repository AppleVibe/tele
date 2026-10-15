import { defineScript } from 'tele'

export default defineScript({
  name: 'quiet hours',
  description: 'no notifications at night, mentions still come through',
  icon: '🤫',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/quiet-hours',
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

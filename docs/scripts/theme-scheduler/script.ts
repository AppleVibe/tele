import { defineScript } from 'tele'
import type { Disposer } from 'tele'

export default defineScript({
  name: 'theme scheduler',
  description: 'night mode by the clock',
  icon: '🌗',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/theme-scheduler',
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

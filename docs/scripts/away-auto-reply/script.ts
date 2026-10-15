import { defineScript } from 'tele'

export default defineScript({
  name: 'away auto-reply',
  description: 'answers private messages once while you are away',
  icon: '💤',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/away-auto-reply',
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

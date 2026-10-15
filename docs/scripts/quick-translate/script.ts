import { defineScript } from 'tele'
import type { Disposer } from 'tele'

export default defineScript({
  name: 'quick translate',
  description: 'translate any message in place',
  icon: '🌐',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/quick-translate-button',
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

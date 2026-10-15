import { defineScript } from 'tele'

export default defineScript({
  name: 'compose snippets',
  description: 'expand short codes while you type',
  icon: '✂️',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/compose-snippets',
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

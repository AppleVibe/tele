import { defineScript } from 'tele'
import type { NowPlaying } from 'tele'

export default defineScript({
  name: 'music status',
  description: 'shows the song you listen to in your bio',
  icon: '🎵',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/music-status-in-your-bio',
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

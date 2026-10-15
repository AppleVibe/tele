import { defineScript } from 'tele'

export default defineScript({
  name: 'call assistant',
  description: 'music pause, auto-mute and a call log',
  icon: '📞',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/call-assistant',
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

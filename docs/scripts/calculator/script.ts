import { defineScript } from 'tele'

export default defineScript({
  name: 'calculator',
  description: '/calc for quick math in any chat',
  icon: '🧮',
  version: '1.0.0',
  author: 'tele',
  homepage: 'https://gettele.app/scripting/calculator-command',
  setup(tg) {
    const evaluate = (source: string): number => {
      const tokens = source.match(/\d+(?:\.\d+)?|[-+*/%^()]/g) ?? []
      if (tokens.join('') !== source.replace(/\s+/g, '')) throw new Error(`not arithmetic: ${source}`)
      let index = 0
      const peek = () => tokens[index]
      const take = () => tokens[index++]
      const primary = (): number => {
        const token = take()
        if (token === '(') {
          const value = sum()
          if (take() !== ')') throw new Error('a ) is missing')
          return value
        }
        if (token === '-') return -primary()
        if (token === '+') return primary()
        if (token === undefined || !/^\d/.test(token)) throw new Error(`unexpected ${token ?? 'end'}`)
        return Number(token)
      }
      const power = (): number => {
        const base = primary()
        if (peek() !== '^') return base
        take()
        return base ** power()
      }
      const product = (): number => {
        let value = power()
        while (peek() === '*' || peek() === '/' || peek() === '%') {
          const operator = take()
          const right = power()
          value = operator === '*' ? value * right : operator === '/' ? value / right : value % right
        }
        return value
      }
      const sum = (): number => {
        let value = product()
        while (peek() === '+' || peek() === '-') {
          const operator = take()
          const right = product()
          value = operator === '+' ? value + right : value - right
        }
        return value
      }
      const result = sum()
      if (index !== tokens.length) throw new Error(`unexpected ${peek()}`)
      return result
    }

    tg.registerCommand({
      name: 'calc',
      description: 'calculate and send the result',
      args: 'expression',
      run: (args, ctx) => {
        const expression = args.trim()
        if (!expression) {
          ctx.setText('/calc ')
          return
        }
        const value = evaluate(expression)
        if (!Number.isFinite(value)) throw new Error(`${expression} has no finite result`)
        return `${expression} = ${Number(value.toPrecision(12))}`
      },
    })
  },
})

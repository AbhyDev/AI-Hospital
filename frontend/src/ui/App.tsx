import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import './glass.css'

type ChatItem = {
  role: 'assistant' | 'user'
  content: string
  speaker?: 'GP' | 'Specialist' | 'Radiologist' | 'Pathologist' | 'Assistant'
}

type AskEvent = {
  thread_id: string
  speaker?: 'GP' | 'Specialist' | 'Radiologist' | 'Pathologist' | 'Assistant'
}

type MessageEventData = {
  thread_id: string
  content: string
  speaker?: 'GP' | 'Specialist' | 'Radiologist' | 'Pathologist' | 'Assistant'
}

const BACKEND = import.meta.env.VITE_API_BASE || '' // use proxy when ''

export default function App() {
  const [threadId, setThreadId] = useState<string | null>(null)
  const [chat, setChat] = useState<ChatItem[]>([])
  const [pendingAsk, setPendingAsk] = useState<AskEvent | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Cursor-driven glow & subtle tilt
  useEffect(() => {
    const el = containerRef.current ?? document.documentElement
    let raf = 0
    const handle = (e: MouseEvent) => {
      const x = e.clientX
      const y = e.clientY
      document.documentElement.style.setProperty('--mx', `${x}px`)
      document.documentElement.style.setProperty('--my', `${y}px`)
      if (containerRef.current) {
        // Parallax tilt relative to center
        const rect = containerRef.current.getBoundingClientRect()
        const cx = rect.left + rect.width / 2
        const cy = rect.top + rect.height / 2
        const dx = (x - cx) / rect.width
        const dy = (y - cy) / rect.height
        cancelAnimationFrame(raf)
        raf = requestAnimationFrame(() => {
          containerRef.current!.style.setProperty('--tiltX', `${(-dy * 4).toFixed(2)}deg`)
          containerRef.current!.style.setProperty('--tiltY', `${(dx * 6).toFixed(2)}deg`)
        })
      }
    }
    window.addEventListener('mousemove', handle)
    return () => {
      window.removeEventListener('mousemove', handle)
      cancelAnimationFrame(raf)
    }
  }, [])

  const startStream = useCallback((userText: string) => {
    const url = `${BACKEND}/api/graph/start/stream?message=${encodeURIComponent(userText)}`
    const es = new EventSource(url)

    es.addEventListener('thread', (e) => {
      const data = JSON.parse((e as MessageEvent).data)
      setThreadId(data.thread_id)
    })

    es.addEventListener('message', (e) => {
      const data = JSON.parse((e as MessageEvent).data) as MessageEventData
      if (!data.content?.trim()) return // Do not render empty messages
      setChat((c) => {
        const last = c[c.length - 1]
        if (last && last.role === 'assistant' && last.content === data.content) return c
        return [...c, { role: 'assistant', content: data.content, speaker: data.speaker }]
      })
    })

    es.addEventListener('ask_user', (e) => {
      const data = JSON.parse((e as MessageEvent).data) as AskEvent
      setPendingAsk(data)
      es.close()
    })

    es.addEventListener('final', (e) => {
      const data = JSON.parse((e as MessageEvent).data) as { thread_id: string; message: string | null }
      if (data.message) setChat((c) => [...c, { role: 'assistant', content: data.message! }])
      es.close()
    })

    es.onerror = () => {
      es.close()
    }
  }, [])

  const resumeStream = useCallback((tid: string, reply: string) => {
    const url = `${BACKEND}/api/graph/resume/stream?thread_id=${encodeURIComponent(tid)}&user_reply=${encodeURIComponent(reply)}`
    const es = new EventSource(url)
    setPendingAsk(null)
  setChat((c) => [...c, { role: 'user', content: reply }])

    es.addEventListener('message', (e) => {
      const data = JSON.parse((e as MessageEvent).data) as MessageEventData
      if (!data.content?.trim()) return // Do not render empty messages
      setChat((c) => {
        const last = c[c.length - 1]
        if (last && last.role === 'assistant' && last.content === data.content) return c
        return [...c, { role: 'assistant', content: data.content, speaker: data.speaker }]
      })
    })

    es.addEventListener('ask_user', (e) => {
      const data = JSON.parse((e as MessageEvent).data) as AskEvent
      setPendingAsk(data)
      es.close()
    })

    es.addEventListener('final', (e) => {
      const data = JSON.parse((e as MessageEvent).data) as { thread_id: string; message: string | null }
      if (data.message) setChat((c) => [...c, { role: 'assistant', content: data.message! }])
      es.close()
    })

    es.onerror = () => {
      es.close()
    }
  }, [])

  const onSubmit = useCallback((e: FormEvent) => {
    e.preventDefault()
    const val = inputRef.current?.value?.trim()
    if (!val) return
    if (!threadId) {
      setChat((prev: ChatItem[]) => [...prev, { role: 'user', content: val }])
      startStream(val)
    } else if (pendingAsk?.thread_id === threadId) {
      resumeStream(threadId, val)
    }
    if (inputRef.current) inputRef.current.value = ''
  }, [threadId, pendingAsk, startStream, resumeStream])

  return (
    <div className="app-root">
      <div className="liquid-bg" />
      <div className="cursor-glow" />
      <div ref={containerRef} className="container glass tilt">
        <header className="header">
          <h1>AI Hospital</h1>
          <div className="badge">Live</div>
        </header>
        <main className="chat glass-inner">
          {chat.map((m: ChatItem, i: number) => (
            <div key={i} className={`bubble ${m.role === 'user' ? 'user' : 'assistant'}`}>
              {m.role === 'assistant' && (
                <div className="speaker">{m.speaker || 'AI'}</div>
              )}
              <div className="content">{m.content}</div>
            </div>
          ))}
          {pendingAsk && (
            <div className="bubble assistant ask">
              <div className="speaker">{pendingAsk.speaker || 'Question'}</div>
              <div className="content">
                {[...chat].reverse().find(m => m.role === 'assistant')?.content || '(Waiting for your answer...)'}
              </div>
            </div>
          )}
        </main>
        <form onSubmit={onSubmit} className="composer glass-inner">
          <input ref={inputRef} className="input" type="text" placeholder={threadId ? 'Type your answer…' : 'Describe your issue…'} />
          <button className="btn" type="submit">{threadId ? (pendingAsk ? 'Answer' : 'Continue') : 'Start'}</button>
        </form>
        <footer className="footer">
          Backend base: {BACKEND || '(proxy /api → http://localhost:8000)'}
        </footer>
      </div>
    </div>
  )
}

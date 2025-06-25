import { useState, useRef, useEffect } from 'react'
import Message from './Message'
import InputForm from './InputForm'

export interface CitationType {
  no: number
  id: string
  datetime: string
  name_and_trip: string
}

export interface MessageType {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  citations?: CitationType[]
}

const ChatInterface = () => {
  const [messages, setMessages] = useState<MessageType[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (question: string) => {
    // ユーザーのメッセージを追加
    const userMessage: MessageType = {
      role: 'user',
      content: question,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    // AIアシスタントのメッセージを初期化
    const assistantMessage: MessageType = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      citations: []
    }
    setMessages(prev => [...prev, assistantMessage])

    try {
      const response = await fetch('/api/v1/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('Response body is not readable')
      }

      let buffer = ''
      
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        buffer += chunk

        // SSEのデータをパース
        const lines = buffer.split('\n')
        buffer = lines[lines.length - 1] // 未処理の部分を保持

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim()
          
          if (line.startsWith('data: ')) {
            const dataStr = line.substring(6)
            if (dataStr) {
              try {
                const data = JSON.parse(dataStr)
                
                // タイプ別の処理
                if (data.type === 'error') {
                  throw new Error(data.error)
                } else if (data.type === 'done') {
                  // 完了
                  setIsLoading(false)
                } else if (data.type === 'citations') {
                  // 出典情報を追加
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMessage = newMessages[newMessages.length - 1]
                    if (lastMessage && lastMessage.role === 'assistant') {
                      lastMessage.citations = data.citations
                    }
                    return newMessages
                  })
                } else if (data.type === 'token') {
                  // トークンを追加
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMessage = newMessages[newMessages.length - 1]
                    if (lastMessage && lastMessage.role === 'assistant') {
                      lastMessage.content += data.token
                    }
                    return newMessages
                  })
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', e)
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => {
        const newMessages = [...prev]
        const lastMessage = newMessages[newMessages.length - 1]
        if (lastMessage && lastMessage.role === 'assistant') {
          lastMessage.content = 'エラーが発生しました。もう一度お試しください。'
        }
        return newMessages
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full w-full max-w-6xl mx-auto">
      <div className="flex-1 overflow-y-auto p-5 bg-gray-50 dark:bg-gray-900">
        {messages.map((message, index) => (
          <Message key={index} message={message} />
        ))}
        {isLoading && (
          <div className="flex justify-center items-center p-5 gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }}></span>
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }}></span>
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }}></span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <InputForm onSend={handleSend} disabled={isLoading} />
    </div>
  )
}

export default ChatInterface
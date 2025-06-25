import { useState, FormEvent, KeyboardEvent } from 'react'

interface InputFormProps {
  onSend: (message: string) => void
  disabled?: boolean
}

const InputForm = ({ onSend, disabled = false }: InputFormProps) => {
  const [input, setInput] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      handleSubmit(e as any)
    }
  }

  return (
    <form className="border-t border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-800" onSubmit={handleSubmit}>
      <div className="flex gap-4 items-end">
        <textarea
          className="flex-1 p-3 border border-gray-300 dark:border-gray-600 rounded-lg resize-none bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="質問を入力してください..."
          disabled={disabled}
          rows={3}
        />
        <button
          type="submit"
          className="px-6 py-3 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white rounded-lg font-medium transition-colors disabled:cursor-not-allowed"
          disabled={disabled || !input.trim()}
        >
          送信
        </button>
      </div>
      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
        Shift + Enter で改行、Enter で送信
      </div>
    </form>
  )
}

export default InputForm
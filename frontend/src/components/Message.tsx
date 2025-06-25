import { MessageType, CitationType } from './ChatInterface'

interface MessageProps {
  message: MessageType
}

const Citation = ({ citation }: { citation: CitationType }) => {
  const formatDateTime = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleString('ja-JP', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-md text-xs">
      <span className="font-mono font-medium text-blue-600 dark:text-blue-400">
        No.{citation.no}
      </span>
      <span className="text-gray-600 dark:text-gray-400">
        {citation.name_and_trip}
      </span>
      <span className="text-gray-500 dark:text-gray-500">
        {formatDateTime(citation.datetime)}
      </span>
    </div>
  )
}

const Message = ({ message }: MessageProps) => {
  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString('ja-JP', {
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const isUser = message.role === 'user'
  const baseClasses = 'mb-5 p-4 rounded-lg shadow-sm'
  const userClasses = 'bg-blue-100 dark:bg-blue-900 ml-auto max-w-[80%]'
  const assistantClasses = 'bg-white dark:bg-gray-800 mr-auto max-w-[80%]'

  return (
    <div className={`${baseClasses} ${isUser ? userClasses : assistantClasses}`}>
      <div className="flex justify-between items-center mb-2 text-sm">
        <span className="font-semibold text-gray-700 dark:text-gray-300">
          {isUser ? 'あなた' : 'AIアシスタント'}
        </span>
        <span className="text-gray-500 dark:text-gray-400 text-xs">
          {formatTime(message.timestamp)}
        </span>
      </div>
      <div className="text-gray-800 dark:text-gray-200 leading-relaxed">
        {message.content.split('\n').map((line, index) => (
          <p key={index} className="my-1 whitespace-pre-wrap break-words">
            {line || '\u00A0'}
          </p>
        ))}
      </div>
      
      {/* 出典情報の表示 */}
      {!isUser && message.citations && message.citations.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">
            出典:
          </div>
          <div className="flex flex-wrap gap-2">
            {message.citations.map((citation, idx) => (
              <Citation key={idx} citation={citation} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Message
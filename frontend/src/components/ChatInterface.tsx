import React, { useState, useRef, useEffect } from 'react';
import { Message } from './Message';
import { InputForm } from './InputForm';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (question: string) => {
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: question }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/v1/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let aiResponse = '';

        // Add empty assistant message
        setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.substring(6);
              if (data) {
                try {
                  const parsed = JSON.parse(data);
                  
                  if (parsed.type === 'complete') {
                    // Response complete
                    break;
                  } else if (parsed.type === 'error') {
                    throw new Error(parsed.message);
                  } else if (parsed.token) {
                    aiResponse += parsed.token;
                    // Update the last message
                    setMessages(prev => {
                      const newMessages = [...prev];
                      newMessages[newMessages.length - 1].content = aiResponse;
                      return newMessages;
                    });
                  }
                } catch (e) {
                  console.error('Error parsing SSE data:', e);
                }
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'エラーが発生しました。もう一度お試しください。',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto p-4">
      <h1 className="text-2xl font-bold text-center mb-6">掲示板 RAG チャット</h1>
      
      <div className="flex-1 overflow-y-auto mb-4 border border-gray-300 rounded-lg p-4 bg-white">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            掲示板について質問してください
          </div>
        ) : (
          messages.map((message, index) => (
            <Message key={index} role={message.role} content={message.content} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <InputForm onSend={handleSend} disabled={isLoading} />
    </div>
  );
};
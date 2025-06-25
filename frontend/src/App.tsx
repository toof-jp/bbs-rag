import ChatInterface from './components/ChatInterface'

function App() {
  return (
    <div className="flex flex-col h-screen w-full">
      <header className="bg-gray-800 dark:bg-gray-900 text-white p-5 text-center">
        <h1 className="text-3xl font-bold m-0">掲示板AIアシスタント</h1>
        <p className="mt-2 opacity-80">掲示板の過去ログについて質問してください</p>
      </header>
      <main className="flex-1 flex overflow-hidden">
        <ChatInterface />
      </main>
    </div>
  )
}

export default App
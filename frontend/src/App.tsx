import React from 'react';
import { ChatInterface } from './components/ChatInterface';

function App() {
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto h-screen py-8">
        <ChatInterface />
      </div>
    </div>
  );
}

export default App;
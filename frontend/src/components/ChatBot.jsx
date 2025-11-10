import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import TriageSummary from './TriageSummary'
import ProvidersButton from './ProvidersButton'
import './ChatBot.css'

/** Helper: Detect messages that come from location or doctor search */
const isLocationMessage = (message) => {
  return (
    message.includes('📍') ||
    message.includes('🏥') ||
    message.toLowerCase().includes('nearby') ||
    message.toLowerCase().includes('location')
  )
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function ChatBot({ language, llmProvider, prefillMessage, symptomData, onSessionIdChange }) {
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [conversationComplete, setConversationComplete] = useState(false)
  const [triageResult, setTriageResult] = useState(null)
  const [showProviders, setShowProviders] = useState(false)
  const messagesEndRef = useRef(null)
  const prefillSentRef = useRef(false)

  // Initialize session + welcome message
  useEffect(() => {
    initializeSession()

    const welcomeMessage = {
      role: 'assistant',
      content:
        "👋 Hello! I'm HealthGuide, your AI assistant for the Fever Helpline.\nI understand you're concerned about a fever. Can you tell me about your symptoms?",
      timestamp: new Date().toISOString(),
    }
    setMessages([welcomeMessage])
  }, [])

  // Auto-send prefill message when provided
  useEffect(() => {
    if (prefillMessage && prefillMessage.trim() && !prefillSentRef.current && sessionId) {
      prefillSentRef.current = true
      setTimeout(() => {
        handleSendMessage(prefillMessage, true)
      }, 500)
    } else if (prefillMessage && prefillMessage.trim() && !sessionId) {
      // If we have a prefill message but no session, wait a bit for session to be created
      const checkSession = setInterval(() => {
        if (sessionId) {
          clearInterval(checkSession)
          prefillSentRef.current = true
          setTimeout(() => {
            handleSendMessage(prefillMessage, true)
          }, 500)
        }
      }, 100)
      
      // Clear interval after 5 seconds to avoid infinite loop
      setTimeout(() => clearInterval(checkSession), 5000)
    }
  }, [prefillMessage, sessionId])

  // Auto-scroll when messages update
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  /** Initialize backend session (or fallback) */
  const initializeSession = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/session`)
      const newSessionId = response.data.session_id
      setSessionId(newSessionId)
      onSessionIdChange?.(newSessionId)
      // Store in localStorage for smart find doctor
      localStorage.setItem('healthguide_session_id', newSessionId)
    } catch (error) {
      console.error('Error initializing session:', error)
      const fallbackSessionId = `session-${Date.now()}`
      setSessionId(fallbackSessionId)
      onSessionIdChange?.(fallbackSessionId)
      localStorage.setItem('healthguide_session_id', fallbackSessionId)
    }
  }

  /** Handle user message send */
  const handleSendMessage = async (message, isPrefill = false) => {
    if (!message.trim() || loading) return

    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    }

    // 🟢 If message is location/doctor info, just display it (no backend call)
    if (isLocationMessage(message)) {
      setMessages((prev) => [...prev, userMessage])
      return
    }

    // Otherwise, send to backend
    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    try {
      // Prepare conversation history
      const conversationHistory = messages.map((msg) => ({
        role: msg.role,
        content: msg.content,
      }))

      // Prepare payload
      const requestPayload = {
        session_id: sessionId,
        message,
        conversation_history: conversationHistory,
        llm_provider: llmProvider || 'openai',
      }

      // Include structured symptom data (for prefill message)
      if (symptomData && isPrefill) {
        requestPayload.symptom_data = {
          symptoms: symptomData.symptoms || [],
          by_category: symptomData.byCategory || null,
          emergency_detected: symptomData.emergencyDetected || false,
          total_selected: symptomData.totalSelected || 0,
          language: symptomData.language || language,
        }
      }

      // Call backend /api/triage
      const response = await axios.post(`${API_BASE_URL}/api/triage`, requestPayload)

      // Add assistant message
      const assistantMessage = {
        role: 'assistant',
        content: response.data.message,
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMessage])

      // Update triage summary + flags
      if (response.data.triage_result) {
        setTriageResult(response.data.triage_result)
        setConversationComplete(response.data.conversation_complete)
        
        // Store triage level in localStorage for smart find doctor
        if (response.data.triage_result.triage_level) {
          localStorage.setItem('healthguide_triage_level', response.data.triage_result.triage_level)
        }
      }

      // Auto-show providers if red flag detected
      if (response.data.triage_result?.red_flag_detected) {
        setShowProviders(true)
        setConversationComplete(true)
      }
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = {
        role: 'assistant',
        content:
          "⚠️ Sorry, I'm having trouble processing your request. Please try again or contact emergency services if this is urgent.",
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chatbot-container">
      <div className="chatbot-messages">
        <MessageList messages={messages} loading={loading} />
        <div ref={messagesEndRef} />
      </div>

      {conversationComplete && triageResult && (
        <TriageSummary triageResult={triageResult} />
      )}

      {conversationComplete && (
        <ProvidersButton
          show={showProviders || conversationComplete}
          onToggle={() => setShowProviders(!showProviders)}
        />
      )}

      <MessageInput
        onSendMessage={handleSendMessage}
        disabled={loading || conversationComplete}
        placeholder={loading ? 'Thinking...' : 'Type your message...'}
        language={language}
      />
    </div>
  )
}

export default ChatBot

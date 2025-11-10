// frontend/src/App.jsx
import React, { useState, useEffect } from 'react'
import ChatBot from './components/ChatBot'
import Disclaimer from './components/Disclaimer'
import LanguageSelector from './components/LanguageSelector'
import LLMProviderSelector from './components/LLMProviderSelector'
import SymptomSelector from './components/SymptomSelector'
import TemperatureChart from './components/TemperatureChart'
import TemperatureSelector from './components/TemperatureSelector'
import ProbableCause from './components/ProbableCause'
import LocationPermission from './components/LocationPermission'
import NearbyProviders from './components/NearbyProviders'
import MedicationReminder from './components/MedicationReminder'
import HomeCareCard from './components/HomeCareCard'
import ThemeToggle from './components/ThemeToggle'
import AccessibilityToggle from './components/AccessibilityToggle'
import QuickActions from './components/QuickActions'
import DoctorMap from './components/DoctorMap'
import './App.css'

function App() {
  const [language, setLanguage] = useState('en')
  const [llmProvider, setLlmProvider] = useState('openai')
  const [showDisclaimer, setShowDisclaimer] = useState(true)
  const [prefillMessage, setPrefillMessage] = useState('')
  const [symptomData, setSymptomData] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [showDoctorMap, setShowDoctorMap] = useState(false)
  const [userCoords, setUserCoords] = useState(null)
  const [temperatureData, setTemperatureData] = useState(null)
  const [probableCauses, setProbableCauses] = useState([])
  const [locationPermission, setLocationPermission] = useState(null)
  const [nearbyProviders, setNearbyProviders] = useState([])
  const [homeCareTips, setHomeCareTips] = useState([])
  const [medicationSuggestions, setMedicationSuggestions] = useState(null)
  const [smartFindData, setSmartFindData] = useState(null)

  useEffect(() => {
    const disclaimerShown = localStorage.getItem('disclaimerShown')
    if (disclaimerShown) setShowDisclaimer(false)
  }, [])

  const handleDisclaimerAccept = () => {
    setShowDisclaimer(false)
    localStorage.setItem('disclaimerShown', 'true')
  }

  const handleSymptomsSubmit = async (payload, summaryText) => {
    setSymptomData(payload)
    // Store symptoms in localStorage for smart find doctor
    localStorage.setItem('healthguide_symptoms', JSON.stringify(payload.symptoms || []))
    
    // Create a natural, conversational message for the triage endpoint
    // This will be sent to the LLM through ChatBot with structured symptom_data
    const symptomsList = payload.symptoms.join(', ')
    const triageMessage = `I have these symptoms: ${symptomsList}.`
    
    setPrefillMessage(triageMessage)
    // Trigger disease detection
    detectDisease(payload.symptoms || [])
  }

  const handleTemperatureSubmit = async (tempData) => {
    // Get session ID from localStorage if not available in state
    const currentSessionId = sessionId || localStorage.getItem('healthguide_session_id')
    
    if (!currentSessionId) {
      console.error('No session ID available. Creating a new session...')
      // Try to create a session first
      try {
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        const sessionResponse = await fetch(`${API_BASE_URL}/api/session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
        const sessionData = await sessionResponse.json()
        const newSessionId = sessionData.session_id
        setSessionId(newSessionId)
        localStorage.setItem('healthguide_session_id', newSessionId)
        
        // Now proceed with temperature assessment
        await submitTemperature(newSessionId, tempData)
      } catch (error) {
        console.error('Error creating session:', error)
        alert('Please start a conversation first before adding temperature.')
        return
      }
    } else {
      await submitTemperature(currentSessionId, tempData)
    }
  }
  
  const submitTemperature = async (currentSessionId, tempData) => {
    setTemperatureData(tempData)
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_BASE_URL}/api/temperature/assess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessionId,
          temperature_celsius: tempData.type === 'numeric' && tempData.unit === 'C' ? tempData.value : null,
          temperature_fahrenheit: tempData.type === 'numeric' && tempData.unit === 'F' ? tempData.value : null,
          descriptive: tempData.type === 'descriptive' ? tempData.value : null
        })
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to assess temperature')
      }
      
      const result = await response.json()
      setTemperatureData(result)
      
      // Create a natural message about temperature for the chat
      const tempMessage = tempData.type === 'numeric' 
        ? `My temperature is ${tempData.value}°${tempData.unit}.`
        : `I feel ${tempData.value?.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}.`
      
      // Add temperature to chat conversation
      setPrefillMessage(tempMessage)
      
      // Trigger disease detection with temperature category
      if (symptomData?.symptoms) {
        detectDisease(symptomData.symptoms, result.category)
      }
    } catch (error) {
      console.error('Error assessing temperature:', error)
      alert(`Error: ${error.message || 'Failed to assess temperature. Please try again.'}`)
    }
  }

  const detectDisease = async (symptoms, temperatureCategory = null) => {
    if (!symptoms || symptoms.length === 0) return
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const response = await fetch(`${API_BASE_URL}/api/disease/detect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symptoms: symptoms,
          temperature_category: temperatureCategory,
          duration_days: symptomData?.duration_days,
          additional_context: {}
        })
      })
      const data = await response.json()
      setProbableCauses(data.probable_causes || [])
      if (data.probable_causes && data.probable_causes.length > 0) {
        setHomeCareTips(data.probable_causes[0].home_care || [])
      }
      // Store medication suggestions for the ProbableCause component
      if (data.medication_suggestions) {
        setMedicationSuggestions(data.medication_suggestions)
      }
    } catch (error) {
      console.error('Error detecting disease:', error)
    }
  }

  const handleLocationPermission = (coords) => {
    setLocationPermission(coords)
    setUserCoords(coords)
    // Fetch nearby providers
    fetchNearbyProviders(coords.lat, coords.lon)
  }

  const fetchNearbyProviders = async (lat, lon, smartData = null) => {
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      
      // Use smart-find if we have session data, otherwise use regular endpoint
      const sessionId = localStorage.getItem('healthguide_session_id')
      const triageLevel = localStorage.getItem('healthguide_triage_level')
      const symptoms = JSON.parse(localStorage.getItem('healthguide_symptoms') || '[]')
      
      if (smartData) {
        // Use provided smart find data
        setNearbyProviders(smartData.providers || [])
        setSmartFindData(smartData)
        return
      }
      
      // Try smart-find endpoint
      if (sessionId) {
        const response = await fetch(`${API_BASE_URL}/api/providers/smart-find`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            latitude: lat,
            longitude: lon,
            radius_km: 10,
            provider_type: 'hospital',
            session_id: sessionId,
            triage_level: triageLevel,
            symptoms: symptoms
          })
        })
        
        if (response.ok) {
          const data = await response.json()
          setNearbyProviders(data.providers || [])
          setSmartFindData(data)
          return
        }
      }
      
      // Fallback to regular endpoint
      const response = await fetch(`${API_BASE_URL}/api/providers/nearby`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: lat,
          longitude: lon,
          radius_km: 5,
          provider_type: 'hospital',
          limit: 10
        })
      })
      const data = await response.json()
      setNearbyProviders(data)
    } catch (error) {
      console.error('Error fetching nearby providers:', error)
    }
  }

  const handleQuickAction = (action, data = null) => {
    switch (action) {
      case 'fever':
        setPrefillMessage('I have a fever. Can you help me assess my symptoms?')
        break
      case 'emergency':
        setPrefillMessage('EMERGENCY: I need immediate medical attention.')
        break
      case 'find-doctor':
        if (data && data.latitude && data.longitude) {
          // Handle smart find data from QuickActions
          setUserCoords({ lat: data.latitude, lon: data.longitude })
          setShowDoctorMap(true)
          fetchNearbyProviders(data.latitude, data.longitude, data)
        } else {
          setShowDoctorMap(true)
        }
        break
      default:
        break
    }
  }

  // Check if providers view should be shown (full page)
  const showProvidersView = (showDoctorMap && userCoords) || (nearbyProviders.length > 0 && userCoords) || (smartFindData && userCoords);

  return (
    <div className="App">
      {/* Nearby Providers - Full Page View (outside container) */}
      {showProvidersView ? (
        <NearbyProviders 
          providers={nearbyProviders}
          userLocation={userCoords}
          smartFindData={smartFindData}
          onClose={() => {
            setShowDoctorMap(false)
            setSmartFindData(null)
            setNearbyProviders([])
          }}
        />
      ) : (
        <div className="app-container">
          <header className="app-header">
            <div className="header-top">
              <h1>🌡️ HealthGuide</h1>
              <div className="header-actions">
                <ThemeToggle />
                <AccessibilityToggle />
              </div>
            </div>
            <p className="subtitle">Fever Helpline - Your AI Health Assistant</p>
            <div className="header-controls">
              <LanguageSelector language={language} onLanguageChange={setLanguage} />
              <LLMProviderSelector provider={llmProvider} onProviderChange={setLlmProvider} />
            </div>
          </header>

          {showDisclaimer && <Disclaimer onAccept={handleDisclaimerAccept} language={language} />}

          {/* Quick Actions */}
          <QuickActions 
            onAction={(action, data) => {
              if (action === 'find-doctor' && data) {
                handleQuickAction(action, data)
              } else {
                handleQuickAction(action)
              }
            }}
            onMapOpen={(lat, lon, smartData) => {
              setUserCoords({ lat, lon })
              setShowDoctorMap(true)
              if (smartData) {
                setSmartFindData(smartData)
                setNearbyProviders(smartData.providers || [])
              }
            }} 
            language={language} 
          />

          {/* Symptom Selector */}
          <SymptomSelector onSubmit={handleSymptomsSubmit} language={language} />

          {/* Temperature Selector - Show if session exists or if symptoms are selected */}
          {(sessionId || symptomData) && (
            <TemperatureSelector 
              onSubmit={handleTemperatureSubmit}
            />
          )}

          {/* Temperature Chart */}
          {sessionId && <TemperatureChart sessionId={sessionId} />}

          {/* Probable Cause Detection */}
          {probableCauses.length > 0 && (
            <ProbableCause 
              probableCauses={probableCauses}
              homeCare={homeCareTips}
              medications={medicationSuggestions}
            />
          )}

          {/* Home Care Card */}
          {homeCareTips.length > 0 && (
            <HomeCareCard 
              homeCareTips={homeCareTips}
              diseaseName={probableCauses[0]?.disease}
            />
          )}

          {/* Location Permission */}
          {!userCoords && (
            <LocationPermission 
              onLocationGranted={handleLocationPermission}
            />
          )}

          {/* Medication Reminder */}
          {sessionId && (
            <MedicationReminder 
              sessionId={sessionId}
              onReminderCreated={(reminder) => {
                console.log('Reminder created:', reminder)
              }}
            />
          )}

          {/* ChatBot */}
          <ChatBot 
            language={language} 
            llmProvider={llmProvider} 
            prefillMessage={prefillMessage}
            symptomData={symptomData}
            onSessionIdChange={setSessionId}
          />
        </div>
      )}
    </div>
  )
}

export default App

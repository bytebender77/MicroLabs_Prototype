import { FaExclamationTriangle, FaStethoscope, FaHospital } from 'react-icons/fa'
import './QuickActions.css'

function QuickActions({ onAction, onMapOpen, language = 'en' }) {
  const actions = {
    en: {
      fever: { label: 'I have fever', icon: FaStethoscope, action: 'fever' },
      emergency: { label: 'Emergency', icon: FaExclamationTriangle, action: 'emergency' },
      findDoctor: { label: 'Find Doctor', icon: FaHospital, action: 'find-doctor' }
    },
    hi: {
      fever: { label: 'मुझे बुखार है', icon: FaStethoscope, action: 'fever' },
      emergency: { label: 'आपातकाल', icon: FaExclamationTriangle, action: 'emergency' },
      findDoctor: { label: 'डॉक्टर खोजें', icon: FaHospital, action: 'find-doctor' }
    }
  }

  const currentActions = actions[language] || actions.en

  const handleClick = async (action) => {
    // 🚨 Emergency Action
    if (action === 'emergency') {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: 'User reports a medical emergency. Provide immediate steps and safety guidance.'
        })
      })
      const data = await res.json()
      onAction?.('🚨 Emergency Advice:\n' + (data.reply || 'Please seek immediate help!'))
      return
    }

    // 🏥 Find Doctor Action - Smart Find
    if (action === 'find-doctor') {
      if (!navigator.geolocation) {
        onAction?.('⚠️ Geolocation not supported.')
        return
      }

      onAction?.('📍 Getting your location and assessing your situation... please allow permission.')

      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords
          onAction?.(`✅ Location found. Analyzing your situation...`)

          // 🗺️ Trigger map modal or section
          onMapOpen?.(latitude, longitude)

          try {
            // Get session ID and triage info from localStorage or context
            const sessionId = localStorage.getItem('healthguide_session_id')
            const triageLevel = localStorage.getItem('healthguide_triage_level')
            const symptoms = JSON.parse(localStorage.getItem('healthguide_symptoms') || '[]')
            
            const payload = {
              latitude,
              longitude,
              radius_km: 10,
              provider_type: 'hospital'
            }
            
            // Use smart-find endpoint
            const res = await fetch('http://localhost:8000/api/providers/smart-find', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                ...payload,
                session_id: sessionId,
                triage_level: triageLevel,
                symptoms: symptoms
              })
            })
            
            if (!res.ok) throw new Error('Failed to fetch providers')
            
            const data = await res.json()
            
            // Show smart response with ambulance assessment
            if (data.smart_response) {
              onAction?.(data.smart_response)
            }
            
            // Store providers for map display
            if (data.providers && data.providers.length > 0) {
              // Trigger map with providers and smart data
              onMapOpen?.(latitude, longitude, data)
            }
            
            // If ambulance is needed, show urgent alert
            if (data.assessment?.needs_ambulance) {
              const emergencyNumbers = data.emergency_numbers || {}
              const alertMessage = `🚨 URGENT: Ambulance may be needed!\n\n📞 Emergency Numbers:\n${Object.entries(emergencyNumbers).map(([key, value]) => `${key}: ${value}`).join('\n')}\n\nPlease call immediately if symptoms are severe!`
              setTimeout(() => {
                if (window.confirm(alertMessage + '\n\nWould you like to call ambulance now?')) {
                  if (emergencyNumbers.ambulance) {
                    window.location.href = `tel:${emergencyNumbers.ambulance}`
                  }
                }
              }, 500)
            }
          } catch (err) {
            console.error('Find doctor error:', err)
            onAction?.('❌ Failed to fetch providers. Please try again.')
          }
        },
        (err) => {
          console.error('Geolocation error:', err)
          const messages = {
            1: '❌ Permission denied. Please allow location access.',
            2: '⚠️ Location unavailable.',
            3: '⌛ Request timed out.'
          }
          onAction?.(messages[err.code] || '❌ Could not fetch location.')
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
      )
      return
    }

    // 🩺 Fever Action
    if (onAction) onAction(action)
  }

  return (
    <div className="quick-actions">
      <h3 className="quick-actions-title">Quick Actions</h3>
      <div className="quick-actions-grid">
        {Object.values(currentActions).map((item, index) => {
          const Icon = item.icon
          return (
            <button
              key={index}
              className={`quick-action-btn ${item.action}`}
              onClick={() => handleClick(item.action)}
              aria-label={item.label}
            >
              <Icon className="quick-action-icon" />
              <span className="quick-action-label">{item.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default QuickActions

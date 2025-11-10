from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import MedicationReminder, save_medication_reminder, get_medication_reminders, deactivate_medication_reminder


class MedicationService:
    """
    Medication reminder service for tracking and scheduling medication doses.
    """
    
    FREQUENCY_OPTIONS = {
        "once": {"label": "Once", "times_per_day": 1, "interval_hours": None},
        "daily": {"label": "Once daily", "times_per_day": 1, "interval_hours": 24},
        "2x_daily": {"label": "Twice daily", "times_per_day": 2, "interval_hours": 12},
        "3x_daily": {"label": "Three times daily", "times_per_day": 3, "interval_hours": 8},
        "4x_daily": {"label": "Four times daily", "times_per_day": 4, "interval_hours": 6},
        "every_6_hours": {"label": "Every 6 hours", "times_per_day": 4, "interval_hours": 6},
        "every_8_hours": {"label": "Every 8 hours", "times_per_day": 3, "interval_hours": 8},
        "every_12_hours": {"label": "Every 12 hours", "times_per_day": 2, "interval_hours": 12},
    }
    
    @staticmethod
    def create_reminder(
        db: Session,
        session_id: str,
        medication_name: str,
        dosage: str,
        frequency: str,
        duration_days: int,
        notes: Optional[str] = None,
        start_time: Optional[datetime] = None
    ) -> MedicationReminder:
        """
        Create a new medication reminder.
        """
        if frequency not in MedicationService.FREQUENCY_OPTIONS:
            raise ValueError(f"Invalid frequency: {frequency}")
        
        reminder = save_medication_reminder(
            db=db,
            session_id=session_id,
            medication_name=medication_name,
            dosage=dosage,
            frequency=frequency,
            duration_days=duration_days,
            notes=notes
        )
        return reminder
    
    @staticmethod
    def get_reminder_schedule(reminder: MedicationReminder) -> List[Dict]:
        """
        Calculate reminder schedule times for a medication reminder.
        """
        if reminder.frequency not in MedicationService.FREQUENCY_OPTIONS:
            return []
        
        frequency_info = MedicationService.FREQUENCY_OPTIONS[reminder.frequency]
        interval_hours = frequency_info.get("interval_hours")
        
        if not interval_hours:
            # One-time dose
            return [{
                "dose_number": 1,
                "scheduled_time": reminder.start_date.isoformat(),
                "status": "pending"
            }]
        
        schedule = []
        current_time = reminder.start_date
        dose_number = 1
        
        # Calculate all doses for the duration
        while current_time <= reminder.end_date and dose_number <= reminder.duration_days * frequency_info["times_per_day"]:
            schedule.append({
                "dose_number": dose_number,
                "scheduled_time": current_time.isoformat(),
                "status": "pending" if current_time > datetime.now() else "missed"
            })
            current_time += timedelta(hours=interval_hours)
            dose_number += 1
        
        return schedule
    
    @staticmethod
    def get_active_reminders(db: Session, session_id: str) -> List[Dict]:
        """
        Get all active medication reminders for a session with schedule.
        """
        reminders = get_medication_reminders(db, session_id, active_only=True)
        
        result = []
        for reminder in reminders:
            schedule = MedicationService.get_reminder_schedule(reminder)
            result.append({
                "id": reminder.id,
                "medication_name": reminder.medication_name,
                "dosage": reminder.dosage,
                "frequency": reminder.frequency,
                "frequency_label": MedicationService.FREQUENCY_OPTIONS.get(
                    reminder.frequency, {}
                ).get("label", reminder.frequency),
                "duration_days": reminder.duration_days,
                "start_date": reminder.start_date.isoformat(),
                "end_date": reminder.end_date.isoformat() if reminder.end_date else None,
                "notes": reminder.notes,
                "schedule": schedule,
                "next_dose": schedule[0] if schedule else None,
                "total_doses": len(schedule)
            })
        
        return result
    
    @staticmethod
    def stop_reminder(db: Session, reminder_id: int) -> bool:
        """
        Stop/deactivate a medication reminder.
        """
        return deactivate_medication_reminder(db, reminder_id)
    
    @staticmethod
    def get_frequency_options() -> Dict:
        """
        Get available frequency options.
        """
        return {
            "options": [
                {
                    "value": key,
                    "label": info["label"],
                    "times_per_day": info["times_per_day"],
                    "interval_hours": info["interval_hours"]
                }
                for key, info in MedicationService.FREQUENCY_OPTIONS.items()
            ]
        }
    
    @staticmethod
    def get_upcoming_doses(db: Session, session_id: str, hours_ahead: int = 24) -> List[Dict]:
        """
        Get upcoming medication doses in the next N hours.
        """
        reminders = get_medication_reminders(db, session_id, active_only=True)
        upcoming = []
        cutoff_time = datetime.now() + timedelta(hours=hours_ahead)
        
        for reminder in reminders:
            schedule = MedicationService.get_reminder_schedule(reminder)
            for dose in schedule:
                dose_time = datetime.fromisoformat(dose["scheduled_time"].replace("Z", "+00:00"))
                if datetime.now() <= dose_time <= cutoff_time:
                    upcoming.append({
                        "reminder_id": reminder.id,
                        "medication_name": reminder.medication_name,
                        "dosage": reminder.dosage,
                        "scheduled_time": dose["scheduled_time"],
                        "dose_number": dose["dose_number"],
                        "notes": reminder.notes
                    })
        
        # Sort by scheduled time
        upcoming.sort(key=lambda x: x["scheduled_time"])
        return upcoming


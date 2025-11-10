from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.database import FeverTrendDB
import json

class AnalyticsService:
    """
    Analytics service for fever trend monitoring and outbreak detection.
    Used by public health teams and administrators.
    """
    
    @staticmethod
    def log_fever_case(
        db: Session,
        session_id: str,
        location_data: Dict,
        symptom_data: Dict,
        triage_result: Dict
    ):
        """
        Log anonymized fever case for trend analysis.
        """
        # Round coordinates for privacy (2 decimal places = ~1km precision)
        lat_rounded = str(round(location_data.get('latitude', 0), 2)) if location_data.get('latitude') else None
        lon_rounded = str(round(location_data.get('longitude', 0), 2)) if location_data.get('longitude') else None
        
        trend_entry = FeverTrendDB(
            session_id=session_id,
            timestamp=datetime.utcnow(),
            city=location_data.get('city'),
            region=location_data.get('region'),
            country=location_data.get('country', 'India'),
            latitude_rounded=lat_rounded,
            longitude_rounded=lon_rounded,
            temperature_category=symptom_data.get('temperature_category'),
            probable_disease=triage_result.get('probable_disease'),
            triage_level=triage_result.get('triage_level'),
            age_group=symptom_data.get('age_group'),
            symptoms=symptom_data.get('symptoms', []),
            fever_duration_days=symptom_data.get('duration_days'),
            red_flag_detected=triage_result.get('red_flag_detected', False),
            emergency_referral=triage_result.get('emergency_referral', False)
        )
        
        db.add(trend_entry)
        db.commit()
    
    @staticmethod
    def get_geographic_trends(
        db: Session,
        days: int = 7,
        country: str = "India"
    ) -> List[Dict]:
        """
        Get geographic fever trends for heatmap visualization.
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        trends = db.query(
            FeverTrendDB.city,
            FeverTrendDB.region,
            FeverTrendDB.latitude_rounded,
            FeverTrendDB.longitude_rounded,
            func.count(FeverTrendDB.trend_id).label('case_count'),
            func.count(func.nullif(FeverTrendDB.red_flag_detected, False)).label('emergency_count')
        ).filter(
            and_(
                FeverTrendDB.timestamp >= start_date,
                FeverTrendDB.country == country,
                FeverTrendDB.latitude_rounded.isnot(None)
            )
        ).group_by(
            FeverTrendDB.city,
            FeverTrendDB.region,
            FeverTrendDB.latitude_rounded,
            FeverTrendDB.longitude_rounded
        ).all()
        
        return [
            {
                "city": t.city,
                "region": t.region,
                "latitude": float(t.latitude_rounded) if t.latitude_rounded else None,
                "longitude": float(t.longitude_rounded) if t.longitude_rounded else None,
                "case_count": t.case_count,
                "emergency_count": t.emergency_count,
                "severity": "high" if t.case_count > 10 else "medium" if t.case_count > 5 else "low"
            }
            for t in trends
        ]
    
    @staticmethod
    def get_disease_distribution(
        db: Session,
        days: int = 7,
        region: Optional[str] = None
    ) -> Dict:
        """
        Get distribution of probable diseases.
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(
            FeverTrendDB.probable_disease,
            func.count(FeverTrendDB.trend_id).label('count')
        ).filter(
            FeverTrendDB.timestamp >= start_date
        )
        
        if region:
            query = query.filter(FeverTrendDB.region == region)
        
        results = query.group_by(
            FeverTrendDB.probable_disease
        ).all()
        
        total = sum(r.count for r in results)
        
        return {
            "total_cases": total,
            "distribution": [
                {
                    "disease": r.probable_disease,
                    "count": r.count,
                    "percentage": round((r.count / total * 100), 1) if total > 0 else 0
                }
                for r in results if r.probable_disease
            ]
        }
    
    @staticmethod
    def get_time_series_data(
        db: Session,
        days: int = 30,
        disease: Optional[str] = None
    ) -> List[Dict]:
        """
        Get time series data for trend charts.
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = db.query(
            func.date(FeverTrendDB.timestamp).label('date'),
            func.count(FeverTrendDB.trend_id).label('cases'),
            func.count(func.nullif(FeverTrendDB.emergency_referral, False)).label('emergencies')
        ).filter(
            FeverTrendDB.timestamp >= start_date
        )
        
        if disease:
            query = query.filter(FeverTrendDB.probable_disease == disease)
        
        results = query.group_by(
            func.date(FeverTrendDB.timestamp)
        ).order_by(
            func.date(FeverTrendDB.timestamp)
        ).all()
        
        return [
            {
                "date": r.date.isoformat(),
                "cases": r.cases,
                "emergencies": r.emergencies
            }
            for r in results
        ]
    
    @staticmethod
    def detect_potential_outbreaks(
        db: Session,
        threshold_multiplier: float = 2.0
    ) -> List[Dict]:
        """
        Detect potential disease outbreaks based on unusual spike in cases.
        """
        # Get last 7 days data
        recent_start = datetime.utcnow() - timedelta(days=7)
        # Get baseline (previous 30 days)
        baseline_start = datetime.utcnow() - timedelta(days=37)
        baseline_end = datetime.utcnow() - timedelta(days=7)
        
        # Get recent cases by region and disease
        recent = db.query(
            FeverTrendDB.region,
            FeverTrendDB.probable_disease,
            func.count(FeverTrendDB.trend_id).label('recent_count')
        ).filter(
            FeverTrendDB.timestamp >= recent_start
        ).group_by(
            FeverTrendDB.region,
            FeverTrendDB.probable_disease
        ).all()
        
        # Get baseline cases
        baseline = db.query(
            FeverTrendDB.region,
            FeverTrendDB.probable_disease,
            func.count(FeverTrendDB.trend_id).label('baseline_count')
        ).filter(
            and_(
                FeverTrendDB.timestamp >= baseline_start,
                FeverTrendDB.timestamp <= baseline_end
            )
        ).group_by(
            FeverTrendDB.region,
            FeverTrendDB.probable_disease
        ).all()
        
        # Create baseline lookup
        baseline_dict = {
            (b.region, b.probable_disease): b.baseline_count
            for b in baseline
        }
        
        # Detect outbreaks
        outbreaks = []
        for r in recent:
            if not r.region or not r.probable_disease:
                continue
                
            baseline_count = baseline_dict.get((r.region, r.probable_disease), 0)
            baseline_avg = baseline_count / 30 * 7  # Normalize to 7 days
            
            if baseline_avg > 0 and r.recent_count > baseline_avg * threshold_multiplier:
                increase_pct = ((r.recent_count - baseline_avg) / baseline_avg) * 100
                outbreaks.append({
                    "region": r.region,
                    "disease": r.probable_disease,
                    "recent_cases": r.recent_count,
                    "baseline_average": round(baseline_avg, 1),
                    "increase_percentage": round(increase_pct, 1),
                    "severity": "critical" if increase_pct > 200 else "warning",
                    "alert_message": f"{r.probable_disease} cases in {r.region} increased by {round(increase_pct, 1)}% compared to baseline"
                })
        
        return sorted(outbreaks, key=lambda x: x['increase_percentage'], reverse=True)
    
    @staticmethod
    def get_summary_stats(db: Session, days: int = 7) -> Dict:
        """
        Get summary statistics for dashboard.
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        total_cases = db.query(func.count(FeverTrendDB.trend_id)).filter(
            FeverTrendDB.timestamp >= start_date
        ).scalar()
        
        emergency_cases = db.query(func.count(FeverTrendDB.trend_id)).filter(
            and_(
                FeverTrendDB.timestamp >= start_date,
                FeverTrendDB.emergency_referral == True
            )
        ).scalar()
        
        unique_regions = db.query(func.count(func.distinct(FeverTrendDB.region))).filter(
            FeverTrendDB.timestamp >= start_date
        ).scalar()
        
        # Get most common disease
        most_common = db.query(
            FeverTrendDB.probable_disease,
            func.count(FeverTrendDB.trend_id).label('count')
        ).filter(
            FeverTrendDB.timestamp >= start_date
        ).group_by(
            FeverTrendDB.probable_disease
        ).order_by(
            func.count(FeverTrendDB.trend_id).desc()
        ).first()
        
        return {
            "total_cases": total_cases,
            "emergency_cases": emergency_cases,
            "emergency_rate": round((emergency_cases / total_cases * 100), 1) if total_cases > 0 else 0,
            "regions_affected": unique_regions,
            "most_common_disease": most_common.probable_disease if most_common else None,
            "period_days": days
        }
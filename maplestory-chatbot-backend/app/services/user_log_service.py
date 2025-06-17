import json
import uuid
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import aiofiles
import logging
from collections import defaultdict, Counter

from app.models.user_log import UserInteractionLog, LogAnalytics, UserFeedback, LogSource, LogStatus
from app.config.settings import settings

logger = logging.getLogger(__name__)

class UserLogService:
    """사용자 로그 서비스"""
    
    def __init__(self):
        self.log_dir = Path("logs/user_interactions")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 메모리 캐시 (최근 1000개 로그)
        self._cache: List[UserInteractionLog] = []
        self._cache_limit = 1000
        
    async def log_interaction(
        self,
        user_id: str,
        session_id: str,
        platform: LogSource,
        user_message: str,
        bot_response: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        status: LogStatus = LogStatus.SUCCESS,
        error_message: Optional[str] = None,
        sources_used: Optional[List[Dict[str, Any]]] = None,
        vector_scores: Optional[List[float]] = None,
        model_used: Optional[str] = None,
        tokens_used: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """사용자 상호작용 로그 기록"""
        try:
            log_id = str(uuid.uuid4())
            
            log_entry = UserInteractionLog(
                log_id=log_id,
                user_id=user_id,
                session_id=session_id,
                platform=platform,
                user_message=user_message,
                bot_response=bot_response,
                response_time_ms=response_time_ms,
                status=status,
                error_message=error_message,
                sources_used=sources_used or [],
                vector_scores=vector_scores or [],
                sources_count=len(sources_used) if sources_used else 0,
                model_used=model_used,
                tokens_used=tokens_used,
                context=context or {}
            )
            
            # 메모리 캐시에 추가
            self._cache.append(log_entry)
            if len(self._cache) > self._cache_limit:
                self._cache.pop(0)
            
            # 파일에 비동기 저장
            await self._save_log_to_file(log_entry)
            
            logger.info(f"사용자 로그 기록 완료: {log_id}")
            return log_id
            
        except Exception as e:
            logger.error(f"로그 기록 실패: {str(e)}")
            return ""
    
    async def _save_log_to_file(self, log_entry: UserInteractionLog):
        """로그를 파일에 저장"""
        try:
            # 날짜별 로그 파일
            date_str = log_entry.timestamp.strftime("%Y-%m-%d")
            log_file = self.log_dir / f"interactions_{date_str}.jsonl"
            
            # JSON Lines 형식으로 저장
            log_data = log_entry.model_dump()
            log_data['timestamp'] = log_entry.timestamp.isoformat()
            
            async with aiofiles.open(log_file, "a", encoding="utf-8") as f:
                await f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"로그 파일 저장 실패: {str(e)}")
    
    async def get_recent_logs(self, limit: int = 100) -> List[UserInteractionLog]:
        """최근 로그 조회"""
        return self._cache[-limit:] if len(self._cache) >= limit else self._cache
    
    async def get_user_logs(self, user_id: str, days: int = 7) -> List[UserInteractionLog]:
        """특정 사용자의 로그 조회"""
        user_logs = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 캐시에서 먼저 검색
        for log in self._cache:
            if (log.user_id == user_id and 
                start_date <= log.timestamp <= end_date):
                user_logs.append(log)
        
        # 파일에서 추가 검색 (필요시)
        if len(user_logs) < 100:  # 캐시에 충분하지 않다면 파일에서 로드
            file_logs = await self._load_logs_from_files(start_date, end_date, user_id)
            user_logs.extend(file_logs)
        
        # 시간 순 정렬
        user_logs.sort(key=lambda x: x.timestamp, reverse=True)
        return user_logs
    
    async def _load_logs_from_files(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        user_id: Optional[str] = None
    ) -> List[UserInteractionLog]:
        """파일에서 로그 로드"""
        logs = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            log_file = self.log_dir / f"interactions_{date_str}.jsonl"
            
            if log_file.exists():
                try:
                    async with aiofiles.open(log_file, "r", encoding="utf-8") as f:
                        async for line in f:
                            if line.strip():
                                log_data = json.loads(line)
                                log_data['timestamp'] = datetime.fromisoformat(log_data['timestamp'])
                                
                                if user_id is None or log_data.get('user_id') == user_id:
                                    logs.append(UserInteractionLog(**log_data))
                                    
                except Exception as e:
                    logger.error(f"로그 파일 읽기 실패 {log_file}: {str(e)}")
            
            current_date += timedelta(days=1)
        
        return logs
    
    async def get_analytics(self, days: int = 7) -> LogAnalytics:
        """로그 분석 데이터 생성"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 기간 내 로그 수집
            all_logs = await self._load_logs_from_files(start_date, end_date)
            
            if not all_logs:
                return LogAnalytics(
                    total_interactions=0,
                    unique_users=0,
                    success_rate=0.0,
                    avg_response_time=0.0,
                    most_common_queries=[],
                    error_rate=0.0
                )
            
            # 분석 계산
            total_interactions = len(all_logs)
            unique_users = len(set(log.user_id for log in all_logs))
            
            success_logs = [log for log in all_logs if log.status == LogStatus.SUCCESS]
            success_rate = len(success_logs) / total_interactions if total_interactions > 0 else 0
            
            error_logs = [log for log in all_logs if log.status == LogStatus.ERROR]
            error_rate = len(error_logs) / total_interactions if total_interactions > 0 else 0
            
            # 평균 응답 시간 (밀리초 -> 초)
            response_times = [log.response_time_ms for log in all_logs if log.response_time_ms is not None]
            avg_response_time = sum(response_times) / len(response_times) / 1000 if response_times else 0
            
            # 자주 묻는 질문 분석
            queries = [log.user_message[:50] for log in all_logs]  # 처음 50자만
            query_counter = Counter(queries)
            most_common_queries = [query for query, _ in query_counter.most_common(10)]
            
            return LogAnalytics(
                total_interactions=total_interactions,
                unique_users=unique_users,
                success_rate=success_rate,
                avg_response_time=avg_response_time,
                most_common_queries=most_common_queries,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"분석 데이터 생성 실패: {str(e)}")
            return LogAnalytics(
                total_interactions=0,
                unique_users=0,
                success_rate=0.0,
                avg_response_time=0.0,
                most_common_queries=[],
                error_rate=0.0
            )
    
    async def add_feedback(
        self, 
        log_id: str, 
        user_id: str, 
        rating: int, 
        feedback_text: Optional[str] = None
    ) -> bool:
        """사용자 피드백 추가"""
        try:
            feedback = UserFeedback(
                log_id=log_id,
                user_id=user_id,  
                rating=rating,
                feedback_text=feedback_text
            )
            
            # 피드백 파일에 저장
            date_str = datetime.now().strftime("%Y-%m-%d")
            feedback_file = self.log_dir / f"feedback_{date_str}.jsonl"
            
            feedback_data = feedback.model_dump()
            feedback_data['timestamp'] = feedback.timestamp.isoformat()
            
            async with aiofiles.open(feedback_file, "a", encoding="utf-8") as f:
                await f.write(json.dumps(feedback_data, ensure_ascii=False) + "\n")
            
            logger.info(f"피드백 기록 완료: {log_id}")
            return True
            
        except Exception as e:
            logger.error(f"피드백 기록 실패: {str(e)}")
            return False
    
    async def cleanup_old_logs(self, days_to_keep: int = 30):
        """오래된 로그 파일 정리"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            for log_file in self.log_dir.glob("*.jsonl"):
                # 파일명에서 날짜 추출
                try:
                    if "interactions_" in log_file.name:
                        date_str = log_file.name.replace("interactions_", "").replace(".jsonl", "")
                        file_date = datetime.strptime(date_str, "%Y-%m-%d")
                        
                        if file_date < cutoff_date:
                            log_file.unlink()
                            logger.info(f"오래된 로그 파일 삭제: {log_file}")
                            
                except Exception as e:
                    logger.warning(f"로그 파일 날짜 파싱 실패 {log_file}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"로그 정리 실패: {str(e)}")

# 전역 서비스 인스턴스
user_log_service = UserLogService() 
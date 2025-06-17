# 📊 로그 파일 실시간 모니터링 방법들

## 🔍 실시간 로그 확인

### 1. 실시간 로그 tail 모니터링
```bash
# 오늘 날짜 로그 파일을 실시간으로 모니터링
tail -f logs/user_interactions/interactions_$(date +%Y-%m-%d).jsonl

# 로그가 추가될 때마다 즉시 확인 가능
```

### 2. 새로운 로그 항목을 예쁘게 포맷팅해서 실시간 확인
```bash
# 새로운 로그를 JSON 포맷으로 실시간 출력
tail -f logs/user_interactions/interactions_$(date +%Y-%m-%d).jsonl | while read line; do echo "$line" | python -m json.tool; echo "---"; done
```

## 📈 로그 분석 명령어들

### 3. 로그 항목 수 확인  
```bash
# 전체 로그 파일의 항목 수
wc -l logs/user_interactions/*.jsonl

# 오늘의 로그 항목 수만
wc -l logs/user_interactions/interactions_$(date +%Y-%m-%d).jsonl
```

### 4. 최신 로그 항목 확인
```bash
# 가장 최근 로그 항목을 예쁘게 출력
tail -1 logs/user_interactions/interactions_$(date +%Y-%m-%d).jsonl | python -m json.tool
```

### 5. 특정 사용자 로그 필터링
```bash
# 특정 사용자의 모든 로그 확인
grep 'discord_457115703816880129' logs/user_interactions/*.jsonl

# 특정 사용자의 로그 개수
grep -c 'discord_457115703816880129' logs/user_interactions/*.jsonl
```

## 🚨 문제 진단 명령어들

### 6. 오류 로그만 확인
```bash
# 상태가 'error'인 로그만 필터링
grep '"status": "error"' logs/user_interactions/*.jsonl

# 오류 메시지가 있는 로그 확인
grep '"error_message":' logs/user_interactions/*.jsonl | grep -v 'null'
```

### 7. 응답 시간이 긴 로그 확인
```bash
# 응답 시간이 2초 이상인 로그 (2000ms+)
grep -E '"response_time_ms": [2-9][0-9]{3}' logs/user_interactions/*.jsonl

# 응답 시간이 5초 이상인 로그 (5000ms+)  
grep -E '"response_time_ms": [5-9][0-9]{3}' logs/user_interactions/*.jsonl
```

### 8. 검색 결과가 없는 로그 확인
```bash
# sources_count가 0인 로그 (검색 결과 없음)
grep '"sources_count": 0' logs/user_interactions/*.jsonl
```

## 📊 통계 및 분석

### 9. 가장 많이 사용하는 질문 패턴 분석
```bash
# 질문 키워드 빈도 분석 (간단한 예시)
grep -o '"user_message": "[^"]*"' logs/user_interactions/*.jsonl | sort | uniq -c | sort -nr | head -10
```

### 10. 시간대별 사용량 분석
```bash
# 시간대별 로그 개수 (시간별 그룹화)
grep -o '"timestamp": "[^"]*"' logs/user_interactions/*.jsonl | cut -d'"' -f4 | cut -dT -f2 | cut -d: -f1 | sort | uniq -c
```

### 11. 플랫폼별 사용량 확인
```bash
# 플랫폼별 로그 개수
grep -o '"platform": "[^"]*"' logs/user_interactions/*.jsonl | sort | uniq -c
```

## 🔧 로그 관리 명령어들

### 12. 로그 백업
```bash
# 로그 파일들을 날짜별로 압축 백업
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/user_interactions/
```

### 13. 오래된 로그 정리 (수동)
```bash
# 7일 이전의 로그 파일 찾기
find logs/user_interactions/ -name "*.jsonl" -mtime +7

# 7일 이전의 로그 파일 삭제 (주의: 실제 삭제 전에 백업!)
find logs/user_interactions/ -name "*.jsonl" -mtime +7 -delete
```

## 🧪 개발 및 테스트

### 14. 로그 기능 테스트 실행
```bash
# 로그 시스템 전체 테스트
python scripts/test_user_logs.py
```

### 15. API를 통한 로그 조회
```bash
# 최근 로그 50개 조회
curl "http://localhost:8000/api/logs/recent?limit=50"

# 분석 데이터 조회
curl "http://localhost:8000/api/logs/analytics?days=7"
```

## 💡 유용한 팁들

### 16. 로그 파일 크기 모니터링
```bash
# 로그 파일 크기 확인
du -h logs/user_interactions/*.jsonl

# 전체 로그 디렉토리 크기
du -sh logs/user_interactions/
```

### 17. JSON 검증
```bash
# 로그 파일의 JSON 형식이 올바른지 확인
while read line; do echo "$line" | python -m json.tool > /dev/null || echo "Invalid JSON: $line"; done < logs/user_interactions/interactions_$(date +%Y-%m-%d).jsonl
```

### 18. 로그 파일 상태 확인
```bash
# 현재 로그 파일들 목록과 마지막 수정 시간
ls -lt logs/user_interactions/

# 오늘 생성된 로그가 있는지 확인
ls -la logs/user_interactions/interactions_$(date +%Y-%m-%d).jsonl 2>/dev/null && echo "Today's log exists" || echo "No log for today"
```

---

## 🚀 빠른 시작 명령어

새로운 로그를 실시간으로 모니터링하려면:
```bash
tail -f logs/user_interactions/interactions_$(date +%Y-%m-%d).jsonl
```

로그 분석을 빠르게 하려면:
```bash
python scripts/test_user_logs.py
```

API로 최근 상황을 확인하려면:
```bash
curl "http://localhost:8000/api/logs/analytics?days=1"
``` 
# Wellda AI 솔루션 (LLM)

## Quick Starts
API 서버 실행을 위한 환경 세팅 혹은 자세한 사용 방법은 각 기능 디렉터리 내 README를 참조하세요. 서버 로그는 `<root>/utils/utils_logs`에 저장됩니다.

### API 서버 실행
#### 터미널 (Remote Server)
```shell
nohup uvicorn app:app --host 0.0.0.0 --port 5000 

nohup gunicorn app:app --workers 9 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000 --timeout 200 --keep-alive 5 --graceful-timeout 100 --max-requests 1000 --max-requests-jitter 100
```
- 현재 서버 버전: Ubuntu 24.04, Python 3.10.X

### LLM 기반 코치 도우미 추천 답변 생성
#### CURL
```shell
curl -X POST http://<SERVER_URL>/summary/ \
    -H "Content-Type: application/json" \
    -d '{"query": "<USER_INPUT>"}'
```
```shell
curl -X POST http://<SERVER_URL>/reference/ \
    -H "Content-Type: application/json" \
    -d '{"query": "<USER_INPUT>"}'
```
```shell
curl -X POST http://<SERVER_URL>/answer/ \
    -H "Content-Type: application/json" \
    -d '{"query": "<USER_INPUT>", "data": [...]}'
```

### 식사 로깅: 영양성분 생성
#### CURL
```shell
curl -X POST http://<SERVER_URL>/api/gen/nutrition \
    -H "Content-Type: application/json" \
    -H "x-api-key: <SERVICE_API_KEY>" \
    -d '{"foodName": "<FOOD_NAME>", "quantity": 1, "unit": 0}'
```
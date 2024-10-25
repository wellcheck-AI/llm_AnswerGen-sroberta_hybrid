# LLM 기반 코치 도우미 추천 답변 생성
Welda 플랫폼의 코칭 업무를 지원하기 위해 설계된 추천 답변 생성 기능을 제공합니다.
Langchain과 LLM(openai API)로 연관 가이드를 연결하고, 이를 통해 사용자 질문에 대해 최적화된 답변을 생성하는 API를 포함합니다.

## 주요 기능
* 질문 요약 및 분석: 입력된 질문을 요약하여 핵심만을 전달합니다.
* 연관 가이드 추천: 질문과 연관된 가이드를 랭킹하여 제공합니다.
* LLM 기반 답변 생성: LLM 및 Langchain을 사용하여 답변을 생성하고 추천합니다.

## Issue  
- [ ] 플랫폼 고도화 시 백엔드 수준에서 HTTP 응답 상태 핸들링 로직 변경
- [ ] 플랫폼 고도화 시 API 수준에서 응답 본문 내 `status_code` 필드 삭제

## API 명세
### Input format
```
{
    "query": "혈당이란 무엇인가요?"
}
```

### Output foramt
| Status Code | 요약 API<br>(Summary API) | 답변 가이드 검색 API<br>(Reference API) | 답변 추천 API<br>(Answer API) |
|:-----------:|:------------------------:|:--------------------------------------:|:-----------------------------:|
| 200         |            O             |                    O                   |               O               |
| 204         |            X             |                    O                   |               X               |
| 403         |            O             |                    O                   |               O               |
| 405         |            O             |                    O                   |               O               |
| 500         |            O             |                    O                   |               O               |
- **200** : 작업 성공, 데이터 반환
- **204** : 작업 성공, 관련 데이터 없음
- **403** : 작업 실패, API 서버 에러
- **405** : 작업 실패, 빈 쿼리 입력
- **500** : 작업 실패, 예상치 못한 에러

---
#### 성공 (200, 204)
- 요약 API
    ```json
    {
        "status_code": 200,
        "data": [
            {
                "summary": "허리 사이즈 감량 목표 달성을 위한 미션 방법"
            }
        ]
    }
    ```
- 답변 가이드 검색 API
    - 204에서 data는 `[[None, [], []], [None, [], []], ...]`의 형태
    ```json
    {
        "status_code": 200,
        "data": [
            {
                "reference" : [
                    {
                        "index": 1,
                        "text": "식사 후 발생한 혈당 스파이크는 식곤증을 유발할 수 있습니다.",
                        "keyword" : ["식곤증\n" , "식후졸음\n"]
                    },
                    ...
                ]
            }
        ]
    }
    ```
- 답변 추천 API
    ```json
    {
        "status_code": 200,
        "data": [
            {
                "index": [1, 2, 3],
                "reference": ["식사 후 발생한 혈당 스파이크는 식곤증을 유발할 수 있습니다.", "참고문헌2", "참고문헌3"]
            }
        ]
    }
    ```
---
#### 실패
```json
{
    "status_code": <STATUS_CODE>,
    "message": "현재 <PROCESS_NAME>이 어렵습니다. 잠시 후에 다시 사용해주세요."
}

```

## DB Update
로컬에서 진행을 권장합니다
### 데이터 세팅
```
root_dir
    ├ data/
    │   └ <DATA_FILE>
    └ ...
```
- 데이터는 `.csv`, `.xlsx` 포맷을 지원하며, 두 번째 열이 '분류' 열이어야 합니다.
### Build Index
```shell
python db_update.py
```
- (24.10.02) `prod-search-sroberta`로 고정 및 사용량이 적은 시간대(새벽 00:00 ~ 1:00 등)에 업데이트 진행 예정  
~~- `db_update.py` 파일 실행 전 `config/conf.yaml` 파일 내 `index_name`을 확인해주세요~~  
    ~~- `index_name`은 db update 진행 시점 기준 product에서 사용 중인 인덱스 명과는 다른 값이어야 합니다(`choices = ["prod-search-sroberta-a", "prod-search-sroberta-b"]`)~~  
    ~~- `config/conf.yaml` 파일 내 지정된 `index_name`으로 새로운 인덱스 생성이 진행되며, 인덱스 생성 후 검색 결과가 정상적으로 반환되는 경우 이전에 사용 중이었던 인덱스는 삭제됩니다.~~  
        ~~- 인덱스 생성에는 250여개의 데이터 기준 약 10분 정도가 소요되며, 위 로직을 따르는 이유는 인덱스가 생성되는 10분 사이에도 api가 정상동작하도록 하기 위함입니다.~~  

### Upload TF-IDF Params (only in local)
```shell
git add config/params/tfidf_params.pkl
git commit -m "Update: guide DB"
git push origin <BRANCH_NAME>
```
- 원격 서버에서 업데이트를 진행할 경우에는 이 단계를 건너뛰세요.

## ubuntu 서버에서 동작
### 가상환경 실행 (requirements.txt 설치된 상태)
```
source .venv/bin/activate
```

### API 엔드포인트 앱 실행
```
nohup python3 app.py > output.log 2>&1 &
```

### 프로세스 확인
```
ps aux | grep app.py
```

## Setting Environment (initial)
```
Python == 3.10.X
```
### Install Mecab
```shell
apt update
apt install default-jdk autoconf automake libtool pkg-config gcc g++
curl -LO https://bitbucket.org/eunjeon/mecab-ko/downloads/mecab-0.996-ko-0.9.2.tar.gz
tar zxfv mecab-0.996-ko-0.9.2.tar.gz
curl -LO https://bitbucket.org/eunjeon/mecab-ko-dic/downloads/mecab-ko-dic-2.1.1-20180720.tar.gz
tar -zxvf mecab-ko-dic-2.1.1-20180720.tar.gz

cd mecab-ko-dic-2.1.1-20180720
ldconfig
ldconfig -p | grep /usr/local/lib
cd ..

cd mecab-0.996-ko-0.9.2
./configure
make
make check
make install
cd ..

cd mecab-ko-dic-2.1.1-20180720
./autogen.sh
./configure
make
make install
cd ..

# 가상환경 생성

pip install konlpy
pip install mecab-python3
```
- `mecab-0.996-ko-0.9.2`의 `./configure` 실행 후에도 `make` 파일이 생성되지 않을 경우, `autoreconf -fi` 실행 후 `./configure`를 재실행해주세요.
- 모든 프로세스 실행 후에도 `/usr/local/lib/mecab/dic/mecab-ko-dic` 디렉터리가 생성되지 않을 경우, 직접 디렉터리를 생성한 후 `mecab-ko-dic-2.1.1-20180720` 내의 파일을 옮겨주세요

### Install requirements
```shell
pip install -r requirements.txt
```

### Change the source file
```
cp text.py <env_path>/site-packages/sklearn/feature_extraction/text.py
```
- 이 단계는 `requirements.txt`가 모두 설치된 후 진행되어야 합니다.

## 변경사항
2024-10-16
1. 응답 본문(body)에 `status_code` 필드를 포함시켜 상태를 전달하던 방식에서, 실제 HTTP 응답 자체의 상태 코드를 사용하여 상태를 전달하는 방식으로 변경 

2024-10-15
1. 입력 쿼리에 대한 로깅 기능 추가

2024-10-02
1. 검색 API 변경
    - 임베딩 모델: SRoBERTa
    - 희소 벡터 생성 메트릭: TF-IDF, Mecab
2. DB 업데이트 코드 추가

2024-09-06
1. 서치 코드 변경
Deberta 모델을 제거하고, OpenAI API를 사용한 새로운 서치 로직으로 대체, 키워드 서치 & Rerank 기능 관련 제거, 추천 답변 생성 코드 수정
2. 의존성
Langchain 호출 경로를 최신 버전 업데이트, ChatOpenAI 파라미터 수정

2024-09-09
1. 잘못된 가상환경 제거 및 신규 생성
2. Openai API KEY 교체 

2024-10-10
1. 로깅 설정 추가
1) /etc/profile 줄 추가
export PROMPT_COMMAND='RETRN_VAL=$?; logger -t bash -p local1.notice "$(whoami) [$(date +%Y-%m-%d\ %H:%M:%S)] $(history 1 | sed "s/^[ ]*[0-9]\+[ ]*//" )"'
2) /etc/rsyslog.d/50-default.conf 줄 추가
local1.notice    /var/log/cmd.log
3) rsyslog 재시작 : sudo systemctl restart rsyslog

2. 메일링 설정
1) /home/ubuntu/send_ssh_log.sh 생성
2) crontab -e 줄 추가 : * * * * * /home/ubutu/send_ssh_log.sh
3) 외부 stmp 서버 설정 (hostname -f : ip-172-31-50-136.ap-northeast-2.compute.internal)
4) /etc/postfix/main.cf 변경 : relayhost설정, TLS 설정 추가
5) /etc/postfix/sasl_passwd : 계정정보 추가 후 적용
sudo vim /etc/postfix/main.cf
sudo postmap /etc/postfix/sasl_passwd
sudo systemctl restart postfix
6) 테스트 : echo "Test email content" | mail -s "Test Subject" test@test.com
tail -n /var/log/auth.log
tail -f /var/log/mail.log
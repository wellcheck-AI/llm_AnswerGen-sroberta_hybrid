#!/bin/bash

# 로그 파일 경로
LOGFILE="/var/log/auth.log"
LAST_LOG="/tmp/last_ssh_log"  # 마지막으로 확인한 로그 줄 번호 저장 파일

# 마지막으로 확인한 줄 번호를 저장하는 파일이 없으면 생성
if [ ! -f $LAST_LOG ]; then
  echo 0 > $LAST_LOG
fi

LAST_LINE=$(cat $LAST_LOG)  # 마지막 확인한 로그 줄 번호 읽기
CURRENT_LINE=$(wc -l < $LOGFILE)  # 현재 로그 파일의 총 줄 수

# 새로운 로그 줄이 추가되었는지 확인
if [ $LAST_LINE -lt $CURRENT_LINE ]; then
  # 새로운 로그 부분에서 SSH 접속 성공 패턴 감지
  tail -n $((CURRENT_LINE - LAST_LINE)) $LOGFILE | grep -E "sshd\|Accepted"

  # 새로운 SSH 접속이 감지되었을 경우 최근 5줄 메일로 전송
  if [ $? -eq 0 ]; then
    tail -n 10 $LOGFILE | mail -s "New SSH Connection Detected" -r "aimkt6@gmail.com" dyk43e@daewoong.co.kr
  fi

  # 현재 로그의 마지막 줄 번호 업데이트
  echo "$CURRENT_LINE" > $LAST_LOG
fi

# #!/bin/bash

# # 로그 파일 경로
# LOGFILE="/var/log/auth.log"  # Ubuntu 기반
# SEARCH_PATTERN="Accepted"  # SSH 접속 성공 패턴

# # 현재 로그 파일의 총 줄 수 확인
# CURRENT_LINE=$(wc -l < $LOGFILE)

# # SSH 접속 패턴 감지
# NEW_CONNECTION=$(sudo tail -n 50 $LOGFILE | grep -E "$SEARCH_PATTERN")

# # 새로운 SSH 접속이 감지되었을 경우
# if [ ! -z "$NEW_CONNECTION" ]; then
#   # 감지된 패턴과 해당 로그의 최근 5줄을 메일로 전송
#   sudo tail -n 5 $LOGFILE | mail -s "New SSH Connection Detected" -r "aimkt6@gmail.com" dyk43e@daewoong.co.kr
# fi

# #!/bin/bash

# # 로그 파일 경로
# LOGFILE="/var/log/auth.log"  # Ubuntu 기반
# SEARCH_PATTERN="Accepted"  # SSH 접속 성공 패턴
# LAST_LOG="/tmp/last_ssh_log"  # 마지막으로 확인한 로그 저장 파일
# TMP_LOG="/tmp/ssh_log_tmp"  # 임시 로그 파일

# # 마지막으로 확인한 줄 번호를 저장하는 파일이 없으면 생성
# if [ ! -f $LAST_LOG ]; then
#   echo 0 | sudo tee $LAST_LOG
# fi

# LAST_LINE=$(sudo cat $LAST_LOG)  # 마지막 확인한 로그 줄 번호 읽기
# CURRENT_LINE=$(sudo wc -l < $LOGFILE)  # 현재 로그 파일의 총 줄 수

# if [ $LAST_LINE -lt $CURRENT_LINE ]; then
#   # 새로운 로그 부분에서 패턴 메시지가 있는지 확인하여 임시 파일에 저장
#   sudo tail -n $((CURRENT_LINE - LAST_LINE)) $LOGFILE | grep "$SEARCH_PATTERN" | sudo tee $TMP_LOG
  
#   # 새로운 SSH 접속이 감지되었을 경우에만 메일을 전송
#   if [ -s $TMP_LOG ]; then
#     sudo cat $TMP_LOG | mail -s "New SSH Connection Detected" -r "aimkt6@gmail.com" dyk43e@daewoong.co.kr
#   fi
  
#   # 현재 로그의 마지막 줄 번호 업데이트
#   echo "$CURRENT_LINE" | sudo tee $LAST_LOG
# fi
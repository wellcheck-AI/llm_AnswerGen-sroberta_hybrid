#!/bin/bash

# Homebrew 설치 확인 및 설치
if ! command -v brew &> /dev/null; then
    echo "Homebrew 설치 중..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 필요한 의존성 설치
brew install git
brew install autoconf
brew install automake
brew install libtool
brew install pkg-config
brew install gcc
brew install curl
brew install gettext

# MeCab 관련 패키지 설치
brew install mecab
brew install mecab-ko
brew install mecab-ko-dic

# 환경 변수 설정
echo 'export MECAB_PATH="/usr/local/lib/mecab/dic/mecab-ko-dic"' >> ~/.zshrc
echo 'export LD_LIBRARY_PATH="/usr/local/lib:$LD_LIBRARY_PATH"' >> ~/.zshrc
source ~/.zshrc

# Python 패키지 설치
pip install mecab-python3
pip install konlpy

# 설치 확인
echo "MeCab 설치 상태 확인..."
mecab --version
echo "설치가 완료되었습니다."

# 테스트 실행
echo "테스트 실행 중..."
python3 -c "
from konlpy.tag import Mecab
try:
    mecab = Mecab()
    print('테스트 결과:', mecab.pos('테스트 문장입니다.'))
    print('MeCab이 성공적으로 설치되었습니다.')
except Exception as e:
    print('오류 발생:', str(e))
"
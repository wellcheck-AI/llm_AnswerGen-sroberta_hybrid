from konlpy.tag import Mecab

dicpath = "/opt/homebrew/lib/mecab/dic/mecab-ko-dic"
try:
    mecab = Mecab(dicpath=dicpath)
    print(f'성공! 사용된 사전 경로: {dicpath}')
    print('테스트 결과:', mecab.pos('테스트 문장입니다.'))
except Exception as e:
    print(f'오류 발생: {str(e)}')
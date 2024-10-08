import io
import sys
import io
import unittest
from app import app  # api가 정의된 app.py에서 가져옴

# 표준 출력(stdout)을 UTF-8로 강제 설정
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')

class SuccessTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()  # 클라이언트 생성
        self.headers = {'content-type': 'application/json'}  # 헤더 설정
        self.context = None  # 초기화
        self.query = "나 장어집 가서 다이어트 하려고 뭐먹을까?"

    def print_response(self, response):
        print("Status Code:", response.status_code)
        print("Response JSON:", response.json)

    def create_answer_request(self, query, reference_list_response):
        """쿼리와 2번 API 응답 데이터를 결합하여 3번 API 입력 데이터 생성"""
        indexes = []
        references = []

        # Reference 데이터를 순회하여 index와 text를 추출
        for ref in reference_list_response['data'][0]['reference']:
            indexes.append(ref['index'])
            references.append(ref['text'])

        # 변환된 데이터를 사용하여 AnswerRequest 구조 생성
        data_item = {
            'index': indexes,
            'reference': references
        }

        answer_request = {
            'query': query,
            'data': [data_item]
        }
        print(answer_request)
        return answer_request

    def test_summary(self):
        """1번 요약 API 호출 테스트"""
        response = self.client.post(
            '/summary/',
            json={'query': self.query},
            headers=self.headers
        )
        self.print_response(response)
        self.assertIn('summary', response.json['data'][0])

    def test_search_answer(self):
        """2번 문서 검색 API 호출 테스트"""
        response = self.client.post(
            '/reference/',
            json={'query': self.query},
            headers=self.headers
        )
        self.print_response(response)
        self.context = response.json  # 컨텍스트 저장

        """3번 답변 생성 API 호출 테스트"""
        if self.context is None:
            self.fail("No context available. Run test_search first.")

        # 쿼리와 검색 결과를 사용해 3번 API의 요청 데이터 생성
        answer_request = self.create_answer_request(self.query, self.context)

        response = self.client.post(
            '/answer/',
            json=answer_request,
            headers=self.headers
        )
        self.print_response(response)
        self.assertIn('answer', response.json['data'][0])

if __name__ == '__main__':
    # 1번 요약 API 실행
    print("=== Running Summary API Test ===")
    unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(SuccessTests))

    # 2번 문서 검색 및 3번 답변 생성 API 실행
    print("\n=== Running Search and Answer API Tests ===")
    suite = unittest.TestSuite()
    suite.addTest(SuccessTests('test_search_answer'))
    unittest.TextTestRunner().run(suite)

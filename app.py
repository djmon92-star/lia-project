import json
import os
import re
import traceback
from flask import Flask, render_template, request
from google import genai
from groq import Groq
import requests

app = Flask(__name__, template_folder='.')

# 도서관정보나루 API 키
DATA4LIB_KEY = (
    '6ccfec20e4f6af131b8883ba9b858d432bfeac4e33f2ed30eb19e0b63e5aece1'
)

# 1. 젬마(Google) API 키
GEMMA_API_KEY = 'AQ.Ab8RN6KvaVu6uV0Oq1lHchbv-bOQPXS70aur05c8dwt7er34Yw'
client = genai.Client(api_key=GEMMA_API_KEY)

# 2. 라마(Groq) API 키
GROQ_API_KEY = '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'
groq_client = Groq(api_key=GROQ_API_KEY)

# 서버 시작 시 내 Groq API 키로 사용 가능한 활성 모델 자동 탐색
AVAILABLE_GROQ_MODELS = []
try:
  groq_model_list = groq_client.models.list()
  for m in groq_model_list.data:
    m_id = m.id
    if all(
        exclude not in m_id.lower()
        for exclude in ['whisper', 'guard', 'tts', 'vision', 'playai']
    ):
      AVAILABLE_GROQ_MODELS.append(m_id)
  AVAILABLE_GROQ_MODELS.sort(key=lambda x: (0 if 'llama' in x.lower() else 1))
  print('=== [내 키로 호출 가능한 Groq(라마) 모델 목록] ===')
  print(AVAILABLE_GROQ_MODELS)
  print('================================================')
except Exception as e:
  print('Groq 모델 목록 조회 실패:', e)

# 🌟 직접 보내주신 완벽한 20권 고전 명작 및 ISBN 데이터베이스
CLASSIC_BOOKS = [
    {
        'id': 0,
        'title': '젊은 베르테르의 슬픔',
        'author': '요한 볼프강 폰 괴테',
        'isbn': '9788937460258',
        'altIsbns': ['9788937460258'],
        'theme': '젊은 날의 사랑, 격정적 감정, 실연, 열정, 고뇌',
    },
    {
        'id': 1,
        'title': '위대한 개츠비',
        'author': 'F. 스콧 피츠제럴드',
        'isbn': '9788937460753',
        'altIsbns': ['9788937460753'],
        'theme': '이루지 못한 꿈, 그리움, 이상과 현실의 괴리, 공허함',
    },
    {
        'id': 2,
        'title': '이반 일리치의 죽음',
        'author': '레프 톨스토이',
        'isbn': '9788937464386',
        'altIsbns': ['9788937464386'],
        'theme': '삶의 의미, 죽음 앞의 성찰, 진정한 삶, 허위와 진실',
    },
    {
        'id': 3,
        'title': '사람은 무엇으로 사는가',
        'author': '레프 톨스토이',
        'isbn': '9788937464720',
        'altIsbns': ['9788937464720'],
        'theme': '사랑, 인간의 본질, 나눔, 따뜻한 위로, 삶의 지혜',
    },
    {
        'id': 4,
        'title': '폭풍의 언덕',
        'author': '에밀리 브론테',
        'isbn': '9788937461187',
        'altIsbns': ['9788937461187'],
        'theme': '지독한 사랑과 복수, 집착, 황량한 열정, 운명적 만남',
    },
    {
        'id': 5,
        'title': '수레바퀴 아래서',
        'author': '헤르만 헤세',
        'isbn': '9788937460500',
        'altIsbns': ['9788937460500'],
        'theme': '사회적 압박, 경쟁과 피로, 번아웃, 학업 스트레스, 위로',
    },
    {
        'id': 6,
        'title': '면도날',
        'author': '서머싯 몸',
        'isbn': '9788937462146',
        'altIsbns': ['9788937462146'],
        'theme': '진정한 구원, 영혼의 방황, 물질주의 탈피, 삶의 목적',
    },
    {
        'id': 7,
        'title': '1984',
        'author': '조지 오웰',
        'isbn': '9788937460777',
        'altIsbns': ['9788937460777'],
        'theme': '감시와 통제, 전체주의, 개인의 자유, 진실과 저항',
    },
    {
        'id': 8,
        'title': '노인과 바다',
        'author': '어니스트 헤밍웨이',
        'isbn': '9788937462788',
        'altIsbns': ['9788937462788'],
        'theme': '포기하지 않는 의지, 시련 극복, 인내, 도전에 대한 용기',
    },
    {
        'id': 9,
        'title': '무진기행',
        'author': '김승옥',
        'isbn': '9788937461491',
        'altIsbns': ['9788937461491'],
        'theme': '안개 낀 일탈, 도피, 고독, 자아 성찰, 현대인의 방황',
    },
    {
        'id': 10,
        'title': '사랑에 대하여',
        'author': '스탕달',
        'isbn': '9788937464614',
        'altIsbns': ['9788937464614'],
        'theme': '사랑의 심리학, 감정의 파동, 연애의 본질, 마음의 기복',
    },
    {
        'id': 11,
        'title': '달과 6펜스',
        'author': '서머싯 몸',
        'isbn': '9788937460388',
        'altIsbns': ['9788937460388'],
        'theme': '예술혼, 현실과 이상의 괴리, 파격적 삶, 내면의 욕구',
    },
    {
        'id': 12,
        'title': '동물농장',
        'author': '조지 오웰',
        'isbn': '9788937460050',
        'altIsbns': ['9788937460050'],
        'theme': '권력의 부패, 사회 비판, 평등과 자유, 통찰력',
    },
    {
        'id': 13,
        'title': '오만과 편견',
        'author': '제인 오스틴',
        'isbn': '9788937460883',
        'altIsbns': ['9788937460883'],
        'theme': '오해와 진실, 성장하는 사랑, 편견 극복, 인연',
    },
    {
        'id': 14,
        'title': '인간 실격',
        'author': '다자이 오사무',
        'isbn': '9788937461033',
        'altIsbns': ['9788937461033'],
        'theme': '타인의 시선, 소외감, 고독, 인간관계의 어려움, 우울',
    },
    {
        'id': 15,
        'title': '이방인',
        'author': '알베르 카뮈',
        'isbn': '9788937443848',
        'altIsbns': ['9788937443848', '9788937462672'],
        'theme': '부조리, 무관심, 반복되는 일상, 세상의 시선과 진실',
    },
    {
        'id': 16,
        'title': '데미안',
        'author': '헤르만 헤세',
        'isbn': '9788937460449',
        'altIsbns': ['9788937460449'],
        'theme': '자아 탐색, 청춘의 방황, 성장, 내면의 목소리',
    },
    {
        'id': 17,
        'title': '브람스를 좋아하세요...',
        'author': '프랑수아즈 사강',
        'isbn': '9788937461798',
        'altIsbns': ['9788937461798'],
        'theme': '쓸쓸한 사랑, 시간의 흐름, 고독, 성숙한 관계',
    },
    {
        'id': 18,
        'title': '싯다르타',
        'author': '헤르만 헤세',
        'isbn': '9788937460586',
        'altIsbns': ['9788937460586'],
        'theme': '구도의 길, 진리 탐구, 깨달음, 내면의 평화',
    },
    {
        'id': 19,
        'title': '로미오와 줄리엣',
        'author': '윌리엄 셰익스피어',
        'isbn': '9788937461736',
        'altIsbns': ['9788937461736', '8937461730'],
        'theme': '운명적 사랑, 뜨거운 열정, 순수함, 감정의 교감',
    },
]


@app.route('/')
def index():
  return render_template('index.html')


@app.route('/api/libraries')
def get_libs():
  isbn = request.args.get('isbn')
  region = request.args.get('region')
  page_size = request.args.get('pageSize', '100')

  url = f'http://data4library.kr/api/libSrchByBook?authKey={DATA4LIB_KEY}&isbn={isbn}&region={region}&pageSize={page_size}&format=json'

  try:
    res = requests.get(url, timeout=5)
    return res.text, res.status_code, {'Content-Type': 'application/json'}
  except Exception as e:
    return {'error': str(e)}, 500


def call_groq_llama(prompt_text):
  models_to_try = list(AVAILABLE_GROQ_MODELS)
  if not models_to_try:
    try:
      for m in groq_client.models.list().data:
        if 'whisper' not in m.id.lower() and 'guard' not in m.id.lower():
          models_to_try.append(m.id)
      models_to_try.sort(key=lambda x: (0 if 'llama' in x.lower() else 1))
    except Exception:
      pass

  for g_model in models_to_try:
    try:
      print(f'[Groq AI 호출 시도] 모델명: {g_model}')
      completion = groq_client.chat.completions.create(
          model=g_model,
          messages=[{'role': 'user', 'content': prompt_text}],
          temperature=0.6,
      )
      print(f'✅ [Groq AI 호출 성공] 적용 모델: {g_model}')
      return completion.choices[0].message.content
    except Exception as e:
      print(f'⚠️ [Groq 모델 {g_model} 시도 실패]: {e}')
      continue

  raise Exception('Groq에서 호출 가능한 모델이 없습니다.')


@app.route('/api/prescribe', methods=['POST'])
def prescribe_llm():
  data = request.json
  llm_type = data.get('llm', 'gemma')
  user_prompt = data.get('prompt', '').strip()
  if not user_prompt:
    user_prompt = '지친 일상에 위로가 되는 책을 추천해줘.'

  books_info = '\n'.join([
      f"{b['id']}. 《{b['title']}》 ({b['author']}) - 핵심테마: {b['theme']}"
      for b in CLASSIC_BOOKS
  ])

  full_prompt = f"""당신은 도서관의 지혜로운 사서 AI입니다.
사용자의 고민을 깊이 읽고, 아래 [고전문학 목록] (총 20권) 중에서 사용자의 고민에 가장 어울리는 책 단 1권을 선택하여 맞춤형 문학 처방을 내려주세요.

[사용자 고민]
{user_prompt}

[고전문학 목록]
{books_info}

반드시 아래의 JSON 형식으로만 응답하세요 (마크다운 기호나 다른 부연 설명 없이 순수 JSON만 출력):
{{
  "book_id": 선택한_책의_번호_숫자(0부터 19 사이),
  "comment": "선택한 책의 실제 내용과 인물을 구체적으로 언급하며 사용자의 고민을 위로하는 따뜻하고 깊이 있는 처방 해설 (한국어 3~4문장)",
  "quote": "해당 작품의 분위기를 담은 인상적인 명문장이나 핵심 구절 (한국어 1~2문장)"
}}"""

  raw_response = ''

  try:
    if llm_type == 'gemma':
      candidate_models = ['gemma-4-26b-a4b-it', 'gemma-3-27b-it']
      success = False
      for model_name in candidate_models:
        try:
          print(f'[구글 AI 호출 시도] 모델명: {model_name}')
          response = client.models.generate_content(
              model=model_name,
              contents=full_prompt,
          )
          raw_response = response.text
          print(f'✅ [구글 AI 호출 성공] 적용 모델: {model_name}')
          success = True
          break
        except Exception as inner_e:
          print(f'⚠️ [{model_name} 응답 실패]: {inner_e}')
          continue

      if not success:
        raw_response = call_groq_llama(full_prompt)

    else:
      raw_response = call_groq_llama(full_prompt)

    json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
    if json_match:
      parsed = json.loads(json_match.group(0))
      book_id = int(parsed.get('book_id', 0))
      if not (0 <= book_id < len(CLASSIC_BOOKS)):
        book_id = 0
      selected_book = CLASSIC_BOOKS[book_id]
      ai_comment = parsed.get('comment', '')
      ai_quote = parsed.get(
          'quote',
          '책장 사이에서 당신만을 위한 따뜻한 위로의 문장을 발견하시길'
          ' 바랍니다.',
      )
    else:
      selected_book = CLASSIC_BOOKS[0]
      ai_comment = raw_response
      ai_quote = (
          '새는 알을 깨고 나오려 투쟁한다. 알은 세계이다. 태어나려는 자는'
          ' 하나의 세계를 깨뜨려야 한다.'
      )

  except Exception as e:
    print('=== [AI 연동 에러 발생 상세 내용] ===')
    traceback.print_exc()
    selected_book = CLASSIC_BOOKS[0]
    ai_comment = (
        f'실시간 AI 엔진 통신 중 오류가 발생했습니다. (상세 내용: {str(e)})'
    )
    ai_quote = '잠시 숨을 고르고 고전이 건네는 지혜에 귀를 기울여 보세요.'

  return {
      'llm': llm_type,
      'book': selected_book,
      'comment': ai_comment,
      'quote': ai_quote,
  }


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  app.run(host='0.0.0.0', port=port, debug=True)
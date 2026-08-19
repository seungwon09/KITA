# KITA 진짜 클라우드 배포 다음 단계

지금 완료된 것은 노트북 기반 공개 백엔드 자동복구입니다.
노트북이 꺼져도 작동하는 출시용 서버를 만들려면 아래 중 하나가 필요합니다.

## 필요한 결정

1. 백엔드 실행 위치
   - 추천: Google Cloud Run
   - 대안: Render, Railway, Fly.io, VPS

2. 운영 DB
   - 추천: MongoDB Atlas
   - 대안: Google Cloud Mongo 호환 DB, VPS 내부 MongoDB

3. 고정 주소
   - 추천: 도메인 구매 후 `api.도메인`을 백엔드에 연결
   - 대안: Cloud Run 기본 HTTPS 주소 사용

4. 결제/사업자
   - 토스페이먼츠 실결제 키가 생기면 `.env.production`에 연결합니다.

## 현재 가능한 수준

- Firebase Hosting 공개 화면: 완료
- 공개 백엔드 임시 터널: 완료
- 자동 재시작: 로컬 로그온 기준 준비
- 로컬 DB 백업: 준비

## 출시용 85% 이상으로 올리는 작업

1. Google Cloud 또는 Render 계정 연결
2. MongoDB Atlas 생성
3. KITA Node 서버 배포
4. Study AI 서버 배포
5. Firebase `kita-runtime-config.js`를 고정 API 주소로 교체
6. 도메인/HTTPS 연결
7. 운영 백업 스케줄 설정


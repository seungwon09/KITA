# KITA: 사업자등록 전 출시 준비 작업

사업자등록, 통장, 토스 실결제 심사 없이 지금 바로 끝낼 수 있는 작업 목록입니다.

## 지금 가능한 것

1. Git 저장소와 백업 안전장치
   - `.env`, 로그, 업로드 파일, DB 백업은 Git에 넣지 않습니다.
   - 기능 단위로 커밋해서 언제든 되돌릴 수 있게 합니다.

2. 배포 구조 정리
   - `docker-compose.prod.yml`, `Caddyfile`, `deploy-production.sh`로 서버 배포 구조를 유지합니다.
   - 실제 도메인이 생기면 `KITA_DOMAIN`, `PUBLIC_BASE_URL`, `CORS_ORIGINS`만 교체합니다.

3. 카카오 로그인 준비
   - 카카오 개발자 콘솔에서 REST API 키를 발급받으면 `.env`의 `KAKAO_REST_API_KEY`에 넣습니다.
   - Redirect URI는 개발 중 `http://127.0.0.1:3000/api/auth/kakao/callback`, 배포 후 `https://도메인/api/auth/kakao/callback`입니다.

4. 결제 개발모드
   - `ALLOW_DEV_PAYMENTS=true`이면 실제 결제 키 없이도 유료 플랜 활성화 흐름을 테스트합니다.
   - 실결제는 `TOSS_CLIENT_KEY`, `TOSS_SECRET_KEY`가 생긴 뒤 켭니다.

5. 앱 품질 강화
   - AI 답변 형식, 모바일 UI, 관리자 자료 업로드/검증 흐름을 계속 개선합니다.

## 사업자등록 후 바꾸는 것

1. 토스페이먼츠 실결제 키 입력
2. 이용약관/개인정보처리방침/환불정책 공개
3. 실제 도메인과 HTTPS 고정
4. 운영 DB 백업 주기 설정


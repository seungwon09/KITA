# KITA 서버 실행 안내

이 폴더는 KITA 웹, Study AI, MongoDB를 Docker로 함께 실행하는 배포 묶음입니다.

## 로컬 실행

Docker Desktop과 Ollama를 먼저 켠 뒤 PowerShell에서 실행합니다.

```powershell
cd C:\Users\user\Documents\Codex\kita-deploy
docker compose up -d --build
```

브라우저 주소:

- 사용자 화면: `http://127.0.0.1:3000`
- 관리자 화면: `http://127.0.0.1:3000/admin.html`
- 관리자 PIN: `.env` 파일의 `ADMIN_PIN`

웹 포트 `3000`만 같은 와이파이의 다른 기기에서 접근할 수 있습니다. Study AI `8002`와 MongoDB `27017`은 노트북 내부에서만 접근할 수 있습니다.

## 로컬 종료

```powershell
docker compose down
```

## 실제 도메인 배포

1. VPS 또는 클라우드 서버를 준비합니다.
2. 이 폴더를 서버로 옮깁니다.
3. `.env.production.example`을 `.env.production`으로 복사합니다.
4. `.env.production`의 도메인, 비밀키, DB 비밀번호를 교체합니다.
5. 서버 방화벽에서 `80`, `443` 포트만 엽니다.
6. 서버에서 `./deploy-production.sh`를 실행합니다.

Caddy가 HTTPS 인증서를 자동으로 연결합니다. MongoDB, Study AI, Ollama는 외부 포트를 열지 않습니다.

출시 전에는 [SECURITY_RELEASE_CHECKLIST.md](./SECURITY_RELEASE_CHECKLIST.md)를 확인합니다.

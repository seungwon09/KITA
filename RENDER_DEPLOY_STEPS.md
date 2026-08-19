# KITA Render 배포 순서

## 1. GitHub에 저장소 만들기

1. GitHub에서 새 저장소를 만든다.
2. 저장소 이름은 예: `kita`
3. Public/Private은 아무거나 가능하다. 처음에는 Private 추천.
4. 만든 뒤 GitHub가 보여주는 repo URL을 복사한다.

## 2. 이 폴더를 GitHub로 올리기

VS Code 터미널에서:

```powershell
cd C:\Users\user\Documents\Codex\kita-deploy
git remote add origin 붙여넣은_GitHub_주소
git branch -M main
git push -u origin main
```

이미 origin이 있다고 나오면:

```powershell
git remote set-url origin 붙여넣은_GitHub_주소
git push -u origin main
```

## 3. MongoDB Atlas 만들기

Render에는 MongoDB가 내장으로 붙지 않으므로 MongoDB Atlas를 쓴다.

1. Atlas에서 새 클러스터 생성
2. Database user 생성
3. Network Access는 Render에서 붙을 수 있게 임시로 `0.0.0.0/0` 허용
4. Connect URL 복사

형태:

```text
mongodb+srv://아이디:비밀번호@.../kita?retryWrites=true&w=majority
```

## 4. Render Blueprint 만들기

1. Render Dashboard 접속
2. New + 버튼
3. Blueprint 선택
4. GitHub 저장소 `kita` 연결
5. `render.yaml` 감지되면 Apply

Render가 만들 서비스:

- `kita-api`: KITA 웹/API 서버
- `kita-study-ai`: 풀이 엔진 서버

## 5. Render에서 입력해야 하는 값

`kita-api` 서비스에 입력:

```text
ADMIN_PIN=너만 아는 관리자 코드
MONGO_URI=MongoDB Atlas 연결 주소
AI_API_KEY=네가 산 API 키
```

나중에 준비되면 추가:

```text
KAKAO_REST_API_KEY=
TOSS_CLIENT_KEY=
TOSS_SECRET_KEY=
FIREBASE_SERVICE_ACCOUNT_JSON=
FIREBASE_WEB_API_KEY=
FIREBASE_AUTH_DOMAIN=
FIREBASE_PROJECT_ID=kita-ec927
FIREBASE_APP_ID=
FIREBASE_MESSAGING_SENDER_ID=
FIREBASE_STORAGE_BUCKET=
FIREBASE_MEASUREMENT_ID=
```

## 6. 배포 후 확인

Render 배포가 끝나면 아래를 연다.

```text
https://kita-api.onrender.com/
https://kita-api.onrender.com/api/live
https://kita-api.onrender.com/api/health
```

`/api/live`가 되면 웹 서버는 성공.

`/api/health`가 되면 MongoDB + Study AI까지 성공.

## 7. 도메인 연결

오늘 바로는 Render 기본 주소로 테스트한다.

나중에 `.com`을 사면 Render의 `kita-api` 서비스에서 Custom Domains에 연결한다.

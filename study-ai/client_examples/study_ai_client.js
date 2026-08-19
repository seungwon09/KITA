const DEFAULT_BASE_URL = "http://127.0.0.1:8002";

async function requestJson(path, options = {}, baseUrl = DEFAULT_BASE_URL) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Study AI API ${response.status}: ${body}`);
  }
  return response.json();
}

export async function loadStudyAiBootstrap({
  userId = "student-1",
  plan = "pro",
  baseUrl = DEFAULT_BASE_URL,
} = {}) {
  return requestJson(
    `/app-ai/mobile/bootstrap/${encodeURIComponent(userId)}?plan=${encodeURIComponent(plan)}`,
    {},
    baseUrl
  );
}

export async function analyzeStudyProblem({
  userId = "student-1",
  problemText,
  subject = "math",
  plan = "pro",
  userSolution = null,
  elapsedSeconds = 0,
  wasCorrect = true,
  baseUrl = DEFAULT_BASE_URL,
}) {
  return requestJson(
    "/app-ai/mobile/analyze",
    {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        problem_text: problemText,
        subject,
        plan,
        student_level: "intermediate",
        user_solution: userSolution,
        elapsed_seconds: elapsedSeconds,
        was_correct: wasCorrect,
        time_limit_seconds: 90,
        include_practice: true,
        include_home: true,
        include_personalization: true,
        include_training_queue: true,
      }),
    },
    baseUrl
  );
}

export async function analyzeStudyPhoto({
  userId = "student-1",
  imageFile,
  plan = "pro",
  baseUrl = DEFAULT_BASE_URL,
}) {
  const formData = new FormData();
  formData.append("image", imageFile);
  formData.append("user_id", userId);
  formData.append("subject", "auto");
  formData.append("plan", plan);
  formData.append("student_level", "intermediate");
  formData.append("elapsed_seconds", "0");
  formData.append("was_correct", "true");
  formData.append("auto_solve", "true");

  const response = await fetch(`${baseUrl}/app-ai/mobile/ocr-analyze`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Study AI OCR API ${response.status}: ${body}`);
  }
  return response.json();
}

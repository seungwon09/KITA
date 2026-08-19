const state = {
  subject: "math",
  fastOnly: false,
  timerStartedAt: null,
  timerInterval: null,
  elapsedSeconds: 0,
};

const $ = (id) => document.getElementById(id);

async function checkHealth() {
  try {
    const response = await fetch("/health", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    $("status").textContent = data.mock_llm ? "Mock 모델" : `로컬 모델 · ${data.model}`;
    $("status").classList.remove("offline");
  } catch (error) {
    $("status").textContent = "서버 연결 끊김";
    $("status").classList.add("offline");
  }
}

function setSubject(subject) {
  state.subject = subject;
  document.querySelectorAll(".segment").forEach((button) => {
    button.classList.toggle("active", button.dataset.subject === subject);
  });
}

function setBusy(isBusy) {
  $("solveBtn").disabled = isBusy;
  $("ocrBtn").disabled = isBusy;
  $("status").textContent = isBusy ? "풀이 중" : "로컬 모델";
}

function setOcrBusy(isBusy) {
  $("ocrBtn").disabled = isBusy;
  $("ocrStatus").textContent = isBusy ? "OCR 처리 중" : "OCR 대기";
}

function setOcrWarning(message) {
  const warning = $("ocrWarning");
  warning.textContent = message || "";
  warning.hidden = !message;
}

function formatTime(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const seconds = Math.floor(totalSeconds % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function startTimer() {
  if (state.timerInterval) clearInterval(state.timerInterval);
  state.timerStartedAt = Date.now() - state.elapsedSeconds * 1000;
  state.timerInterval = setInterval(updateTimer, 250);
  $("examNotice").hidden = true;
}

function stopTimer() {
  updateTimer();
  if (state.timerInterval) clearInterval(state.timerInterval);
  state.timerInterval = null;
  $("elapsedSeconds").value = Math.max(0, Math.round(state.elapsedSeconds));
}

function resetTimer() {
  if (state.timerInterval) clearInterval(state.timerInterval);
  state.timerInterval = null;
  state.timerStartedAt = null;
  state.elapsedSeconds = 0;
  $("timerDisplay").textContent = "00:00";
  $("elapsedSeconds").value = 0;
  $("examNotice").hidden = true;
}

function updateTimer() {
  if (state.timerStartedAt === null) return;
  state.elapsedSeconds = (Date.now() - state.timerStartedAt) / 1000;
  const rounded = Math.round(state.elapsedSeconds);
  $("timerDisplay").textContent = formatTime(rounded);
  $("elapsedSeconds").value = rounded;
  const limit = Number($("timeLimitSeconds").value || 0);
  if (limit > 0 && rounded > limit) {
    $("examNotice").hidden = false;
    $("examNotice").textContent = "제한 시간을 넘었습니다. 이 유형은 빠른 풀이 훈련 대상으로 저장하세요.";
  }
}

function renderExamStrategy(data) {
  const elapsed = Number($("elapsedSeconds").value || 0);
  const limit = Number($("timeLimitSeconds").value || 0);
  const speed = elapsed <= limit ? "시간 안에 풀이" : "시간 초과";
  const action =
    elapsed <= limit
      ? "같은 유형을 한 단계 어려운 문제로 넘어가도 됩니다."
      : "기본 풀이를 다시 보고, 빠른 풀이만 보고 재도전하세요.";
  $("examStrategy").innerHTML = `
    <div class="metric-grid">
      <div class="metric"><span>실제 시간</span><strong>${elapsed}초</strong></div>
      <div class="metric"><span>제한 시간</span><strong>${limit || "-"}초</strong></div>
      <div class="metric"><span>판정</span><strong>${speed}</strong></div>
      <div class="metric"><span>풀이 엔진</span><strong>${data.engine === "rules" ? "즉시" : "LLM"}</strong></div>
    </div>
    <pre>${action}</pre>
  `;
}

function renderSolution(data) {
  $("verifiedAnswer").textContent = data.verified_answer || "검산 답 없음";
  const engineLabel = data.engine === "rules" ? "즉시 풀이" : "로컬 모델";
  $("difficulty").textContent = `${data.analysis.subject} / ${data.analysis.difficulty} / ${engineLabel}`;
  $("analysis").textContent = `${data.analysis.unit} · ${data.analysis.problem_type}`;
  $("basicSolution").textContent = data.basic_solution || "";
  $("fastSolution").textContent = data.fast_solution || "";
  $("similarProblem").textContent = data.similar_problem || "";
  document.querySelector(".result-card.wide").style.display = state.fastOnly ? "none" : "";

  if (data.quality_warnings && data.quality_warnings.length > 0) {
    $("analysis").innerHTML += `<br><span class="warn">${data.quality_warnings.join(" / ")}</span>`;
  }
  renderExamStrategy(data);
}

function detectSubjectFromText(text) {
  const scienceWords = ["질량", "가속도", "힘", "전압", "전류", "몰", "속력", "속도", "밀도", "부피", "압력", "운동에너지", "위치에너지", "저항"];
  return scienceWords.some((word) => text.includes(word)) ? "science" : "math";
}

function renderInsight(data) {
  $("insight").textContent = [
    `풀이 기록: ${data.total_attempts}`,
    `약한 단원: ${data.weak_units.join(", ") || "없음"}`,
    `느린 유형: ${data.slow_types.join(", ") || "없음"}`,
    `반복 실수: ${data.repeated_mistakes.join(", ") || "없음"}`,
    `다음 추천: ${data.next_recommendation}`,
  ].join("\n");
}

function renderHistory(items) {
  const history = $("history");
  if (!items.length) {
    history.textContent = "아직 기록이 없습니다.";
    return;
  }
  history.innerHTML = items
    .map((item) => {
      const result = item.was_correct === null ? "미기록" : item.was_correct ? "맞음" : "틀림";
      const time = item.elapsed_seconds === null ? "-" : `${item.elapsed_seconds}초`;
      return `
        <button class="history-item" type="button" data-problem="${escapeHtml(item.problem_text)}" data-subject="${item.subject}">
          <span>${escapeHtml(item.problem_text)}</span>
          <small>${item.subject} · ${item.unit} · ${result} · ${time}</small>
        </button>
      `;
    })
    .join("");

  document.querySelectorAll(".history-item").forEach((button) => {
    button.addEventListener("click", () => {
      $("problemText").value = button.dataset.problem;
      setSubject(button.dataset.subject);
    });
  });
}

function renderAttemptList(targetId, items, emptyText) {
  const target = $(targetId);
  if (!items.length) {
    target.textContent = emptyText;
    return;
  }
  target.innerHTML = items
    .map((item) => {
      const result = item.was_correct === null ? "미기록" : item.was_correct ? "맞음" : "틀림";
      const time = item.elapsed_seconds === null ? "-" : `${item.elapsed_seconds}초`;
      return `
        <button class="history-item" type="button" data-problem="${escapeHtml(item.problem_text)}" data-subject="${item.subject}">
          <span>${escapeHtml(item.problem_text)}</span>
          <small>${item.subject} · ${item.problem_type} · ${result} · ${time}</small>
        </button>
      `;
    })
    .join("");
  target.querySelectorAll(".history-item").forEach((button) => {
    button.addEventListener("click", () => {
      $("problemText").value = button.dataset.problem;
      setSubject(button.dataset.subject);
    });
  });
}

function renderReviewBundle(data) {
  $("review").innerHTML = `
    <div class="recommend-head">
      <strong>오늘 복습</strong>
      <span>${escapeHtml(data.message)}</span>
    </div>
    <div class="recommend-columns">
      <div>
        <h3>복습 리스트</h3>
        <ul>${data.today_review.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>재출제</h3>
        <ul class="problem-links">
          ${data.retry_problems
            .map(
              (item) =>
                `<li><button type="button" class="problem-pick" data-problem="${escapeHtml(item)}">${escapeHtml(item)}</button><button type="button" class="problem-solve" data-problem="${escapeHtml(item)}">바로 풀이</button></li>`
            )
            .join("")}
        </ul>
      </div>
      <div>
        <h3>최근 오답</h3>
        <ul>${data.wrong_items.slice(0, 5).map((item) => `<li>${escapeHtml(item.problem_text)}</li>`).join("") || "<li>없음</li>"}</ul>
      </div>
      <div>
        <h3>느린 문제</h3>
        <ul>${data.slow_items.slice(0, 5).map((item) => `<li>${escapeHtml(item.problem_text)}</li>`).join("") || "<li>없음</li>"}</ul>
      </div>
    </div>
  `;
  $("review").querySelectorAll(".problem-pick").forEach((button) => {
    button.addEventListener("click", () => {
      $("problemText").value = button.dataset.problem;
      setSubject(detectSubjectFromText(button.dataset.problem));
    });
  });
  $("review").querySelectorAll(".problem-solve").forEach((button) => {
    button.addEventListener("click", async () => {
      $("problemText").value = button.dataset.problem;
      setSubject(detectSubjectFromText(button.dataset.problem));
      await solveProblem();
    });
  });
}

function renderProgress(data) {
  $("metricTotal").textContent = data.total_attempts;
  $("metricAccuracy").textContent = `${data.accuracy_percent}%`;
  $("metricAvgTime").textContent =
    data.average_elapsed_seconds === null ? "-" : `${data.average_elapsed_seconds}초`;
  $("metricRecentTime").textContent =
    data.recent_average_elapsed_seconds === null
      ? "-"
      : `${data.recent_average_elapsed_seconds}초`;
  $("progress").textContent = [
    `맞은 문제: ${data.correct_attempts}`,
    `틀린 문제: ${data.wrong_attempts}`,
    `추세: ${data.trend_message}`,
  ].join("\n");
}

function renderRecommendation(data) {
  $("recommendation").innerHTML = `
    <div class="recommend-head">
      <strong>${escapeHtml(data.priority)}</strong>
      <span>${escapeHtml(data.message)}</span>
    </div>
    <div class="recommend-columns">
      <div>
        <h3>오늘 할 일</h3>
        <ol>${data.today_plan.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
      </div>
      <div>
        <h3>복습 대상</h3>
        <ul>${data.review_targets.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>추천 유형</h3>
        <ul>${data.recommended_problem_types.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>오늘 추천 문제</h3>
        <ul class="problem-links">
          ${data.recommended_problems
            .map(
              (item) =>
                `<li><button type="button" class="problem-pick" data-problem="${escapeHtml(item)}">${escapeHtml(item)}</button><button type="button" class="problem-solve" data-problem="${escapeHtml(item)}">바로 풀이</button></li>`
            )
            .join("")}
        </ul>
      </div>
    </div>
  `;

  document.querySelectorAll(".problem-pick").forEach((button) => {
    button.addEventListener("click", () => {
      $("problemText").value = button.dataset.problem;
      if (
        button.dataset.problem.includes("질량") ||
        button.dataset.problem.includes("전압") ||
        button.dataset.problem.includes("몰")
      ) {
        setSubject("science");
      } else {
        setSubject("math");
      }
    });
  });
  document.querySelectorAll(".problem-solve").forEach((button) => {
    button.addEventListener("click", async () => {
      $("problemText").value = button.dataset.problem;
      setSubject(detectSubjectFromText(button.dataset.problem));
      await solveProblem();
    });
  });
}

function renderConcept(data) {
  $("studyGuide").innerHTML = `
    <div class="recommend-head">
      <strong>${escapeHtml(data.unit)}</strong>
      <span>${escapeHtml(data.one_line)}</span>
    </div>
    <div class="recommend-columns">
      <div>
        <h3>핵심</h3>
        <ul>${data.core_points.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>출제 패턴</h3>
        <ul>${data.exam_patterns.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>실수</h3>
        <ul>${data.common_mistakes.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>검산</h3>
        <p>${escapeHtml(data.quick_check)}</p>
      </div>
    </div>
  `;
}

function renderFormula(data) {
  $("studyGuide").innerHTML = `
    <div class="recommend-head">
      <strong>${data.subject === "science" ? "과학 공식 노트" : "수학 공식 노트"}</strong>
      <span>문제에서 바로 꺼내 쓸 공식만 모았습니다.</span>
    </div>
    <div class="formula-list">
      ${data.formulas
        .map(
          (item) => `
            <button class="formula-card" type="button" data-formula="${escapeHtml(item.formula)}">
              <strong>${escapeHtml(item.name)}</strong>
              <code>${escapeHtml(item.formula)}</code>
              <span>${escapeHtml(item.tip)}</span>
            </button>
          `
        )
        .join("")}
    </div>
    <div class="recommend-columns two">
      <div>
        <h3>무조건 암기</h3>
        <ul>${data.must_memorize.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>언제 쓰나</h3>
        <ul>${data.use_when.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
    </div>
  `;

  $("studyGuide").querySelectorAll(".formula-card").forEach((button) => {
    button.addEventListener("click", () => {
      $("problemText").value = `${button.dataset.formula} 공식을 쓰는 기본 문제를 내고 풀어줘`;
    });
  });
}

function renderLearningRoute(data) {
  $("studyGuide").innerHTML = `
    <div class="recommend-head">
      <strong>${escapeHtml(data.priority)}</strong>
      <span>${escapeHtml(data.message)}</span>
    </div>
    <div class="recommend-columns">
      <div>
        <h3>전체 루트</h3>
        <ol>${data.route.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
      </div>
      <div>
        <h3>오늘 미션</h3>
        <ol>${data.daily_mission.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
      </div>
      <div>
        <h3>다음 해금</h3>
        <p>${escapeHtml(data.next_unlock)}</p>
      </div>
      <div>
        <h3>바로 할 일</h3>
        <button type="button" class="problem-solve" id="routeReviewBtn">복습 묶음 열기</button>
      </div>
    </div>
  `;
  $("routeReviewBtn").addEventListener("click", loadReviewBundle);
}

function renderProblemSet(data) {
  $("practiceSet").innerHTML = `
    <div class="recommend-head">
      <strong>${data.subject === "science" ? "과학" : "수학"} ${escapeHtml(data.difficulty)}</strong>
      <span>${escapeHtml(data.message)}</span>
    </div>
    <div class="practice-list">
      ${data.problems
        .map(
          (item, index) => `
            <div class="practice-card">
              <div>
                <strong>${index + 1}. ${escapeHtml(item.problem)}</strong>
                <span>${escapeHtml(item.unit)} · ${escapeHtml(item.target_skill)} · 답 ${escapeHtml(item.expected_answer)}</span>
              </div>
              <div class="practice-actions">
                <button type="button" class="problem-pick" data-problem="${escapeHtml(item.problem)}" data-subject="${escapeHtml(item.subject)}">입력</button>
                <button type="button" class="problem-solve" data-problem="${escapeHtml(item.problem)}" data-subject="${escapeHtml(item.subject)}">바로 풀이</button>
              </div>
            </div>
          `
        )
        .join("")}
    </div>
  `;
  $("practiceSet").querySelectorAll(".problem-pick").forEach((button) => {
    button.addEventListener("click", () => {
      $("problemText").value = button.dataset.problem;
      setSubject(button.dataset.subject);
    });
  });
  $("practiceSet").querySelectorAll(".problem-solve").forEach((button) => {
    button.addEventListener("click", async () => {
      $("problemText").value = button.dataset.problem;
      setSubject(button.dataset.subject);
      await solveProblem();
    });
  });
}

function renderAppAi(data) {
  $("appAiResult").innerHTML = `
    <div class="recommend-head">
      <strong>앱 API 응답 · ${escapeHtml(data.feature_access.plan)}</strong>
      <span>request_id: ${escapeHtml(data.request_id)}</span>
    </div>
    <div class="app-card-grid">
      ${data.ui_cards
        .map(
          (card) => `
            <div class="metric">
              <span>${escapeHtml(card.title)}</span>
              <strong>${escapeHtml(card.body)}</strong>
            </div>
          `
        )
        .join("")}
    </div>
    <div class="recommend-columns">
      <div>
        <h3>풀이 평가</h3>
        <p>${escapeHtml(data.evaluation.verdict)} · ${data.evaluation.score}점</p>
        <ul>${data.evaluation.missing_steps.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>실수 감지</h3>
        <p>${escapeHtml(data.mistake_report.risk_level)}</p>
        <ul>${data.mistake_report.detected_mistakes.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>시험 전략</h3>
        <p>${escapeHtml(data.exam_strategy.speed_judgement)}</p>
        <ul>${data.exam_strategy.recommended_order.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>잠긴 기능</h3>
        <ul>${data.feature_access.locked_features.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>없음</li>"}</ul>
      </div>
    </div>
    <details class="json-box">
      <summary>앱 개발용 JSON 보기</summary>
      <pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>
    </details>
  `;
}

function renderAppHome(data) {
  $("appProfile").innerHTML = `
    <div class="recommend-head">
      <strong>앱 홈 데이터</strong>
      <span>${escapeHtml(data.user_id)} · 오늘 사용 ${data.usage.used_today}/${data.usage.daily_limit}</span>
    </div>
    <div class="app-card-grid">
      ${data.dashboard_cards
        .map(
          (card) => `
            <div class="metric">
              <span>${escapeHtml(card.title)}</span>
              <strong>${escapeHtml(card.body)}</strong>
            </div>
          `
        )
        .join("")}
    </div>
    <div class="recommend-columns">
      <div>
        <h3>빠른 실행</h3>
        <ul>${data.quick_actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>추천</h3>
        <p>${escapeHtml(data.recommendation.priority)}</p>
        <ul>${data.recommendation.today_plan.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>학습 스타일</h3>
        <p>${escapeHtml(data.learning_style.primary_style)}</p>
        <ul>${data.learning_style.best_study_method.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>속도</h3>
        <p>${escapeHtml(data.speed_optimization.message)}</p>
      </div>
    </div>
  `;
}

function renderProfileBlock(title, data) {
  $("appProfile").innerHTML = `
    <div class="recommend-head">
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(data.user_id || data.plan || data.feature || "app-ai")}</span>
    </div>
    <details class="json-box" open>
      <summary>결과 JSON</summary>
      <pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>
    </details>
  `;
}

function renderPersonalization(data) {
  $("appProfile").innerHTML = `
    <div class="recommend-head">
      <strong>개인화 대시보드 · ${escapeHtml(data.learner_stage)}</strong>
      <span>${escapeHtml(data.today_focus)} 중심으로 다음 문제를 고릅니다.</span>
    </div>
    <div class="metric-grid">
      <div class="metric"><span>기록</span><strong>${data.total_attempts}</strong></div>
      <div class="metric"><span>정답률</span><strong>${data.overall_accuracy_percent}%</strong></div>
      <div class="metric"><span>평균 시간</span><strong>${data.average_seconds === null ? "-" : `${data.average_seconds}초`}</strong></div>
      <div class="metric"><span>위험</span><strong>${data.risk_flags.length}</strong></div>
    </div>
    <div class="recommend-columns">
      <div>
        <h3>강점</h3>
        <ul>${data.strongest_skills.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>약점</h3>
        <ul>${data.weakest_skills.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>위험 신호</h3>
        <ul>${data.risk_flags.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>다음 행동</h3>
        <ol>${data.next_best_actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
      </div>
    </div>
    <div class="skill-list">
      ${data.skill_profiles
        .map(
          (item) => `
            <div class="skill-card">
              <div>
                <strong>${escapeHtml(item.unit)} · ${escapeHtml(item.problem_type)}</strong>
                <span>${escapeHtml(item.label)} · ${escapeHtml(item.speed_level)}</span>
              </div>
              <div class="skill-bars">
                <span>숙련도 ${item.mastery_score}</span>
                <meter min="0" max="100" value="${item.mastery_score}"></meter>
                <span>약점 ${item.weakness_score}</span>
                <meter min="0" max="100" value="${item.weakness_score}"></meter>
              </div>
              <p>${escapeHtml(item.next_action)}</p>
            </div>
          `
        )
        .join("")}
    </div>
    <details class="json-box">
      <summary>앱 개발용 JSON 보기</summary>
      <pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>
    </details>
  `;
}

function renderTrainingQueue(data) {
  $("appProfile").innerHTML = `
    <div class="recommend-head">
      <strong>${escapeHtml(data.queue_title)}</strong>
      <span>${data.estimated_minutes}분 · ${escapeHtml(data.finish_rule)}</span>
    </div>
    <div class="practice-list">
      ${data.items
        .map(
          (item, index) => `
            <div class="practice-card">
              <div>
                <strong>${index + 1}. ${escapeHtml(item.problem)}</strong>
                <span>${escapeHtml(item.unit)} · ${escapeHtml(item.mode)} · 목표 ${item.target_seconds}초</span>
                <p>${escapeHtml(item.reason)} / ${escapeHtml(item.expected_benefit)}</p>
              </div>
              <div class="practice-actions">
                <button type="button" class="problem-pick" data-problem="${escapeHtml(item.problem)}" data-subject="${escapeHtml(item.subject)}">입력</button>
                <button type="button" class="problem-solve" data-problem="${escapeHtml(item.problem)}" data-subject="${escapeHtml(item.subject)}">바로 풀이</button>
              </div>
            </div>
          `
        )
        .join("")}
    </div>
  `;
  $("appProfile").querySelectorAll(".problem-pick").forEach((button) => {
    button.addEventListener("click", () => {
      $("problemText").value = button.dataset.problem;
      setSubject(button.dataset.subject);
    });
  });
  $("appProfile").querySelectorAll(".problem-solve").forEach((button) => {
    button.addEventListener("click", async () => {
      $("problemText").value = button.dataset.problem;
      setSubject(button.dataset.subject);
      await solveProblem();
    });
  });
}

function renderWeaknessDive(data) {
  $("appProfile").innerHTML = `
    <div class="recommend-head">
      <strong>약점 심층 · ${escapeHtml(data.target)}</strong>
      <span>${escapeHtml(data.success_metric)}</span>
    </div>
    <div class="recommend-columns">
      <div>
        <h3>원인</h3>
        <ul>${data.root_causes.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>근거</h3>
        <ul>${data.evidence.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
      <div>
        <h3>훈련</h3>
        <ol>${data.drills.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
      </div>
      <div>
        <h3>다음 분기</h3>
        <p>${escapeHtml(data.escalation_rule)}</p>
      </div>
    </div>
  `;
}

function renderPlans(data) {
  $("appProfile").innerHTML = `
    <div class="recommend-head">
      <strong>요금제 기능표</strong>
      <span>기본 요금제: ${escapeHtml(data.default_plan)}</span>
    </div>
    <div class="plan-grid">
      ${data.plans
        .map(
          (plan) => `
            <div class="plan-card">
              <h3>${escapeHtml(plan.plan)} · ${escapeHtml(plan.price_label)}</h3>
              <strong>${plan.daily_limit}회/일</strong>
              <p>${escapeHtml(plan.recommended_for)}</p>
              <h4>가능</h4>
              <ul>${plan.features.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
              <h4>잠김</h4>
              <ul>${plan.locked_features.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>없음</li>"}</ul>
            </div>
          `
        )
        .join("")}
    </div>
  `;
}

function renderFeatureRegistry(data) {
  $("appProfile").innerHTML = `
    <div class="recommend-head">
      <strong>기능 레지스트리</strong>
      <span>${data.features.length}개 기능 · UI 버튼은 action만 연결하면 됩니다.</span>
    </div>
    <div class="practice-list">
      ${data.features
        .map(
          (item) => `
            <div class="practice-card">
              <div>
                <strong>${escapeHtml(item.label)} · ${escapeHtml(item.action)}</strong>
                <span>${escapeHtml(item.category)} · ${escapeHtml(item.required_plan)} · ${escapeHtml(item.ui_target)}</span>
                <p>${escapeHtml(item.description)}</p>
              </div>
              <div class="practice-actions">
                <button type="button" class="production-action" data-action="${escapeHtml(item.action)}">실행</button>
              </div>
            </div>
          `
        )
        .join("")}
    </div>
  `;
  $("appProfile").querySelectorAll(".production-action").forEach((button) => {
    button.addEventListener("click", () => runProductionAction(button.dataset.action));
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderOcrSummary(ocr) {
  const warnings = ocr.warnings || [];
  const corrections = ocr.corrections || [];
  const formulas = ocr.formula_candidates || [];
  const quality = ocr.image_quality || {};
  const candidates = ocr.candidates || [];
  return `
    <div class="recommend-columns">
      <div><h3>인식 과목</h3><p>${escapeHtml(ocr.detected_subject || "unknown")} / ${escapeHtml(ocr.detected_unit || "미분류")}</p></div>
      <div><h3>문제 유형</h3><p>${escapeHtml(ocr.problem_type || "일반 문제")}</p></div>
      <div><h3>신뢰도</h3><p>${Math.round((ocr.confidence || 0) * 100)}%</p></div>
      <div><h3>품질</h3><p>${escapeHtml(quality.width || "-")}x${escapeHtml(quality.height || "-")} / 흔들림 ${escapeHtml(quality.blur_score || "-")}</p></div>
    </div>
    <div class="recommend-columns">
      <div><h3>인식된 수식</h3><ul>${formulas.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>없음</li>"}</ul></div>
      <div><h3>자동 보정</h3><ul>${corrections.slice(0, 6).map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>없음</li>"}</ul></div>
      <div><h3>확인 필요</h3><ul>${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("") || "<li>없음</li>"}</ul></div>
      <div><h3>후보</h3><ul>${candidates.slice(0, 3).map((item) => `<li>${escapeHtml(item.variant)} · ${Math.round((item.confidence || 0) * 100)}%</li>`).join("") || "<li>없음</li>"}</ul></div>
    </div>
  `;
}

async function solveProblem() {
  setBusy(true);
  try {
    if (state.timerInterval) stopTimer();
    setSubject(detectSubjectFromText($("problemText").value));
    const response = await fetch("/solve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: $("userId").value || "student-1",
        problem_text: $("problemText").value,
        subject: state.subject,
        student_level: "intermediate",
        mode: "compare",
        user_solution: $("userSolution").value || null,
        elapsed_seconds: Number($("elapsedSeconds").value || 0),
        was_correct: $("wasCorrect").value === "true",
      }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    renderSolution(await response.json());
  } catch (error) {
    $("basicSolution").textContent = `오류: ${error.message}`;
  } finally {
    setBusy(false);
  }
}

function toggleFastOnly() {
  state.fastOnly = !state.fastOnly;
  $("fastOnlyBtn").classList.toggle("active-action", state.fastOnly);
  document.querySelector(".result-card.wide").style.display = state.fastOnly ? "none" : "";
}

async function copyResult() {
  const text = [
    `검산 답: ${$("verifiedAnswer").textContent}`,
    "",
    "[빠른 풀이]",
    $("fastSolution").textContent,
    "",
    "[기본 풀이]",
    $("basicSolution").textContent,
  ].join("\n");
  await navigator.clipboard.writeText(text);
  $("status").textContent = "결과 복사됨";
}

async function loadInsight() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/insight`);
  if (!response.ok) {
    $("insight").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderInsight(await response.json());
}

async function loadHistory() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/attempts?limit=20`);
  if (!response.ok) {
    $("history").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderHistory(await response.json());
}

async function loadWrongOnly() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/attempts/wrong?limit=20`);
  if (!response.ok) {
    $("review").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderAttemptList("review", await response.json(), "아직 오답 기록이 없습니다.");
}

async function loadSlowOnly() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/attempts/slow?limit=20`);
  if (!response.ok) {
    $("review").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderAttemptList("review", await response.json(), "아직 느린 문제 기록이 없습니다.");
}

async function loadReviewBundle() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/review`);
  if (!response.ok) {
    $("review").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderReviewBundle(await response.json());
}

async function loadProgress() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/progress`);
  if (!response.ok) {
    $("progress").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProgress(await response.json());
}

async function loadRecommendation() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/recommendation`);
  if (!response.ok) {
    $("recommendation").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderRecommendation(await response.json());
}

async function loadConcept() {
  const response = await fetch(`/study/concepts?subject=${encodeURIComponent(state.subject)}`);
  if (!response.ok) {
    $("studyGuide").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderConcept(await response.json());
}

async function loadFormula() {
  const response = await fetch(`/study/formulas?subject=${encodeURIComponent(state.subject)}`);
  if (!response.ok) {
    $("studyGuide").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderFormula(await response.json());
}

async function loadLearningRoute() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/learning-route`);
  if (!response.ok) {
    $("studyGuide").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderLearningRoute(await response.json());
}

async function loadGeneratedProblems() {
  const response = await fetch(`/practice/generate?subject=${encodeURIComponent(state.subject)}&difficulty=same&count=5`);
  if (!response.ok) {
    $("practiceSet").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProblemSet(await response.json());
}

async function loadAdaptiveProblems() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/adaptive-problems?subject=${encodeURIComponent(state.subject)}`);
  if (!response.ok) {
    $("practiceSet").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProblemSet(await response.json());
}

async function loadExpectedProblems() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/expected-problems?subject=${encodeURIComponent(state.subject)}`);
  if (!response.ok) {
    $("practiceSet").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProblemSet(await response.json());
}

async function loadTargetedPractice() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/students/${encodeURIComponent(userId)}/targeted-practice?subject=mixed&count=8`);
  if (!response.ok) {
    $("practiceSet").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProblemSet(await response.json());
}

async function loadAppAiAnalysis() {
  setBusy(true);
  try {
    const response = await fetch("/app-ai/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: $("userId").value || "student-1",
        problem_text: $("problemText").value,
        subject: state.subject,
        plan: $("planTier").value,
        student_level: "intermediate",
        user_solution: $("userSolution").value || null,
        elapsed_seconds: Number($("elapsedSeconds").value || 0),
        was_correct: $("wasCorrect").value === "true",
        time_limit_seconds: Number($("timeLimitSeconds").value || 90),
        include_practice: true,
      }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    renderSolution(data.solve);
    renderInsight(data.insight);
    renderRecommendation(data.recommendation);
    renderLearningRoute(data.learning_route);
    if (data.practice_set) renderProblemSet(data.practice_set);
    renderAppAi(data);
  } catch (error) {
    $("appAiResult").textContent = `오류: ${error.message}`;
  } finally {
    setBusy(false);
  }
}

async function loadMobileConfig() {
  const response = await fetch("/app-ai/mobile/config");
  if (!response.ok) {
    $("appAiResult").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("모바일 앱 설정", await response.json());
}

async function loadMobileBundle() {
  setBusy(true);
  try {
    const response = await fetch("/app-ai/mobile/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: $("userId").value || "student-1",
        problem_text: $("problemText").value,
        subject: state.subject,
        plan: $("planTier").value,
        student_level: "intermediate",
        user_solution: $("userSolution").value || null,
        elapsed_seconds: Number($("elapsedSeconds").value || 0),
        was_correct: $("wasCorrect").value === "true",
        time_limit_seconds: Number($("timeLimitSeconds").value || 90),
        include_practice: true,
        include_home: true,
        include_personalization: true,
        include_training_queue: true,
      }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    renderSolution(data.analyze.solve);
    if (data.home) renderAppHome(data.home);
    if (data.personalization) renderPersonalization(data.personalization);
    if (data.training_queue) renderTrainingQueue(data.training_queue);
    $("appAiResult").innerHTML = `
      <div class="recommend-head">
        <strong>모바일 앱 번들</strong>
        <span>${escapeHtml(data.config.api_version)} · ${escapeHtml(data.analyze.request_id)}</span>
      </div>
      <div class="recommend-columns">
        <div><h3>정답</h3><p>${escapeHtml(data.analyze.solve.verified_answer || "검산 답 없음")}</p></div>
        <div><h3>엔진</h3><p>${escapeHtml(data.analyze.solve.engine)}</p></div>
        <div><h3>다음 화면</h3><ul>${data.next_client_actions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
        <div><h3>API</h3><p>${escapeHtml(data.config.endpoints.analyze_text)}</p></div>
      </div>
      <details class="json-box">
        <summary>앱 개발용 JSON 보기</summary>
        <pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>
      </details>
    `;
  } catch (error) {
    $("appAiResult").textContent = `오류: ${error.message}`;
  } finally {
    setBusy(false);
  }
}

async function loadMobileOcrAnalyze() {
  const file = $("imageInput").files[0];
  if (!file) {
    $("appAiResult").textContent = "사진을 먼저 선택하세요.";
    return;
  }
  setBusy(true);
  try {
    const formData = new FormData();
    formData.append("image", file);
    formData.append("user_id", $("userId").value || "student-1");
    formData.append("subject", "auto");
    formData.append("plan", $("planTier").value);
    formData.append("student_level", "intermediate");
    formData.append("elapsed_seconds", String(Number($("elapsedSeconds").value || 0)));
    formData.append("was_correct", $("wasCorrect").value);
    formData.append("auto_solve", "true");
    const response = await fetch("/app-ai/mobile/ocr-analyze", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    $("problemText").value = data.ocr.extracted_text;
    if (data.ocr.detected_subject && data.ocr.detected_subject !== "unknown") {
      setSubject(data.ocr.detected_subject);
    }
    if (data.analyze) renderSolution(data.analyze.solve);
    $("appAiResult").innerHTML = `
      <div class="recommend-head">
        <strong>사진 앱 분석</strong>
        <span>OCR 신뢰도 ${Math.round(data.ocr.confidence * 100)}%</span>
      </div>
      ${data.warning ? `<div class="notice">${escapeHtml(data.warning)}</div>` : ""}
      ${renderOcrSummary(data.ocr)}
      <details class="json-box" open>
        <summary>결과 JSON</summary>
        <pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre>
      </details>
    `;
  } catch (error) {
    $("appAiResult").textContent = `오류: ${error.message}`;
  } finally {
    setBusy(false);
  }
}

async function loadAppHome() {
  const userId = $("userId").value || "student-1";
  const plan = $("planTier").value;
  const response = await fetch(`/app-ai/home/${encodeURIComponent(userId)}?plan=${encodeURIComponent(plan)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderAppHome(await response.json());
}

async function loadLearningStyleProfile() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/learning-style/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("학습 스타일", await response.json());
}

async function loadMentalAnalysis() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/mental/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("멘탈 분석", await response.json());
}

async function loadSpeedOptimization() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/speed/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("속도 최적화", await response.json());
}

async function loadAppSession() {
  const userId = $("userId").value || "student-1";
  const plan = $("planTier").value;
  const response = await fetch(`/app-ai/session/${encodeURIComponent(userId)}?plan=${encodeURIComponent(plan)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("앱 세션", await response.json());
}

async function loadPlans() {
  const response = await fetch("/app-ai/plans");
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderPlans(await response.json());
}

async function loadFeatureGate() {
  const response = await fetch("/app-ai/gate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: $("userId").value || "student-1",
      plan: $("planTier").value,
      feature: "solution_evaluation",
    }),
  });
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("기능 잠금 판정", await response.json());
}

async function loadStudySession() {
  const userId = $("userId").value || "student-1";
  const plan = $("planTier").value;
  const response = await fetch(`/app-ai/study-session/${encodeURIComponent(userId)}?plan=${encodeURIComponent(plan)}&subject=${encodeURIComponent(state.subject)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("오늘 학습 세션", await response.json());
}

async function loadReviewSchedule() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/review-schedule/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("복습 일정", await response.json());
}

async function loadAdminSmokeTest() {
  const response = await fetch("/admin/smoke-test");
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("관리자 점검", await response.json());
}

async function loadProductionStatus() {
  const response = await fetch("/app-ai/production/status");
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("완성 상태", await response.json());
}

async function loadFeatureRegistry() {
  const response = await fetch("/app-ai/production/registry");
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderFeatureRegistry(await response.json());
}

async function runProductionAction(action) {
  const response = await fetch("/app-ai/production/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action,
      user_id: $("userId").value || "student-1",
      plan: $("planTier").value,
      subject: state.subject,
      problem_text: $("problemText").value,
      user_solution: $("userSolution").value || null,
      elapsed_seconds: Number($("elapsedSeconds").value || 0),
      was_correct: $("wasCorrect").value === "true",
      time_limit_seconds: Number($("timeLimitSeconds").value || 90),
      count: 8,
    }),
  });
  if (!response.ok) {
    $("appAiResult").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  const data = await response.json();
  renderProfileBlock(`실행 결과 · ${action}`, data);
}

async function saveProfile() {
  const userId = $("userId").value || "student-1";
  const response = await fetch("/app-ai/profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      nickname: userId,
      grade: "미설정",
      target_exam: "내신/수능",
      target_score: "점수 상승",
      preferred_subjects: ["math", "science"],
      goal_message: "시험 점수 올리기",
    }),
  });
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("프로필", await response.json());
}

async function saveBookmark() {
  const response = await fetch("/app-ai/bookmark", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: $("userId").value || "student-1",
      problem_text: $("problemText").value,
      subject: state.subject,
      note: "나중에 다시 볼 문제",
    }),
  });
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  const saved = await response.json();
  const listResponse = await fetch(`/app-ai/bookmarks/${encodeURIComponent(saved.user_id)}`);
  const list = listResponse.ok ? await listResponse.json() : { saved };
  renderProfileBlock("북마크", list);
}

async function loadStudentReport() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/report/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("학생 리포트", await response.json());
}

async function loadAchievements() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/achievements/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("성취 배지", await response.json());
}

async function loadLeaderboard() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/leaderboard/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("랭킹", await response.json());
}

async function loadNotificationPlan() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/notifications/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("알림 계획", await response.json());
}

async function loadMasteryMap() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/mastery/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("단원 숙련도", await response.json());
}

async function loadPersonalizationDashboard() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/personalization/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderPersonalization(await response.json());
}

async function loadTrainingQueue() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/training-queue/${encodeURIComponent(userId)}?subject=mixed&count=8`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderTrainingQueue(await response.json());
}

async function loadWeaknessDive() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/weakness-deep-dive/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderWeaknessDive(await response.json());
}

async function startDiagnostic() {
  const response = await fetch("/app-ai/diagnostic/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      subject: "mixed",
      count: 8,
      difficulty: "same",
    }),
  });
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("진단 테스트", await response.json());
}

async function loadSolutionVariants() {
  const response = await fetch("/app-ai/solution-variants", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      problem_text: $("problemText").value,
      subject: state.subject,
      student_level: "intermediate",
    }),
  });
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("풀이 4종 비교", await response.json());
}

async function loadTutorHint() {
  const response = await fetch("/app-ai/tutor-hint", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      problem_text: $("problemText").value,
      subject: state.subject,
      step: 1,
      reveal_answer: false,
    }),
  });
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("단계 힌트", await response.json());
}

async function loadErrorTaxonomy() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/error-taxonomy/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("오류 분류", await response.json());
}

async function loadWeeklyPlan() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/weekly-plan/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("7일 계획", await response.json());
}

async function checkAnswer() {
  const response = await fetch("/app-ai/answer-check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      problem_text: $("problemText").value,
      expected_answer: $("verifiedAnswer").textContent === "아직 풀이 전입니다." ? "-3" : $("verifiedAnswer").textContent,
      student_answer: $("userSolution").value || $("verifiedAnswer").textContent,
      subject: state.subject,
    }),
  });
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("답안 채점", await response.json());
}

async function startMockExam() {
  const response = await fetch("/app-ai/mock-exam/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      subject: "mixed",
      count: 10,
      difficulty: "exam",
      time_limit_minutes: 20,
    }),
  });
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("모의고사", await response.json());
}

async function submitMockExamDemo() {
  const startResponse = await fetch("/app-ai/mock-exam/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subject: "mixed", count: 6, difficulty: "exam", time_limit_minutes: 12 }),
  });
  if (!startResponse.ok) {
    $("appProfile").textContent = `오류: HTTP ${startResponse.status}`;
    return;
  }
  const exam = await startResponse.json();
  const answers = exam.questions.slice(0, 6).map((question, index) => ({
    question_id: question.question_id,
    problem: question.problem,
    subject: question.subject,
    unit: question.unit,
    target_skill: question.target_skill,
    expected_answer: question.expected_answer,
    student_answer: index % 3 === 0 ? "모름" : question.expected_answer,
    elapsed_seconds: 70 + index * 15,
    marked_for_review: index % 3 === 0,
  }));
  const response = await fetch("/app-ai/mock-exam/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: $("userId").value || "student-1",
      exam_id: exam.exam_id,
      time_limit_minutes: exam.time_limit_minutes,
      answers,
    }),
  });
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("모의고사 제출", await response.json());
}

async function loadFlashcards() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/flashcards/${encodeURIComponent(userId)}?subject=mixed`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("플래시카드", await response.json());
}

async function loadMistakeNotebook() {
  const userId = $("userId").value || "student-1";
  const response = await fetch(`/app-ai/mistake-notebook/${encodeURIComponent(userId)}`);
  if (!response.ok) {
    $("appProfile").textContent = `오류: HTTP ${response.status}`;
    return;
  }
  renderProfileBlock("고급 오답노트", await response.json());
}

async function readImageText() {
  const file = $("imageInput").files[0];
  if (!file) {
    $("ocrStatus").textContent = "사진을 먼저 선택";
    return;
  }

  setOcrBusy(true);
  setOcrWarning("");
  try {
    const formData = new FormData();
    formData.append("image", file);
    const response = await fetch("/ocr", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    $("problemText").value = data.extracted_text;
    if (data.detected_subject && data.detected_subject !== "unknown") {
      setSubject(data.detected_subject);
    }
    $("ocrStatus").textContent = `신뢰도 ${Math.round(data.confidence * 100)}% · ${data.detected_subject || "unknown"} · ${data.detected_unit || "미분류"}`;
    const warnings = data.warnings || [];
    const corrections = data.corrections || [];
    if (data.needs_review || warnings.length > 0) {
      setOcrWarning(
        ["확인 필요: 등호, 부호, 숫자, 단위를 확인하세요", ...warnings, ...corrections.slice(0, 3)]
          .filter(Boolean)
          .join(" / ")
      );
    }
    if ($("autoSolveAfterOcr").checked && data.extracted_text.trim()) {
      await solveProblem();
    }
  } catch (error) {
    $("ocrStatus").textContent = `OCR 오류: ${error.message}`;
  } finally {
    setOcrBusy(false);
  }
}

function previewImage() {
  const file = $("imageInput").files[0];
  if (!file) return;
  const preview = $("previewImage");
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  $("ocrStatus").textContent = "사진 선택됨";
  setOcrWarning("");
}

document.querySelectorAll(".segment").forEach((button) => {
  button.addEventListener("click", () => setSubject(button.dataset.subject));
});

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    $("problemText").value = button.dataset.example;
    setSubject(button.dataset.subject);
  });
});

$("solveBtn").addEventListener("click", solveProblem);
$("startTimerBtn").addEventListener("click", startTimer);
$("stopTimerBtn").addEventListener("click", stopTimer);
$("resetTimerBtn").addEventListener("click", resetTimer);
$("autoSubjectBtn").addEventListener("click", () => setSubject(detectSubjectFromText($("problemText").value)));
$("fastOnlyBtn").addEventListener("click", toggleFastOnly);
$("copyResultBtn").addEventListener("click", copyResult);
$("insightBtn").addEventListener("click", loadInsight);
$("historyBtn").addEventListener("click", loadHistory);
$("wrongBtn").addEventListener("click", loadWrongOnly);
$("slowBtn").addEventListener("click", loadSlowOnly);
$("reviewBtn").addEventListener("click", loadReviewBundle);
$("progressBtn").addEventListener("click", loadProgress);
$("recommendBtn").addEventListener("click", loadRecommendation);
$("conceptBtn").addEventListener("click", loadConcept);
$("formulaBtn").addEventListener("click", loadFormula);
$("routeBtn").addEventListener("click", loadLearningRoute);
$("generateBtn").addEventListener("click", loadGeneratedProblems);
$("adaptiveBtn").addEventListener("click", loadAdaptiveProblems);
$("expectedBtn").addEventListener("click", loadExpectedProblems);
$("targetedBtn").addEventListener("click", loadTargetedPractice);
$("appAiBtn").addEventListener("click", loadAppAiAnalysis);
$("mobileConfigBtn").addEventListener("click", loadMobileConfig);
$("mobileBundleBtn").addEventListener("click", loadMobileBundle);
$("mobileOcrBtn").addEventListener("click", loadMobileOcrAnalyze);
$("appHomeBtn").addEventListener("click", loadAppHome);
$("styleBtn").addEventListener("click", loadLearningStyleProfile);
$("mentalBtn").addEventListener("click", loadMentalAnalysis);
$("speedBtn").addEventListener("click", loadSpeedOptimization);
$("sessionBtn").addEventListener("click", loadAppSession);
$("plansBtn").addEventListener("click", loadPlans);
$("gateBtn").addEventListener("click", loadFeatureGate);
$("studySessionBtn").addEventListener("click", loadStudySession);
$("reviewScheduleBtn").addEventListener("click", loadReviewSchedule);
$("adminBtn").addEventListener("click", loadAdminSmokeTest);
$("productionStatusBtn").addEventListener("click", loadProductionStatus);
$("featureRegistryBtn").addEventListener("click", loadFeatureRegistry);
$("profileBtn").addEventListener("click", saveProfile);
$("bookmarkBtn").addEventListener("click", saveBookmark);
$("reportBtn").addEventListener("click", loadStudentReport);
$("achievementBtn").addEventListener("click", loadAchievements);
$("leaderboardBtn").addEventListener("click", loadLeaderboard);
$("notificationBtn").addEventListener("click", loadNotificationPlan);
$("masteryBtn").addEventListener("click", loadMasteryMap);
$("personalizationBtn").addEventListener("click", loadPersonalizationDashboard);
$("trainingQueueBtn").addEventListener("click", loadTrainingQueue);
$("weaknessDiveBtn").addEventListener("click", loadWeaknessDive);
$("diagnosticBtn").addEventListener("click", startDiagnostic);
$("variantsBtn").addEventListener("click", loadSolutionVariants);
$("hintBtn").addEventListener("click", loadTutorHint);
$("errorTaxonomyBtn").addEventListener("click", loadErrorTaxonomy);
$("weeklyPlanBtn").addEventListener("click", loadWeeklyPlan);
$("answerCheckBtn").addEventListener("click", checkAnswer);
$("mockExamBtn").addEventListener("click", startMockExam);
$("mockSubmitBtn").addEventListener("click", submitMockExamDemo);
$("flashcardBtn").addEventListener("click", loadFlashcards);
$("mistakeNotebookBtn").addEventListener("click", loadMistakeNotebook);
$("ocrBtn").addEventListener("click", readImageText);
$("imageInput").addEventListener("change", previewImage);

checkHealth();
setInterval(checkHealth, 10000);

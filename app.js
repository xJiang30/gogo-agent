const STORAGE_KEY = "gogo-agent-flow-mvp";
const STATE_VERSION = 6;

const defaultChatImportPrompt =
  "我想 9 月从上海出发去日本 5-6 天，两个人，预算 8000-10000，想要温泉、美食、自然风景，不想每天太赶。";

const promptPresets = [
  "8月10日-8月13日去杭州，2个人，预算3000以内，想吃吃喝喝和citywalk，节奏不要太赶。",
  "想去海边但别太商业化，3天，从上海出发，预算不太限制，想拍照出片也想吃当地小店。",
  "亲子3人去东京5天，住交通方便的地方，不想每天换酒店，安排一天周边游。",
];

const sampleItinerary = [
  {
    id: "day-1",
    label: "Day 1",
    date: "抵达日",
    title: "落地与轻量探索",
    nodes: [
      {
        id: "n1",
        type: "transport",
        time: "13:10",
        title: "抵达目的地",
        location: "机场 / 车站",
        duration: "45 分钟",
        detail: "先把抵达、入住和晚餐排稳，避免第一天节奏太赶。",
        tags: ["抵达", "交通"],
        booked: false,
        x: 28,
        y: 72,
      },
      {
        id: "n2",
        type: "hotel",
        time: "15:00",
        title: "入住交通方便区域酒店",
        location: "核心交通圈",
        duration: "30 分钟",
        detail: "这是当天的入住节点；后续每天会默认从这个酒店出发、再回到这个酒店。",
        tags: ["入住", "酒店"],
        booked: false,
        x: 42,
        y: 48,
      },
      {
        id: "n3",
        type: "meal",
        time: "18:30",
        title: "当地代表性晚餐",
        location: "住处附近",
        duration: "90 分钟",
        detail: "第一晚安排低负担餐厅，结合用户偏好避开过度网红化选择。",
        tags: ["晚餐", "低负担"],
        booked: false,
        x: 54,
        y: 42,
      },
      {
        id: "n10",
        type: "hotel",
        time: "20:30",
        title: "回到酒店休息",
        location: "核心交通圈",
        duration: "过夜",
        detail: "当天时间线收束到酒店，方便第二天从同一地点出发。",
        tags: ["hotel-return", "休息"],
        booked: false,
        x: 42,
        y: 48,
      },
    ],
  },
  {
    id: "day-2",
    label: "Day 2",
    date: "核心游玩日",
    title: "城市主线与偏好体验",
    nodes: [
      {
        id: "n11",
        type: "hotel",
        time: "09:00",
        title: "从酒店出发",
        location: "核心交通圈",
        duration: "15 分钟",
        detail: "如果连续入住同一酒店，每天路线默认从酒店开始。",
        tags: ["hotel-start", "出发"],
        booked: false,
        x: 42,
        y: 48,
      },
      {
        id: "n4",
        type: "place",
        time: "10:00",
        title: "经典区域慢游",
        location: "城市核心区",
        duration: "2 小时",
        detail: "把必玩点和步行距离一起考虑，避免为了打卡牺牲体验。",
        tags: ["经典必玩", "步行"],
        booked: false,
        x: 38,
        y: 34,
      },
      {
        id: "n5",
        type: "meal",
        time: "12:30",
        title: "风格匹配午餐",
        location: "游玩区域附近",
        duration: "75 分钟",
        detail: "餐厅会根据预算、人数和自由输入偏好筛选。",
        tags: ["午餐", "吃吃喝喝"],
        booked: false,
        x: 47,
        y: 38,
      },
      {
        id: "n6",
        type: "place",
        time: "15:00",
        title: "兴趣向探索",
        location: "小众街区 / 展览 / 自然点",
        duration: "2.5 小时",
        detail: "这里会吸收旅行风格按钮和其他要求，做成可替换节点。",
        tags: ["兴趣", "可替换"],
        booked: false,
        x: 60,
        y: 52,
      },
      {
        id: "n12",
        type: "hotel",
        time: "20:30",
        title: "回到酒店",
        location: "核心交通圈",
        duration: "过夜",
        detail: "当天结束后默认回到同一酒店；如果换酒店，可以把这里编辑成新入住节点。",
        tags: ["hotel-return", "同一酒店"],
        booked: false,
        x: 42,
        y: 48,
      },
    ],
  },
  {
    id: "day-3",
    label: "Day 3",
    date: "弹性日",
    title: "周边或补充安排",
    nodes: [
      {
        id: "n13",
        type: "hotel",
        time: "08:45",
        title: "酒店退房 / 寄存行李",
        location: "核心交通圈",
        duration: "30 分钟",
        detail: "最后一天先处理退房和行李，再开始当天路线。",
        tags: ["hotel-start", "退房"],
        booked: false,
        x: 42,
        y: 48,
      },
      {
        id: "n7",
        type: "transport",
        time: "09:30",
        title: "周边交通方案",
        location: "目的地周边",
        duration: "1-2 小时",
        detail: "如果用户提到周边游、少走路或带老人，会优先调整交通方式。",
        tags: ["周边游", "交通"],
        booked: false,
        x: 52,
        y: 56,
      },
      {
        id: "n8",
        type: "place",
        time: "12:00",
        title: "周边体验",
        location: "自然 / 古建 / 海边",
        duration: "3 小时",
        detail: "根据当天节奏选择自然、古建或海边体验。",
        tags: ["自然风光", "可替换"],
        booked: false,
        x: 72,
        y: 30,
      },
      {
        id: "n9",
        type: "meal",
        time: "18:00",
        title: "收尾晚餐",
        location: "返程便利区域",
        duration: "90 分钟",
        detail: "最后一晚减少折返，把体验和第二天交通一起考虑。",
        tags: ["晚餐", "收尾"],
        booked: false,
        x: 77,
        y: 38,
      },
      {
        id: "n14",
        type: "transport",
        time: "20:00",
        title: "返程 / 前往下一站",
        location: "车站 / 机场",
        duration: "60 分钟",
        detail: "最后一个节点可以是返程，也可以编辑成回酒店继续住。",
        tags: ["返程", "交通"],
        booked: false,
        x: 32,
        y: 70,
      },
    ],
  },
];

const replacementPools = {
  place: [
    { title: "附近美术馆", meta: "室内 · 适合雨天 · 约 90 分钟", reason: "适合替代户外节点，移动成本低。" },
    { title: "本地市场散步", meta: "美食 · 上午更好 · 约 75 分钟", reason: "更贴合吃喝和 citywalk 偏好。" },
    { title: "历史街区慢游", meta: "文化 · 低强度 · 约 2 小时", reason: "适合想看古建但不想太赶的行程。" },
  ],
  meal: [
    { title: "本地家庭料理", meta: "需预约 · 约 ¥250/人", reason: "比网红店更稳定，适合轻松晚餐。" },
    { title: "市场小吃组合", meta: "随性 · 约 ¥120/人", reason: "适合吃吃喝喝，但排队和天气要留意。" },
    { title: "交通便利居酒屋", meta: "室内 · 约 ¥220/人", reason: "适合落地后不想折腾的晚上。" },
  ],
  transport: [
    { title: "公共交通优先", meta: "稳定 · 成本低 · 换乘较多", reason: "预算友好，适合轻装旅行。" },
    { title: "打车分段", meta: "省体力 · 价格中高 · 灵活", reason: "适合带老人、亲子或少走路需求。" },
    { title: "包车半日", meta: "舒适 · 价格高 · 覆盖周边", reason: "适合一天周边游或景点分散的路线。" },
  ],
  hotel: [
    { title: "车站步行 5 分钟酒店", meta: "交通优先 · 可取消 · 中档", reason: "对每天出发和返程都更友好。" },
    { title: "主商圈设计酒店", meta: "餐厅多 · 夜间方便 · 中高档", reason: "更适合购物、美食和 citywalk。" },
    { title: "安静型公寓酒店", meta: "空间大 · 亲子友好 · 中档", reason: "适合多人、亲子或停留时间较长的安排。" },
  ],
};

const state = loadState();
const app = document.querySelector("#app");

function loadState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      const parsed = JSON.parse(saved);
      if (parsed.version !== STATE_VERSION) {
        localStorage.removeItem(STORAGE_KEY);
        return createInitialState();
      }
      return {
        ...parsed,
        version: STATE_VERSION,
        screen: parsed.screen || "studio",
        chatImportPrompt: parsed.chatImportPrompt || defaultChatImportPrompt,
        chatMessages: parsed.chatMessages || [
          {
            role: "agent",
            text: "把你的旅行想法直接丢给我：去哪、多久、预算、人数、偏好、不想要什么都可以混在一句话里。",
          },
        ],
        itinerary: parsed.itinerary || structuredClone(sampleItinerary),
      };
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  return createInitialState();
}

function createInitialState() {
  return {
    version: STATE_VERSION,
    screen: "studio",
    chatImportPrompt: defaultChatImportPrompt,
    chatMessages: [
      {
        role: "agent",
        text: "把你的旅行想法直接丢给我：去哪、多久、预算、人数、偏好、不想要什么都可以混在一句话里。",
      },
    ],
    selectedPlanId: "chat-import-demo",
    activeDayId: "day-1",
    activeNodeId: null,
    drawerMode: "ask",
    validationError: "",
    itinerary: structuredClone(sampleItinerary),
  };
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function render() {
  app.className = "app";
  app.innerHTML = state.screen === "studio" ? renderStudio() : renderBoard();
}

function renderStudio() {
  return `
    <main class="chat-import-shell">
      <section class="chat-import-hero" aria-labelledby="chat-import-title">
        <div>
          <div class="brand-row">
            <div class="brand-mark">G</div>
            <div>
              <h1>Gogo Agent</h1>
              <p>Chat-first travel planning</p>
            </div>
          </div>
          <h2 id="chat-import-title">用聊天把旅行想法导入进来。</h2>
        </div>
      </section>

      <section class="chat-import-panel">
        <div class="chat-window">
          ${state.chatMessages.map(renderChatMessage).join("")}
        </div>

        <div class="prompt-presets" aria-label="示例需求">
          ${promptPresets.map((prompt) => `<button class="prompt-chip" data-action="prompt-chip" data-value="${escapeAttr(prompt)}">${escapeHtml(prompt)}</button>`).join("")}
        </div>

        <div class="chat-composer">
          <textarea id="trip-prompt" placeholder="例如：我想8月去杭州3天，两个人，预算3000以内，想吃吃喝喝和citywalk，节奏不要太赶。">${escapeHtml(state.chatImportPrompt)}</textarea>
          <div class="composer-actions">
            <button class="primary-btn" data-action="submit-chat-import">导入并规划</button>
          </div>
        </div>
      </section>

      ${state.validationError ? `<div class="toast">${state.validationError}</div>` : ""}
    </main>
  `;
}

function renderChatMessage(message) {
  return `
    <article class="import-message ${message.role}">
      <span>${message.role === "user" ? "You" : "Agent"}</span>
      <p>${escapeHtml(message.text)}</p>
    </article>
  `;
}

function renderBoard() {
  const activeDay = getActiveDay();
  const activeNode = getActiveNode();
  const plan = buildPlanSummary();

  return `
    <main class="board-shell">
      <section class="timeline-panel">
        <header class="board-header">
          <div class="board-title">
            <button class="ghost-btn" data-action="back-studio">‹ 修改需求</button>
            <h1>${escapeHtml(plan.title)}</h1>
            <p class="muted">${escapeHtml(plan.summary)}</p>
          </div>
          <div class="board-actions">
            <button class="ghost-btn" data-action="ask-overall">问 AI 优化整体路线</button>
            <button class="primary-btn" data-action="confirm-plan">确认当前规划</button>
          </div>
        </header>

        <div class="intake-summary">
          ${renderSummaryItem("目的地", plan.destination)}
          ${renderSummaryItem("时间", plan.time)}
          ${renderSummaryItem("预算", plan.budget || "未限制")}
          ${renderSummaryItem("人数", plan.travelers || "未填写")}
          ${renderSummaryItem("风格", plan.styles || "未选择")}
        </div>

        <nav class="day-tabs" aria-label="Days">
          ${state.itinerary.map((day) => `
            <button class="day-tab ${day.id === state.activeDayId ? "active" : ""}" data-action="set-day" data-day-id="${day.id}">
              ${day.label} · ${day.date}
            </button>
          `).join("")}
        </nav>

        <div class="timeline">
          <div class="panel-title">
            <div>
              <h2>${activeDay.title}</h2>
            </div>
            <button class="primary-btn" data-action="add-node">新增节点</button>
          </div>
          ${activeDay.nodes.map(renderTimeNode).join("")}
        </div>
      </section>

      <section class="map-panel">
        <header class="map-header">
          <div>
            <h2>实时路线图</h2>
            <p class="muted">${activeDay.label} · ${activeDay.title}</p>
          </div>
          <button class="ghost-btn" data-action="open-navigation">打开导航</button>
        </header>
        ${renderMap(activeDay)}
        ${renderContextPanel(activeDay)}
      </section>
    </main>
    ${renderDrawer(activeNode)}
  `;
}

function renderSummaryItem(label, value) {
  return `<div><span>${label}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function renderTimeNode(node) {
  const active = node.id === state.activeNodeId;
  return `
    <article class="time-node">
      <div class="time-label">${node.time}</div>
      <div class="node-card ${node.type} ${active ? "active" : ""}" data-action="open-node" data-node-id="${node.id}">
        <div class="node-top">
          <div>
            <span class="tag">${nodeLabel(node.type)}</span>
            <h3>${escapeHtml(node.title)}</h3>
          </div>
          ${node.booked ? `<span class="pill green">已确认</span>` : `<span class="pill amber">待确认</span>`}
        </div>
        <div class="node-meta">
          <span>${escapeHtml(node.location)}</span>
          <span>${escapeHtml(node.duration)}</span>
          <span>${escapeHtml(node.detail)}</span>
        </div>
        ${renderNodeTags(node.tags)}
        <div class="node-actions">
          <button class="node-action" data-action="edit-node" data-node-id="${node.id}">编辑</button>
          <button class="node-action" data-action="ask-node" data-node-id="${node.id}">问 AI</button>
          <button class="node-action danger" data-action="delete-node" data-node-id="${node.id}">删除</button>
        </div>
      </div>
    </article>
  `;
}

function renderNodeTags(tags = []) {
  if (!tags.length) return "";
  return `<div class="node-tags">${tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")}</div>`;
}

function renderMap(day) {
  const points = day.nodes.map((node) => `${node.x},${node.y}`).join(" ");
  return `
    <div class="map-canvas">
      <svg class="route-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <polyline points="${points}" fill="none" stroke="rgba(36, 90, 126, 0.55)" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="3 2" />
      </svg>
      ${day.nodes.map((node) => `
        <button class="map-pin ${node.type}" style="left:${node.x}%;top:${node.y}%;" data-action="open-node" data-node-id="${node.id}" title="${escapeAttr(node.title)}">
          <span class="pin-dot"></span>
          <span class="map-label">${node.time} ${escapeHtml(node.title)}</span>
        </button>
      `).join("")}
    </div>
  `;
}

function renderContextPanel(day) {
  const transports = day.nodes.filter((node) => node.type === "transport").length;
  const hotels = day.nodes.filter((node) => node.type === "hotel").length;
  const pending = day.nodes.filter((node) => !node.booked).length;
  return `
    <div class="context-panel">
      <h3>当天概览</h3>
      <div class="stat-row"><span class="muted">地点/活动</span><strong>${day.nodes.filter((node) => node.type === "place" || node.type === "meal").length}</strong></div>
      <div class="stat-row"><span class="muted">交通段</span><strong>${transports}</strong></div>
      <div class="stat-row"><span class="muted">酒店</span><strong>${hotels || "无"}</strong></div>
      <div class="stat-row"><span class="muted">待确认</span><strong>${pending}</strong></div>
    </div>
  `;
}

function renderDrawer(node) {
  if (!node) return `<aside class="drawer hidden"></aside>`;
  const focus = state.drawerMode === "manual" ? "edit" : "ai";
  return `
    <aside class="drawer">
      <div class="drawer-head">
        <div>
          <span class="tag">${nodeLabel(node.type)}</span>
          <h2>${escapeHtml(node.title)}</h2>
          <p class="muted">${node.time} · ${escapeHtml(node.location)}</p>
        </div>
        <button class="icon-btn" data-action="close-drawer" aria-label="关闭">×</button>
      </div>

      ${renderNodeWorkbench(node, focus)}
    </aside>
  `;
}

function renderNodeWorkbench(node, focus) {
  return `
    <div class="node-workbench ${focus === "edit" ? "focus-edit" : "focus-ai"}">
      <section class="workbench-panel workbench-editor">
        <div class="workbench-title">
          <strong>手动编辑</strong>
        </div>
        ${renderManualEditor(node)}
      </section>

      <section class="workbench-panel workbench-ai">
        <div class="workbench-title">
          <strong>问 AI</strong>
        </div>
        <div class="ai-prompt-grid">
          ${renderAiPromptButtons(node)}
        </div>
        <div class="ai-box">
          <strong>上下文</strong>
          <p class="muted">${nodeInsight(node)}</p>
          <div class="llm-response-space">
            <article class="llm-message ai">
              <span>AI</span>
              <p>${nodeInsight(node)}</p>
              ${renderAiSuggestionCard(node)}
            </article>
          </div>
          <textarea id="ai-question" placeholder="例如：这里能不能换成少走路版本？如果下雨怎么办？"></textarea>
          <div class="prompt-actions">
            <button class="primary-btn" data-action="mock-answer">询问</button>
          </div>
        </div>
      </section>
    </div>
  `;
}

function renderAiPromptButtons(node) {
  const prompts = [
    "找 3 个替代",
    "换成少走路版本",
    "如果下雨怎么办",
    "这段安排会不会太赶",
    node.type === "transport" ? "比较交通方式" : "补一段交通建议",
    node.type === "hotel" ? "检查酒店位置是否合适" : "附近有什么顺路体验",
  ];
  return prompts.map((prompt) => `<button class="small-btn" data-action="ai-prompt" data-prompt="${escapeAttr(prompt)}">${escapeHtml(prompt)}</button>`).join("");
}

function renderAiSuggestionCard(node) {
  const options = replacementPools[node.type] || replacementPools.place;
  const suggestion = options[0];
  return `
    <article class="ai-suggestion-card">
      <span class="tag">AI 建议</span>
      <h3>${escapeHtml(suggestion.title)}</h3>
      <p class="muted">${escapeHtml(suggestion.meta)}</p>
      <p>${escapeHtml(suggestion.reason)}</p>
      <div class="prompt-actions">
        <button class="ghost-btn" data-action="shuffle-options">换一条建议</button>
        <button class="primary-btn" data-action="apply-ai-suggestion">应用到节点</button>
      </div>
    </article>
  `;
}

function renderManualEditor(node) {
  return `
    <div class="field-grid">
      <label>时间<input id="edit-time" value="${escapeAttr(node.time)}" /></label>
      <label>类型
        <select id="edit-type">
          ${["place", "meal", "transport", "hotel"].map((type) => `<option value="${type}" ${node.type === type ? "selected" : ""}>${nodeLabel(type)}</option>`).join("")}
        </select>
      </label>
      <label>标题<input id="edit-title" value="${escapeAttr(node.title)}" /></label>
      <label>地点<input id="edit-location" value="${escapeAttr(node.location)}" /></label>
      <label>时长<input id="edit-duration" value="${escapeAttr(node.duration)}" /></label>
      <label>Tags<input id="edit-tags" value="${escapeAttr((node.tags || []).join("、"))}" placeholder="酒店、出发、citywalk" /></label>
    </div>
    <div class="ai-box" style="margin-top: 12px;">
      <strong>备注</strong>
      <textarea id="edit-detail">${escapeHtml(node.detail)}</textarea>
    </div>
    <div class="prompt-actions editor-actions">
      <button class="ghost-btn" data-action="toggle-booked">${node.booked ? "取消确认" : "标记已确认"}</button>
      <button class="danger-btn" data-action="delete-node" data-node-id="${node.id}">删除节点</button>
      <button class="primary-btn" data-action="save-node">保存编辑</button>
    </div>
  `;
}

function submitChatImport() {
  const prompt = document.querySelector("#trip-prompt")?.value.trim() || "";
  state.chatImportPrompt = prompt;
  state.validationError = "";

  if (!prompt) {
    state.validationError = "先告诉我一点旅行想法，比如想去哪、多久、预算或偏好。";
    saveState();
    render();
    return;
  }

  state.chatMessages = [
    ...state.chatMessages,
    { role: "user", text: prompt },
    { role: "agent", text: "收到，已导入为一个可编辑 Trip Board。" },
  ];
  state.selectedPlanId = "chat-import-demo";
  state.screen = "board";
  state.activeDayId = "day-1";
  state.activeNodeId = "n1";
  state.drawerMode = "ask";
  applyChatPromptToItinerary(prompt);
  saveState();
  render();
}

function applyChatPromptToItinerary(prompt) {
  const destination = inferDestination(prompt);
  const origin = inferOrigin(prompt);
  const dayCount = inferDayCount(prompt);
  state.itinerary = structuredClone(sampleItinerary);
  state.itinerary.forEach((day, index) => {
    day.date = index === 0 ? "第 1 天" : `第 ${index + 1} 天`;
  });
  state.itinerary[0].nodes[0].title = `${origin}前往${destination}`;
  state.itinerary[0].nodes[0].location = `${origin} → ${destination}`;
  state.itinerary[0].nodes[1].title = `入住${destination}交通便利区域酒店`;
  state.itinerary
    .flatMap((day) => day.nodes)
    .filter((node) => node.type === "hotel")
    .forEach((node) => {
      node.location = `${destination}核心交通圈`;
    });
  state.itinerary[1].title = `${destination}核心体验`;
  state.itinerary[2].title = dayCount > 3 ? `${destination}周边弹性日` : `${destination}轻松收尾`;
}

function buildPlanSummary() {
  const prompt = state.chatImportPrompt || defaultChatImportPrompt;
  const destination = inferDestination(prompt);
  const time = inferTime(prompt);
  return {
    title: `${destination}旅行 Trip Board`,
    destination,
    time,
    budget: inferBudget(prompt),
    travelers: inferTravelers(prompt),
    styles: inferStyles(prompt),
    summary: prompt,
  };
}

function inferDestination(prompt) {
  const known = ["杭州", "福冈", "东京", "大阪", "首尔", "上海", "北京", "广州", "日本", "海边"];
  return known.find((item) => prompt.includes(item)) || "目的地";
}

function inferOrigin(prompt) {
  const match = prompt.match(/从([^，,。.\s]{2,8})出发/);
  return match?.[1] || "出发地";
}

function inferDayCount(prompt) {
  const match = prompt.match(/(\d+)\s*[-到至]?\s*(\d+)?\s*天/);
  if (match) return Number(match[2] || match[1]);
  const rangeMatch = prompt.match(/\d+月\d+日[-到至]\d+月?\d+日/);
  if (rangeMatch) return 4;
  return 3;
}

function inferTime(prompt) {
  const dateRange = prompt.match(/\d+月\d+日[-到至]\d+月?\d+日/)?.[0];
  const days = prompt.match(/\d+\s*[-到至]?\s*\d*\s*天/)?.[0];
  return dateRange || days || "时间待定";
}

function inferBudget(prompt) {
  const explicit = prompt.match(/预算\s*[:：]?\s*([\d万千kK块元以内\-到至不太限制]+)|([\d万千kK]+)\s*[-到至]\s*([\d万千kK]+)|([\d万千kK]+)\s*以内/);
  return explicit?.[0] || "未限制";
}

function inferTravelers(prompt) {
  return prompt.match(/(\d+|一|两|三|四|五)个?人|亲子\d*人?|带老人/)?.[0] || "未填写";
}

function inferStyles(prompt) {
  const styles = ["经典必玩", "吃吃喝喝", "小众探索", "拍照出片", "逛街购物", "citywalk", "自然风光", "文艺展览", "历史古建", "温泉", "美食", "海边", "周边游"].filter((style) =>
    prompt.toLowerCase().includes(style.toLowerCase()),
  );
  return styles.join("、") || "由 AI 从聊天中判断";
}

function getActiveDay() {
  return state.itinerary.find((day) => day.id === state.activeDayId) || state.itinerary[0];
}

function getActiveNode() {
  for (const day of state.itinerary) {
    const node = day.nodes.find((item) => item.id === state.activeNodeId);
    if (node) return node;
  }
  return null;
}

function nodeLabel(type) {
  return {
    place: "地点",
    meal: "餐饮",
    transport: "交通",
    hotel: "酒店",
  }[type] || "节点";
}

function nodeInsight(node) {
  if (node.type === "transport") return "这个节点的关键是交通方式、换乘压力、时间弹性和价格。";
  if (node.type === "hotel") return "酒店会影响每天出发和返回路线，应该跟预算、人数和交通便利度一起判断。";
  if (node.type === "meal") return "餐饮节点适合结合前后地点距离判断，避免为了吃饭打断路线。";
  return "这个地点适合从体验内容、停留时间、替代点位和天气风险几个维度编辑。";
}

function setDay(dayId) {
  state.activeDayId = dayId;
  const day = getActiveDay();
  state.activeNodeId = day.nodes[0]?.id || null;
  state.drawerMode = "ask";
  saveState();
  render();
}

function openNode(nodeId, mode = "ask") {
  state.activeNodeId = nodeId;
  state.drawerMode = mode;
  saveState();
  render();
}

function applyReplacement(index) {
  const node = getActiveNode();
  if (!node) return;
  const pool = state.drawerMode === "transport" ? replacementPools.transport : replacementPools[node.type] || replacementPools.place;
  const replacement = pool[Number(index)];
  if (!replacement) return;

  node.title = replacement.title;
  node.detail = replacement.reason;
  node.duration = replacement.meta.split("·")[2]?.trim() || node.duration;
  node.booked = false;
  saveState();
  render();
}

function applyAiSuggestion() {
  const node = getActiveNode();
  if (!node) return;
  const pool = replacementPools[node.type] || replacementPools.place;
  const suggestion = pool[0];
  if (!suggestion) return;

  node.title = suggestion.title;
  node.detail = suggestion.reason;
  node.duration = suggestion.meta.split("·").at(-1)?.trim() || node.duration;
  node.tags = [...new Set([...(node.tags || []), "AI建议"])];
  state.drawerMode = "manual";
  saveState();
  render();
}

function saveNodeEdits() {
  const node = getActiveNode();
  if (!node) return;
  node.time = document.querySelector("#edit-time")?.value.trim() || node.time;
  node.type = document.querySelector("#edit-type")?.value || node.type;
  node.title = document.querySelector("#edit-title")?.value.trim() || node.title;
  node.location = document.querySelector("#edit-location")?.value.trim() || node.location;
  node.duration = document.querySelector("#edit-duration")?.value.trim() || node.duration;
  node.detail = document.querySelector("#edit-detail")?.value.trim() || node.detail;
  node.tags = parseTags(document.querySelector("#edit-tags")?.value || "");
  sortActiveDayNodes();
  saveState();
  render();
}

function addNode() {
  const day = getActiveDay();
  const id = `n${Date.now()}`;
  const node = {
    id,
    type: "place",
    time: suggestNextTime(day),
    title: "新节点",
    location: "待定地点",
    duration: "60 分钟",
    detail: "待补充地点、时间、备注和 tags。",
    tags: ["新建"],
    booked: false,
    x: 50,
    y: 50,
  };
  day.nodes.push(node);
  state.activeNodeId = id;
  state.drawerMode = "manual";
  sortActiveDayNodes();
  saveState();
  render();
}

function deleteNode(nodeId) {
  const day = getActiveDay();
  const id = nodeId || state.activeNodeId;
  day.nodes = day.nodes.filter((node) => node.id !== id);
  state.activeNodeId = day.nodes[0]?.id || null;
  state.drawerMode = "ask";
  saveState();
  render();
}

function parseTags(value) {
  return value
    .split(/[，,、\s]+/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function sortActiveDayNodes() {
  const day = getActiveDay();
  day.nodes.sort((a, b) => a.time.localeCompare(b.time, "zh-CN", { numeric: true }));
}

function suggestNextTime(day) {
  const last = [...day.nodes].sort((a, b) => a.time.localeCompare(b.time, "zh-CN", { numeric: true })).at(-1);
  if (!last?.time.match(/^\d{1,2}:\d{2}$/)) return "10:00";
  const [hour, minute] = last.time.split(":").map(Number);
  return `${String(Math.min(hour + 1, 23)).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", "&#039;");
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  event.stopPropagation();
  const action = target.dataset.action;

  if (action === "prompt-chip") {
    state.chatImportPrompt = target.dataset.value;
    saveState();
    render();
  }

  if (action === "submit-chat-import") submitChatImport();

  if (action === "manual-planning") {
    state.validationError = "手动规划入口暂不展开；这里先保留为后续创建空白 Trip Board。";
    saveState();
    render();
  }

  if (action === "back-studio") {
    state.screen = "studio";
    saveState();
    render();
  }

  if (action === "set-day") setDay(target.dataset.dayId);
  if (action === "add-node") addNode();
  if (action === "delete-node") deleteNode(target.dataset.nodeId);
  if (action === "open-node") openNode(target.dataset.nodeId, "ask");
  if (action === "edit-node") openNode(target.dataset.nodeId, "manual");
  if (action === "ask-node") openNode(target.dataset.nodeId, "ask");

  if (action === "close-drawer") {
    state.activeNodeId = null;
    saveState();
    render();
  }

  if (action === "ai-prompt") {
    const input = document.querySelector("#ai-question");
    if (input) input.value = target.dataset.prompt;
  }

  if (action === "apply-ai-suggestion") applyAiSuggestion();
  if (action === "save-node") saveNodeEdits();

  if (action === "toggle-booked") {
    const node = getActiveNode();
    if (node) {
      node.booked = !node.booked;
      saveState();
      render();
    }
  }

  if (action === "mock-answer") {
    const box = document.querySelector(".ai-box");
    if (box && !box.querySelector(".mock-answer")) {
      box.insertAdjacentHTML(
        "beforeend",
        `<p class="mock-answer"><strong>模拟回答：</strong>这里会结合自由输入、地点数据和前后节点，判断是否需要追问或直接给替代方案。</p>`,
      );
    }
  }

  if (action === "shuffle-options") {
    const node = getActiveNode();
    if (node) {
      const pool = replacementPools[node.type] || replacementPools.place;
      pool.push(pool.shift());
      saveState();
      render();
    }
  }

  if (action === "ask-overall") {
    state.activeNodeId = getActiveDay().nodes[0]?.id || null;
    state.drawerMode = "ask";
    saveState();
    render();
  }

  if (action === "confirm-plan") {
    state.itinerary.forEach((day) => day.nodes.forEach((node) => (node.booked = node.booked || node.type === "place" || node.type === "meal")));
    saveState();
    render();
  }
});

document.addEventListener("input", (event) => {
  if (event.target.id === "trip-prompt") {
    state.chatImportPrompt = event.target.value;
    saveState();
  }
});

render();

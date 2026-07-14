const STORAGE_KEY = "gogo-agent-flow-mvp";
const browserConfig = window.__GOGO_ENV__ || {};
const runtimeConfig = {
  openAIApiKey: browserConfig.openAIApiKey || "",
  openAIBaseUrl: browserConfig.openAIBaseUrl || "https://api.openai.com/v1",
  openAIModel: browserConfig.openAIModel || "gpt-4.1-mini",
};

window.__GOGO_ENV__ = runtimeConfig;

const defaultPrompt =
  "我想 9 月从上海出发去日本 5-6 天，两个人，预算 8000-10000，想要温泉、美食、自然风景，不想每天太赶。";

const plans = [
  {
    id: "relaxed-onsen",
    title: "福冈 + 由布院轻松温泉线",
    style: "轻松",
    summary: "城市美食和温泉小镇组合，移动少，适合第一次验证 Trip Board 编辑体验。",
    days: "6 天",
    budget: "约 ¥8,600",
    pace: "低到中",
    highlights: ["博多美食", "由布院温泉", "金鳞湖散步"],
  },
  {
    id: "food-city",
    title: "福冈城市美食深挖线",
    style: "美食",
    summary: "减少跨城移动，把餐厅、咖啡、市场和城市散步排得更细。",
    days: "5 天",
    budget: "约 ¥7,800",
    pace: "低",
    highlights: ["天神夜生活", "柳桥市场", "海边半日"],
  },
  {
    id: "nature-kyushu",
    title: "北九州自然风景线",
    style: "自然",
    summary: "增加门司港和别府，风景更丰富，但交通规划要求更高。",
    days: "6 天",
    budget: "约 ¥9,700",
    pace: "中",
    highlights: ["门司港", "别府地狱", "由布院"],
  },
];

const itinerary = [
  {
    id: "day-1",
    label: "Day 1",
    date: "9月10日",
    title: "抵达福冈",
    nodes: [
      {
        id: "n1",
        type: "transport",
        time: "13:10",
        title: "抵达福冈机场",
        location: "FUK",
        duration: "45 分钟",
        detail: "入境后乘地铁前往博多站，先不要安排重景点。",
        booked: false,
        x: 28,
        y: 72,
      },
      {
        id: "n2",
        type: "hotel",
        time: "15:00",
        title: "Hotel Vista Hakata 入住",
        location: "博多站",
        duration: "3 晚",
        detail: "作为福冈段基地，步行到车站约 6 分钟。",
        booked: false,
        x: 42,
        y: 48,
      },
      {
        id: "n3",
        type: "meal",
        time: "18:30",
        title: "天神拉面晚餐",
        location: "天神",
        duration: "90 分钟",
        detail: "落地第一晚保持轻松，餐后可短距离散步。",
        booked: false,
        x: 54,
        y: 42,
      },
    ],
  },
  {
    id: "day-2",
    label: "Day 2",
    date: "9月11日",
    title: "福冈城市轻探索",
    nodes: [
      {
        id: "n4",
        type: "place",
        time: "10:00",
        title: "大濠公园",
        location: "中央区",
        duration: "90 分钟",
        detail: "轻松散步，适合调整节奏；雨天可替换为美术馆或咖啡路线。",
        booked: false,
        x: 38,
        y: 34,
      },
      {
        id: "n5",
        type: "transport",
        time: "12:00",
        title: "地铁前往博多老街区",
        location: "大濠公园 → 祇园",
        duration: "18 分钟",
        detail: "可选地铁或打车。打车更省体力，地铁更稳定。",
        booked: false,
        x: 47,
        y: 38,
      },
      {
        id: "n6",
        type: "place",
        time: "14:00",
        title: "博多老街区散步",
        location: "祇园 / 博多",
        duration: "2 小时",
        detail: "和下午茶、伴手礼顺路，适合慢节奏探索。",
        booked: false,
        x: 49,
        y: 50,
      },
    ],
  },
  {
    id: "day-3",
    label: "Day 3",
    date: "9月12日",
    title: "由布院温泉日",
    nodes: [
      {
        id: "n7",
        type: "transport",
        time: "09:24",
        title: "由布院之森列车",
        location: "博多 → 由布院",
        duration: "2 小时 12 分",
        detail: "需要确认车次和指定席。若票紧张，可改普通 JR 或巴士。",
        booked: false,
        x: 52,
        y: 56,
      },
      {
        id: "n8",
        type: "place",
        time: "13:30",
        title: "金鳞湖 + Floral Village",
        location: "由布院",
        duration: "3 小时",
        detail: "两个点位距离近，适合放在同一天下午。",
        booked: false,
        x: 72,
        y: 30,
      },
      {
        id: "n9",
        type: "hotel",
        time: "17:30",
        title: "温泉旅馆入住",
        location: "由布院",
        duration: "1 晚",
        detail: "晚餐和温泉是当天重点，建议不要再加远距离活动。",
        booked: false,
        x: 77,
        y: 38,
      },
    ],
  },
];

const replacementPools = {
  place: [
    {
      title: "福冈市美术馆",
      meta: "室内 · 适合雨天 · 约 90 分钟",
      reason: "替代大濠公园时路线损耗最低，仍在同一区域。",
    },
    {
      title: "柳桥连合市场",
      meta: "美食 · 上午更好 · 约 75 分钟",
      reason: "更贴合美食偏好，可以和午餐自然衔接。",
    },
    {
      title: "栉田神社 + 川端商店街",
      meta: "文化散步 · 低强度 · 约 2 小时",
      reason: "不重复已有点位，适合替换博多老街区的一部分。",
    },
  ],
  meal: [
    {
      title: "博多水炊き晚餐",
      meta: "预约优先 · 约 ¥350/人",
      reason: "比拉面更有仪式感，适合旅行第一晚升级体验。",
    },
    {
      title: "天神屋台轻食",
      meta: "随性 · 排队风险 · 约 ¥180/人",
      reason: "更有当地感，但天气和排队不确定。",
    },
    {
      title: "海鲜居酒屋",
      meta: "室内 · 适合聊天 · 约 ¥280/人",
      reason: "稳定、省心，适合落地后不想折腾。",
    },
  ],
  transport: [
    {
      title: "JR 特急指定席",
      meta: "稳定 · 需提前订票 · ¥5,000 左右",
      reason: "最适合确定性强的行程，能减少当天决策压力。",
    },
    {
      title: "高速巴士",
      meta: "更便宜 · 约 2.5 小时 · 座位舒适",
      reason: "预算更友好，但受路况影响更大。",
    },
    {
      title: "包车/打车分段",
      meta: "省体力 · 价格高 · 灵活",
      reason: "适合带行李或同行人不想换乘的情况。",
    },
  ],
  hotel: [
    {
      title: "博多站步行 5 分钟酒店",
      meta: "交通优先 · 可取消 · 约 ¥760/晚",
      reason: "对第一天和去由布院的交通都最友好。",
    },
    {
      title: "天神设计型酒店",
      meta: "餐厅多 · 夜间方便 · 约 ¥690/晚",
      reason: "更适合美食线，但去车站略麻烦。",
    },
    {
      title: "由布院含晚餐温泉旅馆",
      meta: "体验优先 · 需预订 · 约 ¥1,600/晚",
      reason: "如果把温泉作为核心体验，这比普通酒店更值得。",
    },
  ],
};

const state = loadState();
const app = document.querySelector("#app");

function loadState() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    }
  }

  return {
    screen: "studio",
    prompt: defaultPrompt,
    generated: false,
    selectedPlanId: null,
    activeDayId: "day-1",
    activeNodeId: null,
    drawerMode: "ask",
    chat: [
      {
        role: "agent",
        text: "告诉我你大概想去哪、几天、预算和不想要什么。信息不完整也没关系，我会先给你 3 个可编辑计划。",
      },
    ],
    itinerary: structuredClone(itinerary),
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
    <main class="studio">
      <section class="chat-hero">
        <div class="brand-row">
          <div class="brand-mark">G</div>
          <div>
            <h1>Gogo Agent</h1>
            <p>New travel plan</p>
          </div>
        </div>
        <h2>从一句模糊想法开始，生成可编辑旅行计划。</h2>
        <p>先对话，不先填表。Agent 会把不完整的信息整理成几个可选计划；选中之后再进入 Trip Board 看时间线、地图、交通和酒店。</p>
        <div class="prompt-panel">
          <textarea id="trip-prompt" aria-label="旅行想法">${escapeHtml(state.prompt)}</textarea>
          <div class="prompt-actions">
            <div class="chips">
              <button class="chip" data-action="preset" data-value="亲子 7 天，少走路，预算 15000">亲子少走路</button>
              <button class="chip" data-action="preset" data-value="冰岛 8 天，自驾，看极光，预算别太夸张">冰岛极光</button>
              <button class="chip" data-action="preset" data-value="首尔 4 天，购物美食，住得方便">首尔周末</button>
            </div>
            <button class="primary-btn" data-action="generate-plans">生成 3 个计划</button>
          </div>
        </div>
      </section>

      <section class="chat-thread">
        ${state.chat.map(renderMessage).join("")}
        ${state.generated ? renderPlanPanel() : ""}
      </section>
    </main>
  `;
}

function renderMessage(message) {
  return `
    <article class="message ${message.role}">
      <span class="message-meta">${message.role === "user" ? "You" : "Agent"}</span>
      <div>${escapeHtml(message.text)}</div>
    </article>
  `;
}

function renderPlanPanel() {
  return `
    <div class="plan-panel">
      <div class="panel-title">
        <div>
          <h2>推荐计划</h2>
          <p class="muted">一次只给 3 个方向。每个都可以进入 Trip Board 后继续编辑。</p>
        </div>
        <button class="ghost-btn" data-action="regenerate-plans">换一批</button>
      </div>
      <div class="plan-grid">
        ${plans.map(renderPlanCard).join("")}
      </div>
    </div>
  `;
}

function renderPlanCard(plan) {
  const selected = state.selectedPlanId === plan.id;
  return `
    <article class="plan-card ${selected ? "selected" : ""}">
      <div class="plan-top">
        <div>
          <span class="tag">${plan.style}</span>
          <h3>${plan.title}</h3>
        </div>
        <button class="primary-btn" data-action="enter-board" data-plan-id="${plan.id}">进入 Trip Board</button>
      </div>
      <p class="muted">${plan.summary}</p>
      <div class="plan-meta">
        <div><span>天数</span><strong>${plan.days}</strong></div>
        <div><span>预算</span><strong>${plan.budget}</strong></div>
        <div><span>节奏</span><strong>${plan.pace}</strong></div>
      </div>
      <div class="chips">
        ${plan.highlights.map((item) => `<span class="chip">${item}</span>`).join("")}
      </div>
    </article>
  `;
}

function renderBoard() {
  const plan = plans.find((item) => item.id === state.selectedPlanId) || plans[0];
  const activeDay = getActiveDay();
  const activeNode = getActiveNode();

  return `
    <main class="board-shell">
      <section class="timeline-panel">
        <header class="board-header">
          <div class="board-title">
            <button class="ghost-btn" data-action="back-studio">← 新对话</button>
            <h1>${plan.title}</h1>
            <p class="muted">${plan.summary}</p>
          </div>
          <div class="board-actions">
            <button class="ghost-btn" data-action="ask-overall">问 AI 优化整体路线</button>
            <button class="primary-btn" data-action="confirm-plan">确认当前计划</button>
          </div>
        </header>

        <nav class="day-tabs" aria-label="Days">
          ${state.itinerary
            .map(
              (day) => `
            <button class="day-tab ${day.id === state.activeDayId ? "active" : ""}" data-action="set-day" data-day-id="${day.id}">
              ${day.label} · ${day.date}
            </button>
          `,
            )
            .join("")}
        </nav>

        <div class="timeline">
          <div class="panel-title">
            <div>
              <h2>${activeDay.title}</h2>
              <p class="muted">点击任意节点进行编辑，地图会同步高亮。</p>
            </div>
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

function renderTimeNode(node) {
  const active = node.id === state.activeNodeId;
  return `
    <article class="time-node">
      <div class="time-label">${node.time}</div>
      <div class="node-card ${node.type} ${active ? "active" : ""}" data-action="open-node" data-node-id="${node.id}">
        <div class="node-top">
          <div>
            <span class="tag">${nodeLabel(node.type)}</span>
            <h3>${node.title}</h3>
          </div>
          ${node.booked ? `<span class="pill green">已确认</span>` : `<span class="pill amber">待确认</span>`}
        </div>
        <div class="node-meta">
          <span>${node.location}</span>
          <span>${node.duration}</span>
          <span>${node.detail}</span>
        </div>
        <div class="node-actions">
          <button class="node-action" data-action="edit-node" data-node-id="${node.id}">编辑</button>
          <button class="node-action" data-action="ask-node" data-node-id="${node.id}">问 AI</button>
          ${node.type === "transport" ? `<button class="node-action" data-action="transport-node" data-node-id="${node.id}">比较交通</button>` : ""}
          ${node.type === "hotel" ? `<button class="node-action" data-action="booking-node" data-node-id="${node.id}">预订详情</button>` : ""}
        </div>
      </div>
    </article>
  `;
}

function renderMap(day) {
  const points = day.nodes.map((node) => `${node.x},${node.y}`).join(" ");
  return `
    <div class="map-canvas">
      <svg class="route-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <polyline points="${points}" fill="none" stroke="rgba(36, 90, 126, 0.55)" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="3 2" />
      </svg>
      ${day.nodes
        .map(
          (node) => `
        <button class="map-pin ${node.type}" style="left:${node.x}%;top:${node.y}%;" data-action="open-node" data-node-id="${node.id}" title="${node.title}">
          <span class="pin-dot"></span>
          <span class="map-label">${node.time} ${node.title}</span>
        </button>
      `,
        )
        .join("")}
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
  const mode = state.drawerMode;
  return `
    <aside class="drawer">
      <div class="drawer-head">
        <div>
          <span class="tag">${nodeLabel(node.type)}</span>
          <h2>${node.title}</h2>
          <p class="muted">${node.time} · ${node.location}</p>
        </div>
        <button class="icon-btn" data-action="close-drawer" aria-label="关闭">×</button>
      </div>

      <div class="drawer-actions">
        <button class="small-btn" data-action="drawer-mode" data-mode="ask">问这里玩什么</button>
        <button class="small-btn" data-action="drawer-mode" data-mode="replace">找 3 个替代</button>
        <button class="small-btn" data-action="drawer-mode" data-mode="manual">手动编辑</button>
        ${node.type === "transport" ? `<button class="small-btn" data-action="drawer-mode" data-mode="transport">交通选择</button>` : ""}
        ${node.type === "hotel" ? `<button class="small-btn" data-action="drawer-mode" data-mode="booking">预订详情</button>` : ""}
      </div>

      ${renderDrawerBody(node, mode)}
    </aside>
  `;
}

function renderDrawerBody(node, mode) {
  if (mode === "manual") return renderManualEditor(node);
  if (mode === "replace") return renderReplacements(node);
  if (mode === "transport") return renderTransportChoices(node);
  if (mode === "booking") return renderBookingDetails(node);
  return renderAskPanel(node);
}

function renderAskPanel(node) {
  return `
    <div class="ai-box">
      <strong>AI 对这个节点的理解</strong>
      <p class="muted">${nodeInsight(node)}</p>
      <textarea placeholder="例如：这里有什么好玩的？适合待多久？如果下雨怎么办？"></textarea>
      <div class="prompt-actions">
        <span class="field-hint">原型会模拟回答，真实版本接 LLM 和地点数据。</span>
        <button class="primary-btn" data-action="mock-answer">询问</button>
      </div>
    </div>
  `;
}

function renderReplacements(node) {
  const options = replacementPools[node.type] || replacementPools.place;
  return `
    <div class="option-list">
      ${options
        .map(
          (option, index) => `
        <article class="option-card">
          <div class="place-row">
            <div>
              <h3>${option.title}</h3>
              <p class="muted">${option.meta}</p>
            </div>
            <button class="primary-btn" data-action="apply-replacement" data-index="${index}">替换</button>
          </div>
          <p>${option.reason}</p>
        </article>
      `,
        )
        .join("")}
      <button class="ghost-btn" data-action="shuffle-options">换一批 3 个</button>
    </div>
  `;
}

function renderManualEditor(node) {
  return `
    <div class="field-grid">
      <label>时间<input id="edit-time" value="${escapeAttr(node.time)}" /></label>
      <label>标题<input id="edit-title" value="${escapeAttr(node.title)}" /></label>
      <label>地点<input id="edit-location" value="${escapeAttr(node.location)}" /></label>
      <label>时长<input id="edit-duration" value="${escapeAttr(node.duration)}" /></label>
    </div>
    <div class="ai-box" style="margin-top: 12px;">
      <strong>说明</strong>
      <textarea id="edit-detail">${escapeHtml(node.detail)}</textarea>
    </div>
    <div class="prompt-actions">
      <button class="ghost-btn" data-action="toggle-booked">${node.booked ? "取消确认" : "标记已确认"}</button>
      <button class="primary-btn" data-action="save-node">保存编辑</button>
    </div>
  `;
}

function renderTransportChoices(node) {
  const options = replacementPools.transport;
  return `
    <div class="ai-box">
      <strong>先选交通类别，再细选班次/价格</strong>
      <p class="muted">当前节点：${node.title}。真实版本可以接 Google Maps、JR/航班/巴士数据；这里先模拟决策辅助。</p>
    </div>
    <div class="option-list">
      ${options
        .map(
          (option, index) => `
        <article class="transport-card">
          <div class="place-row">
            <div>
              <h3>${option.title}</h3>
              <p class="muted">${option.meta}</p>
            </div>
            <button class="primary-btn" data-action="apply-replacement" data-index="${index}">选择</button>
          </div>
          <p>${option.reason}</p>
        </article>
      `,
        )
        .join("")}
    </div>
  `;
}

function renderBookingDetails(node) {
  return `
    <div class="hotel-card">
      <h3>${node.booked ? "预订详情" : "待预订"}</h3>
      <p class="muted">${node.booked ? "确认号：DEMO-0926 · 入住凭证可在这里快速查阅。" : "确认预订后，这里会显示订单号、入住时间、取消截止日期和原平台跳转。"}</p>
      <div class="drawer-actions">
        <button class="primary-btn" data-action="toggle-booked">${node.booked ? "改为未确认" : "标记已预订"}</button>
        <button class="ghost-btn" data-action="open-navigation">跳转原平台</button>
      </div>
    </div>
  `;
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
  if (node.type === "transport") return "这个节点的关键不是景点介绍，而是确定交通方式、换乘压力、时间弹性和价格。";
  if (node.type === "hotel") return "酒店节点会影响每天出发和回程路线，确认预订后应显示入住凭证、地址和取消政策。";
  if (node.type === "meal") return "餐饮节点适合和前后地点距离一起判断，避免为了吃饭打断路线。";
  return "这个地点适合从体验内容、停留时间、替代点位和天气风险几个维度编辑。";
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

function openNode(nodeId, mode = "ask") {
  state.activeNodeId = nodeId;
  state.drawerMode = mode;
  saveState();
  render();
}

function setDay(dayId) {
  state.activeDayId = dayId;
  const day = getActiveDay();
  state.activeNodeId = day.nodes[0]?.id || null;
  state.drawerMode = "ask";
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

function saveNodeEdits() {
  const node = getActiveNode();
  if (!node) return;
  node.time = document.querySelector("#edit-time")?.value.trim() || node.time;
  node.title = document.querySelector("#edit-title")?.value.trim() || node.title;
  node.location = document.querySelector("#edit-location")?.value.trim() || node.location;
  node.duration = document.querySelector("#edit-duration")?.value.trim() || node.duration;
  node.detail = document.querySelector("#edit-detail")?.value.trim() || node.detail;
  saveState();
  render();
}

document.addEventListener("click", (event) => {
  const target = event.target.closest("[data-action]");
  if (!target) return;
  event.stopPropagation();
  const action = target.dataset.action;

  if (action === "preset") {
    state.prompt = target.dataset.value;
    saveState();
    render();
  }

  if (action === "generate-plans" || action === "regenerate-plans") {
    state.prompt = document.querySelector("#trip-prompt")?.value.trim() || state.prompt;
    state.generated = true;
    state.chat.push({ role: "user", text: state.prompt });
    state.chat.push({
      role: "agent",
      text: "我先给你 3 个方向：一个轻松温泉线、一个城市美食线、一个自然风景线。选一个进入 Trip Board 后，我们再按天和节点细改。",
    });
    saveState();
    render();
  }

  if (action === "enter-board") {
    state.selectedPlanId = target.dataset.planId;
    state.screen = "board";
    state.activeDayId = "day-1";
    state.activeNodeId = "n1";
    state.drawerMode = "ask";
    saveState();
    render();
  }

  if (action === "back-studio") {
    state.screen = "studio";
    saveState();
    render();
  }

  if (action === "set-day") setDay(target.dataset.dayId);
  if (action === "open-node") openNode(target.dataset.nodeId, "ask");
  if (action === "edit-node") openNode(target.dataset.nodeId, "manual");
  if (action === "ask-node") openNode(target.dataset.nodeId, "ask");
  if (action === "transport-node") openNode(target.dataset.nodeId, "transport");
  if (action === "booking-node") openNode(target.dataset.nodeId, "booking");

  if (action === "close-drawer") {
    state.activeNodeId = null;
    saveState();
    render();
  }

  if (action === "drawer-mode") {
    state.drawerMode = target.dataset.mode;
    saveState();
    render();
  }

  if (action === "apply-replacement") applyReplacement(target.dataset.index);

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
        `<p class="mock-answer"><strong>模拟回答：</strong>这里最值得关注的是它和前后节点的距离、是否受天气影响、是否需要预约。你可以直接让我换 3 个替代点，我会排除当前行程里已经出现的内容。</p>`,
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
    state.prompt = event.target.value;
    saveState();
  }
});

render();

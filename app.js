const STORAGE_KEY = "gogo-agent-product-demo-v3";
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
    intakeReady: false,
    selectedPlanId: null,
    activeDayId: "day-1",
    activeNodeId: null,
    drawerMode: "assist",
    assistantCollapsed: true,
    pendingProposal: null,
    draftNotice: "",
    chat: [
      {
        role: "agent",
        text: "先随便说说你想去哪、几天、预算、同行人和偏好。我整理够关键信息后，就可以开始生成 Trip Board。",
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
    <main class="studio-shell">
      <header class="home-nav">
        <div class="brand-row">
          <div class="brand-mark">G</div>
          <div>
            <h1>Gogo Agent</h1>
            <p>AI travel planning workspace</p>
          </div>
        </div>
      </header>

      <section class="intake-panel">
        <p class="eyebrow">Plan from a conversation</p>
        <h2>说出你的旅行想法。</h2>
        <p class="lede">我会提取目的地、时间、预算、同行人和偏好；信息够了，就直接生成可编辑的 Trip Board。</p>
        ${state.intakeReady ? renderTripBrief() : ""}
        ${renderIntakeComposer()}
      </section>
    </main>
  `;
}

function renderTripBrief() {
  const items = [
    ["目的地", "日本 / 九州"],
    ["时间", "9 月 · 5-6 天"],
    ["同行", "2 人"],
    ["预算", "¥8,000-10,000"],
    ["偏好", "温泉、美食、自然，不赶"],
  ];
  return `
    <div class="trip-brief">
      ${items
        .map(
          ([label, value]) => `
        <div class="field-row">
          <span>${label}</span>
          <strong>${state.intakeReady ? value : "待确认"}</strong>
        </div>
      `,
        )
        .join("")}
    </div>
  `;
}

function renderIntakeComposer() {
  return `
    <div class="intake-composer">
      <textarea id="trip-prompt" aria-label="旅行想法">${escapeHtml(state.prompt)}</textarea>
      <div class="prompt-actions">
        <div class="chips">
          <button class="chip" data-action="preset" data-value="亲子 7 天，少走路，预算 15000">亲子少走路</button>
          <button class="chip" data-action="preset" data-value="冰岛 8 天，自驾，看极光，预算别太夸张">冰岛极光</button>
          <button class="chip" data-action="preset" data-value="首尔 4 天，购物美食，住得方便">首尔周末</button>
        </div>
        <div class="composer-actions">
          ${state.intakeReady ? `<button class="primary-btn" data-action="start-plan">Start Plan</button>` : ""}
          <button class="ghost-btn" data-action="send-intake">${state.intakeReady ? "更新信息" : "整理信息"}</button>
        </div>
      </div>
    </div>
  `;
}

function renderPlanPanel() {
  return `
    <div class="plan-panel">
      <div class="panel-title">
        <div>
          <h2>选择一个方向</h2>
          <p class="muted">不用一次选对，进入 Trip Board 后可以继续改。</p>
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
  const decision = planDecision(plan);
  return `
    <article class="plan-card ${selected ? "selected" : ""}">
      <div class="plan-top">
        <div>
          <span class="tag">${plan.style}</span>
          <h3>${plan.title}</h3>
        </div>
        <button class="primary-btn" data-action="enter-board" data-plan-id="${plan.id}">选这个</button>
      </div>
      <p class="choice-line"><strong>最适合：</strong>${decision.bestFor}</p>
      <p class="muted"><strong>注意：</strong>${decision.watch}</p>
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
  const assistantOpen = activeNode && !state.assistantCollapsed;

  return `
    <main class="board-shell ${assistantOpen ? "assistant-open" : "assistant-closed"}">
      <section class="timeline-panel">
        <header class="board-header">
          <div class="board-title">
            <button class="ghost-btn" data-action="back-studio">新对话</button>
            <h1>${plan.title}</h1>
            <p class="muted">${plan.summary}</p>
          </div>
          <div class="board-actions">
            <button class="ghost-btn" data-action="ask-overall">让 AI 看看哪里可优化</button>
            <button class="primary-btn" data-action="confirm-plan">保存为行程草稿</button>
          </div>
        </header>
        ${state.draftNotice ? `<div class="draft-notice">${state.draftNotice}</div>` : ""}

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
              <p class="muted">${daySummary(activeDay)}</p>
            </div>
          </div>
          ${activeDay.nodes.map(renderTimeNode).join("")}
        </div>
      </section>

      <section class="map-panel">
        <header class="map-header">
          <div>
            <h2>路线感</h2>
            <p class="muted">${activeDay.label} · ${activeDay.title} · ${daySummary(activeDay)}</p>
          </div>
          <button class="ghost-btn" data-action="open-navigation">导航</button>
        </header>
        ${renderMap(activeDay)}
      </section>
      ${renderAssistantDrawer(activeNode)}
    </main>
  `;
}

function renderTimeNode(node) {
  const active = node.id === state.activeNodeId;
  return `
    <article class="time-node">
      <div class="time-label">${node.time}</div>
      <div class="node-card ${node.type} ${active ? "active" : ""}" data-action="open-node" data-node-id="${node.id}" role="button" tabindex="0">
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
          <span class="node-action-hint">点击查看</span>
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

function renderAssistantDrawer(node) {
  if (state.assistantCollapsed) {
    return `
      <aside class="assistant-drawer collapsed">
        <button class="assistant-rail" data-action="expand-assistant" aria-label="展开 AI 面板">
          <span>AI</span>
          <strong>${node ? node.title : "选择节点"}</strong>
        </button>
      </aside>
    `;
  }
  if (!node) {
    return `
      <aside class="assistant-drawer expanded empty">
        <div class="assistant-empty">
          <h2>选择一个节点</h2>
          <p class="muted">点击时间线或地图上的任意节点，在这里继续问 AI、手动编辑，或预览修改。</p>
          <button class="ghost-btn" data-action="collapse-assistant">收起</button>
        </div>
      </aside>
    `;
  }
  const mode = state.drawerMode;
  return `
    <aside class="assistant-drawer expanded">
      <div class="assistant-head">
        <div>
          <span class="tag">${nodeLabel(node.type)}</span>
          <h2>${node.title}</h2>
          <p class="muted">${node.time} · ${node.location}</p>
        </div>
        <button class="ghost-btn" data-action="collapse-assistant">收起</button>
      </div>

      <div class="assistant-actions">
        <button class="small-btn ${mode === "assist" ? "active" : ""}" data-action="drawer-mode" data-mode="assist">问问 AI</button>
        <button class="small-btn ${mode === "manual" ? "active" : ""}" data-action="drawer-mode" data-mode="manual">手动编辑</button>
        ${node.type === "hotel" ? `<button class="small-btn ${mode === "booking" ? "active" : ""}" data-action="drawer-mode" data-mode="booking">预订</button>` : ""}
      </div>

      ${renderDrawerBody(node, mode)}
    </aside>
  `;
}

function renderDrawerBody(node, mode) {
  if (mode === "manual") return renderManualEditor(node);
  if (mode === "booking") return renderBookingDetails(node);
  if (state.pendingProposal?.nodeId === node.id) return renderProposalPreview(node);
  return renderAssistPanel(node);
}

function renderAssistPanel(node) {
  const suggestions = intentSuggestions(node);
  return `
    <div class="ai-box">
      <strong>想怎么调整这里？</strong>
      <p class="muted">${nodeInsight(node)}</p>
      <div class="intent-chips">
        ${suggestions.map((item) => `<button class="chip" data-action="intent-chip" data-value="${escapeAttr(item)}">${item}</button>`).join("")}
      </div>
      <textarea id="node-intent" placeholder="比如：这里会不会太赶？换个更安静的？下雨怎么办？"></textarea>
      <div class="prompt-actions">
        <span class="field-hint">AI 会判断是回答、推荐候选，还是生成修改预览。</span>
        <button class="primary-btn" data-action="mock-answer">发送</button>
      </div>
    </div>
  `;
}

function renderProposalPreview(node) {
  const proposal = state.pendingProposal;
  const replacement = proposal.replacement;
  return `
    <div class="proposal-preview">
      <span class="tag">修改预览</span>
      <h3>${proposal.title}</h3>
      <div class="preview-swap">
        <div>
          <span class="muted">当前</span>
          <strong>${node.title}</strong>
          <p>${node.detail}</p>
        </div>
        <div>
          <span class="muted">建议</span>
          <strong>${replacement.title}</strong>
          <p>${replacement.reason}</p>
        </div>
      </div>
      <div class="impact-list">
        ${proposal.impact.map((item) => `<div>${item}</div>`).join("")}
      </div>
      <div class="prompt-actions">
        <button class="ghost-btn" data-action="cancel-proposal">取消</button>
        <button class="primary-btn" data-action="accept-proposal">应用修改</button>
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
      <div class="assistant-actions">
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

function planDecision(plan) {
  return {
    "relaxed-onsen": {
      bestFor: "想要温泉、美食和低压力移动的第一次验证。",
      watch: "由布院住宿和指定席需要提前确认。",
    },
    "food-city": {
      bestFor: "想少换酒店，把预算花在餐厅和城市散步上。",
      watch: "自然风景会少一些，适合把体验做深。",
    },
    "nature-kyushu": {
      bestFor: "想要更丰富风景，能接受每天多一点移动。",
      watch: "交通衔接和行李安排需要更仔细。",
    },
  }[plan.id];
}

function daySummary(day) {
  const transportCount = day.nodes.filter((node) => node.type === "transport").length;
  const hasHotel = day.nodes.some((node) => node.type === "hotel");
  if (day.id === "day-1") return "落地日保持轻松，先确认机场到酒店和晚餐距离就好。";
  if (day.id === "day-2") return "城市散步为主，路线短，适合根据天气临时替换室内点。";
  if (day.id === "day-3") return "温泉日重点在交通和入住时间，别把下午塞得太满。";
  return `${transportCount} 段移动${hasHotel ? "，含住宿安排" : ""}，适合先看节奏再细改。`;
}

function intentSuggestions(node) {
  if (node.type === "transport") return ["会不会太赶", "换个更稳的交通", "省点预算"];
  if (node.type === "hotel") return ["位置合适吗", "换个更方便的区域", "标记已预订"];
  if (node.type === "meal") return ["附近更好吃的", "排队风险", "换个轻松晚餐"];
  return ["下雨怎么办", "换个更安静的", "适合待多久"];
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

function openNode(nodeId, mode = "assist") {
  state.activeNodeId = nodeId;
  state.drawerMode = mode;
  state.assistantCollapsed = false;
  state.pendingProposal = null;
  saveState();
  render();
}

function setDay(dayId) {
  state.activeDayId = dayId;
  state.activeNodeId = null;
  state.drawerMode = "assist";
  state.assistantCollapsed = true;
  state.pendingProposal = null;
  saveState();
  render();
}

function collapseAssistant() {
  state.assistantCollapsed = true;
  saveState();
  render();
}

function expandAssistant() {
  state.assistantCollapsed = false;
  saveState();
  render();
}

function applyReplacement(index) {
  const node = getActiveNode();
  if (!node) return;
  const pool = node.type === "transport" ? replacementPools.transport : replacementPools[node.type] || replacementPools.place;
  const replacement = pool[Number(index)];
  if (!replacement) return;

  state.pendingProposal = {
    nodeId: node.id,
    replacement,
    title: `把「${node.title}」调整为「${replacement.title}」`,
    impact: proposalImpact(node, replacement),
  };
  state.drawerMode = "assist";
  state.assistantCollapsed = false;
  saveState();
  render();
}

function proposalImpact(node, replacement) {
  const impact = ["正式行程不会立刻改变，应用后才会写入当前节点。"];
  if (node.type === "transport") impact.push("可能影响当天到达时间，后续会重新检查相邻节点。");
  if (node.type === "hotel") impact.push("会影响之后每天出发和返回路线。");
  if (replacement.meta.includes("¥")) impact.push(`参考成本：${replacement.meta}`);
  return impact;
}

function acceptProposal() {
  const node = getActiveNode();
  const proposal = state.pendingProposal;
  if (!node || proposal?.nodeId !== node.id) return;
  const replacement = proposal.replacement;
  node.title = replacement.title;
  node.detail = replacement.reason;
  node.duration = replacement.meta.split("·")[2]?.trim() || node.duration;
  node.booked = false;
  state.pendingProposal = null;
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

function fillIntent(value) {
  const input = document.querySelector("#node-intent");
  if (input) input.value = value;
}

function renderMockAnswer() {
  const node = getActiveNode();
  if (!node) return;
  const box = document.querySelector(".ai-box");
  if (!box || box.querySelector(".mock-answer")) return;
  const intent = document.querySelector("#node-intent")?.value.trim() || "";
  const asksForChange = /换|替|改|省|更稳|更方便|更安静|预算/.test(intent);

  if (asksForChange) {
    const pool = node.type === "transport" ? replacementPools.transport : replacementPools[node.type] || replacementPools.place;
    box.insertAdjacentHTML(
      "beforeend",
      `<div class="option-list mock-answer">
        ${pool
          .map(
            (option, index) => `
          <article class="option-card">
            <div class="place-row">
              <div>
                <h3>${option.title}</h3>
                <p class="muted">${option.meta}</p>
              </div>
              <button class="primary-btn" data-action="apply-replacement" data-index="${index}">预览</button>
            </div>
            <p>${option.reason}</p>
          </article>
        `,
          )
          .join("")}
      </div>`,
    );
    return;
  }

  box.insertAdjacentHTML(
    "beforeend",
    `<p class="mock-answer"><strong>模拟回答：</strong>这一步主要看它和前后节点的距离、天气风险、预约必要性和体力消耗。你也可以直接说“换个更轻松的”，我会先给出修改预览，不会立刻改行程。</p>`,
  );
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

  if (action === "send-intake") {
    state.prompt = document.querySelector("#trip-prompt")?.value.trim() || state.prompt;
    state.intakeReady = true;
    state.chat.push({ role: "user", text: state.prompt });
    state.chat.push({
      role: "agent",
      text: "信息够了：目的地、天数、预算、同行人和偏好都能支撑第一版行程。我先生成一个可编辑 Trip Board，进去后我们再按天和节点细改。",
    });
    saveState();
    render();
  }

  if (action === "start-plan") {
    state.selectedPlanId = "relaxed-onsen";
    state.screen = "board";
    state.activeDayId = "day-1";
    state.activeNodeId = null;
    state.drawerMode = "assist";
    state.assistantCollapsed = true;
    state.pendingProposal = null;
    saveState();
    render();
  }

  if (action === "back-studio") {
    state.screen = "studio";
    saveState();
    render();
  }

  if (action === "set-day") setDay(target.dataset.dayId);
  if (action === "open-node") openNode(target.dataset.nodeId, "assist");

  if (action === "collapse-assistant") collapseAssistant();
  if (action === "expand-assistant") expandAssistant();

  if (action === "drawer-mode") {
    state.drawerMode = target.dataset.mode;
    saveState();
    render();
  }

  if (action === "apply-replacement") applyReplacement(target.dataset.index);
  if (action === "accept-proposal") acceptProposal();

  if (action === "cancel-proposal") {
    state.pendingProposal = null;
    saveState();
    render();
  }

  if (action === "intent-chip") fillIntent(target.dataset.value);

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
    renderMockAnswer();
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
    state.drawerMode = "assist";
    state.assistantCollapsed = false;
    saveState();
    render();
  }

  if (action === "confirm-plan") {
    state.itinerary.forEach((day) => day.nodes.forEach((node) => (node.booked = node.booked || node.type === "place" || node.type === "meal")));
    const remaining = state.itinerary.flatMap((day) => day.nodes).filter((node) => !node.booked).length;
    state.draftNotice = `行程草稿已保存。还有 ${remaining} 项酒店或交通需要确认。`;
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

document.addEventListener("keydown", (event) => {
  const target = event.target.closest?.(".node-card[data-action='open-node']");
  if (!target || (event.key !== "Enter" && event.key !== " ")) return;
  event.preventDefault();
  openNode(target.dataset.nodeId, "assist");
});

render();

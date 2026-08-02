import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const root = path.resolve(import.meta.dirname, "..");
const source = fs.readFileSync(path.join(root, "app.js"), "utf8");

function createElement(tagName = "div") {
  return {
    tagName: tagName.toUpperCase(),
    className: "",
    innerHTML: "",
    value: "",
    dataset: {},
    children: [],
    appendChild(child) {
      this.children.push(child);
      return child;
    },
    closest() {
      return null;
    },
    querySelector() {
      return null;
    },
    insertAdjacentHTML(_position, html) {
      this.innerHTML += html;
    },
  };
}

function boot() {
  const app = createElement("div");
  const listeners = {};
  const store = new Map();
  const sandbox = {
    console,
    structuredClone,
    window: { __GOGO_ENV__: {} },
    localStorage: {
      getItem: (key) => store.get(key) ?? null,
      setItem: (key, value) => store.set(key, String(value)),
      removeItem: (key) => store.delete(key),
    },
    document: {
      querySelector(selector) {
        if (selector === "#app") return app;
        return null;
      },
      addEventListener(type, handler) {
        listeners[type] = handler;
      },
    },
  };

  vm.createContext(sandbox);
  vm.runInContext(
    `${source}\n;globalThis.__test = { state, render, getActiveNode, applyReplacement, openNode, collapseAssistant };`,
    sandbox,
    { filename: "app.js" },
  );
  return { app, api: sandbox.__test };
}

function test(name, fn) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

test("entering the board starts with a collapsed assistant rail", () => {
  const { app, api } = boot();
  api.state.selectedPlanId = "relaxed-onsen";
  api.state.screen = "board";
  api.state.activeDayId = "day-1";
  api.state.activeNodeId = null;
  api.render();

  assert.match(app.innerHTML, /assistant-drawer collapsed/);
  assert.match(app.innerHTML, /data-action="expand-assistant"/);
  assert.doesNotMatch(app.innerHTML, /抵达福冈机场<\/h2>/);
});

test("opening a node expands a side drawer without using a floating panel", () => {
  const { app, api } = boot();
  api.state.selectedPlanId = "relaxed-onsen";
  api.state.screen = "board";
  api.state.activeDayId = "day-1";

  api.openNode("n1");

  assert.match(app.innerHTML, /assistant-drawer expanded/);
  assert.match(app.innerHTML, /抵达福冈机场<\/h2>/);
  assert.doesNotMatch(app.innerHTML, /inspector-panel/);
  assert.doesNotMatch(app.innerHTML, /class="drawer/);
});

test("collapsing the assistant keeps the current node context", () => {
  const { app, api } = boot();
  api.state.selectedPlanId = "relaxed-onsen";
  api.state.screen = "board";
  api.state.activeDayId = "day-1";
  api.openNode("n1");

  api.collapseAssistant();
  api.render();

  assert.equal(api.state.activeNodeId, "n1");
  assert.match(app.innerHTML, /assistant-drawer collapsed/);
  assert.match(app.innerHTML, /抵达福冈机场/);
});

test("intake is conversational and starts a plan without showing three plan cards", () => {
  const { app, api } = boot();
  api.state.intakeReady = true;
  api.render();

  assert.match(app.innerHTML, /data-action="send-intake"/);
  assert.match(app.innerHTML, /Start Plan/);
  assert.doesNotMatch(app.innerHTML, /生成 3 个计划/);
  assert.doesNotMatch(app.innerHTML, /推荐计划|选择一个方向/);
});

test("main page uses a single focused premium intake surface", () => {
  const { app, api } = boot();
  api.render();

  assert.match(app.innerHTML, /class="studio-shell"/);
  assert.match(app.innerHTML, /class="intake-panel"/);
  assert.doesNotMatch(app.innerHTML, /class="chat-thread"/);
  assert.doesNotMatch(app.innerHTML, /class="intake-card"/);
  assert.doesNotMatch(app.innerHTML, /class="message /);
});

test("ready intake shows a compact brief in the same surface", () => {
  const { app, api } = boot();
  api.state.intakeReady = true;
  api.render();

  assert.match(app.innerHTML, /class="trip-brief"/);
  assert.match(app.innerHTML, /日本 \/ 九州/);
  assert.match(app.innerHTML, /Start Plan/);
  assert.doesNotMatch(app.innerHTML, /开始前需要知道/);
});

test("timeline nodes expose a single lightweight details action", () => {
  const { app, api } = boot();
  api.state.selectedPlanId = "relaxed-onsen";
  api.state.screen = "board";
  api.state.activeDayId = "day-1";
  api.state.activeNodeId = null;
  api.render();

  assert.match(app.innerHTML, /点击查看/);
  assert.doesNotMatch(app.innerHTML, /data-action="edit-node"/);
  assert.doesNotMatch(app.innerHTML, /data-action="ask-node"/);
  assert.doesNotMatch(app.innerHTML, /data-action="transport-node"/);
  assert.doesNotMatch(app.innerHTML, /data-action="booking-node"/);
});

test("timeline node cards are directly clickable to open the assistant", () => {
  const { app, api } = boot();
  api.state.selectedPlanId = "relaxed-onsen";
  api.state.screen = "board";
  api.state.activeDayId = "day-1";
  api.state.activeNodeId = null;
  api.render();

  assert.match(app.innerHTML, /class="node-card transport "[^>]*data-action="open-node"[^>]*data-node-id="n1"/);
  assert.match(app.innerHTML, /class="node-card transport "[^>]*role="button"/);
  assert.match(app.innerHTML, /class="node-card transport "[^>]*tabindex="0"/);
});

test("map panel does not render the redundant route summary stats card", () => {
  const { app, api } = boot();
  api.state.selectedPlanId = "relaxed-onsen";
  api.state.screen = "board";
  api.state.activeDayId = "day-1";
  api.state.activeNodeId = null;
  api.render();

  assert.match(app.innerHTML, /class="map-canvas"/);
  assert.doesNotMatch(app.innerHTML, /今天顺不顺/);
  assert.doesNotMatch(app.innerHTML, /class="stat-row"/);
});

test("applying an AI suggestion opens a proposal preview instead of mutating the trip immediately", () => {
  const { app, api } = boot();
  api.state.selectedPlanId = "relaxed-onsen";
  api.state.screen = "board";
  api.state.activeDayId = "day-1";
  api.state.activeNodeId = "n1";
  api.state.drawerMode = "suggest";

  const originalTitle = api.getActiveNode().title;
  api.applyReplacement(0);
  api.render();

  assert.equal(api.getActiveNode().title, originalTitle);
  assert.equal(api.state.pendingProposal.replacement.title, "JR 特急指定席");
  assert.match(app.innerHTML, /修改预览/);
  assert.match(app.innerHTML, /应用修改/);
});

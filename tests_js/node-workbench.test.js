const fs = require("node:fs");
const assert = require("node:assert/strict");

const app = fs.readFileSync("app.js", "utf8");
const styles = fs.readFileSync("styles.css", "utf8");

for (const token of [
  "node-workbench",
  "workbench-editor",
  "workbench-ai",
  "ai-suggestion-card",
  "llm-response-space",
  "data-action=\"ask-node\"",
  "data-action=\"edit-node\"",
  "data-action=\"ai-prompt\"",
  "data-action=\"apply-ai-suggestion\"",
  "找 3 个替代",
  "比较交通方式",
]) {
  assert.ok(app.includes(token), `app.js should include ${token}`);
}

for (const removedToken of [
  "data-action=\"transport-node\"",
  "data-action=\"booking-node\"",
  "data-action=\"drawer-mode\"",
]) {
  assert.ok(!app.includes(removedToken), `app.js should remove separate drawer action ${removedToken}`);
}

assert.ok(styles.includes(".node-workbench"), "styles should define the unified node workbench");
assert.ok(styles.includes(".ai-prompt-grid"), "styles should define prompt shortcuts");
assert.ok(styles.includes(".ai-suggestion-card"), "styles should define AI suggestion cards");
assert.ok(styles.includes(".llm-response-space"), "styles should reserve space for LLM answers");

const aiBoxStart = app.indexOf('<div class="ai-box">');
const aiBoxEnd = app.indexOf("</div>", app.indexOf("llm-response-space"));
const suggestionIndex = app.indexOf("${renderAiSuggestionCard(node)}");
assert.ok(suggestionIndex > aiBoxStart && suggestionIndex < aiBoxEnd, "AI suggestion should render inside the AI dialog box");

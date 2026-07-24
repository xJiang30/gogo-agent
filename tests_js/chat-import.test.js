const fs = require("node:fs");
const assert = require("node:assert/strict");

const app = fs.readFileSync("app.js", "utf8");
const styles = fs.readFileSync("styles.css", "utf8");

for (const token of ["chatImportPrompt", "trip-prompt", "submit-chat-import", "prompt-chip"]) {
  assert.ok(app.includes(token), `app.js should include ${token}`);
}

for (const removedToken of ["InitialPlanningForm", "destination-input", "submit-initial-planning", "destination_candidates"]) {
  assert.ok(!app.includes(removedToken), `app.js should not include structured form token ${removedToken}`);
}

assert.ok(app.includes('state.screen = "board"'), "chat import should enter the trip board directly");
assert.ok(styles.includes(".chat-import-shell"), "styles should define the chat import shell");
assert.ok(styles.includes(".chat-composer"), "styles should define the chat composer");
assert.ok(!styles.includes(".planning-layout"), "styles should not keep the structured planning layout");

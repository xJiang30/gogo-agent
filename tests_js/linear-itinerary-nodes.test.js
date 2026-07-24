const fs = require("node:fs");
const assert = require("node:assert/strict");

const app = fs.readFileSync("app.js", "utf8");
const styles = fs.readFileSync("styles.css", "utf8");

for (const token of [
  "tags:",
  "hotel-start",
  "hotel-return",
  "data-action=\"add-node\"",
  "data-action=\"delete-node\"",
  "id=\"edit-tags\"",
  "id=\"edit-type\"",
  "function addNode",
  "function deleteNode",
]) {
  assert.ok(app.includes(token), `app.js should include ${token}`);
}

assert.ok(!app.includes('duration: "3 晚"'), "hotel should not be represented as one multi-night node");
assert.ok(styles.includes(".node-tags"), "styles should render node tags");
assert.ok(styles.includes(".danger-btn"), "styles should include a delete button style");

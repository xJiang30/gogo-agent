const fs = require("node:fs");
const assert = require("node:assert/strict");

const app = fs.readFileSync("app.js", "utf8");
const styles = fs.readFileSync("styles.css", "utf8");

for (const token of ["workbench-panel", "workbench-editor", "workbench-ai"]) {
  assert.ok(app.includes(token), `app.js should include aligned drawer panel token ${token}`);
}

for (const phrase of [
  "不用先填表",
  "真实版本",
  "这个 demo",
  "demo 会",
  "支持模糊表达",
  "点击任意节点",
  "字段随时可改",
  "这些原来的散装操作",
  "这里预留给用户追问",
]) {
  assert.ok(!app.includes(phrase), `visible UI copy should not include explanatory phrase: ${phrase}`);
}

assert.ok(styles.includes(".workbench-panel"), "styles should align both drawer panels with shared styling");

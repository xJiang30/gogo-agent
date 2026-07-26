const assert = require("node:assert/strict");
const runtime = require("../agent-runtime");

const replaceDecision = runtime.decideEscalation({
  intent: "replace_hotel",
  affectedDayIds: ["day-1"],
  affectedNodeIds: ["node-1"],
});

assert.equal(replaceDecision.decision, runtime.EscalationDecision.LIGHTWEIGHT_RESEARCH);
assert.ok(!Object.values(runtime.EscalationDecision).includes("local_proposal"));

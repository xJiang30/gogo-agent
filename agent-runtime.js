(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.GogoAgentRuntime = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const EscalationDecision = Object.freeze({
    DIRECT_ANSWER: "direct_answer",
    LIGHTWEIGHT_RESEARCH: "lightweight_research",
    GRAPH_REPLAN: "graph_replan",
  });

  function decideEscalation(input) {
    const reasons = [];
    const affectedDayIds = input.affectedDayIds || [];
    const affectedNodeIds = input.affectedNodeIds || [];

    if (affectedDayIds.length >= 2) {
      reasons.push("Touches multiple days");
    }

    if (input.requiresStayReorder) {
      reasons.push("Requires stay-anchor reorder");
    }

    if (input.requiresCrossCityRebuild) {
      reasons.push("Requires cross-city mobility rebuild");
    }

    if (input.breaksMultiDayConstraints) {
      reasons.push("Breaks multi-day constraints");
    }

    if (reasons.length > 0 || input.canCloseLocally === false) {
      return {
        decision: EscalationDecision.GRAPH_REPLAN,
        reasons,
        affectedDayIds,
        affectedNodeIds,
      };
    }

    if (input.intent === "replace_hotel" || input.intent === "replace_node" || input.intent === "replace_transport") {
      return {
        decision: EscalationDecision.LIGHTWEIGHT_RESEARCH,
        reasons: ["Single-node replace text is consultative until the user applies or triggers replan"],
        affectedDayIds,
        affectedNodeIds,
      };
    }

    if (input.intent === "research") {
      return {
        decision: EscalationDecision.LIGHTWEIGHT_RESEARCH,
        reasons: ["Needs provider lookup but not replanning"],
        affectedDayIds,
        affectedNodeIds,
      };
    }

    return {
      decision: EscalationDecision.DIRECT_ANSWER,
      reasons: ["Can answer directly without proposal"],
      affectedDayIds,
      affectedNodeIds,
    };
  }

  function createTripProposal(input) {
    return {
      proposalId: input.proposalId,
      tripId: input.tripId,
      baseVersion: input.baseVersion,
      scope: input.scope,
      title: input.title,
      summary: input.summary,
      reasons: input.reasons || [],
      warnings: input.warnings || [],
      operations: input.operations || [],
      impact: input.impact || { affectedDayIds: [], requiresRecalcSegmentIds: [] },
      evidence: input.evidence || [],
      status: input.status || "draft",
    };
  }

  function createProposalService() {
    const proposals = new Map();

    return {
      persistProposal(proposal, context) {
        const currentVersion = context.currentTripVersion;
        const nextStatus = proposal.baseVersion === currentVersion ? "pending" : "conflicted";
        const stored = { ...proposal, status: nextStatus };
        proposals.set(stored.proposalId, stored);
        return stored;
      },

      getProposal(proposalId) {
        return proposals.get(proposalId) || null;
      },

      listProposals() {
        return Array.from(proposals.values());
      },

      updateProposalStatus(proposalId, status) {
        const current = proposals.get(proposalId);
        if (!current) return null;
        const updated = { ...current, status };
        proposals.set(proposalId, updated);
        return updated;
      },
    };
  }

  function executeAcceptedProposal(trip, proposal) {
    if (proposal.status !== "accepted") {
      throw new Error("Only accepted proposals can be executed");
    }

    if (trip.version !== proposal.baseVersion) {
      throw new Error("Trip version mismatch");
    }

    const nextTrip = {
      ...trip,
      version: trip.version + 1,
      days: trip.days.map((day) => ({
        ...day,
        nodes: day.nodes.map((node) => ({ ...node })),
      })),
    };

    for (const operation of proposal.operations) {
      if (operation.type === "ReplaceNode") {
        const day = nextTrip.days.find((item) => item.id === operation.dayId);
        if (!day) continue;
        const index = day.nodes.findIndex((node) => node.id === operation.nodeId);
        if (index === -1) continue;
        day.nodes[index] = {
          ...day.nodes[index],
          ...operation.replacement,
        };
      }

      if (operation.type === "UpdateNode") {
        const day = nextTrip.days.find((item) => item.id === operation.dayId);
        if (!day) continue;
        const node = day.nodes.find((item) => item.id === operation.nodeId);
        if (!node) continue;
        Object.assign(node, operation.patch);
      }
    }

    return {
      trip: nextTrip,
      decisionLog: {
        proposalId: proposal.proposalId,
        tripId: proposal.tripId,
        executedAt: new Date().toISOString(),
        operations: proposal.operations,
      },
    };
  }

  return {
    EscalationDecision,
    decideEscalation,
    createTripProposal,
    createProposalService,
    executeAcceptedProposal,
  };
});

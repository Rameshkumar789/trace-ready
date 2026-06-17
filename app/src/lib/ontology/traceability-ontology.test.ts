import { describe, expect, it } from "vitest";
import { decideEntityScope } from "./entity-scope";
import { decideProductScope } from "./product-scope";
import { cteTypes } from "./cte-types";
import { hasTlc } from "./tlc-types";
import { traceabilityPlanMissingItems } from "./traceability-plan-types";

describe("traceability ontology", () => {
  it("represents all major FSMA 204 CTE categories", () => {
    expect(cteTypes).toEqual([
      "harvest",
      "cooling",
      "initial_packing",
      "first_land_based_receiving",
      "shipping",
      "receiving",
      "transformation"
    ]);
  });

  it("keeps entity and product scope as decision objects", () => {
    expect(
      decideEntityScope({
        businessId: "biz-1",
        companyName: "Pilot Co",
        handlesFtlFoods: true,
        coveredEntityStatus: "not_determined",
        evidenceRefs: [{ sheet: "00_Business_Profile" }]
      }).status
    ).toBe("not_determined");
    expect(decideProductScope({ productId: "p1", productName: "Fresh Basil", isFtlMaybe: true }).status).toBe(
      "covered"
    );
  });

  it("treats TLC and traceability plan concepts as first-class", () => {
    expect(hasTlc("TLC-1")).toBe(true);
    expect(
      traceabilityPlanMissingItems({
        exists: true,
        recordMaintenanceProcedure: "WMS export",
        ftlIdentificationProcedure: "",
        pointOfContact: "QA",
        evidenceRefs: []
      })
    ).toEqual(["ftl_identification_procedure"]);
  });
});

import type { FTLItem, ProductScopeDecision } from "./types";

export function decideProductScope(product: FTLItem): ProductScopeDecision {
  if (product.isFtlMaybe === true) {
    return {
      productId: product.productId,
      status: "covered",
      reason: "Product master marks the item as likely FTL.",
      evidenceRefs: [{ sheet: "01_Product_Master", field: product.productName }]
    };
  }
  if (product.isFtlMaybe === false) {
    return {
      productId: product.productId,
      status: "not_covered",
      reason: "Product master marks the item as not FTL.",
      evidenceRefs: [{ sheet: "01_Product_Master", field: product.productName }]
    };
  }
  return {
    productId: product.productId,
    status: "not_determined",
    reason: "Product master lacks enough FTL category evidence.",
    evidenceRefs: [{ sheet: "01_Product_Master", field: product.productName }]
  };
}

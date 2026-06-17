import type { FTLItem, ProductScopeDecision } from "@/lib/ontology/types";
import { decideProductScope } from "@/lib/ontology/product-scope";

export function mapProductScope(products: FTLItem[]): ProductScopeDecision[] {
  return products.map(decideProductScope);
}

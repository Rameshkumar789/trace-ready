import { PrismaClient } from "@prisma/client";

const globalForPrisma = globalThis as typeof globalThis & {
  traceReadyPrisma?: PrismaClient;
};

export function getPrismaClient(): PrismaClient {
  if (!globalForPrisma.traceReadyPrisma) {
    globalForPrisma.traceReadyPrisma = new PrismaClient();
  }
  return globalForPrisma.traceReadyPrisma;
}

export type BellwetherPrismaClient = ReturnType<typeof getPrismaClient>;

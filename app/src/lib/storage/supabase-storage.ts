import { createClient } from "@supabase/supabase-js";
import { LocalMemoryStorageProvider, type StorageProvider, type StoredObject } from "./storage-provider";

class SupabaseStorageProvider implements StorageProvider {
  private client = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL ?? "", process.env.SUPABASE_SERVICE_ROLE_KEY ?? "");
  private bucket = getPrivateStorageBucket();

  async put(key: string, bytes: Uint8Array, contentType: string): Promise<StoredObject> {
    const { error } = await this.client.storage.from(this.bucket).upload(key, bytes, {
      contentType,
      upsert: true
    });
    if (error) throw new Error(error.message);
    return { bucket: this.bucket, key, contentType, size: bytes.byteLength };
  }

  async get(key: string): Promise<Uint8Array | undefined> {
    const { data, error } = await this.client.storage.from(this.bucket).download(key);
    if (error || !data) return undefined;
    return new Uint8Array(await data.arrayBuffer());
  }
}

export function getStorageProvider(): StorageProvider {
  if (process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return new SupabaseStorageProvider();
  }
  if (isProductionRuntime() && process.env.BELLWETHER_ALLOW_MEMORY_STORAGE !== "true") {
    throw new Error("Non-durable memory storage is disabled in production. Configure Supabase Storage.");
  }
  return new LocalMemoryStorageProvider();
}

export function getRequiredStorageProvider(): StorageProvider {
  if (process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) {
    return new SupabaseStorageProvider();
  }
  throw new Error("Supabase Storage is required for DB-backed uploads.");
}

function getPrivateStorageBucket() {
  return process.env.SUPABASE_PRIVATE_BUCKET ?? process.env.BELLWETHER_STORAGE_BUCKET ?? "bellwether-pilot-private";
}

function isProductionRuntime() {
  return process.env.NODE_ENV === "production" || process.env.VERCEL_ENV === "production" || process.env.BELLWETHER_ENV === "production";
}

export interface StoredObject {
  bucket: string;
  key: string;
  contentType: string;
  size: number;
}

export interface StorageProvider {
  put(key: string, bytes: Uint8Array, contentType: string): Promise<StoredObject>;
  get(key: string): Promise<Uint8Array | undefined>;
}

export class LocalMemoryStorageProvider implements StorageProvider {
  private objects = new Map<string, { bytes: Uint8Array; contentType: string }>();

  async put(key: string, bytes: Uint8Array, contentType: string): Promise<StoredObject> {
    this.objects.set(key, { bytes, contentType });
    return { bucket: "local-memory", key, contentType, size: bytes.byteLength };
  }

  async get(key: string): Promise<Uint8Array | undefined> {
    return this.objects.get(key)?.bytes;
  }
}

import { readFile } from "node:fs/promises";
import path from "node:path";

export async function GET() {
  const templatePath = path.join(process.cwd(), "../data/samples/fsma204-full-audit-sample.xlsx");
  const file = await readFile(templatePath);

  return new Response(new Uint8Array(file), {
    headers: {
      "Content-Disposition": 'attachment; filename="bellwether-upload-template.xlsx"',
      "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Cache-Control": "private, max-age=300"
    }
  });
}

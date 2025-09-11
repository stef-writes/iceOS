import fs from "node:fs/promises";
import path from "node:path";
import openapiTS from "openapi-typescript";

async function main() {
  const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost").replace(/\/$/, "");
  const outPath = path.resolve(process.cwd(), "apps/web/modules/api/types.ts");
  const specUrl = `${apiUrl}/openapi.json`;

  const res = await fetch(specUrl);
  if (!res.ok) {
    throw new Error(`Failed to fetch OpenAPI from ${specUrl}: ${res.status}`);
  }
  const schema = await res.json();
  const dts = await openapiTS(schema, { additionalProperties: false });

  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await fs.writeFile(outPath, dts, "utf8");
  console.log(`[gen-types] Wrote ${outPath} from ${specUrl}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

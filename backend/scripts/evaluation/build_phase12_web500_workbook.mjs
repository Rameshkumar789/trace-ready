import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const DATA_DIR = "../data/regulatory/intelligence/generalization";
const OUTPUT_DIR = "../outputs/phase12-web500-eval";
const OUTPUT_FILE = `${OUTPUT_DIR}/phase12-web500-real-world-eval.xlsx`;

const [summary, records, results, metrics, sources] = await Promise.all([
  readJson(`${DATA_DIR}/phase12-web500-summary.json`),
  readJson(`${DATA_DIR}/phase12-web500-input-records.json`),
  readJson(`${DATA_DIR}/phase12-web500-results.json`),
  readJson(`${DATA_DIR}/phase12-web500-metrics.json`),
  readJson(`${DATA_DIR}/phase12-web500-source-register.json`),
]);

const resultsById = new Map(results.map((row) => [row.record_id, row]));
const workbook = Workbook.create();

const summarySheet = workbook.worksheets.add("Summary");
const dataSheet = workbook.worksheets.add("Eval_Data_500");
const resultSheet = workbook.worksheets.add("Results");
const failuresSheet = workbook.worksheets.add("Failures");
const metricsSheet = workbook.worksheets.add("Metrics");
const sourcesSheet = workbook.worksheets.add("Source_Register");

writeSummary(summarySheet, summary, metrics);
writeEvalData(dataSheet, records);
writeResults(resultSheet, results);
writeFailures(failuresSheet, records, resultsById);
writeMetrics(metricsSheet, metrics);
writeSources(sourcesSheet, sources);

for (const sheet of [summarySheet, dataSheet, resultSheet, failuresSheet, metricsSheet, sourcesSheet]) {
  styleUsedRange(sheet);
}

metricsSheet.charts.add("bar", {
  title: "Pass vs Fail",
  categories: ["Pass", "Fail"],
  series: [{ name: "Records", values: [metrics.pass_count, metrics.fail_count] }],
  hasLegend: false,
  from: { row: 1, col: 5 },
  extent: { widthPx: 420, heightPx: 260 },
});

metricsSheet.charts.add("bar", {
  title: "Precision and Recall",
  categories: ["Precision", "Recall", "Exact Match"],
  series: [{ name: "Rate", values: [metrics.precision, metrics.recall, metrics.exact_match_rate] }],
  hasLegend: false,
  from: { row: 16, col: 5 },
  extent: { widthPx: 420, heightPx: 260 },
});

await verifyWorkbook(workbook);
await fs.mkdir(OUTPUT_DIR, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(OUTPUT_FILE);
console.log(JSON.stringify({ outputFile: OUTPUT_FILE, records: records.length, metrics }, null, 2));

async function readJson(path) {
  return JSON.parse(await fs.readFile(path, "utf8"));
}

function writeSummary(sheet, summary, metrics) {
  const rows = [
    ["TraceReady Phase 12 Web-500 Evaluation Workbook", ""],
    ["Generated At", summary.generatedAt],
    ["Record Count", summary.recordCount],
    ["Source Count", summary.sourceCount],
    ["Exact Match Rate", metrics.exact_match_rate],
    ["Precision", metrics.precision],
    ["Recall", metrics.recall],
    ["False Positive Rate", metrics.false_positive_rate],
    ["False Negative Rate", metrics.false_negative_rate],
    ["Pass Count", metrics.pass_count],
    ["Fail Count", metrics.fail_count],
    ["Scope", "Public internet source-derived eval rows; not real customer transaction exports."],
    ["Live Model Outputs Used", "No"],
    ["Open Food Facts API", "Attempted; HTTP 503. Workbook uses public article descriptions instead of bulk API records."],
    ["Limitation 1", summary.importantLimitations[0]],
    ["Limitation 2", summary.importantLimitations[1]],
    ["Limitation 3", summary.importantLimitations[2]],
    ["Limitation 4", summary.importantLimitations[3]],
  ];
  writeMatrix(sheet, "A1:B18", rows);
  sheet.getRange("A1:B1").format = {
    fill: { type: "solid", color: "#17324D" },
    font: { color: "#FFFFFF", bold: true, size: 14 },
  };
  sheet.getRange("A2:A18").format.font = { bold: true };
}

function writeEvalData(sheet, records) {
  const headers = [
    "record_id",
    "scenario_family",
    "source_name",
    "source_url",
    "source_basis",
    "product",
    "product_category",
    "lot_or_batch",
    "observed_text",
    "expected_ctes",
    "expected_abstentions",
    "gold_label_method",
  ];
  const rows = [headers, ...records.map((record) => headers.map((header) => toCell(record[header])))];
  writeMatrix(sheet, rangeFor(rows), rows);
}

function writeResults(sheet, results) {
  const headers = [
    "record_id",
    "scenario_family",
    "source_name",
    "expected_ctes",
    "predicted_ctes",
    "expected_abstentions",
    "predicted_abstentions",
    "status",
    "errors",
  ];
  const rows = [headers, ...results.map((result) => headers.map((header) => toCell(result[header])))];
  writeMatrix(sheet, rangeFor(rows), rows);
}

function writeFailures(sheet, records, resultsById) {
  const headers = [
    "record_id",
    "source_name",
    "scenario_family",
    "observed_text",
    "expected_ctes",
    "predicted_ctes",
    "expected_abstentions",
    "predicted_abstentions",
    "errors",
  ];
  const failureRows = records
    .map((record) => ({ record, result: resultsById.get(record.record_id) }))
    .filter(({ result }) => result?.status === "fail")
    .map(({ record, result }) => [
      record.record_id,
      record.source_name,
      record.scenario_family,
      record.observed_text,
      toCell(result.expected_ctes),
      toCell(result.predicted_ctes),
      toCell(result.expected_abstentions),
      toCell(result.predicted_abstentions),
      toCell(result.errors),
    ]);
  const rows = [headers, ...failureRows];
  writeMatrix(sheet, rangeFor(rows), rows);
}

function writeMetrics(sheet, metrics) {
  const topRows = [
    ["Metric", "Value"],
    ["Record count", metrics.record_count],
    ["Pass count", metrics.pass_count],
    ["Fail count", metrics.fail_count],
    ["Exact match rate", metrics.exact_match_rate],
    ["Precision", metrics.precision],
    ["Recall", metrics.recall],
    ["False positive rate", metrics.false_positive_rate],
    ["False negative rate", metrics.false_negative_rate],
  ];
  writeMatrix(sheet, rangeFor(topRows), topRows);
  const cteRows = [
    ["CTE", "Precision", "Recall", "False Positives", "False Negatives"],
    ...Object.keys(metrics.precision_by_cte).sort().map((cte) => [
      cte,
      metrics.precision_by_cte[cte],
      metrics.recall_by_cte[cte],
      metrics.false_positive_by_cte[cte],
      metrics.false_negative_by_cte[cte],
    ]),
  ];
  writeMatrix(sheet, `A12:E${11 + cteRows.length}`, cteRows);
  const sourceRows = [
    ["Source", "Count", "Pass", "Fail", "Pass Rate"],
    ...Object.entries(metrics.by_source).map(([source, values]) => [
      source,
      values.count,
      values.pass,
      values.fail,
      values.count ? Math.round((values.pass / values.count) * 10000) / 10000 : 0,
    ]),
  ];
  writeMatrix(sheet, `A24:E${23 + sourceRows.length}`, sourceRows);
  sheet.getRange("B5:B9").format.numberFormat = "0.00%";
  sheet.getRange(`B13:C${11 + cteRows.length}`).format.numberFormat = "0.00%";
  sheet.getRange(`E25:E${23 + sourceRows.length}`).format.numberFormat = "0.00%";
}

function writeSources(sheet, sources) {
  const headers = ["source_key", "source_name", "source_url", "source_basis"];
  const rows = [headers, ...sources.map((source) => headers.map((header) => source[header]))];
  writeMatrix(sheet, rangeFor(rows), rows);
}

function styleUsedRange(sheet) {
  const preview = sheet.getRange("A1:Z1");
  preview.format = {
    fill: { type: "solid", color: "#17324D" },
    font: { color: "#FFFFFF", bold: true },
    wrapText: true,
    verticalAlignment: "center",
  };
  sheet.getRange("A:Z").format.wrapText = true;
  sheet.getRange("A:Z").format.autofitColumns();
}

function writeMatrix(sheet, range, rows) {
  sheet.getRange(range).values = rows;
}

function rangeFor(rows) {
  return `A1:${columnName(rows[0].length)}${rows.length}`;
}

function columnName(index) {
  let name = "";
  let current = index;
  while (current > 0) {
    const remainder = (current - 1) % 26;
    name = String.fromCharCode(65 + remainder) + name;
    current = Math.floor((current - 1) / 26);
  }
  return name;
}

function toCell(value) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (value == null) {
    return "";
  }
  return value;
}

async function verifyWorkbook(workbook) {
  const summaryInspect = await workbook.inspect({
    kind: "table",
    range: "Summary!A1:B18",
    include: "values",
    tableMaxRows: 20,
    tableMaxCols: 4,
  });
  console.log(summaryInspect.ndjson);
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 50 },
    summary: "final formula error scan",
  });
  console.log(errors.ndjson);
  await workbook.render({ sheetName: "Summary", range: "A1:B18", scale: 2 });
  await workbook.render({ sheetName: "Metrics", range: "A1:J34", scale: 2 });
  await workbook.render({ sheetName: "Eval_Data_500", range: "A1:L20", scale: 2 });
  await workbook.render({ sheetName: "Failures", range: "A1:I20", scale: 2 });
  await workbook.render({ sheetName: "Source_Register", range: "A1:D10", scale: 2 });
}

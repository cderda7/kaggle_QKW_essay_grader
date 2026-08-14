/**
 * build_tracker_doc.js — builds tracker_table.docx from tracker_log.json.
 *
 * This is the second half of the tracker agent (see run_tracker.py for the first half). It reads
 * the JSON log and produces a .docx with a single 5-column table — blank/label, QWK, ∆, rationale,
 * concerns — matching the layout of the hand-built "Template GitHub Commit Tracker" Google Doc.
 * Only Claude runs this step (it needs Node + the docx package, which live in the Cowork cloud
 * workspace, not necessarily on your Mac) — it's committed here so the exact table-building logic
 * is visible/auditable, not because you're expected to run it yourself.
 *
 * The concerns column is always left blank — populating it is explicitly your job, never the
 * agent's (see decisions_log.md).
 *
 * Usage: node build_tracker_doc.js <tracker_log.json> <output.docx>
 */

const fs = require("fs");
const {
  Document, Packer, Table, TableRow, TableCell, Paragraph, TextRun,
  WidthType, ShadingType, VerticalAlign, HeadingLevel, AlignmentType, PageOrientation,
} = require("docx");

const [, , logPath, outPath] = process.argv;
if (!logPath || !outPath) {
  console.error("Usage: node build_tracker_doc.js <tracker_log.json> <output.docx>");
  process.exit(1);
}

const entries = JSON.parse(fs.readFileSync(logPath, "utf8"));

// US Letter, DXA units (1440 = 1"). Table width ~9360 DXA (6.5"), 5 columns.
const COLUMN_WIDTHS = [1440, 1560, 2160, 2160, 2040]; // label, QWK, ∆, rationale, concerns
const TABLE_WIDTH = COLUMN_WIDTHS.reduce((a, b) => a + b, 0);

function headerCell(text, width) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, color: "auto", fill: "D9D9D9" },
    verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, bold: true })],
    })],
  });
}

function textCell(lines, width) {
  const paragraphs = (lines && lines.length ? lines : [""]).map(
    (line) => new Paragraph({ children: [new TextRun({ text: String(line) })] })
  );
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    verticalAlign: VerticalAlign.CENTER,
    children: paragraphs,
  });
}

function qwkCellLines(entry) {
  const lines = [];
  lines.push(entry.qwk === null || entry.qwk === undefined ? "—" : entry.qwk.toFixed(3));
  if (entry.qwk_notes && entry.qwk_notes.length) {
    for (const note of entry.qwk_notes) lines.push(note);
  }
  return lines;
}

const headerRow = new TableRow({
  tableHeader: true,
  children: [
    headerCell("", COLUMN_WIDTHS[0]),
    headerCell("QWK", COLUMN_WIDTHS[1]),
    headerCell("∆", COLUMN_WIDTHS[2]),
    headerCell("rationale", COLUMN_WIDTHS[3]),
    headerCell("concerns", COLUMN_WIDTHS[4]),
  ],
});

const dataRows = entries.map((entry) => new TableRow({
  children: [
    textCell([entry.label], COLUMN_WIDTHS[0]),
    textCell(qwkCellLines(entry), COLUMN_WIDTHS[1]),
    textCell([entry.delta || ""], COLUMN_WIDTHS[2]),
    textCell([entry.rationale || ""], COLUMN_WIDTHS[3]),
    textCell([entry.concerns || ""], COLUMN_WIDTHS[4]),
  ],
}));

// Two blank rows at the end, matching the template's layout, for you to fill in by hand if wanted
// before the next regenerate (note: any hand edits to a blank row will be LOST on the next
// recreate-on-run sync, since the doc is fully regenerated from tracker_log.json each time).
const blankRow = () => new TableRow({
  children: COLUMN_WIDTHS.map((w) => textCell([""], w)),
});

const table = new Table({
  width: { size: TABLE_WIDTH, type: WidthType.DXA },
  columnWidths: COLUMN_WIDTHS,
  rows: [headerRow, ...dataRows, blankRow(), blankRow()],
});

const doc = new Document({
  sections: [{
    properties: {
      // Portrait US-Letter dimensions in; docx-js swaps them internally for landscape.
      page: {
        size: { width: 12240, height: 15840 },
        orientation: PageOrientation.LANDSCAPE,
      },
    },
    children: [
      new Paragraph({ heading: HeadingLevel.HEADING_1, text: "Commit Tracker" }),
      new Paragraph({ text: "" }),
      table,
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(outPath, buffer);
  console.log(`Wrote ${outPath} (${entries.length} data rows)`);
});

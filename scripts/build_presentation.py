"""Build the RiskPulse AI hackathon presentation without external packages."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "presentation.pdf"
ARCHITECTURE = ROOT / "docs" / "architecture.png"
WIDTH = 1280
HEIGHT = 720


def rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))  # type: ignore[return-value]


def pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def parse_png(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Unsupported image format: {path}")

    position = 8
    compressed = bytearray()
    width = height = color_type = bit_depth = None
    while position < len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        chunk_type = data[position + 4 : position + 8]
        chunk = data[position + 8 : position + 8 + length]
        position += length + 12
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", chunk[:10])
        elif chunk_type == b"IDAT":
            compressed.extend(chunk)
        elif chunk_type == b"IEND":
            break

    if (width, height, bit_depth, color_type) != (width, height, 8, 2):
        raise ValueError("The architecture image must be an 8-bit RGB PNG")

    raw = zlib.decompress(compressed)
    bytes_per_pixel = 3
    stride = width * bytes_per_pixel
    rows: list[bytes] = []
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        current = bytearray(raw[offset : offset + stride])
        offset += stride
        for index in range(stride):
            left = current[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            above = previous[index]
            upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            if filter_type == 1:
                current[index] = (current[index] + left) & 255
            elif filter_type == 2:
                current[index] = (current[index] + above) & 255
            elif filter_type == 3:
                current[index] = (current[index] + ((left + above) // 2)) & 255
            elif filter_type == 4:
                estimate = left + above - upper_left
                distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
                current[index] = (current[index] + predictor) & 255
            elif filter_type != 0:
                raise ValueError(f"Unsupported PNG filter: {filter_type}")
        rows.append(bytes(current))
        previous = current
    return width, height, b"".join(rows)


class PdfDocument:
    def __init__(self) -> None:
        self.objects: list[bytes] = []
        self.font = self.object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        self.bold_font = self.object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
        self.image_width, self.image_height, image_data = parse_png(ARCHITECTURE)
        self.image = self.object(
            b"<< /Type /XObject /Subtype /Image /Width "
            + str(self.image_width).encode()
            + b" /Height "
            + str(self.image_height).encode()
            + b" /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length "
            + str(len(zlib.compress(image_data, 9))).encode()
            + b" >>\nstream\n"
            + zlib.compress(image_data, 9)
            + b"\nendstream"
        )
        self.pages: list[int] = []

    def object(self, value: bytes) -> int:
        self.objects.append(value)
        return len(self.objects)

    def page(self, content: str, with_image: bool = False) -> None:
        stream = content.encode("latin-1")
        content_id = self.object(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        xobjects = b" /XObject << /Im1 " + str(self.image).encode() + b" 0 R >>" if with_image else b""
        page = (
            b"<< /Type /Page /Parent PARENT 0 R /MediaBox [0 0 "
            + str(WIDTH).encode()
            + b" "
            + str(HEIGHT).encode()
            + b"] /Resources << /Font << /F1 "
            + str(self.font).encode()
            + b" 0 R /F2 "
            + str(self.bold_font).encode()
            + b" 0 R >>"
            + xobjects
            + b" >> /Contents "
            + str(content_id).encode()
            + b" 0 R >>"
        )
        self.pages.append(self.object(page))

    def save(self, path: Path) -> None:
        pages_id = self.object(b"")
        page_bytes = []
        for page_id in self.pages:
            page_bytes.append(self.objects[page_id - 1].replace(b"PARENT 0 R", str(pages_id).encode() + b" 0 R"))
        for page_id, value in zip(self.pages, page_bytes):
            self.objects[page_id - 1] = value
        self.objects[pages_id - 1] = (
            b"<< /Type /Pages /Kids ["
            + b" ".join(str(page_id).encode() + b" 0 R" for page_id in self.pages)
            + b"] /Count "
            + str(len(self.pages)).encode()
            + b" >>"
        )
        catalog_id = self.object(b"<< /Type /Catalog /Pages " + str(pages_id).encode() + b" 0 R >>")

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for index, value in enumerate(self.objects, start=1):
            offsets.append(len(output))
            output.extend(f"{index} 0 obj\n".encode())
            output.extend(value)
            output.extend(b"\nendobj\n")
        xref_offset = len(output)
        output.extend(f"xref\n0 {len(self.objects) + 1}\n".encode())
        output.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.extend(f"{offset:010d} 00000 n \n".encode())
        output.extend(
            b"trailer\n<< /Size "
            + str(len(self.objects) + 1).encode()
            + b" /Root "
            + str(catalog_id).encode()
            + b" 0 R >>\nstartxref\n"
            + str(xref_offset).encode()
            + b"\n%%EOF\n"
        )
        path.write_bytes(output)


class Slide:
    def __init__(self, number: int, kicker: str, title: str) -> None:
        self.number = number
        self.kicker = kicker
        self.title = title
        self.commands: list[str] = []
        self.background("F7F9FC")
        self.header()

    def command(self, value: str) -> None:
        self.commands.append(value)

    def color(self, hex_color: str, stroke: bool = False) -> None:
        r, g, b = rgb(hex_color)
        self.command(f"{r:.4f} {g:.4f} {b:.4f} {'RG' if stroke else 'rg'}")

    def background(self, hex_color: str) -> None:
        self.color(hex_color)
        self.command(f"0 0 {WIDTH} {HEIGHT} re f")

    def rect(self, x: float, y: float, width: float, height: float, fill: str, stroke: str | None = None, radius: float = 0) -> None:
        self.color(fill)
        if radius:
            curve = min(radius, width / 2, height / 2)
            path = f"{x + curve} {HEIGHT - y - height} m {x + width - curve} {HEIGHT - y - height} l {x + width} {HEIGHT - y - height + curve} l {x + width} {HEIGHT - y - curve} l {x + width - curve} {HEIGHT - y} l {x + curve} {HEIGHT - y} l {x} {HEIGHT - y - curve} l {x} {HEIGHT - y - height + curve} l h f"
            self.command(path)
        else:
            self.command(f"{x} {HEIGHT - y - height} {width} {height} re f")
        if stroke:
            self.color(stroke, stroke=True)
            self.command(f"{x} {HEIGHT - y - height} {width} {height} re S")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: str, width: float = 1) -> None:
        self.color(color, stroke=True)
        self.command(f"{width} w {x1} {HEIGHT - y1} m {x2} {HEIGHT - y2} l S")

    def text(self, x: float, y: float, value: str, size: float = 16, color: str = "14213D", bold: bool = False) -> None:
        self.color(color)
        font = "/F2" if bold else "/F1"
        baseline = HEIGHT - y - size
        self.command(f"BT {font} {size} Tf {x} {baseline} Td ({pdf_text(value)}) Tj ET")

    def wrapped(self, x: float, y: float, value: str, max_width: float, size: float = 15, color: str = "425466", leading: float | None = None, bold: bool = False) -> float:
        leading = leading or size * 1.35
        words = value.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) * size * 0.5 <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        for index, line in enumerate(lines):
            self.text(x, y + index * leading, line, size, color, bold)
        return y + len(lines) * leading

    def bullet_list(self, x: float, y: float, bullets: list[str], max_width: float, size: float = 15, color: str = "425466", gap: float = 13) -> float:
        current_y = y
        for bullet in bullets:
            self.rect(x, current_y + 7, 6, 6, "12B8A6", radius=3)
            current_y = self.wrapped(x + 18, current_y, bullet, max_width - 18, size, color, size * 1.35)
            current_y += gap
        return current_y

    def card(self, x: float, y: float, width: float, height: float, title: str, body: str, accent: str = "12B8A6") -> None:
        self.rect(x, y, width, height, "FFFFFF", "D7E0EA", 12)
        self.rect(x, y, 5, height, accent, radius=2)
        self.text(x + 22, y + 18, title, 17, "14213D", True)
        self.wrapped(x + 22, y + 48, body, width - 42, 13, "5C6B7A", 18)

    def header(self) -> None:
        self.text(50, 30, "RISKPULSE AI", 12, "12B8A6", True)
        self.text(50, 48, self.kicker.upper(), 10, "7B8794", True)
        self.text(50, 74, self.title, 30, "14213D", True)
        self.text(1190, 40, f"0{self.number} / 07", 11, "7B8794", True)
        self.line(50, 118, 1230, 118, "D7E0EA")

    def footer(self) -> None:
        self.line(50, 681, 1230, 681, "D7E0EA")
        self.text(50, 692, "Explainable risk intelligence | Educational prototype", 10, "7B8794")
        self.text(1120, 692, "RiskPulse AI", 10, "12B8A6", True)

    def finish(self) -> str:
        self.footer()
        return "\n".join(self.commands)


def make_slides(document: PdfDocument) -> None:
    # 1 - Title
    slide = Slide(1, "Campus hackathon submission", "RiskPulse AI")
    slide.rect(50, 160, 1180, 410, "14213D", radius=18)
    slide.rect(50, 160, 14, 410, "12B8A6", radius=7)
    slide.text(105, 215, "Explainable risk intelligence", 39, "FFFFFF", True)
    slide.text(105, 267, "From unstructured information to auditable portfolio impact", 20, "B8C9DB")
    slide.line(105, 326, 820, 326, "12B8A6", 3)
    slide.text(105, 360, "AI / NLP risk engine + deterministic stress testing", 22, "FFFFFF", True)
    slide.text(105, 412, "Candidate: Amit Kumar", 16, "D9E3ED")
    slide.text(105, 442, "College / Campus: IIIT Raichur", 16, "D9E3ED")
    slide.text(105, 472, "S&P Global & Crisil Campus Hackathon", 16, "D9E3ED")
    slide.rect(900, 225, 230, 230, "0B6E68", radius=115)
    slide.rect(947, 272, 136, 136, "12B8A6", radius=68)
    slide.line(975, 364, 1049, 290, "FFFFFF", 7)
    slide.line(975, 364, 1049, 364, "FFFFFF", 7)
    slide.text(975, 480, "SIGNAL", 12, "8FE8DA", True)
    slide.text(975, 500, "to IMPACT", 12, "FFFFFF", True)
    document.page(slide.finish())

    # 2 - Problem and approach
    slide = Slide(2, "01 | Why this matters", "Problem & approach")
    slide.card(50, 152, 535, 390, "The business problem", "Risk teams receive fragmented, unstructured information. A headline or social post may indicate credit, geopolitical, regulatory, or market stress, but raw text does not explain which portfolio positions are exposed or how severe the impact could be.", "E45B4C")
    slide.bullet_list(78, 315, [
        "Information is high-volume and difficult to prioritize.",
        "Entity names, event types, and exposure links are easy to miss.",
        "Naive stress tests are disconnected from their triggering evidence.",
    ], 470, 14, "425466", 12)
    slide.card(625, 152, 605, 390, "The RiskPulse AI approach", "A traceable pipeline links source records to risk signals and then to deterministic, auditable portfolio stress results.", "12B8A6")
    steps = [("01", "Ingest", "RSS and historical social CSV"), ("02", "Understand", "Entities, sentiment, event type"), ("03", "Score", "Impact 1-10 with factor explanation"), ("04", "Stress", "Scenario routing and position P&L")]
    y = 285
    for number, title, body in steps:
        slide.rect(665, y, 38, 38, "E8F7F5", "12B8A6", 8)
        slide.text(674, y + 9, number, 11, "0B6E68", True)
        slide.text(725, y + 2, title, 16, "14213D", True)
        slide.text(725, y + 23, body, 13, "5C6B7A")
        if y < 470:
            slide.line(684, y + 42, 684, y + 65, "12B8A6", 1.5)
        y += 65
    document.page(slide.finish())

    # 3 - System design
    slide = Slide(3, "02 | How it works", "System design & data flow")
    slide.text(50, 132, "A source record becomes a persisted, explainable stress result.", 16, "425466")
    image_width = 1160
    image_height = image_width * document.image_height / document.image_width
    x = (WIDTH - image_width) / 2
    image_y = 164
    image_bottom = HEIGHT - image_y - image_height
    slide.command(f"q {image_width:.2f} 0 0 {image_height:.2f} {x:.2f} {image_bottom:.2f} cm /Im1 Do Q")
    document.page(slide.finish(), with_image=True)

    # 4 - Implementation highlights
    slide = Slide(4, "03 | Build choices", "Implementation highlights")
    cards = [
        (50, 155, 270, 205, "Ingestion", "RSS, social CSV replay, optional Reddit, normalized timestamps, content hashes, source-level status, bounded retries.", "2B78C5"),
        (345, 155, 270, 205, "NLP risk engine", "Alias-driven entities, heuristic default, optional FinBERT, event classifier, sentiment [-1, 1], impact [1-10].", "6B4ACB"),
        (640, 155, 270, 205, "Stress engine", "One event-to-scenario mapping, targeted eligibility, corporate credit, equities, bonds, swaps, and FX forwards.", "D88A00"),
        (935, 155, 295, 205, "Auditability", "PostgreSQL persistence, Alembic migrations, input snapshots, calculation details, reconciliation, and triggering article links.", "0B8F7C"),
    ]
    for card in cards:
        slide.card(*card)
    slide.text(50, 415, "Technology choices", 19, "14213D", True)
    slide.bullet_list(55, 455, [
        "FastAPI + SQLAlchemy + PostgreSQL: clear service boundaries and durable audit records.",
        "Next.js + TypeScript + Recharts: fast analyst-facing views for feed, signals, portfolio, and stress results.",
        "Deterministic scoring and scenario valuation: repeatable demo behavior and testable assumptions.",
    ], 1120, 15, "425466", 11)
    slide.rect(50, 610, 1180, 43, "E8F7F5", radius=8)
    slide.text(70, 622, "Design principle", 13, "0B6E68", True)
    slide.text(200, 622, "Every material result should answer: what happened, why it mattered, and which positions were affected?", 13, "425466")
    document.page(slide.finish())

    # 5 - Key results
    slide = Slide(5, "04 | Evidence", "Key results")
    metrics = [(50, "82", "backend tests passing", "12B8A6"), (305, "2", "data sources in the demo", "2B78C5"), (560, "20", "seeded portfolio positions", "6B4ACB"), (815, "7", "default auto-trigger threshold", "D88A00"), (1070, "1.0000", "smoke accuracy / macro-F1", "0B8F7C")]
    for x, value, label, accent in metrics:
        slide.rect(x, 155, 180, 115, "FFFFFF", "D7E0EA", 10)
        slide.rect(x, 155, 180, 6, accent, radius=3)
        slide.text(x + 18, 183, value, 30, "14213D", True)
        slide.wrapped(x + 18, 225, label, 145, 11, "5C6B7A", 14)
    slide.text(50, 325, "Naive flow vs. RiskPulse AI", 20, "14213D", True)
    slide.rect(50, 365, 535, 220, "FFF8F7", "F2C5C0", 10)
    slide.text(75, 390, "Naive feed", 16, "A8392F", True)
    slide.bullet_list(75, 430, ["Raw articles without exposure linkage", "No consistent score range or rationale", "Manual scenario selection", "No position-level reconciliation"], 450, 14, "6E4A48", 10)
    slide.rect(625, 365, 605, 220, "F1FBF9", "B7E6DE", 10)
    slide.text(650, 390, "RiskPulse AI", 16, "0B6E68", True)
    slide.bullet_list(650, 430, ["Named issuer and ticker aliases map signals to positions", "Sentiment, event weight, and entity exposure explain impact", "Impact above 7 automatically routes a scenario", "Before/after P&L, top losses, matched positions, and reconciliation"], 520, 14, "35625E", 10)
    slide.text(50, 625, "The smoke metrics are deliberately qualified: the local PhraseBank fixture has three rows and is not a full benchmark.", 11, "7B8794")
    document.page(slide.finish())

    # 6 - Domain impact
    slide = Slide(6, "05 | Why it matters", "Domain impact")
    slide.text(50, 145, "A practical analyst workflow", 21, "14213D", True)
    timeline = [
        ("01", "Detect", "A new article or historical social record enters the same normalized pipeline."),
        ("02", "Explain", "Entity, event type, sentiment, and impact factors are visible instead of hidden in a black box."),
        ("03", "Prioritize", "A threshold identifies material signals and selects the matching stress scenario."),
        ("04", "Act", "The analyst sees portfolio value change, top losses, and matched exposures for review."),
    ]
    x = 70
    for index, (number, title, body) in enumerate(timeline):
        slide.rect(x, 220, 210, 62, "14213D", radius=10)
        slide.text(x + 18, 235, number, 14, "8FE8DA", True)
        slide.text(x + 55, 233, title, 17, "FFFFFF", True)
        slide.wrapped(x, 315, body, 210, 13, "425466", 18)
        if index < len(timeline) - 1:
            slide.line(x + 215, 251, x + 270, 251, "12B8A6", 3)
            slide.line(x + 260, 243, x + 270, 251, "12B8A6", 3)
            slide.line(x + 260, 259, x + 270, 251, "12B8A6", 3)
        x += 290
    slide.card(50, 470, 560, 125, "Business value", "Creates a common language between information, risk signals, exposure, and scenario results. This supports faster triage and more defensible analyst conversations.", "12B8A6")
    slide.card(650, 470, 580, 125, "Demo value", "The workflow is deterministic, inspectable, and easy to replay. A reviewer can move from a triggering article to the exact positions included in the stress result.", "2B78C5")
    document.page(slide.finish())

    # 7 - Limitations and next steps
    slide = Slide(7, "06 | Responsible use", "Limitations & next steps")
    slide.card(50, 155, 555, 395, "Current limitations", "This is a case-study prototype. The output is designed to demonstrate traceability and scenario mechanics, not to represent a calibrated production risk model.", "E45B4C")
    slide.bullet_list(78, 290, [
        "Portfolio holdings are synthetic; transaction categories are proxies, not proof of real exposures.",
        "Stress shocks are illustrative assumptions and are not forecasts or investment advice.",
        "Historical social replay lacks live delivery order, deleted-post behavior, engagement data, and return labels.",
        "Heuristic sentiment is the safe default; FinBERT requires model download and legal review.",
    ], 490, 14, "6E4A48", 11)
    slide.card(655, 155, 575, 395, "Next steps", "The foundation can evolve toward a governed risk workflow with stronger data and model controls.", "12B8A6")
    slide.bullet_list(683, 290, [
        "Replace synthetic holdings with permissioned portfolio and reference-data integrations.",
        "Calibrate shocks and validate results against approved market and credit methodologies.",
        "Add authentication, role-based access, secrets management, observability, and deployment controls.",
        "Expand evaluation beyond the three-row smoke fixture and monitor model drift.",
    ], 510, 14, "425466", 11)
    slide.rect(50, 595, 1180, 47, "14213D", radius=8)
    slide.text(75, 609, "Demo sequence", 13, "8FE8DA", True)
    slide.text(205, 609, "Ingest demo articles -> process NLP -> open Stress Testing -> inspect triggering article and matched positions", 13, "FFFFFF")
    document.page(slide.finish())


def main() -> None:
    if not ARCHITECTURE.exists():
        raise SystemExit(f"Missing architecture asset: {ARCHITECTURE}")
    document = PdfDocument()
    make_slides(document)
    document.save(OUTPUT)
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

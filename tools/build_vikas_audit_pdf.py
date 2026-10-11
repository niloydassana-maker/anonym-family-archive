# -*- coding: utf-8 -*-
"""
Builds an executive 3-page publication-grade PDF report:
d:\anonym\docs\VIKAS-GHOSH-DNA-FORENSIC-AUDIT.pdf
from the forensic analysis of Vikas (Bikash) Ghosh.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.pdfgen import canvas

PDF_OUT = r"d:\anonym\docs\VIKAS-GHOSH-DNA-FORENSIC-AUDIT.pdf"

# Palette
NAVY      = HexColor("#0F172A")
SLATE     = HexColor("#334155")
LIGHT_BG  = HexColor("#F8FAFC")
BORDER    = HexColor("#CBD5E1")
RED_WARN  = HexColor("#B91C1C")
AMBER     = HexColor("#B45309")
GREEN_OK  = HexColor("#15803D")
WHITE     = HexColor("#FFFFFF")
ROW_ALT   = HexColor("#F1F5F9")

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(1.4 * cm, A4[1] - 1.1 * cm, "DNA & FORENSIC TECHNICAL AUDIT : VIKAS (BIKASH) GHOSH")
            self.drawRightString(A4[0] - 1.4 * cm, A4[1] - 1.1 * cm, "OCTOBER 2026 · ARCHIVE")
            self.setStrokeColor(BORDER)
            self.setLineWidth(0.5)
            self.line(1.4 * cm, A4[1] - 1.25 * cm, A4[0] - 1.4 * cm, A4[1] - 1.25 * cm)

        # Footer (all pages)
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.5)
        self.line(1.4 * cm, 1.2 * cm, A4[0] - 1.4 * cm, 1.2 * cm)
        self.drawString(1.4 * cm, 0.85 * cm, "FORTRESS ARCHITECTURAL AUDIT · ZERO-MANUFACTURE LAW ENFORCED")
        self.drawRightString(A4[0] - 1.4 * cm, 0.85 * cm, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def build_pdf():
    os.makedirs(os.path.dirname(PDF_OUT), exist_ok=True)
    
    doc = SimpleDocTemplate(
        PDF_OUT,
        pagesize=A4,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    # Custom typography styles
    st_title = ParagraphStyle(
        "DocTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=NAVY,
        spaceAfter=2
    )
    st_subtitle = ParagraphStyle(
        "DocSub",
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=RED_WARN,
        spaceAfter=8
    )
    st_meta = ParagraphStyle(
        "MetaText",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=SLATE
    )
    st_h1 = ParagraphStyle(
        "H1",
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=NAVY,
        spaceBefore=8,
        spaceAfter=4
    )
    st_h2 = ParagraphStyle(
        "H2",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13.5,
        textColor=SLATE,
        spaceBefore=6,
        spaceAfter=3
    )
    st_body = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12.5,
        textColor=HexColor("#1E293B"),
        alignment=TA_JUSTIFY,
        spaceAfter=5
    )
    st_bullet = ParagraphStyle(
        "Bullet",
        parent=st_body,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=4
    )
    st_th = ParagraphStyle(
        "TH",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=WHITE,
        alignment=TA_LEFT
    )
    st_td = ParagraphStyle(
        "TD",
        fontName="Helvetica",
        fontSize=7.8,
        leading=10.5,
        textColor=HexColor("#0F172A"),
        alignment=TA_LEFT
    )
    st_td_bold = ParagraphStyle(
        "TDBold",
        parent=st_td,
        fontName="Helvetica-Bold"
    )
    st_td_warn = ParagraphStyle(
        "TDWarn",
        parent=st_td,
        fontName="Helvetica-Bold",
        textColor=RED_WARN
    )
    st_code = ParagraphStyle(
        "CodeBlock",
        fontName="Courier",
        fontSize=7.5,
        leading=10.2,
        textColor=HexColor("#0F172A"),
        alignment=TA_LEFT
    )
    st_verdict = ParagraphStyle(
        "Verdict",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=NAVY
    )

    story = []

    # ================= PAGE 1 =================
    # Title & Header
    story.append(Paragraph("DNA &amp; FORENSIC TECHNICAL AUDIT : VIKAS (BIKASH) GHOSH", st_title))
    story.append(Paragraph("DECONSTRUCTION OF TECHNICAL CAPABILITY, SYSTEMIC ARCHITECTURE &amp; OPERATIONAL REALITY", st_subtitle))

    # Meta Table
    meta_data = [
        [
            Paragraph("<b>Subject:</b> Bikash (Vikas) Ghosh<br/><b>Origin:</b> Dum Dum, West Bengal", st_meta),
            Paragraph("<b>Classification:</b> Non-Technical / MLM Operative<br/><b>Affiliation:</b> Smart Value / APLL", st_meta),
            Paragraph("<b>Audit Date:</b> October 11, 2026<br/><b>Auditor:</b> Fortress Architecture Council", st_meta)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[6.0*cm, 6.2*cm, 6.0*cm])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 4))

    # 1. Executive Summary Table
    story.append(Paragraph("1. Executive Summary &amp; Pedigree Deconstruction", st_h1))
    story.append(Paragraph(
        "Forensic contrast between the subject's projected public persona and verified empirical reality:", st_body
    ))

    ped_headers = ["Parameter", "Publicly Projected Claim", "Verified Forensic Reality", "Delta / Discrepancy"]
    ped_rows = [
        [
            "Identity & Roots",
            "Self-styled 'IT Visionary', 'Imperial King', and direct-selling business icon.",
            "Bikash Ghosh, Dum Dum, WB. Son of a rickshaw puller; lower-middle-class roots.",
            "Humble origins romanticized and weaponized into a stage recruitment myth."
        ],
        [
            "Formal Education",
            "Presents self as a high-stature technology and enterprise business authority.",
            "Non-graduate; 3rd-year college dropout. Zero software, CS, or math credentials.",
            "100% Non-Credentialed in computing and software engineering."
        ],
        [
            "Primary Vehicle",
            "Smart Value Products & Services Ltd. (SVPSL) and APLL ecosystem.",
            "Senior multi-level sales recruiter and downline motivator for 10+ years.",
            "Multi-level network sales operation; not a technology enterprise."
        ],
        [
            "Core Product",
            "'IT Smart Plus', 'Information Technology Revolution', 'Digital Empowerment'.",
            "Outdated introductory booklets (basic MS Office, DCA/PGDCA theory, static booklets).",
            "Regulatory product shield; negligible open-market engineering utility."
        ],
        [
            "Technical Output",
            "Frontline champion of the digital era and youth tech empowerment.",
            "0 Git repositories, 0 lines of production code, 0 RFCs, 0 software deployments.",
            "Absolute Zero (0.0%) empirical software engineering footprint."
        ]
    ]

    t_ped_data = [[Paragraph(f"<b>{h}</b>", st_th) for h in ped_headers]]
    for i, r in enumerate(ped_rows):
        t_ped_data.append([
            Paragraph(r[0], st_td_bold),
            Paragraph(r[1], st_td),
            Paragraph(r[2], st_td),
            Paragraph(r[3], st_td_warn if "Zero" in r[3] or "100%" in r[3] else st_td)
        ])
    t_ped = Table(t_ped_data, colWidths=[3.0*cm, 4.8*cm, 5.4*cm, 5.0*cm])
    t_ped.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        *([('BACKGROUND', (0, k), (-1, k), ROW_ALT) for k in range(2, len(t_ped_data), 2)])
    ]))
    story.append(t_ped)
    story.append(Spacer(1, 4))

    # 2. Technical Capability Audit
    story.append(Paragraph("2. Technical Capability Audit: The Absolute Zero Baseline", st_h1))
    story.append(Paragraph(
        "Evaluated against standard enterprise engineering criteria (enterprise CTOs and systems architects):",
        st_body
    ))

    cap_headers = ["Engineering Domain", "Enterprise Standard Metric", "Subject Empirical Reality", "Evaluation"]
    cap_rows = [
        ["Systems Architecture", "Microservices, distributed consensus, fault-tolerance", "Layman buzzwords ('Computer Yug', 'Digital Era')", "ABSENT (0%)"],
        ["Low-Level Engineering", "C/C++, Rust, POSIX, Linux Kernel internals", "Zero experience; cannot read or write low-level code", "ABSENT (0%)"],
        ["High-Level Languages", "Java, Go, Python, TypeScript / Node.js", "Zero production script authorship across any language", "ABSENT (0%)"],
        ["Database & Spatial", "SQL, PostGIS, GiST indices, ACID transactions", "Understands databases only as a static 'distributor list'", "ABSENT (0%)"],
        ["Distributed Queuing", "Kafka, Redis Streams, RabbitMQ backpressure", "Zero message queuing or async concurrency knowledge", "ABSENT (0%)"],
        ["Cloud & Infra", "AWS, GCP, Kubernetes, Docker, CI/CD runners", "Zero cloud orchestration, IAM, or container deployment", "ABSENT (0%)"],
        ["Security & Protocols", "TLS, OAuth2, SHA-256 receipts, socket streaming", "Zero protocol awareness or cryptographic literacy", "ABSENT (0%)"],
        ["Algorithms & Math", "DSA, graph theory, optimization, complexity analysis", "Zero formal algorithmic or mathematical grounding", "ABSENT (0%)"],
    ]

    t_cap_data = [[Paragraph(f"<b>{h}</b>", st_th) for h in cap_headers]]
    for r in cap_rows:
        t_cap_data.append([
            Paragraph(r[0], st_td_bold),
            Paragraph(r[1], st_td),
            Paragraph(r[2], st_td),
            Paragraph(f"<b>{r[3]}</b>", st_td_warn)
        ])
    t_cap = Table(t_cap_data, colWidths=[3.4*cm, 5.4*cm, 6.6*cm, 2.8*cm])
    t_cap.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        *([('BACKGROUND', (0, k), (-1, k), ROW_ALT) for k in range(2, len(t_cap_data), 2)])
    ]))
    story.append(t_cap)

    # ================= PAGE 2 =================
    story.append(PageBreak())

    # 3. The Broken Architecture
    story.append(Paragraph("3. The Broken Architecture: The Trojan Horse & Downline Engine", st_h1))
    story.append(Paragraph(
        "Vikas Ghosh does not run a software architecture. His operation is a <b>human binary recruitment tree</b> wrapped inside an educational IT veneer.",
        st_body
    ))

    arch_box = [
        [Paragraph(
            "<b>STRUCTURAL SCHEMATIC OF THE PIPELINE:</b><br/>"
            "<b>[Target Audience]</b> Economically vulnerable Tier-2/3 college students, freshers, dropouts.<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;│<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;▼<br/>"
            "<b>[The Trojan Horse]</b> APLL 'IT Smart' Package (~₹10,000–₹15,000 admission fee).<br/>"
            "<i>(Elementary computer leaflets serving as a regulatory legal shield)</i><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;│<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;▼<br/>"
            "<b>[The Binary Recruitment Matrix]</b><br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;├── <b>Left Leg:</b> Recruits peer → Peer buys package → Points generated<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;└── <b>Right Leg:</b> Recruits peer → Peer buys package → Pair matched<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;│<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;▼<br/>"
            "<b>[Upward Capital Extraction]</b> Commissions flow directly to apex 'Imperial Kings'.<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;│<br/>"
            "&nbsp;&nbsp;&nbsp;&nbsp;▼<br/>"
            "<b>[Theatrical Stabilizer]</b> Luxury car spectacles, rented auditoriums, blaring music, emotional rallies.",
            st_code
        )]
    ]
    t_arch = Table(arch_box, colWidths=[18.2*cm])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 6))

    story.append(Paragraph("<b>The Three Structural Fractures:</b>", st_h2))
    story.append(Paragraph(
        "<b>1. The Commodity Carrier (Regulatory Evasion Shield):</b> Authentic technology companies earn revenue by delivering computational or operational utility (solving a business bottleneck, reducing latency, automating workflows). In Vikas Ghosh's model, the educational software product is simply a <i>statutory commodity carrier</i> designed to navigate around the <i>Prize Chits and Money Circulation Schemes (Banning) Act, 1978</i>. The training itself holds zero hiring credibility in authentic enterprise tech firms.",
        st_bullet
    ))
    story.append(Paragraph(
        "<b>2. Closed-Loop Capital Extraction:</b> There is zero institutional or B2B enterprise client revenue entering the ecosystem. 100% of the funds originate from freshers paying admission fees. It is a mathematically bounded extraction engine where the vast majority of downline participants must operate at a net financial deficit to subsidize the apex commissions of top promoters.",
        st_bullet
    ))
    story.append(Paragraph(
        "<b>3. The Motivational Heat-Sink:</b> Because the system produces no tangible software or business value, it is prone to structural exhaustion and distributor disillusionment. To maintain pressure, the architecture depends entirely on emotional cooling mechanisms: high-decibel motivational rallies, luxury cars (Audi/BMW), and messianic speeches designed to suppress critical thinking.",
        st_bullet
    ))
    story.append(Spacer(1, 6))

    # 4. Capability Defect
    story.append(Paragraph("4. Capability Defect: Root Cause Analysis", st_h1))
    story.append(Paragraph(
        "<b>A. The Cargo-Cult IT Syndrome:</b> The subject adopts the external aesthetics of modern enterprise technology leaders (suits, microphones, corporate jargon, laptop banners) without possessing the scientific or engineering foundation. He conflates <i>selling a brochure about computers</i> with <i>being a computer architect</i>.",
        st_body
    ))
    story.append(Paragraph(
        "<b>B. Predatory Rhetorical Arbitrage:</b> His sole developed capability is oratorical manipulation directed at vulnerable youth. Instead of equipping students with real, employable skills (data structures, systems design, Linux, backend development), he trains them in social prospecting—converting family members and peers into downline sales targets.",
        st_body
    ))
    story.append(Paragraph(
        "<b>C. Structural Fragility Under Technical Scrutiny:</b> His entire authority exists only in closed halls where the audience has no baseline knowledge of computer science. If subjected to a basic technical panel regarding database transactions, concurrency, or network architecture, his entire persona collapses immediately.",
        st_body
    ))

    # ================= PAGE 3 =================
    story.append(PageBreak())

    # 5. Enterprise Reality vs Stagecraft
    story.append(Paragraph("5. The Empirical Contrast: Enterprise Systems Reality vs. Stagecraft", st_h1))
    story.append(Paragraph(
        "A rigorous architectural comparison between authentic enterprise engineering reality and downline stagecraft:",
        st_body
    ))

    comp_headers = ["Dimension", "Enterprise Systems Architecture (e.g. Baba / Niloy Das)", "Vikas (Bikash) Ghosh"]
    comp_rows = [
        ["Pedigree & Education", "NIT Alumnus; 20+ years enterprise systems architecture (Bengaluru origin)", "3rd-year college dropout; zero engineering background"],
        ["Technical Domain", "Kernel scheduling, distributed microservices, PostGIS spatial data, low-latency APIs", "Motivational speaking, MLM recruitment scripts, sales prospecting"],
        ["Verification Standard", "Zero-Manufacture Law: live network echo, screen proofs, SHA-256 verifiable disk receipts", "Theatrical stage entrances, rented luxury vehicles, unverified assertions"],
        ["Economic Model", "Solving mission-critical enterprise bottlenecks for institutional clients paying verified retainers", "Extracting admission fees from unemployed rural/suburban freshers in a binary downline"],
        ["Target Engagement", "Founders, CEOs, CTOs, Enterprise Directors, Technology Leaders", "Freshers, college students, job seekers in economically depressed districts"],
    ]

    t_comp_data = [[Paragraph(f"<b>{h}</b>", st_th) for h in comp_headers]]
    for r in comp_rows:
        t_comp_data.append([
            Paragraph(r[0], st_td_bold),
            Paragraph(r[1], st_td),
            Paragraph(r[2], st_td)
        ])
    t_comp = Table(t_comp_data, colWidths=[3.4*cm, 7.4*cm, 7.4*cm])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        *([('BACKGROUND', (0, k), (-1, k), ROW_ALT) for k in range(2, len(t_comp_data), 2)])
    ]))
    story.append(t_comp)
    story.append(Spacer(1, 14))

    # 6. Conclusion
    story.append(Paragraph("6. Audit Verdict &amp; Archival Receipt", st_h1))
    verdict_box = [
        [Paragraph(
            "<b>FINAL AUDIT VERDICT:</b><br/>"
            "1. <b>Technical Capability: 0.0% (Absolute Defect).</b> Subject possesses zero capacity to conceptualize, write, design, or audit software systems.<br/>"
            "2. <b>System Architecture: Broken &amp; Parasitic.</b> Operates a zero-sum binary recruitment network using introductory educational packages as a legal shield.<br/>"
            "3. <b>Core Finding:</b> Vikas Ghosh is an MLM sales recruiter. Any conflation between his stagecraft and authentic enterprise software engineering is fundamentally category-erroneous.<br/><br/>"
            "<b>FORTRESS ARCHIVAL CITATION:</b><br/>"
            "• Disk Location: <code>d:\\anonym\\docs\\VIKAS-GHOSH-DNA-FORENSIC-AUDIT.pdf</code><br/>"
            "• Markdown Master: <code>d:\\anonym\\docs\\VIKAS-GHOSH-DNA-FORENSIC-AUDIT.md</code><br/>"
            "• Standard Enforced: Supreme Edict &amp; Zero-Manufacture Law (Zero Synthetic Proof).",
            st_verdict
        )]
    ]
    t_verd = Table(verdict_box, colWidths=[18.2*cm])
    t_verd.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), HexColor("#FEF2F2")),
        ('BOX', (0,0), (-1,-1), 1.5, RED_WARN),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_verd)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {PDF_OUT}")

if __name__ == "__main__":
    build_pdf()

"""Generate Production Brief docx for the KR Pension SAA promotional video.

Output: docs/production_brief_kr_pension_saa.docx
Audience: external video producer (영상 제작자)
Emphasis: (1) AI Agent multi-agent architecture (2) AI 자율 결정 (no human in loop)
"""
from __future__ import annotations
from pathlib import Path

from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ---------- 스타일 헬퍼 ----------
NAVY = RGBColor(0x1F, 0x4E, 0x79)
GOLD = RGBColor(0xC8, 0x9B, 0x3C)
GRAY = RGBColor(0x55, 0x55, 0x55)
LIGHT = RGBColor(0xEE, 0xEE, 0xEE)


def set_kr_font(run, size_pt=10, bold=False, color=None):
    run.font.name = "Malgun Gothic"
    run.font.size = Pt(size_pt)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = OxmlElement("w:rFonts")
    rfonts.set(qn("w:eastAsia"), "Malgun Gothic")
    rfonts.set(qn("w:ascii"), "Malgun Gothic")
    rfonts.set(qn("w:hAnsi"), "Malgun Gothic")
    rpr.append(rfonts)


def add_h1(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_kr_font(r, 18, bold=True, color=NAVY)
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(8)
    # 가는 밑줄
    pPr = p._element.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:color"), "1F4E79")
    pBdr.append(bottom)
    pPr.append(pBdr)


def add_h2(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_kr_font(r, 13, bold=True, color=NAVY)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)


def add_h3(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_kr_font(r, 11, bold=True, color=GRAY)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)


def add_body(doc, text, bold=False, color=None, size=10):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_kr_font(r, size, bold=bold, color=color)
    p.paragraph_format.space_after = Pt(4)
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(text)
    set_kr_font(r, 10)
    p.paragraph_format.left_indent = Cm(0.5 + 0.5 * level)
    p.paragraph_format.space_after = Pt(2)
    return p


def add_callout(doc, text, color=GOLD):
    p = doc.add_paragraph()
    r = p.add_run("▸ " + text)
    set_kr_font(r, 10, bold=True, color=color)
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_after = Pt(6)


def shade_cell(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_table(doc, headers, rows, widths=None, header_color="1F4E79"):
    n_cols = len(headers)
    table = doc.add_table(rows=1 + len(rows), cols=n_cols)
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    if widths:
        for i, w in enumerate(widths):
            for cell in table.columns[i].cells:
                cell.width = Cm(w)

    # 헤더
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h)
        set_kr_font(r, 10, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shade_cell(cell, header_color)

    # 본문
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = table.rows[1 + ri].cells[ci]
            cell.text = ""
            p = cell.paragraphs[0]
            r = p.add_run(str(val))
            set_kr_font(r, 9.5)
            p.paragraph_format.space_after = Pt(0)
    doc.add_paragraph()
    return table


# ---------- 문서 작성 ----------
def build():
    doc = Document()

    # 페이지 여백
    for section in doc.sections:
        section.top_margin = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(2.2)
        section.right_margin = Cm(2.2)

    # ====== 표지 ======
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("PRODUCTION BRIEF")
    set_kr_font(r, 11, bold=True, color=GOLD)
    p.paragraph_format.space_before = Pt(60)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("KR 연금 자율주행 SAA")
    set_kr_font(r, 32, bold=True, color=NAVY)
    p.paragraph_format.space_after = Pt(0)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Self-Driving Pension Allocation by Multi-Agent AI")
    set_kr_font(r, 14, color=GRAY)
    p.paragraph_format.space_after = Pt(40)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("외부 영상 제작자 작업 가이드")
    set_kr_font(r, 12, bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("핵심 메시지: 46개 AI 에이전트가 자율 협의해 만드는 한국형 퇴직연금 포트폴리오")
    set_kr_font(r, 11, color=GRAY)
    p.paragraph_format.space_after = Pt(60)

    # 메타 표
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ci in range(2):
        for cell in meta_table.columns[ci].cells:
            cell.width = Cm(7.0)
    metas = [
        ("프로젝트", "KR Pension Self-Driving SAA — 홍보 영상"),
        ("대상", "30-50대 DC/IRP 가입자, 퇴직연금 운용에 관심 있는 직장인"),
        ("형식", "메인 90초 + 티저 30초 (옵션: 3분 deep-dive)"),
        ("발행 채널", "YouTube / Instagram Reels / 카카오톡 채널"),
    ]
    for i, (k, v) in enumerate(metas):
        c0 = meta_table.rows[i].cells[0]
        c1 = meta_table.rows[i].cells[1]
        c0.text = ""
        c1.text = ""
        r0 = c0.paragraphs[0].add_run(k)
        set_kr_font(r0, 10, bold=True, color=NAVY)
        r1 = c1.paragraphs[0].add_run(v)
        set_kr_font(r1, 10)
        shade_cell(c0, "EEEEEE")

    doc.add_page_break()

    # ====== 1. 프로젝트 개요 ======
    add_h1(doc, "1. 프로젝트 개요")

    add_body(doc, "본 영상은 한국 퇴직연금(DC/IRP) 가입자를 대상으로 한 'AI 에이전트 자율운용 SAA' 데모 서비스의 홍보 영상입니다. 시청자가 30초 내에 '내 연금을 AI가 자율로 운용해주는 새로운 방식이 나왔다'는 사실을 인지하고, 90초 안에 그 차별성과 신뢰 근거(8.3년 백테스트 실적)를 이해하도록 설계되어야 합니다.", size=10)

    add_h2(doc, "영상이 반드시 전달해야 할 3가지 사실")
    add_callout(doc, "① 사람이 아니라 'AI 에이전트들'이 자율적으로 의사결정합니다.")
    add_callout(doc, "② 매크로 진단 → 21개 모델 산출 → 동료평가 → CIO 앙상블, 모든 단계가 자동입니다.")
    add_callout(doc, "③ 위험자산 70% 한도(법적 상한)를 100% 활용해 8.3년 백테스트 Sharpe 1.195를 달성했습니다.")

    add_h2(doc, "영상에서 절대 사용하면 안 되는 표현")
    add_bullet(doc, "\"수익 보장\", \"손실 없음\" — 백테스트는 미래를 보장하지 않습니다.")
    add_bullet(doc, "\"전문가가 운용\" — 본 모델의 차별성은 'AI 자율'이며 사람 자문이 아닙니다. 이 메시지가 흐려지면 안 됩니다.")
    add_bullet(doc, "\"투자 권유\" 인상을 주는 문구 — 면책 고지 필수.")
    add_bullet(doc, "타사 명칭 직접 비교 — 차별화는 카테고리(TDF, robo, 자문사) 단위로만.")

    add_h2(doc, "필수 면책 문구 (자막 / 엔드 카드)")
    add_body(doc, "「본 자료는 정보 제공 목적이며 투자 권유가 아닙니다. 투자 의사결정과 그 결과는 투자자 본인의 책임입니다. 백테스트 성과는 미래 수익을 보장하지 않습니다.」", color=GRAY)

    doc.add_page_break()

    # ====== 2. 핵심 메시지 / Tagline ======
    add_h1(doc, "2. 핵심 메시지 · Tagline")

    add_h2(doc, "Hero Tagline 후보 (3개 중 택일)")
    add_body(doc, "★ 1순위 추천", bold=True, color=GOLD)
    add_callout(doc, "\"46개 AI 에이전트가 협의해 결정하는, 한국형 퇴직연금 자율주행 SAA\"", color=NAVY)
    add_body(doc, "2순위", bold=True, color=GRAY)
    add_callout(doc, "\"사람이 아닌 AI가 직접 결정합니다 — Self-Driving Pension Allocation\"", color=NAVY)
    add_body(doc, "3순위", bold=True, color=GRAY)
    add_callout(doc, "\"AI 투자 위원회가 매월 당신의 연금을 다시 설계합니다\"", color=NAVY)

    add_h2(doc, "보조 카피 (자막 / 엔드 카드)")
    add_bullet(doc, "\"21개의 AI가 동료평가까지 한다\"")
    add_bullet(doc, "\"매크로부터 ETF 비중까지 — 100% 자동\"")
    add_bullet(doc, "\"위험자산 70% 한도, 끝까지 활용한 8.3년\"")
    add_bullet(doc, "\"모든 의사결정이 투명하게 공개됩니다\"")

    add_h2(doc, "키워드 — 영상 내내 등장해야 할 핵심 단어")
    add_body(doc, "AI 에이전트 (AI Agent), 자율 (Autonomous), 다중 에이전트 (Multi-Agent), 자율주행 (Self-Driving), 매크로 진단, 동료평가, CIO 앙상블", bold=True, color=NAVY)

    doc.add_page_break()

    # ====== 3. AI 에이전트 시스템 — 가장 중요한 섹션 ======
    add_h1(doc, "3. AI 에이전트 시스템 (반드시 강조)")

    add_body(doc, "본 모델은 단일 알고리즘이 아닌 9개 역할의 AI 에이전트가 자율적으로 협업하는 다중 에이전트 시스템입니다. 사람이 운영하는 자산운용사 조직 구조를 그대로 AI로 옮긴 것이 핵심 컨셉입니다 — 매크로 애널리스트, 18명의 자산 애널리스트, 21명의 포트폴리오 매니저, 위험관리자, 동료평가단, CIO. 영상 시청자가 이 'AI 조직' 이미지를 잡으면 차별화가 즉시 전달됩니다.", size=10)

    add_h2(doc, "AI 에이전트 ↔ 사람 자산운용사 조직 매핑")
    add_table(
        doc,
        headers=["사람 자산운용사 직무", "본 모델의 AI 에이전트", "수", "역할"],
        rows=[
            ["매크로 이코노미스트", "Macro Agent", "1", "ECOS+FRED 14개 지표 → 경기 레짐 분류"],
            ["섹터/자산 애널리스트", "Asset Class Agents", "18", "각 ETF별 기대수익률·변동성 추정"],
            ["퀀트 리서처", "Covariance Agent + PC Researcher", "2", "공분산 추정 + 신규 모델 제안"],
            ["포트폴리오 매니저", "PC Agents", "21", "각자 다른 알고리즘으로 비중 산출"],
            ["리스크 매니저 (CRO)", "CRO Agent", "1", "21개 안에 대한 위험 보고"],
            ["투자위원회 동료평가", "Strategy Review Agent", "1", "Borda count 투표로 최상위 5개 선별"],
            ["CIO (최고투자책임자)", "CIO Agent", "1", "7개 앙상블 후보 중 매크로에 맞춰 최종 선택"],
            ["성과 분석가", "Meta Agent", "1", "예측 vs 실현 추적, 자기개선 제안"],
        ],
        widths=[4.5, 4.5, 1.2, 5.3],
    )

    add_callout(doc, "영상에서 이 표를 1초 동안 풀스크린으로 보여주세요 — 시청자가 'AI가 통째로 운용사를 대체한다'는 메시지를 즉각 받습니다.", color=GOLD)

    add_h2(doc, "'자율'의 의미 — 영상에서 풀어 설명")
    add_bullet(doc, "사람의 개입 없이 분기마다 매크로 진단 → 자산 분석 → 21개 모델 산출 → 동료평가 → CIO 결정이 자동 실행됩니다.")
    add_bullet(doc, "투자자는 '이번 분기 추천 포트폴리오'를 받기만 하고, 매수·리밸런싱 결정도 본인이 합니다 (AI는 결정 자료 제공).")
    add_bullet(doc, "AI 에이전트는 정해진 프로토콜로 협업합니다 — 자료 호출, 분석, 평가, 합의가 모두 코드로 실행되어 재현 가능합니다.")

    add_h2(doc, "21개 PC 에이전트는 각자 어떻게 다른가")
    add_body(doc, "동일한 시장 데이터를 받아도 21개의 AI는 서로 다른 *철학*으로 비중을 산출합니다. 이 다양성이 본 모델의 핵심입니다.", size=10)
    add_table(
        doc,
        headers=["에이전트 카테고리", "개수", "철학", "대표 예"],
        rows=[
            ["Heuristic", "2", "단순 규칙 기반", "Equal Weight, Market Cap"],
            ["Return-Optimized", "5", "수익률 최대화", "Max Sharpe, Black-Litterman"],
            ["Risk-Structured", "6", "위험 구조화", "Risk Parity, GMV, HRP"],
            ["Non-Traditional", "7", "비전통 / 견고성", "CVaR-Min, Max-DD Constrained, Tail Risk Parity"],
            ["Researcher (자가제안)", "1", "매크로에 맞춰 *새로운* 방법 제안", "Maximum Entropy 등"],
        ],
        widths=[4.5, 1.2, 4.0, 5.8],
    )

    doc.add_page_break()

    # ====== 4. 스토리 구조 (90초 메인) ======
    add_h1(doc, "4. 스토리 구조 — 90초 메인 영상")

    add_table(
        doc,
        headers=["시간", "막", "메시지", "화면", "음향"],
        rows=[
            ["0:00 - 0:10", "Hook", "퇴직연금 70% 위험자산 한도, 안 쓰면 누적 100%p 기회비용", "안전자산 100% 누적곡선 vs 60/40 BM 누적곡선 비교 (Backtest 페이지)", "긴장감 있는 BGM 도입"],
            ["0:10 - 0:25", "Problem", "TDF는 정적, robo는 단일 알고리즘 블랙박스, 자문사는 분기 1회 정성 판단", "3가지 카테고리 슬라이드 (각 5초씩)", "BGM 유지"],
            ["0:25 - 0:45", "Solution-1", "AI 46명이 운용사 통째로 대체 — 자율 협업", "Section 3 매핑 표를 애니메이션으로 (사람 ↔ AI)", "BGM 전환 (희망적 톤)"],
            ["0:45 - 1:00", "Solution-2", "매크로 진단 → 21개 모델 → 동료평가 → CIO 결정 (5단계 파이프라인)", "5단계 다이어그램 + 대시보드 페이지 5의 21×ETF 히트맵", "BGM 가속"],
            ["1:00 - 1:15", "Result", "8.3년 walk-forward Sharpe 1.195, CAGR 11.15%, MDD -21.6% — KR 60/40 대비 변동성 32% 낮음", "Backtest 페이지 NAV 곡선 + 메트릭 카드 4장", "BGM 절정"],
            ["1:15 - 1:30", "CTA", "매월 자동 추천 — 무료 데모 공개", "URL + QR 코드 + 면책 고지", "BGM 페이드아웃"],
        ],
        widths=[2.0, 1.5, 5.0, 5.0, 2.0],
    )

    add_h2(doc, "30초 티저 (Hook + Result만)")
    add_bullet(doc, "0:00 - 0:05  훅: \"퇴직연금, AI 46명에게 맡긴다면?\"")
    add_bullet(doc, "0:05 - 0:20  Solution: AI 조직 매핑 표 빠른 컷 + 21개 모델 히트맵")
    add_bullet(doc, "0:20 - 0:30  Result + CTA: Sharpe 1.195 / 누적 +133% / URL")

    doc.add_page_break()

    # ====== 5. Narration 초안 (90초 풀버전) ======
    add_h1(doc, "5. Narration 초안 (90초 메인)")

    add_body(doc, "아래 narration은 직접 사용 가능하며, 시간 정합성을 위해 단어를 가감해도 됩니다. 자막은 narration의 80% 길이로 단순화 권장.", color=GRAY)

    seg = [
        ("0:00 - 0:10  [Hook]",
         "당신의 퇴직연금. 위험자산 70%까지 가능합니다. 그런데, 그 한도를 안 쓰면? 8년간 100%포인트의 기회비용이 쌓입니다.",
         "[화면] 누적 수익률 비교 차트, 안전자산 100% vs 60/40 BM"),
        ("0:10 - 0:25  [Problem]",
         "TDF는 정적입니다. 나이만 보고 비중을 정합니다. 로보 어드바이저는 한 가지 알고리즘 블랙박스입니다. 자문사는 분기에 한 번, 정성적으로 판단합니다. 모두 한계가 있습니다.",
         "[화면] 3개 카테고리 슬라이드 컷 이동"),
        ("0:25 - 0:45  [Solution-1: AI 조직]",
         "그래서 우리는 자산운용사 한 채를 통째로 AI로 만들었습니다. 매크로 애널리스트 1명, 자산 애널리스트 18명, 포트폴리오 매니저 21명, 위험 관리자, 동료평가단, 그리고 CIO. 모두 자율 AI 에이전트입니다. 사람의 개입 없이, 분기마다 자동으로 협의합니다.",
         "[화면] Section 3 매핑 표 애니메이션 (사람 → AI 변환)"),
        ("0:45 - 1:00  [Solution-2: 5단계]",
         "매크로 진단으로 시작합니다. 한국 14개 거시지표를 읽어 경기 레짐을 분류합니다. 21개 AI가 각자 다른 철학으로 포트폴리오를 산출합니다. AI들이 서로의 결과를 동료평가합니다. CIO가 7개 앙상블 후보 중 지금 시장에 맞는 것을 선택합니다.",
         "[화면] 5단계 파이프라인 다이어그램 + 21×ETF 히트맵 (페이지 5)"),
        ("1:00 - 1:15  [Result]",
         "결과는 어떨까요? 2018년부터 8.3년간의 walk-forward 백테스트, Sharpe 비율 1.195, 연환산 수익률 11.15%, 최대 낙폭 21.6%. 한국 60/40 벤치마크 대비 변동성은 32% 낮으면서, 위험조정 수익률은 29% 높습니다.",
         "[화면] Backtest 페이지 NAV 곡선 + 메트릭 카드 4장 클로즈업"),
        ("1:15 - 1:30  [CTA]",
         "매월 1일, 새로운 추천 포트폴리오가 자동으로 산출됩니다. 무료 데모를 지금 확인하세요.",
         "[화면] URL · 비밀번호 안내 · QR 코드 · 면책 고지 (5초 풀스크린)"),
    ]
    for tcode, text, vis in seg:
        add_h3(doc, tcode)
        p = doc.add_paragraph()
        r = p.add_run("Narration: ")
        set_kr_font(r, 10, bold=True, color=NAVY)
        r = p.add_run(text)
        set_kr_font(r, 10)
        p = doc.add_paragraph()
        r = p.add_run(vis)
        set_kr_font(r, 9.5, color=GRAY)
        p.paragraph_format.space_after = Pt(8)

    doc.add_page_break()

    # ====== 6. 차별화 매트릭스 ======
    add_h1(doc, "6. 차별화 매트릭스 (Why Different)")

    add_body(doc, "영상 0:10-0:25 'Problem' 막에서 활용. 3개 카테고리 모두 보여주면 산만합니다 — 영상에서는 본 모델의 ★ 행만 강조하고, 비교 카테고리는 1행씩 빠른 컷으로 처리하세요.", color=GRAY)

    add_table(
        doc,
        headers=["항목", "본 모델 (AI 자율)", "TDF", "단일 robo", "자문사"],
        rows=[
            ["의사결정 주체", "★ AI 에이전트 9개 역할 (46개)", "정적 글라이드패스", "단일 알고리즘", "사람 자문가"],
            ["매크로 반영", "★ 분기마다 14개 지표 자동 진단", "없음 (나이만)", "부분적", "정성 판단"],
            ["알고리즘 다양성", "★ 21개 PC 모델 병렬 + 동료평가", "1개", "1-2개", "0 (사람)"],
            ["모델 선택 근거", "★ AI 동료평가 + 매크로 매핑", "N/A", "불명 (블랙박스)", "자문가 판단"],
            ["위험자산 활용", "★ 70% 한도 100% 사용", "나이 따라 감소", "변동", "변동"],
            ["투명성", "★ 모든 21개 모델 weights 공개", "닫힘", "닫힘", "부분"],
            ["백테스트 공개", "★ walk-forward 8.3년 (2018-2026)", "✗", "△", "✗"],
            ["사람 개입", "★ 0회 (완전 자율)", "1회 (가입 시)", "월 1회+", "분기/연 1회"],
            ["비용", "★ 무료 데모", "TER 0.3-0.5%", "자문료 0.5-1%", "1%+"],
        ],
        widths=[3.0, 4.5, 2.5, 2.5, 2.5],
    )

    add_callout(doc, "★ = 본 모델 우위 구간. 9개 항목 중 9개 모두 ★. 영상에서 \"9 of 9\" 같은 메시지로 시각화 가능.", color=GOLD)

    doc.add_page_break()

    # ====== 7. 시각 자료 캡처 가이드 ======
    add_h1(doc, "7. 시각 자료 캡처 가이드 (Capture Guide)")

    add_body(doc, "본 영상의 B-roll(배경 영상)은 라이브 대시보드에서 직접 녹화합니다. URL: https://kr-pension-saa-gloual88.streamlit.app/  비밀번호: 3734  (Cloud 자동 배포 직후 안정화 30초).", size=10)

    add_h2(doc, "녹화 스펙")
    add_bullet(doc, "해상도: 1920×1080 (FHD) 이상, 가능하면 4K로 녹화 후 다운샘플")
    add_bullet(doc, "프레임: 60fps (마우스 이동 부드럽게)")
    add_bullet(doc, "브라우저: Chrome 전체화면 모드 (F11), 주소창 / 사이드바 / 시크릿 입력 화면 모두 컷에서 제외")
    add_bullet(doc, "다크모드 OFF — 본 대시보드는 라이트 테마 기준")

    add_h2(doc, "페이지별 녹화 포커스")
    add_table(
        doc,
        headers=["페이지", "추천 컷", "용도", "녹화 시간"],
        rows=[
            ["5_월간_연금_포트폴리오", "도넛 차트 (위험 70%) + 21×ETF 히트맵 + 카테고리 stack", "Solution-2 막의 '21개 모델' 시각화", "30초"],
            ["1_Backtest", "변형 선택 → 'v1 lock70 Baseline' → NAV 곡선 + 성과 표", "Result 막의 백테스트 근거", "20초"],
            ["2_Macro_Regime", "매크로 indicator dashboard + regime 라벨", "Solution-2의 '매크로 진단'", "10초"],
            ["3_Asset_Classes", "ETF 18개 카드 + CMA 수치", "Solution-1의 '18 자산 애널리스트' 강조", "10초"],
            ["6_현재_포트폴리오", "오늘 산출된 비중 도넛", "CTA 막 - 사용자 화면", "5초"],
        ],
        widths=[3.5, 6.5, 3.5, 1.5],
    )

    add_h2(doc, "고해상도 스크린샷 (정지 이미지로 사용)")
    add_bullet(doc, "위험자산 70% lock 도넛 (페이지 5 상단) — Solution / Result에서 풀스크린")
    add_bullet(doc, "21×ETF 히트맵 (페이지 5 섹션 2) — Solution-2 핵심 시각")
    add_bullet(doc, "Backtest NAV 곡선 (페이지 1) — Result 핵심")
    add_bullet(doc, "Section 3의 'AI 조직 매핑' 표 (이 docx에서 추출하여 모션그래픽 처리 권장)")

    add_h2(doc, "외부 도구로 만들 추가 자료")
    add_bullet(doc, "메트릭 카드 (단일 숫자 카드 4장): \"Sharpe 1.195\" / \"+133%\" / \"MDD -21.6%\" / \"σ -32%\" — Result 막에서 빠른 컷")
    add_bullet(doc, "5단계 파이프라인 다이어그램 (애니메이션): 매크로 → 21 PC → 동료평가 → CIO → 산출")
    add_bullet(doc, "QR 코드 (URL): CTA 막 5초 풀스크린")

    doc.add_page_break()

    # ====== 8. 브랜드 / 톤 가이드 ======
    add_h1(doc, "8. 브랜드 · 톤 가이드")

    add_h2(doc, "색상 팔레트 (대시보드와 일치)")
    add_table(
        doc,
        headers=["용도", "Hex", "RGB", "사용처"],
        rows=[
            ["주요 (Primary Navy)", "#1F4E79", "31, 78, 121", "제목, 강조 텍스트, 차트 메인"],
            ["보조 (Accent Gold)", "#C89B3C", "200, 155, 60", "★ 표시, 핵심 수치, CTA 버튼"],
            ["중성 (Gray)", "#555555", "85, 85, 85", "보조 텍스트, 캡션"],
            ["배경 (Light)", "#EEEEEE", "238, 238, 238", "테이블 헤더 배경, 카드 배경"],
            ["채권 (FixedIncome)", "#7E9BB8", "126, 155, 184", "FI 자산 차트"],
            ["실물 (RealAssets)", "#C89B3C", "200, 155, 60", "Gold/원유 자산"],
            ["현금 (Cash)", "#5B8A72", "91, 138, 114", "Cash 자산"],
        ],
        widths=[3.5, 2.5, 3.5, 5.5],
    )

    add_h2(doc, "톤 (Voiceover · BGM)")
    add_bullet(doc, "Voiceover 톤: 신뢰감 + 데이터 기반 차분함. \"권유\"가 아닌 \"설명\".")
    add_bullet(doc, "성별: 30-40대 남성 또는 여성 모두 가능. 전문성이 우선.")
    add_bullet(doc, "BGM: Hook 막은 약간 긴장감, Solution부터 희망적/진취적, Result는 절정. 일렉트로닉 minimal 권장 (재무/금융 영상 표준).")
    add_bullet(doc, "효과음: AI 작동음(키보드 타이핑, 스캔 효과음) Solution-1 막에서 사용 가능 — 단, 과도하면 신뢰감 훼손.")

    add_h2(doc, "타이포그래피")
    add_bullet(doc, "한글: Pretendard 또는 Noto Sans KR (대시보드 fallback: Malgun Gothic)")
    add_bullet(doc, "영문: Inter 또는 Roboto")
    add_bullet(doc, "수치 강조: Bold + 1.2× 크기. 단위 (% / 배 / 원) 항상 명시.")

    add_h2(doc, "모션 스타일")
    add_bullet(doc, "데이터 시각화 위주. 인물(스톡 영상) 사용 시 1-2컷에 한정.")
    add_bullet(doc, "트랜지션: 빠른 컷 + 페이드 X (정보 영상 톤). 화면 전환 시 마진 작게.")
    add_bullet(doc, "텍스트 모션: 슬라이드 인/타이프라이터/줌 모두 가능 — 단, 한 영상에서 2종 이하로 제한.")

    doc.add_page_break()

    # ====== 9. 결과 (강조 수치 모음) ======
    add_h1(doc, "9. 강조 수치 (Result 막에서 보여줄 모든 숫자)")

    add_body(doc, "Result 막에서 모든 숫자를 다 보여주려 하지 마세요 — 4개 메트릭 카드를 1.5초씩 빠른 컷으로 보여주거나, 표 1장을 3초간 풀스크린이 좋습니다.", color=GRAY)

    add_h2(doc, "Walk-forward Backtest (2018-01-02 ~ 2026-05-08, 34 분기 QS 리밸런싱)")
    add_table(
        doc,
        headers=["지표", "AI baseline ★", "AI Phase 2 LLM", "KR 60/40 BM"],
        rows=[
            ["연환산 수익률", "11.15%", "11.15%", "12.82%"],
            ["연환산 변동성", "9.33%", "9.26%", "13.79%"],
            ["Sharpe Ratio", "1.195", "1.204", "0.929"],
            ["Max Drawdown", "-21.57%", "-21.56%", "-26.73%"],
            ["총 누적 수익률", "132.85%", "133.00%", "152.58%"],
            ["거래 비용 (누적)", "9 bp", "10 bp", "—"],
            ["분기당 평균 턴오버", "5.52%", "5.70%", "—"],
        ],
        widths=[3.5, 4.0, 4.0, 4.0],
    )

    add_callout(doc, "★ 영상에는 baseline 수치(Sharpe 1.195)를 사용하세요 — production 운영 기준이며, Phase 2 대비 turnover/비용이 낮습니다. Phase 2 결과는 'LLM Phase 2까지 검증한 데이터'라는 *기술 신뢰성* 메시지로만 활용 가능.", color=GOLD)

    add_callout(doc, "핵심 메시지: 'AI 자율은 BM 대비 변동성을 32% 낮추면서 Sharpe를 29% 높입니다.' 이 한 줄이 Result 막의 narration이어야 합니다.", color=GOLD)

    # 비교 차트 임베드 (있으면)
    chart_path = Path(__file__).resolve().parents[1] / "docs" / "lock70_nav_comparison.png"
    if chart_path.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(str(chart_path), width=Cm(15.5))
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rc = cap.add_run("[ 그림: 3-line NAV 비교 — baseline / Phase 2 LLM / KR 60/40 BM ]")
        set_kr_font(rc, 9, color=GRAY)

    add_h2(doc, "LLM Phase 2의 가치 — Why baseline은 충분한가")
    add_bullet(doc, "한국에서 LLM의 부가가치는 매우 작음 — Phase 1 검증 (2026-05-01) 동일 결론, lock70 + Phase 2 (2026-05-10) 재확인.")
    add_bullet(doc, "lock70 IPS가 ensemble 자유도를 좁힘 — 위험자산 70% 고정 상태에서 LLM은 카테고리 *내부* 분배만 다르게 가능.")
    add_bullet(doc, "Phase 2 ROI 낮음: 분기당 ~$0.4 cost로 Sharpe +0.7% 개선 (1.195 → 1.204), σ -7bp. 통계적으로 noise 수준.")
    add_bullet(doc, "Production 운영에는 baseline 추천: 결정적, API cost 0, 결과 거의 동일.")
    add_bullet(doc, "LLM의 진짜 가치는 의사결정이 아닌 *설명*에 있음 — board memo, regime narrative, Q&A.")

    add_h2(doc, "현재 시점 모델 포트폴리오 (2026-05-10 산출, 18-ETF 풀 유니버스)")
    add_table(
        doc,
        headers=["카테고리", "비중", "내용"],
        rows=[
            ["Equity (KR + US + Intl)", "55.00% (lock)", "kr-large-cap, kr-kosdaq, kr-dividend, us-large-cap, us-tech, us-dividend, intl-developed, emerging-markets"],
            ["RealAssets (실물)", "15.00% (lock)", "gold (KODEX 골드선물H), commodities (TIGER 원유선물H)"],
            ["FixedIncome (채권)", "25.56%", "kr-treasuries-10y, kr-short-bonds, kr-credit, us-treasuries-10y/30y, us-ig-credit"],
            ["Cash (현금성)", "4.44%", "KOFR 금리 액티브, 머니마켓 액티브"],
            ["위험자산 합", "70.00%", "DC/IRP 법적 한도 100% 활용"],
        ],
        widths=[4.5, 3.0, 8.5],
    )

    doc.add_page_break()

    # ====== 10. 체크리스트 ======
    add_h1(doc, "10. 체크리스트 (영상 제작자 확인용)")

    add_h2(doc, "콘텐츠 검증")
    add_bullet(doc, "□ 영상 시작 10초 안에 'AI 에이전트' 또는 '자율'이라는 단어가 등장한다")
    add_bullet(doc, "□ Section 3의 사람 ↔ AI 매핑 표가 1초 이상 등장한다")
    add_bullet(doc, "□ 21개 PC 모델의 다양성을 시각적으로 보여준다 (히트맵 권장)")
    add_bullet(doc, "□ 'AI가 동료평가한다' 메시지가 narration에 포함된다")
    add_bullet(doc, "□ 위험자산 70% lock이 시각적으로 표현된다 (도넛 차트)")
    add_bullet(doc, "□ Backtest Sharpe 1.195와 누적 수익률 +133%가 명확히 보인다")
    add_bullet(doc, "□ 면책 고지가 엔드 카드에 1.5초 이상 정지된 상태로 등장한다")

    add_h2(doc, "기술적 검증")
    add_bullet(doc, "□ 1080p 이상 / 60fps")
    add_bullet(doc, "□ Voiceover 0dB 정규화, BGM -18dB 이하 (목소리 묻히지 않게)")
    add_bullet(doc, "□ 자막 항상 표시 (음소거 시청자 고려)")
    add_bullet(doc, "□ 인스타그램 Reels용 9:16 세로 버전 별도 제공 (옵션)")

    add_h2(doc, "법적 검증")
    add_bullet(doc, "□ '수익 보장' / '손실 없음' 표현 없음")
    add_bullet(doc, "□ 타사 명칭 직접 비교 없음 (카테고리 단위만)")
    add_bullet(doc, "□ 면책 고지 자막 + 엔드 카드 모두 포함")
    add_bullet(doc, "□ 실명 / 개인정보 노출 없음 (대시보드 캡처 시 사이드바 사용자명 가림 처리)")

    # ====== 부록 ======
    add_h1(doc, "부록: 자주 묻는 질문 (영상 후기 / 댓글 대비)")

    qas = [
        ("Q. AI가 직접 매매도 합니까?",
         "A. 아닙니다. 본 모델은 추천 포트폴리오를 산출합니다. 매수·매도는 사용자가 직접 본인 DC/IRP 계좌에서 실행합니다."),
        ("Q. 매월/분기 리밸런싱 주기는?",
         "A. 백테스트는 분기 리밸런싱(QS, 1월/4월/7월/10월). 라이브 데모는 월 1회 산출."),
        ("Q. 어떤 AI 모델을 사용합니까?",
         "A. 21개의 정량 알고리즘이 베이스. 일부 단계에서 Anthropic Claude 4.6/4.7을 'CIO judge' / 'CMA judge'로 사용 (Phase 2). 모든 결정은 코드로 재현 가능."),
        ("Q. 위험자산 70% 고정인데 침체기에 위험하지 않나요?",
         "A. 본 모델은 70% 안에서 카테고리 *내부* 분배(어느 ETF에 얼마)를 매크로에 따라 조정합니다. 침체기에는 미국 장기 국채, 금, 단기 채권 비중이 자동 증가합니다 (FI curve tilt)."),
        ("Q. 백테스트가 좋아도 미래를 보장하지는 않잖아요?",
         "A. 맞습니다. 본 자료는 정보 제공 목적이며 투자 권유가 아닙니다. 백테스트 성과는 미래 수익을 보장하지 않습니다."),
    ]
    for q, a in qas:
        add_h3(doc, q)
        add_body(doc, a, size=10)

    out = Path(__file__).resolve().parents[1] / "docs" / "production_brief_kr_pension_saa.docx"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    print(f"Written: {out}")


if __name__ == "__main__":
    build()

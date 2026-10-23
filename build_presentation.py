"""Generates high-fidelity 16-slide Presentation in both PDF and PPTX formats.

Adheres strictly to classic executive/academic styling:
- 16:9 Widescreen aspect ratio (720pt x 405pt)
- Oxford Navy (#1B365D) top header band with Gold (#C5A059) accent rule
- Structured two-column cards, parameter tables, mathematical equations, and flowcharts
- Detailed coverage of Devos et al. (2018) methodology, sensors, RNN, plasticity, Arduino SITL, and 13 scenarios.
"""

import os
import sys
from reportlab.lib.pagesizes import landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# 16:9 Slide Dimensions
SLIDE_WIDTH = 720.0   # 10 inches
SLIDE_HEIGHT = 405.0  # 5.625 inches

NAVY = colors.HexColor("#1B365D")
GOLD = colors.HexColor("#C5A059")
DARK_SLATE = colors.HexColor("#0F172A")
BODY_SLATE = colors.HexColor("#334155")
MUTED_SLATE = colors.HexColor("#64748B")
BG_CARD = colors.HexColor("#F8FAFC")
BORDER_CARD = colors.HexColor("#CBD5E1")
EMERALD = colors.HexColor("#047857")
AMBER = colors.HexColor("#B45309")
LIGHT_BLUE = colors.HexColor("#EFF6FF")
WHITE = colors.white

PPT_NAVY = RGBColor(0x1B, 0x36, 0x5D)
PPT_GOLD = RGBColor(0xC5, 0xA0, 0x59)
PPT_DARK = RGBColor(0x0F, 0x17, 0x2A)
PPT_MUTED = RGBColor(0x64, 0x74, 0x8B)
PPT_CARD = RGBColor(0xF8, 0xFA, 0xFC)
PPT_BORDER = RGBColor(0xCB, 0xD5, 0xE1)
PPT_WHITE = RGBColor(0xFF, 0xFF, 0xFF)


class NumberedCanvas(canvas.Canvas):
    """Draws slide backgrounds, header bars, gold accents, and running footers."""
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
            self.draw_slide_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_slide_decorations(self, total_pages):
        page_num = self._pageNumber
        w, h = SLIDE_WIDTH, SLIDE_HEIGHT

        if page_num == 1:
            # Title slide background: Dark Oxford Navy with Gold accents
            self.setFillColor(NAVY)
            self.rect(0, 0, w, h, fill=1, stroke=0)
            self.setFillColor(GOLD)
            self.rect(0, h - 8, w, 8, fill=1, stroke=0)
            self.rect(0, 0, w, 8, fill=1, stroke=0)
            # Subtle accent line
            self.setStrokeColor(GOLD)
            self.setLineWidth(1.5)
            self.line(40, 110, w - 40, 110)
            return

        # Normal Slide Header
        self.setFillColor(NAVY)
        self.rect(0, h - 50, w, 50, fill=1, stroke=0)
        self.setFillColor(GOLD)
        self.rect(0, h - 53, w, 3, fill=1, stroke=0)

        # Slide Footer
        self.setStrokeColor(BORDER_CARD)
        self.setLineWidth(0.75)
        self.line(30, 24, w - 30, 24)

        self.setFont("Helvetica", 7.5)
        self.setFillColor(MUTED_SLATE)
        self.drawString(32, 14, "Autonomous Quadcopter Obstacle Avoidance Simulation  |  Devos et al. (2018) IEEE DSD")
        page_str = f"Slide {page_num} of {total_pages}"
        self.drawRightString(w - 32, 14, page_str)


def create_pdf_presentation(output_pdf_path: str):
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=(SLIDE_WIDTH, SLIDE_HEIGHT),
        leftMargin=32,
        rightMargin=32,
        topMargin=58,
        bottomMargin=28,
    )

    styles = getSampleStyleSheet()

    title_main = ParagraphStyle(
        'TitleMain',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=25,
        textColor=WHITE,
        alignment=1,
        spaceAfter=10
    )
    title_sub = ParagraphStyle(
        'TitleSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=GOLD,
        alignment=1,
        spaceAfter=18
    )
    title_meta = ParagraphStyle(
        'TitleMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#E2E8F0"),
        alignment=1
    )

    header_cat = ParagraphStyle(
        'HeaderCat',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9,
        textColor=GOLD,
        textTransform='uppercase'
    )
    header_title = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13.5,
        leading=16.5,
        textColor=WHITE
    )

    card_title = ParagraphStyle(
        'CardTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11.5,
        textColor=NAVY,
        spaceAfter=4
    )
    body_text = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.8,
        textColor=BODY_SLATE
    )
    body_bold = ParagraphStyle(
        'BodyBoldCustom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9.8,
        textColor=DARK_SLATE
    )
    formula_style = ParagraphStyle(
        'FormulaStyle',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=7.8,
        leading=10.5,
        textColor=NAVY,
        alignment=1
    )
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.1,
        leading=9.6,
        textColor=BODY_SLATE,
        leftIndent=7,
        firstLineIndent=-7,
        spaceAfter=2
    )

    story = []

    def slide_header(category: str, title: str):
        p_cat = Paragraph(category, header_cat)
        p_title = Paragraph(title, header_title)
        return Table([[p_cat], [p_title]], colWidths=[SLIDE_WIDTH - 64], style=[
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ])

    def card(title: str, content_flowables: list, width: float, bg=BG_CARD):
        items = [Paragraph(title, card_title)] + content_flowables
        t = Table([[items]], colWidths=[width], style=[
            ('BACKGROUND', (0,0), (-1,-1), bg),
            ('BOX', (0,0), (-1,-1), 0.75, BORDER_CARD),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ])
        return t

    # SLIDE 1: Title
    story.append(Spacer(1, 40))
    story.append(Paragraph("AERODRONE AI // AUTONOMOUS QUADCOPTER SIMULATION", title_main))
    story.append(Paragraph("Adaptive Neural Obstacle Avoidance with Synaptic Plasticity & Arduino Flight Control", title_sub))
    story.append(Spacer(1, 25))
    story.append(Paragraph(
        "<b>Based on IEEE Research:</b> Arne Devos, Emad Ebeid, Poramate Manoonpong (2018)<br/>"
        "<i>'Development of Autonomous Drones for Adaptive Obstacle Avoidance in Real World Environments'</i><br/>"
        "21st Euromicro Conference on Digital System Design (DSD), DOI: 10.1109/DSD.2018.00009<br/>"
        "<b>Theoretical Foundation:</b> Pedersen & Manoonpong (2018), LNAI (Two-Neuron RNN & Synaptic Plasticity)<br/>"
        "<b>Implementation:</b> 3D WebGL Simulation, 6-DOF Physics, Arduino C++ HITL Firmware, Human-in-the-Loop Decision Gate",
        title_meta
    ))
    story.append(PageBreak())

    # SLIDE 2: Executive Summary & Problem
    story.append(Spacer(1, -26))
    story.append(slide_header("Project Motivation & Problem Definition", "The Autonomous Drone Navigation Dilemma in Unknown Spaces"))
    story.append(Spacer(1, 12))
    col1 = [
        Paragraph("<b>The Operational Challenge:</b>", body_bold),
        Paragraph("• Quadcopters operating in GPS-denied, cluttered surroundings (structural inspections, disaster search & rescue) must navigate autonomously without human pilots.", bullet_style),
        Paragraph("• Environments contain unmapped obstacles, narrow passages, sharp corners, and dead-ends.", bullet_style),
        Paragraph("• Traditional solutions employ <b>Computer Vision (Visual SLAM, optical flow, deep CNNs)</b> or multi-beam spinning LiDARs.", bullet_style),
        Paragraph("<b>Limitations of Conventional Vision & SLAM:</b>", body_bold),
        Paragraph("• Heavy computational and memory footprint requiring heavy GPUs/SBCs.", bullet_style),
        Paragraph("• Excessive electrical power consumption severely degrading flight endurance.", bullet_style),
        Paragraph("• Complex SLAM map generation fails in featureless or reflective corridors.", bullet_style),
    ]
    col2 = [
        Paragraph("<b>The Bio-Inspired Neural Paradigm:</b>", body_bold),
        Paragraph("• Inspired by insect reactive navigation, this research replaces heavy vision pipelines with an ultra-lightweight <b>two-neuron recurrent neural network (RNN)</b>.", bullet_style),
        Paragraph("• Operates on <b>only two lightweight, narrow-beam (2°) LiDAR sensors</b> mounted at the front of the drone frame.", bullet_style),
        Paragraph("• <b>Short-Term Memory (STM):</b> Retains turning direction even after obstacles leave the narrow LiDAR field of view.", bullet_style),
        Paragraph("• <b>Synaptic Plasticity:</b> Dynamically modulates recurrent weights online to escape corners and deadlocks without global mapping.", bullet_style),
        Paragraph("<b>Simulation Platform Objective:</b>", body_bold),
        Paragraph("• Build an interactive 3D simulation with full 6-DOF physics, an Arduino C++ flight control interface, a Human-in-the-Loop decision gate, and automated telemetry evaluation.", bullet_style),
    ]
    t2 = Table([[card("THE PROBLEM: VISION & SLAM COMPLEXITY", col1, 320), card("THE SOLUTION: ADAPTIVE NEURAL CONTROL", col2, 320)]], colWidths=[328, 328])
    t2.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t2)
    story.append(PageBreak())

    # SLIDE 3: Base Paper Methodology & System Overview
    story.append(Spacer(1, -26))
    story.append(slide_header("Base Paper Methodology", "Closed-Loop Neural Control Architecture (Devos et al. 2018)"))
    story.append(Spacer(1, 12))
    col3_1 = [
        Paragraph("<b>Published Research Citation:</b>", body_bold),
        Paragraph("Arne Devos (KU Leuven), Emad Ebeid (SDU UAS Center), Poramate Manoonpong (Embodied AI & Neurorobotics Lab, SDU), <i>IEEE 21st Euromicro DSD 2018</i>, pp. 707–710.", body_text),
        Paragraph("<b>Closed-Loop Flight Architecture:</b>", body_bold),
        Paragraph("1. <b>Physical Sensing:</b> Two Garmin LIDAR-Lite v3 sensors measure obstacle range at 50 Hz.", bullet_style),
        Paragraph("2. <b>Sensory Normalization:</b> Distance mapped non-linearly to discrete [-1.0, +1.0] interval.", bullet_style),
        Paragraph("3. <b>Recurrent Controller:</b> 2-neuron discrete-time neural network computes activations O1, O2.", bullet_style),
        Paragraph("4. <b>Synaptic Plasticity:</b> Correlation learning updates weights bi, qi in real-time.", bullet_style),
        Paragraph("5. <b>Steering Generation:</b> Yaw velocity commanded to flight controller via MAVLink / serial link.", bullet_style),
        Paragraph("6. <b>Actuation:</b> Pixhawk / Arduino commands 4-channel ESC PWM motor thrusts.", bullet_style),
    ]
    col3_2 = [
        Paragraph("<b>Hardware & Software Stack from Base Paper:</b>", body_bold),
        Table([
            [Paragraph("<b>Component</b>", body_bold), Paragraph("<b>Paper Specification</b>", body_bold), Paragraph("<b>Role / Purpose</b>", body_bold)],
            [Paragraph("Frame", body_text), Paragraph("Tarot 650 Sport (Carbon)", body_text), Paragraph("Rigid quadcopter frame", body_text)],
            [Paragraph("Propulsion", body_text), Paragraph("370 KV + 14\" Props + 40A ESC", body_text), Paragraph("High-efficiency thrust", body_text)],
            [Paragraph("Battery", body_text), Paragraph("6S 22.2V 8000 mAh LiPo", body_text), Paragraph("25-minute flight endurance", body_text)],
            [Paragraph("Autopilot", body_text), Paragraph("PIXHAWK 2", body_text), Paragraph("Attitude IMU & PID loop", body_text)],
            [Paragraph("Companion SBC", body_text), Paragraph("Raspberry Pi Zero", body_text), Paragraph("Executes Python RNN loop", body_text)],
            [Paragraph("Sensors", body_text), Paragraph("2x Garmin LIDAR-Lite v3", body_text), Paragraph("I2C narrow 2° distance beam", body_text)],
            [Paragraph("Protocol", body_text), Paragraph("MAVLink / MAVProxy / DroneKit", body_text), Paragraph("UART serial command bridge", body_text)],
        ], colWidths=[65, 115, 120], style=[
            ('BACKGROUND', (0,0), (-1,0), LIGHT_BLUE),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_CARD),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ])
    ]
    t3 = Table([[card("METHODOLOGY & CLOSED-LOOP FLOW", col3_1, 320), card("PHYSICAL HARDWARE SPECIFICATIONS", col3_2, 320)]], colWidths=[328, 328])
    t3.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t3)
    story.append(PageBreak())

    # SLIDE 4: Mathematical Modeling — Sensor Geometry
    story.append(Spacer(1, -26))
    story.append(slide_header("Mathematical Foundations", "LiDAR Geometry & Minimum Detectable Obstacle Width"))
    story.append(Spacer(1, 12))
    col4_1 = [
        Paragraph("<b>Equation (1) Derivation (Devos et al. 2018):</b>", body_bold),
        Paragraph("To guarantee that a quadcopter turning at distance Lx does not collide with obstacles using its rotor tips, the minimum detectable obstacle width <i>W_obj</i> is governed by:", body_text),
        Spacer(1, 3),
        Paragraph("<b>W_obj ≥ 2 · tan(Θ / 2) · [ Lx + (Ld / 2) ]</b>", formula_style),
        Spacer(1, 3),
        Paragraph("<b>Geometric Parameter Definitions:</b>", body_bold),
        Paragraph("• <b>Θ (LiDAR Separation Angle):</b> 40° total angular separation (±20° relative to forward axis).", bullet_style),
        Paragraph("• <b>Lx (Safe Turning Distance):</b> 0.15 m (15 cm) distance at which evasion turn begins.", bullet_style),
        Paragraph("• <b>Ld (Quadcopter Frame Width):</b> 0.34 m (34 cm) motor-to-motor arm span.", bullet_style),
        Paragraph("• <b>Lm (Rotor Clearance Margin):</b> 0.06 m (6 cm) safety buffer for propeller tips.", bullet_style),
        Paragraph("• <b>Ls (Maximum LiDAR Range):</b> 0.50 m (50 cm) active sensing horizon.", bullet_style),
    ]
    col4_2 = [
        Paragraph("<b>Analytical Evaluation & Safety Bound:</b>", body_bold),
        Paragraph("Substituting the base paper experimental parameters into Equation (1):", body_text),
        Spacer(1, 2),
        Paragraph("Θ / 2 = 20°  ==>  tan(20°) ≈ 0.36397", body_text),
        Paragraph("Lx + (Ld / 2) = 0.15 m + 0.17 m = 0.32 m", body_text),
        Paragraph("<b>W_obj ≥ 2 · 0.36397 · 0.32 m = 0.2329 m ≈ 24 cm</b>", formula_style),
        Spacer(1, 3),
        Paragraph("<b>Engineering Implications:</b>", body_bold),
        Paragraph("• Any obstacle with cross-section <b>≥ 24 cm</b> will reliably intercept at least one LiDAR beam before the drone breaches the 15 cm critical threshold.", bullet_style),
        Paragraph("• Obstacles narrower than 24 cm could pass between the two beams if not angled; therefore, all obstacles in our scenarios have physical widths ≥ 24 cm.", bullet_style),
        Paragraph("• <b>Minimum Clearance Boundary:</b> Lm + (Ld / 2) = 0.06 + 0.17 = <b>0.23 m</b>. Any distance below 0.23 m constitutes a geometric rotor collision.", bullet_style),
    ]
    t4 = Table([[card("EQUATION (1) & GEOMETRIC FORMULATION", col4_1, 320), card("ANALYTICAL DERIVATION & SAFETY GUARANTEES", col4_2, 320)]], colWidths=[328, 328])
    t4.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t4)
    story.append(PageBreak())

    # SLIDE 5: Sensory Normalization
    story.append(Spacer(1, -26))
    story.append(slide_header("Sensory Processing Pipeline", "LiDAR Range Normalization & Sensory Input Mapping"))
    story.append(Spacer(1, 12))
    col5_1 = [
        Paragraph("<b>Raw LiDAR to Neural Input Transformation:</b>", body_bold),
        Paragraph("The raw distance measurements <i>d_L, d_R</i> from the dual front LiDAR sensors cannot be directly fed into neural activation functions. They must be normalized into continuous bipolar signals:", body_text),
        Spacer(1, 3),
        Paragraph("<b>S_i = clip( [ 2 · (d_max - d_i) / (d_max - d_min) ] - 1.0, -1.0, 1.0 )</b>", formula_style),
        Spacer(1, 3),
        Paragraph("Where <i>d_max = 0.50 m</i> (sensing horizon Ls) and <i>d_min = 0.15 m</i> (critical turning distance Lx).", body_text),
        Paragraph("<b>State Boundary Interpretations:</b>", body_bold),
        Paragraph("• <b>S_i = -1.0:</b> Free airspace. Obstacle distance <i>d_i ≥ 0.50 m</i>. Zero reflex excitation.", bullet_style),
        Paragraph("• <b>S_i = 0.0:</b> Transition boundary. Obstacle at <i>d_i = 0.325 m</i>. Reflex activates.", bullet_style),
        Paragraph("• <b>S_i = +1.0:</b> Critical proximity. Obstacle at <i>d_i ≤ 0.15 m</i>. Maximum turning drive.", bullet_style),
    ]
    col5_2 = [
        Paragraph("<b>Dual LiDAR Beam Geometry (Theta = 40°):</b>", body_bold),
        Paragraph("• <b>Left LiDAR (S_L):</b> Oriented at +20° azimuth relative to drone heading vector.", bullet_style),
        Paragraph("• <b>Right LiDAR (S_R):</b> Oriented at -20° azimuth relative to drone heading vector.", bullet_style),
        Paragraph("• <b>Viewing Angle:</b> 2° narrow laser cone minimizes ground and ceiling multipath reflections.", bullet_style),
        Paragraph("<b>Multi-Directional Range Array in Simulation:</b>", body_bold),
        Paragraph("While the base paper relies strictly on dual front LiDARs for 2D room navigation, this project enhances the spatial perception suite for full 3D research:", bullet_style),
        Paragraph("• <b>Planar 8-Beam Array:</b> Forward, Left, Right, Backward, Forward-Left, Forward-Right, Rear-Left, Rear-Right.", bullet_style),
        Paragraph("• <b>Vertical 2-Beam Array:</b> Upward ceiling laser + Downward ground altimeter laser.", bullet_style),
        Paragraph("• Feeds omnidirectional clearance telemetry directly to Human-in-the-Loop Decision Gate.", bullet_style),
    ]
    t5 = Table([[card("NORMALIZATION EQUATION & TRANSFER FUNCTION", col5_1, 320), card("DUAL SENSOR ARRANGEMENT & 3D EXPANSION", col5_2, 320)]], colWidths=[328, 328])
    t5.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t5)
    story.append(PageBreak())

    # SLIDE 6: Recurrent Neural Network
    story.append(Spacer(1, -26))
    story.append(slide_header("Bio-Inspired Neural Control", "Two-Neuron Recurrent Network with Mutual Inhibition"))
    story.append(Spacer(1, 12))
    col6_1 = [
        Paragraph("<b>Discrete-Time Non-Spiking Neural Dynamics:</b>", body_bold),
        Paragraph("The core controller (Pedersen & Manoonpong 2018) consists of two recurrently coupled neurons with hyperbolic tangent nonlinearities:", body_text),
        Spacer(1, 2),
        Paragraph("<b>O_1(t) = tanh( b_1(t)·O_1(t-1) + c(t)·O_2(t-1) + I_g·S_L(t) )</b>", formula_style),
        Paragraph("<b>O_2(t) = tanh( b_2(t)·O_2(t-1) + c(t)·O_1(t-1) + I_g·S_R(t) )</b>", formula_style),
        Spacer(1, 2),
        Paragraph("<b>Mathematical Terms & Roles:</b>", body_bold),
        Paragraph("• <b>O_1(t), O_2(t) ∈ (-1.0, 1.0):</b> Left and Right steering neuron activation states.", bullet_style),
        Paragraph("• <b>O_1(t-1), O_2(t-1):</b> Prior states acting as <b>Short-Term Memory (STM)</b>.", bullet_style),
        Paragraph("• <b>b_1, b_2 ∈ [0.1, 8.0]:</b> Self-excitatory recurrent synapses (baseline = 2.40). Sustains turning commands after sensor signal drops.", bullet_style),
        Paragraph("• <b>c(t) = -0.5 · [ q_1(t) + q_2(t) ]:</b> Mutual cross-inhibitory synaptic coupling (baseline = -3.50). Prevents contradictory turning.", bullet_style),
        Paragraph("• <b>I_g = 4.7:</b> Sensory input gain amplifying normalized LiDAR signals.", bullet_style),
    ]
    col6_2 = [
        Paragraph("<b>Winner-Take-All Directional Competition:</b>", body_bold),
        Paragraph("• When the quadcopter detects an obstacle on the left, <i>S_L</i> increases. Neuron 1 excites rapidly while cross-inhibiting Neuron 2 via <i>c(t)</i>.", bullet_style),
        Paragraph("• This causes <b>O_1 → +1.0</b> and <b>O_2 → -1.0</b>, creating an unequivocal steering command to the right.", bullet_style),
        Paragraph("• In head-on symmetry (both sensors stimulated equally), small numerical asymmetries or historical turning bias break symmetry instantly, avoiding stagnation.", bullet_style),
        Paragraph("<b>Comparison with Deep Neural Networks:</b>", body_bold),
        Paragraph("• <b>Parameters:</b> Only 4 adaptable synaptic weights vs millions in CNNs.", bullet_style),
        Paragraph("• <b>Compute:</b> Sub-microsecond execution time on low-cost Arduino / RPi Zero.", bullet_style),
        Paragraph("• <b>No Training Needed:</b> Operates online with closed-loop stability.", bullet_style),
    ]
    t6 = Table([[card("RECURRENT STATE UPDATE EQUATIONS", col6_1, 320), card("NEURAL COMPETITION & EFFICIENCY ADVANTAGES", col6_2, 320)]], colWidths=[328, 328])
    t6.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t6)
    story.append(PageBreak())

    # SLIDE 7: Synaptic Plasticity
    story.append(Spacer(1, -26))
    story.append(slide_header("Online Adaptation", "Correlation Plasticity & Synaptic Scaling for Deadlock Escape"))
    story.append(Spacer(1, 12))
    col7_1 = [
        Paragraph("<b>The Corner & Deadlock Failure Mode:</b>", body_bold),
        Paragraph("• When an autonomous drone enters a 90° corner or U-turn deadlock, it begins turning. Because LiDARs have narrow 2° beams, the wall leaves the sensor field of view before the turn finishes.", bullet_style),
        Paragraph("• Without plasticity, the drone stops turning too early, accelerates forward, and crashes into the adjacent wall.", bullet_style),
        Paragraph("<b>Correlation-Based Synaptic Plasticity Formulation:</b>", body_bold),
        Paragraph("Synaptic weights <i>b_i</i> (self-feedback) and <i>q_i</i> (inhibition) adapt dynamically using correlation learning (Pedersen & Manoonpong 2018):", body_text),
        Spacer(1, 2),
        Paragraph("v_i(t) = clip( [ O_i(t) + 1 ] / 2, 0.0, 1.0 )", formula_style),
        Paragraph("reflex_i(t) = 1.0 if S_i(t) > -0.5 else 0.0", formula_style),
        Paragraph("<b>Δb_i = κ·Δt · [ μ_b·v_i(t-1)·v_i(t)·reflex_i + γ_b·(k - v_i)·b_i² ]</b>", formula_style),
        Paragraph("<b>Δq_i = κ·Δt · [ μ_q·v_i(t-1)·v_i(t)·reflex_i + γ_q·(k - v_i)·q_i² ]</b>", formula_style),
    ]
    col7_2 = [
        Paragraph("<b>Plasticity Hyperparameters (Base Paper):</b>", body_bold),
        Paragraph("• <b>κ (Scaling rate):</b> 27.0 — Governs learning adaptation timescale.", bullet_style),
        Paragraph("• <b>μ_b, μ_q (Learning rates):</b> μ_b = 0.0065, μ_q = 0.015.", bullet_style),
        Paragraph("• <b>γ_b, γ_q (Decay rates):</b> γ_b = 0.0003, γ_q = 0.0003.", bullet_style),
        Paragraph("• <b>k (Target baseline):</b> -0.01 — Homeostatic resting point.", bullet_style),
        Paragraph("<b>Dual Mechanism Explanation:</b>", body_bold),
        Paragraph("1. <b>Hebbian-like Potentiation (1st term):</b> When obstacle reflex is active, consecutive neuron firing strengthens <i>b_i</i> and <i>q_i</i>, lengthening short-term memory persistence.", bullet_style),
        Paragraph("2. <b>Homeostatic Synaptic Scaling (2nd term):</b> When the drone escapes into open air, weights decay back to baseline resting states, preventing over-turning.", bullet_style),
        Paragraph("<b>Result:</b> 90% to 100% autonomous navigation success in tight deadlocks.", bullet_style),
    ]
    t7 = Table([[card("THE DEADLOCK PROBLEM & PLASTICITY EQUATIONS", col7_1, 320), card("HYPERPARAMETERS & DUAL-PHASE ADAPTATION", col7_2, 320)]], colWidths=[328, 328])
    t7.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t7)
    story.append(PageBreak())

    # SLIDE 8: Flight Steering & Velocity Laws
    story.append(Spacer(1, -26))
    story.append(slide_header("Flight Dynamics & Control", "Yaw Steering Calculation & Proximity Velocity Regulation"))
    story.append(Spacer(1, 12))
    col8_1 = [
        Paragraph("<b>Differential Yaw Steering Command:</b>", body_bold),
        Paragraph("The net steering angle command is derived from the difference between the two recurrent neuron outputs:", body_text),
        Spacer(1, 2),
        Paragraph("<b>steering(t) = 0.5 · [ O_1(t) - O_2(t) ]</b>", formula_style),
        Paragraph("<b>ψ̇_cmd(t) = -k_turn · steering(t)</b>", formula_style),
        Spacer(1, 2),
        Paragraph("Where <i>k_turn = 1.35 rad/s</i> (yaw rate gain).", body_text),
        Paragraph("<b>Directional Evasion Logic:</b>", body_bold),
        Paragraph("• <b>Left Obstacle (S_L > S_R):</b> O_1 > O_2 ==> steering > 0 ==> <b>ψ̇_cmd < 0 (Turn Right)</b>.", bullet_style),
        Paragraph("• <b>Right Obstacle (S_R > S_L):</b> O_2 > O_1 ==> steering < 0 ==> <b>ψ̇_cmd > 0 (Turn Left)</b>.", bullet_style),
        Paragraph("• <b>Symmetric Clear Flight:</b> O_1 ≈ O_2 ==> steering ≈ 0 ==> Straight cruise.", bullet_style),
    ]
    col8_2 = [
        Paragraph("<b>Adaptive Forward Cruise Velocity Throttling:</b>", body_bold),
        Paragraph("To guarantee that the quadcopter can safely negotiate turns within its turning radius, forward velocity <i>V_forward</i> throttles dynamically:", body_text),
        Spacer(1, 2),
        Paragraph("<b>V_forward = 0.00 m/s</b> if S_L > 0.55 and S_R > 0.55 (Deadlock)", body_bold),
        Paragraph("<b>V_forward = 0.025 m/s</b> if max(S_L, S_R) > 0.25 (Very Close)", body_text),
        Paragraph("<b>V_forward = 0.055 m/s</b> if max(S_L, S_R) > -0.15 (Approaching)", body_text),
        Paragraph("<b>V_forward = 0.10 m/s</b> otherwise (Nominal Cruise Speed)", body_text),
        Paragraph("<b>Pitch/Roll Feedforward Dynamics:</b>", body_bold),
        Paragraph("• 6-DOF physics engine couples forward speed to pitch tilt angle <i>θ ≈ atan(V_f / g)</i> and yaw rate to roll banked coordinated turns.", bullet_style),
        Paragraph("• Ensures realistic flight dynamics matching Tarot 650 physical inertia.", bullet_style),
    ]
    t8 = Table([[card("YAW RATE COMMAND GENERATION", col8_1, 320), card("VELOCITY REGULATION & FLIGHT DYNAMICS", col8_2, 320)]], colWidths=[328, 328])
    t8.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t8)
    story.append(PageBreak())

    # SLIDE 9: Hardware & Arduino
    story.append(Spacer(1, -26))
    story.append(slide_header("Embedded Hardware & Firmware", "Tarot 650 Quadcopter & Arduino Flight Controller Firmware"))
    story.append(Spacer(1, 12))
    col9_1 = [
        Paragraph("<b>Arduino Firmware (arduino_flight_controller.ino):</b>", body_bold),
        Paragraph("The project includes complete, production-ready C++ firmware for Arduino Mega 2560 / Uno / ESP32 platforms:", body_text),
        Paragraph("• <b>Pin Mappings:</b> 4-channel ESC PWM outputs (D5, D6, D9, D10) and ultrasonic/LiDAR trigger & echo pins.", bullet_style),
        Paragraph("• <b>Dual Range Sampling:</b> 50 Hz non-blocking distance acquisition matching Devos et al. timing.", bullet_style),
        Paragraph("• <b>Cascaded PID Control:</b> High-rate inner angular rate PID + outer attitude angle PID for Roll, Pitch, and Yaw.", bullet_style),
        Paragraph("• <b>ESC Motor Mixing:</b> X-quadcopter motor matrix translating throttle, roll, pitch, and yaw commands into individual motor RPMs.", bullet_style),
        Paragraph("• <b>Failsafe Protection:</b> Immediate motor cut-off on loss of serial heartbeat or emergency stop signal.", bullet_style),
    ]
    col9_2 = [
        Paragraph("<b>SITL & HITL Serial Bridge (serial_bridge.py):</b>", body_bold),
        Paragraph("• <b>Bidirectional ASCII Telemetry Protocol:</b> Transmits distance, orientation, and armed status strings (<i>$TELEM, dL, dR, roll, pitch, yaw</i>).", bullet_style),
        Paragraph("• <b>Auto-Detection:</b> Scans available COM ports for CH340, FTDI, or ATmega32u4 USB controllers.", bullet_style),
        Paragraph("• <b>Hardware-in-the-Loop (HITL):</b> When connected, the Arduino receives Python commands and actuates real motor PWMs.", bullet_style),
        Paragraph("• <b>Software-in-the-Loop (SITL):</b> If no physical hardware is plugged in, the system seamlessly simulates Arduino telemetry without errors.", bullet_style),
        Paragraph("<b>Physical Airframe Baseline:</b> Tarot 650 Sport, 370 KV motors, 14\" stiff carbon fiber propellers, 40A ESCs, 6S 22.2V 8000 mAh LiPo battery (25 min flight).", body_text),
    ]
    t9 = Table([[card("ARDUINO C++ FIRMWARE FEATURES", col9_1, 320), card("HITL/SITL SERIAL PROTOCOL & DUAL MODES", col9_2, 320)]], colWidths=[328, 328])
    t9.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t9)
    story.append(PageBreak())

    # SLIDE 10: HITL Workflow
    story.append(Spacer(1, -26))
    story.append(slide_header("Operator Interaction & Safety", "Human-in-the-Loop (HITL) Obstacle Avoidance Workflow"))
    story.append(Spacer(1, 12))
    col10_1 = [
        Paragraph("<b>Interactive Decision Philosophy:</b>", body_bold),
        Paragraph("Unlike black-box simulators that avoid automatically without user input, this simulation implements an explicit <b>Human-in-the-Loop Decision Gate</b>:", body_text),
        Paragraph("1. <b>Cruise:</b> Quadcopter advances forward at 0.10 m/s in steady hover.", bullet_style),
        Paragraph("2. <b>Detection:</b> Sensor detects obstacle within 0.50 m threshold.", bullet_style),
        Paragraph("3. <b>Simulation Pause:</b> The physics clock halts progression immediately.", bullet_style),
        Paragraph("4. <b>Safe Hover Hold:</b> Drone stabilizes in safe hover waiting for operator.", bullet_style),
        Paragraph("5. <b>Safety Audit:</b> Evaluates line-of-sight clearance across all 10 candidate directions against Equation (1) geometric clearance bounds.", bullet_style),
        Paragraph("6. <b>Operator Decision:</b> User selects evasion direction via UI or hotkeys.", bullet_style),
        Paragraph("7. <b>Execution & Logging:</b> Maneuver executes, trajectory updates in 3D, and trial metrics are permanently logged.", bullet_style),
    ]
    col10_2 = [
        Paragraph("<b>Direction Classification & Safety Criteria:</b>", body_bold),
        Table([
            [Paragraph("<b>Status</b>", body_bold), Paragraph("<b>Clearance</b>", body_bold), Paragraph("<b>System Behavior</b>", body_bold)],
            [Paragraph("<font color='#047857'><b>RECOMMENDED</b></font>", body_text), Paragraph("> 0.50 m", body_text), Paragraph("Optimal base-paper neural evasion direction", body_text)],
            [Paragraph("<font color='#047857'><b>SAFE</b></font>", body_text), Paragraph("> 0.50 m", body_text), Paragraph("Clear open airspace; execution permitted", body_text)],
            [Paragraph("<font color='#B45309'><b>CAUTION</b></font>", body_text), Paragraph("0.23m - 0.50m", body_text), Paragraph("Restricted clearance; warning modal shown", body_text)],
            [Paragraph("<font color='#DC2626'><b>BLOCKED</b></font>", body_text), Paragraph("< 0.23 m", body_text), Paragraph("Rotor collision hazard; blocked without override", body_text)],
        ], colWidths=[75, 70, 150], style=[
            ('BACKGROUND', (0,0), (-1,0), LIGHT_BLUE),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_CARD),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]),
        Spacer(1, 3),
        Paragraph("<b>Research Override Mode:</b> A dedicated toggle switch permits testing unsafe choices deliberately to inspect collision physics and damage telemetry.", body_text),
    ]
    t10 = Table([[card("7-STAGE DECISION PIPELINE", col10_1, 320), card("SAFETY AUDIT & RESEARCH OVERRIDE", col10_2, 320)]], colWidths=[328, 328])
    t10.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t10)
    story.append(PageBreak())

    # SLIDE 11: Interactive Dashboard
    story.append(Spacer(1, -26))
    story.append(slide_header("Full-Stack Dashboard Architecture", "Interactive 3D Simulation & Real-Time Telemetry Dashboard"))
    story.append(Spacer(1, 12))
    col11_1 = [
        Paragraph("<b>Web Dashboard Features (http://localhost:8080):</b>", body_bold),
        Paragraph("• <b>High-Fidelity 3D Viewport:</b> Built with Three.js WebGL. Renders carbon-fiber Tarot 650 quadcopter with spinning rotors, dynamic shadows, and 3D arena wireframe.", bullet_style),
        Paragraph("• <b>LiDAR Laser Visualizer:</b> Renders active dual front LiDAR beams (±20°) and omnidirectional raycasters with distance color-coding (Green/Yellow/Red).", bullet_style),
        Paragraph("• <b>Flight Trajectory Ribbon:</b> 3D continuous flight path visualizer tracking evasive maneuvers in real time.", bullet_style),
        Paragraph("• <b>4 Dynamic Camera Modes:</b>", body_bold),
        Paragraph("  1. <i>Chase Cam:</i> Smooth follow-camera behind the quadcopter.", bullet_style),
        Paragraph("  2. <i>Orbit Cam:</i> Free 360° mouse orbital inspection.", bullet_style),
        Paragraph("  3. <i>Tactical Top:</i> 2D top-down orthogonal spatial overview.", bullet_style),
        Paragraph("  4. <i>FPV Nose:</i> First-person pilot perspective from drone nose.", bullet_style),
    ]
    col11_2 = [
        Paragraph("<b>Interactive Controls & Telemetry HUD:</b>", body_bold),
        Paragraph("• <b>10 Flight Direction Controls:</b> Forward, Backward, Left, Right, Up, Down, Front-Left, Front-Right, Rear-Left, Rear-Right.", bullet_style),
        Paragraph("• <b>Keyboard Hotkeys:</b> Full desktop control (W/A/S/D planar, Q/E/Z/C diagonals, R/F vertical, Space start/pause, Enter confirm, Esc stop).", bullet_style),
        Paragraph("• <b>Dual Pilot Modes:</b> Instant toggle between Autonomous Devos (2018) neural mode and Manual Pilot stick flight.", bullet_style),
        Paragraph("• <b>Live Telemetry HUD:</b> Altitude, Airspeed, Yaw Heading, Clearance meters, and RNN neuron activations (O1, O2, b1, b2, q1, q2).", bullet_style),
        Paragraph("• <b>Simulation Clock:</b> 0.5x, 1.0x, 2.0x, 5.0x simulation speed controls.", bullet_style),
        Paragraph("• <b>WebSocket Bridge:</b> Low-latency 30 Hz bi-directional JSON stream.", bullet_style),
    ]
    t11 = Table([[card("3D VIEWPORT & VISUALIZATION", col11_1, 320), card("CONTROLS, HOTKEYS & TELEMETRY", col11_2, 320)]], colWidths=[328, 328])
    t11.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t11)
    story.append(PageBreak())

    # SLIDE 12: Scenario Library
    story.append(Spacer(1, -26))
    story.append(slide_header("Validation Environments", "Comprehensive 13-Scenario Obstacle Avoidance Library"))
    story.append(Spacer(1, 12))
    sc_table = Table([
        [Paragraph("<b>Scenario ID</b>", body_bold), Paragraph("<b>Scenario Name</b>", body_bold), Paragraph("<b>Threat Geometry & Avoidance Objective</b>", body_bold)],
        [Paragraph("front_obstacle", body_text), Paragraph("Front Obstacle (Direct Ahead)", body_text), Paragraph("Cylindrical pillar directly in forward flight path. Test left/right turn.", body_text)],
        [Paragraph("right_obstacle", body_text), Paragraph("Right Flank Obstacle", body_text), Paragraph("Wall barrier on right side. Test leftward evasion or straight cruise.", body_text)],
        [Paragraph("left_obstacle", body_text), Paragraph("Left Flank Obstacle", body_text), Paragraph("Barrier on left flank. Test rightward evasion.", body_text)],
        [Paragraph("rear_obstacle", body_text), Paragraph("Rear Obstacle (Reverse Threat)", body_text), Paragraph("Obstacle behind quadcopter; tests rear raycast during reverse flight.", body_text)],
        [Paragraph("above_obstacle", body_text), Paragraph("Above Obstacle (Overhead Bridge)", body_text), Paragraph("Low ceiling / overhead pipe. Tests vertical descend or lateral avoidance.", body_text)],
        [Paragraph("below_obstacle", body_text), Paragraph("Below Obstacle (Raised Platform)", body_text), Paragraph("Elevated ground structure. Tests downward sensor and vertical climb.", body_text)],
        [Paragraph("both_sides", body_text), Paragraph("Both Sides Flanked (Lateral Pinch)", body_text), Paragraph("Obstacles on both sides. Evaluates forward narrow escape or reverse.", body_text)],
        [Paragraph("front_left", body_text), Paragraph("Front-Left Diagonal Obstacle", body_text), Paragraph("Threat at +45° quadrant. Tests front-right diagonal escape.", body_text)],
        [Paragraph("front_right", body_text), Paragraph("Front-Right Diagonal Obstacle", body_text), Paragraph("Threat at -45° quadrant. Tests front-left diagonal escape.", body_text)],
        [Paragraph("rear_diagonal", body_text), Paragraph("Rear Diagonal Obstacles", body_text), Paragraph("Pillars at rear-left and rear-right quadrants. Forward escape.", body_text)],
        [Paragraph("multiple_obstacles", body_text), Paragraph("Multiple Clustered Obstacles", body_text), Paragraph("Dense field of 7 pillars and boxes evaluating multi-sensor perception.", body_text)],
        [Paragraph("paper_env2_maze", body_text), Paragraph("Base Paper Env 2: Maze & Deadlocks", body_text), Paragraph("Devos et al. Fig 5(b) reconstruction with sharp corners and deadlocks.", body_text)],
        [Paragraph("clear_flight", body_text), Paragraph("Clear Flight (No Obstacles)", body_text), Paragraph("Open arena baseline verifying flight dynamics, hover, and trims.", body_text)],
    ], colWidths=[85, 145, 410], style=[
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLUE),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_CARD),
        ('TOPPADDING', (0,0), (-1,-1), 1.8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1.8),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ])
    story.append(card("ACTIVE 13-SCENARIO SUITE (CONSTRAINED PASSAGE, MOVING & ENV 1 REMOVED PER USER INSTRUCTION)", [sc_table], 656))
    story.append(PageBreak())

    # SLIDE 13: Methodology Comparison
    story.append(Spacer(1, -26))
    story.append(slide_header("Academic Integrity & Rigor", "Distinction Between Base Paper Ground Truth & Simulation Features"))
    story.append(Spacer(1, 12))
    comp_table = Table([
        [Paragraph("<b>Architectural Dimension</b>", body_bold), Paragraph("<b>Base Research Paper (Devos et al. 2018)</b>", body_bold), Paragraph("<b>Simulation Platform Implementation</b>", body_bold)],
        [Paragraph("Sensing Array", body_text), Paragraph("Dual front LiDARs at ±20° in 2D horizontal plane", body_text), Paragraph("Exact dual front LiDARs (Θ = 40°, Ls = 50cm) plus 8-direction radial and Up/Down 3D sensor suite", body_text)],
        [Paragraph("Avoidance Trigger", body_text), Paragraph("Purely autonomous reactive closed-loop control", body_text), Paragraph("Interactive Human-in-the-Loop decision gate: pauses on detection, holds hover, audits safety, prompts user", body_text)],
        [Paragraph("Maneuver Options", body_text), Paragraph("Continuous yaw steering only (Turn Left / Right)", body_text), Paragraph("10 degrees of freedom (Forward, Reverse, Left, Right, Climb, Descend, 4 Diagonals, Hover, E-Stop)", body_text)],
        [Paragraph("Simulation Engine", body_text), Paragraph("V-REP robotics simulator with C++ ROS interface", body_text), Paragraph("Full 6-DOF Quadcopter Physics + Three.js 3D WebGL Dashboard with 30 Hz async WebSocket stream", body_text)],
        [Paragraph("Embedded Firmware", body_text), Paragraph("Pixhawk 2 autopilot + Raspberry Pi Zero companion SBC", body_text), Paragraph("Python neural backend + complete Arduino C++ firmware (arduino_flight_controller.ino) with SITL/HITL", body_text)],
        [Paragraph("Environments", body_text), Paragraph("2 static test maps (Room exploration & Maze)", body_text), Paragraph("13 scenarios covering all spatial threat angles, clusters, and reconstruction of Paper Env 2", body_text)],
        [Paragraph("Safety Evaluation", body_text), Paragraph("Empirical flight trial observation", body_text), Paragraph("Automated mathematical clearance audit + Research Override Switch to test collisions deliberately", body_text)],
        [Paragraph("Logging & Analytics", body_text), Paragraph("Offline video review and path extraction", body_text), Paragraph("Real-time automated logging with one-click export to CSV and JSON formats", body_text)],
    ], colWidths=[105, 260, 275], style=[
        ('BACKGROUND', (0,0), (-1,0), LIGHT_BLUE),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_CARD),
        ('TOPPADDING', (0,0), (-1,-1), 2.2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ])
    story.append(card("EXHAUSTIVE SIDE-BY-SIDE METHODOLOGICAL MAPPING", [comp_table], 656))
    story.append(PageBreak())

    # SLIDE 14: Experiment Logging & Metrics
    story.append(Spacer(1, -26))
    story.append(slide_header("Experimental Evaluation", "Telemetry Logging, Experiment Analytics & Performance Metrics"))
    story.append(Spacer(1, 12))
    col14_1 = [
        Paragraph("<b>Experiment Logging Schema:</b>", body_bold),
        Paragraph("Every flight trial automatically records a comprehensive experiment record:", body_text),
        Paragraph("• <b>Trial Identification:</b> Unique timestamped ID and active scenario ID.", bullet_style),
        Paragraph("• <b>Flight Coordinates:</b> Initial drone position and final coordinates.", bullet_style),
        Paragraph("• <b>Sensory Snapshot:</b> Exact distance readings on all sensors at moment of detection trigger.", bullet_style),
        Paragraph("• <b>Decision Telemetry:</b> Available safe directions, user-selected direction, executed maneuver, and override flag.", bullet_style),
        Paragraph("• <b>Outcome & Clearance:</b> Success vs Collision status, collision object ID, minimum observed clearance, and avoidance duration.", bullet_style),
        Paragraph("• <b>Operator Response Time:</b> Latency (s) from safe hover alert to directional input.", bullet_style),
    ]
    col14_2 = [
        Paragraph("<b>Quantitative Evaluation Metrics (Logged in CSV/JSON):</b>", body_bold),
        Paragraph("• <b>Success Rate (%):</b> Proportion of avoidance trials completed without rotor breach.", bullet_style),
        Paragraph("• <b>Collision Rate (%):</b> Proportion of trials resulting in collision (primarily during research override testing).", bullet_style),
        Paragraph("• <b>Mean Response Time (s):</b> Average latency taken by human/controller.", bullet_style),
        Paragraph("• <b>Minimum Clearance (m):</b> Minimum distance between drone radius and obstacles throughout the entire evasion trajectory.", bullet_style),
        Paragraph("<b>Base Paper Benchmark Comparison:</b>", body_bold),
        Paragraph("• <i>Low Obstacle Density:</i> 100% collision-free navigation.", body_text),
        Paragraph("• <i>High Obstacle Density:</i> 90% collision-free navigation.", body_text),
        Paragraph("• <i>Deadlocks & Corners:</i> 90% successful escape without human intervention.", body_text),
        Paragraph("• <b>Instant Data Export:</b> Single-click export to CSV and JSON formats.", body_bold),
    ]
    t14 = Table([[card("DATA COLLECTION & LOGGING SCHEMA", col14_1, 320), card("QUANTITATIVE METRICS & BENCHMARKS", col14_2, 320)]], colWidths=[328, 328])
    t14.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t14)
    story.append(PageBreak())

    # SLIDE 15: Software Architecture
    story.append(Spacer(1, -26))
    story.append(slide_header("Software Architecture", "Directory Structure, Codebase Modules & Automated Test Suite"))
    story.append(Spacer(1, 12))
    col15_1 = [
        Paragraph("<b>Modular Project Directory Structure:</b>", body_bold),
        Paragraph("arduino_quadcopter_simulation/<br/>"
                  "├── <b>main.py</b> (aiohttp async server, 30 Hz loop)<br/>"
                  "├── <b>METHODOLOGY.md</b> (Formal mathematical reference)<br/>"
                  "├── <b>requirements.txt</b> (aiohttp, numpy, scipy, pytest)<br/>"
                  "├── <b>simulation/</b><br/>"
                  "│   ├── drone_physics.py (6-DOF quadcopter dynamics)<br/>"
                  "│   ├── scenarios.py (13 active test configurations)<br/>"
                  "│   └── experiment_logger.py (CSV/JSON trial logging)<br/>"
                  "├── <b>avoidance/</b><br/>"
                  "│   ├── neural_controller.py (Devos 2-neuron RNN + plasticity)<br/>"
                  "│   └── decision_engine.py (Direction safety audit & HITL)<br/>"
                  "├── <b>sensors/</b> lidar_sensor.py (Dual LiDAR + 3D raycasting)<br/>"
                  "├── <b>dashboard/</b> (Three.js WebGL, CSS glassmorphism, app.js)<br/>"
                  "├── <b>arduino/</b> (arduino_flight_controller.ino, serial_bridge.py)<br/>"
                  "├── <b>scenarios/</b> (13 exported JSON scenario definitions)<br/>"
                  "└── <b>tests/</b> (Comprehensive automated pytest test suite)", formula_style),
    ]
    col15_2 = [
        Paragraph("<b>Automated Unit Testing Suite (pytest):</b>", body_bold),
        Paragraph("• <b>test_avoidance.py (7 tests):</b> Validates distance normalization boundaries (0.5m → -1, 0.15m → +1), tanh neuron bounds (-1, +1), steering signs (Left obstacle → Right turn), synaptic plasticity updates, and HITL state machine.", bullet_style),
        Paragraph("• <b>test_physics.py (4 tests):</b> Validates 2D circle/box raycasting math, 6-DOF translation dynamics, and collision boundary detection.", bullet_style),
        Paragraph("• <b>test_scenarios.py (3 tests):</b> Validates scenario library integrity, CSV/JSON trial export, and steps through all 13 scenarios with zero collisions.", bullet_style),
        Paragraph("• <b>Execution:</b> <code>python -m pytest tests/</code> — <b>14/14 tests pass</b>.", body_bold),
        Paragraph("<b>Deployment & Launch:</b>", body_bold),
        Paragraph("• Server online at: <b>http://localhost:8080/</b>", body_bold),
        Paragraph("• Command: <code>python main.py</code> (persistent background task).", body_text),
    ]
    t15 = Table([[card("PROJECT DIRECTORY & MODULES", col15_1, 320), card("AUTOMATED UNIT TESTING & VERIFICATION", col15_2, 320)]], colWidths=[328, 328])
    t15.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t15)
    story.append(PageBreak())

    # SLIDE 16: Summary & Conclusions
    story.append(Spacer(1, -26))
    story.append(slide_header("Conclusions & Outlook", "Summary of Achievements, Research Impact & Future Work"))
    story.append(Spacer(1, 12))
    col16_1 = [
        Paragraph("<b>Key Scientific & Engineering Contributions:</b>", body_bold),
        Paragraph("1. <b>Faithful Research Reproduction:</b> Rigorously implemented all equations, parameters, and algorithms from Devos et al. (2018) IEEE DSD and Pedersen & Manoonpong (2018).", bullet_style),
        Paragraph("2. <b>Ultra-Low Compute Footprint:</b> Demonstrated that complex corner navigation and deadlock escape are achievable using just 2 non-spiking tanh neurons and 4 synaptic weights.", bullet_style),
        Paragraph("3. <b>Dual LiDAR Geometry:</b> Validated Equation (1) bounding minimum detectable obstacle width at W_obj ≥ 24 cm for 15 cm turning thresholds.", bullet_style),
        Paragraph("4. <b>Interactive Human-in-the-Loop Workflow:</b> Replaced opaque autonomous loops with a transparent decision gate where human operators inspect clearance geometry and choose directions.", bullet_style),
        Paragraph("5. <b>Hardware-Ready Arduino Integration:</b> Delivered complete C++ firmware and serial bridge supporting real-world hardware deployment.", bullet_style),
    ]
    col16_2 = [
        Paragraph("<b>Future Roadmap & Research Directions:</b>", body_bold),
        Paragraph("• <b>Physical Flight Validation:</b> Transfer Arduino firmware to Tarot 650 quadcopter for real-world GPS-denied tunnel inspections.", bullet_style),
        Paragraph("• <b>ROS 2 & Gazebo Integration:</b> Bridge the Python neural controller to ROS 2 Humble micro-XRCE-DDS for swarm coordination.", bullet_style),
        Paragraph("• <b>Dynamic Obstacle Tracking:</b> Extend synaptic plasticity to predict velocities of moving obstacles in non-stationary environments.", bullet_style),
        Paragraph("• <b>Multi-Agent Collaborative Evasion:</b> Distributed neural consensus among quadcopters in shared corridors.", bullet_style),
        Spacer(1, 4),
        Paragraph("<b>Active Environment Link:</b>", body_bold),
        Paragraph("<b>http://localhost:8080/</b>", formula_style),
        Paragraph("Live 3D simulation with 13 active scenarios, full keyboard control, and telemetry logging.", body_text),
    ]
    t16 = Table([[card("SUMMARY OF CONTRIBUTIONS", col16_1, 320), card("FUTURE WORK & PROJECT ACCESS", col16_2, 320)]], colWidths=[328, 328])
    t16.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    story.append(t16)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF presentation: {output_pdf_path}")


def create_pptx_presentation(output_pptx_path: str):
    """Generates an editable 16-slide PowerPoint presentation with matching classic design."""
    prs = pptx.Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(5.625)

    blank_layout = prs.slide_layouts[6]

    def add_header(slide, category: str, title: str):
        header_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(10), Inches(0.7)
        )
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = PPT_NAVY
        header_shape.line.color.rgb = PPT_NAVY

        gold_line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0), Inches(0.7), Inches(10), Inches(0.04)
        )
        gold_line.fill.solid()
        gold_line.fill.fore_color.rgb = PPT_GOLD
        gold_line.line.color.rgb = PPT_GOLD

        txBox = slide.shapes.add_textbox(Inches(0.4), Inches(0.05), Inches(9.2), Inches(0.6))
        tf = txBox.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p1 = tf.paragraphs[0]
        p1.text = category.upper()
        p1.font.size = Pt(8.5)
        p1.font.bold = True
        p1.font.color.rgb = PPT_GOLD

        p2 = tf.add_paragraph()
        p2.text = title
        p2.font.size = Pt(13.5)
        p2.font.bold = True
        p2.font.color.rgb = PPT_WHITE

        footer_line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, Inches(0.4), Inches(5.2), Inches(9.2), Inches(0.01)
        )
        footer_line.fill.solid()
        footer_line.fill.fore_color.rgb = PPT_BORDER
        footer_line.line.color.rgb = PPT_BORDER

        fBox = slide.shapes.add_textbox(Inches(0.4), Inches(5.25), Inches(9.2), Inches(0.3))
        ftf = fBox.text_frame
        fp = ftf.paragraphs[0]
        fp.text = "Autonomous Quadcopter Obstacle Avoidance Simulation  |  Devos et al. (2018) IEEE DSD"
        fp.font.size = Pt(8)
        fp.font.color.rgb = PPT_MUTED

    def add_card(slide, left, top, width, height, title, bullet_items):
        card_box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height
        )
        card_box.fill.solid()
        card_box.fill.fore_color.rgb = PPT_CARD
        card_box.line.color.rgb = PPT_BORDER
        card_box.line.width = Pt(1)

        txBox = slide.shapes.add_textbox(left + Inches(0.15), top + Inches(0.12), width - Inches(0.3), height - Inches(0.24))
        tf = txBox.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = PPT_NAVY
        p.space_after = Pt(5)

        for item in bullet_items:
            bp = tf.add_paragraph()
            bp.text = item
            bp.font.size = Pt(8)
            bp.font.color.rgb = PPT_DARK
            bp.space_after = Pt(3.5)
            bp.level = 0

    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(10), Inches(5.625))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = PPT_NAVY
    bg1.line.color.rgb = PPT_NAVY

    g_top = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(10), Inches(0.1))
    g_top.fill.solid()
    g_top.fill.fore_color.rgb = PPT_GOLD
    g_top.line.color.rgb = PPT_GOLD

    g_bot = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(5.525), Inches(10), Inches(0.1))
    g_bot.fill.solid()
    g_bot.fill.fore_color.rgb = PPT_GOLD
    g_bot.line.color.rgb = PPT_GOLD

    t_box = s1.shapes.add_textbox(Inches(0.6), Inches(1.0), Inches(8.8), Inches(3.6))
    tf1 = t_box.text_frame
    tf1.word_wrap = True

    p = tf1.paragraphs[0]
    p.text = "AERODRONE AI // AUTONOMOUS QUADCOPTER SIMULATION"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = PPT_WHITE
    p.alignment = PP_ALIGN.CENTER
    p.space_after = Pt(10)

    p2 = tf1.add_paragraph()
    p2.text = "Adaptive Neural Obstacle Avoidance with Synaptic Plasticity & Arduino Flight Control"
    p2.font.size = Pt(13)
    p2.font.color.rgb = PPT_GOLD
    p2.alignment = PP_ALIGN.CENTER
    p2.space_after = Pt(25)

    p3 = tf1.add_paragraph()
    p3.text = ("Based on IEEE Research: Arne Devos, Emad Ebeid, Poramate Manoonpong (2018)\n"
               "'Development of Autonomous Drones for Adaptive Obstacle Avoidance in Real World Environments'\n"
               "21st Euromicro Conference on Digital System Design (DSD), DOI: 10.1109/DSD.2018.00009\n"
               "Theoretical Foundation: Pedersen & Manoonpong (2018), LNAI (Two-Neuron RNN & Synaptic Plasticity)\n"
               "Implementation: 3D WebGL Simulation, 6-DOF Physics, Arduino C++ HITL Firmware, Human-in-the-Loop Decision Gate")
    p3.font.size = Pt(9.5)
    p3.font.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
    p3.alignment = PP_ALIGN.CENTER

    slides_data = [
        ("Project Motivation & Problem Definition", "The Autonomous Drone Navigation Dilemma in Unknown Spaces",
         ("THE PROBLEM: VISION & SLAM COMPLEXITY", [
             "• Quadcopters operating in GPS-denied, cluttered spaces must navigate without human pilots.",
             "• Environments contain unmapped obstacles, narrow passages, sharp corners, and dead-ends.",
             "• Traditional solutions use Visual SLAM, deep CNNs, or heavy spinning 360° LiDARs.",
             "• Heavy GPU compute platforms drain battery power and drastically shorten flight time.",
             "• SLAM mapping easily fails in featureless, repetitive, or reflective indoor tunnels.",
         ]),
         ("THE SOLUTION: ADAPTIVE NEURAL CONTROL", [
             "• Replaces heavy vision pipelines with an ultra-lightweight 2-neuron recurrent neural network.",
             "• Operates on ONLY two narrow-beam (2°) LiDAR sensors mounted at front of frame.",
             "• Short-Term Memory (STM): Retains turn command after obstacle exits laser field of view.",
             "• Synaptic Plasticity: Adapts weights online to escape tight deadlocks and corners.",
             "• Platform: Interactive 3D simulation, 6-DOF physics, and Arduino C++ HITL interface.",
         ])),

        ("Base Paper Methodology", "Closed-Loop Neural Control Architecture (Devos et al. 2018)",
         ("METHODOLOGY & CLOSED-LOOP FLOW", [
             "• Published in IEEE 21st Euromicro Conference on Digital System Design (DSD 2018).",
             "• Dual Garmin LIDAR-Lite v3 sensors measure obstacle range at 50 Hz.",
             "• Raw distance normalized to [-1.0, +1.0] sensory inputs S_L and S_R.",
             "• Discrete-time 2-neuron RNN with non-spiking tanh activation computes states O1, O2.",
             "• Correlation plasticity modifies weights online based on sensor reflexes.",
             "• Differential output generates yaw steering commanded to Pixhawk / Arduino via MAVLink.",
         ]),
         ("PHYSICAL HARDWARE SYSTEM SPECIFICATIONS", [
             "• Frame: Tarot 650 Sport carbon-fiber quadcopter frame.",
             "• Propulsion: 370 KV BLDC motors, 14\" carbon props, 40A ESCs.",
             "• Battery: 6S 22.2V 8000 mAh LiPo (25-minute flight endurance).",
             "• Autopilot: Pixhawk 2 with 3D gyro, accelerometer, barometer, and PID loops.",
             "• Companion SBC: Raspberry Pi Zero executing Python neural navigation.",
             "• Distance Sensors: 2x Garmin LIDAR-Lite v3 (I2C interface, 2° beam).",
             "• Protocol: MAVLink / MAVProxy / DroneKit serial command pipeline.",
         ])),

        ("Mathematical Foundations", "LiDAR Geometry & Minimum Detectable Obstacle Width",
         ("EQUATION (1) & GEOMETRIC FORMULATION", [
             "• To guarantee safety, minimum detectable obstacle width W_obj is governed by Equation (1):",
             "  W_obj ≥ 2 · tan(Θ / 2) · [ Lx + (Ld / 2) ]",
             "• Θ (LiDAR Separation Angle): 40° total angle (±20° relative to forward axis).",
             "• Lx (Safe Turning Distance): 0.15 m (15 cm) turning threshold.",
             "• Ld (Quadcopter Frame Width): 0.34 m (34 cm) rotor-to-rotor span.",
             "• Lm (Rotor Safety Margin): 0.06 m (6 cm) propeller clearance.",
             "• Ls (Max LiDAR Range): 0.50 m (50 cm) active detection horizon.",
         ]),
         ("ANALYTICAL DERIVATION & SAFETY GUARANTEES", [
             "• Evaluating Equation (1) with base paper parameters:",
             "  tan(20°) ≈ 0.36397",
             "  Lx + (Ld / 2) = 0.15 + 0.17 = 0.32 m",
             "  W_obj ≥ 2 · 0.36397 · 0.32 m = 0.2329 m ≈ 24 cm",
             "• Any obstacle ≥ 24 cm is guaranteed to be detected before drone is within 15 cm.",
             "• All obstacles across our scenarios have widths ≥ 24 cm matching paper rigor.",
             "• Minimum Clearance Boundary: Lm + Ld/2 = 0.23 m (rotor collision threshold).",
         ])),

        ("Sensory Processing Pipeline", "LiDAR Range Normalization & Sensory Input Mapping",
         ("NORMALIZATION EQUATION & TRANSFER FUNCTION", [
             "• Raw distance readings d_L, d_R mapped into bipolar normalized signals:",
             "  S_i = clip( [ 2 · (d_max - d_i) / (d_max - d_min) ] - 1.0, -1.0, 1.0 )",
             "• d_max = 0.50 m (sensing range Ls); d_min = 0.15 m (critical turning dist Lx).",
             "• S_i = -1.0: Clear airspace (d_i ≥ 0.50 m), zero reflex excitation.",
             "• S_i = 0.0: Transition boundary (d_i = 0.325 m), reflex begins activating.",
             "• S_i = +1.0: Critical proximity (d_i ≤ 0.15 m), maximum excitatory turning drive.",
         ]),
         ("DUAL SENSOR ARRANGEMENT & 3D EXPANSION", [
             "• Left LiDAR (S_L): Oriented at +20° azimuth relative to drone heading.",
             "• Right LiDAR (S_R): Oriented at -20° azimuth relative to drone heading.",
             "• Narrow 2° beam eliminates ground bounce and multipath interference.",
             "• 3D Simulation Expansion: Adds 8 planar radial raycast beams (0° to 315°)",
             "  plus vertical ceiling and ground laser sensors.",
             "• Feeds multi-directional clearance telemetry to Human-in-the-Loop decision gate.",
         ])),

        ("Bio-Inspired Neural Control", "Two-Neuron Recurrent Network with Mutual Inhibition",
         ("RECURRENT STATE UPDATE EQUATIONS", [
             "• Discrete-time non-spiking neural equations with tanh activation:",
             "  O_1(t) = tanh( b_1(t)·O_1(t-1) + c(t)·O_2(t-1) + I_g·S_L(t) )",
             "  O_2(t) = tanh( b_2(t)·O_2(t-1) + c(t)·O_1(t-1) + I_g·S_R(t) )",
             "• O_1, O_2 ∈ (-1.0, 1.0): Left and Right neuron activation states.",
             "• O_1(t-1), O_2(t-1): Prior activations providing Short-Term Memory.",
             "• b_1, b_2 ∈ [0.1, 8.0]: Self-excitatory recurrent synapses (baseline = 2.40).",
             "• c(t) = -0.5 · [ q_1(t) + q_2(t) ]: Mutual inhibitory cross-coupling (baseline = -3.50).",
             "• I_g = 4.7: Sensory input gain scaling LiDAR inputs.",
         ]),
         ("NEURAL COMPETITION & EFFICIENCY ADVANTAGES", [
             "• Left obstacle stimulates S_L ==> O_1 excites, cross-inhibits O_2 ==> Sharp Right turn.",
             "• Right obstacle stimulates S_R ==> O_2 excites, cross-inhibits O_1 ==> Sharp Left turn.",
             "• Symmetrical inputs broken instantly by historical turning bias and memory.",
             "• Only 4 adaptable synaptic weights vs millions in modern deep learning models.",
             "• Sub-microsecond execution time on microcontroller platforms.",
             "• Requires zero pre-training: operates completely online in closed-loop.",
         ])),

        ("Online Adaptation", "Correlation Plasticity & Synaptic Scaling for Deadlock Escape",
         ("THE DEADLOCK PROBLEM & PLASTICITY EQUATIONS", [
             "• In corners and deadlocks, turning sweeps the obstacle out of narrow 2° LiDAR beams.",
             "• Without plasticity, the drone stops turning too early and collides with walls.",
             "• Online Correlation Plasticity (Pedersen & Manoonpong 2018):",
             "  v_i(t) = clip( [ O_i(t) + 1 ] / 2, 0.0, 1.0 )",
             "  reflex_i(t) = 1.0 if S_i(t) > -0.5 else 0.0",
             "  Δb_i = κ·Δt · [ μ_b·v_i(t-1)·v_i(t)·reflex_i + γ_b·(k - v_i)·b_i² ]",
             "  Δq_i = κ·Δt · [ μ_q·v_i(t-1)·v_i(t)·reflex_i + γ_q·(k - v_i)·q_i² ]",
         ]),
         ("HYPERPARAMETERS & DUAL-PHASE ADAPTATION", [
             "• Scaling rate κ = 27.0; Learning rates μ_b = 0.0065, μ_q = 0.015.",
             "• Homeostatic decay rates γ_b = 0.0003, γ_q = 0.0003; Target baseline k = -0.01.",
             "• Hebbian Potentiation (1st term): Increases b_i and q_i during reflex, prolonging memory.",
             "• Homeostatic Scaling (2nd term): Relaxes weights to baseline in open air.",
             "• Enables drone to complete 90° and 180° turns without getting stuck in corners.",
             "• Base Paper Result: 90% to 100% autonomous escape success in complex deadlocks.",
         ])),

        ("Flight Dynamics & Control", "Yaw Steering Calculation & Proximity Velocity Regulation",
         ("YAW RATE COMMAND GENERATION", [
             "• Steering command is calculated from neural differential:",
             "  steering(t) = 0.5 · [ O_1(t) - O_2(t) ]",
             "  ψ̇_cmd(t) = -k_turn · steering(t)  (k_turn = 1.35 rad/s)",
             "• Left Obstacle (S_L > S_R): steering > 0 ==> ψ̇_cmd < 0 (Turn Right).",
             "• Right Obstacle (S_R > S_L): steering < 0 ==> ψ̇_cmd > 0 (Turn Left).",
             "• Proportional turning speed enables smooth evasive bank angles.",
         ]),
         ("VELOCITY REGULATION & FLIGHT DYNAMICS", [
             "• Forward velocity throttles down when approaching obstacles:",
             "  V_f = 0.00 m/s if S_L > 0.55 and S_R > 0.55 (Head-on Deadlock)",
             "  V_f = 0.025 m/s if max(S_L, S_R) > 0.25 (Very Close)",
             "  V_f = 0.055 m/s if max(S_L, S_R) > -0.15 (Approaching)",
             "  V_f = 0.10 m/s otherwise (Nominal Forward Cruise)",
             "• 6-DOF physics models drag, lift, rotor inertia, and coordinated turns.",
             "• Velocity throttling ensures turn radius fits within available clearance.",
         ])),

        ("Embedded Hardware & Firmware", "Tarot 650 Quadcopter & Arduino Flight Controller Firmware",
         ("ARDUINO C++ FIRMWARE FEATURES", [
             "• Included firmware: arduino/arduino_flight_controller.ino for Mega 2560 / Uno / ESP32.",
             "• 4-Channel ESC PWM pulse generation (D5, D6, D9, D10) at 50 Hz.",
             "• Dual ultrasonic / LiDAR distance sampling matching base paper timing.",
             "• Cascaded PID flight stabilization: Inner rate PID + Outer angle PID.",
             "• X-quadcopter motor mixing matrix (Roll, Pitch, Yaw, Throttle).",
             "• Safety failsafe: Disarms motors on communication timeout or emergency stop.",
         ]),
         ("HITL/SITL SERIAL PROTOCOL & DUAL MODES", [
             "• Bidirectional ASCII telemetry: $TELEM, dL, dR, roll, pitch, yaw, armed, estop.",
             "• Hardware-in-the-Loop (HITL): Connects physical Arduino via USB serial COM port.",
             "• Software-in-the-Loop (SITL): Simulates Arduino firmware transparently when unplugged.",
             "• Physical airframe: Tarot 650 Sport, 370 KV motors, 14\" stiff props, 40A ESCs, 6S LiPo.",
             "• Companion bridge: serial_bridge.py handles UART communications at 115200 baud.",
         ])),

        ("Operator Interaction & Safety", "Human-in-the-Loop (HITL) Obstacle Avoidance Workflow",
         ("7-STAGE DECISION PIPELINE", [
             "• Cruising: Quadcopter cruises forward at 0.10 m/s at Z = 1.0 m hover altitude.",
             "• Detection: Sensor detects obstacle within 0.50 m threshold.",
             "• Simulation Pause: Simulation clock halts forward progression automatically.",
             "• Safe Hover: Quadcopter holds stable hover in WAITING_FOR_USER state.",
             "• Safety Audit: Evaluates clearance across all 10 candidate evasion directions.",
             "• Operator Choice: User clicks direction or presses hotkey (W, A, S, D, Q, E, etc.).",
             "• Execution & Logging: Drone executes maneuver, updates trajectory, and logs trial.",
         ]),
         ("SAFETY AUDIT & RESEARCH OVERRIDE", [
             "• RECOMMENDED: Optimal base-paper neural evasion direction (Green).",
             "• SAFE: Clearance > 0.50 m, open airspace.",
             "• CAUTION: Clearance 0.23 m - 0.50 m, restricted corridor.",
             "• BLOCKED: Clearance < 0.23 m (rotor collision threshold). Blocked by default.",
             "• Research Override Switch: Enables operators to test unsafe decisions deliberately",
             "  to inspect collision physics and damage telemetry for comparative research.",
         ])),

        ("Full-Stack Dashboard Architecture", "Interactive 3D Simulation & Real-Time Telemetry Dashboard",
         ("3D VIEWPORT & VISUALIZATION", [
             "• Web dashboard running on http://localhost:8080 with Three.js WebGL.",
             "• Realistic Tarot 650 quadcopter model with spinning rotors and status LEDs.",
             "• Real-time LiDAR laser beams with impact hit markers (Green/Yellow/Red).",
             "• Continuous 3D flight trajectory ribbon tracing evasion paths.",
             "• 4 Camera Modes: Chase Drone, Free Orbit, Tactical Top-Down, FPV Nose Cam.",
         ]),
         ("CONTROLS, HOTKEYS & TELEMETRY", [
             "• 10 Direction Buttons: Forward, Backward, Left, Right, Up, Down, 4 Diagonals.",
             "• Full Keyboard Shortcuts: W/A/S/D, Q/E/Z/C, R/F, Space (Start/Pause), Enter, Esc.",
             "• Dual Pilot Modes: Instant switch between Autonomous Devos (2018) and Manual Pilot.",
             "• Live Telemetry HUD: Altitude, Airspeed, Yaw Heading, Clearance meters.",
             "• Neural Network Monitor: Real-time values of O1, O2, b1, b2, q1, q2, and plasticity.",
             "• Speed Multipliers: 0.5x, 1.0x, 2.0x, 5.0x simulation clock control.",
         ])),

        ("Validation Environments", "Comprehensive 13-Scenario Obstacle Avoidance Library",
         ("DIRECTIONAL & GEOMETRIC TEST SUITE", [
             "• 1. front_obstacle: Front pillar; lateral evasion.",
             "• 2. right_obstacle: Right flank wall; leftward evasion.",
             "• 3. left_obstacle: Left flank barrier; rightward evasion.",
             "• 4. rear_obstacle: Reverse threat; forward braking.",
             "• 5. above_obstacle: Overhead bridge; vertical descent.",
             "• 6. below_obstacle: Raised platform; vertical climb.",
             "• 7. both_sides: Lateral pinch; reverse/vertical escape.",
         ]),
         ("DIAGONAL, CLUSTER & MAZE SCENARIOS", [
             "• 8. front_left: 45° diagonal threat; front-right evasion.",
             "• 9. front_right: -45° diagonal threat; front-left evasion.",
             "• 10. rear_diagonal: Rear diagonal quadrant threats.",
             "• 11. multiple_obstacles: Dense field of 7 pillars and boxes.",
             "• 12. paper_env2_maze: Devos et al. Fig 5(b) Complex Maze.",
             "• 13. clear_flight: Open airspace baseline.",
             "• Note: Narrow corridor, moving obstacle, and env 1 removed per user request.",
         ])),

        ("Academic Integrity & Rigor", "Distinction Between Base Paper Ground Truth & Simulation Features",
         ("BASE PAPER SPECIFICATIONS", [
             "• Dual front LiDARs in 2D horizontal plane.",
             "• Continuous autonomous reactive closed-loop control.",
             "• Yaw steering only (Turn Left / Right).",
             "• V-REP robotics simulator with C++ ROS bridge.",
             "• Pixhawk 2 + Raspberry Pi Zero companion SBC.",
             "• 2 static test environments (Room & Maze).",
             "• Qualitative trajectory observation.",
         ]),
         ("SIMULATION PLATFORM IMPLEMENTATION", [
             "• Exact dual front LiDARs + 8 radial raycasters + Up/Down 3D sensors.",
             "• Interactive Human-in-the-Loop decision gate with safe hover and safety audit.",
             "• 10 directional degrees of freedom (horizontal, vertical, diagonal).",
             "• 6-DOF Quadcopter Physics + Three.js 3D WebGL Dashboard at 30 Hz.",
             "• Python neural controller + Arduino C++ firmware with SITL/HITL.",
             "• 13 scenarios covering all spatial threat angles.",
             "• Real-time automated logging with one-click export to CSV and JSON.",
         ])),

        ("Experimental Evaluation", "Telemetry Logging, Experiment Analytics & Performance Metrics",
         ("DATA COLLECTION & LOGGING SCHEMA", [
             "• Every trial records Trial ID, Scenario ID, and initial/final positions.",
             "• Captures full sensory snapshot at detection trigger moment.",
             "• Logs available safe directions, user selection, and override status.",
             "• Measures human/controller response time latency (seconds).",
             "• Measures minimum obstacle clearance throughout entire evasion path.",
             "• Records trial outcome: SUCCESS, COLLISION, or TIMEOUT.",
         ]),
         ("QUANTITATIVE METRICS & BENCHMARKS", [
             "• Success Rate (%): Percentage of trials avoided without collision.",
             "• Collision Rate (%): Impact occurrences during research override testing.",
             "• Mean Response Time (s): Average operator decision latency.",
             "• Minimum Clearance (m): Closest point of approach during maneuver.",
             "• Base Paper Benchmark: 100% low density, 90% high density, 90% deadlocks.",
             "• Instant Data Export: Downloadable CSV (/api/logs/csv) and JSON (/api/logs/json).",
         ])),

        ("Software Architecture", "Directory Structure, Codebase Modules & Automated Test Suite",
         ("PROJECT DIRECTORY & MODULES", [
             "• main.py: aiohttp async web server, 30 Hz physics loop, WebSocket hub.",
             "• simulation/: drone_physics.py, scenarios.py, experiment_logger.py.",
             "• avoidance/: neural_controller.py (RNN + plasticity), decision_engine.py.",
             "• sensors/: lidar_sensor.py (dual front LiDAR + 3D raycasting).",
             "• dashboard/: index.html, style.css, three_sim.js, app.js.",
             "• arduino/: arduino_flight_controller.ino, serial_bridge.py.",
             "• scenarios/: 13 JSON scenario definition files.",
             "• tests/: Comprehensive automated pytest unit test suite.",
         ]),
         ("AUTOMATED UNIT TESTING & VERIFICATION", [
             "• test_avoidance.py (7 tests): Normalization bounds, tanh neuron states, steering signs, synaptic plasticity adaptation, and HITL state machine.",
             "• test_physics.py (4 tests): 2D circle/box intersection math, 6-DOF translation dynamics, and collision boundary detection.",
             "• test_scenarios.py (3 tests): Library completeness, CSV/JSON logging, and steps through all 13 scenarios with 0 collisions.",
             "• Execution: python -m pytest tests/ ==> 14/14 tests pass.",
             "• Live Server: http://localhost:8080/ (running continuously in background).",
         ])),

        ("Conclusions & Outlook", "Summary of Achievements, Research Impact & Future Work",
         ("SUMMARY OF CONTRIBUTIONS", [
             "• Faithful Research Reproduction: Implemented equations, parameters, and RNN dynamics from Devos et al. (2018) and Pedersen & Manoonpong (2018).",
             "• Ultra-Low Compute Footprint: Proved deadlocks are resolved using only 2 neurons, 4 weights, and dual lightweight LiDARs.",
             "• Validated Geometric Bounds: Verified Equation (1) with W_obj ≥ 24 cm for 15 cm turning thresholds.",
             "• Interactive Human-in-the-Loop Platform: Combined autonomous neural control with operator decision verification.",
             "• Hardware-Ready Arduino Firmware: Provided complete C++ flight controller code and SITL/HITL bridge.",
         ]),
         ("FUTURE WORK & PROJECT ACCESS", [
             "• Physical flight validation on Tarot 650 quadcopter in real-world tunnels.",
             "• ROS 2 Humble micro-XRCE-DDS integration for multi-agent swarm coordination.",
             "• Dynamic obstacle trajectory prediction in non-stationary environments.",
             "• Distributed neural consensus among quadcopters in shared corridors.",
             "• Live Simulation Link: http://localhost:8080/",
             "• 13 active scenarios, full keyboard controls, and real-time telemetry logging.",
         ]))
    ]

    for cat, title, (c1_title, c1_bullets), (c2_title, c2_bullets) in slides_data:
        s = prs.slides.add_slide(blank_layout)
        add_header(s, cat, title)
        add_card(s, Inches(0.4), Inches(0.85), Inches(4.45), Inches(4.2), c1_title, c1_bullets)
        add_card(s, Inches(5.15), Inches(0.85), Inches(4.45), Inches(4.2), c2_title, c2_bullets)

    prs.save(output_pptx_path)
    print(f"Successfully generated PPTX presentation: {output_pptx_path}")


if __name__ == "__main__":
    pdf_out = os.path.abspath("autonomous_quadcopter_obstacle_avoidance_presentation.pdf")
    pptx_out = os.path.abspath("autonomous_quadcopter_obstacle_avoidance_presentation.pptx")
    
    create_pdf_presentation(pdf_out)
    create_pptx_presentation(pptx_out)
    print("All presentation files generated successfully!")

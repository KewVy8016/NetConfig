---
name: "NetConfig — Device Index"
description: "ระบบภาพของ Nodes และ shared navigation จาก implementation ที่อนุมัติ"
colors:
  accent: "#086281"
  accent-hover: "#064d66"
  graphite: "#1d2838"
  nav-text: "#c9d5df"
  nav-hover: "#2b3b4c"
  ink: "#18232d"
  muted: "#596b7e"
  boundary: "#dce3ea"
  surface: "#ffffff"
  surface-hover: "#f3f6f8"
  selected: "#e7f3f7"
  connected: "#137c42"
  unreachable: "#b52437"
  checking: "#90580d"
  focus: "#15829e"
typography:
  display: {fontFamily: "Ubuntu Sans, sans-serif", fontSize: "45px", fontWeight: 700, lineHeight: 1.18, letterSpacing: "-0.025em"}
  brand: {fontFamily: "Ubuntu Sans, sans-serif", fontSize: "35px", fontWeight: 700, lineHeight: "normal", letterSpacing: "-0.025em"}
  title: {fontFamily: "Noto Sans Thai, IBM Plex Sans Thai, system-ui, sans-serif", fontSize: "20px", fontWeight: 600, lineHeight: 1.6}
  body: {fontFamily: "Noto Sans Thai, IBM Plex Sans Thai, system-ui, sans-serif", fontSize: "14px", fontWeight: 400, lineHeight: 1.6}
  label: {fontFamily: "Noto Sans Thai, IBM Plex Sans Thai, system-ui, sans-serif", fontSize: "15px", fontWeight: 600, lineHeight: 1.6}
  endpoint: {fontFamily: "JetBrains Mono, monospace", fontSize: "17px", fontWeight: 400, lineHeight: 1.6}
rounded:
  control: "6px"
  card: "12px"
spacing:
  compact: "10px"
  action-inline: "18px"
  gap: "16px"
  cell-inline: "20px"
  panel: "24px"
  desktop-inline: "34px"
components:
  button-primary: {backgroundColor: "{colors.accent}", textColor: "{colors.surface}", typography: "{typography.label}", rounded: "{rounded.control}", padding: "10px 18px"}
  button-primary-hover: {backgroundColor: "{colors.accent-hover}"}
  search: {backgroundColor: "{colors.surface}", textColor: "{colors.ink}", rounded: "{rounded.control}", padding: "12px 16px 12px 48px", height: "58px"}
  nav-link: {textColor: "{colors.nav-text}", rounded: "{rounded.control}", padding: "10px 16px"}
  nav-link-active: {backgroundColor: "{colors.accent}", textColor: "{colors.surface}"}
  view-selected: {backgroundColor: "{colors.selected}", textColor: "{colors.accent}"}
  device-card: {backgroundColor: "{colors.surface}", textColor: "{colors.ink}", rounded: "{rounded.card}", padding: "24px"}
---

<!-- ระบบภาพภาษาไทยจากโค้ดจริง: จำกัดขอบเขต Nodes/shared navigation -->
# Design System: NetConfig — Device Index

## Overview

**Creative North Star: "Device Index"**

Device Index ใช้บรรยากาศสารบัญอุปกรณ์ที่อ่านง่าย: เมนู graphite รองรับพื้นที่ทำงานสีขาว เส้นแบ่งสีเทาเย็น และ action สี teal เพื่อให้ผู้ใช้ระบุอุปกรณ์จริงและเปิดงานตั้งค่าได้ทันที รูปทรงเรียบ มุมโค้งน้อย และตัวอักษรที่แยกชื่ออุปกรณ์ออกจาก endpoint ทำให้ข้อมูลเป็นจุดเด่นของหน้าจอ

เอกสารนี้ถอดค่าจาก frontend/src/device-index.css, NodesPage.tsx และ shared navigation ที่ implement ตาม ADR-042 แล้ว ใช้เฉพาะหน้า Nodes และโครง navigation ที่ร่วมกัน; frontend/src/index.css ยังเป็น baseline ของ Add Node, Node Detail, History และ form/config เดิม สัญญาหน้าจอและ interaction ทั้งระบบยังอ้างอิง Design/DESIGN.md; เอกสาร root นี้ไม่ได้อนุมัติการย้าย palette หรือ workflow ของหน้าที่เหลือ

สถานะการส่งมอบและหลักฐานตรวจอยู่ใน docs/UI_REDESIGN_QA.md และ docs/TASKS.md การบันทึก design system ไม่ใช่การรับรองว่า checkpoint ผ่าน; strict comp gate และเหตุการณ์ Rtest ยังไม่ปิด

**Key Characteristics:**

- พื้นที่ทำงานขาวและ navigation graphite
- Action teal พร้อมเส้นแบ่งเทาเย็น
- หัวข้อ Ubuntu Sans, body ภาษาไทย และ endpoint monospace
- พื้นผิวเรียบและสถานะที่มีสี ไอคอน และข้อความ

## Colors

palette เป็น graphite และเทาเย็นบนพื้นที่ขาว โดย teal ใช้กับ action และ navigation ที่ active; ค่าใน frontmatter เป็นค่าจาก implementation ในขอบเขตนี้

- **Primary:** Teal งานตั้งค่า (`accent`) ใช้กับ Add Node, Configure และ active navigation; `accent-hover` เพิ่มน้ำหนักเมื่อ hover, `selected` เป็นพื้นของ Table/Cards ที่เลือก และ `focus` เป็น outline ใน content
- **Neutral:** `graphite` เป็นพื้นเมนู, `nav-text`/`nav-hover` สำหรับข้อความและ hover; `ink` เป็นข้อความหลัก, `muted` เป็นข้อความรอง/Unknown, `boundary` เป็นขอบ, `surface` เป็นพื้นขาว และ `surface-hover` เป็น feedback ของ secondary action
- **Status:** `connected`, `unreachable`, `checking` ใช้กับผลตรวจล่าสุดร่วมกับ icon และ text; Unknown ใช้ `muted`

**The Scoped World Rule.** ใช้ token ชุดนี้เฉพาะ Nodes และ shared navigation; การย้ายหน้าฟอร์มอื่นต้องมีขอบเขตและ Design decision ของงานนั้น

Sidecar สังเคราะห์ tonal ramps ใน OKLCH เพื่อสำรวจสีใน panel เท่านั้น; ramp เหล่านี้ไม่ใช่ token ที่ production ใช้หรืออนุมัติให้ขยาย UI

## Typography

**Display Font:** Ubuntu Sans, sans-serif

**Body Font:** Noto Sans Thai, IBM Plex Sans Thai, system-ui, sans-serif

**Label/Mono Font:** JetBrains Mono, monospace

Ubuntu Sans 700 เก็บใน project และโหลดด้วย `font-display: swap`; body/mono ใช้ Google Fonts import เดิมพร้อม fallback หัวข้ออังกฤษมีน้ำหนักชัดเจน ขณะที่คำอธิบายไทยยังใช้ body เดิมและ endpoint แยกด้วย monospace

- **Display / Brand:** heading ใช้ `display` และย่อเป็น (38px) ที่ tablet, (32px) ที่จอแคบ; brand ใช้ `brand`, Config มี cyan ตาม CSS และเมื่อย่อแสดง NC (20px)
- **Title / Body:** ชื่อ Node ใช้ `title` พร้อม ellipsis/title attribute; body ใช้ `body`, คำอธิบายและ search (18px), คำอธิบายบนจอแคบ (14px)
- **Label / Mono:** controls ใช้ `label`, nav (18px, 500), ชนิดอุปกรณ์ (12px); endpoint ตารางใช้ `endpoint`, Cards (14px), transport (13px, 500, uppercase); wide desktop ขยาย transport/status (16px)

**The Role Pairing Rule.** Ubuntu Sans ใช้กับ brand และหัวข้อ Nodes; body/label ใช้ฟอนต์ไทยเดิม และ endpoint/transport ใช้ JetBrains Mono

## Layout

Sidebar fixed (234px) ชดเชยด้วย content margin และย่อเป็น (64px) ได้ Nodes topbar สูง (62px), content padding (6px 34px 40px); หน้าอื่นยังใช้ padding/topbar ของตนเอง Toolbar gap (16px), search desktop max-width (710px) ตารางกว้างเต็มพื้นที่แต่มี minimum width (960px) และ wrapper เลื่อนได้ Headers สูง (52px), cells (90px), cell padding (16px 20px) Cards ใช้ grid ขั้นต่ำ (310px), gap (20px)

- **Max 1279px:** ขอบ content/topbar (24px), toolbar wrap, search ไม่จำกัด max-width
- **Max 1024px:** content เต็มจอ เมนูปิดถูกซ่อนและเปิดเป็น overlay/backdrop; heading ขนาด tablet
- **Max 600px:** ขอบ content (16px), topbar (12px), search หนึ่งแถว, Cards หนึ่งคอลัมน์, Add Node กระชับลง
- **Min 1536px:** action gap (28px), Configure minimum width (149px), Delete width (52px), status/transport ขยาย

ระยะที่บันทึกเป็นค่าที่ใช้จริง ไม่ใช่ spacing scale ใหม่ให้ทุก form

## Elevation & Depth

Nodes inventory และ Cards ไม่มี box-shadow; hierarchy เกิดจากสีพื้น ขอบ เส้นแบ่ง และช่องว่าง Sidebar graphite แยกจาก content และ tablet backdrop ใช้สีโปร่ง (rgb(14 25 36 / 38%)) baseline ของ form/config ยังใช้ card/dialog/shadow เดิมตาม Design/DESIGN.md

**The Flat Work Plane Rule.** พื้นที่รายการและ Cards ไม่ใช้เงา; hierarchy เกิดจากขอบ เส้นแบ่ง สีพื้น และช่องว่าง

## Shapes

Controls, nav links และ table wrapper ใช้ `rounded.control` พร้อมขอบ (1px) Cards ใช้ `rounded.card` และ `spacing.panel` สถานะใน Nodes ไม่มีพื้น pill/padding เพื่อจัด icon/text ตามแนวข้อมูล

## Components

- **Buttons:** teal/white ตาม `button-primary`; Add Node desktop minimum height (54px), width (174px); Configure padding (10px 12px, 14px) Secondary เป็นขาวมีขอบและ hover เทาอ่อน Delete รองมีกรอบ (42px × 44px), hover red tint, pending opacity (.45) และ disabled; confirmation ระบุชื่อ Node ตาม flow เดิม
- **Inputs:** Search ใช้ `search`, ขนาด (18px), SVG ด้านซ้ายและ Escape ล้างคำค้น Status filter เป็น native select สูง (54px) จาก health result เดิม Focus content outline (2px), offset (4px); sidebar ใช้ cyan สว่างตาม CSS
- **View control:** Table/Cards สูง (52px) มีขอบ/separator; selected ใช้ `view-selected`, `aria-pressed` และ weight (600); hover เป็น teal tint, focus offset (-4px)
- **Cards / Rows:** Cards ใช้ `device-card`, gap (24px) และข้อมูลชุดเดียวกับ Table Rows hover/focus-within มีพื้น teal อ่อนเพื่อระบุบริบท action; ไม่ได้สร้างการเลือกอุปกรณ์หรือสถานะเชื่อมต่อ
- **Navigation:** Nodes/History เป็น SVG links; minimum height (52px), gap (18px), padding ตาม `nav-link` Hover graphite และ active teal Tablet ปิดด้วย link/backdrop/ปุ่มปิด/Escape; sidebar มี `transform 180ms ease-out`, ไม่มี width/margin animation Loading spinner ใช้ (1s linear infinite); reduced motion ปิด transition/animation
- **Status / Feedback:** circle-check, circle-x, loader-circle, circle-help จับคู่ Connected/Unreachable/Checking/Unknown และสี ข้อความผลตรวจล่าสุดอยู่เหนือรายการ; error/empty/loading มีคำไทยและ action ถัดไป

## Do's and Don'ts

### Do:

- **Do** รักษาขอบเขต Nodes/shared navigation และอ่าน Design/DESIGN.md ก่อนขยายไปหน้าฟอร์ม
- **Do** ใช้สีร่วมกับ SVG icon และข้อความกับทุกสถานะ
- **Do** ทำให้ focus มองเห็น และเปิด Configure ผ่าน link ที่ใช้ Enter ได้
- **Do** ใช้ monospace กับ endpoint/transport และข้อความไทยที่ตรงไปตรงมากับ guidance/error
- **Do** ให้สี hover/focus ช่วยระบุแถวที่กำลังใช้งานโดยไม่สร้างสถานะเลือกอุปกรณ์ขึ้นเอง

### Don't:

- **Don't** นำค่า baseline ของ form/config ไปเปลี่ยนเป็น palette ชุดนี้โดยอาศัยเอกสาร root เพียงอย่างเดียว
- **Don't** ใช้ mock data หรือสรุป Connected ว่าเป็น session ที่เปิดอยู่ตลอดเวลา
- **Don't** เพิ่มเงาหรือ gradient เพื่อทำให้ inventory ดูเป็น marketing dashboard
- **Don't** ใช้ emoji หรือ icon แบบตัวอักษรแทน SVG
- **Don't** สรุปว่า QA/checkpoint ผ่านจากการมีเอกสารและ snippets


import streamlit as st
import pandas as pd
import plotly.express as px
import json
import io
from pathlib import Path
from datetime import date

# ==========================================
# 1. ตั้งค่าเว็บไซต์
# ==========================================

st.set_page_config(
    page_title="StayElec | วิเคราะห์ค่าไฟฟ้าที่พัก",
    page_icon="⚡",
    layout="wide"
)

DATA_FILE = Path(__file__).with_name("stayelec_data.json")

# กำลังไฟเริ่มต้นเป็นค่าตัวอย่าง
DEVICES = {
    "เครื่องปรับอากาศ": 900.0,
    "พัดลม": 60.0,
    "โทรทัศน์": 100.0,
    "ตู้เย็น": 100.0,
    "คอมพิวเตอร์": 200.0,
    "เครื่องซักผ้า": 500.0,
    "หม้อหุงข้าว": 700.0,
    "หลอดไฟ LED": 12.0,
    "เครื่องทำน้ำอุ่น": 3500.0,
    "กำหนดเอง": 100.0
}

COLORS = [
    "#8052DF", "#43B8A6", "#66A5ED",
    "#F1B35D", "#E68BB8", "#A08CEB"
]

# ==========================================
# 2. ตกแต่งเว็บไซต์
# ==========================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Prompt', sans-serif;
}

.stApp {
    background: #F8F7FC;
}

.block-container {
    max-width: 1250px;
    padding-top: 1.3rem;
}

[data-testid="stSidebar"] {
    background: #F0EAFB;
    border-right: 1px solid #E8DEF6;
}

[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border-radius: 16px;
    border: 1px solid #EBE4F5;
}

[data-testid="stMetricValue"] {
    color: #6940C6;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 17px !important;
    border-color: #E8E1F2 !important;
}

.stButton button,
.stFormSubmitButton button {
    border-radius: 11px;
}

.stButton button[kind="primary"],
.stFormSubmitButton button[kind="primary"] {
    background: #7549D1;
    border-color: #7549D1;
    color: white;
}

.hero {
    background: linear-gradient(
        110deg, #6540BB, #A581EC
    );
    padding: 26px;
    border-radius: 20px;
    margin-bottom: 22px;
}

.hero h1 {
    color: white;
    font-size: 1.7rem;
    margin: 0;
}

.hero p {
    color: #F1E8FF;
    margin: 8px 0 0;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 3. ฟังก์ชันคำนวณ
# เชื่อมโยงกับ Functions และ Logic
# ==========================================

def money(value):
    return f"฿{value:,.2f}"


def valid_time(hours, minutes):
    # Logic: ตรวจสอบเวลาไม่เกิน 24 ชั่วโมง
    return 0 <= hours * 60 + minutes <= 1440


def calculate(
    watts, hours, minutes,
    quantity, days, rate
):
    # Functions: คำนวณจากตัวแปรที่ผู้ใช้กรอก
    total_hours = hours + minutes / 60

    # 1 หน่วยไฟฟ้า = 1 kWh
    units = (
        watts * total_hours
        * quantity * days / 1000
    )

    cost = units * rate

    return units, cost


def show_chart(fig):
    fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=15, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Prompt",
            color="#554A6C"
        ),
        legend_title_text=""
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==========================================
# 4. โหลดประวัติบิลค่าไฟจริง
# ==========================================

def load_bills():

    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open(
            "r", encoding="utf-8"
        ) as f:
            data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("รูปแบบไฟล์ไม่ถูกต้อง")

        bills_by_month = {}

        for item in data.get("history", []):

            if item.get("source") != "บิลจริง":
                continue

            month = str(item["month"])

            bills_by_month[month] = {
                "month": month,
                "units": float(
                    item.get(
                        "units",
                        item.get("energy", 0)
                    )
                ),
                "bill": float(item["bill"])
            }

        return list(bills_by_month.values())

    except (
        OSError, ValueError, TypeError, KeyError
    ) as error:

        st.error(f"อ่านข้อมูลไม่ได้: {error}")
        st.stop()


# ==========================================
# 5. บันทึกประวัติบิลค่าไฟจริง
# ==========================================

def save_bills(bills):

    try:
        data = {}

        if DATA_FILE.exists():
            with DATA_FILE.open(
                "r", encoding="utf-8"
            ) as f:
                data = json.load(f)

        if not isinstance(data, dict):
            raise ValueError("รูปแบบไฟล์ไม่ถูกต้อง")

        # เก็บข้อมูลเก่าประเภทอื่นไว้
        other_records = [
            item
            for item in data.get("history", [])
            if item.get("source") != "บิลจริง"
        ]

        actual_records = [
            {
                "month": item["month"],
                "source": "บิลจริง",
                "energy": item["units"],
                "bill": item["bill"]
            }
            for item in bills
        ]

        data["history"] = (
            other_records + actual_records
        )

        temp_file = DATA_FILE.with_suffix(".tmp")

        with temp_file.open(
            "w", encoding="utf-8"
        ) as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        temp_file.replace(DATA_FILE)
        return True

    except (
        OSError, ValueError, TypeError, KeyError
    ) as error:

        st.error(f"บันทึกไม่สำเร็จ: {error}")
        return False


# ==========================================
# 6. ข้อมูลสำหรับการใช้งาน
# ==========================================

if "comparison" not in st.session_state:
    st.session_state.comparison = []

if "bills" not in st.session_state:
    st.session_state.bills = load_bills()


# ==========================================
# 7. ฟอร์มเลือกเครื่องใช้ไฟฟ้า
# ==========================================

def device_form(prefix):

    choice = st.selectbox(
        "เลือกเครื่องใช้ไฟฟ้า",
        list(DEVICES.keys()),
        key=f"{prefix}_device"
    )

    # เปลี่ยนกำลังไฟตามอุปกรณ์ที่เลือก
    if st.session_state.get(
        f"{prefix}_previous"
    ) != choice:

        st.session_state[
            f"{prefix}_watts"
        ] = DEVICES[choice]

        st.session_state[
            f"{prefix}_previous"
        ] = choice

    watts = st.number_input(
        "กำลังไฟฟ้า (วัตต์)",
        min_value=0.0,
        step=10.0,
        key=f"{prefix}_watts",
        help="แก้ให้ตรงกับกำลังไฟของอุปกรณ์จริงได้"
    )

    st.write("**ระยะเวลาใช้งานต่อวัน**")

    a, b, c = st.columns(3)

    hours = a.number_input(
        "ชั่วโมง",
        min_value=0,
        max_value=24,
        value=6,
        step=1,
        key=f"{prefix}_hours"
    )

    minutes = b.number_input(
        "นาที",
        min_value=0,
        max_value=59,
        value=0,
        step=1,
        key=f"{prefix}_minutes"
    )

    quantity = c.number_input(
        "จำนวนเครื่อง",
        min_value=1,
        value=1,
        step=1,
        key=f"{prefix}_quantity"
    )

    a, b = st.columns(2)

    days = a.number_input(
        "จำนวนวันที่ใช้งาน",
        min_value=1,
        max_value=366,
        value=30,
        step=1,
        key=f"{prefix}_days"
    )

    rate = b.number_input(
        "อัตราค่าไฟ (บาท/หน่วย)",
        min_value=0.0,
        value=7.0,
        step=0.25,
        format="%.2f",
        key=f"{prefix}_rate"
    )

    return (
        choice, watts, hours,
        minutes, quantity, days, rate
    )


# ==========================================
# 8. เมนูด้านซ้าย
# ==========================================

with st.sidebar:

    st.title("⚡ StayElec")
    st.caption("ระบบวิเคราะห์ค่าไฟฟ้าที่พัก")

    st.divider()

    page = st.radio(
        "เมนู",
        [
            "🏠 คำนวณค่าไฟ",
            "📊 วิเคราะห์และเปรียบเทียบ",
            "📅 ประวัติค่าไฟ"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.caption(
        "คำนวณค่าไฟได้ทันที "
        "โดยไม่ต้องบันทึกเครื่องใช้ไฟฟ้า"
    )


# ==========================================
# 9. ส่วนหัวเว็บไซต์
# ==========================================

st.markdown("""
<div class="hero">
    <h1>⚡ StayElec</h1>
    <p>
        ระบบวิเคราะห์และเปรียบเทียบค่าไฟฟ้าสำหรับที่พัก
    </p>
</div>
""", unsafe_allow_html=True)


# ==========================================
# หน้า 1: คำนวณค่าไฟ
# ==========================================

if page == "🏠 คำนวณค่าไฟ":

    st.header("🏠 คำนวณค่าไฟฟ้า")

    st.write(
        "เลือกเครื่องใช้ไฟฟ้าและกรอกเวลาใช้งาน "
        "เพื่อดูจำนวนหน่วยและค่าไฟได้ทันที"
    )

    left, right = st.columns(
        [1.2, 1],
        gap="large"
    )

    with left:

        with st.container(border=True):

            st.subheader(
                "🔌 ข้อมูลเครื่องใช้ไฟฟ้า"
            )

            (
                choice, watts, hours,
                minutes, quantity,
                days, rate
            ) = device_form("home")

    with right:

        with st.container(border=True):

            st.subheader("📋 ผลการคำนวณ")

            if not valid_time(hours, minutes):

                st.error(
                    "เวลาใช้งานต้องไม่เกิน "
                    "24 ชั่วโมงต่อวัน"
                )

            else:

                units, cost = calculate(
                    watts,
                    hours,
                    minutes,
                    quantity,
                    days,
                    rate
                )

                st.metric(
                    "⚡ จำนวนหน่วยไฟฟ้า",
                    f"{units:,.2f} หน่วย"
                )

                st.metric(
                    "💰 ค่าไฟที่คำนวณได้",
                    money(cost)
                )

                st.divider()

                st.write(f"**อุปกรณ์:** {choice}")

                st.write(
                    f"**เวลาใช้งาน:** "
                    f"{hours} ชั่วโมง "
                    f"{minutes} นาทีต่อวัน"
                )

                st.write(
                    f"**จำนวน:** {quantity} เครื่อง"
                )

                st.write(
                    f"**ระยะเวลา:** {days} วัน"
                )

                st.info(
                    "ผลการคำนวณนี้ไม่ได้ถูกบันทึก"
                    "ลงประวัติค่าไฟ"
                )

    st.caption(
        "กำลังไฟเป็นค่าตัวอย่าง ควรแก้ให้ตรงกับ"
        "อุปกรณ์จริง ผลคำนวณสมมติว่ากำลังไฟคงที่ "
        "ไม่รวมค่าบริการ ภาษี หรือค่าไฟแบบขั้นบันได"
    )


# ==========================================
# หน้า 2: วิเคราะห์และเปรียบเทียบ
# เพิ่ม Sets เข้าไปในระบบ
# ==========================================

elif page == "📊 วิเคราะห์และเปรียบเทียบ":

    st.header(
        "📊 วิเคราะห์และเปรียบเทียบค่าไฟ"
    )

    st.write(
        "เพิ่มเครื่องใช้ไฟฟ้าหลายรายการ "
        "เพื่อทดลองเปรียบเทียบค่าใช้จ่าย"
    )

    # --------------------------------------
    # เพิ่มเครื่องใช้ไฟฟ้า
    # --------------------------------------

    with st.container(border=True):

        st.subheader(
            "＋ เพิ่มรายการเปรียบเทียบ"
        )

        (
            choice, watts, hours,
            minutes, quantity,
            days, rate
        ) = device_form("compare")

        custom_name = st.text_input(
            "ชื่อรายการ (ไม่จำเป็น)",
            placeholder="เช่น แอร์ห้องนอน"
        )

        if st.button(
            "＋ เพิ่มลงตารางเปรียบเทียบ",
            type="primary",
            use_container_width=True
        ):

            # Logic: ตรวจสอบเวลา
            if not valid_time(hours, minutes):

                st.error(
                    "เวลาใช้งานต้องไม่เกิน "
                    "24 ชั่วโมงต่อวัน"
                )

            else:

                # Functions: คำนวณค่าไฟ
                units, cost = calculate(
                    watts,
                    hours,
                    minutes,
                    quantity,
                    days,
                    rate
                )

                st.session_state.comparison.append({

                    # เก็บประเภทอุปกรณ์สำหรับ Sets
                    "ประเภทอุปกรณ์": choice,

                    "เครื่องใช้ไฟฟ้า": (
                        custom_name.strip() or choice
                    ),

                    "กำลังไฟ (วัตต์)": watts,

                    "เวลาใช้งาน/วัน": (
                        f"{hours} ชม. {minutes} นาที"
                    ),

                    "จำนวนเครื่อง": quantity,
                    "จำนวนวัน": days,
                    "หน่วยไฟฟ้า": units,
                    "ค่าไฟ (บาท)": cost
                })

                st.rerun()

    # --------------------------------------
    # แสดงผลเปรียบเทียบ
    # --------------------------------------

    if not st.session_state.comparison:

        st.info(
            "ยังไม่มีรายการเปรียบเทียบ "
            "ลองเพิ่มเครื่องใช้ไฟฟ้าด้านบน"
        )

    else:

        df = pd.DataFrame(
            st.session_state.comparison
        )

        total_units = df[
            "หน่วยไฟฟ้า"
        ].sum()

        total_cost = df[
            "ค่าไฟ (บาท)"
        ].sum()

        # ==================================
        # SETS: หาประเภทอุปกรณ์ที่ไม่ซ้ำกัน
        # ==================================

        # ใช้ชื่อประเภทจริงที่เลือกจากเมนู
        # ไม่ใช่ชื่อรายการที่ผู้ใช้ตั้งเอง
        device_set = set(
            df["ประเภทอุปกรณ์"].tolist()
        )

        # นับจำนวนสมาชิกในเซต
        device_count = len(device_set)

        # แสดงผลรวมทั้ง 3 ช่อง
        a, b, c = st.columns(3)

        a.metric(
            "จำนวนหน่วยไฟฟ้ารวม",
            f"{total_units:,.2f} หน่วย"
        )

        b.metric(
            "ค่าไฟรวม",
            money(total_cost)
        )

        c.metric(
            "ประเภทเครื่องใช้ไฟฟ้า",
            f"{device_count} ประเภท"
        )

        # แสดงสมาชิกของเซต
        st.caption(
            "ประเภทที่เลือก: "
            + ", ".join(sorted(device_set))
        )

        # ----------------------------------
        # ตารางเปรียบเทียบ
        # ----------------------------------

        with st.container(border=True):

            st.subheader(
                "📋 รายการเปรียบเทียบ"
            )

            # ซ่อนคอลัมน์ประเภทอุปกรณ์
            # เพราะใช้สำหรับประมวลผล Sets
            display_df = df.drop(
                columns=["ประเภทอุปกรณ์"]
            )

            st.dataframe(
                display_df.round(2),
                hide_index=True,
                use_container_width=True
            )

        # ----------------------------------
        # กราฟเปรียบเทียบ
        # ----------------------------------

        with st.container(border=True):

            st.subheader(
                "📊 ค่าไฟแต่ละรายการ"
            )

            graph_df = df.reset_index()

            graph_df["รายการ"] = (
                (graph_df["index"] + 1).astype(str)
                + ". "
                + graph_df["เครื่องใช้ไฟฟ้า"]
            )

            fig = px.bar(
                graph_df,
                x="รายการ",
                y="ค่าไฟ (บาท)",
                color="รายการ",
                color_discrete_sequence=COLORS
            )

            fig.update_layout(
                showlegend=False
            )

            show_chart(fig)

        # ----------------------------------
        # ลบรายการทดลอง
        # ----------------------------------

        a, b = st.columns(2)

        if a.button(
            "↩️ ลบรายการล่าสุด",
            use_container_width=True
        ):

            st.session_state.comparison.pop()
            st.rerun()

        if b.button(
            "🗑️ ล้างรายการทั้งหมด",
            use_container_width=True
        ):

            st.session_state.comparison = []
            st.rerun()

        # ----------------------------------
        # ดาวน์โหลด Excel
        # ----------------------------------

        buffer = io.BytesIO()

        with pd.ExcelWriter(
            buffer,
            engine="openpyxl"
        ) as writer:

            df.to_excel(
                writer,
                index=False,
                sheet_name="Comparison"
            )

        st.download_button(
            "⬇️ ดาวน์โหลดผลเปรียบเทียบ Excel",
            data=buffer.getvalue(),
            file_name="StayElec_Comparison.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

        st.caption(
            "ข้อมูลการทดลองไม่ถูกบันทึกลงประวัติ "
            "และจะหายไปเมื่อเริ่มเซสชันใหม่"
        )


# ==========================================
# หน้า 3: ประวัติค่าไฟ
# ==========================================

elif page == "📅 ประวัติค่าไฟ":

    st.header("📅 ประวัติค่าไฟ")

    st.write(
        "บันทึกและตรวจสอบค่าไฟฟ้า"
        "จากบิลจริงในแต่ละเดือน"
    )

    # --------------------------------------
    # บันทึกข้อมูลค่าไฟ
    # --------------------------------------

    with st.container(border=True):

        st.subheader(
            "📋 บันทึกข้อมูลค่าไฟ"
        )

        selected_date = st.date_input(
            "เลือกเดือนของบิล",
            value=date.today(),
            format="DD/MM/YYYY"
        )

        month_key = selected_date.strftime(
            "%Y-%m"
        )

        st.caption(
            f"เดือนที่เลือก: {month_key}"
        )

        existing = next(
            (
                item
                for item in st.session_state.bills
                if item["month"] == month_key
            ),
            None
        )

        with st.form(
            f"actual_bill_{month_key}"
        ):

            a, b = st.columns(2)

            actual_units = a.number_input(
                "จำนวนหน่วยไฟฟ้าตามบิล (หน่วย)",
                min_value=0.0,
                value=(
                    float(existing["units"])
                    if existing else 0.0
                ),
                step=1.0
            )

            actual_bill = b.number_input(
                "ค่าไฟที่จ่ายจริง (บาท)",
                min_value=0.0,
                value=(
                    float(existing["bill"])
                    if existing else 0.0
                ),
                step=1.0
            )

            submitted = st.form_submit_button(
                "💾 บันทึกบิลจริง",
                type="primary"
            )

            if submitted:

                if (
                    actual_units == 0
                    and actual_bill == 0
                ):

                    st.error(
                        "กรุณากรอกข้อมูลจากบิล"
                    )

                else:

                    updated = [
                        item
                        for item in st.session_state.bills
                        if item["month"] != month_key
                    ]

                    updated.append({
                        "month": month_key,
                        "units": actual_units,
                        "bill": actual_bill
                    })

                    if save_bills(updated):

                        st.session_state.bills = updated
                        st.rerun()

    # --------------------------------------
    # รายการย้อนหลัง
    # --------------------------------------

    with st.container(border=True):

        st.subheader(
            "📈 รายการย้อนหลัง"
        )

        records = sorted(
            st.session_state.bills,
            key=lambda item: item["month"]
        )

        if not records:

            st.info(
                "ยังไม่มีข้อมูลบิลค่าไฟจริง"
            )

        else:

            history_df = pd.DataFrame(
                records
            ).rename(columns={
                "month": "เดือน",
                "units": "จำนวนหน่วยไฟฟ้า (หน่วย)",
                "bill": "ค่าไฟจริง (บาท)"
            })

            st.dataframe(
                history_df.round(2),
                hide_index=True,
                use_container_width=True
            )

            # กราฟประวัติค่าไฟ
            fig = px.line(
                history_df,
                x="เดือน",
                y="ค่าไฟจริง (บาท)",
                markers=True,
                color_discrete_sequence=COLORS
            )

            show_chart(fig)

            # ดาวน์โหลด Excel
            buffer = io.BytesIO()

            with pd.ExcelWriter(
                buffer,
                engine="openpyxl"
            ) as writer:

                history_df.to_excel(
                    writer,
                    index=False,
                    sheet_name="Actual Bills"
                )

            st.download_button(
                "⬇️ ดาวน์โหลดประวัติ Excel",
                data=buffer.getvalue(),
                file_name="StayElec_Actual_Bills.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
            )

            # ลบข้อมูลประวัติ
            with st.expander(
                "🗑️ ลบข้อมูลบิลจริง"
            ):

                selected_month = st.selectbox(
                    "เลือกเดือนที่ต้องการลบ",
                    history_df["เดือน"].tolist()
                )

                confirm = st.checkbox(
                    "ยืนยันการลบข้อมูลเดือนนี้"
                )

                if st.button(
                    "ลบข้อมูลเดือนที่เลือก",
                    disabled=not confirm
                ):

                    updated = [
                        item
                        for item in st.session_state.bills
                        if item["month"] != selected_month
                    ]

                    if save_bills(updated):

                        st.session_state.bills = updated
                        st.rerun()


# ==========================================
# ส่วนท้ายเว็บไซต์
# ==========================================

st.divider()

st.caption(
    "StayElec | "
    "ระบบวิเคราะห์และเปรียบเทียบค่าไฟฟ้าสำหรับที่พัก"
)
